"""Advisory candidate selection: no generated coordinates or measured claims."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from archimind.geometry import LayoutGenerationResult
from archimind.models import RoomDesign

PreferenceText = Annotated[str, Field(min_length=1, max_length=400, pattern=r"\S")]
RationaleCode = Literal[
    "window_proximity",
    "entrance_separation",
    "usable_center_space",
    "preference_balance",
    "insufficient_evidence",
    "no_clear_preference",
]
LimitationCode = Literal[
    "limited_candidate_set",
    "subjective_preferences",
    "unmet_preferences",
    "daylight_not_evaluated",
    "ergonomics_not_evaluated",
]


class Contract(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )


class LayoutAdviceRequest(Contract):
    specification: RoomDesign
    generation: LayoutGenerationResult
    soft_preferences: list[PreferenceText] = Field(min_length=1, max_length=8)


class PreferenceAssessment(Contract):
    """An explicitly subjective model judgment, never certified satisfaction."""

    preference_index: int = Field(ge=0, le=7)
    judgment: Literal["favored", "tradeoff", "unmet", "uncertain"]


class LayoutProposal(Contract):
    """Closed model output; Python renders rationale and all numerical evidence.

    No free-form measurement text is accepted. A model can select existing fact
    references and qualitative codes, but cannot supply distances/clearances,
    geometry, scores, claims of daylight quality or ergonomic conclusions.
    """

    decision: Literal["recommend", "abstain"]
    candidate_index: int | None = Field(ge=0, le=1)
    rationale_code: RationaleCode
    evidence_refs: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        max_length=8
    )
    preference_assessments: list[PreferenceAssessment] = Field(max_length=8)
    limitation_codes: list[LimitationCode] = Field(max_length=5)


class MeasuredFeature(Contract):
    ref: str
    candidate_index: int = Field(ge=0, le=1)
    kind: Literal[
        "window_planar_gap",
        "door_planar_gap",
        "heuristic_score",
        "usable_center_space_ratio",
        "usable_center_area",
    ]
    furniture_id: str | None = None
    opening_id: str | None = None
    value: FiniteFloat = Field(ge=0)
    unit: Literal["m", "m2", "ratio", "score"]


class LayoutAdviceContext(Contract):
    """Read-only copied input and Python facts; contains no final approval."""

    request: LayoutAdviceRequest
    features: list[MeasuredFeature]


class LayoutAdviceError(Contract):
    code: Literal[
        "disabled",
        "authorization_required",
        "authentication",
        "unsupported_model",
        "invalid_input",
        "invalid_candidates",
        "oversized_request",
        "timeout",
        "rate_limit",
        "connection",
        "api_error",
        "refusal",
        "incomplete",
        "missing_output",
        "invalid_response",
        "invalid_selection",
        "oversized_output",
    ]
    message: str


class LayoutAdviceResult(Contract):
    status: Literal["recommended", "abstained", "no_candidates", "unavailable", "error"]
    mode: Literal["api_response", "offline_fixture", "not_evaluated"] = "not_evaluated"
    model: str | None = None
    context: LayoutAdviceContext | None = None
    proposal: LayoutProposal | None = None
    rationale: str
    evidence: list[MeasuredFeature] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    unmet_preferences: list[int] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    requires_spatial_critic: Literal[True] = True
    error: LayoutAdviceError | None = None

    @model_validator(mode="after")
    def coherent_status(self) -> Self:
        if self.status in ("recommended", "abstained"):
            if self.context is None or self.proposal is None or self.error is not None:
                raise ValueError(
                    "Advice needs context, a checked proposal and no error"
                )
            expected = "recommend" if self.status == "recommended" else "abstain"
            if self.proposal.decision != expected:
                raise ValueError("Advice status must match decision")
            selected = self.proposal.candidate_index
            if self.status == "recommended" and (
                selected is None
                or selected >= len(self.context.request.generation.candidates)
            ):
                raise ValueError("Recommendation must select a supplied candidate")
            if self.status == "abstained" and selected is not None:
                raise ValueError("Abstention cannot select a candidate")
            if any(fact not in self.context.features for fact in self.evidence):
                raise ValueError("Evidence must match supplied deterministic features")
        elif self.proposal is not None:
            raise ValueError("Unavailable/failed advice cannot contain a proposal")
        if self.status in ("unavailable", "error") and self.error is None:
            raise ValueError("Failed advice needs typed error information")
        return self
