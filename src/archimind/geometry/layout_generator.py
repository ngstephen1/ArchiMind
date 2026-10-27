"""Bounded, seeded placement of zero-rotation furniture in a rectangular room.

An attempt samples one pose per requested item, largest footprint first. A failed
partial Task 04A check abandons that attempt. Completed arrangements must pass
Task 04B with ZERO overlap tolerance. The first requested number of distinct
accepted layouts are ranked, not optimized across the remaining search budget.

Interior samples use 0.01 m precision; exact wall-contact coordinates are also
sampled. These are lower-left footprint positions in the canonical meter system.
Input positions are requests to replace, not fixed anchors or constraints. Heights
and windows are preserved but have no extra placement semantics. No function,
lighting, ergonomics, door-swing, or building-code suitability is inferred.

Each attempt performs at most N containment/overlap validations and one complete
accessibility validation. Work is bounded by max_attempts, capped at 10,000, and
32 furniture items, plus the access engine's combined object limit. Exhaustion
does not prove infeasibility. Only simple necessary conditions are classified as
infeasible (oversize footprints, excess total area, or unusable empty-room entry).
"""

from fractions import Fraction
from random import Random
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from archimind.geometry.accessibility import (
    MAX_ACCESSIBILITY_OBJECTS,
    AccessibilityConfig,
    AccessibilityValidationReport,
    validate_accessibility,
)
from archimind.geometry.footprints import (
    UnsupportedGeometryError,
    furniture_footprint,
    room_footprint,
)
from archimind.geometry.validator import validate_layout
from archimind.models import Furniture, Room, RoomDesign

MAX_GENERATION_ATTEMPTS = 10_000
MAX_GENERATION_FURNITURE = 32


class LayoutScore(BaseModel):
    """0–100 heuristic: 80% usable center-space ratio + 20% clear advisory doors.

    The first ratio divides usable occupant-center area by the inset empty-room
    area. The second is the fraction of doors without advisory warnings. Neither
    measures furniture function or occupant ergonomics. Ratios are rounded to
    12 decimals and the total to 6; hard violations are never traded for score.
    """

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )
    usable_space_ratio: FiniteFloat = Field(ge=0, le=1)
    advisory_clearance_ratio: FiniteFloat = Field(ge=0, le=1)
    total: FiniteFloat = Field(ge=0, le=100)


class LayoutCandidate(BaseModel):
    """A renderer-ready design, its complete passing report, and its score."""

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )
    design: RoomDesign
    validation: AccessibilityValidationReport
    score: LayoutScore

    @model_validator(mode="after")
    def require_passing_report(self) -> Self:
        if self.validation.status != "passed":
            raise ValueError("Only fully validated layouts may be candidates")
        if self.validation.room_id != self.design.room.id:
            raise ValueError("Candidate room and validation report must agree")
        if self.validation.area_tolerance_m2 != 0:
            raise ValueError("Generated candidates require zero overlap tolerance")
        return self


class LayoutGenerationResult(BaseModel):
    """JSON-ready alternatives or an explicit bounded-search outcome.

    Complete means the requested count was found, not globally optimal. Search
    exhaustion can include fewer candidates; unsupported and infeasible outcomes
    contain none. Timing is measured externally to keep this result reproducible.
    """

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )
    status: Literal["complete", "search_exhausted", "infeasible", "unsupported"]
    message: str = Field(min_length=1, pattern=r"\S")
    seed: int
    requested_candidates: int = Field(ge=1, le=2)
    max_attempts: int = Field(ge=0, le=MAX_GENERATION_ATTEMPTS)
    attempts_used: int = Field(ge=0)
    config: AccessibilityConfig
    candidates: list[LayoutCandidate] = Field(default_factory=list, max_length=2)
    rejections: dict[
        Literal["partial_spatial", "complete_access", "duplicate"], int
    ] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        count = len(self.candidates)
        if self.attempts_used > self.max_attempts:
            raise ValueError("Attempt budget exceeded")
        if count > self.requested_candidates:
            raise ValueError("Too many candidates")
        if (self.status == "complete") != (count == self.requested_candidates):
            raise ValueError("Complete status must agree with requested count")
        if self.status in ("infeasible", "unsupported") and count:
            raise ValueError("Infeasible/unsupported results cannot have candidates")
        if any(value < 0 for value in self.rejections.values()):
            raise ValueError("Rejection counts must be nonnegative")
        return self


def _fraction(value: float) -> Fraction:
    return Fraction(str(value))


def _integer_option(name: str, value: int, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def _coordinate(random: Random, maximum: float) -> float:
    # Half of samples touch a wall; the rest sample the interior. This is a
    # search bias, not a preference/ergonomic claim. Never use global RNG state.
    choice = random.randrange(4)
    if choice == 0:
        return 0.0
    if choice == 1:
        return maximum
    return min(maximum, round(random.uniform(0.0, maximum), 2))


def _signature(design: RoomDesign) -> tuple[tuple[str, float, float], ...]:
    return tuple(
        (item.id, item.x_m, item.y_m)
        for item in sorted(design.furniture, key=lambda item: item.id)
    )


def _score(room: Room, report: AccessibilityValidationReport) -> LayoutScore:
    clearance = _fraction(report.config.walking_clearance_m)
    empty_center_area = float(
        (_fraction(room.width_m) - clearance) * (_fraction(room.depth_m) - clearance)
    )
    usable_area = report.checks["circulation"].measurements["usable_center_area_m2"]
    usable_ratio = round(min(1.0, max(0.0, usable_area / empty_center_area)), 12)
    advisory_doors = {
        door_id
        for issue in report.violations
        if issue.violation_type == "door_clearance_warning"
        for door_id in issue.door_ids
    }
    advisory_ratio = round(1.0 - len(advisory_doors) / len(room.doors), 12)
    return LayoutScore(
        usable_space_ratio=usable_ratio,
        advisory_clearance_ratio=advisory_ratio,
        total=round(80.0 * usable_ratio + 20.0 * advisory_ratio, 6),
    )


def generate_layout_candidates(
    room: Room,
    furniture: list[Furniture],
    *,
    seed: int = 42,
    max_candidates: int = 2,
    max_attempts: int = 500,
    config: AccessibilityConfig | None = None,
) -> LayoutGenerationResult:
    """Replace requested positions with up to two feasible, seeded alternatives.

    Each attempt is one construction, abandoned at its first failing partial
    layout. Reports use the existing validators; no geometry constraints are
    reimplemented here. The original room, objects, and list are never edited.
    Input schema/option errors raise ValueError (including ValidationError).
    Valid but unsupported features or exhausted searches return structured data.
    No-door rooms cannot produce accepted candidates. An empty furniture request
    has only one distinct arrangement, so requesting two returns a partial result.
    """
    _integer_option("max_candidates", max_candidates, 1, 2)
    _integer_option("max_attempts", max_attempts, 0, MAX_GENERATION_ATTEMPTS)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    specification = RoomDesign(room=room, furniture=furniture)
    room = specification.room
    requested = specification.furniture
    config = AccessibilityConfig.model_validate(
        config if config is not None else AccessibilityConfig()
    )
    candidates: list[LayoutCandidate] = []
    attempts_used = 0
    rejections = {"partial_spatial": 0, "complete_access": 0, "duplicate": 0}

    def result(status: str, message: str) -> LayoutGenerationResult:
        ranked = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score.total,
                _signature(candidate.design),
            ),
        )
        return LayoutGenerationResult(
            status=status,
            message=message,
            seed=seed,
            requested_candidates=max_candidates,
            max_attempts=max_attempts,
            attempts_used=attempts_used,
            config=config,
            candidates=ranked,
            rejections=rejections,
        )

    if any(item.rotation_deg != 0 for item in requested):
        return result("unsupported", "Generation supports only 0-degree furniture.")
    if (
        len(requested) > MAX_GENERATION_FURNITURE
        or len(requested) + len(room.doors) > MAX_ACCESSIBILITY_OBJECTS
    ):
        return result(
            "unsupported",
            f"Generation supports at most {MAX_GENERATION_FURNITURE} furniture items "
            f"and {MAX_ACCESSIBILITY_OBJECTS} items plus doors combined.",
        )
    for item in requested:
        if item.width_m > room.width_m or item.depth_m > room.depth_m:
            return result(
                "infeasible",
                f"Furniture {item.id!r} cannot fit within the room at rotation zero.",
            )
    total_area = sum(
        (_fraction(item.width_m) * _fraction(item.depth_m) for item in requested),
        Fraction(),
    )
    if total_area > _fraction(room.width_m) * _fraction(room.depth_m):
        return result("infeasible", "Requested footprint area exceeds the room area.")
    try:
        room_footprint(room)
        for item in requested:
            # Original positions do not constrain the search or its numeric checks.
            furniture_footprint(item.model_copy(update={"x_m": 0.0, "y_m": 0.0}))
    except UnsupportedGeometryError as exc:
        return result("unsupported", str(exc))

    empty_report = validate_accessibility(
        RoomDesign(room=room), config=config, area_tolerance_m2=0.0
    )
    if empty_report.status == "unverified":
        return result(
            "unsupported",
            "Empty-room access checks are unsupported or not evaluated; "
            "a modeled, evaluable door is required.",
        )
    if empty_report.status == "failed":
        return result(
            "infeasible",
            "Even the empty room fails the configured door-entry/clearance checks.",
        )

    random = Random(seed)
    placement_order = sorted(
        requested,
        key=lambda item: (-_fraction(item.width_m) * _fraction(item.depth_m), item.id),
    )
    seen = set()
    for attempt in range(1, max_attempts + 1):
        attempts_used = attempt
        placed = []
        for item in placement_order:
            x_limit = float(_fraction(room.width_m) - _fraction(item.width_m))
            y_limit = float(_fraction(room.depth_m) - _fraction(item.depth_m))
            placed.append(
                item.model_copy(
                    update={
                        "x_m": _coordinate(random, x_limit),
                        "y_m": _coordinate(random, y_limit),
                    },
                    deep=True,
                )
            )
            partial = validate_layout(
                RoomDesign(room=room, furniture=placed), area_tolerance_m2=0.0
            )
            if partial.status != "passed":
                rejections["partial_spatial"] += 1
                break
        else:
            design = RoomDesign(
                room=room,
                furniture=sorted(placed, key=lambda item: item.id),
                name="Generated layout",
            )
            report = validate_accessibility(
                design, config=config, area_tolerance_m2=0.0
            )
            if report.status != "passed":
                rejections["complete_access"] += 1
                continue
            signature = _signature(design)
            if signature in seen:
                rejections["duplicate"] += 1
                continue
            seen.add(signature)
            candidates.append(
                LayoutCandidate(
                    design=design, validation=report, score=_score(room, report)
                )
            )
            if len(candidates) == max_candidates:
                return result(
                    "complete", "Found the requested distinct validated layouts."
                )
            if not requested:
                return result(
                    "search_exhausted",
                    "An empty furniture request has only one distinct arrangement; "
                    "returning that validated layout.",
                )

    return result(
        "search_exhausted",
        f"Found {len(candidates)} of {max_candidates} requested layouts within "
        f"{max_attempts} attempts. Search exhaustion is not proof of infeasibility.",
    )
