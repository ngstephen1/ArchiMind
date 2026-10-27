"""A single rectangular room, its openings, and its furniture design.

Coordinate convention (meters):
* (0, 0) is the southwest/bottom-left interior corner.
* X increases east/right; Y increases north/up; Z increases vertically.
* Room width is along X; room depth is along Y.
* North/south wall offsets start at the west end and increase eastward.
* East/west wall offsets start at the south end and increase northward.
* An opening occupies [offset_m, offset_m + width_m] on its supporting wall.
* Door bottoms are at floor level; window bottoms are at sill_height_m.

Only opening extents and identifier integrity are checked here. Furniture
containment, overlap, clearance, and rotated geometry belong to a later phase.
"""

from fractions import Fraction
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from archimind.models.furniture import Furniture

Wall = Literal["north", "south", "east", "west"]


def _exceeds_span(start: float, size: float, limit: float) -> bool:
    """Compare decimal meter values exactly, without float addition roundoff."""
    return Fraction(str(start)) + Fraction(str(size)) > Fraction(str(limit))


class Door(BaseModel):
    """A floor-level opening positioned by distance along its supporting wall."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    id: str = Field(min_length=1, pattern=r"\S")
    wall: Wall
    offset_m: FiniteFloat = Field(ge=0)
    width_m: FiniteFloat = Field(gt=0)
    height_m: FiniteFloat = Field(gt=0)


class Window(BaseModel):
    """A wall opening with sill height measured vertically from the floor."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    id: str = Field(min_length=1, pattern=r"\S")
    wall: Wall
    offset_m: FiniteFloat = Field(ge=0)
    width_m: FiniteFloat = Field(gt=0)
    height_m: FiniteFloat = Field(gt=0)
    sill_height_m: FiniteFloat = Field(ge=0)


class Room(BaseModel):
    """One rectangular room and openings that fit its walls and ceiling."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    id: str = Field(min_length=1, pattern=r"\S")
    name: str = Field(min_length=1, pattern=r"\S")
    width_m: FiniteFloat = Field(gt=0)
    depth_m: FiniteFloat = Field(gt=0)
    ceiling_height_m: FiniteFloat = Field(gt=0)
    doors: list[Door] = Field(default_factory=list)
    windows: list[Window] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_opening_extents(self) -> Self:
        """Check opening positions against this room's wall lengths and height."""
        for opening in [*self.doors, *self.windows]:
            wall_length = (
                self.width_m if opening.wall in ("north", "south") else self.depth_m
            )
            if _exceeds_span(opening.offset_m, opening.width_m, wall_length):
                raise ValueError(
                    f"Opening {opening.id!r} extends beyond its {opening.wall} wall"
                )

        for door in self.doors:
            if door.height_m > self.ceiling_height_m:
                raise ValueError(f"Door {door.id!r} exceeds the room ceiling")
        for window in self.windows:
            if _exceeds_span(
                window.sill_height_m, window.height_m, self.ceiling_height_m
            ):
                raise ValueError(f"Window {window.id!r} exceeds the room ceiling")
        return self


class RoomDesign(BaseModel):
    """A single room and its furniture, sharing one object-ID namespace.

    Schema validation runs on construction and explicit model_validate calls,
    including for existing model instances. After editing nested lists/objects,
    revalidate the complete design before accepting it. In-place edits themselves
    are not transactional or automatically validated.
    """

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    room: Room
    furniture: list[Furniture] = Field(default_factory=list)
    name: str | None = Field(default=None, min_length=1, pattern=r"\S")

    @model_validator(mode="after")
    def validate_unique_identifiers(self) -> Self:
        """Require uniqueness across room, door, window, and furniture IDs."""
        seen: set[str] = set()
        for item in [
            self.room,
            *self.room.doors,
            *self.room.windows,
            *self.furniture,
        ]:
            if item.id in seen:
                raise ValueError(f"Duplicate object identifier in design: {item.id!r}")
            seen.add(item.id)
        return self
