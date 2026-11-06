"""Code-only release gate. No model can call around, override or edit its result.

Everything here is recomputed from the actual design and the user's own words.
What the model claims about a layout is never read.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict
from shapely.geometry import LineString

from archimind.geometry import (
    AccessibilityConfig,
    LayoutCandidate,
    furniture_footprint,
    validate_accessibility,
)
from archimind.models import RoomDesign

# Catalog word -> furniture category used by the canonical models.
CATEGORIES = {"bed": "bed", "desk": "desk", "wardrobe": "storage"}
_LABELS = {category: word for word, category in CATEGORIES.items()}
_MENTION = re.compile(r"\b(beds?|desks?|wardrobes?)\b", re.I)
_CLAUSE = re.compile(r"[.,;!?\n]|\bbut\b|\band\b", re.I)
_NEGATED = re.compile(
    r"\b(?:no|without|remove|delete|drop|skip|get rid of|do not want|don't want)\b"
    r"(?:\s+(?:the|a|an|any|my|that|this))*\s*(?:\w+\s+)?$",
    re.I,
)
_NUMBERS = {
    word: value
    for value, word in enumerate(
        ("one", "two", "three", "four", "five", "six", "seven", "eight"), 1
    )
}
_QUANTITY = re.compile(r"\b(\d+|" + "|".join(_NUMBERS) + r")\s+(?:\w+\s+)?$", re.I)

NEAR_M = 1.0
AWAY_M = 1.5
AGAINST_WALL_M = 0.05
WINDOW_REACH_M = 0.3


class PlacementGoal(BaseModel):
    """A measurable wish. The agent cannot supply coordinates, only goals."""

    model_config = ConfigDict(extra="forbid")

    item: Literal["bed", "desk", "wardrobe"]
    relation: Literal["near_window", "near_door", "away_from_door", "against_wall"]
    required: bool


class GateResult(BaseModel):
    passed: bool
    reasons: list[str]


def expected_items(messages: list[str]) -> dict[str, int]:
    """Read requested items from the user's words; a later message overrides."""
    expected: dict[str, int] = {}
    for message in messages:
        current: dict[str, int] = {}
        for match in _MENTION.finditer(message):
            category = CATEGORIES[match.group(1).lower().rstrip("s")]
            before = message[: match.start()]
            clauses = list(_CLAUSE.finditer(before))
            clause = before[clauses[-1].end() :] if clauses else before
            if _NEGATED.search(clause):
                current[category] = 0
                continue
            quantity = _QUANTITY.search(clause)
            count = 1
            if quantity:
                word = quantity.group(1).lower()
                count = int(word) if word.isdigit() else _NUMBERS[word]
            if current.get(category) != 0:
                current[category] = max(current.get(category, 0), count)
        expected.update(current)
    return expected


def _wall_segment(design: RoomDesign, wall: str, offset: float, width: float):
    room = design.room
    if wall in ("north", "south"):
        y = room.depth_m if wall == "north" else 0.0
        return LineString([(offset, y), (offset + width, y)])
    x = room.width_m if wall == "east" else 0.0
    return LineString([(x, offset), (x, offset + width)])


def window_blockers(design: RoomDesign) -> list[str]:
    """Items taller than the sill standing directly in front of a window."""
    blockers = []
    for item in design.furniture:
        footprint = furniture_footprint(item)
        for window in design.room.windows:
            segment = _wall_segment(
                design, window.wall, window.offset_m, window.width_m
            )
            if (
                item.height_m > window.sill_height_m
                and footprint.distance(segment) <= WINDOW_REACH_M
            ):
                blockers.append(item.id)
                break
    return blockers


def _distance_to_openings(design: RoomDesign, item, openings) -> float | None:
    if not openings:
        return None
    footprint = furniture_footprint(item)
    return min(
        footprint.distance(
            _wall_segment(design, opening.wall, opening.offset_m, opening.width_m)
        )
        for opening in openings
    )


def goal_met(design: RoomDesign, goal: PlacementGoal) -> bool:
    """True when at least one item of that kind satisfies the measured relation."""
    room = design.room
    for item in design.furniture:
        if item.category != CATEGORIES[goal.item]:
            continue
        if goal.relation == "against_wall":
            left, bottom, right, top = furniture_footprint(item).bounds
            if (
                min(left, bottom, room.width_m - right, room.depth_m - top)
                <= AGAINST_WALL_M
            ):
                return True
            continue
        openings = room.windows if goal.relation == "near_window" else room.doors
        distance = _distance_to_openings(design, item, openings)
        if distance is None:
            continue
        if goal.relation == "away_from_door":
            if distance >= AWAY_M:
                return True
        elif distance <= NEAR_M:
            return True
    return False


def _fixed_furniture(design: RoomDesign) -> dict:
    return {
        item.id: item.model_dump(exclude={"x_m", "y_m"}) for item in design.furniture
    }


def release_gate(
    specification: RoomDesign,
    candidate: LayoutCandidate,
    messages: list[str],
    goals: list[PlacementGoal],
    config: AccessibilityConfig,
) -> GateResult:
    """Return every reason a design may not be shown as approved."""
    design = candidate.design
    reasons = []
    actual = validate_accessibility(
        design.model_copy(deep=True), config=config, area_tolerance_m2=0.0
    )
    if actual.status != "passed":
        reasons.append(f"Spatial checks did not pass (status: {actual.status}).")
    elif actual != candidate.validation:
        reasons.append("Spatial report does not match the actual geometry.")
    if specification.room != design.room or _fixed_furniture(
        specification
    ) != _fixed_furniture(design):
        reasons.append(
            "Design does not preserve the room and furniture in the specification."
        )
    counts: dict[str, int] = {}
    for item in design.furniture:
        counts[item.category] = counts.get(item.category, 0) + 1
    for category, wanted in expected_items(messages).items():
        label = _LABELS[category]
        have = counts.get(category, 0)
        if wanted == 0 and have:
            reasons.append(f"The user asked for no {label}, but the design has {have}.")
        elif have < wanted:
            reasons.append(
                f"The user asked for {wanted} {label}(s); design has {have}."
            )
    blockers = window_blockers(design)
    if blockers:
        reasons.append(f"Tall furniture blocks a window: {', '.join(blockers)}.")
    for goal in goals:
        if goal.required and not goal_met(design, goal):
            reasons.append(f"Required goal not met: {goal.item} {goal.relation}.")
    return GateResult(passed=not reasons, reasons=reasons)
