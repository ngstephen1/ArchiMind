"""Deterministic containment and overlap checks; no clearance or safety claims.

Only zero-rotation, planar footprints are evaluated. A passed report means these
Task 04A checks passed, not that a layout is architecturally safe or accessible.
"""

import warnings
from itertools import combinations
from math import isfinite
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator
from shapely import Polygon
from shapely.errors import GEOSException

from archimind.geometry.footprints import (
    UnsupportedGeometryError,
    furniture_footprint,
    room_footprint,
)
from archimind.models import RoomDesign

# Absolute square-meter tolerance for overlap only. Containment uses exact covers,
# without buffering the room. Set the overlap tolerance to zero for strict area > 0.
DEFAULT_AREA_TOLERANCE_M2 = 1e-9
ViolationType = Literal["out_of_bounds", "furniture_overlap", "unsupported_geometry"]
ValidationStatus = Literal["passed", "failed", "unverified"]


class SpatialViolation(BaseModel):
    """One violation or unsupported check, with finite, unit-named measurements.

    An empty furniture_ids list identifies unsupported room geometry; the report's
    room_id and explanation identify that room. Pair IDs are sorted by the engine.
    """

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    violation_type: ViolationType
    furniture_ids: list[str] = Field(default_factory=list, max_length=2)
    message: str = Field(min_length=1, pattern=r"\S")
    measurements: dict[str, FiniteFloat] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_involved_ids(self) -> Self:
        if any(not identifier.strip() for identifier in self.furniture_ids):
            raise ValueError("Furniture IDs must be nonblank")
        if len(set(self.furniture_ids)) != len(self.furniture_ids):
            raise ValueError("Involved furniture IDs must be distinct")
        required = {"out_of_bounds": 1, "furniture_overlap": 2}
        if self.violation_type in required:
            if len(self.furniture_ids) != required[self.violation_type]:
                raise ValueError("Wrong number of furniture IDs for violation type")
        return self


def _status_for(violations: list[SpatialViolation]) -> ValidationStatus:
    if any(issue.violation_type == "unsupported_geometry" for issue in violations):
        return "unverified"
    return "failed" if violations else "passed"


class SpatialValidationReport(BaseModel):
    """A JSON-ready result scoped explicitly to the implemented Task 04A checks.

    Unverified takes precedence when any geometry cannot be evaluated, even if
    known violations also exist. Supported items are still checked. Invalid
    canonical schemas raise ValidationError before a spatial report is produced.
    """

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    room_id: str = Field(min_length=1, pattern=r"\S")
    scope: Literal["task_04a_containment_and_overlap"] = (
        "task_04a_containment_and_overlap"
    )
    status: ValidationStatus
    violations: list[SpatialViolation] = Field(default_factory=list)
    area_tolerance_m2: FiniteFloat = Field(default=DEFAULT_AREA_TOLERANCE_M2, ge=0)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if self.status != _status_for(self.violations):
            raise ValueError(
                "Status must agree with violations and unsupported geometry"
            )
        return self


def validate_layout(
    design: RoomDesign, *, area_tolerance_m2: float = DEFAULT_AREA_TOLERANCE_M2
) -> SpatialValidationReport:
    """Check every supported footprint and unique pair without modifying input.

    Wall contact is allowed via room.covers(footprint). Only intersection area
    greater than area_tolerance_m2 is a collision; boundary/corner contact is not.
    Results are ordered by unsupported geometry, containment, then overlap, with
    furniture IDs ordered lexicographically within each group, independent of
    input order. Unsupported rotations or unreliable numeric geometry never pass.
    """
    design = RoomDesign.model_validate(design)
    if (
        isinstance(area_tolerance_m2, bool)
        or not isinstance(area_tolerance_m2, (int, float))
        or not isfinite(area_tolerance_m2)
        or area_tolerance_m2 < 0
    ):
        raise ValueError("area_tolerance_m2 must be a finite, nonnegative number")

    issues: list[SpatialViolation] = []
    room: Polygon | None = None
    try:
        room = room_footprint(design.room)
    except UnsupportedGeometryError as exc:
        issues.append(
            SpatialViolation(
                violation_type="unsupported_geometry",
                message=str(exc),
                measurements={
                    "room_width_m": design.room.width_m,
                    "room_depth_m": design.room.depth_m,
                },
            )
        )

    footprints: dict[str, Polygon] = {}
    for item in sorted(design.furniture, key=lambda item: item.id):
        try:
            footprint = furniture_footprint(item)
        except UnsupportedGeometryError as exc:
            issues.append(
                SpatialViolation(
                    violation_type="unsupported_geometry",
                    furniture_ids=[item.id],
                    message=str(exc),
                    measurements={"rotation_deg": float(item.rotation_deg)},
                )
            )
            continue
        footprints[item.id] = footprint
        if room is None:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                contained = room.covers(footprint)
                if contained:
                    continue
                outside_area = footprint.difference(room).area
                if not isfinite(outside_area):
                    raise UnsupportedGeometryError("Non-finite outside area")
        except (GEOSException, RuntimeWarning, UnsupportedGeometryError):
            issues.append(
                SpatialViolation(
                    violation_type="unsupported_geometry",
                    furniture_ids=[item.id],
                    message=f"Containment of furniture {item.id!r} could not be verified.",
                )
            )
            continue
        issues.append(
            SpatialViolation(
                violation_type="out_of_bounds",
                furniture_ids=[item.id],
                message=(
                    f"Furniture {item.id!r} extends outside room {design.room.id!r}; "
                    f"outside footprint area is {outside_area:.6g} m²."
                ),
                measurements={"outside_area_m2": outside_area},
            )
        )

    for (first_id, first), (second_id, second) in combinations(footprints.items(), 2):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                area = first.intersection(second).area
                if not isfinite(area):
                    raise UnsupportedGeometryError("Non-finite intersection area")
        except (GEOSException, RuntimeWarning, UnsupportedGeometryError):
            issues.append(
                SpatialViolation(
                    violation_type="unsupported_geometry",
                    furniture_ids=[first_id, second_id],
                    message=f"Overlap of {first_id!r} and {second_id!r} could not be verified.",
                )
            )
            continue
        if area > area_tolerance_m2:
            issues.append(
                SpatialViolation(
                    violation_type="furniture_overlap",
                    furniture_ids=[first_id, second_id],
                    message=(
                        f"Furniture {first_id!r} and {second_id!r} overlap by "
                        f"{area:.6g} m²."
                    ),
                    measurements={"overlap_area_m2": area},
                )
            )

    order = {"unsupported_geometry": 0, "out_of_bounds": 1, "furniture_overlap": 2}
    issues.sort(
        key=lambda issue: (order[issue.violation_type], tuple(issue.furniture_ids))
    )
    return SpatialValidationReport(
        room_id=design.room.id,
        status=_status_for(issues),
        violations=issues,
        area_tolerance_m2=float(area_tolerance_m2),
    )
