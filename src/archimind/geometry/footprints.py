"""Shapely footprints in meters, with a southwest origin and X east/Y north.

Furniture positions are lower-left, unrotated footprint corners. Only rotation
zero is supported. Footprints carry no height, door-clearance, or path semantics.
"""

import warnings
from fractions import Fraction
from math import isfinite

from shapely import Polygon, box
from shapely.errors import GEOSException

from archimind.models import Furniture, Room


class UnsupportedGeometryError(ValueError):
    """Geometry cannot be represented reliably by the current footprint engine."""


def _rectangle(x: float, y: float, width: float, depth: float, label: str) -> Polygon:
    """Build a finite, positive-area rectangle without decimal endpoint drift."""
    try:
        # Match the decimal meter convention used by the canonical opening checks.
        right = float(Fraction(str(x)) + Fraction(str(width)))
        top = float(Fraction(str(y)) + Fraction(str(depth)))
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            polygon = box(x, y, right, top)
            area = polygon.area
            valid = polygon.is_valid
    except (OverflowError, GEOSException, RuntimeWarning) as exc:
        raise UnsupportedGeometryError(
            f"{label} cannot be represented reliably with finite geometry."
        ) from exc

    if (
        polygon.is_empty
        or not valid
        or not all(isfinite(value) for value in polygon.bounds)
        or not isfinite(area)
        or area <= 0
    ):
        raise UnsupportedGeometryError(
            f"{label} cannot be represented as a finite, positive-area polygon."
        )
    return polygon


def furniture_footprint(furniture: Furniture) -> Polygon:
    """Return a zero-rotation footprint, or raise UnsupportedGeometryError.

    Schema-invalid input raises Pydantic ValidationError. No coordinate or model
    mutation occurs, and no room containment or collision decision is made here.
    """
    furniture = Furniture.model_validate(furniture)
    if furniture.rotation_deg != 0:
        raise UnsupportedGeometryError(
            f"Furniture {furniture.id!r} has rotation {furniture.rotation_deg} degrees; "
            "only 0-degree footprints can be verified."
        )
    return _rectangle(
        furniture.x_m,
        furniture.y_m,
        furniture.width_m,
        furniture.depth_m,
        f"Furniture {furniture.id!r}",
    )


def room_footprint(room: Room) -> Polygon:
    """Return the rectangular interior, including its wall boundary."""
    room = Room.model_validate(room)
    return _rectangle(0.0, 0.0, room.width_m, room.depth_m, f"Room {room.id!r}")
