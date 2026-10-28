"""Bounded offline inspection of static embedded GLB assets.

This is a supported-subset inspector, not a full glTF validator or image decoder.
It never fetches resources, edits a model, fits it to a box, or grants rendering
approval. Authored node transforms are applied; the added metric normalization
is identity orientation/scale plus a fixed center/floor anchor. Actual image
decoding, natural-front semantics and materials still require visual review.
"""

import hashlib
import json
import math
import os
import re
import stat
import struct
import zlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, FiniteFloat, StrictInt

from archimind.assets.catalog import FurnitureAssetRecord

MAX_GLB_BYTES = 15 * 1024 * 1024
MAX_SCENE_BYTES = 50 * 1024 * 1024
MAX_ASSET_TRIANGLES = 100_000
MAX_SCENE_TRIANGLES = 300_000
MAX_TEXTURE_DIMENSION = 2048
MAX_TEXTURE_BYTES = 128 * 1024 * 1024
ENVELOPE_TOLERANCE_M = 1e-6
# Core glTF only. Extension names are not evidence of implemented semantics.
_SUPPORTED_EXTENSIONS = frozenset()
MAX_ITEMS = 4096
MAX_DECODED_COMPONENTS = 4_000_000
MAX_VERTEX_VISITS = 1_000_000
_COMPONENTS = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
_WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
Vector = tuple[FiniteFloat, FiniteFloat, FiniteFloat]


class InspectionError(ValueError):
    """Fixed diagnostic code; never includes a filesystem path or source payload."""


def _require(condition, code="invalid_glb"):
    if not condition:
        raise InspectionError(code)


class _Report(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class Bounds(_Report):
    min_xyz: Vector
    max_xyz: Vector

    @property
    def size(self) -> tuple[float, float, float]:
        return tuple(b - a for a, b in zip(self.min_xyz, self.max_xyz))


class ImageInspection(_Report):
    image_index: StrictInt
    mime_type: Literal["image/png", "image/jpeg"]
    width: StrictInt
    height: StrictInt
    container_check: Literal["png_chunks_crc", "jpeg_headers_eoi"]


class Gate(_Report):
    name: str
    status: Literal["passed", "failed"]


class AssetInspection(_Report):
    schema_version: Literal[1] = 1
    status: Literal["rejected", "automated_pass_visual_pending"]
    render_qualified: Literal[False] = False
    asset_id: str
    asset_version: str
    source_product_id: str
    source_model_id: str
    source_model_url: str
    original_size_bytes: StrictInt
    original_sha256: str
    expected_hash_checked: bool
    gltf_version: Literal["2.0"] = "2.0"
    units: Literal["glTF_meters_convention"] = "glTF_meters_convention"
    native_bounds_three: Bounds
    normalized_bounds_three: Bounds
    canonical_mesh_bounds: Bounds
    canonical_envelope: Bounds
    physical_dimensions_wdh_m: Vector
    dimension_deltas_wdh_m: Vector
    dimension_tolerances_wdh_m: Vector
    normalization_scale: Literal[1.0] = 1.0
    normalization_orientation: Literal["identity_Y_up_Z_front_source_convention"] = (
        "identity_Y_up_Z_front_source_convention"
    )
    normalization_translation_three: Vector
    placement_translation_three: Vector
    authored_world_matrices_row_major: tuple[tuple[FiniteFloat, ...], ...]
    mesh_definitions: StrictInt
    mesh_instances: StrictInt
    primitive_instances: StrictInt
    triangles_per_instance: StrictInt
    material_count: StrictInt
    texture_count: StrictInt
    images: tuple[ImageInspection, ...]
    estimated_unique_texture_bytes: StrictInt
    extensions_used: tuple[str, ...]
    extensions_required: tuple[str, ...]
    external_resources: Literal[False] = False
    gates: tuple[Gate, ...]
    deferred_checks: tuple[str, ...] = (
        "image_pixel_decode",
        "natural_front_visual_confirmation",
        "material_visual_review",
        "renderer_compatibility",
        "device_performance",
    )


class SceneBudget(_Report):
    """Resource assessment only; a pass cannot approve an inspected product."""

    passed: bool
    unique_encoded_bytes: StrictInt
    instantiated_triangles: StrictInt
    estimated_unique_texture_bytes: StrictInt
    gates: tuple[Gate, ...]


def _integer(value, minimum=0):
    _require(type(value) is int and value >= minimum)
    return value


def _number(value):
    _require(type(value) in (int, float) and math.isfinite(value))
    return float(value)


def _vector(value, count):
    _require(type(value) is list and len(value) == count)
    return tuple(_number(v) for v in value)


def _reference(values, index):
    _integer(index)
    _require(index < len(values))
    return values[index]


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise InspectionError("nonfinite_json")


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)
    elif isinstance(value, float):
        _require(math.isfinite(value), "nonfinite_json")


def _document(data):
    _require(len(data) >= 28)
    magic, version, size = struct.unpack_from("<4sII", data)
    _require(magic == b"glTF" and version == 2 and size == len(data))
    chunks = []
    offset = 12
    while offset < size:
        _require(offset + 8 <= size)
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        _require(length > 0 and length % 4 == 0 and offset + length <= size)
        chunks.append((kind, memoryview(data)[offset : offset + length]))
        offset += length
    _require(
        len(chunks) == 2 and chunks[0][0] == 0x4E4F534A and chunks[1][0] == 0x004E4942
    )
    document = json.loads(
        bytes(chunks[0][1]),
        object_pairs_hook=_object,
        parse_constant=_invalid_constant,
    )
    _require(document["asset"]["version"] == "2.0")
    _require(document["asset"].get("minVersion", "2.0") == "2.0")
    used = document.get("extensionsUsed", [])
    required = document.get("extensionsRequired", [])
    _require(type(used) is list and type(required) is list)
    _require(len(set(used)) == len(used) and len(set(required)) == len(required))
    _require(all(type(x) is str for x in used + required))
    _require(
        set(required) <= set(used) <= _SUPPORTED_EXTENSIONS, "unsupported_extension"
    )
    for obj in _walk(document):
        _require("uri" not in obj, "external_or_uri_resource")
        if "extensions" in obj:
            _require(type(obj["extensions"]) is dict)
            _require(set(obj["extensions"]) <= set(used), "undeclared_extension")
    for key in (
        "bufferViews",
        "accessors",
        "nodes",
        "meshes",
        "images",
        "textures",
        "materials",
        "samplers",
    ):
        items = document.get(key, [])
        _require(
            type(items) is list and len(items) <= MAX_ITEMS, "inspection_work_limit"
        )
    _require(
        not document.get("animations") and not document.get("skins"),
        "unsupported_deformation",
    )
    buffers = document["buffers"]
    _require(len(buffers) == 1)
    length = _integer(buffers[0]["byteLength"], 1)
    _require(0 <= len(chunks[1][1]) - length <= 3)
    _require(not any(chunks[1][1][length:]))
    blob = chunks[1][1][:length]
    views = []
    for view in document["bufferViews"]:
        _require(_integer(view.get("buffer", 0)) == 0)
        start = _integer(view.get("byteOffset", 0))
        length = _integer(view["byteLength"], 1)
        _require(start + length <= len(blob))
        stride = view.get("byteStride")
        if stride is not None:
            _require(type(stride) is int and 4 <= stride <= 252 and stride % 4 == 0)
        views.append(blob[start : start + length])
    return document, views


def _accessors(document, views):
    values = []
    decoded_components = 0
    for accessor in document["accessors"]:
        _require("sparse" not in accessor, "unsupported_sparse_accessor")
        component = accessor["componentType"]
        _require(type(component) is int and component in _COMPONENTS)
        _require(accessor["type"] in _WIDTHS)
        code, size = _COMPONENTS[component]
        width = _WIDTHS[accessor["type"]]
        count = _integer(accessor["count"], 1)
        decoded_components += count * width
        _require(decoded_components <= MAX_DECODED_COMPONENTS, "inspection_work_limit")
        view_index = _integer(accessor["bufferView"])
        view = _reference(views, view_index)
        stride = document["bufferViews"][view_index].get("byteStride", size * width)
        start = _integer(accessor.get("byteOffset", 0))
        absolute = start + document["bufferViews"][view_index].get("byteOffset", 0)
        _require(start % size == absolute % size == stride % size == 0)
        _require(
            stride >= size * width
            and start + (count - 1) * stride + size * width <= len(view)
        )
        decoded = tuple(
            struct.unpack_from("<" + code * width, view, start + i * stride)
            for i in range(count)
        )
        _require(
            all(math.isfinite(v) for row in decoded for v in row), "nonfinite_accessor"
        )
        values.append(decoded)
    return values


def _multiply(a, b):
    return tuple(
        sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
        for r in range(4)
        for c in range(4)
    )


def _matrix(node):
    if "matrix" in node:
        _require(not any(k in node for k in ("translation", "rotation", "scale")))
        m = _vector(node["matrix"], 16)
        m = tuple(m[c * 4 + r] for r in range(4) for c in range(4))
        _require(m[12:] == (0.0, 0.0, 0.0, 1.0), "non_affine_transform")
        determinant = (
            m[0] * (m[5] * m[10] - m[6] * m[9])
            - m[1] * (m[4] * m[10] - m[6] * m[8])
            + m[2] * (m[4] * m[9] - m[5] * m[8])
        )
        _require(
            math.isfinite(determinant) and determinant != 0, "degenerate_transform"
        )
        return m
    t = _vector(node.get("translation", [0, 0, 0]), 3)
    s = _vector(node.get("scale", [1, 1, 1]), 3)
    _require(all(v != 0 for v in s), "degenerate_transform")
    x, y, z, w = _vector(node.get("rotation", [0, 0, 0, 1]), 4)
    _require(abs(x * x + y * y + z * z + w * w - 1) <= 1e-6, "invalid_quaternion")
    return (
        (1 - 2 * (y * y + z * z)) * s[0],
        2 * (x * y - z * w) * s[1],
        2 * (x * z + y * w) * s[2],
        t[0],
        2 * (x * y + z * w) * s[0],
        (1 - 2 * (x * x + z * z)) * s[1],
        2 * (y * z - x * w) * s[2],
        t[1],
        2 * (x * z - y * w) * s[0],
        2 * (y * z + x * w) * s[1],
        (1 - 2 * (x * x + y * y)) * s[2],
        t[2],
        0.0,
        0.0,
        0.0,
        1.0,
    )


def _geometry(document, values):
    _require(
        len(document["scenes"]) == 1 and _integer(document.get("scene", 0)) == 0,
        "unsupported_scene_selection",
    )
    meshes, nodes = document["meshes"], document["nodes"]
    _require(meshes and nodes)
    low, high = [math.inf] * 3, [-math.inf] * 3
    seen, used_meshes, matrices = set(), set(), []
    mesh_instances = primitives = triangles = vertex_visits = 0
    identity = (
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

    def visit(index, parent):
        nonlocal mesh_instances, primitives, triangles, vertex_visits
        node = _reference(nodes, index)
        _require(index not in seen, "cyclic_or_shared_node")
        seen.add(index)
        _require(
            "skin" not in node and "weights" not in node, "unsupported_deformation"
        )
        world = _multiply(parent, _matrix(node))
        _require(all(math.isfinite(v) for v in world), "nonfinite_transform")
        matrices.append(world)
        if "mesh" in node:
            mesh = _reference(meshes, node["mesh"])
            used_meshes.add(node["mesh"])
            _require("weights" not in mesh, "unsupported_deformation")
            mesh_instances += 1
            _require(mesh["primitives"])
            for primitive in mesh["primitives"]:
                _require(not primitive.get("targets"), "unsupported_deformation")
                _require(primitive.get("mode", 4) == 4, "unsupported_primitive")
                attributes = primitive["attributes"]
                position_id = attributes["POSITION"]
                position_accessor = _reference(document["accessors"], position_id)
                _require(
                    position_accessor["type"] == "VEC3"
                    and position_accessor["componentType"] == 5126
                )
                _require(not position_accessor.get("normalized", False))
                positions = _reference(values, position_id)
                vertex_visits += len(positions)
                _require(vertex_visits <= MAX_VERTEX_VISITS, "inspection_work_limit")
                for attr in attributes.values():
                    _require(len(_reference(values, attr)) == len(positions))
                if "indices" in primitive:
                    accessor = _reference(document["accessors"], primitive["indices"])
                    _require(
                        accessor["type"] == "SCALAR"
                        and accessor["componentType"] in (5121, 5123, 5125)
                    )
                    _require(not accessor.get("normalized", False))
                    indices = _reference(values, primitive["indices"])
                    _require(
                        all(0 <= row[0] < len(positions) for row in indices),
                        "invalid_index",
                    )
                    count = len(indices)
                else:
                    count = len(positions)
                _require(count % 3 == 0, "invalid_triangle_count")
                triangles += count // 3
                primitives += 1
                if "material" in primitive:
                    material = _reference(
                        document.get("materials", []), primitive["material"]
                    )
                    for obj in _walk(material):
                        for key, texture in obj.items():
                            if key.endswith("Texture") and isinstance(texture, dict):
                                _reference(
                                    document.get("textures", []), texture["index"]
                                )
                                coord = texture.get("texCoord", 0)
                                _integer(coord)
                                _require(
                                    f"TEXCOORD_{coord}" in attributes,
                                    "missing_texture_coordinates",
                                )
                # Decode positions, not accessor min/max. Include unused positions
                # conservatively, matching the geometry's complete vertex envelope.
                for point in positions:
                    p = tuple(
                        sum(world[r * 4 + k] * point[k] for k in range(3))
                        + world[r * 4 + 3]
                        for r in range(3)
                    )
                    _require(all(math.isfinite(v) for v in p), "nonfinite_position")
                    for axis in range(3):
                        low[axis], high[axis] = (
                            min(low[axis], p[axis]),
                            max(high[axis], p[axis]),
                        )
        for child in node.get("children", []):
            visit(child, world)

    for index in document["scenes"][0]["nodes"]:
        visit(index, identity)
    _require(
        len(seen) == len(nodes) and len(used_meshes) == len(meshes),
        "unused_scene_geometry",
    )
    _require(mesh_instances > 0 and triangles > 0, "empty_geometry")
    _require(all(b > a for a, b in zip(low, high)), "degenerate_bounds")
    return (
        Bounds(min_xyz=tuple(low), max_xyz=tuple(high)),
        mesh_instances,
        primitives,
        triangles,
        tuple(matrices),
    )


def _image_size(data, mime):
    if mime == "image/png":
        _require(bytes(data[:8]) == b"\x89PNG\r\n\x1a\n", "invalid_image")
        offset, dimensions, idat, ended = 8, None, False, False
        while offset < len(data):
            _require(offset + 12 <= len(data), "invalid_image")
            size = struct.unpack_from(">I", data, offset)[0]
            kind = bytes(data[offset + 4 : offset + 8])
            _require(offset + size + 12 <= len(data), "invalid_image")
            payload = data[offset + 8 : offset + 8 + size]
            crc = zlib.crc32(payload, zlib.crc32(kind)) & 0xFFFFFFFF
            _require(
                crc == struct.unpack_from(">I", data, offset + 8 + size)[0],
                "invalid_image_crc",
            )
            if offset == 8:
                _require(kind == b"IHDR" and size == 13, "invalid_image")
                dimensions = struct.unpack_from(">II", payload)
                depth, color, compression, filtering, interlace = struct.unpack_from(
                    "5B", payload, 8
                )
                allowed_depths = {
                    0: (1, 2, 4, 8, 16),
                    2: (8, 16),
                    3: (1, 2, 4, 8),
                    4: (8, 16),
                    6: (8, 16),
                }
                _require(
                    depth in allowed_depths.get(color, ())
                    and compression == filtering == 0
                    and interlace in (0, 1),
                    "unsupported_image",
                )
            elif kind == b"IHDR":
                raise InspectionError("invalid_image")
            if kind == b"IDAT":
                idat = True
            offset += size + 12
            if kind == b"IEND":
                _require(size == 0 and offset == len(data), "invalid_image")
                ended = True
                break
        _require(
            dimensions is not None and idat and ended and min(dimensions) > 0,
            "invalid_image",
        )
        return *dimensions, "png_chunks_crc"
    _require(
        mime == "image/jpeg"
        and bytes(data[:2]) == b"\xff\xd8"
        and bytes(data[-2:]) == b"\xff\xd9",
        "invalid_image",
    )
    offset, dimensions = 2, None
    while offset < len(data) - 2:
        _require(data[offset] == 0xFF, "invalid_image")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        _require(offset < len(data), "invalid_image")
        marker = data[offset]
        offset += 1
        _require(offset + 2 <= len(data), "invalid_image")
        size = struct.unpack_from(">H", data, offset)[0]
        _require(size >= 2 and offset + size <= len(data), "invalid_image")
        if marker in (0xC0, 0xC1, 0xC2):
            _require(size >= 8 and data[offset + 2] == 8, "unsupported_image")
            h, w = struct.unpack_from(">HH", data, offset + 3)
            _require(
                data[offset + 7] in (1, 3) and w > 0 and h > 0, "unsupported_image"
            )
            dimensions = (w, h)
        if marker == 0xDA:
            _require(dimensions is not None, "invalid_image")
            return *dimensions, "jpeg_headers_eoi"
        offset += size
    raise InspectionError("invalid_image")


def _mipmap_bytes(width, height):
    total = 0
    while True:
        total += width * height * 4
        if width == height == 1:
            return total
        width, height = max(1, width // 2), max(1, height // 2)


def _images(document, views):
    images = []
    for index, image in enumerate(document.get("images", [])):
        mime = image["mimeType"]
        _require(mime in ("image/png", "image/jpeg"), "unsupported_image")
        width, height, checked = _image_size(
            _reference(views, image["bufferView"]), mime
        )
        images.append(
            ImageInspection(
                image_index=index,
                mime_type=mime,
                width=width,
                height=height,
                container_check=checked,
            )
        )
    texture_bytes = 0
    shared = set()
    samplers = document.get("samplers", [])
    for texture in document.get("textures", []):
        image = _reference(images, texture["source"])
        if "sampler" in texture:
            _reference(samplers, texture["sampler"])
        key = (image.image_index, texture.get("sampler"))
        if key not in shared:
            shared.add(key)
            texture_bytes += _mipmap_bytes(image.width, image.height)
    return tuple(images), texture_bytes


def _read_local(path):
    path = Path(path)
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            _require(stat.S_ISREG(info.st_mode), "not_regular_file")
            _require(0 < info.st_size <= MAX_GLB_BYTES, "encoded_asset_limit")
            data = stream.read(MAX_GLB_BYTES + 1)
            _require(
                len(data) == info.st_size and len(data) <= MAX_GLB_BYTES,
                "asset_changed_or_oversized",
            )
            return data
    except OSError:
        raise InspectionError("asset_unavailable") from None


def inspect_furniture_asset(
    path: Path, record: FurnitureAssetRecord, *, expected_sha256: str | None = None
) -> AssetInspection:
    """Inspect one explicit local asset. A passing result still needs visual review."""
    try:
        record = FurnitureAssetRecord.model_validate(record)
        _require(
            (
                record.source_conventions.units,
                record.source_conventions.up,
                record.source_conventions.front,
            )
            == ("meters", "+Y", "+Z"),
            "unsupported_source_conventions",
        )
        data = _read_local(path)
        digest = hashlib.sha256(data).hexdigest()
        if expected_sha256 is not None:
            _require(
                type(expected_sha256) is str
                and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
                "invalid_expected_hash",
            )
            _require(digest == expected_sha256, "hash_mismatch")
        document, views = _document(data)
        values = _accessors(document, views)
        native, meshes, primitives, triangles, matrices = _geometry(document, values)
        images, texture_bytes = _images(document, views)
        w, d, h = (
            record.dimensions.width_m,
            record.dimensions.depth_m,
            record.dimensions.height_m,
        )
        translation = tuple(
            -((a + b) / 2) if i != 1 else -a
            for i, (a, b) in enumerate(zip(native.min_xyz, native.max_xyz))
        )
        low = tuple(a + t for a, t in zip(native.min_xyz, translation))
        high = tuple(b + t for b, t in zip(native.max_xyz, translation))
        normalized = Bounds(min_xyz=low, max_xyz=high)
        canonical = Bounds(
            min_xyz=(low[0] + w / 2, -high[2] + d / 2, low[1]),
            max_xyz=(high[0] + w / 2, -low[2] + d / 2, high[1]),
        )
        envelope = Bounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(w, d, h))
        native_wdh = (native.size[0], native.size[2], native.size[1])
        deltas = tuple(a - b for a, b in zip(native_wdh, (w, d, h)))
        tolerances = tuple(max(0.01, 0.02 * v) for v in (w, d, h))
        checks = [
            (
                "physical_size_agreement",
                all(abs(v) <= t for v, t in zip(deltas, tolerances)),
            ),
            (
                "canonical_envelope",
                all(
                    a >= -ENVELOPE_TOLERANCE_M and b <= limit + ENVELOPE_TOLERANCE_M
                    for a, b, limit in zip(
                        canonical.min_xyz, canonical.max_xyz, (w, d, h)
                    )
                ),
            ),
            ("encoded_asset_bytes", len(data) <= MAX_GLB_BYTES),
            ("asset_triangles", triangles <= MAX_ASSET_TRIANGLES),
            (
                "texture_dimensions",
                all(max(i.width, i.height) <= MAX_TEXTURE_DIMENSION for i in images),
            ),
            ("decoded_texture_bytes", texture_bytes <= MAX_TEXTURE_BYTES),
        ]
        return AssetInspection(
            status="automated_pass_visual_pending"
            if all(v for _, v in checks)
            else "rejected",
            asset_id=record.asset_id,
            asset_version=record.asset_version,
            source_product_id=record.source.product_id,
            source_model_id=record.source.model_id,
            source_model_url=record.source.model_url,
            original_size_bytes=len(data),
            original_sha256=digest,
            expected_hash_checked=expected_sha256 is not None,
            native_bounds_three=native,
            normalized_bounds_three=normalized,
            canonical_mesh_bounds=canonical,
            canonical_envelope=envelope,
            physical_dimensions_wdh_m=(w, d, h),
            dimension_deltas_wdh_m=deltas,
            dimension_tolerances_wdh_m=tolerances,
            normalization_translation_three=translation,
            placement_translation_three=(w / 2, 0.0, -d / 2),
            authored_world_matrices_row_major=matrices,
            mesh_definitions=len(document["meshes"]),
            mesh_instances=meshes,
            primitive_instances=primitives,
            triangles_per_instance=triangles,
            material_count=len(document.get("materials", [])),
            texture_count=len(document.get("textures", [])),
            images=images,
            estimated_unique_texture_bytes=texture_bytes,
            extensions_used=tuple(sorted(document.get("extensionsUsed", []))),
            extensions_required=tuple(sorted(document.get("extensionsRequired", []))),
            gates=tuple(
                Gate(name=name, status="passed" if passed else "failed")
                for name, passed in checks
            ),
        )
    except InspectionError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        OverflowError,
        RecursionError,
        struct.error,
    ):
        raise InspectionError("malformed_or_unsupported_glb") from None


def assess_scene_budget(
    requests: tuple[tuple[AssetInspection, int], ...],
) -> SceneBudget:
    """Count each loaded asset once, but count triangles for every instance."""
    unique = {}
    triangles = 0
    for report, count in requests:
        _require(isinstance(report, AssetInspection), "invalid_scene_request")
        _integer(count, 1)
        key = report.asset_id
        if key in unique:
            _require(unique[key] == report, "conflicting_asset_inspection")
        unique[key] = report
        triangles += report.triangles_per_instance * count
    encoded = sum(r.original_size_bytes for r in unique.values())
    textures = sum(r.estimated_unique_texture_bytes for r in unique.values())
    checks = [
        ("unique_encoded_scene_bytes", encoded <= MAX_SCENE_BYTES),
        ("instantiated_scene_triangles", triangles <= MAX_SCENE_TRIANGLES),
        ("unique_decoded_scene_texture_bytes", textures <= MAX_TEXTURE_BYTES),
    ]
    return SceneBudget(
        passed=all(v for _, v in checks),
        unique_encoded_bytes=encoded,
        instantiated_triangles=triangles,
        estimated_unique_texture_bytes=textures,
        gates=tuple(
            Gate(name=n, status="passed" if v else "failed") for n, v in checks
        ),
    )
