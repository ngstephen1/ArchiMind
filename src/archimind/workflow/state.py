"""JSON-ready contracts for bounded orchestration and optional interpretation.

RoomDesign and the generator/validator reports remain the canonical contracts.
No coordinates, units, identity rules or spatial algorithms are redefined here.
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archimind.agents.requirements_schemas import RequirementsResult
from archimind.geometry import (
    MAX_GENERATION_ATTEMPTS,
    AccessibilityConfig,
    AccessibilityValidationReport,
    LayoutGenerationResult,
)
from archimind.models import RoomDesign

NodeName = Literal[
    "requirements_interpreter", "layout_designer", "spatial_critic", "interior_stylist"
]
ExecutionStatus = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "unsupported",
    "infeasible",
    "exhausted",
    "rejected",
    "needs_clarification",
    "unavailable",
]
MAX_WORKFLOW_ITERATIONS = 1
MAX_NODE_EXECUTIONS = 4


class _Contract(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )


class StylingPreferences(_Contract):
    """A fixture selector only; no inferred taste or rendering/material changes."""

    theme: Literal["neutral", "warm", "cool"] = "neutral"


class DesignRequest(_Contract):
    """Structured input with optional prose retained verbatim.

    Prose is metadata by default; the runner's explicit free-text mode can invoke
    the separately gated Requirements Interpreter.

    Missing specification is a traced requirements failure. Malformed canonical
    data/options raise Pydantic ValidationError before graph execution. Explicit
    empty-furniture specifications are allowed, as in the existing generator.
    """

    specification: RoomDesign | None = None
    original_request: str | None = Field(default=None, min_length=1, max_length=4000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    max_candidates: int = Field(default=2, ge=1, le=2)
    max_attempts: int = Field(default=500, ge=0, le=MAX_GENERATION_ATTEMPTS)
    accessibility: AccessibilityConfig = Field(default_factory=AccessibilityConfig)
    styling_preferences: StylingPreferences = Field(default_factory=StylingPreferences)


class AgentActivity(_Contract):
    """Deterministic activity of a future agent role; no timestamps or LLM claims."""

    sequence: int = Field(ge=1, le=MAX_NODE_EXECUTIONS)
    node: NodeName
    decision: Literal["accepted", "generated", "approved", "styled", "stopped"]
    message: str = Field(min_length=1)


class WorkflowError(_Contract):
    node: NodeName
    code: Literal[
        "missing_specification",
        "unsupported",
        "infeasible",
        "search_exhausted",
        "no_approved_candidates",
        "iteration_limit",
        "node_error",
        "requirements_clarification",
        "requirements_unavailable",
        "requirements_error",
    ]
    message: str = Field(min_length=1)


class CandidateReview(_Contract):
    candidate_index: int = Field(ge=0, le=1)
    report: AccessibilityValidationReport
    accepted: bool
    reason: Literal[
        "approved",
        "spatial_checks_failed",
        "spatial_checks_unverified",
        "report_mismatch",
        "specification_mismatch",
    ]

    @model_validator(mode="after")
    def require_verified_acceptance(self) -> Self:
        if self.accepted != (self.reason == "approved"):
            raise ValueError("Review decision and reason must agree")
        if self.accepted and self.report.status != "passed":
            raise ValueError("An accepted review needs fully passing spatial checks")
        return self


class StylingMetadata(_Contract):
    source: Literal["deterministic_fixture"] = "deterministic_fixture"
    theme: Literal["neutral", "warm", "cool"]
    palette: list[str]
    material_notes: list[str]
    limitation: str = "Metadata only; no geometry, assets or rendering are changed."


class WorkflowState(_Contract):
    """Explicit sequential handoffs; lists use replacement, never shared reducers.

    One generation iteration, at most four node executions, no automatic retry.
    A partial generator result may succeed if a candidate passes independent
    critique; exhaustion without candidates is an explicit terminal outcome.
    """

    request: DesignRequest
    interpretation: RequirementsResult | None = None
    design: RoomDesign | None = None
    generation: LayoutGenerationResult | None = None
    reviews: list[CandidateReview] = Field(default_factory=list, max_length=2)
    selected_candidate_index: int | None = Field(default=None, ge=0, le=1)
    approved_design: RoomDesign | None = None
    styling: StylingMetadata | None = None
    stage: Literal[
        "requirements_interpreter",
        "layout_designer",
        "spatial_critic",
        "interior_stylist",
        "complete",
    ] = "requirements_interpreter"
    status: ExecutionStatus = "pending"
    trace: list[AgentActivity] = Field(
        default_factory=list, max_length=MAX_NODE_EXECUTIONS
    )
    error: WorkflowError | None = None
    iteration_count: int = Field(default=0, ge=0, le=MAX_WORKFLOW_ITERATIONS)

    @model_validator(mode="after")
    def validate_handoffs(self) -> Self:
        if self.interpretation is not None:
            if self.interpretation.status == "ready":
                if self.design != self.interpretation.specification:
                    raise ValueError(
                        "Working specification must match ready interpretation"
                    )
            elif self.design is not None or self.approved_design is not None:
                raise ValueError("Unready interpretation cannot supply a design")
        if [item.sequence for item in self.trace] != list(
            range(1, len(self.trace) + 1)
        ):
            raise ValueError("Trace sequence must be contiguous")
        if len({review.candidate_index for review in self.reviews}) != len(
            self.reviews
        ):
            raise ValueError("Each candidate may be reviewed only once")
        selected = self.selected_candidate_index
        if (selected is None) != (self.approved_design is None):
            raise ValueError("Selected index and approved design must be paired")
        if selected is not None:
            if self.generation is None or selected >= len(self.generation.candidates):
                raise ValueError("Selected candidate must exist")
            approved = next(
                (
                    review
                    for review in self.reviews
                    if review.candidate_index == selected
                ),
                None,
            )
            if approved is None or not approved.accepted:
                raise ValueError("Selection requires an independently approved review")
            if self.approved_design != self.generation.candidates[selected].design:
                raise ValueError("Approved design must equal the selected candidate")
            if approved.report.room_id != self.approved_design.room.id:
                raise ValueError("Approved report must describe the selected room")
        if self.styling is not None and selected is None:
            raise ValueError("Styling requires an approved design")
        if self.status == "succeeded" and (
            self.stage != "complete" or self.styling is None or self.error is not None
        ):
            raise ValueError("Success requires completed styling without an error")
        if self.status in ("pending", "running", "succeeded"):
            if self.error is not None:
                raise ValueError("An active/successful state cannot contain an error")
        elif self.error is None or selected is not None:
            raise ValueError(
                "Terminal failure requires an error and no approved design"
            )
        return self
