"""Nominal window assembly shared by the studio mesh and detail sheet."""

WALL_DEPTH_M = 0.12
FRAME_DEPTH_M = 0.08
SILL_DEPTH_M = 0.20
SILL_THICKNESS_M = 0.045
# The studio frame is centered on the inside face of the wall.
EXTERIOR_REVEAL_M = WALL_DEPTH_M - FRAME_DEPTH_M / 2


def saved_curtain_mount(room, curtain):
    """Mounting study derived from the saved curtain footprint, in room metres."""
    wall = curtain["wall"]
    if wall not in {"east", "west", "north", "south"}:
        raise ValueError("The saved curtain requires an identified wall.")
    along_y = wall in {"east", "west"}
    x, y = curtain["x_m"], curtain["y_m"]
    width, depth = curtain["width_m"], curtain["depth_m"]
    top = curtain["z_m"] + curtain["height_m"]
    start, span = (y, depth) if along_y else (x, width)
    wall_length = room["depth_m"] if along_y else room["width_m"]
    axis = {"west": 0, "east": room["width_m"], "south": 0, "north": room["depth_m"]}
    wall_coordinate = axis[wall]
    center = x + width / 2 if along_y else y + depth / 2
    projection = abs(center - wall_coordinate)
    rail_size = 0.028
    if not (
        start >= -1e-9
        and start + span <= wall_length + 1e-9
        and min(span, projection, top) > rail_size
        and top + rail_size <= room["ceiling_height_m"] + 1e-9
        and (center < wall_coordinate if wall in {"east", "north"} else center > 0)
    ):
        raise ValueError(
            "The saved curtain does not leave space for the modeled mount."
        )
    edge = min(0.12, span / 4)
    return {
        "wall": wall,
        "start_m": start,
        "span_m": span,
        "elevation_m": top,
        "wall_projection_m": projection,
        "rail_size_m": rail_size,
        "rail_center_m": center,
        "wall_coordinate_m": wall_coordinate,
        "bracket_offsets_m": [start + edge, start + span - edge],
    }
