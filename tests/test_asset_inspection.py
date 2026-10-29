"""Synthetic offline GLBs: no acquired product bytes or network in this suite."""

import copy
import hashlib
import importlib.util
import json
import os
import socket
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.assets import furniture_from_catalog, load_catalog
from archimind.assets.inspection import (
    MAX_GLB_BYTES,
    AssetInspection,
    InspectionError,
    assess_scene_budget,
    inspect_furniture_asset,
)

ASSET_ID = "abo-b075x2x4xs-amazon-com"


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("external work forbidden")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(subprocess, "Popen", blocked)
    monkeypatch.setattr(os, "system", blocked)
    import openai

    monkeypatch.setattr(openai, "OpenAI", blocked)
    monkeypatch.setattr(openai, "AsyncOpenAI", blocked)


@pytest.fixture
def record():
    return load_catalog().get_record(ASSET_ID)


def glb(document, blob):
    document = copy.deepcopy(document)
    document["buffers"] = [{"byteLength": len(blob)}]
    header = json.dumps(document, separators=(",", ":")).encode()
    header += b" " * (-len(header) % 4)
    blob += b"\0" * (-len(blob) % 4)
    size = 28 + len(header) + len(blob)
    return (
        struct.pack("<4sII", b"glTF", 2, size)
        + struct.pack("<II", len(header), 0x4E4F534A)
        + header
        + struct.pack("<II", len(blob), 0x004E4942)
        + blob
    )


def duplicate_json_key(data):
    length = struct.unpack_from("<I", data, 12)[0]
    header = data[20 : 20 + length].rstrip(b" ")
    header = header.replace(b'"scene":0', b'"scene":0,"scene":0')
    header += b" " * (-len(header) % 4)
    binary_chunk = data[20 + length :]
    return (
        struct.pack("<4sII", b"glTF", 2, 20 + len(header) + len(binary_chunk))
        + struct.pack("<II", len(header), 0x4E4F534A)
        + header
        + binary_chunk
    )


def geometry(*, scale=1.0, triangles=12):
    # Eight corners, all referenced. glTF XYZ = width, height, depth.
    w, d, h = 0.9906 * scale, 0.9906 * scale, 0.9652 * scale
    points = [
        (x, y, z) for x in (-w / 2, w / 2) for y in (0, h) for z in (-d / 2, d / 2)
    ]
    indices = ([0, 1, 2, 1, 3, 2, 4, 6, 5, 5, 6, 7] * ((triangles + 3) // 4))[
        : triangles * 3
    ]
    positions = b"".join(struct.pack("<3f", *p) for p in points)
    blob = positions + struct.pack("<" + "H" * len(indices), *indices)
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 8},
            {
                "bufferView": 1,
                "componentType": 5123,
                "type": "SCALAR",
                "count": len(indices),
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
            {
                "buffer": 0,
                "byteOffset": len(positions),
                "byteLength": len(blob) - len(positions),
            },
        ],
    }
    return document, blob


def png(width=2, height=2):
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    # The inspector checks the container, not pixels. Large header-only fixtures
    # are intentional and must never be represented as successfully decoded.
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\0" + bytes(width * 4)))
        + chunk(b"IEND", b"")
    )


def with_images(document, blob, images, *, texture_count=None):
    document = copy.deepcopy(document)
    document["images"] = []
    for mime, image in images:
        blob += b"\0" * (-len(blob) % 4)
        index = len(document["bufferViews"])
        document["bufferViews"].append(
            {"buffer": 0, "byteOffset": len(blob), "byteLength": len(image)}
        )
        document["images"].append({"mimeType": mime, "bufferView": index})
        blob += image
    document["textures"] = [
        {"source": i % len(images)}
        for i in range(texture_count if texture_count is not None else len(images))
    ]
    return document, blob


def inspect(tmp_path, record, pair=None, **kwargs):
    document, blob = pair or geometry()
    path = tmp_path / "synthetic.glb"
    path.write_bytes(glb(document, blob))
    return inspect_furniture_asset(path, record, **kwargs)


def gates(report):
    return {g.name: g.status for g in report.gates}


def test_static_core_actual_bounds_and_no_automatic_approval(tmp_path, record):
    result = inspect(tmp_path, record)
    assert result.status == "automated_pass_visual_pending"
    assert not result.render_qualified
    assert all(g.status == "passed" for g in result.gates)
    assert result.physical_dimensions_wdh_m == (0.9906, 0.9906, 0.9652)
    assert result.native_bounds_three.size == pytest.approx((0.9906, 0.9652, 0.9906))
    assert result.canonical_mesh_bounds.min_xyz == pytest.approx((0, 0, 0), abs=1e-6)
    assert result.canonical_mesh_bounds.max_xyz == pytest.approx(
        (0.9906, 0.9906, 0.9652)
    )
    assert result.normalization_scale == 1
    assert result.placement_translation_three == (0.4953, 0, -0.4953)
    assert result.triangles_per_instance == 12
    assert (
        result.original_sha256
        == hashlib.sha256((tmp_path / "synthetic.glb").read_bytes()).hexdigest()
    )
    assert "image_pixel_decode" in result.deferred_checks
    assert AssetInspection.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        result.native_bounds_three.min_xyz = (0, 0, 0)
    with pytest.raises(ValidationError):
        result.render_qualified = True


def test_oversized_passes_agreement_but_fails_strict_containment(tmp_path, record):
    result = inspect(tmp_path, record, geometry(scale=1.01))
    assert gates(result)["physical_size_agreement"] == "passed"
    assert gates(result)["canonical_envelope"] == "failed"
    assert result.status == "rejected" and result.normalization_scale == 1


def test_undersized_passes_containment_but_fails_dimension_agreement(tmp_path, record):
    result = inspect(tmp_path, record, geometry(scale=0.5))
    assert gates(result)["canonical_envelope"] == "passed"
    assert gates(result)["physical_size_agreement"] == "failed"


def test_declared_accessor_bounds_do_not_override_actual_vertices(tmp_path, record):
    document, blob = geometry(scale=1.1)
    document["accessors"][0].update(min=[0, 0, 0], max=[0.1, 0.1, 0.1])
    result = inspect(tmp_path, record, (document, blob))
    assert result.native_bounds_three.size[0] > 1
    assert result.status == "rejected"


@pytest.mark.parametrize("matrix", [False, True])
def test_authored_translation_and_floor_center_anchor(tmp_path, record, matrix):
    document, blob = geometry()
    node = document["nodes"][0]
    if matrix:
        node["matrix"] = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 7, -2, 4, 1]
    else:
        node["translation"] = [7, -2, 4]
    result = inspect(tmp_path, record, (document, blob))
    assert result.normalization_translation_three == pytest.approx((-7, 2, -4))
    assert result.canonical_mesh_bounds.min_xyz == pytest.approx((0, 0, 0), abs=1e-6)
    assert result.status == "automated_pass_visual_pending"


def test_authored_scale_is_not_product_correction(tmp_path, record):
    document, blob = geometry(scale=0.5)
    document["nodes"][0]["scale"] = [2, 2, 2]
    result = inspect(tmp_path, record, (document, blob))
    assert result.status == "automated_pass_visual_pending"
    assert result.normalization_scale == 1
    assert result.authored_world_matrices_row_major[0][0] == 2


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(extensionsUsed=["KHR_draco_mesh_compression"]),
        lambda d: d.update(extensionsRequired=["KHR_texture_transform"]),
        lambda d: d["nodes"][0].update(extensions={"unknown": {}}),
        lambda d: d.update(animations=[{}]),
        lambda d: d.update(skins=[{}]),
        lambda d: d["nodes"][0].update(skin=0),
        lambda d: d["meshes"][0].update(weights=[0]),
        lambda d: d["meshes"][0]["primitives"][0].update(targets=[{}]),
        lambda d: d["meshes"][0]["primitives"][0].update(mode=1),
        lambda d: d["nodes"][0].update(children=[0]),
        lambda d: d["scenes"][0].update(nodes=[0, 0]),
        lambda d: d["nodes"][0].update(mesh=999),
        lambda d: d["nodes"].append({"mesh": 999}),
        lambda d: d["meshes"].append({"primitives": []}),
        lambda d: d["nodes"][0].update(scale=[0, 1, 1]),
        lambda d: d["nodes"][0].update(rotation=[0, 0, 0, 2]),
        lambda d: d["nodes"][0].update(translation=[float("nan"), 0, 0]),
        lambda d: d["nodes"][0].update(matrix=[0] * 16),
        lambda d: d["nodes"][0].update(
            matrix=[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        ),
        lambda d: d["bufferViews"][0].update(byteLength=10**9),
        lambda d: d["bufferViews"][0].update(byteOffset=-1),
        lambda d: d["bufferViews"][0].update(buffer=True),
        lambda d: d["bufferViews"][0].update(byteStride=3),
        lambda d: d["accessors"][0].update(count=10**8),
        lambda d: d["accessors"][0].update(byteOffset=2),
        lambda d: d["accessors"][0].update(bufferView=999),
        lambda d: d["accessors"][0].update(sparse={}),
        lambda d: d["accessors"][0].update(normalized=True),
        lambda d: d["accessors"][1].update(componentType=5126),
        lambda d: d["accessors"][1].update(count=35),
        lambda d: d.update(scene=False),
        lambda d: d.update(nodes=[{}] * 4097),
        lambda d: d.update(extras={"uri": "https://example.com/private-token"}),
        lambda d: d.update(images=[{"uri": "data:image/png;base64,AAAA"}]),
    ],
)
def test_malformed_references_and_unsupported_features(tmp_path, record, change):
    document, blob = geometry()
    change(document)
    with pytest.raises(InspectionError) as error:
        inspect(tmp_path, record, (document, blob))
    assert "private-token" not in str(error.value)


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b"nope" + b[4:],
        lambda b: b[:4] + struct.pack("<I", 1) + b[8:],
        lambda b: b[:-1],
        lambda b: b + b"\0\0\0\0",
        lambda b: b[:12] + struct.pack("<I", 1) + b[16:],
        duplicate_json_key,
    ],
)
def test_malformed_glb_container(tmp_path, record, change):
    path = tmp_path / "bad.glb"
    path.write_bytes(change(glb(*geometry())))
    with pytest.raises(InspectionError) as error:
        inspect_furniture_asset(path, record)
    if change is duplicate_json_key:
        assert str(error.value) == "duplicate_json_key"


@pytest.mark.parametrize("bad_value", [float("inf"), float("nan")])
def test_nonfinite_vertex_values(tmp_path, record, bad_value):
    document, blob = geometry()
    blob = struct.pack("<f", bad_value) + blob[4:]
    with pytest.raises(InspectionError, match="nonfinite_accessor"):
        inspect(tmp_path, record, (document, blob))


def test_invalid_triangle_index(tmp_path, record):
    document, blob = geometry()
    blob = blob[:96] + struct.pack("<H", 8) + blob[98:]
    with pytest.raises(InspectionError, match="invalid_index"):
        inspect(tmp_path, record, (document, blob))


@pytest.mark.parametrize("count,expected", [(100_000, "passed"), (100_001, "failed")])
def test_asset_triangle_budget(tmp_path, record, count, expected):
    result = inspect(tmp_path, record, geometry(triangles=count))
    assert result.triangles_per_instance == count
    assert gates(result)["asset_triangles"] == expected


@pytest.mark.parametrize(
    "dimension,expected", [(2048, "passed"), (2049, "failed"), (4096, "failed")]
)
def test_texture_dimension_budget_without_pixel_decode(
    tmp_path, record, dimension, expected
):
    document, blob = with_images(
        *geometry(), [("image/png", png(dimension, dimension))]
    )
    result = inspect(tmp_path, record, (document, blob))
    assert result.images[0].width == dimension
    assert gates(result)["texture_dimensions"] == expected
    assert "image_pixel_decode" in result.deferred_checks


def test_texture_memory_budget_and_shared_instance_accounting(tmp_path, record):
    pair = with_images(*geometry(), [("image/png", png(2048, 2048))] * 7)
    result = inspect(tmp_path, record, pair)
    assert gates(result)["decoded_texture_bytes"] == "failed"
    pair = with_images(*geometry(), [("image/png", png(2048, 2048))] * 3)
    result = inspect(tmp_path, record, pair)
    assert result.estimated_unique_texture_bytes == 67_108_860
    budget = assess_scene_budget(((result, 2), (result, 1)))
    assert budget.estimated_unique_texture_bytes == 67_108_860
    assert budget.unique_encoded_bytes == result.original_size_bytes
    assert budget.instantiated_triangles == result.triangles_per_instance * 3
    assert budget.passed


def test_shared_texture_entries_count_once(tmp_path, record):
    result = inspect(
        tmp_path,
        record,
        with_images(*geometry(), [("image/png", png(2048, 2048))], texture_count=7),
    )
    assert result.texture_count == 7
    assert result.estimated_unique_texture_bytes == 22_369_620
    assert gates(result)["decoded_texture_bytes"] == "passed"


def test_hierarchy_rotation_and_nonindexed_geometry(tmp_path, record):
    document, blob = geometry()
    document["nodes"] = [
        {"children": [1], "translation": [3, -2, 7]},
        {"mesh": 0, "rotation": [0, 1, 0, 0]},
    ]
    result = inspect(tmp_path, record, (document, blob))
    assert result.status == "automated_pass_visual_pending"
    assert result.mesh_instances == 1
    assert len(result.authored_world_matrices_row_major) == 2
    # A non-indexed triangle soup with the same eight-corner envelope.
    corners = [struct.unpack_from("<3f", blob, i * 12) for i in range(8)]
    points = corners + [corners[0]]
    blob = b"".join(struct.pack("<3f", *p) for p in points)
    document, _ = geometry()
    document["meshes"][0]["primitives"][0].pop("indices")
    document["accessors"] = [document["accessors"][0]]
    document["accessors"][0]["count"] = 9
    document["bufferViews"] = [{"buffer": 0, "byteLength": len(blob)}]
    assert inspect(tmp_path, record, (document, blob)).triangles_per_instance == 3


def test_unsupported_source_orientation_does_not_get_guessed(tmp_path, record):
    conventions = record.source_conventions.model_copy(update={"up": "+Z"})
    altered = record.model_copy(update={"source_conventions": conventions})
    with pytest.raises(InspectionError):
        inspect(tmp_path, altered)


@pytest.mark.parametrize(
    "image,mime",
    [
        (b"not png", "image/png"),
        (png()[:-1], "image/png"),
        (png()[:40] + b"X" + png()[41:], "image/png"),
        (b"\xff\xd8\xff\xd9", "image/jpeg"),
        (png(), "image/webp"),
    ],
)
def test_invalid_images(tmp_path, record, image, mime):
    with pytest.raises(InspectionError):
        inspect(tmp_path, record, with_images(*geometry(), [(mime, image)]))


def test_jpeg_header_dimensions_are_not_pixel_decode(tmp_path, record):
    jpeg = (
        b"\xff\xd8\xff\xc0\x00\x0b\x08"
        + struct.pack(">HH", 32, 64)
        + b"\x01\x01\x11\x00\xff\xda\x00\x02\xff\xd9"
    )
    result = inspect(tmp_path, record, with_images(*geometry(), [("image/jpeg", jpeg)]))
    assert (result.images[0].width, result.images[0].height) == (64, 32)
    assert result.images[0].container_check == "jpeg_headers_eoi"


@pytest.mark.parametrize("field,value", [("source", 99), ("sampler", 99)])
def test_invalid_texture_reference(tmp_path, record, field, value):
    document, blob = with_images(*geometry(), [("image/png", png())])
    document["textures"][0][field] = value
    with pytest.raises(InspectionError):
        inspect(tmp_path, record, (document, blob))


def test_material_texture_requires_valid_coordinates(tmp_path, record):
    document, blob = with_images(*geometry(), [("image/png", png())])
    document["materials"] = [
        {"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}
    ]
    document["meshes"][0]["primitives"][0]["material"] = 0
    with pytest.raises(InspectionError, match="missing_texture_coordinates"):
        inspect(tmp_path, record, (document, blob))


@pytest.mark.parametrize(
    "field,limit,gate",
    [
        ("original_size_bytes", 50 * 1024**2, "unique_encoded_scene_bytes"),
        (
            "estimated_unique_texture_bytes",
            128 * 1024**2,
            "unique_decoded_scene_texture_bytes",
        ),
        ("triangles_per_instance", 300_000, "instantiated_scene_triangles"),
    ],
)
def test_aggregate_limits_at_and_beyond_threshold(tmp_path, record, field, limit, gate):
    result = inspect(tmp_path, record)
    # Synthetic resource-only boundary records, not qualification evidence.
    at = result.model_copy(update={field: limit})
    over = result.model_copy(update={field: limit + 1})
    assert gates(assess_scene_budget(((at, 1),)))[gate] == "passed"
    assert gates(assess_scene_budget(((over, 1),)))[gate] == "failed"
    other = result.model_copy(update={"asset_id": "another", field: 1})
    assert gates(assess_scene_budget(((at, 1), (other, 1))))[gate] == "failed"


def test_conflicting_scene_inspections_and_invalid_instances(tmp_path, record):
    result = inspect(tmp_path, record)
    conflicting = result.model_copy(update={"original_sha256": "0" * 64})
    with pytest.raises(InspectionError, match="conflicting"):
        assess_scene_budget(((result, 1), (conflicting, 1)))
    for count in (0, -1, True, 1.5):
        with pytest.raises(InspectionError):
            assess_scene_budget(((result, count),))


def test_local_hash_and_safe_file_errors(tmp_path, record):
    path = tmp_path / "synthetic.glb"
    path.write_bytes(glb(*geometry()))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert inspect_furniture_asset(
        path, record, expected_sha256=expected
    ).expected_hash_checked
    for digest in ("0" * 64, "ETag", "../secret"):
        with pytest.raises(InspectionError):
            inspect_furniture_asset(path, record, expected_sha256=digest)
    link = tmp_path / "link.glb"
    link.symlink_to(path)
    for invalid in (link, tmp_path / "SECRET_PATH", tmp_path):
        with pytest.raises(InspectionError) as error:
            inspect_furniture_asset(invalid, record)
        assert str(tmp_path) not in str(error.value)
    path.write_bytes(b"")
    with pytest.raises(InspectionError, match="encoded_asset_limit"):
        inspect_furniture_asset(path, record)
    with path.open("wb") as stream:
        stream.truncate(MAX_GLB_BYTES + 1)
    with pytest.raises(InspectionError, match="encoded_asset_limit"):
        inspect_furniture_asset(path, record)
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(InspectionError, match="not_regular_file"):
        inspect_furniture_asset(fifo, record)


def test_cli_exit_codes_and_sanitization(tmp_path, record, monkeypatch, capsys):
    source = Path(__file__).resolve().parents[1] / "scripts/inspect_furniture_assets.py"
    spec = importlib.util.spec_from_file_location("inspection_cli", source)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    path = tmp_path / "input.glb"
    args = [str(source), "--asset-id", ASSET_ID, "--file", str(path)]
    monkeypatch.setattr(sys, "argv", args)
    for scale, expected in ((1, 0), (1.01, 2)):
        path.write_bytes(glb(*geometry(scale=scale)))
        assert cli.main() == expected
        assert json.loads(capsys.readouterr().out)["render_qualified"] is False
    path.write_bytes(b"SECRET_TOKEN")
    assert cli.main() == 1
    output = capsys.readouterr().out
    assert "SECRET_TOKEN" not in output and str(path) not in output
    args[2] = "unknown"
    assert cli.main() == 1
    assert (
        json.loads(capsys.readouterr().out)["error_code"] == "invalid_catalog_reference"
    )


def test_reports_deterministic_inputs_catalog_geometry_and_placeholder_unchanged(
    tmp_path, record, monkeypatch
):
    from archimind.examples.sample_realistic_room import create_sample_realistic_room
    from archimind.geometry.accessibility import validate_accessibility
    from archimind.render import realistic_scene, realistic_viewer

    design = create_sample_realistic_room()
    design.furniture[0] = furniture_from_catalog(
        ASSET_ID, furniture_id="charles", name="Charles", x_m=1, y_m=0.95
    )
    before, metadata = design.model_dump_json(), record.model_dump_json()
    validation = validate_accessibility(design).model_dump_json()
    result = inspect(tmp_path, record, geometry(scale=1.01))
    assert inspect(tmp_path, record, geometry(scale=1.01)) == result
    mount, verify = Mock(), Mock(side_effect=AssertionError("no asset allowed"))
    monkeypatch.setattr(realistic_viewer, "verify_asset", verify)
    monkeypatch.setattr(realistic_viewer, "_component", lambda: mount)
    bindings = {f.id: None for f in design.furniture}
    realistic_scene.render_realistic_scene(design, asset_bindings=bindings)
    verify.assert_not_called()
    payload = mount.call_args.kwargs["data"]
    assert all(b["asset_id"] is None for b in payload["asset_bindings"])
    assert payload["design"] == design.model_dump(mode="json")
    assert design.model_dump_json() == before
    assert record.model_dump_json() == metadata
    assert validate_accessibility(design).model_dump_json() == validation
    assert {f.id: None for f in design.furniture} == bindings
    assert load_catalog(version="1.0.0").catalog_version == "1.0.0"
    assert all(not r.render_qualified for r in load_catalog().records)
