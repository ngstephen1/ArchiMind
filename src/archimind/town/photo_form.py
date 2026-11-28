"""Room-photo intake for the private Town editor."""

import json

import streamlit as st

from archimind.designer_handoff.survey import Survey
from archimind.studio.contracts import StudioError

from .room_photos import prepare_photo, review_photos


def photo_form(project, revision, home, *, allow_analysis):
    room_ids = (
        [r["design"]["room"]["id"] for r in home["rooms"]] if home else ["bedroom"]
    )
    room = st.selectbox(
        "Room for these photos",
        room_ids,
        index=room_ids.index("bedroom") if "bedroom" in room_ids else 0,
        key=f"photo-room-{project}",
    )
    prefix = f"intake-{project}-{revision}-{room}"
    uploads = st.file_uploader(
        "Add 1–4 room photos",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=prefix + "-photos",
        max_upload_size=8,
    )
    if not uploads:
        st.caption(
            "Photograph the doorway, window and furniture from different corners. Record dimensions separately."
        )
        return
    if len(uploads) > 4:
        st.error("Choose up to four photos.")
        return
    if any(upload.size > 8 * 1024 * 1024 for upload in uploads):
        st.error("Choose photos under 8 MiB each.")
        return
    try:
        photos = [prepare_photo(file.getvalue()) for file in uploads]
    except ValueError as exc:
        st.error(str(exc))
        return
    ids = [digest for digest, _ in photos]
    if len(set(ids)) != len(ids):
        st.error("Remove duplicate views.")
        return
    key = prefix + "-" + "-".join(ids)
    cols = st.columns(min(2, len(photos)))
    for index, (digest, jpeg) in enumerate(photos):
        cols[index % 2].image(jpeg, caption=f"Photo {index + 1} · {digest[:10]}")
    st.caption(
        "Upload previews are session-only. The intake download contains fingerprints and notes. Keep the original photos with your survey."
    )
    if allow_analysis:
        consent = st.checkbox(
            "Send these resized photos to OpenAI for one visual review",
            key=key + "-consent",
        )
        if st.button(
            "Review visible features", key=key + "-review", disabled=not consent
        ):
            try:
                with st.spinner("Reading room photos…"):
                    st.session_state[key] = [
                        x.model_dump()
                        for x in review_photos([p for _, p in photos], consent)
                    ]
            except (ValueError, StudioError) as exc:
                st.error(str(exc))
    with st.form(key + "-reviewed-intake"):
        notes = []
        for index, row in enumerate(st.session_state.get(key, [])):
            if st.checkbox(
                f"Photo {row['photo']} · {row['observation']} — {row['field_question']}",
                key=f"{key}-accept-{index}",
            ):
                notes.append(
                    dict(
                        row,
                        source_sha256=ids[row["photo"] - 1],
                        status="reviewed visual observation",
                    )
                )
        for index, digest in enumerate(ids):
            note = st.text_input(
                f"Your observation for photo {index + 1}",
                max_chars=600,
                key=key + f"-note-{index}",
            )
            if note.strip():
                notes.append(
                    {
                        "source_sha256": digest,
                        "observation": note.strip(),
                        "status": "user observation",
                    }
                )
        record = {
            "schema_version": 1,
            "kind": "room-photo-intake",
            "project": project,
            "revision": revision,
            "home_id": home["id"] if home else None,
            "room": room,
            "photo_sha256": ids,
            "observations": notes,
            "survey": None,
        }
        survey_file = st.file_uploader(
            "Attach a dated measured-room survey (JSON)",
            type="json",
            key=key + "-survey",
        )
        prepare = st.form_submit_button("Prepare intake download")
    if not prepare:
        return
    if survey_file:
        try:
            if survey_file.size > 128000:
                raise ValueError("The survey exceeds 128 KB.")
            survey = Survey.model_validate_json(survey_file.getvalue())
            if (
                survey.project_id != project
                or survey.source_kind != "measured"
                or not survey.surveyed_on
            ):
                raise ValueError("Use a dated measured survey for this project.")
        except ValueError as exc:
            st.error(str(exc))
            return
        record["survey"] = survey.model_dump(mode="json")
        record["field_questions"] = survey.verification_items()
        st.write("Survey boundary", survey.vertices_m)
    else:
        record["field_questions"] = [
            "Measure the room perimeter, independent check dimension, ceiling, openings and retained furniture."
        ]
        st.caption("Room dimensions and clearances await a measured survey.")
    st.download_button(
        "Download room intake",
        json.dumps(record, indent=2),
        file_name=f"{room}-r{revision}-intake.json",
        mime="application/json",
        key=key + "-export",
    )
