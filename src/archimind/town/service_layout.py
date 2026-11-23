"""Modeled kitchen and bathroom fixture runs for residential Town studies."""

from dataclasses import dataclass

from archimind.geometry import validate_accessibility
from archimind.geometry.accessibility import AccessibilityConfig
from archimind.models import Furniture, Room, RoomDesign


@dataclass(frozen=True)
class FixtureSpec:
    id: str
    category: str
    width_m: float
    depth_m: float
    height_m: float
    operating_depth_m: float
    moving_leaf_depth_m: float = 0.0


FIXTURES = {
    "kitchen-dining": (
        FixtureSpec("refrigerator", "refrigeration", 0.75, 0.72, 1.95, 1.20, 0.75),
        FixtureSpec("prep-counter", "preparation", 0.95, 0.65, 0.92, 0.95),
        FixtureSpec("kitchen-sink", "washing", 0.8, 0.65, 0.92, 0.95),
        FixtureSpec("cooking-range", "cooking", 0.6, 0.65, 0.92, 1.20, 0.52),
    ),
    "bathroom": (
        FixtureSpec("toilet", "toilet", 0.40, 0.72, 0.78, 0.85),
        FixtureSpec("vanity", "basin", 0.85, 0.5, 0.85, 0.85),
        FixtureSpec("tub", "bathing", 1.5, 0.72, 0.55, 0.8),
    ),
}

DINING_RESERVATION = (1.75, 2.4, 0.87)
FIXTURE_GAP_M = 0.15


def design_service_room(room: Room) -> RoomDesign:
    """Place a fixture run at the south wall with a north-facing working side."""
    specs = FIXTURES[room.id]
    run_width = sum(spec.width_m for spec in specs) + (len(specs) - 1) * FIXTURE_GAP_M
    x = round((room.width_m - run_width) / 2, 6)
    objects = []
    for spec in specs:
        objects.append(
            Furniture(
                id=spec.id,
                name=spec.id.replace("-", " ").title(),
                category=spec.category,
                x_m=x,
                y_m=0.0,
                width_m=spec.width_m,
                depth_m=spec.depth_m,
                height_m=spec.height_m,
            )
        )
        x = round(x + spec.width_m + FIXTURE_GAP_M, 6)
    if room.id == "kitchen-dining":
        w, d, h = DINING_RESERVATION
        objects.append(
            Furniture(
                id="breakfast-suite",
                name="Breakfast Suite",
                category="table",
                x_m=round((room.width_m - w) / 2, 6),
                y_m=round(room.depth_m - d - 0.12, 6),
                width_m=w,
                depth_m=d,
                height_m=h,
            )
        )
    design = RoomDesign(room=room, furniture=objects)
    service_evidence(design)
    return design


def service_evidence(design: RoomDesign, *, passage_m: float = 0.6) -> dict:
    """Verify each operating state separately against the saved furnished plan.

    Front working strips start at the modeled fixture face. The moving leaf
    reserves its full projection across the fixture width. Vendor hinge geometry
    and utility endpoints need field coordination.
    """
    specs = FIXTURES[design.room.id]
    objects = {item.id: item for item in design.furniture}
    required = [spec.id for spec in specs]
    if design.room.id == "kitchen-dining":
        required.append("breakfast-suite")
    if missing := [identifier for identifier in required if identifier not in objects]:
        raise ValueError(
            f"Missing required fixture or dining reservation: {', '.join(missing)}."
        )
    if design.room.id == "kitchen-dining":
        table = objects["breakfast-suite"]
        if (table.width_m, table.depth_m, table.height_m, table.rotation_deg) != (
            *DINING_RESERVATION,
            0,
        ):
            raise ValueError("Dining must retain its four-place reservation.")
    states = []
    config = AccessibilityConfig(walking_clearance_m=passage_m)
    for spec in specs:
        item = objects[spec.id]
        if (item.width_m, item.depth_m, item.height_m, item.rotation_deg) != (
            spec.width_m,
            spec.depth_m,
            spec.height_m,
            0,
        ):
            raise ValueError(
                f"{item.id} does not match the modeled fixture and orientation."
            )
        open_depth = round(item.depth_m + spec.operating_depth_m, 6)
        occupied = item.model_copy(update={"depth_m": open_depth})
        open_design = design.model_copy(
            update={
                "furniture": [
                    occupied if other.id == item.id else other
                    for other in design.furniture
                ],
            }
        )
        if validate_accessibility(open_design, config=config).status != "passed":
            raise ValueError(
                f"{item.id} working or appliance-opening zone is obstructed."
            )
        states.append(
            {
                "fixture_id": item.id,
                "front_y_m": round(item.y_m + item.depth_m, 6),
                "x_m": item.x_m,
                "width_m": item.width_m,
                "working_depth_m": spec.operating_depth_m,
                "leaf_projection_m": spec.moving_leaf_depth_m,
            }
        )
    return {
        "operating_zones": states,
        "service_connections": "field verification pending",
    }
