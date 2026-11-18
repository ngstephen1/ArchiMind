"""A separate concept workspace; existing catalog and chat snapshots stay separate."""

import os

import streamlit as st

from archimind.assets.designer_concepts import approved_chairs, preview_bytes
from archimind.models import Door, Room, Window
from archimind.render import render_design_3d, render_floorplan
from archimind.render.realistic_viewer import _component
from archimind.studio.contracts import StudioError, digest
from archimind.studio.workflow import (
    ChairBinding,
    build_room,
    propose_room,
    scene_payload,
)

DRAFT = "studio_draft"
BUILD = "studio_build"
SIGNATURE = "studio_input_signature"
REVISION = "studio_generation_revision"


def room_from_editor(width, depth, height, doors, windows):
    def records(value):
        return value.to_dict("records") if hasattr(value, "to_dict") else value

    return Room(
        id="studio-room",
        name="3D Studio room",
        width_m=float(width),
        depth_m=float(depth),
        ceiling_height_m=float(height),
        doors=[
            Door(id=f"studio-door-{i}", **row)
            for i, row in enumerate(records(doors), 1)
        ],
        windows=[
            Window(id=f"studio-window-{i}", **row)
            for i, row in enumerate(records(windows), 1)
        ],
    )


def _review_designer_chair():
    options = {chair.sha256: chair for chair in approved_chairs()}
    key = "studio_designer_chair"
    previous = st.session_state.get(key)
    if not options and not previous:
        return None, False

    def label(key):
        if key is None:
            return "No additional chair"
        chair = options.get(key)
        return (
            f"{chair.name} · {chair.variant_label} · v{chair.version}"
            if chair
            else "Unavailable chair"
        )

    choices = [None, *options]
    if previous and previous not in choices:
        choices.append(previous)
    selected = st.selectbox(
        "Add a designer chair",
        choices,
        index=choices.index(previous),
        format_func=label,
        key=key,
    )
    if selected is None:
        return None, False
    chair = options.get(selected)
    if chair is None:
        st.warning("The selected chair is unavailable. Choose another option to build.")
        return None, True
    try:
        front = preview_bytes(chair, "front")
        angled = preview_bytes(chair, "three-quarter")
    except ValueError:
        st.warning("Chair previews are unavailable. Choose another option to build.")
        return None, True
    st.image([front, angled], caption=["Front", "Three-quarter"], width=220)
    st.caption(
        f"One additional designer chair · {chair.width_m:g} × {chair.depth_m:g} × {chair.height_m:g} m (W × D × H)."
    )
    return ChairBinding(
        concept_id=chair.concept_id, version=chair.version, sha256=chair.sha256
    ), False


def render_studio():
    st.title("ArchiMind 3D Studio")
    st.link_button("Back to existing workflows", "?workspace=design")
    st.write(
        "Create a furnished rectangular bedroom, living room or home office from procedural shapes. Set the measured room, review proposed furnishings, then build synchronized A/B concept layouts."
    )
    st.caption(
        "Concept furniture has no verified manufacturer, price or product qualification. Spatial checks use conservative rectangular reservations; style and intended-use suitability are not certified. No voice input or dataset access."
    )
    kind = st.selectbox(
        "Room type", ["Bedroom", "Living room", "Home office"], key="studio_kind"
    )
    cols = st.columns(3)
    width = cols[0].number_input(
        "Width (m)", min_value=1.0, max_value=20.0, value=5.0, key="studio_width"
    )
    depth = cols[1].number_input(
        "Depth (m)", min_value=1.0, max_value=20.0, value=4.0, key="studio_depth"
    )
    height = cols[2].number_input(
        "Ceiling height (m)",
        min_value=1.0,
        max_value=6.0,
        value=2.7,
        key="studio_height",
    )
    st.caption(
        "Southwest origin. North/south offsets start at WEST; east/west offsets start at SOUTH. Enter measured openings; defaults are editable example measurements."
    )
    wall_config = {
        "wall": st.column_config.SelectboxColumn(
            "Wall", options=["south", "east", "north", "west"], required=True
        )
    }
    st.markdown("#### Entrances")
    doors = st.data_editor(
        [{"wall": "south", "offset_m": 0.6, "width_m": 0.85, "height_m": 2.1}],
        num_rows="dynamic",
        column_config=wall_config,
        hide_index=True,
        key="studio_doors",
    )
    windows = []
    if st.checkbox("Include windows", value=True, key="studio_windows_enabled"):
        st.markdown("#### Windows")
        windows = st.data_editor(
            [
                {
                    "wall": "north",
                    "offset_m": 2.7,
                    "width_m": 1.5,
                    "height_m": 1.2,
                    "sill_height_m": 0.9,
                }
            ],
            num_rows="dynamic",
            column_config=wall_config,
            hide_index=True,
            key="studio_windows",
        )
    brief = st.text_area(
        "Design brief",
        "A warm contemporary interior with recognizable furniture, wood details and a calm blue-green palette. Keep the entrance accessible.",
        max_chars=4000,
        key="studio_brief",
    )
    seed = st.number_input(
        "Layout seed", min_value=0, max_value=2**32 - 1, value=42, key="studio_seed"
    )
    room, problem = None, None
    try:
        room = room_from_editor(width, depth, height, doors, windows)
        if not room.doors:
            raise ValueError
    except (ValueError, TypeError):
        problem = "Complete the room measurements and at least one entrance. Every opening must fit its wall and ceiling."
        st.error(problem)
    signature = digest(
        {
            "room": None if room is None else room.model_dump(mode="json"),
            "kind": kind,
            "brief": brief,
        }
    )
    if st.session_state.get(SIGNATURE) != signature:
        st.session_state.pop(DRAFT, None)
        st.session_state[SIGNATURE] = signature
    st.markdown("### 1. Propose furnishings")
    allow = st.checkbox(
        "Allow submitted 3D creation actions to send this room and brief to OpenAI",
        key="studio_consent",
    )
    enabled = os.environ.get("ARCHIMIND_ENABLE_OPENAI_STUDIO", "0") == "1"
    if not enabled:
        st.info(
            "Live creation is disabled. The offline examples work without credentials or API requests."
        )
    st.caption(
        "Offline examples use fixed furniture and colors; they do not interpret the design brief."
    )
    st.caption(
        "Propose makes one model request. Build makes up to eight requests, two at a time, for unique furniture recipes. No automatic retries; a build has a 180-second request deadline. Reruns and A/B/view controls make no requests."
    )
    if st.button(
        "Load example furnishing plan",
        key="studio_example",
        disabled=problem is not None,
    ):
        st.session_state.pop(DRAFT, None)
        try:
            st.session_state[DRAFT] = propose_room(room, kind, brief, offline=True)
        except (StudioError, ValueError):
            st.error(
                "The example furniture does not fit this room. Adjust the room or propose a custom furnishing plan."
            )
    if st.button(
        "Propose AI furnishing plan",
        key="studio_propose",
        disabled=not (room and allow and enabled),
    ):
        try:
            with st.spinner("Proposing concept furnishings…"):
                st.session_state[DRAFT] = propose_room(
                    room, kind, brief, allow_live=allow
                )
        except StudioError as e:
            st.session_state.pop(DRAFT, None)
            st.error(str(e))
        except Exception:
            st.session_state.pop(DRAFT, None)
            st.error(
                "The furnishing plan could not be created. Previous displayed results have been kept."
            )
    draft = st.session_state.get(DRAFT)
    if draft is not None:
        st.markdown("### 2. Review proposed concepts")
        st.text(draft.plan.description)
        st.caption(
            f"Source: {draft.source} · {len(draft.plan.items)} unique recipes · {sum(i.quantity for i in draft.plan.items)} furniture instances. Dimensions below are proposed whole-object reservations, not product facts. Revise the brief to request a different plan."
        )
        st.dataframe(
            [i.model_dump() for i in draft.plan.items],
            hide_index=True,
            key="studio_plan_review",
        )
        chair_binding, chair_problem = _review_designer_chair()
        if st.button(
            "Build 3D room",
            key="studio_build_button",
            type="primary",
            disabled=chair_problem
            or (draft.source == "ai_concept" and not (allow and enabled)),
        ):
            try:
                with st.spinner("Placing furniture and building bounded 3D recipes…"):
                    built = build_room(
                        draft, int(seed), allow_live=allow, designer_chair=chair_binding
                    )
            except StudioError as e:
                st.error(str(e))
            except Exception:
                st.error(
                    "The room could not be built. Previous displayed results have been kept."
                )
            else:
                st.session_state[BUILD] = built
                st.session_state[REVISION] = st.session_state.get(REVISION, 0) + 1
    built = st.session_state.get(BUILD)
    if built is None:
        return
    st.markdown("### Currently displayed concept room")
    st.caption(
        f"Source: {built.draft.source} · seed {built.seed} · snapshot {built.snapshot_id[:16]}. Pending inputs do not change this result."
    )
    if signature != digest(
        {
            "room": built.draft.room().model_dump(mode="json"),
            "kind": built.draft.room_kind,
            "brief": built.draft.brief,
        }
    ):
        st.info(
            "Room inputs changed. The displayed room still belongs to the earlier build."
        )
    if built.designer_chair is not None:
        st.caption(
            f"Designer chair · {built.designer_chair.concept_id} · version {built.designer_chair.version} · SHA-256 {built.designer_chair.sha256}"
        )
    result = built.result()
    if result.status != "complete":
        st.warning(
            f"{result.status}: {len(result.candidates)} of 2 alternatives found. {result.message}"
        )
    else:
        st.success(f"Built {len(result.candidates)} validated concept alternatives.")
    if not result.candidates:
        return
    revision = st.session_state[REVISION]
    labels = [f"Layout {c}" for c in "AB"[: len(result.candidates)]]
    label = st.radio(
        "Concept alternative",
        labels,
        horizontal=True,
        key=f"studio_selection_{revision}",
    )
    candidate = result.candidates[labels.index(label)]
    st.caption(
        f"{label} · Validation: {candidate.validation.status} · Comparison score: {candidate.score.total:g} · {result.attempts_used} search attempts. Rotation is 0°; no building-code or functional suitability certification."
    )
    st.plotly_chart(
        render_floorplan(candidate.design),
        width="stretch",
        theme=None,
        key="studio_floorplan",
    )
    view = st.radio(
        "Concept view",
        ["Procedural 3D", "Plotly schematic"],
        horizontal=True,
        key="studio_view",
    )
    if view == "Procedural 3D":
        with st.container(key=f"selected-realistic-owner-{revision}"):
            _component()(
                data=scene_payload(built, candidate), key=f"studio-realistic-{revision}"
            )
    else:
        st.plotly_chart(
            render_design_3d(candidate.design),
            width="stretch",
            theme=None,
            key="studio_schematic",
        )
    st.download_button(
        "Download concept snapshot",
        built.model_dump_json(indent=2),
        file_name="archimind-concept-room.json",
        mime="application/json",
        key="studio_download",
    )
