"""Standalone advisory critique contracts; no placement or approval authority."""

from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from archimind.agents.layout_schemas import (
    Contract,
    LayoutAdviceRequest,
    LayoutAdviceResult,
    PreferenceText,
)

Index = Annotated[int, Field(ge=0, le=1)]
Reference = Annotated[str, Field(min_length=1, max_length=100)]
Category = Literal[
    "window_proximity",
    "wall_proximity",
    "entrance_separation",
    "usable_center_space",
    "heuristic_score",
    "spatial_validation",
    "missing_evidence",
]
MissingTopic = Literal[
    "none",
    "daylight",
    "ergonomics",
    "code_compliance",
    "furniture_usability",
    "preference_details",
    "additional_constraints",
    "alternative_layouts",
]
Stance = Literal["supports", "challenges", "cannot_evaluate", "not_provided"]


class SpatialCriticRequest(Contract):
    """C1 packet supplies canonical candidates, reports, scores and preferences.

    Additional constraints are retained as unverified requirements, never silently
    translated into new geometry rules. Candidate IDs are stable candidate-0/1
    aliases for this packet's indices, not new persistent design identities.
    """

    layout: LayoutAdviceRequest
    explicit_constraints: list[PreferenceText] = Field(
        default_factory=list, max_length=8
    )
    layout_recommendation: LayoutAdviceResult | None = None


class CriticEvidence(Contract):
    """Python-produced C1 facts plus wall gaps and scoped check results."""

    ref: str
    candidate_index: Index
    kind: Literal[
        "window_planar_gap",
        "door_planar_gap",
        "heuristic_score",
        "usable_center_space_ratio",
        "usable_center_area",
        "wall_planar_gap",
        "spatial_check",
    ]
    value: FiniteFloat | None = Field(default=None, ge=0)
    unit: Literal["m", "m2", "ratio", "score"] | None = None
    furniture_id: str | None = None
    opening_id: str | None = None
    wall: Literal["north", "south", "east", "west"] | None = None
    check_name: (
        Literal["containment", "furniture_overlap", "door_clearance", "circulation"]
        | None
    ) = None
    check_status: Literal["passed"] | None = None


class SpatialCriticContext(Contract):
    request: SpatialCriticRequest
    features: list[CriticEvidence]


class CriticObservationProposal(Contract):
    """No free prose, distances or severity claims from the model."""

    category: Category
    candidate_indices: list[Index] = Field(max_length=2)
    furniture_ids: list[Reference] = Field(max_length=4)
    evidence_refs: list[Reference] = Field(max_length=8)
    relation: Literal["less", "greater", "equal", "reported", "unknown"]
    missing_topic: MissingTopic


class CriticPreferenceAssessment(Contract):
    preference_index: int = Field(ge=0, le=7)
    judgment: Literal["partial_support", "tradeoff", "conflict", "unverified"]
    observation_indices: list[Annotated[int, Field(ge=0, le=2)]] = Field(max_length=3)


class SpatialCriticProposal(Contract):
    """Closed structured output; Python derives every factual statement."""

    decision: Literal["critique", "request_information", "abstain"]
    observations: list[CriticObservationProposal] = Field(max_length=3)
    preference_assessments: list[CriticPreferenceAssessment] = Field(max_length=8)
    recommendation_stance: Stance
    stance_observation_indices: list[Annotated[int, Field(ge=0, le=2)]] = Field(
        max_length=3
    )


class GroundedObservation(Contract):
    category: Category
    candidate_ids: list[str]
    furniture_ids: list[str]
    explanation: str
    evidence: list[CriticEvidence]


class GroundedPreference(Contract):
    preference_index: int
    judgment: Literal["partial_support", "tradeoff", "conflict", "unverified"]
    explanation: str
    observation_indices: list[int]


class SpatialCriticError(Contract):
    code: Literal[
        "disabled",
        "authorization_required",
        "authentication",
        "unsupported_model",
        "invalid_input",
        "invalid_candidates",
        "invalid_recommendation",
        "oversized_request",
        "timeout",
        "rate_limit",
        "connection",
        "api_error",
        "refusal",
        "incomplete",
        "missing_output",
        "invalid_response",
        "invalid_evidence",
        "oversized_output",
    ]
    message: str


class SpatialCriticResult(Contract):
    status: Literal["evaluated", "abstained", "no_candidates", "unavailable", "error"]
    mode: Literal["api_response", "offline_fixture", "not_evaluated"] = "not_evaluated"
    model: str | None = None
    context: SpatialCriticContext | None = None
    proposal: SpatialCriticProposal | None = None
    assessment: str
    observations: list[GroundedObservation] = Field(default_factory=list, max_length=3)
    preference_feedback: list[GroundedPreference] = Field(
        default_factory=list, max_length=8
    )
    recommendation_stance: Stance = "cannot_evaluate"
    recommendation_explanation: str = "No recommendation judgment was evaluated."
    unverified_constraints: list[int] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    advisory_only: Literal[True] = True
    error: SpatialCriticError | None = None

    @model_validator(mode="after")
    def coherent_result(self) -> Self:
        if self.status in ("evaluated", "abstained"):
            if self.context is None or self.proposal is None or self.error is not None:
                raise ValueError(
                    "Critique needs context, a checked proposal and no error"
                )
            if (self.status == "abstained") != (self.proposal.decision == "abstain"):
                raise ValueError("Critique status and proposal disagree")
            if self.recommendation_stance != self.proposal.recommendation_stance:
                raise ValueError("Critique stance and proposal disagree")
            if len(self.observations) != len(self.proposal.observations):
                raise ValueError("Every observation needs a grounded explanation")
            for observation in self.observations:
                if any(
                    fact not in self.context.features for fact in observation.evidence
                ):
                    raise ValueError("Evidence must match supplied Python features")
        elif self.proposal is not None or self.observations or self.preference_feedback:
            raise ValueError("Unevaluated results cannot present a critique")
        if (self.status in ("error", "unavailable")) != (self.error is not None):
            raise ValueError("Failure status requires typed error information")
        return self
