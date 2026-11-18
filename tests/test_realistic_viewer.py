"""Offline checks for one allowlisted GLB, provenance and trusted viewer data."""

import hashlib
import json
import struct
from pathlib import Path
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
    assert {p.name for p in viewer.ASSET_DIR.rglob("*.glb")} == {
        "SheenChair.glb",
        "CharlesArmchair.glb",
        "BelayaDesk.glb",
        "designer-54e0786096a654b33368b39b0377822a05168fb19c4528efa2386081f6bebc81.glb",
        "designer-609b06fda80ff254cf00d844ae451ed8c03b3229c3af41812689591c03e62258.glb",
        "designer-5d0044a1acf345f50fa80443c7f722bb2267960bf3a69cd581a310586e8c84d3.glb",
        "designer-3f475788571c146b30a8e5e6a6c8eb33970622e789d66e37821f962e60ad175f.glb",
    }


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


def _app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
    ).run()


def test_experimental_demo_is_opt_in_and_existing_plots_remain():
    app = _app()
    assert not app.exception
    assert "Realistic 3D Viewer — Experimental" in [h.value for h in app.subheader]
    assert app.checkbox(key="experimental_chair_enabled").value is False
    assert not app.get("bidi_component")
    assert len(app.get("plotly_chart")) == 3


def test_enabled_streamlit_component_does_not_change_plotly_or_layouts():
    app = _app()
    before = [chart.proto.spec for chart in app.get("plotly_chart")]
    app.checkbox(key="experimental_chair_enabled").check().run()
    assert not app.exception and not app.error
    assert len(app.get("bidi_component")) == 1
    assert app.get("bidi_component")[0].key == "experimental-room"
    assert [chart.proto.spec for chart in app.get("plotly_chart")] == before
    app.button(key="generate_layouts").click().run()
    app.radio(key="selected_layout").set_value("Layout B").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 5
    assert len(app.get("bidi_component")) == 1
    assert app.radio(key="selected_layout").value == "Layout B"


def test_streamlit_missing_asset_is_safe_and_sanitized(monkeypatch):
    def missing():
        raise viewer.ViewerAssetError("private-path")

    monkeypatch.setattr(viewer, "verify_asset", missing)
    app = _app()
    app.checkbox(key="experimental_chair_enabled").check().run()
    app.radio(key="experimental_scene_mode").set_value("Single chair (06D)").run()
    assert not app.exception
    assert "local asset or configuration is unavailable" in app.error[0].value
    assert "private-path" not in app.error[0].value
    assert not app.get("bidi_component")
    assert len(app.get("plotly_chart")) == 3
