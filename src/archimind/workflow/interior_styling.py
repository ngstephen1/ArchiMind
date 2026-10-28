"""E2 final styling handoff; E1 remains the only provider/catalog implementation."""

import os
from collections.abc import Callable

from archimind.agents import interior_stylist_agent, requirements_agent
from archimind.agents.interior_stylist_grounding import (
    interpret_style_proposal,
    prepare_stylist_context,
)
from archimind.agents.interior_stylist_schemas import (
    InteriorStylistError,
    InteriorStylistRequest,
    InteriorStylistResult,
)
from archimind.geometry import validate_accessibility
from archimind.geometry.layout_generator import _score
from archimind.workflow.layout_recommendation import _approved, advisor_preferences
from archimind.workflow.state import AIStylingState, WorkflowState


def selection_is_safe(state: WorkflowState) -> bool:
    """Current E2 approval gate, shared with selected-layout fixture requests."""
    try:
        selected = state.selected_candidate_index
        if not _approved(state, selected):
            return False
        candidate = state.generation.candidates[selected]
        if (
            state.approved_design != candidate.design
            or candidate.validation.config != state.request.accessibility
        ):
            return False
        actual = validate_accessibility(
            candidate.design.model_copy(deep=True),
            config=state.request.accessibility.model_copy(deep=True),
            area_tolerance_m2=0.0,
        )
        return (
            actual.status == "passed"
            and actual == candidate.validation
            and _score(candidate.design.room, actual) == candidate.score
        )
    except Exception:
        return False


def stylist_policy(state: WorkflowState, *, allow_live: bool) -> AIStylingState:
    """All E2 invocations, including trusted offline fixtures, need explicit consent."""
    metadata = state.ai_styling.model_copy(deep=True)
    if not metadata.requested:
        return metadata
    if os.environ.get("ARCHIMIND_ENABLE_OPENAI_STYLIST", "0") != "1":
        return metadata.model_copy(
            update={"status": "disabled", "reason": "feature_disabled"}
        )
    if allow_live is not True:
        return metadata.model_copy(
            update={"status": "unavailable", "reason": "authorization_required"}
        )
    return metadata.model_copy(update={"status": "pending", "reason": None})


def interior_styling(
    state: WorkflowState,
    *,
    allow_live: bool = False,
    stylist: Callable[..., InteriorStylistResult] | None = None,
) -> dict:
    """Style once, or route to the fixture while a fresh approved selection is safe.

    The trusted injection receives a deep copy. It is not an untrusted-code
    sandbox. Compare all authoritative workflow data before and after invocation;
    fresh deterministic validation and scoring never replace the original reports.
    """
    from archimind.workflow.nodes import stop, transition

    metadata = state.ai_styling.model_copy(deep=True)
    selected = state.selected_candidate_index
    if metadata.executed or any(
        event.node == "ai_interior_stylist" for event in state.trace
    ):
        return stop(
            state,
            "ai_interior_stylist",
            "iteration_limit",
            "AI stylist may execute at most once.",
            ai_styling=metadata.model_copy(
                update={
                    "status": "rejected",
                    "source": None,
                    "reason": "iteration_limit",
                    "result": InteriorStylistResult(
                        status="error",
                        message="Stylist cannot execute again.",
                        error=InteriorStylistError(
                            code="invalid_input",
                            message="Stylist cannot execute again.",
                        ),
                    ),
                }
            ),
        )
    fields = {
        "request",
        "design",
        "generation",
        "reviews",
        "selected_candidate_index",
        "selection_source",
        "approved_design",
        "layout_recommendation",
        "spatial_critique",
    }
    before = state.model_dump(include=fields)

    def safe_selection():
        return state.model_dump(include=fields) == before and selection_is_safe(state)

    def failure(code, *, status="error"):
        return InteriorStylistResult(
            status=status,
            message=f"AI stylist returned {code}.",
            error=InteriorStylistError(
                code=code, message=f"AI stylist returned {code}."
            ),
        )

    def unsafe(executed):
        return stop(
            state,
            "ai_interior_stylist",
            "no_approved_candidates",
            "Selected layout failed fresh verification or changed during styling; no design approved.",
            status="rejected",
            ai_styling=metadata.model_copy(
                update={
                    "status": "rejected",
                    "executed": executed,
                    "source": None,
                    "reason": "unsafe_selection",
                    "result": failure("invalid_layout"),
                }
            ),
        )

    if not safe_selection():
        return unsafe(False)

    def finish(status, reason, *, executed, result=None):
        if not safe_selection():
            return unsafe(executed)
        source = "ai" if status == "styled" else None
        updated = metadata.model_copy(
            update={
                "status": status,
                "reason": reason,
                "executed": executed,
                "candidate_index": selected,
                "result": result,
                "source": source,
            },
            deep=True,
        )
        mode = result.mode if result is not None else "not_evaluated"
        return transition(
            state,
            "ai_interior_stylist",
            "styled" if source == "ai" else "fallback",
            f"AI styling requested; executed={executed}; status={status}; mode={mode}; reason={reason}; "
            f"selected source candidate {selected} unchanged; selection source {state.selection_source}; "
            + (
                "style source ai; metadata only."
                if source == "ai"
                else "routing to deterministic_fixture styling; no AI plan applied."
            ),
            status="succeeded" if source == "ai" else "running",
            ai_styling=updated,
        )

    policy = stylist_policy(state, allow_live=allow_live)
    if policy.status != "pending":
        return finish(policy.status, policy.reason, executed=False)
    try:
        style_request = state.request.style_request
        if (
            style_request is None
            and state.interpretation is not None
            and state.interpretation.extraction is not None
        ):
            preference = state.interpretation.extraction.style
            style_request = preference.text if preference is not None else None
        request = InteriorStylistRequest(
            candidate=state.generation.candidates[selected].model_copy(deep=True),
            style_request=style_request,
            soft_preferences=advisor_preferences(state),
            critique=state.spatial_critique.result
            if state.spatial_critique.status in ("evaluated", "abstained")
            else None,
        )
        context = prepare_stylist_context(request)
    except Exception:
        return finish(
            "rejected", "invalid_input", executed=False, result=failure("invalid_input")
        )
    try:
        result = (stylist or interior_stylist_agent.recommend_style)(
            request.model_copy(deep=True), allow_live_usage=allow_live
        )
    except Exception:
        return finish(
            "error", "stylist_exception", executed=True, result=failure("api_error")
        )
    try:
        result = InteriorStylistResult.model_validate(result)
        if result.status in ("error", "unavailable"):
            return finish(
                result.status,
                result.error.code,
                executed=True,
                result=failure(result.error.code, status=result.status),
            )
        if result.context != context:
            raise ValueError(
                "Style context differs from the selected candidate/preferences"
            )
        if result.mode == "offline_fixture":
            if stylist is None or result.model is not None:
                raise ValueError("Offline output requires an explicit trusted fixture")
        elif result.mode == "api_response":
            model = os.environ.get(
                "ARCHIMIND_OPENAI_MODEL", requirements_agent.DEFAULT_MODEL
            )
            if (
                allow_live is not True
                or result.model != model
                or model not in requirements_agent.SUPPORTED_MODELS
            ):
                raise ValueError("API output needs matching authorization/model")
        elif not (
            result.status == "needs_clarification"
            and request.style_request is None
            and result.proposal is None
            and result.model is None
        ):
            raise ValueError("Styling requires explicit provenance")
        if result.proposal is None:
            checked = InteriorStylistResult(
                status="needs_clarification",
                context=context,
                message="Provide a stated style request before requesting a style plan.",
                clarification_reasons=["missing_style_details"],
            )
        else:
            checked = interpret_style_proposal(
                context, result.proposal, mode=result.mode, model=result.model
            )
        if checked != result:
            raise ValueError("Style plan differs from canonical E1 grounding")
    except Exception:
        return finish(
            "rejected", "invalid_style", executed=True, result=failure("invalid_style")
        )
    return finish(
        checked.status,
        "stylist_clarification" if checked.status == "needs_clarification" else None,
        executed=True,
        result=checked,
    )
