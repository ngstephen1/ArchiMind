"""Optional, button-driven appearance metadata for the stored layout selection."""

import hashlib
import json
import os

import streamlit as st

from archimind.agents.interior_stylist_catalog import (
    ACCENTS,
    MATERIALS,
    PALETTES,
    THEMES,
)
from archimind.agents.interior_stylist_schemas import InteriorStylistResult
from archimind.geometry import LayoutGenerationResult
from archimind.models import RoomDesign
from archimind.workflow import DesignRequest, WorkflowState, style_selected_layout

RESULT_KEY = "interior_styling_result"
ERROR_KEY = "interior_styling_error"
LAYOUT_KEY = "interior_styling_layout"
CONTEXT_KEY = "interior_styling_context"
PENDING_KEY = "interior_styling_pending"
INFLIGHT_KEY = "interior_styling_inflight"
ENABLE_KEY = "interior_styling_enabled"
THEME_KEY = "interior_styling_theme"
PREFERENCE_KEY = "interior_styling_preferences"
CONSENT_KEY = "interior_styling_consent"
PREVIEW_KEY = "interior_styling_color_preview"


def _clear_request() -> None:
    """Widget callbacks run before rendering, so consent can be cleared safely."""
    for key in (RESULT_KEY, ERROR_KEY, PENDING_KEY):
        st.session_state.pop(key, None)
    st.session_state[CONSENT_KEY] = False
    st.session_state[PREVIEW_KEY] = False


def reset_styling() -> None:
    """Invalidate a replaced generation; leave layout state and in-flight guard alone."""
    _clear_request()
    st.session_state.pop(LAYOUT_KEY, None)
    st.session_state.pop(CONTEXT_KEY, None)


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _layout_binding(specification, generation, index) -> str:
    return _digest(
        [
            specification.model_dump(mode="json"),
            generation.model_dump(mode="json"),
            index,
        ]
    )


def _queue(context: str, ai: bool) -> None:
    """Consume one explicit click/authorization before any adapter can execute."""
    if st.session_state.get(INFLIGHT_KEY):
        return
    consent = st.session_state.get(CONSENT_KEY) is True
    st.session_state[CONSENT_KEY] = False
    st.session_state[PREVIEW_KEY] = False
    st.session_state.pop(ERROR_KEY, None)
    if ai and (
        st.session_state.get(ENABLE_KEY) is not True
        or not consent
        or os.environ.get("ARCHIMIND_ENABLE_OPENAI_STYLIST", "0") != "1"
    ):
        st.session_state[ERROR_KEY] = (
            "AI styling requires enablement and authorization for this request."
        )
        return
    st.session_state.pop(RESULT_KEY, None)
    st.session_state[PENDING_KEY] = (context, ai, consent if ai else False)


def _show_result(result: WorkflowState, label: str) -> None:
    metadata = result.ai_styling
    if result.status != "succeeded":
        st.error(
            "Styling was not approved for this layout. Generate a valid layout before trying again."
        )
        return
    st.markdown(f"#### Styling for {label}")
    st.caption(
        f"Selected layout unchanged · Original score {result.generation.candidates[result.selected_candidate_index].score.total:.6f} · Seed {result.generation.seed}"
    )
    if metadata.source == "deterministic_fixture":
        if metadata.requested:
            st.warning(
                "Deterministic fixture fallback — AI styling did not produce an accepted plan."
            )
            st.caption(f"AI outcome: {metadata.status} · Reason: {metadata.reason}")
            if metadata.result is not None:
                st.write(metadata.result.message)
        else:
            st.success("Deterministic fixture — AI was not requested.")
        st.write("Fixture palette: " + ", ".join(result.styling.palette))
        for note in result.styling.material_notes:
            st.caption(note)
        st.caption("Execution mode: not_evaluated · Source: deterministic_fixture")
        return
    advice = metadata.result
    plan = advice.plan
    st.success(
        "Mocked AI stylist — offline fixture"
        if advice.mode == "offline_fixture"
        else "AI stylist — API response"
    )
    st.caption(f"Execution mode: {advice.mode} · Source: ai")
    st.write(
        f"Theme: {THEMES[plan.theme_id].label} · Palette: {PALETTES[plan.palette_id].label}"
    )
    st.write(f"Walls: {plan.wall_finish.label} ({plan.wall_finish.base_color_hex})")
    st.write(f"Floor: {plan.floor_finish.label} ({plan.floor_finish.base_color_hex})")
    st.dataframe(
        [
            {
                "Furniture ID": identifier,
                "Finish appearance": finish.label,
                "Catalog color": finish.base_color_hex,
            }
            for identifier, finish in plan.furniture_finishes.items()
        ],
        hide_index=True,
        width="stretch",
        key="interior_style_finishes",
    )
    if plan.accents:
        st.write(
            "Accents: "
            + ", ".join(
                f"{accent.label} ({accent.color_hex})" for accent in plan.accents
            )
        )
    st.write(plan.explanation)
    with st.expander("Preferences and limitations"):
        for note in plan.preference_notes:
            st.write(note.explanation)
        for text in [*plan.conflicts, *plan.assumptions, *plan.limitations]:
            st.caption(text)


def render_interior_styling(
    specification: RoomDesign,
    generation: LayoutGenerationResult,
    selected_candidate_index: int,
) -> InteriorStylistResult | None:
    """No validation, generation or model invocation happens without a button click."""
    layout = _layout_binding(specification, generation, selected_candidate_index)
    if st.session_state.get(LAYOUT_KEY) != layout:
        reset_styling()
        st.session_state[LAYOUT_KEY] = layout
    label = f"Layout {'AB'[selected_candidate_index]}"
    st.markdown("### Interior Styling — Optional")
    st.caption(
        f"{label} · "
        + (
            "Flat catalog colors are previewed in the selected Plotly 3D view. No textures or physical materials are applied."
            if st.session_state.get(PREVIEW_KEY)
            else "Appearance suggestions only. Materials are not applied to the 2D or 3D views."
        )
    )
    ai = st.checkbox(
        "Enable AI-assisted styling", key=ENABLE_KEY, on_change=_clear_request
    )
    theme = "neutral"
    preferences = ""
    available = os.environ.get("ARCHIMIND_ENABLE_OPENAI_STYLIST", "0") == "1"
    if ai:
        theme_ids = list(THEMES)
        theme = st.selectbox(
            "Style theme",
            theme_ids,
            index=theme_ids.index("neutral"),
            format_func=lambda identifier: THEMES[identifier].label,
            key=THEME_KEY,
            on_change=_clear_request,
        )
        palette = PALETTES[THEMES[theme].palette_ids[0]]
        st.write(f"Catalog palette preview: {palette.label}")
        st.caption(
            "Walls: "
            + ", ".join(
                MATERIALS[identifier].label for identifier in palette.wall_material_ids
            )
        )
        st.caption(
            "Accents: "
            + ", ".join(ACCENTS[identifier].label for identifier in palette.accent_ids)
        )
        preferences = st.text_area(
            "Optional style preferences",
            max_chars=400,
            height=90,
            key=PREFERENCE_KEY,
            on_change=_clear_request,
            help="Appearance preferences, not guarantees of safety, performance or exact materials.",
        )
        if not available:
            st.info(
                "AI styling is not enabled for this deployment. Fixture styling remains available."
            )
            st.session_state[CONSENT_KEY] = False
    context = _digest([layout, ai, theme, preferences])
    st.session_state[CONTEXT_KEY] = context
    stored = st.session_state.get(RESULT_KEY)
    if stored is not None and stored[0] != context:
        st.session_state.pop(RESULT_KEY, None)
        st.session_state[CONSENT_KEY] = False
    if ai:
        consent = st.checkbox(
            "Authorize one OpenAI request",
            key=CONSENT_KEY,
            disabled=not available,
            help="Required again for every attempt. A request may incur API usage; no key is entered or displayed here.",
        )
        st.button(
            "Request AI styling",
            key="request_ai_styling",
            disabled=not available
            or not consent
            or bool(st.session_state.get(INFLIGHT_KEY)),
            on_click=_queue,
            args=(context, True),
        )
    else:
        st.caption(
            "The neutral fixture uses existing deterministic metadata and needs no API key."
        )
    st.button(
        "Show fixture styling",
        key="show_fixture_styling",
        disabled=bool(st.session_state.get(INFLIGHT_KEY)),
        on_click=_queue,
        args=(context, False),
    )

    pending = st.session_state.pop(PENDING_KEY, None)
    if (
        pending is not None
        and pending[0] == context
        and not st.session_state.get(INFLIGHT_KEY)
    ):
        st.session_state[INFLIGHT_KEY] = True
        try:
            request = DesignRequest(
                specification=specification,
                seed=generation.seed,
                max_candidates=generation.requested_candidates,
                accessibility=generation.config,
                style_request=f"{THEMES[theme].label} interior."
                if pending[1]
                else None,
                soft_preferences=[preferences.strip()]
                if pending[1] and preferences.strip()
                else [],
            )
            with st.spinner("Checking the selected layout and preparing styling…"):
                outcome = style_selected_layout(
                    request,
                    generation,
                    selected_candidate_index,
                    use_ai_stylist=pending[1],
                    allow_live_stylist=pending[2],
                )
            outcome = WorkflowState.model_validate(outcome)
            if outcome.generation != generation or (
                outcome.status == "succeeded"
                and outcome.selected_candidate_index != selected_candidate_index
            ):
                raise ValueError("Styling changed the selected source data")
            if (
                st.session_state.get(CONTEXT_KEY) == context
                and _layout_binding(specification, generation, selected_candidate_index)
                == layout
            ):
                st.session_state[RESULT_KEY] = (context, outcome)
        except Exception:
            st.session_state[ERROR_KEY] = (
                "Could not prepare styling. Your layout is unchanged; please try again."
            )
        finally:
            st.session_state[INFLIGHT_KEY] = False
    if st.session_state.get(ERROR_KEY):
        st.error(st.session_state[ERROR_KEY])
    stored = st.session_state.get(RESULT_KEY)
    if stored is not None and stored[0] == context:
        _show_result(stored[1], label)
        result = stored[1]
        if result.status == "succeeded" and result.ai_styling.source == "ai":
            if st.checkbox(
                "Preview catalog colors in selected 3D view",
                key=PREVIEW_KEY,
                help="Changes colors only. One finish per furniture object; accents remain metadata. No model call or layout generation.",
            ):
                return result.ai_styling.result
    elif not st.session_state.get(ERROR_KEY):
        st.info(
            f"No styling requested for {label}. Choose the fixture or explicitly enable AI styling."
        )
