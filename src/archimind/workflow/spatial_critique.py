"""D2 read-only handoff to the existing D1 critic; no selection authority."""

import os
from collections.abc import Callable

from archimind.agents import requirements_agent, spatial_critic_agent
from archimind.agents.spatial_critic_grounding import (
    interpret_critic_proposal,
    prepare_critic_context,
)
from archimind.agents.spatial_critic_schemas import (
    SpatialCriticError,
    SpatialCriticRequest,
    SpatialCriticResult,
)
from archimind.geometry import validate_accessibility
from archimind.workflow.layout_recommendation import (
    _advisory_request,
    _approved,
    advisor_preferences,
)
from archimind.workflow.state import SpatialCritiqueState, WorkflowState


def critic_policy(state: WorkflowState) -> SpatialCritiqueState:
    metadata = state.spatial_critique.model_copy(deep=True)
    if not metadata.requested:
        return metadata.model_copy(update={"status": "not_requested"})
    if os.environ.get("ARCHIMIND_ENABLE_OPENAI_CRITIC", "0") != "1":
        return metadata.model_copy(
            update={"status": "disabled", "reason": "feature_disabled"}
        )
    preferences = advisor_preferences(state)
    if not preferences or len(preferences) > 8:
        return metadata.model_copy(
            update={
                "status": "skipped",
                "reason": "no_preferences"
                if not preferences
                else "too_many_preferences",
            }
        )
    return metadata.model_copy(update={"status": "pending", "reason": None})


def spatial_critique(
    state: WorkflowState,
    *,
    allow_live: bool = False,
    critic: Callable[..., SpatialCriticResult] | None = None,
) -> dict:
    """Review the already selected candidate exactly once; retain it on any outcome."""
    from archimind.workflow.nodes import stop, transition

    metadata = state.spatial_critique.model_copy(deep=True)
    selected = state.selected_candidate_index
    if metadata.executed or any(
        event.node == "ai_spatial_critic" for event in state.trace
    ):
        return stop(
            state,
            "ai_spatial_critic",
            "iteration_limit",
            "AI spatial critic may execute at most once.",
        )

    def safe_selection():
        if not (
            _approved(state, selected)
            and state.approved_design == state.generation.candidates[selected].design
        ):
            return False
        try:
            actual = validate_accessibility(
                state.approved_design.model_copy(deep=True),
                config=state.request.accessibility.model_copy(deep=True),
                area_tolerance_m2=0.0,
            )
            return (
                actual.status == "passed"
                and actual == state.generation.candidates[selected].validation
            )
        except Exception:
            return False

    if not safe_selection():
        return stop(
            state,
            "ai_spatial_critic",
            "no_approved_candidates",
            "No authoritative deterministic selection remains safe for critique.",
            status="rejected",
        )

    def finish(status, reason, *, executed, result=None, indices=None):
        if not safe_selection():
            unsafe = SpatialCriticResult(
                status="error",
                assessment="Selected layout failed fresh deterministic verification.",
                error=SpatialCriticError(
                    code="invalid_candidates",
                    message="Selected layout failed fresh deterministic verification.",
                ),
            )
            return stop(
                state,
                "ai_spatial_critic",
                "no_approved_candidates",
                "The selected candidate no longer matches its authoritative critique.",
                status="rejected",
                spatial_critique=metadata.model_copy(
                    update={
                        "status": "rejected",
                        "executed": executed,
                        "candidate_index": selected,
                        "candidate_indices": indices or [],
                        "result": unsafe,
                        "reason": "unsafe_selection",
                    },
                    deep=True,
                ),
            )
        updated = metadata.model_copy(
            update={
                "status": status,
                "reason": reason,
                "executed": executed,
                "candidate_index": selected,
                "candidate_indices": indices or [],
                "result": result,
            },
            deep=True,
        )
        outcome = (
            result.proposal.decision
            if result is not None and result.proposal is not None
            else reason
        )
        stance = (
            result.recommendation_stance
            if result is not None and result.proposal is not None
            else "not_evaluated"
        )
        mode = result.mode if result is not None else "not_evaluated"
        return transition(
            state,
            "ai_spatial_critic",
            "reviewed" if status in ("evaluated", "abstained") else "fallback",
            f"AI critic requested; executed={executed}; status={status}; mode={mode}; "
            f"outcome={outcome}; stance={stance}; target source candidate {selected}; "
            f"selection unchanged at {selected}; final source {state.selection_source}. "
            "Advisory feedback only; deterministic spatial approval remains authoritative.",
            spatial_critique=updated,
        )

    policy = critic_policy(state)
    if policy.status != "pending":
        return finish(policy.status, policy.reason or "not_requested", executed=False)
    try:
        layout, indices = _advisory_request(state)
        local_target = indices.index(selected)
        advice = (
            state.layout_recommendation.advice
            if state.layout_recommendation.status == "recommended"
            else None
        )
        if advice is not None and (
            state.selection_source != "ai_recommendation"
            or state.layout_recommendation.proposed_candidate_index != selected
            or state.layout_recommendation.candidate_indices != indices
        ):
            raise ValueError("Accepted recommendation and selection disagree")
        constraints = []
        if (
            state.interpretation is not None
            and state.interpretation.extraction is not None
        ):
            constraints = [
                item.text for item in state.interpretation.extraction.hard_constraints
            ]
        request = SpatialCriticRequest(
            layout=layout,
            layout_recommendation=advice,
            explicit_constraints=constraints,
            reviewed_candidate_index=local_target,
        )
        context = prepare_critic_context(request)
    except Exception:
        error = SpatialCriticResult(
            status="error",
            assessment="Critic input does not match approved workflow data.",
            error=SpatialCriticError(
                code="invalid_input",
                message="Critic input does not match approved workflow data.",
            ),
        )
        return finish("rejected", "invalid_input", executed=False, result=error)
    try:
        result = (critic or spatial_critic_agent.critique_design)(
            request.model_copy(deep=True),
            allow_live_usage=allow_live,
        )
    except Exception:
        error = SpatialCriticResult(
            status="error",
            assessment="Critic invocation failed; selected layout retained.",
            error=SpatialCriticError(
                code="api_error",
                message="Critic invocation failed; selected layout retained.",
            ),
        )
        return finish(
            "error", "critic_exception", executed=True, result=error, indices=indices
        )
    try:
        result = SpatialCriticResult.model_validate(result)
        if result.status in ("error", "unavailable"):
            code = result.error.code
            sanitized = SpatialCriticResult(
                status=result.status,
                assessment=f"AI critic returned {code}.",
                error=SpatialCriticError(
                    code=code, message=f"AI critic returned {code}."
                ),
            )
            return finish(
                result.status, code, executed=True, result=sanitized, indices=indices
            )
        if result.status not in ("evaluated", "abstained") or result.context != context:
            raise ValueError("Critique context differs from approved target packet")
        if result.mode == "offline_fixture":
            if critic is None or result.model is not None:
                raise ValueError("Offline result requires explicit trusted injection")
        elif result.mode == "api_response":
            model = os.environ.get(
                "ARCHIMIND_OPENAI_MODEL", requirements_agent.DEFAULT_MODEL
            )
            if (
                allow_live is not True
                or result.model != model
                or model not in requirements_agent.SUPPORTED_MODELS
            ):
                raise ValueError("API result lacks matching authorization/model")
        else:
            raise ValueError("Critique requires explicit execution provenance")
        checked = interpret_critic_proposal(
            context, result.proposal, mode=result.mode, model=result.model
        )
        if checked != result:
            raise ValueError("Critique differs from canonical D1 grounding")
    except Exception:
        error = SpatialCriticResult(
            status="error",
            assessment="Critique did not match authoritative workflow evidence.",
            error=SpatialCriticError(
                code="invalid_evidence",
                message="Critique did not match authoritative workflow evidence.",
            ),
        )
        return finish(
            "rejected", "invalid_evidence", executed=True, result=error, indices=indices
        )
    return finish(
        checked.status,
        "critic_abstained" if checked.status == "abstained" else None,
        executed=True,
        result=checked,
        indices=indices,
    )
