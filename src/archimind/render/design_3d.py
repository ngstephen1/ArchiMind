"""Compose the existing structural room scene with canonical furniture meshes."""

from html import escape
from math import isfinite

import plotly.graph_objects as go

from archimind.models import RoomDesign
from archimind.render.furniture_3d import FurnitureGeometryError, render_furniture_3d
from archimind.render.room_3d import render_room_3d

MAX_DESIGN_3D_FURNITURE = 100


def render_design_3d(design: RoomDesign) -> go.Figure:
    """Render a furnished design, preserving structural meshes and source models.

    Uses render_room_3d for all walls/openings, initial camera and interactions.
    Axis ranges include out-of-room and above-ceiling furniture without moving it.
    Equal meters along X/Y/Z are preserved using the full scene's span ratios.
    This viewer does not check collisions, clearances, or architectural validity.
    Furniture is sorted by ID for stable geometry/legend order; work is bounded.
    """
    design = RoomDesign.model_validate(design)
    if len(design.furniture) > MAX_DESIGN_3D_FURNITURE:
        raise FurnitureGeometryError(
            f"3D design rendering supports at most {MAX_DESIGN_3D_FURNITURE} furniture objects"
        )
    figure = render_room_3d(design.room)
    ranges = [
        [0.0, design.room.width_m],
        [0.0, design.room.depth_m],
        [0.0, design.room.ceiling_height_m],
    ]
    for item in sorted(design.furniture, key=lambda item: item.id):
        for mesh in render_furniture_3d(item):
            figure.add_trace(mesh)
            for limits, coordinates in zip(
                ranges, (mesh.x, mesh.y, mesh.z), strict=True
            ):
                limits[0] = min(limits[0], min(coordinates))
                limits[1] = max(limits[1], max(coordinates))
    spans = [high - low for low, high in ranges]
    if not all(isfinite(span) and span > 0 for span in spans):
        raise FurnitureGeometryError("Furnished scene spans exceed numeric limits")
    proportions = [0.8 * span / max(spans) for span in spans]
    if any(value <= 0 for value in proportions):
        raise FurnitureGeometryError(
            "Furnished scene proportions exceed numeric limits"
        )
    figure.update_layout(
        title={"text": f"{escape(design.room.name)} · Furnished room", "x": 0.02},
        height=640,
        meta={
            "kind": "design_3d",
            "room_id": design.room.id,
            "units": "m",
            "origin": "southwest_floor",
            "spatially_validated": False,
        },
        uirevision=f"design-3d:{design.room.id}",
    )
    figure.update_scenes(
        xaxis_range=ranges[0],
        yaxis_range=ranges[1],
        zaxis_range=ranges[2],
        aspectratio=dict(zip("xyz", proportions, strict=True)),
    )
    return figure
