"""Furniture data, independent of collision detection or placement algorithms.

All distances are in meters. (x_m, y_m) is the lower-left corner of the unrotated
footprint in room coordinates: X points east and Y points north. Rotation is a
stored property only; it does not shift the position or swap width and depth.
Negative and out-of-room positions are intentionally representable.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator


class Furniture(BaseModel):
    """A named furniture item with an unrotated rectangular footprint."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    id: str = Field(min_length=1, pattern=r"\S")
    name: str = Field(min_length=1, pattern=r"\S")
    category: str = Field(min_length=1, pattern=r"\S")
    x_m: FiniteFloat
    y_m: FiniteFloat
    width_m: FiniteFloat = Field(gt=0)
    depth_m: FiniteFloat = Field(gt=0)
    height_m: FiniteFloat = Field(gt=0)
    rotation_deg: Literal[0, 90, 180, 270] = 0

    @field_validator("rotation_deg", mode="before")
    @classmethod
    def require_integer_rotation(cls, value: object) -> object:
        """Reject booleans/floats that could otherwise compare equal to literals."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("rotation_deg must be an integer: 0, 90, 180, or 270")
        return value
