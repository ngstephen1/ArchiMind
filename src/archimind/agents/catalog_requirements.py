"""Immutable evidence contracts for the catalog-aware Requirements Interpreter."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from archimind.agents.requirements_schemas import RequirementsError
from archimind.models import Room


class Frozen(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class CatalogChatTurn(Frozen):
    id: int = Field(ge=1)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class SourceQuote(Frozen):
    turn_id: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=400)


class ChatMeasurement(Frozen):
    value: FiniteFloat = Field(ge=0, le=1000)
    unit: Literal["m", "ft"]
    value_source: SourceQuote
    unit_source: SourceQuote


class ChatTextFact(Frozen):
    value: str = Field(min_length=1, max_length=128)
    source: SourceQuote


class ChatOpening(Frozen):
    wall: Literal["north", "south", "east", "west"] | None
    wall_source: SourceQuote | None
    offset: ChatMeasurement | None
    width: ChatMeasurement | None
    height: ChatMeasurement | None
    sill_height: ChatMeasurement | None


class CatalogFurnitureIntent(Frozen):
    function: Literal[
        "bed",
        "desk",
        "wardrobe",
        "chair",
        "armchair",
        "bookcase",
        "nightstand",
        "unsupported",
    ]
    source: SourceQuote
    quantity: int | None = Field(ge=1, le=8)
    variant: ChatTextFact | None
    product_id: ChatTextFact | None
    required_use: ChatTextFact | None
    materials: tuple[ChatTextFact, ...] = Field(max_length=8)
    styles: tuple[ChatTextFact, ...] = Field(max_length=8)
    colors: tuple[ChatTextFact, ...] = Field(max_length=8)
    max_width: ChatMeasurement | None
    max_depth: ChatMeasurement | None
    max_height: ChatMeasurement | None


class CatalogConversationExtraction(Frozen):
    room_type: Literal["bedroom", "unknown", "unsupported"]
    room_source: SourceQuote | None
    shape: Literal["rectangular", "unknown", "unsupported"]
    shape_source: SourceQuote | None
    width: ChatMeasurement | None
    depth: ChatMeasurement | None
    ceiling_height: ChatMeasurement | None
    doors: tuple[ChatOpening, ...] = Field(max_length=16)
    windows_state: Literal["unknown", "none", "present"]
    windows_source: SourceQuote | None
    windows: tuple[ChatOpening, ...] = Field(max_length=16)
    furniture: tuple[CatalogFurnitureIntent, ...] = Field(max_length=8)
    hard_constraints: tuple[ChatTextFact, ...] = Field(max_length=16)
    soft_preferences: tuple[ChatTextFact, ...] = Field(max_length=16)
    missing_or_ambiguous: tuple[str, ...] = Field(max_length=16)
    unsupported_features: tuple[str, ...] = Field(max_length=16)


class CatalogChatDraft(Frozen):
    turns: tuple[CatalogChatTurn, ...]
    extraction: CatalogConversationExtraction
    room_json: str

    def room(self) -> Room:
        return Room.model_validate_json(self.room_json)


class CatalogConversationResult(Frozen):
    status: Literal[
        "ready", "needs_clarification", "unsupported", "unavailable", "error"
    ]
    draft: CatalogChatDraft | None = None
    extraction: CatalogConversationExtraction | None = None
    clarifications: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    error: RequirementsError | None = None
    mode: Literal["api_response", "offline_fixture"] = "api_response"
    model: str | None = None

    @model_validator(mode="after")
    def coherent(self):
        if (self.status == "ready") != (self.draft is not None):
            raise ValueError("Only ready results contain drafts")
        if self.status == "needs_clarification" and not self.clarifications:
            raise ValueError("Clarification requires questions")
        if self.status in ("unavailable", "error") and self.error is None:
            raise ValueError("Failures require typed errors")
        return self
