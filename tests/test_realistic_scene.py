"""Canonical scene envelopes, trusted asset bindings and failure boundaries."""

import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.examples.sample_chair import create_sample_chair
from archimind.examples.sample_realistic_room import create_sample_realistic_room
from archimind.models import RoomDesign
from archimind.render import realistic_scene as scene
from archimind.render import realistic_viewer as legacy


def test_contract_reuses_canonical_models_and_preserves_complete_data():
    design = create_sample_realistic_room()
    before = design.model_dump_json()
    payload = scene.scene_payload(design)
    contract = scene.ArchitecturalScene.model_validate(payload)
    assert isinstance(contract.design, RoomDesign)
    assert contract.design == design
    assert payload["design"] == design.model_dump(mode="json")
    assert design.model_dump_json() == before
    assert (
        scene.ArchitecturalScene.model_validate_json(contract.model_dump_json())
        == contract
    )
    assert scene.scene_payload(design) == payload
    assert json.loads((legacy.ASSET_DIR / "room-design.json").read_text()) == payload


def test_doors_windows_and_coordinates_keep_canonical_units_and_elevations():
    payload = scene.scene_payload(create_sample_realistic_room())
    room = payload["design"]["room"]
    assert (room["width_m"], room["depth_m"], room["ceiling_height_m"]) == (5, 4, 2.7)
    assert room["doors"][0] == {
        "id": "entry",
        "wall": "south",
        "offset_m": 0.45,
        "width_m": 0.9,
        "height_m": 2.1,
    }
    assert room["windows"][0]["sill_height_m"] == 0.9
    assert room["windows"][0]["wall"] == "north"
    assert {f["id"]: (f["x_m"], f["y_m"]) for f in payload["design"]["furniture"]} == {
        "chair-a": (1, 0.95),
        "chair-b": (2.25, 1.2),
        "desk-placeholder": (3.25, 2.8),
    }


def test_catalog_is_typed_frozen_and_contains_only_existing_asset():
    assert set(scene.ASSET_CATALOG) == {"sheen-chair"}
    assert scene.ASSET_CATALOG["sheen-chair"].native_up == "+Y"
    with pytest.raises(TypeError):
        scene.ASSET_CATALOG["other"] = scene.ASSET_CATALOG["sheen-chair"]
    with pytest.raises(ValidationError):
        scene.ASSET_CATALOG["sheen-chair"].native_up = "+Z"


def test_multiple_instances_have_independent_bindings_and_placeholder():
    payload = scene.scene_payload(create_sample_realistic_room())
    assert payload["asset_bindings"] == [
        {"furniture_id": "chair-a", "asset_id": "sheen-chair"},
        {"furniture_id": "chair-b", "asset_id": "sheen-chair"},
        {"furniture_id": "desk-placeholder", "asset_id": None},
    ]


def test_unknown_categories_use_explicit_procedural_fallback():
    design = create_sample_realistic_room()
    design.furniture[2].category = "unmapped-category"
    payload = scene.scene_payload(design)
    assert payload["asset_bindings"][2]["asset_id"] is None
    assert payload["design"]["furniture"][2]["category"] == "unmapped-category"


@pytest.mark.parametrize(
    "identifier",
    ["../chair.glb", "https://example.com/chair.glb", "file:///tmp/chair", "unknown"],
)
def test_untrusted_asset_identifiers_rejected(identifier):
    with pytest.raises(ValidationError):
        scene.scene_payload(
            create_sample_realistic_room(), asset_bindings={"chair-a": identifier}
        )


def test_unknown_furniture_and_asset_category_mismatch_rejected():
    with pytest.raises(ValueError, match="unknown furniture"):
        scene.scene_payload(
            create_sample_realistic_room(), asset_bindings={"unknown": "sheen-chair"}
        )
    with pytest.raises(ValidationError, match="category"):
        scene.scene_payload(
            create_sample_realistic_room(),
            asset_bindings={"desk-placeholder": "sheen-chair"},
        )


def test_duplicate_binding_and_missing_binding_rejected():
    payload = scene.scene_payload(create_sample_realistic_room())
    payload["asset_bindings"][1] = payload["asset_bindings"][0]
    with pytest.raises(ValidationError, match="exactly once"):
        scene.ArchitecturalScene.model_validate(payload)
    payload["asset_bindings"] = []
    with pytest.raises(ValidationError, match="exactly once"):
        scene.ArchitecturalScene.model_validate(payload)


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_nonzero_rotations_are_explicitly_unsupported(rotation):
    design = create_sample_realistic_room()
    design.furniture[0].rotation_deg = rotation
    with pytest.raises(ValidationError, match="rotation 0"):
        scene.scene_payload(design)


def test_empty_room_requires_no_asset_and_still_mounts(monkeypatch):
    design = create_sample_realistic_room()
    design.furniture = []
    verify = Mock(side_effect=AssertionError("must not load GLB"))
    mount = Mock()
    monkeypatch.setattr(legacy, "verify_asset", verify)
    monkeypatch.setattr(legacy, "_component", lambda: mount)
    scene.render_realistic_scene(design)
    verify.assert_not_called()
    assert mount.call_args.kwargs["data"]["asset_bindings"] == []
    assert mount.call_args.kwargs["data"]["design"]["room"]["doors"]


def test_missing_or_corrupt_asset_keeps_room_with_explicit_unavailable_flag(
    monkeypatch,
):
    design = create_sample_realistic_room()
    before = design.model_dump_json()
    mount = Mock()
    monkeypatch.setattr(
        legacy,
        "verify_asset",
        Mock(side_effect=legacy.ViewerAssetError("private-path")),
    )
    monkeypatch.setattr(legacy, "_component", lambda: mount)
    scene.render_realistic_scene(design)
    payload = mount.call_args.kwargs["data"]
    assert payload["unavailable_assets"] == ["sheen-chair"]
    assert payload["design"] == design.model_dump(mode="json")
    assert "private-path" not in json.dumps(payload)
    assert design.model_dump_json() == before


def test_explicit_placeholder_override_does_not_attempt_asset_loading(monkeypatch):
    design = create_sample_chair()
    mount = Mock()
    verify = Mock()
    monkeypatch.setattr(legacy, "verify_asset", verify)
    monkeypatch.setattr(legacy, "_component", lambda: mount)
    scene.render_realistic_scene(design, asset_bindings={"sheen-chair": None})
    verify.assert_not_called()
    assert mount.call_args.kwargs["data"]["asset_bindings"] == [
        {"furniture_id": "sheen-chair", "asset_id": None}
    ]


def test_previous_single_chair_contract_remains_compatible():
    design = create_sample_chair()
    before = design.model_dump_json()
    assert legacy.viewer_payload(design)["schema_version"] == 1
    assert (
        scene.scene_payload(design)["design"]["furniture"][0]
        == legacy.viewer_payload(design)["furniture"]
    )
    assert design.model_dump_json() == before


def test_canonical_schema_and_work_limits_are_preserved():
    design = create_sample_realistic_room()
    design.room.doors[0].offset_m = 10
    with pytest.raises(ValidationError):
        scene.scene_payload(design)
    design = create_sample_realistic_room()
    source = design.furniture[0]
    design.furniture = [
        source.model_copy(update={"id": f"item-{i}"}) for i in range(25)
    ]
    with pytest.raises(ValidationError, match="24"):
        scene.scene_payload(design)


def test_invalid_numeric_data_is_rejected_before_component_mount():
    design = create_sample_realistic_room()
    design.furniture[0].x_m = float("inf")
    with pytest.raises(ValidationError):
        scene.scene_payload(design)


def _app():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
    ).run()


def test_streamlit_room_default_is_fixed_and_independent_of_layout_generation(
    monkeypatch,
):
    from archimind.ui import layout_generation as ui

    generator = Mock(wraps=ui.generate_layout_candidates)
    monkeypatch.setattr(ui, "generate_layout_candidates", generator)
    app = _app()
    before = [chart.proto.spec for chart in app.get("plotly_chart")]
    app.checkbox(key="experimental_chair_enabled").check().run()
    assert not app.exception
    assert app.radio(key="experimental_scene_mode").value == "Architectural room"
    proto = app.get("bidi_component")[0].proto
    assert json.loads(proto.json) == scene.scene_payload(create_sample_realistic_room())
    assert not proto.html_content  # JS mounts directly; no literal HTML filename in UI.
    generator.assert_not_called()
    assert [chart.proto.spec for chart in app.get("plotly_chart")] == before
    scene_before = proto.json
    app.button(key="generate_layouts").click().run()
    app.radio(key="selected_layout").set_value("Layout B").run()
    assert app.get("bidi_component")[0].proto.json == scene_before
    assert app.radio(key="selected_layout").value == "Layout B"


def test_streamlit_legacy_mode_still_uses_original_version_one_data():
    app = _app()
    app.checkbox(key="experimental_chair_enabled").check().run()
    app.radio(key="experimental_scene_mode").set_value("Single chair (06D)").run()
    assert not app.exception
    component = app.get("bidi_component")[0]
    assert component.key == "experimental-chair"
    assert json.loads(component.proto.json) == legacy.viewer_payload(
        create_sample_chair()
    )
    app.radio(key="experimental_scene_mode").set_value("Architectural room").run()
    assert app.get("bidi_component")[0].key == "experimental-room"


def test_streamlit_missing_asset_preserves_architectural_scene(monkeypatch):
    monkeypatch.setattr(
        legacy,
        "verify_asset",
        Mock(side_effect=legacy.ViewerAssetError("private-path")),
    )
    app = _app()
    app.checkbox(key="experimental_chair_enabled").check().run()
    assert not app.exception and not app.error
    payload = json.loads(app.get("bidi_component")[0].proto.json)
    assert payload["unavailable_assets"] == ["sheen-chair"]
    assert len(payload["design"]["furniture"]) == 3
    assert payload["design"]["room"]["doors"]
    assert "private-path" not in json.dumps(payload)
    assert len(app.get("plotly_chart")) == 3
