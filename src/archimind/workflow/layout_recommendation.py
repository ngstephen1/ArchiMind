"""C2 handoff/provenance checks around the existing C1 adapter and grounding."""

import os
from collections.abc import Callable

from archimind.agents import layout_agent, requirements_agent
from archimind.agents.layout_grounding import (
    interpret_layout_proposal,
    prepare_layout_context,
)
from archimind.agents.layout_schemas import (
    LayoutAdviceError,
    LayoutAdviceRequest,
    LayoutAdviceResult,
)
from archimind.geometry import LayoutGenerationResult
from archimind.workflow.state import LayoutRecommendationState, WorkflowState


def advisor_preferences(state: WorkflowState) -> list[str]:
    if state.request.soft_preferences:
        return list(state.request.soft_preferences)
    if state.interpretation is not None and state.interpretation.extraction is not None:
        return [
            preference.text
            for preference in state.interpretation.extraction.soft_preferences
        ]
    return []


def advisor_policy(state: WorkflowState) -> LayoutRecommendationState:
    metadata = state.layout_recommendation.model_copy(deep=True)
    if not metadata.requested:
        return metadata.model_copy(update={"status": "not_requested"})
    if os.environ.get("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "0") != "1":
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


def _approved(state: WorkflowState, index: int | None) -> bool:
    from archimind.workflow.nodes import _preserves_specification

    if (
        state.generation is None
        or state.design is None
        or index is None
        or not 0 <= index < len(state.generation.candidates)
    ):
        return False
    candidate = state.generation.candidates[index]
    review = next(
        (item for item in state.reviews if item.candidate_index == index), None
    )
    return bool(
        review is not None
        and review.accepted
        and review.report.status == "passed"
        and review.report == candidate.validation
        and _preserves_specification(state.design, candidate.design)
    )


def _advisory_request(state: WorkflowState) -> tuple[LayoutAdviceRequest, list[int]]:
    """A derived approved-only view; original generation/results are never edited.

    When filtering removes a rejected source candidate, the local C1 packet's
    count/status describes this complete advisory subset. Its explicit index map
    retains source identity; source search metadata stays intact in workflow state.
    """
    indices = [
        index
        for index in range(len(state.generation.candidates))
        if _approved(state, index)
    ]
    if not indices:
        raise ValueError("No approved advisor candidates")
    source = state.generation
    if indices == list(range(len(source.candidates))):
        generation = source.model_copy(deep=True)
    else:
        generation = LayoutGenerationResult.model_validate(
            {
                **dict(source),
                "status": "complete",
                "requested_candidates": len(indices),
                "candidates": [
                    source.candidates[index].model_copy(deep=True) for index in indices
                ],
            }
        )
    return LayoutAdviceRequest(
        specification=state.design.model_copy(deep=True),
        generation=generation,
        soft_preferences=advisor_preferences(state),
    ), indices


def layout_recommendation(
    state: WorkflowState,
    *,
    allow_live: bool = False,
    advisor: Callable[..., LayoutAdviceResult] | None = None,
) -> dict:
    """One checked recommendation or an explicit, independently approved fallback."""
    from archimind.workflow.nodes import stop, transition

    metadata = state.layout_recommendation.model_copy(deep=True)
    original = metadata.deterministic_candidate_index
    if metadata.executed or any(item.node == "layout_advisor" for item in state.trace):
        return stop(
            state,
            "layout_advisor",
            "iteration_limit",
            "Layout advisor may execute at most once.",
        )
    if not _approved(state, original):
        return stop(
            state,
            "layout_advisor",
            "no_approved_candidates",
            "No independently approved deterministic fallback remains safe.",
            status="rejected",
        )

    def fallback(
        status: str,
        reason: str,
        *,
        executed: bool,
        advice=None,
        indices=None,
        proposed=None,
    ):
        if not _approved(state, original):
            return stop(
                state,
                "layout_advisor",
                "no_approved_candidates",
                "The deterministic fallback no longer matches its authoritative critique.",
                status="rejected",
            )
        updated = metadata.model_copy(
            update={
                "status": status,
                "executed": executed,
                "reason": reason,
                "advice": advice,
                "candidate_indices": indices or [],
                "proposed_candidate_index": proposed,
            },
            deep=True,
        )
        return transition(
            state,
            "layout_advisor",
            "fallback",
            f"Advisor {status}; executed={executed}; reason={reason}; proposed source index={proposed}; "
            f"retained deterministic candidate {original}; final source deterministic.",
            layout_recommendation=updated,
            selected_candidate_index=original,
            approved_design=state.generation.candidates[original].design.model_copy(
                deep=True
            ),
            selection_source="deterministic",
        )

    policy = advisor_policy(state)
    if policy.status != "pending":
        return fallback(policy.status, policy.reason or "not_requested", executed=False)
    try:
        request, indices = _advisory_request(state)
        expected_context = prepare_layout_context(request)
    except Exception:
        return fallback("rejected", "invalid_advisor_input", executed=False)
    try:
        result = (advisor or layout_agent.recommend_layout)(
            request.model_copy(deep=True), allow_live=allow_live
        )
    except Exception:
        return fallback("error", "advisor_exception", executed=True, indices=indices)
    proposed = None
    try:
        result = LayoutAdviceResult.model_validate(result)
        if result.proposal is not None and result.proposal.candidate_index is not None:
            local = result.proposal.candidate_index
            if local < len(indices):
                proposed = indices[local]
        if result.status in ("error", "unavailable"):
            code = result.error.code
            # Preserve actual status/code, never raw provider/DI messages or context.
            safe_error = LayoutAdviceResult(
                status=result.status,
                rationale=f"Layout advisor returned {code}.",
                error=LayoutAdviceError(
                    code=code, message=f"Layout advisor returned {code}."
                ),
            )
            return fallback(
                result.status, code, executed=True, advice=safe_error, indices=indices
            )
        if (
            result.status not in ("recommended", "abstained")
            or result.context != expected_context
        ):
            raise ValueError("Advisor context does not match approved source data")
        if result.mode == "offline_fixture":
            if result.model is not None or advisor is None:
                raise ValueError("Offline fixture requires explicit trusted injection")
        elif result.mode == "api_response":
            expected_model = os.environ.get(
                "ARCHIMIND_OPENAI_MODEL", requirements_agent.DEFAULT_MODEL
            )
            if (
                allow_live is not True
                or result.model != expected_model
                or expected_model not in requirements_agent.SUPPORTED_MODELS
            ):
                raise ValueError(
                    "API recommendation has no matching live authorization/model"
                )
        else:
            raise ValueError("A successful recommendation needs explicit provenance")
        # Reuse C1's own grounding/rendering; reject altered evidence/rationale/reports.
        checked = interpret_layout_proposal(
            expected_context, result.proposal, mode=result.mode, model=result.model
        )
        if checked != result:
            raise ValueError(
                "Recommendation is inconsistent with canonical grounded output"
            )
        if checked.status == "abstained":
            return fallback(
                "abstained",
                "advisor_abstained",
                executed=True,
                advice=checked,
                indices=indices,
            )
        if not _approved(state, proposed):
            raise ValueError("Proposed source candidate is not critic-approved")
    except Exception:
        return fallback(
            "rejected",
            "invalid_recommendation",
            executed=True,
            indices=indices,
            proposed=proposed,
        )

    updated = metadata.model_copy(
        update={
            "status": "recommended",
            "executed": True,
            "reason": None,
            "candidate_indices": indices,
            "proposed_candidate_index": proposed,
            "advice": checked,
        },
        deep=True,
    )
    return transition(
        state,
        "layout_advisor",
        "recommended",
        f"Advisor executed via {checked.mode}; local index {checked.proposal.candidate_index} "
        f"maps to approved source candidate {proposed}; recommendation accepted; "
        f"rationale={checked.proposal.rationale_code}; final source ai_recommendation.",
        layout_recommendation=updated,
        selected_candidate_index=proposed,
        approved_design=state.generation.candidates[proposed].design.model_copy(
            deep=True
        ),
        selection_source="ai_recommendation",
    )
