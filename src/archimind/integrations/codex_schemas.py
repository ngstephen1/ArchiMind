"""Strict contracts for untrusted advice; suggestions are never validated placements."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

Text = Annotated[str, Field(min_length=1, max_length=2000, pattern=r"\S")]
FailureCode = Literal[
    "disabled",
    "authorization_required",
    "invalid_request",
    "request_too_large",
    "unsupported_geometry",
    "missing_cli",
    "unsupported_cli",
    "authentication_unavailable",
    "timeout",
    "process_error",
    "malformed_json",
    "invalid_schema",
    "unknown_furniture",
    "response_too_large",
    "io_error",
    "unsupported_platform",
]


class AdviceModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class FurniturePlacementSuggestion(AdviceModel):
    """Position uses the canonical southwest-origin, unrotated footprint in meters."""

    furniture_id: Text
    x_m: FiniteFloat
    y_m: FiniteFloat
    explanation: Text


class CodexAdvice(AdviceModel):
    design_analysis: Text
    suggestions: list[FurniturePlacementSuggestion] = Field(max_length=3)
    limitations: list[Text] = Field(min_length=1, max_length=8)


class CodexAdviceResult(AdviceModel):
    """Success means a parsed response, never proof of accessibility or validity."""

    status: Literal["success", "disabled", "failure"]
    error_code: FailureCode | None = None
    message: Text
    advice: CodexAdvice | None = None
    requires_spatial_validation: Literal[True] = True

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        if self.status == "success":
            if self.advice is None or self.error_code is not None:
                raise ValueError("Success requires advice and no error")
        elif self.advice is not None or self.error_code is None:
            raise ValueError("Non-success requires an error and no advice")
        if (self.status == "disabled") != (self.error_code == "disabled"):
            raise ValueError("Disabled status and code must agree")
        return self
