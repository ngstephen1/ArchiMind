"""Style an existing caller-selected layout; never execute layout generation."""

from collections.abc import Callable
from functools import partial

from langsmith import tracing_context

from archimind.agents.interior_stylist_schemas import (
    InteriorStylistError,
    InteriorStylistResult,
)
from archimind.geometry import LayoutGenerationResult
from archimind.workflow import nodes
from archimind.workflow.graph import _guard
from archimind.workflow.interior_styling import (
    interior_styling,
    selection_is_safe,
    stylist_policy,
)
from archimind.workflow.state import AIStylingState, DesignRequest, WorkflowState


def _fixture(state: WorkflowState) -> dict:
    def unsafe():
        metadata = state.ai_styling.model_copy(
            update={
                "status": "rejected" if state.ai_styling.requested else "not_requested",
                "source": None,
                "reason": "unsafe_selection",
                "result": InteriorStylistResult(
                    status="error",
                    message="Selected layout failed fresh verification.",
                    error=InteriorStylistError(
                        code="invalid_layout",
                        message="Selected layout failed fresh verification.",
                    ),
                )
                if state.ai_styling.requested
                else None,
            }
        )
        return nodes.stop(
            state,
            "interior_stylist",
            "no_approved_candidates",
            "Selected layout failed fresh verification; no styling approved.",
            status="rejected",
            ai_styling=metadata,
        )

    if not selection_is_safe(state):
        return unsafe()
    before = state.model_dump(
        exclude={"trace", "stage", "status", "styling", "ai_styling"}
    )
    updates = nodes.interior_stylist(state)
    checked = WorkflowState.model_validate({**dict(state), **updates})
    if checked.model_dump(
        exclude={"trace", "stage", "status", "styling", "ai_styling"}
    ) != before or not selection_is_safe(checked):
        return unsafe()
    return updates


def style_selected_layout(
    request: DesignRequest,
    generation: LayoutGenerationResult,
    selected_candidate_index: int,
    *,
    use_ai_stylist: bool = False,
    allow_live_stylist: bool = False,
    interior_stylist: Callable[..., InteriorStylistResult] | None = None,
) -> WorkflowState:
    """Verify and style a stored selection with E2's gates and checked fallback.

    This is a fresh styling attempt, not a rerun of the four-role workflow.
    Original indices, complete generation metadata and reports are retained.
    Iteration count stays zero: no generator or other AI role runs here.
    """
    if type(use_ai_stylist) is not bool or type(allow_live_stylist) is not bool:
        raise ValueError("Workflow modes and authorization must be boolean")
    if type(selected_candidate_index) is not int:
        raise ValueError("Selected candidate index must be an integer")
    request = DesignRequest.model_validate(request).model_copy(deep=True)
    generation = LayoutGenerationResult.model_validate(generation).model_copy(deep=True)
    initial = WorkflowState(
        request=request,
        design=request.specification,
        generation=generation,
        ai_styling=AIStylingState(
            requested=use_ai_stylist,
            status="pending" if use_ai_stylist else "not_requested",
        ),
    )
    initial.ai_styling = stylist_policy(initial, allow_live=allow_live_stylist)
    if request.specification is None:
        return WorkflowState.model_validate(
            {
                **dict(initial),
                **nodes.stop(
                    initial,
                    "spatial_critic",
                    "missing_specification",
                    "Styling requires the original room specification.",
                ),
            }
        )
    # Invalid indices must not turn into the default first-approved selection.
    if not 0 <= selected_candidate_index < len(generation.candidates):
        return WorkflowState.model_validate(
            {
                **dict(initial),
                **nodes.stop(
                    initial,
                    "spatial_critic",
                    "no_approved_candidates",
                    "Selected candidate is unavailable.",
                    status="rejected",
                ),
            }
        )
    with tracing_context(enabled=False):
        state = WorkflowState.model_validate(
            _guard(
                "spatial_critic",
                partial(
                    nodes.spatial_critic,
                    selected_candidate_index=selected_candidate_index,
                ),
            )(initial)
        )
        if state.status != "running":
            return state
        if state.ai_styling.status == "pending":
            state = WorkflowState.model_validate(
                _guard(
                    "ai_interior_stylist",
                    partial(
                        interior_styling,
                        allow_live=allow_live_stylist,
                        stylist=interior_stylist,
                    ),
                )(state)
            )
        if state.status == "running":
            state = WorkflowState.model_validate(
                _guard("interior_stylist", _fixture)(state)
            )
    return state
