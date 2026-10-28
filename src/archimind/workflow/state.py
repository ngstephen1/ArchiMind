"""JSON-ready contracts for bounded orchestration and optional interpretation.

RoomDesign and the generator/validator reports remain the canonical contracts.
No coordinates, units, identity rules or spatial algorithms are redefined here.
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archimind.agents.layout_schemas import LayoutAdviceResult, PreferenceText
from archimind.agents.requirements_schemas import RequirementsResult
from archimind.agents.spatial_critic_schemas import SpatialCriticResult
from archimind.geometry import (
    MAX_GENERATION_ATTEMPTS,
    AccessibilityConfig,
    AccessibilityValidationReport,
    LayoutGenerationResult,
)
from archimind.models import RoomDesign

NodeName = Literal[
    "requirements_interpreter",
    "layout_designer",
    "spatial_critic",
    "layout_advisor",
    "ai_spatial_critic",
    "interior_stylist",
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
MAX_NODE_EXECUTIONS = 6


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
    soft_preferences: list[PreferenceText] = Field(default_factory=list, max_length=8)


class AgentActivity(_Contract):
    """Ordered role decisions; mock/API selection provenance is explicit."""

    sequence: int = Field(ge=1, le=MAX_NODE_EXECUTIONS)
    node: NodeName
    decision: Literal[
        "accepted",
        "generated",
        "approved",
        "recommended",
        "fallback",
        "reviewed",
        "styled",
        "stopped",
    ]
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


class LayoutRecommendationState(_Contract):
    """Selection provenance; checked advice reuses the C1 output contract.

    ``executed`` records an adapter invocation, not proof of live model usage.
    Candidate indices are original generator indices; ``candidate_indices`` maps
    the advice context's local indices to those original indices.
    """

    requested: bool = False
    status: Literal[
        "not_requested",
        "pending",
        "disabled",
        "skipped",
        "recommended",
        "abstained",
        "unavailable",
        "error",
        "rejected",
    ] = "not_requested"
    executed: bool = False
    deterministic_candidate_index: int | None = Field(default=None, ge=0, le=1)
    proposed_candidate_index: int | None = Field(default=None, ge=0, le=1)
    candidate_indices: list[int] = Field(default_factory=list, max_length=2)
    advice: LayoutAdviceResult | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_advisor_state(self) -> Self:
        if (self.status == "not_requested") != (not self.requested):
            raise ValueError("Advisor request and execution status disagree")
        if self.executed and self.status in (
            "not_requested",
            "pending",
            "disabled",
            "skipped",
        ):
            raise ValueError("A skipped advisor cannot have executed")
        if len(set(self.candidate_indices)) != len(self.candidate_indices) or any(
            type(index) is not int or index not in (0, 1)
            for index in self.candidate_indices
        ):
            raise ValueError("Advisor index mapping must contain unique source indices")
        if self.advice is not None and self.advice.status != self.status:
            raise ValueError(
                "Advisor metadata must preserve the checked response status"
            )
        if self.status == "recommended":
            if (
                not self.executed
                or self.advice is None
                or self.proposed_candidate_index is None
            ):
                raise ValueError("Recommendation requires executed, checked advice")
            local = self.advice.proposal.candidate_index
            if (
                local is None
                or local >= len(self.candidate_indices)
                or self.candidate_indices[local] != self.proposed_candidate_index
            ):
                raise ValueError(
                    "Proposed source index must match advisor-local mapping"
                )
        return self


class SpatialCritiqueState(_Contract):
    """Advisory execution, independent of selection and deterministic approval.

    Candidate index is the original generator index; candidate_indices maps D1's
    local packet indices to originals. Executed means adapter invocation, not
    evidence of live API usage. D1 owns assessment, stance and observations.
    """

    requested: bool = False
    status: Literal[
        "not_requested",
        "pending",
        "disabled",
        "skipped",
        "evaluated",
        "abstained",
        "unavailable",
        "error",
        "rejected",
    ] = "not_requested"
    executed: bool = False
    candidate_index: int | None = Field(default=None, ge=0, le=1)
    candidate_indices: list[int] = Field(default_factory=list, max_length=2)
    result: SpatialCriticResult | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def coherent_critique(self) -> Self:
        if (self.status == "not_requested") != (not self.requested):
            raise ValueError("Critic request and execution status disagree")
        if self.executed and self.status in (
            "not_requested",
            "pending",
            "disabled",
            "skipped",
        ):
            raise ValueError("A skipped critic cannot have executed")
        if len(set(self.candidate_indices)) != len(self.candidate_indices) or any(
            type(index) is not int or index not in (0, 1)
            for index in self.candidate_indices
        ):
            raise ValueError("Critic mapping must contain unique source indices")
        if self.result is not None and self.result.status != (
            "error" if self.status == "rejected" else self.status
        ):
            raise ValueError("Critic metadata must preserve the actual response status")
        if self.status in ("evaluated", "abstained"):
            if (
                not self.executed
                or self.result is None
                or self.candidate_index not in self.candidate_indices
            ):
                raise ValueError(
                    "A critique needs execution, a checked result and target mapping"
                )
            if (
                self.result.context.request.reviewed_candidate_index
                != self.candidate_indices.index(self.candidate_index)
            ):
                raise ValueError("Critic target must match the local-to-source mapping")
        return self


class WorkflowState(_Contract):
    """Explicit sequential handoffs; lists use replacement, never shared reducers.

    One generation iteration, four to six nodes, no automatic retry.
    A partial generator result may succeed if a candidate passes independent
    critique; exhaustion without candidates is an explicit terminal outcome.
    """

    request: DesignRequest
    interpretation: RequirementsResult | None = None
    design: RoomDesign | None = None
    generation: LayoutGenerationResult | None = None
    reviews: list[CandidateReview] = Field(default_factory=list, max_length=2)
    layout_recommendation: LayoutRecommendationState = Field(
        default_factory=LayoutRecommendationState
    )
    spatial_critique: SpatialCritiqueState = Field(default_factory=SpatialCritiqueState)
    selection_source: Literal["deterministic", "ai_recommendation"] | None = None
    selected_candidate_index: int | None = Field(default=None, ge=0, le=1)
    approved_design: RoomDesign | None = None
    styling: StylingMetadata | None = None
    stage: Literal[
        "requirements_interpreter",
        "layout_designer",
        "spatial_critic",
        "layout_advisor",
        "ai_spatial_critic",
        "interior_stylist",
        "complete",
    ] = "requirements_interpreter"
    status: ExecutionStatus = "pending"
    trace: list[AgentActivity] = Field(
        default_factory=list, max_length=MAX_NODE_EXECUTIONS
    )
    error: WorkflowError | None = None
    iteration_count: int = Field(default=0, ge=0, le=MAX_WORKFLOW_ITERATIONS)

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_selection(cls, value):
        """Old serialized states have no advisor/source fields; infer their defaults."""
        if (
            isinstance(value, dict)
            and value.get("selected_candidate_index") is not None
        ):
            value = dict(value)
            if "selection_source" not in value:
                value["selection_source"] = "deterministic"
            if "layout_recommendation" not in value:
                value["layout_recommendation"] = {
                    "deterministic_candidate_index": value["selected_candidate_index"]
                }
        return value

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
            if approved.report != self.generation.candidates[selected].validation:
                raise ValueError(
                    "Selected candidate must retain its authoritative critique"
                )
            original = self.layout_recommendation.deterministic_candidate_index
            if original is None or not any(
                review.candidate_index == original and review.accepted
                for review in self.reviews
            ):
                raise ValueError(
                    "Original deterministic selection must be critic-approved"
                )
            if self.selection_source == "deterministic":
                if (
                    selected != original
                    or self.layout_recommendation.status == "recommended"
                ):
                    raise ValueError(
                        "Deterministic selection must retain the original without accepted AI advice"
                    )
            elif self.selection_source == "ai_recommendation":
                metadata = self.layout_recommendation
                if (
                    metadata.status != "recommended"
                    or selected != metadata.proposed_candidate_index
                ):
                    raise ValueError("AI source requires an accepted recommendation")
                advice_candidates = (
                    metadata.advice.context.request.generation.candidates
                )
                if len(advice_candidates) != len(metadata.candidate_indices):
                    raise ValueError("Advisor context and source mapping must agree")
                for local, source in enumerate(metadata.candidate_indices):
                    if (
                        source >= len(self.generation.candidates)
                        or advice_candidates[local]
                        != self.generation.candidates[source]
                    ):
                        raise ValueError(
                            "Advisor candidates must equal immutable source candidates"
                        )
            else:
                raise ValueError("Selection needs an explicit source")
        elif self.selection_source is not None:
            raise ValueError("A selection source requires a final selected candidate")
        critique = self.spatial_critique
        if critique.candidate_index is not None:
            if self.generation is None or critique.candidate_index >= len(
                self.generation.candidates
            ):
                raise ValueError("Critic target must exist")
            if selected is not None and selected != critique.candidate_index:
                raise ValueError("AI critique cannot change the selected candidate")
        if critique.status in ("evaluated", "abstained"):
            packet = critique.result.context.request
            candidates = packet.layout.generation.candidates
            if len(candidates) != len(critique.candidate_indices):
                raise ValueError("Critic packet and source mapping must agree")
            for local, source in enumerate(critique.candidate_indices):
                if (
                    source >= len(self.generation.candidates)
                    or candidates[local] != self.generation.candidates[source]
                ):
                    raise ValueError(
                        "Critic candidates must equal immutable source candidates"
                    )
                if not any(
                    review.candidate_index == source
                    and review.accepted
                    and review.report == candidates[local].validation
                    for review in self.reviews
                ):
                    raise ValueError(
                        "Critic candidates require authoritative deterministic approval"
                    )
            expected_advice = (
                self.layout_recommendation.advice
                if self.layout_recommendation.status == "recommended"
                else None
            )
            if packet.layout_recommendation != expected_advice or (
                expected_advice is not None
                and self.layout_recommendation.proposed_candidate_index
                != critique.candidate_index
            ):
                raise ValueError(
                    "Critic recommendation must equal the accepted advisor selection"
                )
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
