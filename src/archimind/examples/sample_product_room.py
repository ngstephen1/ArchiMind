"""Fixed native-scale fixture, independent of generated bedroom alternatives."""

from typing import NamedTuple

from archimind.assets import PlanningFurnitureBinding, furniture_from_planning_envelope
from archimind.assets.render_qualification import CHARLES_ID
from archimind.examples.sample_realistic_room import create_sample_realistic_room
from archimind.models import RoomDesign


class SampleProductFixture(NamedTuple):
    design: RoomDesign
    planning_bindings: tuple[PlanningFurnitureBinding, ...]


def create_sample_product_fixture() -> SampleProductFixture:
    """Return fresh canonical data and explicit sidecars, without spatial work."""
    design = create_sample_realistic_room()
    design.name = "Charles native-scale product demonstration"
    specs = tuple(
        furniture_from_planning_envelope(
            CHARLES_ID,
            furniture_id=f.id,
            name=f"Charles {f.id}",
            x_m=f.x_m,
            y_m=f.y_m,
        )
        for f in design.furniture[:2]
    )
    design.furniture[:2] = [p.furniture for p in specs]
    return SampleProductFixture(design, tuple(p.binding for p in specs))


def create_sample_product_room() -> RoomDesign:
    """Backward-compatible geometry-only factory; still performs no validation."""
    return create_sample_product_fixture().design
