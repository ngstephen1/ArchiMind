"""Bounded GLB inspection on synthetic files (no real assets in CI)."""

import json
import math
import struct

import pytest

from archimind.datasets.glb import inspect_glb
from archimind.datasets.safe_io import UnsafeContentError

PNG_64x32 = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 64, 32)


def write_glb(path, doc, binary=b""):
    body = json.dumps(doc).encode()
    body += b" " * (-len(body) % 4)
    chunks = struct.pack("<II", len(body), 0x4E4F534A) + body
    if binary:
        binary += b"\x00" * (-len(binary) % 4)
        chunks += struct.pack("<II", len(binary), 0x004E4942) + binary
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(chunks)) + chunks)
    return path


def box_doc(nodes, *, count=36, mode=None, indices=True):
    prim = {"attributes": {"POSITION": 0}}
    if indices:
        prim["indices"] = 1
    if mode is not None:
        prim["mode"] = mode
    return {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
        "meshes": [{"primitives": [prim]}],
        "accessors": [
            {"count": 8, "min": [-0.5, 0.0, -0.25], "max": [0.5, 1.0, 0.25]},
            {"count": count},
        ],
    }


def test_identity_box_bounds_and_triangles(tmp_path):
    summary = inspect_glb(write_glb(tmp_path / "a.glb", box_doc([{"mesh": 0}])))
    assert summary.world_min == (-0.5, 0.0, -0.25)
    assert summary.world_max == (0.5, 1.0, 0.25)
    assert summary.triangles == 12
    assert summary.transformed_nodes == 0
    assert summary.max_texture_px == 0


def test_parent_translation_and_child_quarter_turn_are_applied(tmp_path):
    half = math.sqrt(0.5)
    nodes = [
        {"translation": [2.0, 0.0, 3.0], "children": [1]},
        {"rotation": [0.0, half, 0.0, half], "mesh": 0},  # +90 deg about y
    ]
    summary = inspect_glb(write_glb(tmp_path / "t.glb", box_doc(nodes)))
    lo, hi = summary.world_min, summary.world_max
    # A quarter turn swaps the x and z extents; the parent moves the box.
    assert [round(v, 9) for v in lo] == [1.75, 0.0, 2.5]
    assert [round(v, 9) for v in hi] == [2.25, 1.0, 3.5]
    assert summary.transformed_nodes == 2


def test_matrix_node_scale(tmp_path):
    matrix = [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1]
    summary = inspect_glb(
        write_glb(tmp_path / "m.glb", box_doc([{"matrix": matrix, "mesh": 0}]))
    )
    assert summary.size == (2.0, 2.0, 1.0)


def test_non_triangle_primitives_are_counted_not_triangulated(tmp_path):
    doc = box_doc([{"mesh": 0}], mode=1)
    summary = inspect_glb(write_glb(tmp_path / "l.glb", doc))
    assert summary.triangles == 0 and summary.non_triangle_primitives == 1


def test_embedded_png_size_is_read_from_its_header(tmp_path):
    doc = box_doc([{"mesh": 0}])
    doc["bufferViews"] = [{"buffer": 0, "byteOffset": 0, "byteLength": len(PNG_64x32)}]
    doc["buffers"] = [{"byteLength": len(PNG_64x32)}]
    doc["images"] = [{"bufferView": 0, "mimeType": "image/png"}]
    summary = inspect_glb(write_glb(tmp_path / "i.glb", doc, PNG_64x32))
    assert summary.images == 1 and summary.max_texture_px == 64


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: (
            d["nodes"].append({"children": [0]}) or d["nodes"][0].update(children=[1])
        ),
        lambda d: d["nodes"][0].update(matrix=[1] * 16, translation=[0, 0, 0]),
        lambda d: d["nodes"][0].update(rotation=[0, 0, 0, 2]),
        lambda d: d["nodes"][0].update(translation=[0, "x", 0]),
        lambda d: d["accessors"][0].pop("min"),
        lambda d: d["accessors"][1].update(count=10),
        lambda d: d["nodes"][0].update(mesh=5),
        lambda d: d["scenes"][0].update(nodes=[9]),
        lambda d: d.update(buffers=[{"uri": "https://example.com/x.bin"}]),
        lambda d: d.update(meshes=[{"primitives": []}]),
    ],
)
def test_unsafe_or_malformed_glbs_are_rejected(tmp_path, mutate):
    doc = box_doc([{"mesh": 0}])
    mutate(doc)
    with pytest.raises(UnsafeContentError):
        inspect_glb(write_glb(tmp_path / "bad.glb", doc))


def test_byte_limit(tmp_path):
    path = write_glb(tmp_path / "big.glb", box_doc([{"mesh": 0}]))
    with pytest.raises(UnsafeContentError):
        inspect_glb(path, max_bytes=16)
