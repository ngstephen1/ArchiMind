"""Optional requirements interpretation; three unchanged deterministic roles."""

from collections.abc import Callable

from archimind.agents.requirements_agent import interpret_requirements
from archimind.agents.requirements_conversion import prepare_requirements
from archimind.agents.requirements_schemas import RequirementsResult
from archimind.geometry import (
    AccessibilityValidationReport,
    LayoutGenerationResult,
    generate_layout_candidates,
    validate_accessibility,
)
from archimind.models import RoomDesign
from archimind.workflow.layout_recommendation import advisor_policy
from archimind.workflow.spatial_critique import critic_policy
from archimind.workflow.state import (
    MAX_WORKFLOW_ITERATIONS,
    AgentActivity,
    CandidateReview,
    ExecutionStatus,
    NodeName,
    StylingMetadata,
    WorkflowError,
    WorkflowState,
)


def transition(
    state: WorkflowState,
    node: NodeName,
    decision: str,
    message: str,
    *,
    status: ExecutionStatus = "running",
    **updates: object,
) -> dict:
    """Return replacement channel values; never append to a caller's lists."""
    return {
        **updates,
        "stage": "complete" if status == "succeeded" else node,
        "status": status,
        "trace": [
            *state.trace,
            AgentActivity(
                sequence=len(state.trace) + 1,
                node=node,
                decision=decision,
                message=message,
            ),
        ],
    }


def stop(
    state: WorkflowState,
    node: NodeName,
    code: str,
    message: str,
    *,
    status: ExecutionStatus = "failed",
    **updates: object,
) -> dict:
    if state.ai_styling.requested and state.ai_styling.status == "pending":
        updates.setdefault(
            "ai_styling",
            state.ai_styling.model_copy(
                update={
                    "status": "skipped",
                    "reason": "workflow_terminated_before_stylist",
                }
            ),
        )
    if state.spatial_critique.requested and state.spatial_critique.status == "pending":
        updates.setdefault(
            "spatial_critique",
            state.spatial_critique.model_copy(
                update={
                    "status": "skipped",
                    "reason": "workflow_terminated_before_critic",
                }
            ),
        )
    if (
        state.layout_recommendation.requested
        and state.layout_recommendation.status == "pending"
    ):
        updates.setdefault(
            "layout_recommendation",
            state.layout_recommendation.model_copy(
                update={
                    "status": "skipped",
                    "reason": "workflow_terminated_before_advisor",
                }
            ),
        )
    return transition(
        state,
        node,
        "stopped",
        message,
        status=status,
        error=WorkflowError(node=node, code=code, message=message),
        selected_candidate_index=None,
        selection_source=None,
        approved_design=None,
        styling=None,
        **updates,
    )


def requirements_interpreter(
    state: WorkflowState,
    *,
    interpret_free_text: bool = False,
    allow_live: bool = False,
    interpreter: Callable[..., RequirementsResult] | None = None,
) -> dict:
    """Canonical input takes precedence; free-text interpretation is explicit.

    The default retains 07A's prose-as-metadata behavior. Trusted callable DI is
    available for offline demonstrations; description data cannot choose it.
    """
    if state.request.specification is None:
        if interpret_free_text and state.request.original_request:
            description = state.request.original_request
            result = RequirementsResult.model_validate(
                (interpreter or interpret_requirements)(
                    description, allow_live=allow_live
                )
            )
            if result.status == "ready":
                verified = prepare_requirements(
                    result.extraction, description, mode=result.mode, model=result.model
                )
                if (
                    verified.status != "ready"
                    or verified.specification != result.specification
                ):
                    raise ValueError("Interpretation and canonical conversion disagree")
                style = verified.extraction.style
                message = (
                    f"Requirements ready via {verified.mode}; canonical specification prepared. "
                    f"Assumptions: {' | '.join(verified.assumptions)} "
                    f"Style retained: {style.text if style else 'unspecified'}; "
                    f"{len(verified.extraction.soft_preferences)} soft preference(s) retained, not enforced."
                )
                return transition(
                    state,
                    "requirements_interpreter",
                    "accepted",
                    message,
                    interpretation=verified,
                    design=verified.specification.model_copy(deep=True),
                )
            statuses = {
                "needs_clarification": (
                    "needs_clarification",
                    "requirements_clarification",
                ),
                "unsupported": ("unsupported", "unsupported"),
                "unavailable": ("unavailable", "requirements_unavailable"),
                "error": ("failed", "requirements_error"),
            }
            status, code = statuses[result.status]
            details = " | ".join(result.clarifications) or (
                result.error.message
                if result.error
                else "Unsupported requirements; review interpretation limitations."
            )
            return stop(
                state,
                "requirements_interpreter",
                code,
                details,
                status=status,
                interpretation=result,
            )
        return stop(
            state,
            "requirements_interpreter",
            "missing_specification",
            "A structured RoomDesign specification is required; prose is not interpreted.",
        )
    design = RoomDesign.model_validate(state.request.specification).model_copy(
        deep=True
    )
    return transition(
        state,
        "requirements_interpreter",
        "accepted",
        f"Accepted structured room and {len(design.furniture)} furniture requests.",
        design=design,
    )


def layout_designer(state: WorkflowState) -> dict:
    """Delegate placement/search/heuristic scoring to the existing generator."""
    if state.iteration_count >= MAX_WORKFLOW_ITERATIONS:
        return stop(
            state,
            "layout_designer",
            "iteration_limit",
            "The single generation iteration is already consumed.",
        )
    if state.design is None:
        raise ValueError("Missing requirements handoff")
    design = state.design.model_copy(deep=True)
    request = state.request
    result = LayoutGenerationResult.model_validate(
        generate_layout_candidates(
            design.room,
            design.furniture,
            seed=request.seed,
            max_candidates=request.max_candidates,
            max_attempts=request.max_attempts,
            config=request.accessibility.model_copy(deep=True),
        )
    )
    if (
        result.seed != request.seed
        or result.requested_candidates != request.max_candidates
        or result.max_attempts != request.max_attempts
        or result.config != request.accessibility
    ):
        raise ValueError("Generator returned different request options")
    updates = {"generation": result, "iteration_count": state.iteration_count + 1}
    outcomes = {
        "unsupported": (
            "unsupported",
            "unsupported",
            "Generation cannot evaluate this specification.",
        ),
        "infeasible": (
            "infeasible",
            "infeasible",
            "The generator proved a necessary placement condition infeasible.",
        ),
        "search_exhausted": (
            "exhausted",
            "search_exhausted",
            "Search budget exhausted; infeasibility is not proved.",
        ),
    }
    if not result.candidates:
        status, code, message = outcomes[result.status]
        return stop(state, "layout_designer", code, message, status=status, **updates)
    return transition(
        state,
        "layout_designer",
        "generated",
        f"Generated {len(result.candidates)} candidate(s) in {result.attempts_used} "
        f"attempt(s); generator outcome: {result.status}.",
        **updates,
    )


def _preserves_specification(original: RoomDesign, candidate: RoomDesign) -> bool:
    """Check identity/dimension handoff only; placement validation stays in Shapely."""

    def fixed_furniture(design: RoomDesign) -> dict:
        return {
            item.id: item.model_dump(exclude={"x_m", "y_m"})
            for item in design.furniture
        }

    return original.room == candidate.room and fixed_furniture(
        original
    ) == fixed_furniture(candidate)


def spatial_critic(
    state: WorkflowState, *, selected_candidate_index: int | None = None
) -> dict:
    """Re-check actual candidates at zero tolerance; claimed reports cannot approve."""
    if state.generation is None or state.design is None:
        raise ValueError("Missing generation handoff")
    reviews = []
    for index, candidate in enumerate(state.generation.candidates):
        actual = AccessibilityValidationReport.model_validate(
            validate_accessibility(
                candidate.design.model_copy(deep=True),
                config=state.request.accessibility.model_copy(deep=True),
                area_tolerance_m2=0.0,
            )
        )
        if actual.status != "passed":
            reason = (
                "spatial_checks_failed"
                if actual.status == "failed"
                else "spatial_checks_unverified"
            )
        elif not _preserves_specification(state.design, candidate.design):
            reason = "specification_mismatch"
        elif actual != candidate.validation:
            reason = "report_mismatch"
        else:
            reason = "approved"
        reviews.append(
            CandidateReview(
                candidate_index=index,
                report=actual,
                accepted=reason == "approved",
                reason=reason,
            )
        )
    selected = (
        next((review.candidate_index for review in reviews if review.accepted), None)
        if selected_candidate_index is None
        else next(
            (
                review.candidate_index
                for review in reviews
                if review.accepted
                and review.candidate_index == selected_candidate_index
            ),
            None,
        )
    )
    if selected is None:
        return stop(
            state,
            "spatial_critic",
            "no_approved_candidates",
            "No requested candidate passed independent spatial and specification checks.",
            status="rejected",
            reviews=reviews,
        )
    advisor_state = advisor_policy(state).model_copy(
        update={
            "deterministic_candidate_index": selected
            if selected_candidate_index is None
            else None
        }
    )
    critique_state = critic_policy(state)
    advisor_note = (
        f" AI layout recommendation requested: {advisor_state.status}; "
        f"reason={advisor_state.reason or 'eligible'}; current source deterministic."
        if advisor_state.requested
        else " AI layout recommendation not requested; selection source deterministic."
    )
    if critique_state.requested:
        advisor_note += f" AI spatial critique requested: {critique_state.status}; reason={critique_state.reason or 'eligible'}; executed=False."
    if selected_candidate_index is not None:
        advisor_note = " Caller selection retained; selection source user_selection; no generation or AI layout advice executed."
    return transition(
        state,
        "spatial_critic",
        "approved",
        f"Reviewed {len(reviews)} candidate(s); selected approved candidate {selected} (zero-based)."
        + advisor_note,
        reviews=reviews,
        layout_recommendation=advisor_state,
        spatial_critique=critique_state,
        selected_candidate_index=selected,
        selection_source="deterministic"
        if selected_candidate_index is None
        else "user_selection",
        approved_design=state.generation.candidates[selected].design.model_copy(
            deep=True
        ),
    )


def interior_stylist(state: WorkflowState) -> dict:
    """Attach a fixture palette only; leave approved coordinates/reports untouched."""
    if state.approved_design is None:
        raise ValueError("Styling requires an approved candidate")
    theme = state.request.styling_preferences.theme
    palettes = {
        "neutral": ["ivory", "slate", "natural oak"],
        "warm": ["cream", "terracotta", "walnut"],
        "cool": ["white", "muted blue", "light ash"],
    }
    return transition(
        state,
        "interior_stylist",
        "styled",
        f"Attached deterministic {theme} styling metadata; geometry unchanged."
        + (
            f" Final selected candidate {state.selected_candidate_index}; source {state.selection_source}; AI critique advisory only."
            if state.spatial_critique.requested
            else ""
        )
        + (
            f" AI styling {state.ai_styling.status}; executed={state.ai_styling.executed}; "
            f"reason={state.ai_styling.reason}; style source deterministic_fixture."
            if state.ai_styling.requested
            else ""
        ),
        status="succeeded",
        ai_styling=state.ai_styling.model_copy(
            update={"source": "deterministic_fixture"}
        ),
        styling=StylingMetadata(
            theme=theme,
            palette=palettes[theme],
            material_notes=["Fixture suggestions only; materials are not applied."],
        ),
    )
