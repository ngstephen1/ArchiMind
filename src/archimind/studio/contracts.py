"""Concept recipes are bounded data, never programs, products or source evidence."""

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from archimind.models import Room

RoomKind = Literal["Bedroom", "Living room", "Home office"]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Unit = Annotated[FiniteFloat, Field(ge=0.001, le=1)]
Position = Annotated[FiniteFloat, Field(ge=0, le=1)]
Dimension = Annotated[FiniteFloat, Field(ge=0.05, le=10)]
MAX_PARTS = 64
MAX_ASSETS = 8
MAX_INSTANCES = 12


class StudioError(ValueError):
    """Only sanitized, application-written errors may reach the Studio UI."""


class Frozen(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


def digest(value) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(raw).hexdigest()


class ConceptItem(Frozen):
    name: str = Field(min_length=1, max_length=80)
    category: Literal["bed", "desk", "chair", "sofa", "table", "storage", "decor"]
    description: str = Field(min_length=1, max_length=400)
    width_m: Dimension
    depth_m: Dimension
    height_m: Dimension
    quantity: int = Field(ge=1, le=3)


class FurnishingPlan(Frozen):
    description: str = Field(min_length=1, max_length=600)
    wall_color: Color
    floor_color: Color
    items: tuple[ConceptItem, ...] = Field(min_length=1, max_length=MAX_ASSETS)

    @model_validator(mode="after")
    def count_instances(self) -> Self:
        if sum(i.quantity for i in self.items) > MAX_INSTANCES:
            raise ValueError("At most 12 furniture instances")
        return self


class Part(Frozen):
    # Local Y-up coordinates normalized to the object's W/H/D reservation.
    # Every primitive is centered at center; no rotation, code, URLs or loops.
    kind: Literal["box", "cylinder", "cone", "sphere"]
    # Homogeneous bounded arrays keep the provider schema in the supported
    # Structured Outputs subset (no positional prefixItems), while tuples keep
    # the accepted snapshot immutable.
    size: tuple[Unit, ...] = Field(min_length=3, max_length=3)
    center: tuple[Position, ...] = Field(min_length=3, max_length=3)
    color: Color
    roughness: Annotated[FiniteFloat, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def containment(self) -> Self:
        if any(
            c - s / 2 < -1e-9 or c + s / 2 > 1 + 1e-9
            for c, s in zip(self.center, self.size, strict=True)
        ):
            raise ValueError("Part exceeds the normalized reservation")
        return self


class Recipe(Frozen):
    parts: tuple[Part, ...] = Field(min_length=1, max_length=MAX_PARTS)

    @model_validator(mode="after")
    def grounded(self) -> Self:
        if len({(p.color.lower(), p.roughness) for p in self.parts}) > 8:
            raise ValueError("At most eight material finishes per recipe")
        if min(p.center[1] - p.size[1] / 2 for p in self.parts) > 1e-6:
            raise ValueError("A floor-standing concept must contact the floor")
        return self


class StudioDraft(Frozen):
    room_json: str
    room_kind: RoomKind
    brief: str = Field(min_length=1, max_length=4000)
    plan: FurnishingPlan
    source: Literal["offline_demo", "ai_concept"]
    model: str | None

    def room(self) -> Room:
        return Room.model_validate_json(self.room_json)

    @model_validator(mode="after")
    def valid_room(self) -> Self:
        room = self.room()
        if not room.doors or not all(
            0.1 <= v <= 20 for v in (room.width_m, room.depth_m, room.ceiling_height_m)
        ):
            raise ValueError("Studio needs a bounded rectangular room and an entrance")
        if len(room.doors) + len(room.windows) > 16:
            raise ValueError("At most 16 openings")
        for item in self.plan.items:
            if (
                item.width_m > room.width_m
                or item.depth_m > room.depth_m
                or item.height_m > room.ceiling_height_m
            ):
                raise ValueError("Concept reservation exceeds the room")
        if (self.source == "offline_demo") != (self.model is None):
            raise ValueError("Invalid provenance")
        return self
