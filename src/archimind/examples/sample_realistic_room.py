"""Independent reproducible scene; not an optimized or spatially validated layout."""

from archimind.models import Door, Furniture, Room, RoomDesign, Window


def create_sample_realistic_room() -> RoomDesign:
    return RoomDesign(
        name="Experimental architectural room",
        room=Room(
            id="realistic-room",
            name="Experimental room",
            width_m=5.0,
            depth_m=4.0,
            ceiling_height_m=2.7,
            doors=[
                Door(id="entry", wall="south", offset_m=0.45, width_m=0.9, height_m=2.1)
            ],
            windows=[
                Window(
                    id="north-window",
                    wall="north",
                    offset_m=2.4,
                    width_m=1.5,
                    height_m=1.2,
                    sill_height_m=0.9,
                )
            ],
        ),
        furniture=[
            Furniture(
                id="chair-a",
                name="Chair A",
                category="chair",
                x_m=1.0,
                y_m=0.95,
                width_m=0.85,
                depth_m=0.7,
                height_m=0.85,
            ),
            Furniture(
                id="chair-b",
                name="Chair B",
                category="chair",
                x_m=2.25,
                y_m=1.2,
                width_m=0.75,
                depth_m=0.65,
                height_m=0.8,
            ),
            Furniture(
                id="desk-placeholder",
                name="Desk",
                category="desk",
                x_m=3.25,
                y_m=2.8,
                width_m=1.35,
                depth_m=0.65,
                height_m=0.75,
            ),
        ],
    )
