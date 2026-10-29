"""Fixed qualification demonstration; not generated or claimed to be optimized."""

from archimind.assets import furniture_from_planning_envelope
from archimind.assets.render_qualification import CHARLES_ID
from archimind.examples.sample_realistic_room import create_sample_realistic_room
from archimind.models import RoomDesign


def create_sample_product_room() -> RoomDesign:
    design = create_sample_realistic_room()
    design.name = "Charles native-scale product demonstration"
    design.furniture[:2] = [
        furniture_from_planning_envelope(
            CHARLES_ID,
            furniture_id=f.id,
            name=f"Charles {f.id}",
            x_m=f.x_m,
            y_m=f.y_m,
        ).furniture
        for f in design.furniture[:2]
    ]
    return design
