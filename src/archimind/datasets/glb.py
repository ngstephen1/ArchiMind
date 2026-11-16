"""Bounded, dependency-free glTF 2.0 binary (GLB) inspection.

Reads only the container, the JSON chunk and (for embedded image headers) the
binary chunk. It never decodes vertex data: bounds come from the POSITION accessor
``min``/``max``, which glTF 2.0 requires, transformed by each node's world matrix.
Every corner of a primitive's local box is transformed, so the world box is exact
for the accessor bounds under any rigid or scaled transform.
"""

import math
import struct
from dataclasses import dataclass
from pathlib import Path

from archimind.datasets.safe_io import UnsafeContentError, read_glb_json

BIN_CHUNK = 0x004E4942
MAX_NODES = 10_000
MAX_DEPTH = 64
TRIANGLES = 4
_IDENTITY = (
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
)

Matrix = tuple[float, ...]  # 16 floats, column-major like glTF
Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class GlbSummary:
    nodes: int
    meshes: int
    primitives: int
    triangles: int
    non_triangle_primitives: int
    world_min: Vec3
    world_max: Vec3
    transformed_nodes: int  # nodes whose local matrix is not the identity
    images: int
    max_texture_px: int | None  # None when an image header could not be read
    extensions_used: tuple[str, ...]

    @property
    def size(self) -> Vec3:
        return tuple(b - a for a, b in zip(self.world_min, self.world_max, strict=True))


def _finite(values, n: int, what: str) -> tuple[float, ...]:
    if not isinstance(values, list) or len(values) != n:
        raise UnsafeContentError(f"{what} must have {n} numbers")
    out = []
    for v in values:
        if (
            isinstance(v, bool)
            or not isinstance(v, int | float)
            or not math.isfinite(v)
        ):
            raise UnsafeContentError(f"{what} must be finite numbers")
        out.append(float(v))
    return tuple(out)


def _mul(a: Matrix, b: Matrix) -> Matrix:
    """Column-major 4x4 product a @ b."""
    return tuple(
        sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4))
        for c in range(4)
        for r in range(4)
    )


def _trs(node: dict) -> Matrix:
    if "matrix" in node:
        if any(k in node for k in ("translation", "rotation", "scale")):
            raise UnsafeContentError("Node has both matrix and TRS")
        return _finite(node["matrix"], 16, "matrix")
    tx, ty, tz = _finite(node.get("translation", [0, 0, 0]), 3, "translation")
    x, y, z, w = _finite(node.get("rotation", [0, 0, 0, 1]), 4, "rotation")
    sx, sy, sz = _finite(node.get("scale", [1, 1, 1]), 3, "scale")
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if not 0.99 < norm < 1.01:
        raise UnsafeContentError("Node rotation is not a unit quaternion")
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    r = (
        1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
        2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
        2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y),
    )  # fmt: skip
    return (
        r[0] * sx, r[1] * sx, r[2] * sx, 0.0,
        r[3] * sy, r[4] * sy, r[5] * sy, 0.0,
        r[6] * sz, r[7] * sz, r[8] * sz, 0.0,
        tx, ty, tz, 1.0,
    )  # fmt: skip


def _apply(m: Matrix, p: Vec3) -> Vec3:
    x, y, z = p
    return (
        m[0] * x + m[4] * y + m[8] * z + m[12],
        m[1] * x + m[5] * y + m[9] * z + m[13],
        m[2] * x + m[6] * y + m[10] * z + m[14],
    )


def _image_px(data: bytes) -> int | None:
    """Largest dimension from a PNG, JPEG or WebP header; ``None`` if unknown."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return max(w, h)
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                return None
            marker, length = data[i + 1], struct.unpack(">H", data[i + 2 : i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return max(w, h)
            i += 2 + length
        return None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        kind = data[12:16]
        if kind == b"VP8X":
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return max(w, h)
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return max(w & 0x3FFF, h & 0x3FFF)
        if kind == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return max((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    return None


def _bin_chunk(path: Path) -> bytes:
    with open(path, "rb") as handle:
        handle.seek(12)
        json_len = struct.unpack("<I", handle.read(4))[0]
        handle.seek(20 + json_len)
        header = handle.read(8)
        if len(header) < 8:
            return b""
        length, kind = struct.unpack("<II", header)
        if kind != BIN_CHUNK:
            raise UnsafeContentError("Second GLB chunk is not BIN")
        data = handle.read(length)
    if len(data) != length:
        raise UnsafeContentError("Truncated GLB BIN chunk")
    return data


def inspect_glb(path: Path, *, max_bytes: int = 64 * 1024 * 1024) -> GlbSummary:
    """Summarize a GLB's structure, world bounds, triangles and texture sizes."""
    path = Path(path)
    doc = read_glb_json(path, max_bytes=max_bytes)
    nodes = doc.get("nodes") or []
    meshes = doc.get("meshes") or []
    accessors = doc.get("accessors") or []
    if len(nodes) > MAX_NODES:
        raise UnsafeContentError("GLB has too many nodes")
    scenes = doc.get("scenes") or [{"nodes": list(range(len(nodes)))}]
    scene = scenes[doc.get("scene", 0)] if doc.get("scene", 0) < len(scenes) else None
    if not isinstance(scene, dict):
        raise UnsafeContentError("GLB default scene is missing")

    def accessor(index):
        if not isinstance(index, int) or not 0 <= index < len(accessors):
            raise UnsafeContentError("Accessor index out of range")
        return accessors[index]

    lo, hi = [math.inf] * 3, [-math.inf] * 3
    primitives = triangles = other = transformed = 0
    visited: set[int] = set()
    stack = [(root, _IDENTITY, 0) for root in scene.get("nodes") or []]
    while stack:
        index, parent, depth = stack.pop()
        if not isinstance(index, int) or not 0 <= index < len(nodes):
            raise UnsafeContentError("Node index out of range")
        if index in visited or depth > MAX_DEPTH:
            raise UnsafeContentError("GLB node graph has a cycle or is too deep")
        visited.add(index)
        node = nodes[index]
        local = _trs(node)
        if any(abs(a - b) > 1e-9 for a, b in zip(local, _IDENTITY, strict=True)):
            transformed += 1
        world = _mul(parent, local)
        if "mesh" in node:
            mesh_index = node["mesh"]
            if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(meshes):
                raise UnsafeContentError("Mesh index out of range")
            for prim in meshes[mesh_index].get("primitives") or []:
                primitives += 1
                pos = accessor((prim.get("attributes") or {}).get("POSITION"))
                pmin = _finite(pos.get("min"), 3, "POSITION min")
                pmax = _finite(pos.get("max"), 3, "POSITION max")
                for corner in (
                    (x, y, z) for x in (pmin[0], pmax[0]) for y in (pmin[1], pmax[1])
                    for z in (pmin[2], pmax[2])
                ):  # fmt: skip
                    for axis, value in enumerate(_apply(world, corner)):
                        lo[axis], hi[axis] = min(lo[axis], value), max(hi[axis], value)
                if prim.get("mode", TRIANGLES) != TRIANGLES:
                    other += 1
                    continue
                source = accessor(prim["indices"]) if "indices" in prim else pos
                count = source.get("count")
                if not isinstance(count, int) or count < 0 or count % 3:
                    raise UnsafeContentError("Triangle primitive count is invalid")
                triangles += count // 3
        for child in node.get("children") or []:
            stack.append((child, world, depth + 1))
    if not primitives:
        raise UnsafeContentError("GLB has no mesh primitives")

    images = doc.get("images") or []
    sizes: list[int | None] = []
    if images:
        blob, views = _bin_chunk(path), doc.get("bufferViews") or []
        for image in images:
            view = image.get("bufferView")
            if not isinstance(view, int) or not 0 <= view < len(views):
                sizes.append(None)
                continue
            start = views[view].get("byteOffset", 0)
            sizes.append(_image_px(blob[start : start + 64 * 1024]))
    return GlbSummary(
        nodes=len(nodes),
        meshes=len(meshes),
        primitives=primitives,
        triangles=triangles,
        non_triangle_primitives=other,
        world_min=tuple(lo),
        world_max=tuple(hi),
        transformed_nodes=transformed,
        images=len(images),
        max_texture_px=None if None in sizes else max(sizes, default=0),
        extensions_used=tuple(sorted(doc.get("extensionsUsed") or [])),
    )
