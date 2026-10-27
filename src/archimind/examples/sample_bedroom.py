"""A manually specified bedroom for demonstration, not an optimized layout."""

from archimind.models import Door, Furniture, Room, RoomDesign, Window


def create_sample_bedroom() -> RoomDesign:
    """Return a fresh 5 x 4 x 2.7 m bedroom with zero-rotation furniture.

    All positions are lower-left footprint corners, in meters, measured from the
    southwest room origin. This example makes no clearance or collision claims.
    """
    return RoomDesign(
        name="Sample bedroom",
        room=Room(
            id="bedroom",
            name="Bedroom",
            width_m=5.0,
            depth_m=4.0,
            ceiling_height_m=2.7,
            doors=[
                Door(
                    id="south-door",
                    wall="south",
                    offset_m=0.6,
                    width_m=0.85,
                    height_m=2.1,
                )
            ],
            windows=[
                Window(
                    id="north-window",
                    wall="north",
                    offset_m=2.7,
                    width_m=1.5,
                    height_m=1.2,
                    sill_height_m=0.9,
                )
            ],
        ),
        furniture=[
            Furniture(
                id="queen-bed",
                name="Queen bed",
                category="bed",
                x_m=0.4,
                y_m=1.4,
                width_m=1.6,
                depth_m=2.0,
                height_m=0.6,
            ),
            Furniture(
                id="desk",
                name="Desk",
                category="desk",
                x_m=3.2,
                y_m=3.2,
                width_m=1.2,
                depth_m=0.6,
                height_m=0.75,
            ),
            Furniture(
                id="wardrobe",
                name="Wardrobe",
                category="storage",
                x_m=3.4,
                y_m=0.4,
                width_m=1.5,
                depth_m=0.6,
                height_m=2.0,
            ),
        ],
    )
