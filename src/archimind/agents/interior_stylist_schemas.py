"""Strict style metadata, separate from the selected canonical LayoutCandidate."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from archimind.agents.interior_stylist_catalog import (
    ACCENTS,
    MATERIALS,
    PALETTES,
    AccentId,
    AccentSpec,
    MaterialId,
    MaterialSpec,
    PaletteId,
    StyleCatalog,
    ThemeId,
)
from archimind.agents.layout_schemas import Contract, PreferenceText
from archimind.agents.spatial_critic_schemas import SpatialCriticResult
from archimind.geometry import LayoutCandidate

ConflictCode = Literal[
    "mixed_theme_request",
    "palette_preference_conflict",
    "unavailable_material",
    "missing_style_details",
    "unsupported_performance_claim",
]


class InteriorStylistRequest(Contract):
    """Exactly one caller-selected candidate; the stylist has no selection API.

    Its design, furniture IDs, original score and complete report travel together.
    A report is independently rechecked before styling. Optional critique must
    describe this same candidate by exact data, including any local review target.
    """

    candidate: LayoutCandidate
    style_request: PreferenceText | None = None
    soft_preferences: list[PreferenceText] = Field(default_factory=list, max_length=8)
    critique: SpatialCriticResult | None = None


class InteriorStylistContext(Contract):
    request: InteriorStylistRequest
    catalog: StyleCatalog


class FurnitureFinishSelection(Contract):
    furniture_id: Annotated[str, Field(min_length=1, max_length=100)]
    material_id: MaterialId


class StylePreferenceAssessment(Contract):
    """Index 0 is the main style request; 1..8 are additional preferences."""

    preference_index: int = Field(ge=0, le=8)
    judgment: Literal["favored", "partial", "tradeoff", "unmet", "unverified"]


class InteriorStyleProposal(Contract):
    """Model output has IDs/codes only: no paths, colors, prose or measurements."""

    decision: Literal["style", "request_clarification"]
    theme_id: ThemeId | None
    palette_id: PaletteId | None
    wall_material_id: MaterialId | None
    floor_material_id: MaterialId | None
    furniture_finishes: list[FurnitureFinishSelection] = Field(max_length=32)
    accent_ids: list[AccentId] = Field(max_length=3)
    rationale_code: Literal[
        "coherent_palette",
        "restrained_accents",
        "finish_consistency",
        "clarification_needed",
    ]
    preference_assessments: list[StylePreferenceAssessment] = Field(max_length=9)
    conflict_codes: list[ConflictCode] = Field(max_length=5)


class StylePreferenceNote(Contract):
    preference_index: int
    judgment: Literal["favored", "partial", "tradeoff", "unmet", "unverified"]
    explanation: str


class InteriorStylePlan(Contract):
    """Resolved renderer-independent appearance metadata; no geometry fields."""

    catalog_version: Literal["archimind_style_v1"] = "archimind_style_v1"
    theme_id: ThemeId
    palette_id: PaletteId
    wall_finish: MaterialSpec
    floor_finish: MaterialSpec
    furniture_finishes: dict[str, MaterialSpec]
    accents: list[AccentSpec] = Field(max_length=3)
    explanation: str
    preference_notes: list[StylePreferenceNote]
    conflicts: list[str]
    unmet_preferences: list[int]
    assumptions: list[str]
    limitations: list[str]
    rendered: Literal[False] = False


class InteriorStylistError(Contract):
    code: Literal[
        "disabled",
        "authorization_required",
        "authentication",
        "unsupported_model",
        "invalid_input",
        "invalid_layout",
        "invalid_critique",
        "oversized_request",
        "timeout",
        "rate_limit",
        "connection",
        "api_error",
        "refusal",
        "incomplete",
        "missing_output",
        "invalid_response",
        "invalid_style",
        "oversized_output",
    ]
    message: str


class InteriorStylistResult(Contract):
    status: Literal["styled", "needs_clarification", "unavailable", "error"]
    mode: Literal["api_response", "offline_fixture", "not_evaluated"] = "not_evaluated"
    model: str | None = None
    context: InteriorStylistContext | None = None
    proposal: InteriorStyleProposal | None = None
    plan: InteriorStylePlan | None = None
    message: str
    clarification_reasons: list[ConflictCode] = Field(default_factory=list)
    error: InteriorStylistError | None = None

    @model_validator(mode="after")
    def coherent_result(self) -> Self:
        if self.status == "styled":
            if (
                self.plan is None
                or self.context is None
                or self.proposal is None
                or self.proposal.decision != "style"
                or self.error is not None
            ):
                raise ValueError(
                    "Styling needs a checked plan, context and proposal without an error"
                )
            ids = {item.id for item in self.context.request.candidate.design.furniture}
            if set(self.plan.furniture_finishes) != ids:
                raise ValueError(
                    "Style plan must cover exactly the selected furniture IDs"
                )
            palette = PALETTES[self.plan.palette_id]
            if (
                self.plan.theme_id != palette.theme_id
                or self.plan.theme_id != self.proposal.theme_id
                or self.plan.palette_id != self.proposal.palette_id
            ):
                raise ValueError(
                    "Plan theme/palette must match its proposal and catalog"
                )
            if (
                self.plan.wall_finish.material_id != self.proposal.wall_material_id
                or self.plan.floor_finish.material_id != self.proposal.floor_material_id
            ):
                raise ValueError("Plan wall/floor finishes must match the proposal")
            if {
                key: value.material_id
                for key, value in self.plan.furniture_finishes.items()
            } != {
                item.furniture_id: item.material_id
                for item in self.proposal.furniture_finishes
            }:
                raise ValueError("Plan furniture finishes must match the proposal")
            if [
                item.accent_id for item in self.plan.accents
            ] != self.proposal.accent_ids:
                raise ValueError("Plan accents must match the proposal")
            materials = [
                self.plan.wall_finish,
                self.plan.floor_finish,
                *self.plan.furniture_finishes.values(),
            ]
            if any(item != MATERIALS[item.material_id] for item in materials) or any(
                item != ACCENTS[item.accent_id] for item in self.plan.accents
            ):
                raise ValueError(
                    "Resolved appearance values must equal immutable catalog entries"
                )
            if (
                self.plan.wall_finish.material_id not in palette.wall_material_ids
                or self.plan.floor_finish.material_id not in palette.floor_material_ids
                or any(
                    item.material_id not in palette.furniture_material_ids
                    for item in self.plan.furniture_finishes.values()
                )
                or any(
                    item.accent_id not in palette.accent_ids
                    for item in self.plan.accents
                )
            ):
                raise ValueError("Resolved style must use compatible palette entries")
            if len(self.proposal.furniture_finishes) != len(ids) or len(
                set(self.proposal.accent_ids)
            ) != len(self.proposal.accent_ids):
                raise ValueError(
                    "Style selections must be distinct and cover each object once"
                )
        elif self.plan is not None:
            raise ValueError(
                "Unevaluated/clarification results cannot present a style plan"
            )
        if self.status in ("unavailable", "error"):
            if self.error is None or self.proposal is not None:
                raise ValueError("Failed styling needs a typed error and no proposal")
        elif self.error is not None:
            raise ValueError("Successful/clarification styling cannot contain an error")
        if self.status == "needs_clarification" and not self.clarification_reasons:
            raise ValueError("Clarification needs an explicit reason")
        return self
