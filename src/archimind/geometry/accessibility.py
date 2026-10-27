"""Conservative, planar door access and circulation approximations (Task 04B).

Coordinates remain meters, X east and Y north from the southwest interior corner.
Doors have no hinge/swing data: rectangles here describe approach space, NOT swing.

Circulation uses continuous polygon connectivity, not a sampled occupancy grid
(there is no grid resolution). A translating, axis-aligned square of the chosen
width represents the occupant. Inset the room by half that width, expand each
rectangular furniture footprint by the same amount, then subtract their union.
Positive-area components are usable center-space regions. Every region must be
reachable from EVERY door's midpoint, inset by half the clearance width. Separate
doors do not excuse disconnected regions within this single room.

This deliberately conservative approximation can reject diagonal/circular-body
routes, a wide door usable away from its midpoint, and exact-width pinches that
connect only along a line or point. Tiny isolated positive-area regions count.
Floating-point topology near tangencies can affect results; there is no grid
aliasing, but neither numeric certification nor architectural compliance. We do
not evaluate functional access to individual furniture, height, windows, hinges,
or spaces too small for the square. Only rotation zero is supported. The access
stage is bounded to 256 total furniture objects plus doors; excess is unsupported.
"""

import warnings
from fractions import Fraction
from math import isfinite
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator
from shapely import LineString, Point, Polygon, union_all
from shapely.errors import GEOSException

from archimind.geometry.footprints import (
    UnsupportedGeometryError,
    _rectangle,
    furniture_footprint,
    room_footprint,
)
from archimind.geometry.validator import (
    DEFAULT_AREA_TOLERANCE_M2,
    SpatialValidationReport,
    SpatialViolation,
    ValidationStatus,
    validate_layout,
)
from archimind.models import Door, Room, RoomDesign

MAX_ACCESSIBILITY_OBJECTS = 256
CheckName = Literal["containment", "furniture_overlap", "door_clearance", "circulation"]
CheckStatus = Literal["passed", "failed", "unsupported", "not_evaluated"]


class AccessibilityConfig(BaseModel):
    """Meter-based assumptions, not regulatory or door-swing requirements."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )

    required_door_depth_m: FiniteFloat = Field(default=0.3, gt=0)
    advisory_door_depth_m: FiniteFloat = Field(default=0.9, gt=0)
    advisory_side_margin_m: FiniteFloat = Field(default=0.15, ge=0)
    walking_clearance_m: FiniteFloat = Field(default=0.6, gt=0)

    @model_validator(mode="after")
    def validate_depths(self) -> Self:
        if self.advisory_door_depth_m < self.required_door_depth_m:
            raise ValueError("Advisory depth must be at least the required depth")
        return self


class AccessibilityIssue(SpatialViolation):
    """An existing spatial issue or an access error/warning with door IDs."""

    violation_type: Literal[
        "out_of_bounds",
        "furniture_overlap",
        "unsupported_geometry",
        "blocked_door",
        "door_clearance_warning",
        "circulation_disconnected",
        "unsupported_check",
    ]
    door_ids: list[str] = Field(default_factory=list)
    severity: Literal["error", "warning"] = "error"

    @model_validator(mode="after")
    def validate_access_issue(self) -> Self:
        if any(not value.strip() for value in self.door_ids):
            raise ValueError("Door IDs must be nonblank")
        if len(set(self.door_ids)) != len(self.door_ids):
            raise ValueError("Door IDs must be distinct")
        if self.violation_type in ("blocked_door", "door_clearance_warning"):
            if len(self.door_ids) != 1 or len(self.furniture_ids) != 1:
                raise ValueError("Door issues require one door and one furniture ID")
        expected = (
            "warning" if self.violation_type == "door_clearance_warning" else "error"
        )
        if self.severity != expected:
            raise ValueError("Only advisory door clearance issues are warnings")
        return self


class CheckResult(BaseModel):
    """Explicit evaluation state, including why a check was skipped."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )
    status: CheckStatus
    message: str = Field(min_length=1, pattern=r"\S")
    measurements: dict[str, FiniteFloat] = Field(default_factory=dict)


def _overall_status(
    issues: list[AccessibilityIssue], checks: dict[CheckName, CheckResult]
) -> ValidationStatus:
    if any(
        check.status in ("unsupported", "not_evaluated") for check in checks.values()
    ) or any(
        issue.violation_type in ("unsupported_geometry", "unsupported_check")
        for issue in issues
    ):
        return "unverified"
    if any(check.status == "failed" for check in checks.values()) or any(
        issue.severity == "error" for issue in issues
    ):
        return "failed"
    return "passed"


class AccessibilityValidationReport(SpatialValidationReport):
    """Additive Task 04B report; the Task 04A API/report remain unchanged.

    A passed result permits advisory warnings but requires all four checks to be
    evaluated. Unknown/unsupported takes precedence over known failures. The
    inherited validator is overridden to enforce this broader status contract.
    """

    scope: Literal["task_04b_accessibility"] = "task_04b_accessibility"
    violations: list[AccessibilityIssue] = Field(default_factory=list)
    checks: dict[CheckName, CheckResult]
    config: AccessibilityConfig

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if set(self.checks) != {
            "containment",
            "furniture_overlap",
            "door_clearance",
            "circulation",
        }:
            raise ValueError("Every implemented check needs an explicit result")
        if self.status != _overall_status(self.violations, self.checks):
            raise ValueError("Status must agree with all issues and check results")
        return self


def _sum(*values: float) -> float:
    """Use decimal meter arithmetic consistently with the existing engine."""
    result = float(sum((Fraction(str(value)) for value in values), Fraction()))
    if not isfinite(result):
        raise UnsupportedGeometryError("Non-finite accessibility geometry")
    return result


def _bounds_rectangle(left: float, bottom: float, right: float, top: float) -> Polygon:
    if right <= left or top <= bottom:
        raise UnsupportedGeometryError("Collapsed accessibility rectangle")
    return _rectangle(
        left, bottom, _sum(right, -left), _sum(top, -bottom), "Access rectangle"
    )


def _opening_segment(room: Room, door: Door) -> LineString:
    start, end = door.offset_m, _sum(door.offset_m, door.width_m)
    if door.wall in ("north", "south"):
        y = room.depth_m if door.wall == "north" else 0.0
        segment = LineString([(start, y), (end, y)])
    else:
        x = room.width_m if door.wall == "east" else 0.0
        segment = LineString([(x, start), (x, end)])
    if not isfinite(segment.length) or segment.length <= 0:
        raise UnsupportedGeometryError("Door opening segment collapsed")
    return segment


def _clearance_zone(room: Room, door: Door, depth: float, margin: float) -> Polygon:
    """Extrude the opening inward, expand along its wall, and clip at corners."""
    left, bottom, right, top = _opening_segment(room, door).bounds
    if door.wall in ("north", "south"):
        left, right = (
            max(0.0, _sum(left, -margin)),
            min(room.width_m, _sum(right, margin)),
        )
        bottom, top = (
            (max(0.0, _sum(room.depth_m, -depth)), room.depth_m)
            if door.wall == "north"
            else (0.0, min(room.depth_m, depth))
        )
    else:
        bottom, top = (
            max(0.0, _sum(bottom, -margin)),
            min(room.depth_m, _sum(top, margin)),
        )
        left, right = (
            (max(0.0, _sum(room.width_m, -depth)), room.width_m)
            if door.wall == "east"
            else (0.0, min(room.width_m, depth))
        )
    return _bounds_rectangle(left, bottom, right, top)


def _entry_point(room: Room, door: Door, radius: float) -> Point:
    midpoint = _opening_segment(room, door).interpolate(0.5, normalized=True)
    if door.wall == "south":
        return Point(midpoint.x, radius)
    if door.wall == "north":
        return Point(midpoint.x, _sum(room.depth_m, -radius))
    if door.wall == "west":
        return Point(radius, midpoint.y)
    return Point(_sum(room.width_m, -radius), midpoint.y)


def _door_issues(
    design: RoomDesign, footprints: dict[str, Polygon], config: AccessibilityConfig
) -> list[AccessibilityIssue]:
    issues = []
    for door in sorted(design.room.doors, key=lambda door: door.id):
        required = _clearance_zone(design.room, door, config.required_door_depth_m, 0.0)
        advisory = _clearance_zone(
            design.room,
            door,
            config.advisory_door_depth_m,
            config.advisory_side_margin_m,
        )
        for identifier, footprint in footprints.items():
            required_area = required.intersection(footprint).area
            advisory_area = advisory.intersection(footprint).area
            if not isfinite(required_area) or not isfinite(advisory_area):
                raise UnsupportedGeometryError("Non-finite door intersection area")
            if required_area <= 0 and advisory_area <= 0:
                continue
            blocked = required_area > 0
            issues.append(
                AccessibilityIssue(
                    violation_type=(
                        "blocked_door" if blocked else "door_clearance_warning"
                    ),
                    furniture_ids=[identifier],
                    door_ids=[door.id],
                    severity="error" if blocked else "warning",
                    message=(
                        f"Furniture {identifier!r} "
                        + (
                            "blocks the required"
                            if blocked
                            else "intersects the advisory"
                        )
                        + f" rectangular approach zone of door {door.id!r}; "
                        "this is not a door-swing check."
                    ),
                    measurements={
                        "intersection_area_m2": (
                            required_area if blocked else advisory_area
                        )
                    },
                )
            )
    return issues


def _circulation(
    design: RoomDesign, footprints: dict[str, Polygon], config: AccessibilityConfig
) -> tuple[list[AccessibilityIssue], CheckResult]:
    room = design.room
    width = config.walking_clearance_m
    radius = width / 2
    if radius <= 0:
        raise UnsupportedGeometryError("Clearance radius is below numeric precision")
    components: list[Polygon] = []
    if min(room.width_m, room.depth_m) > width:
        right, top = _sum(room.width_m, -radius), _sum(room.depth_m, -radius)
        if right >= room.width_m or top >= room.depth_m:
            raise UnsupportedGeometryError("Room inset is below numeric precision")
        inset = _bounds_rectangle(radius, radius, right, top)
        obstacles = []
        for footprint in footprints.values():
            left, bottom, right, top = footprint.bounds
            expanded = (
                _sum(left, -radius),
                _sum(bottom, -radius),
                _sum(right, radius),
                _sum(top, radius),
            )
            if not (
                expanded[0] < left
                and expanded[1] < bottom
                and expanded[2] > right
                and expanded[3] > top
            ):
                raise UnsupportedGeometryError(
                    "Obstacle expansion is below numeric precision"
                )
            obstacles.append(_bounds_rectangle(*expanded))
        free = inset.difference(union_all(obstacles))
        if not free.is_valid or not isfinite(free.area):
            raise UnsupportedGeometryError("Unreliable circulation free-space topology")
        if isinstance(free, Polygon):
            components = [] if free.is_empty else [free]
        elif free.geom_type == "MultiPolygon":
            components = list(free.geoms)
        elif not free.is_empty:
            raise UnsupportedGeometryError("Unexpected circulation geometry type")

    components.sort(key=lambda polygon: (*polygon.bounds, polygon.area))
    inaccessible_doors = []
    for door in sorted(room.doors, key=lambda door: door.id):
        entry = _entry_point(room, door, radius)
        if door.width_m < width or not any(
            component.covers(entry) for component in components
        ):
            inaccessible_doors.append(door.id)
    measurements = {
        "usable_region_count": float(len(components)),
        "usable_center_area_m2": sum(component.area for component in components),
        "inaccessible_door_count": float(len(inaccessible_doors)),
        "walking_clearance_m": width,
    }
    failed = len(components) != 1 or bool(inaccessible_doors)
    issues = []
    if failed:
        issues.append(
            AccessibilityIssue(
                violation_type="circulation_disconnected",
                door_ids=inaccessible_doors or sorted(door.id for door in room.doors),
                message=(
                    f"Found {len(components)} usable center-space regions and "
                    f"{len(inaccessible_doors)} inaccessible door entries with a "
                    f"{width:g} m square clearance; every door must reach one "
                    "connected usable region. A blocked entry or passage below "
                    "this clearance may prevent circulation."
                ),
                measurements=measurements,
            )
        )
    return issues, CheckResult(
        status="failed" if failed else "passed",
        message=(
            "Door midpoint entries and all positive-area square-clearance regions "
            + ("are not connected." if failed else "are connected.")
        ),
        measurements=measurements,
    )


def validate_accessibility(
    design: RoomDesign,
    *,
    config: AccessibilityConfig | None = None,
    area_tolerance_m2: float = DEFAULT_AREA_TOLERANCE_M2,
) -> AccessibilityValidationReport:
    """Run Task 04A plus door/circulation checks without changing input models.

    No doors -> both access checks explicitly not_evaluated, overall unverified.
    Unsupported footprints are never omitted from a claimed circulation pass.
    Door blockers among supported items remain reported. Boundary-only rectangle
    contact is allowed; any positive-area required-zone intrusion is an error,
    regardless of the separate furniture-overlap area tolerance.
    """
    design = RoomDesign.model_validate(design)
    config = AccessibilityConfig.model_validate(
        config if config is not None else AccessibilityConfig()
    )
    base = validate_layout(design, area_tolerance_m2=area_tolerance_m2)
    issues = [
        AccessibilityIssue.model_validate(issue.model_dump())
        for issue in base.violations
    ]
    unknown_geometry = base.status == "unverified"
    checks: dict[CheckName, CheckResult] = {}
    for name, issue_type in (
        ("containment", "out_of_bounds"),
        ("furniture_overlap", "furniture_overlap"),
    ):
        failed = any(issue.violation_type == issue_type for issue in issues)
        checks[name] = CheckResult(
            status="unsupported"
            if unknown_geometry
            else "failed"
            if failed
            else "passed",
            message=(
                "See Task 04A issues; unsupported geometry prevents a complete result."
                if unknown_geometry
                else "Task 04A check completed; see any reported violations."
            ),
        )

    if not design.room.doors:
        for name in ("door_clearance", "circulation"):
            checks[name] = CheckResult(
                status="not_evaluated", message="Room has no door; no entrance assumed."
            )
    elif len(design.furniture) + len(design.room.doors) > MAX_ACCESSIBILITY_OBJECTS:
        message = f"Access checks support at most {MAX_ACCESSIBILITY_OBJECTS} furniture objects plus doors."
        issues.append(
            AccessibilityIssue(violation_type="unsupported_check", message=message)
        )
        for name in ("door_clearance", "circulation"):
            checks[name] = CheckResult(status="unsupported", message=message)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            try:
                room_footprint(design.room)
                footprints = {}
                for item in sorted(design.furniture, key=lambda item: item.id):
                    try:
                        footprints[item.id] = furniture_footprint(item)
                    except UnsupportedGeometryError:
                        pass  # Already recorded by Task 04A; checks stay unsupported.
                door_issues = _door_issues(design, footprints, config)
                issues.extend(door_issues)
                checks["door_clearance"] = CheckResult(
                    status=(
                        "unsupported"
                        if unknown_geometry
                        else "failed"
                        if any(issue.severity == "error" for issue in door_issues)
                        else "passed"
                    ),
                    message="Rectangular approach zones checked; no swing inferred.",
                )
            except (
                UnsupportedGeometryError,
                GEOSException,
                RuntimeWarning,
                OverflowError,
            ):
                message = "Door approach geometry could not be evaluated reliably."
                issues.append(
                    AccessibilityIssue(
                        violation_type="unsupported_check", message=message
                    )
                )
                checks["door_clearance"] = CheckResult(
                    status="unsupported", message=message
                )

            if unknown_geometry or checks["door_clearance"].status == "unsupported":
                checks["circulation"] = CheckResult(
                    status="unsupported",
                    message="Complete room, door, and furniture geometry is required.",
                )
            else:
                try:
                    circulation_issues, result = _circulation(
                        design, footprints, config
                    )
                    issues.extend(circulation_issues)
                    checks["circulation"] = result
                except (
                    UnsupportedGeometryError,
                    GEOSException,
                    RuntimeWarning,
                    OverflowError,
                ):
                    message = "Circulation geometry could not be evaluated reliably."
                    issues.append(
                        AccessibilityIssue(
                            violation_type="unsupported_check", message=message
                        )
                    )
                    checks["circulation"] = CheckResult(
                        status="unsupported", message=message
                    )

    order = {
        "unsupported_geometry": 0,
        "unsupported_check": 1,
        "out_of_bounds": 2,
        "furniture_overlap": 3,
        "blocked_door": 4,
        "door_clearance_warning": 5,
        "circulation_disconnected": 6,
    }
    issues.sort(
        key=lambda issue: (
            order[issue.violation_type],
            tuple(issue.door_ids),
            tuple(issue.furniture_ids),
            issue.message,
        )
    )
    return AccessibilityValidationReport(
        room_id=design.room.id,
        status=_overall_status(issues, checks),
        violations=issues,
        area_tolerance_m2=base.area_tolerance_m2,
        checks=checks,
        config=config,
    )
