"""Structural room meshes in meters: X east, Y north, Z up from southwest.

Walls are zero-thickness surfaces. Each wall is split at opening endpoints;
within each horizontal strip only the solid vertical intervals are triangulated.
Door and window rectangles therefore leave actual holes in the wall mesh. Blue
window panes and opening outlines are separate traces, not replacement wall faces.
No furniture, swing geometry, wall thickness, ceiling slab, or layout sync is used.

Opening rectangles may share boundaries or be stacked at different elevations.
Positive-area overlap on the same wall is rejected. Decimal-rational arithmetic
matches the canonical opening extent checks; collapsed/non-finite panels are
rejected before Plotly. Work is bounded to 128 openings in this single room.
"""

from dataclasses import dataclass
from fractions import Fraction
from html import escape
from itertools import combinations, pairwise
from math import isfinite

import plotly.graph_objects as go

from archimind.models import Door, Room, RoomDesign, Wall, Window

MAX_ROOM_3D_OPENINGS = 128
_WALLS: tuple[Wall, ...] = ("south", "east", "north", "west")
_FLOOR = "#E8DFCF"
_WALL = "#A7BBC0"
_INK = "#334D59"
_WINDOW = "#398FC4"
_DOOR = "#A8793C"


class RoomGeometryError(ValueError):
    """Structural geometry cannot be represented correctly by this renderer."""


@dataclass(frozen=True)
class _Opening:
    source: Door | Window
    left: Fraction
    right: Fraction
    bottom: Fraction
    top: Fraction


def _fraction(value: float) -> Fraction:
    return Fraction(str(value))


def _span(start: Fraction, end: Fraction) -> tuple[float, float]:
    try:
        first, last = float(start), float(end)
    except OverflowError as exc:
        raise RoomGeometryError("A room coordinate exceeds numeric limits") from exc
    if not isfinite(first) or not isfinite(last) or last <= first:
        raise RoomGeometryError("A structural span collapsed or is non-finite")
    return first, last


def _area(width: Fraction, height: Fraction) -> None:
    try:
        area = float(width * height)
    except OverflowError as exc:
        raise RoomGeometryError(
            "A structural panel area exceeds numeric limits"
        ) from exc
    if not isfinite(area) or area <= 0:
        raise RoomGeometryError("A structural panel has no finite positive area")


def _wall_point(
    room: Room, wall: Wall, along: float, z: float
) -> tuple[float, float, float]:
    if wall == "south":
        return along, 0.0, z
    if wall == "north":
        return along, room.depth_m, z
    if wall == "west":
        return 0.0, along, z
    return room.width_m, along, z


def _wall_quad(
    room: Room,
    wall: Wall,
    left: Fraction,
    right: Fraction,
    bottom: Fraction,
    top: Fraction,
) -> list[tuple[float, float, float]]:
    first, last = _span(left, right)
    low, high = _span(bottom, top)
    _area(right - left, top - bottom)
    return [
        _wall_point(room, wall, first, low),
        _wall_point(room, wall, last, low),
        _wall_point(room, wall, last, high),
        _wall_point(room, wall, first, high),
    ]


def _mesh(
    quads: list[list[tuple[float, float, float]]], *, reverse: bool = False, **style
) -> go.Mesh3d:
    vertices = [point for quad in quads for point in quad]
    triangles = []
    for index in range(0, len(vertices), 4):
        triangles.extend(
            [(index, index + 2, index + 1), (index, index + 3, index + 2)]
            if reverse
            else [(index, index + 1, index + 2), (index, index + 2, index + 3)]
        )
    return go.Mesh3d(
        x=[point[0] for point in vertices],
        y=[point[1] for point in vertices],
        z=[point[2] for point in vertices],
        i=[triangle[0] for triangle in triangles],
        j=[triangle[1] for triangle in triangles],
        k=[triangle[2] for triangle in triangles],
        flatshading=True,
        lighting={"ambient": 0.8, "diffuse": 0.5, "specular": 0.05},
        **style,
    )


def _openings(room: Room) -> dict[Wall, list[_Opening]]:
    sources = [*room.doors, *room.windows]
    if len(sources) > MAX_ROOM_3D_OPENINGS:
        raise RoomGeometryError(
            f"3D rendering supports at most {MAX_ROOM_3D_OPENINGS} openings"
        )
    by_wall: dict[Wall, list[_Opening]] = {wall: [] for wall in _WALLS}
    for source in sorted(sources, key=lambda source: source.id):
        left = _fraction(source.offset_m)
        bottom = (
            _fraction(source.sill_height_m)
            if isinstance(source, Window)
            else Fraction()
        )
        opening = _Opening(
            source,
            left,
            left + _fraction(source.width_m),
            bottom,
            bottom + _fraction(source.height_m),
        )
        _span(opening.left, opening.right)
        _span(opening.bottom, opening.top)
        by_wall[source.wall].append(opening)
    for wall, openings in by_wall.items():
        for first, second in combinations(openings, 2):
            if max(first.left, second.left) < min(first.right, second.right) and max(
                first.bottom, second.bottom
            ) < min(first.top, second.top):
                raise RoomGeometryError(
                    f"Openings {first.source.id!r} and {second.source.id!r} overlap "
                    f"on the {wall} wall"
                )
    return by_wall


def _wall_panels(room: Room, wall: Wall, openings: list[_Opening]) -> list:
    length = _fraction(room.width_m if wall in ("north", "south") else room.depth_m)
    height = _fraction(room.ceiling_height_m)
    cuts = sorted(
        {
            Fraction(),
            length,
            *(value for opening in openings for value in (opening.left, opening.right)),
        }
    )
    panels = []
    for left, right in pairwise(cuts):
        active = sorted(
            (
                opening
                for opening in openings
                if opening.left <= left and right <= opening.right
            ),
            key=lambda opening: (opening.bottom, opening.top, opening.source.id),
        )
        cursor = Fraction()
        for opening in active:
            if cursor < opening.bottom:
                panels.append(
                    _wall_quad(room, wall, left, right, cursor, opening.bottom)
                )
            cursor = opening.top
        if cursor < height:
            panels.append(_wall_quad(room, wall, left, right, cursor, height))
    return panels


def render_room_3d(room: Room) -> go.Figure:
    """Return an interactive structural scene; schema/geometry errors are explicit.

    RoomDesign revalidation reuses canonical room/opening ID integrity. Models
    are never edited. Four wall meshes use explicit independent triangles, so no
    automatic triangulation can bridge an opening. A fully open wall has no mesh.
    Axis proportions follow width:depth:height, with a uniform framing scale. Camera
    controls support orbit, zoom and pan; a stable room revision preserves camera
    position across unrelated Streamlit reruns.
    """
    room = RoomDesign(room=room).room
    width, depth, height = map(
        _fraction, (room.width_m, room.depth_m, room.ceiling_height_m)
    )
    _area(width, depth)
    _area(width, height)
    _area(depth, height)
    dimensions = (room.width_m, room.depth_m, room.ceiling_height_m)
    # Orthographic eye distance changes depth, not magnification. Proportional
    # aspect ratios preserve equal meters while leaving space for mobile labels.
    aspectratio = {
        axis: 0.8 * (dimension / max(dimensions))
        for axis, dimension in zip("xyz", dimensions, strict=True)
    }
    if any(value <= 0 for value in aspectratio.values()):
        raise RoomGeometryError("Room proportions exceed scene numeric limits")
    by_wall = _openings(room)
    figure = go.Figure()
    figure.add_trace(
        _mesh(
            [
                [
                    (0.0, 0.0, 0.0),
                    (room.width_m, 0.0, 0.0),
                    (room.width_m, room.depth_m, 0.0),
                    (0.0, room.depth_m, 0.0),
                ]
            ],
            name="Floor",
            color=_FLOOR,
            opacity=1.0,
            meta={"kind": "floor", "room_id": room.id},
            showlegend=True,
            legendgroup="floor",
            hovertemplate="Floor<br>X: %{x:.2f} m<br>Y: %{y:.2f} m<extra></extra>",
        )
    )
    wall_legend = False
    for wall in _WALLS:
        panels = _wall_panels(room, wall, by_wall[wall])
        if panels:
            figure.add_trace(
                _mesh(
                    panels,
                    reverse=wall in ("north", "west"),
                    name="Walls",
                    color=_WALL,
                    opacity=0.38,
                    showlegend=not wall_legend,
                    legendgroup="walls",
                    meta={"kind": "wall", "wall": wall, "panel_count": len(panels)},
                    hovertemplate=(
                        f"{wall.capitalize()} wall<br>" + "Z: %{z:.2f} m<extra></extra>"
                    ),
                )
            )
            wall_legend = True
    seen_kinds = set()
    for wall in _WALLS:
        for opening in by_wall[wall]:
            source = opening.source
            kind = "window" if isinstance(source, Window) else "door"
            points = _wall_quad(
                room, wall, opening.left, opening.right, opening.bottom, opening.top
            )
            metadata = {"kind": kind, "id": source.id, "wall": wall}
            hover = (
                f"{kind.title()} opening: {escape(source.id)}<br>Wall: {wall}<br>"
                f"Offset: {source.offset_m:g} m<br>Width: {source.width_m:g} m<br>"
                f"Height: {source.height_m:g} m<extra></extra>"
            )
            if kind == "window":
                figure.add_trace(
                    _mesh(
                        [points],
                        reverse=wall in ("north", "west"),
                        name="Windows",
                        color=_WINDOW,
                        opacity=0.3,
                        meta=metadata,
                        legendgroup=kind,
                        showlegend=kind not in seen_kinds,
                        hovertemplate=hover,
                    )
                )
            outline = [*points, points[0]]
            figure.add_trace(
                go.Scatter3d(
                    x=[point[0] for point in outline],
                    y=[point[1] for point in outline],
                    z=[point[2] for point in outline],
                    mode="lines",
                    line={"color": _WINDOW if kind == "window" else _DOOR, "width": 5},
                    name="Doors" if kind == "door" else "Window edges",
                    meta={**metadata, "kind": f"{kind}_outline"},
                    legendgroup=kind,
                    showlegend=kind == "door" and kind not in seen_kinds,
                    hovertemplate=hover,
                )
            )
            seen_kinds.add(kind)

    figure.update_layout(
        template="plotly_white",
        title={"text": f"{escape(room.name)} · Structural room", "x": 0.02},
        height=580,
        margin={"l": 0, "r": 0, "t": 88, "b": 0},
        font={"color": _INK, "size": 12},
        paper_bgcolor="#FFFFFF",
        legend={"orientation": "h", "x": 0, "y": 1.03, "yanchor": "bottom"},
        meta={
            "kind": "room_3d",
            "room_id": room.id,
            "units": "m",
            "origin": "southwest_floor",
        },
        uirevision=f"room-3d:{room.id}:{room.width_m}:{room.depth_m}:{room.ceiling_height_m}",
        scene={
            "aspectmode": "manual",
            "aspectratio": aspectratio,
            "dragmode": "orbit",
            "camera": {
                "eye": {"x": 1.6, "y": -1.6, "z": 1.6},
                "up": {"x": 0, "y": 0, "z": 1},
                "projection": {"type": "orthographic"},
            },
            "xaxis": {
                "title": "X (m) · East",
                "range": [0, room.width_m],
                "showspikes": False,
                "showbackground": False,
                "showgrid": False,
                "zeroline": False,
            },
            "yaxis": {
                "title": "Y (m) · North",
                "range": [0, room.depth_m],
                "showspikes": False,
                "showbackground": False,
                "showgrid": False,
                "zeroline": False,
            },
            "zaxis": {
                "title": "Z (m) · Up",
                "range": [0, room.ceiling_height_m],
                "showspikes": False,
                "showbackground": False,
                "showgrid": False,
                "zeroline": False,
            },
        },
    )
    return figure
