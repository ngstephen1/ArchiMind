"""Public architectural models; all distances are in meters.

The room origin is its southwest interior corner. X increases east, Y increases
north, and Z increases vertically. Furniture positions locate the lower-left
corner of the unrotated footprint; rotation is stored without transforming it.
"""

from archimind.models.furniture import Furniture
from archimind.models.room import Door, Room, RoomDesign, Wall, Window

__all__ = ["Door", "Furniture", "Room", "RoomDesign", "Wall", "Window"]
