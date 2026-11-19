"""Interactive, metric floor plans without placement or spatial validation.

The origin is southwest, X points east, and Y points north. Furniture uses its
lower-left unrotated footprint corner. Only zero rotation is supported here.
Opening spans determine visible wall strokes; no opening collision test is made.
"""

from html import escape

import plotly.graph_objects as go

from archimind.models import Room, RoomDesign, Wall

_INK = "#263B48"
_DOOR = "#A8793C"
_WINDOW = "#237CB8"
_PALETTE = (
    ("#D7EBE5", "#4A8C80"),
    ("#E0E8F3", "#627FA5"),
    ("#EEE3D2", "#A88A60"),
    ("#E8E1EF", "#9075A0"),
)


def _wall_point(room: Room, wall: Wall, offset: float) -> tuple[float, float]:
    """Map a wall offset to the established room coordinates."""
    if wall == "north":
        return offset, room.depth_m
    if wall == "south":
        return offset, 0.0
    if wall == "east":
        return room.width_m, offset
    return 0.0, offset


def _add_walls(figure: go.Figure, room: Room, ink: str = _INK) -> None:
    """Draw wall strokes between openings, leaving the opening spans clear."""
    for wall in ("south", "east", "north", "west"):
        length = room.width_m if wall in ("north", "south") else room.depth_m
        spans = sorted(
            (item.offset_m, item.offset_m + item.width_m)
            for item in [*room.doors, *room.windows]
            if item.wall == wall
        )
        x: list[float | None] = []
        y: list[float | None] = []
        cursor = 0.0
        for start, end in [*spans, (length, length)]:
            if start > cursor:
                first = _wall_point(room, wall, cursor)
                last = _wall_point(room, wall, start)
                x.extend([first[0], last[0], None])
                y.extend([first[1], last[1], None])
            cursor = max(cursor, end)
        figure.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"color": ink, "width": 5},
                name="Wall",
                legendgroup="walls",
                showlegend=wall == "south",
                hoverinfo="skip",
                meta={"kind": "wall", "wall": wall},
            )
        )


def render_floorplan(design: RoomDesign, plan_theme=None) -> go.Figure:
    """Render an existing design without modifying it or checking spatial validity.

    Existing model instances are schema-revalidated to catch nested edits.
    Nonzero furniture rotations raise ValueError rather than displaying an
    inaccurate footprint. Axes include out-of-room furniture so it is not hidden.
    ``plan_theme`` (a style pack's PlanTheme or its dict) recolours the plan;
    None keeps today's colours exactly. Geometry and labels never change.
    """
    theme = plan_theme.model_dump() if hasattr(plan_theme, "model_dump") else plan_theme
    design = RoomDesign.model_validate(design)
    rotated = [
        f"{item.id} ({item.rotation_deg} degrees)"
        for item in design.furniture
        if item.rotation_deg != 0
    ]
    if rotated:
        raise ValueError(
            "Nonzero furniture rotations are not supported by the 2D renderer yet: "
            + ", ".join(rotated)
        )

    room = design.room
    figure = go.Figure()
    figure.add_shape(
        type="rect",
        name="Room footprint",
        x0=0,
        y0=0,
        x1=room.width_m,
        y1=room.depth_m,
        fillcolor=theme["floor_fill"] if theme else "#F8FAFB",
        line={"width": 0},
        layer="below",
    )

    min_x, max_x = 0.0, room.width_m
    min_y, max_y = 0.0, room.depth_m
    for index, item in enumerate(design.furniture):
        right, top = item.x_m + item.width_m, item.y_m + item.depth_m
        min_x, max_x = min(min_x, item.x_m), max(max_x, right)
        min_y, max_y = min(min_y, item.y_m), max(max_y, top)
        fill, border = (
            (theme["furniture_fill"], theme["furniture_stroke"])
            if theme
            else _PALETTE[index % len(_PALETTE)]
        )
        hover = (
            f"<b>{escape(item.name)}</b><br>"
            f"ID: {escape(item.id)}<br>Category: {escape(item.category)}<br>"
            f"Lower-left: ({item.x_m:g}, {item.y_m:g}) m<br>"
            f"Size: {item.width_m:g} × {item.depth_m:g} m<br>"
            f"Height: {item.height_m:g} m<br>Rotation: {item.rotation_deg}°"
        )
        figure.add_trace(
            go.Scatter(
                x=[item.x_m, right, right, item.x_m, item.x_m],
                y=[item.y_m, item.y_m, top, top, item.y_m],
                mode="lines",
                fill="toself",
                fillcolor=fill,
                line={"color": border, "width": 1.5},
                name=escape(item.name),
                ids=[item.id] * 5,
                meta={
                    "kind": "furniture",
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                },
                hoveron="fills+points",
                # Filled-region hover reads scalar text; vertices use the template.
                text=hover,
                hoverinfo="text",
                hovertemplate=hover + "<extra></extra>",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[item.x_m + item.width_m / 2],
                y=[item.y_m + item.depth_m / 2],
                mode="text",
                text=[escape(item.name)],
                textfont={"size": 12, "color": theme["label_color"] if theme else _INK},
                hoverinfo="skip",
                showlegend=False,
                meta={"kind": "furniture_label", "id": item.id},
            )
        )

    _add_walls(figure, room, theme["wall_fill"] if theme else _INK)
    for kind, openings, color in (
        ("door", room.doors, theme["door_color"] if theme else _DOOR),
        ("window", room.windows, theme["window_color"] if theme else _WINDOW),
    ):
        for index, opening in enumerate(openings):
            first = _wall_point(room, opening.wall, opening.offset_m)
            last = _wall_point(room, opening.wall, opening.offset_m + opening.width_m)
            figure.add_trace(
                go.Scatter(
                    x=[first[0], last[0]],
                    y=[first[1], last[1]],
                    mode="lines+markers",
                    line={
                        "color": color,
                        "width": 4,
                        "dash": "dot" if kind == "door" else "solid",
                    },
                    marker={"color": color, "size": 6},
                    name=kind.title(),
                    legendgroup=kind,
                    showlegend=index == 0,
                    meta={"kind": kind, "id": opening.id, "wall": opening.wall},
                    hovertemplate=(
                        f"<b>{kind.title()}: {escape(opening.id)}</b><br>"
                        f"Wall: {opening.wall}<br>Offset: {opening.offset_m:g} m<br>"
                        f"Width: {opening.width_m:g} m<br>Height: {opening.height_m:g} m"
                        "<extra></extra>"
                    ),
                )
            )
            figure.add_annotation(
                x=(first[0] + last[0]) / 2,
                y=(first[1] + last[1]) / 2,
                xshift={"west": -24, "east": 24}.get(opening.wall, 0),
                yshift={"south": -20, "north": 20}.get(opening.wall, 0),
                text=kind.title(),
                font={"size": 11, "color": color},
                showarrow=False,
            )

    padding = max(room.width_m, room.depth_m, max_x - min_x, max_y - min_y) * 0.12
    figure.update_layout(
        template="plotly_white",
        title={"text": escape(design.name or room.name), "x": 0.02},
        height=560,
        margin={"l": 64, "r": 36, "t": 88, "b": 64},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": _INK, "size": 12},
        legend={"orientation": "h", "x": 0, "y": 1.01, "yanchor": "bottom"},
        dragmode="pan",
        hovermode="closest",
        meta={"room_id": room.id, "units": "m", "origin": "southwest"},
        xaxis={
            "title": "X (m) · East →",
            "range": [min_x - padding, max_x + padding],
            "constrain": "domain",
            "fixedrange": False,
            "zeroline": False,
            "gridcolor": "#E9EDF1",
        },
        yaxis={
            "title": "Y (m) · North ↑",
            "range": [min_y - padding, max_y + padding],
            "scaleanchor": "x",
            "scaleratio": 1,
            "constrain": "domain",
            "fixedrange": False,
            "zeroline": False,
            "gridcolor": "#E9EDF1",
        },
    )
    return figure
