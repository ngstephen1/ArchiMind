"""Optional bedroom references for the next chat specification (P4, default off).

The server turns this on with ``ARCHIMIND_ENABLE_DATASET_REFERENCES=1``. It
reads a verified pack only from the server-side ``ARCHIMIND_DATASET_REFERENCE_ROOT``.
The audience is ``public`` unless the server sets
``ARCHIMIND_DATASET_REFERENCE_AUDIENCE=local``, which is for research checkouts
only. Users never supply a path or URL.

References are examples. They never change product choices, preparation,
generation or the currently displayed A/B results, and they make no model,
provider, network or acquisition calls. Their state lives under ``dataset_ref``
session keys, separate from chat preparation and generation state.
"""

import os
from pathlib import Path

import streamlit as st

FLAG = "ARCHIMIND_ENABLE_DATASET_REFERENCES"
ROOT_ENV = "ARCHIMIND_DATASET_REFERENCE_ROOT"
AUDIENCE_ENV = "ARCHIMIND_DATASET_REFERENCE_AUDIENCE"
PREFIX = "dataset_ref"
RESULT = "dataset_ref_result"
PREVIEW = "dataset_ref_preview_rank"

SOURCE_LABELS = {
    "ssr_3dfront": "SSR-3DFRONT (derived from 3D-FRONT / 3D-FUTURE)",
    "midi_3dfront": "MIDI-3D (3D-FRONT)",
}
UNAVAILABLE = {
    "not_configured": "No reference pack is configured on this server.",
    "pack_not_found": "The configured reference pack is not present on this server.",
    "pack_not_public": "The configured reference pack is approved for local research only, not for this audience.",
    "source_not_public": "A reference source lacks public permission.",
    "assets_not_public": "Reference meshes lack public permission.",
}


def enabled() -> bool:
    return os.environ.get(FLAG, "0") == "1"


def clear_reference_state() -> None:
    """Drop pending references only; displayed results and preparation stay."""
    for key in list(st.session_state):
        if key.startswith(PREFIX):
            del st.session_state[key]


def _select_preview(rank: int) -> None:
    st.session_state[PREVIEW] = rank


def _pack_key():
    root = os.environ.get(ROOT_ENV, "").strip()
    audience = os.environ.get(AUDIENCE_ENV, "public")
    try:
        stat = (Path(root) / "manifest.json").stat() if root else None
        version = (stat.st_mtime_ns, stat.st_size) if stat else None
    except OSError:
        version = None
    return root, audience, version


@st.cache_resource(max_entries=2, show_spinner=False)
def _load(root: str, audience: str, version):
    from archimind.datasets.search import load_reference_pack

    # ``version`` is part of the cache key, so a replaced manifest reloads and
    # re-verifies the pack.
    return load_reference_pack(Path(root) if root else None, audience=audience)


def current_pack():
    root, audience, version = _pack_key()
    return _load(root, audience, version)


def _hit_text(hit) -> str:
    room = hit.room
    matched = ", ".join(
        f"{m.found}/{m.requested} {m.term or m.category.replace('_', '/')}"
        for m in hit.category_matches
    )
    return (
        f"**#{hit.rank} · {hit.reference_id}**  \n"
        f"{SOURCE_LABELS.get(hit.source, hit.source)} · split {hit.split} · "
        f"{'canonical' if hit.tier == 'canonical' else 'reference only'}  \n"
        f"Room {room.width_m:.2f} × {room.depth_m:.2f} × {room.height_m:.2f} m · "
        f"matched {matched or 'no category requests'} · "
        f"openings {'recorded' if hit.openings == 'known' else 'unknown'}"
    )


def _render_preview(hit, pack) -> None:
    from archimind.datasets.search import prepare_reference_preview

    preview = prepare_reference_preview(hit, pack=pack)
    if preview.status != "ready":
        message = {
            "stale_snapshot": "The reference pack changed since this search. Find references again.",
            "reference_not_found": "This reference is no longer in the pack.",
        }.get(preview.reason, "This preview is unavailable.")
        st.warning(message)
        return
    for label in preview.labels:
        st.caption(label)
    failed = [c.name for c in preview.checks if c.status == "FAIL"]
    if failed:
        st.caption("Source checks that did not pass: " + ", ".join(failed) + ".")
    if preview.display == "canonical_footprints":
        from archimind.models import Furniture, Room, RoomDesign
        from archimind.render import render_floorplan

        design = RoomDesign(
            name="Reference footprints (not validated)",
            room=Room(
                id="reference-room",
                name="Reference room (doors and windows unknown)",
                width_m=preview.room.width_m,
                depth_m=preview.room.depth_m,
                ceiling_height_m=preview.room.height_m,
            ),
            furniture=[
                Furniture(
                    id=f"reference-{i}",
                    name=o.category.replace("_", "/"),
                    category=o.category,
                    x_m=o.x_m,
                    y_m=o.y_m,
                    width_m=o.width_m,
                    depth_m=o.depth_m,
                    height_m=o.height_m,
                )
                for i, o in enumerate(preview.objects, start=1)
            ],
        )
        st.plotly_chart(
            render_floorplan(design),
            width="stretch",
            theme=None,
            key=f"dataset-ref-floorplan-{hit.rank}",
            config={"scrollZoom": True, "displaylogo": False},
            alt="Top-down reference footprints; doors and windows unknown; not a validated layout.",
        )
        st.caption(
            "Reference footprints only. Doors and windows are not drawn because the source "
            "does not record them; this is not a spatially approved layout."
        )
    else:
        st.info(
            "Not drawn as a floor plan: this reference has furniture at quarter turns, "
            "which the canonical preview does not support. Footprints are listed instead."
        )
        st.dataframe(
            [
                {
                    "Category": o.category,
                    "x, y (m)": (o.x_m, o.y_m),
                    "W × D × H (m)": (o.width_m, o.depth_m, o.height_m),
                    "Quarter turns": o.yaw_quarter_turns,
                }
                for o in preview.objects
            ],
            hide_index=True,
            width="stretch",
        )


def render_dataset_references(draft) -> None:
    """Explicit, local reference retrieval for a ready chat draft."""
    if not enabled():
        return
    from archimind.datasets.canonical import digest
    from archimind.datasets.search import (
        reference_query_from_chat,
        search_references,
    )

    with st.container(key="dataset_references"):
        st.markdown("#### References for next specification")
        st.caption(
            "Example bedrooms from research datasets, to compare against this draft. They are "
            "not products and change no selections. Currently displayed results are unaffected."
        )
        try:
            query = reference_query_from_chat(draft)
        except ValueError:
            clear_reference_state()
            st.info("This draft cannot be turned into a reference query.")
            return
        stored = st.session_state.get(RESULT)
        if stored is not None and stored.query_digest != digest(query.model_dump()):
            # Changed pending measurements or requests invalidate references only.
            clear_reference_state()
            stored = None
        if st.button("Find bedroom references", key="dataset_ref_find"):
            st.session_state.pop(PREVIEW, None)
            stored = search_references(query, pack=current_pack())
            st.session_state[RESULT] = stored
        if stored is None:
            st.caption(
                "Nothing searched yet. Searching is local and makes no model requests."
            )
            return
        if stored.status == "unavailable":
            st.warning(
                UNAVAILABLE.get(stored.reason, "The reference pack is unavailable.")
                + " Chat, product choices and generation are unaffected."
            )
            return
        if stored.status == "empty":
            st.info(
                "No reference bedroom has any of the requested furniture."
                if stored.reason == "no_matches"
                else "The draft has nothing to search for yet."
            )
            return
        pack = current_pack()
        st.caption(
            f"Pack {stored.pack_id} · snapshot {stored.snapshot_id[:12]} · "
            f"{len(stored.scene_hits)} of {stored.eligible_scenes} eligible references"
        )
        for hit in stored.scene_hits:
            with st.container(border=True):
                st.markdown(_hit_text(hit))
                for reason in hit.reasons:
                    st.caption(reason)
                if hit.aliases:
                    st.caption(
                        "Identical content also appears as: " + ", ".join(hit.aliases)
                    )
                # A callback sets the selection before the rerun, so exactly one
                # preview is drawn per run regardless of hit order.
                st.button(
                    "Preview reference",
                    key=f"dataset_ref_preview:{hit.rank}",
                    on_click=_select_preview,
                    args=(hit.rank,),
                )
                if st.session_state.get(PREVIEW) == hit.rank:
                    _render_preview(hit, pack)
        if stored.asset_status == "no_assets_in_pack":
            st.caption("No reference meshes are approved in this pack.")
        for limitation in stored.limitations:
            st.caption(limitation)
        st.caption(
            "Attribution: 3D-FRONT and 3D-FUTURE (Alibaba Tianchi) via SSR-3DFRONT. "
            "Research datasets; check the pack's permission record before any public use."
        )
