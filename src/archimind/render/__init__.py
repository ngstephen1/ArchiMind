"""Visualization functions that consume canonical ArchiMind models."""

from archimind.render.design_3d import MAX_DESIGN_3D_FURNITURE, render_design_3d
from archimind.render.floorplan_2d import render_floorplan
from archimind.render.furniture_3d import FurnitureGeometryError, render_furniture_3d
from archimind.render.room_3d import (
    MAX_ROOM_3D_OPENINGS,
    RoomGeometryError,
    render_room_3d,
)

__all__ = [
    "MAX_DESIGN_3D_FURNITURE",
    "MAX_ROOM_3D_OPENINGS",
    "FurnitureGeometryError",
    "RoomGeometryError",
    "render_floorplan",
    "render_design_3d",
    "render_furniture_3d",
    "render_room_3d",
]
