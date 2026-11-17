"""Rigid source-to-canonical transforms, quaternion classification and footprints.

Canonical frame (ArchiMind): meters, X east, Y north, Z up, southwest origin, and
furniture positioned by the lower-left corner of its footprint.

Source conventions (up axis, quaternion order, pivot, whether ``size`` is a full or
half extent) are *inputs* recorded in :class:`Convention`, never assumptions baked
into code. P1 proves them for each real source before any geometry is admitted, and
an unproven convention blocks admission instead of guessing.
"""

import math
from dataclasses import dataclass
from typing import Literal

from archimind.datasets.canonical import digest

Matrix = tuple[tuple[float, float, float], ...]

# Y-up (X right, Y up, Z toward the viewer) -> canonical Z-up. Canonical
# (x, y, z) = (X, -Z, Y). A proper rotation: orthonormal with determinant +1.
Y_UP_TO_Z_UP: Matrix = ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0))
IDENTITY: Matrix = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

ANGLE_TOLERANCE_DEG = 0.5
TILT_TOLERANCE_DEG = 0.5


class GeometryError(ValueError):
    """Geometry violates a recorded convention or admission rule."""


@dataclass(frozen=True)
class Convention:
    """Everything needed to interpret one source's transforms. Versioned by digest."""

    name: str
    basis: Matrix
    quaternion_order: Literal["xyzw", "wxyz"]
    pivot: Literal["center", "bottom_center"]
    size_semantics: Literal["full_extent", "half_extent"]

    @property
    def version_digest(self) -> str:
        return digest(
            {
                "name": self.name,
                "basis": self.basis,
                "quaternion_order": self.quaternion_order,
                "pivot": self.pivot,
                "size_semantics": self.size_semantics,
            }
        )


def matmul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def transpose(a: Matrix) -> Matrix:
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


def apply(a: Matrix, v: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(a[i][k] * v[k] for k in range(3)) for i in range(3))


def determinant(a: Matrix) -> float:
    return (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )


def check_rigid(a: Matrix, *, tolerance: float = 1e-9) -> None:
    product = matmul(a, transpose(a))
    for i in range(3):
        for j in range(3):
            if abs(product[i][j] - (1.0 if i == j else 0.0)) > tolerance:
                raise GeometryError("Basis is not orthonormal")
    if abs(determinant(a) - 1.0) > tolerance:
        raise GeometryError("Basis is not a proper rotation (determinant must be +1)")


def normalize_quaternion(
    q: tuple[float, float, float, float], order: Literal["xyzw", "wxyz"]
) -> tuple[float, float, float, float]:
    """Return a unit quaternion in (x, y, z, w) order, with a canonical sign."""
    if len(q) != 4 or not all(math.isfinite(c) for c in q):
        raise GeometryError("Quaternion must have four finite components")
    x, y, z, w = q if order == "xyzw" else (q[1], q[2], q[3], q[0])
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm < 1e-9:
        raise GeometryError("Zero-length quaternion")
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    # q and -q are the same rotation; fix the sign so equal rotations compare equal.
    for c in (w, x, y, z):
        if abs(c) > 1e-12:
            if c < 0:
                x, y, z, w = -x, -y, -z, -w
            break
    return (x, y, z, w)


def quaternion_matrix(q_xyzw: tuple[float, float, float, float]) -> Matrix:
    x, y, z, w = q_xyzw
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def canonical_rotation(basis: Matrix, source_rotation: Matrix) -> Matrix:
    """Express a source-frame rotation in the canonical frame: B R B^T."""
    return matmul(matmul(basis, source_rotation), transpose(basis))


@dataclass(frozen=True)
class Orientation:
    yaw_deg: float
    tilt_deg: float
    quarter_turns: int | None  # None when yaw is not a multiple of 90 degrees


def classify(rotation: Matrix) -> Orientation:
    """Split a canonical rotation into tilt from vertical and yaw about +Z."""
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, rotation[2][2]))))
    yaw = math.degrees(math.atan2(rotation[1][0], rotation[0][0])) % 360.0
    nearest = round(yaw / 90.0)
    turns = None
    if abs(yaw - nearest * 90.0) <= ANGLE_TOLERANCE_DEG:
        turns = nearest % 4
    return Orientation(yaw_deg=yaw, tilt_deg=tilt, quarter_turns=turns)


@dataclass(frozen=True)
class CanonicalBox:
    x_m: float
    y_m: float
    bottom_z_m: float
    width_m: float  # extent along canonical X after rotation
    depth_m: float  # extent along canonical Y after rotation
    height_m: float
    quarter_turns: int


def object_box(
    convention: Convention,
    *,
    size: tuple[float, float, float],
    position: tuple[float, float, float],
    rotation: tuple[float, float, float, float],
    origin: tuple[float, float, float],
) -> CanonicalBox:
    """Canonical lower-left box of one object, or :class:`GeometryError`.

    ``size`` is the source's local (X, Y, Z) extent; ``origin`` is the source-frame
    point that becomes canonical (0, 0, 0) (e.g. the room's minimum corner on the
    floor). Objects that are tilted or not at a quarter-turn yaw are rejected rather
    than snapped, because snapping would misrepresent the source.
    """
    check_rigid(convention.basis)
    if not all(math.isfinite(s) and s > 0 for s in size):
        raise GeometryError("invalid_dimensions")
    full = tuple(
        s * 2 if convention.size_semantics == "half_extent" else s for s in size
    )
    q = normalize_quaternion(rotation, convention.quaternion_order)
    orientation = classify(canonical_rotation(convention.basis, quaternion_matrix(q)))
    if orientation.tilt_deg > TILT_TOLERANCE_DEG:
        raise GeometryError("tilted_object")
    if orientation.quarter_turns is None:
        raise GeometryError("non_quarter_turn_rotation")
    # Local extents in the canonical frame (unsigned), before yaw.
    local = tuple(abs(c) for c in apply(convention.basis, full))
    width, depth, height = local
    if orientation.quarter_turns % 2:
        width, depth = depth, width
    rel = tuple(p - o for p, o in zip(position, origin, strict=True))
    cx, cy, cz = apply(convention.basis, rel)
    bottom = cz - height / 2 if convention.pivot == "center" else cz
    return CanonicalBox(
        x_m=cx - width / 2,
        y_m=cy - depth / 2,
        bottom_z_m=bottom,
        width_m=width,
        depth_m=depth,
        height_m=height,
        quarter_turns=orientation.quarter_turns,
    )
