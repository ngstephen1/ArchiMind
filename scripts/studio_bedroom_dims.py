"""Nominal window assembly shared by the studio mesh and detail sheet."""

WALL_DEPTH_M = 0.12
FRAME_DEPTH_M = 0.08
SILL_DEPTH_M = 0.20
SILL_THICKNESS_M = 0.045
# The studio frame is centered on the inside face of the wall.
EXTERIOR_REVEAL_M = WALL_DEPTH_M - FRAME_DEPTH_M / 2
