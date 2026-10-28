"""Extraction is untrusted evidence, separate from canonical architectural data."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from archimind.models import RoomDesign

ShortText = Annotated[str, Field(min_length=1, max_length=400)]
Notes = Annotated[list[ShortText], Field(max_length=16)]
CatalogKey = Literal["queen_bed", "desk", "wardrobe", "unknown_bed", "unsupported"]


class Contract(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )


class LengthEvidence(Contract):
    """Original number and unit; the LLM must never perform unit conversion."""

    value: FiniteFloat = Field(ge=0, le=1000)
    unit: Literal["m", "ft"]
    source_text: ShortText


class FurnitureRequirement(Contract):
    catalog_key: CatalogKey
    source_text: ShortText
    quantity: int | None = Field(ge=1, le=8)
    width: LengthEvidence | None
    depth: LengthEvidence | None
    height: LengthEvidence | None


class OpeningRequirement(Contract):
    wall: Literal["north", "south", "east", "west"] | None
    source_text: ShortText
    offset: LengthEvidence | None
    width: LengthEvidence | None
    height: LengthEvidence | None


class WindowRequirement(OpeningRequirement):
    sill_height: LengthEvidence | None


class Preference(Contract):
    text: ShortText
    source_text: ShortText


class RequirementsSchema(Contract):
    """All fields required (nullable when unknown) for Responses Structured Outputs.

    This is extraction metadata, not a second Room/Furniture model. Values may
    not be used for placement until application conversion and canonical checks.
    """

    room_type: Literal["bedroom", "studio", "unsupported", "unknown"]
    room_type_source: ShortText | None
    shape: Literal["rectangular", "unsupported", "unknown"]
    width: LengthEvidence | None
    depth: LengthEvidence | None
    ceiling_height: LengthEvidence | None
    furniture: list[FurnitureRequirement] = Field(max_length=16)
    doors: list[OpeningRequirement] | None = Field(max_length=16)
    windows: list[WindowRequirement] | None = Field(max_length=16)
    style: Preference | None
    hard_constraints: list[Preference] = Field(max_length=16)
    soft_preferences: list[Preference] = Field(max_length=16)
    missing_or_ambiguous: Notes
    assumptions: Notes
    unsupported_features: Notes


class RequirementsError(Contract):
    code: Literal[
        "disabled",
        "authorization_required",
        "authentication",
        "unsupported_model",
        "invalid_input",
        "timeout",
        "rate_limit",
        "connection",
        "api_error",
        "refusal",
        "incomplete",
        "missing_output",
        "invalid_response",
        "oversized_output",
    ]
    message: ShortText


class RequirementsResult(Contract):
    status: Literal[
        "ready", "needs_clarification", "unsupported", "unavailable", "error"
    ]
    mode: Literal["api_response", "offline_fixture"] = "api_response"
    model: str | None = None
    extraction: RequirementsSchema | None = None
    specification: RoomDesign | None = None
    clarifications: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: RequirementsError | None = None

    @model_validator(mode="after")
    def require_coherent_result(self) -> Self:
        if (self.status == "ready") != (self.specification is not None):
            raise ValueError(
                "Only a ready result may contain a canonical specification"
            )
        if (
            self.status in ("ready", "needs_clarification", "unsupported")
            and self.extraction is None
        ):
            raise ValueError("An interpretation outcome needs extraction data")
        if self.status == "ready" and (self.clarifications or self.error):
            raise ValueError(
                "Ready requirements cannot have outstanding questions/errors"
            )
        if self.status == "needs_clarification" and not self.clarifications:
            raise ValueError("Clarification requires specific questions")
        if self.status in ("unavailable", "error") and self.error is None:
            raise ValueError("Failure needs a typed error")
        return self
