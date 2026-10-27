"""Offline checks for one allowlisted GLB, provenance and trusted viewer data."""

import hashlib
import json
import struct
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.examples.sample_chair import create_sample_chair
from archimind.render import realistic_viewer as viewer


def test_asset_provenance_file_and_model_license():
    metadata = viewer.verify_asset()
    path = viewer.asset_path()
    assert metadata["creator"] == "Eric Chadwick"
    assert metadata["copyright"] == "2020 Wayfair, LLC"
    assert metadata["license"] == "CC0-1.0"
    assert metadata["download_date"] == "2026-10-27"
    assert metadata["size_bytes"] == path.stat().st_size == 4125648
    assert path.stat().st_size < viewer.MAX_ASSET_BYTES
    assert metadata["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert metadata["source_commit"] in metadata["download_url"]
    for name in ("README.md", "UPSTREAM_LICENSE.md", "CC0-1.0.txt", "CC-BY-4.0.txt"):
        assert (path.parent / name).is_file()
    assert "CC-BY-4.0" in (path.parent / "README.md").read_text()
    assert len(list(viewer.ASSET_DIR.rglob("*.glb"))) == 1


def test_glb_contains_actual_geometry_pbr_materials_and_embedded_images():
    document = viewer._glb_document(viewer.asset_path().read_bytes())
    assert len(document["meshes"]) == 4
    assert len(document["images"]) == 7
    assert all(
        "uri" not in image and "bufferView" in image for image in document["images"]
    )
    assert all("pbrMetallicRoughness" in material for material in document["materials"])
    assert "KHR_materials_sheen" in document["extensionsUsed"]
    triangles = sum(
        document["accessors"][p["indices"]]["count"] // 3
        for m in document["meshes"]
        for p in m["primitives"]
    )
    assert triangles == 39936


@pytest.mark.parametrize(
    "name",
    [
        "../SheenChair.glb",
        "/tmp/SheenChair.glb",
        "https://example.com/a.glb",
        "file:///a",
        "chair.glb",
        "%2e%2e/SheenChair.glb",
        "furniture/SheenChair.glb",
    ],
)
def test_asset_paths_are_allowlisted(name):
    with pytest.raises(viewer.ViewerAssetError):
        viewer.asset_path(name)


def test_missing_asset_is_explicit(monkeypatch, tmp_path):
    monkeypatch.setattr(viewer, "ASSET_DIR", tmp_path)
    with pytest.raises(viewer.ViewerAssetError, match="missing"):
        viewer.verify_asset()


def test_symlink_escape_is_rejected(monkeypatch, tmp_path):
    (tmp_path / "furniture").mkdir()
    (tmp_path / "furniture" / viewer.ASSET_NAME).symlink_to(viewer.asset_path())
    monkeypatch.setattr(viewer, "ASSET_DIR", tmp_path)
    with pytest.raises(viewer.ViewerAssetError, match="outside"):
        viewer.verify_asset()


def test_corrupt_asset_fails_integrity(monkeypatch, tmp_path):
    original = viewer.asset_path()
    (tmp_path / "furniture").mkdir()
    data = bytearray(original.read_bytes())
    data[0] = 0
    (tmp_path / "furniture" / viewer.ASSET_NAME).write_bytes(data)
    (tmp_path / "furniture" / "PROVENANCE.json").write_bytes(
        original.with_name("PROVENANCE.json").read_bytes()
    )
    monkeypatch.setattr(viewer, "ASSET_DIR", tmp_path)
    with pytest.raises(viewer.ViewerAssetError, match="integrity"):
        viewer.verify_asset()


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not glb",
        struct.pack("<4sII", b"glTF", 1, 12),
        struct.pack("<4sII", b"glTF", 2, 100),
    ],
)
def test_bad_glb_structure(data):
    with pytest.raises(viewer.ViewerAssetError, match="structure"):
        viewer._glb_document(data)


def test_payload_is_canonical_json_without_mutation_or_asset_urls():
    design = create_sample_chair()
    before = design.model_dump_json()
    payload = viewer.viewer_payload(design)
    assert design.model_dump_json() == before
    assert payload["furniture"] == design.furniture[0].model_dump(mode="json")
    assert payload["room"]["width_m"] == 3.2
    assert payload["asset_id"] == "sheen-chair"
    assert set(payload) == {"schema_version", "asset_id", "room", "furniture"}
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert json.loads((viewer.ASSET_DIR / "sample-design.json").read_text()) == payload


@pytest.mark.parametrize(
    "changes",
    [
        {"rotation_deg": 90},
        {"category": "desk"},
        {"width_m": 11.0},
        {"x_m": 21.0},
        {"name": "x" * 257},
    ],
)
def test_unsupported_input_is_rejected(changes):
    design = create_sample_chair()
    for key, value in changes.items():
        setattr(design.furniture[0], key, value)
    with pytest.raises(ValueError):
        viewer.viewer_payload(design)


def test_empty_or_multiple_chairs_not_supported():
    design = create_sample_chair()
    design.furniture.append(design.furniture[0].model_copy(update={"id": "other"}))
    with pytest.raises(ValueError, match="exactly one"):
        viewer.viewer_payload(design)
    design.furniture = []
    with pytest.raises(ValueError, match="exactly one"):
        viewer.viewer_payload(design)


def test_schema_revalidation_rejects_nonfinite_values():
    design = create_sample_chair()
    design.furniture[0].x_m = float("nan")
    with pytest.raises(ValidationError):
        viewer.viewer_payload(design)


def test_component_receives_only_data_and_fixed_key(monkeypatch):
    mount = Mock()
    monkeypatch.setattr(viewer, "_component", lambda: mount)
    design = create_sample_chair()
    before = design.model_dump_json()
    viewer.render_realistic_viewer(design)
    mount.assert_called_once_with(
        data=viewer.viewer_payload(design), key="experimental-chair"
    )
    assert design.model_dump_json() == before


def test_bundled_assets_have_no_runtime_cdn_imports():
    bundle = (viewer.ASSET_DIR / "viewer.js").read_text()
    assert 'from"https:' not in bundle
    assert 'import("https:' not in bundle
    assert (viewer.ASSET_DIR / "THIRD_PARTY_NOTICES.txt").is_file()
    assert (viewer.ASSET_DIR / "viewer.js.LEGAL.txt").is_file()
