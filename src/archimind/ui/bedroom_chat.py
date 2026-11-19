"""Conversation is pending input; existing generation/results remain authoritative."""

import os
import re

import streamlit as st

from archimind.agents.catalog_conversation import (
    interpret_catalog_conversation,
    validate_turns,
)
from archimind.agents.catalog_requirements import CatalogChatTurn
from archimind.assets.chat_specifications import (
    prepare_chat_specification,
    procedural_options,
    retrieve_chat_candidates,
)
from archimind.assets.specifications import (
    PreparedCatalogSpecification,
    catalog_product_options,
    fingerprint,
)
from archimind.retrieval import resolve_result

TURNS = "chat_bedroom_turns"
RESULT = "chat_bedroom_result"
MATCHES = "chat_bedroom_matches"
REVISION = "chat_bedroom_revision"
PREPARED = "chat_bedroom_prepared"
SIGNATURE = "chat_bedroom_signature"


def _plain(text: str) -> str:
    """One short line with markdown control characters escaped."""
    text = " ".join(text.split())[:120]
    return re.sub(r"([\\`*_{}\[\]<>#|~])", r"\\\1", text)


def _unsupported_reasons(extraction, turns) -> list[str]:
    """What made a request unsupported, in the user's own words where possible."""
    if extraction is None:
        return []
    from archimind.agents.catalog_conversation import _request_constraint

    reasons = []
    if extraction.room_type == "unsupported":
        reasons.append("only bedrooms are supported")
    if extraction.shape == "unsupported":
        reasons.append("only single rectangular rooms are supported")
    reasons += [_plain(f) for f in extraction.unsupported_features]
    reasons += [
        f"mandatory constraint: {_plain(c.value)}"
        for c in extraction.hard_constraints
        if _request_constraint(c, extraction.furniture, turns) == "unsupported"
    ]
    reasons += [
        f"unsupported furniture: {_plain(i.source.text)}"
        for i in extraction.furniture
        if i.function == "unsupported"
    ]
    return list(dict.fromkeys(reasons))[:4]


def _assistant_text(result, turns=()):
    if result.error:
        return result.error.message
    if result.status == "unsupported":
        reasons = _unsupported_reasons(getattr(result, "extraction", None), turns)
        if reasons:
            return (
                "This request includes something the app cannot do yet:\n"
                + "\n".join(f"- {r}" for r in reasons)
                + "\n\nPlease revise it; no layout has changed."
            )
        return "This request includes unsupported room geometry or mandatory constraints. Please revise it; no layout has changed."
    if result.status == "needs_clarification":
        return "Please clarify:\n" + "\n".join(
            "- " + q for q in result.clarifications[:8]
        )
    return "The room requirements are ready for review. Choose every product, explicitly accept a compatible procedural placeholder, or omit the item. Then Prepare and review before Generate."


def _selection_signature(draft, selections, manual):
    return fingerprint(
        {
            "draft": draft.model_dump(mode="json"),
            "selections": selections,
            "procedural": manual,
            "catalog": [o.model_dump(mode="json") for o in catalog_product_options()],
        }
    )


def _reset_pending_chat():
    # Run before widget construction, leaving consent/control identity stable.
    # Submission remains an explicit per-request action after a reset.
    for key in (
        TURNS,
        RESULT,
        MATCHES,
        REVISION,
        PREPARED,
        SIGNATURE,
        "chat_bedroom_message",
    ):
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if key.startswith(("chat_choice:", "dataset_ref")):
            del st.session_state[key]


def render_bedroom_chat() -> PreparedCatalogSpecification | None:
    st.markdown("#### Chat bedroom — next specification")
    st.caption(
        "One rectangular bedroom. All measurements and selections require review. Pending chat edits never change currently displayed layouts."
    )
    st.caption(
        "Coordinates: southwest origin; X east, Y north. North/south wall offsets start at WEST; east/west offsets start at SOUTH. All furniture yaw is zero."
    )
    st.button(
        "New conversation", key="chat_bedroom_reset", on_click=_reset_pending_chat
    )
    turns = st.session_state.get(TURNS, ())
    for turn in turns:
        with st.chat_message(turn.role):
            st.write(turn.content)
    enabled = os.environ.get("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "0") == "1"
    if not enabled:
        st.info(
            "Live interpretation is disabled by the server. Set ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS=1 and provide server API credentials to use chat; existing input modes remain available."
        )
    st.caption(
        "Submitting sends this conversation to the configured OpenAI model once. No automatic retries. Up to 20 user turns and 12,000 UTF-8 context bytes; no silent truncation. Product/Prepare/Generate controls make no model requests."
    )
    message = st.chat_input(
        "Describe your bedroom or answer the clarification",
        key="chat_bedroom_message",
        disabled=not enabled,
        max_chars=4000,
    )
    if message and enabled:
        st.session_state.pop(PREPARED, None)
        st.session_state.pop(SIGNATURE, None)
        proposed = (
            *turns,
            CatalogChatTurn(
                id=max((t.id for t in turns), default=0) + 1,
                role="user",
                content=message,
            ),
        )
        try:
            validate_turns(proposed)
        except ValueError:
            st.error(
                "Conversation reached its turn/context limit. Start a new conversation; displayed layouts are preserved."
            )
            return None
        with st.spinner("Interpreting requirements…"):
            result = interpret_catalog_conversation(proposed, allow_live=True)
        answer = CatalogChatTurn(
            id=proposed[-1].id + 1,
            role="assistant",
            content=_assistant_text(result, proposed),
        )
        st.session_state[TURNS] = (*proposed, answer)
        st.session_state[RESULT] = result
        st.session_state[REVISION] = st.session_state.get(REVISION, 0) + 1
        st.session_state.pop(MATCHES, None)
        if result.status == "ready":
            try:
                st.session_state[MATCHES] = retrieve_chat_candidates(result.draft)
            except (ValueError, OSError):
                st.error(
                    "The current catalog evidence is unavailable. No specification was prepared."
                )
        with st.chat_message("user"):
            st.write(message)
        with st.chat_message("assistant"):
            st.write(answer.content)
    result = st.session_state.get(RESULT)
    if result is None or result.status != "ready":
        if result is not None and result.status == "unsupported":
            st.warning(
                "Mandatory placement/geometry requirements cannot be silently relaxed. Revise the request explicitly."
            )
        return None
    draft = result.draft
    room = draft.room()
    st.write(
        f"**Next room:** {room.width_m:g} × {room.depth_m:g} × {room.ceiling_height_m:g} m · {len(room.doors)} door(s), {len(room.windows)} window(s)"
    )
    with st.expander("Room measurements, openings and source evidence"):
        st.json(
            {
                "canonical_room": room.model_dump(mode="json"),
                "extraction": draft.extraction.model_dump(mode="json"),
            }
        )
    for text in result.limitations:
        st.caption(text)
    # Optional, default-off dataset references; separate state, no model calls.
    from archimind.ui.dataset_references import render_dataset_references

    render_dataset_references(draft)
    try:
        unavailable = [
            o.record.search.reviewed_name
            for o in catalog_product_options()
            if not o.preparation_available
        ]
    except (ValueError, OSError):
        st.session_state.pop(PREPARED, None)
        st.error("Current catalog qualification evidence is unavailable.")
        return None
    if unavailable:
        st.warning(
            "Required planning evidence is unavailable for: "
            + ", ".join(unavailable)
            + ". Published dimensions cannot replace that evidence."
        )
    if st.button("Refresh catalog choices", key="chat_refresh_catalog"):
        st.session_state.pop(PREPARED, None)
        st.session_state.pop(SIGNATURE, None)
        st.session_state[REVISION] = st.session_state.get(REVISION, 0) + 1
        try:
            st.session_state[MATCHES] = retrieve_chat_candidates(draft)
        except (ValueError, OSError):
            st.session_state.pop(MATCHES, None)
            st.error("Current catalog evidence is unavailable; nothing was prepared.")
    matches = st.session_state.get(MATCHES)
    if matches is None:
        return None
    selections, manual = {}, {}
    all_chosen = True
    for match in matches:
        key = match.request_id
        st.markdown(f"**{key}: {match.intent.function}**")
        try:
            options = resolve_result(match.result)
        except ValueError:
            st.session_state.pop(PREPARED, None)
            st.error(
                "Catalog/evidence changed. Submit your requirements again before preparation."
            )
            return None
        labels = {o.record.asset_id: o.record.search.reviewed_name for o in options}
        for option in options:
            record = option.record
            published = (
                record.dimensions.width_m,
                record.dimensions.depth_m,
                record.dimensions.height_m,
            )
            dims = (
                option.planning_dimensions.wdh
                if option.planning_dimensions
                else published
            )
            st.caption(
                f"{record.search.reviewed_name} · Metadata qualified · Published {published} m W×D×H · Generation {dims} m · Native mesh {'approved' if option.render_qualified else 'unavailable; placeholder'}"
            )
            uses = ", ".join(record.search.usage_tags or ()) or "unrecorded"
            style = (
                ", ".join(v.value for v in record.search.styles or ()) or "unrecorded"
            )
            materials = (
                ", ".join(v.value for v in record.search.materials or ())
                or "unrecorded"
            )
            st.caption(
                f"Why this candidate? Reviewed use: {uses}. Variant: {record.variant_label}. "
                f"Material: {materials}. Style: {style}. Its generation footprint is "
                f"{dims[0]:.2f} × {dims[1]:.2f} m; fit with other items is checked at generation."
            )
            st.markdown(
                f"[Product evidence]({record.source.metadata_url}) · [{record.legal.license_id}]({record.legal.license_url})"
            )
            st.caption(record.legal.attribution)
        templates = procedural_options(match.intent, draft.turns) if not options else ()
        if not options:
            st.info(
                "No eligible real product matches this request. Revise it, explicitly omit it, or accept an available procedural template."
            )
        for f in templates:
            labels["procedural:" + f.id] = (
                f"Procedural {f.name}: {f.width_m:g} × {f.depth_m:g} × {f.height_m:g} m (illustrative, not a real product)"
            )
        choices = ["choose", *labels, "omit"]
        selected = st.selectbox(
            f"Choose {key}",
            choices,
            format_func=lambda v, labels=labels: labels.get(
                v,
                {
                    "choose": "Choose explicitly…",
                    "omit": "Omit this requested item",
                }.get(v, v),
            ),
            key=f"chat_choice:{st.session_state.get(REVISION, 0)}:{key}",
        )
        if selected == "choose":
            all_chosen = False
        elif selected == "omit":
            selections[key] = None
        elif selected.startswith("procedural:"):
            manual[key] = selected.split(":", 1)[1]
        else:
            selections[key] = selected
    try:
        signature = _selection_signature(draft, selections, manual)
    except (ValueError, OSError):
        st.session_state.pop(PREPARED, None)
        st.error("Current qualification evidence is unavailable.")
        return None
    if signature != st.session_state.get(SIGNATURE) or not all_chosen:
        st.session_state.pop(PREPARED, None)
    if st.button(
        "Prepare new specification", key="prepare_chat", disabled=not all_chosen
    ):
        try:
            st.session_state[PREPARED] = prepare_chat_specification(
                draft, selections=selections, procedural_ids=manual
            )
            st.session_state[SIGNATURE] = signature
        except (ValueError, OSError):
            st.session_state.pop(PREPARED, None)
            st.error(
                "The selected specification could not be prepared against current evidence. Review the requests and choices."
            )
    prepared = st.session_state.get(PREPARED)
    if not isinstance(prepared, PreparedCatalogSpecification):
        st.info(
            "Choose every item and Prepare before generating. Selection/evidence changes require preparation again; seed edits do not."
        )
        return None
    st.markdown("#### Review next chat specification")
    design = prepared.design()
    assignments = {a.furniture_id: a for a in prepared.assignments}
    st.dataframe(
        [
            {
                "Item": f.name,
                "Identity": assignments[f.id].product_id
                if f.id in assignments
                else f.id,
                "Dimension basis": assignments[f.id].dimension_basis
                if f.id in assignments
                else "explicit procedural template",
                "W × D × H (m)": (f.width_m, f.depth_m, f.height_m),
            }
            for f in design.furniture
        ],
        hide_index=True,
        width="stretch",
    )
    st.write(
        "Explicitly omitted requests: "
        + (", ".join(k for k, v in selections.items() if v is None) or "none")
    )
    st.caption(
        "Positions start at (0,0) as unvalidated inputs. Only Generate Layouts places and spatially validates them; current layouts remain unchanged until that action returns."
    )
    if not design.furniture:
        st.info(
            "Empty specification reviewed. Only one distinct empty arrangement exists."
        )
    return prepared
