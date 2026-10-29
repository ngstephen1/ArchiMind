"""Product renderer contract, local bytes only; no services or acquisition."""

import copy
import hashlib
import json
import socket
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from archimind.assets import load_catalog, load_planning_envelope
from archimind.assets import render_assets as assets
from archimind.assets.render_qualification import CHARLES_ID, ProductQualificationError
from archimind.examples.sample_product_room import create_sample_product_room
from archimind.examples.sample_realistic_room import create_sample_realistic_room
from archimind.render import product_scene as module
from archimind.render.product_scene import ProductScene, product_scene_payload

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External work forbidden")

    # Streamlit's asyncio loop needs an AF_UNIX self-pipe. Deny network
    # operations rather than breaking that internal socketpair construction.
    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    for name in ("create_connection", "getaddrinfo", "gethostbyname"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def payload():
    d = create_sample_product_room()
    return product_scene_payload(
        d,
        asset_bindings={
            f.id: CHARLES_ID if f.category == "chair" else None for f in d.furniture
        },
    )


def test_release_binds_current_catalog_envelope_and_visual_evidence():
    release = assets.product_release()
    e = load_planning_envelope(CHARLES_ID)
    r = load_catalog().get_record(CHARLES_ID)
    projection = assets.product_projection()[CHARLES_ID]
    assert release.render_qualified
    assert release.source_glb_sha256 == e.evidence.source_glb_sha256
    assert release.envelope_sha256 == e.metadata_sha256
    assert release.catalog_record_sha256 == e.catalog_record_sha256
    assert not r.render_qualified and not e.qualification.render_qualified
    assert (r.dimensions.width_m, r.dimensions.depth_m, r.dimensions.height_m) == (
        0.9906,
        0.9906,
        0.9652,
    )
    assert projection["variant_label"] == "Sod"
    assert projection["product_id"] == projection["model_id"] == "B075X2X4XS"
    assert projection["catalog_version"] == "1.0.0"
    assert projection["dimensions"] == list(e.planning_dimensions.wdh)
    assert (
        assets.verify_product_asset()["inspection"]["original_sha256"]
        == release.source_glb_sha256
    )


def test_projected_registry_reproducible():
    from scripts.build_product_registry import registry_source

    assert (
        ROOT / "frontend/realistic_viewer/src/product_registry.js"
    ).read_text() == registry_source()


@pytest.mark.parametrize("kind", ["release", "visual", "duplicate", "missing"])
def test_release_metadata_fail_closed(monkeypatch, tmp_path, kind):
    real = ROOT / "src/archimind/assets"
    for name in ["product_render_release.json", "charles_visual_review.json"]:
        (tmp_path / name).write_bytes((real / name).read_bytes())
    file = tmp_path / (
        "charles_visual_review.json"
        if kind == "visual"
        else "product_render_release.json"
    )
    if kind == "missing":
        file.unlink()
    elif kind == "duplicate":
        file.write_text('{"schema_version":1,"schema_version":1}')
    else:
        obj = json.loads(file.read_text())
        obj["asset_id"] = "secret-invalid"
        file.write_text(json.dumps(obj))
    monkeypatch.setattr(assets.resources, "files", lambda *args: tmp_path)
    with pytest.raises(
        ProductQualificationError, match="^product_release_unavailable$"
    ):
        assets.product_release()


def test_asset_hash_and_no_duplicate_mesh_copy():
    path = assets.product_asset_path()
    assert path.name == "CharlesArmchair.glb"
    assert path.stat().st_size == 4252440
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == assets.product_release().source_glb_sha256
    )
    assert list((ROOT / "src").rglob("CharlesArmchair.glb")) == [path]
    source = json.loads((path.parent / "CHARLES_PROVENANCE.json").read_text())
    assert source["sha256"] == assets.product_release().source_glb_sha256
    assert "Original GLB bytes unchanged" in source["modifications"]
    for name in [
        source["license_text"],
        source["attribution_notice"],
        "ABO_SOURCE_README.md",
    ]:
        assert (path.parent / name).is_file()


def test_missing_and_corrupt_assets_become_placeholders(monkeypatch, tmp_path):
    d = create_sample_product_room()
    seen = []
    monkeypatch.setattr(
        module, "_component", lambda: lambda **kwargs: seen.append(kwargs)
    )
    monkeypatch.setattr(assets, "product_asset_path", lambda: tmp_path / "missing.glb")
    for content in [None, b"corrupt"]:
        if content:
            (tmp_path / "missing.glb").write_bytes(content)
        before = d.model_dump_json()
        module.render_product_scene(
            d,
            asset_bindings={
                f.id: CHARLES_ID if f.category == "chair" else None for f in d.furniture
            },
        )
        assert seen[-1]["data"]["unavailable_assets"] == [CHARLES_ID]
        assert before == d.model_dump_json()


def test_product_payload_roundtrip_and_no_input_mutation():
    d = create_sample_product_room()
    original = d.model_dump_json()
    p = payload()
    assert ProductScene.model_validate_json(json.dumps(p)).model_dump(mode="json") == p
    assert d.model_dump_json() == original
    assert p == payload()
    assert [f["id"] for f in p["design"]["furniture"]] == [
        "chair-a",
        "chair-b",
        "desk-placeholder",
    ]
    assert p["design"]["room"] == create_sample_realistic_room().room.model_dump(
        mode="json"
    )


@pytest.mark.parametrize(
    "change",
    [
        "rotation",
        "dimensions",
        "category",
        "version",
        "digest",
        "asset",
        "extra",
        "missing",
        "duplicate",
        "placeholder_claim",
        "unavailable",
    ],
)
def test_scene_rejects_untrusted_or_stale_bindings(change):
    p = copy.deepcopy(payload())
    f = p["design"]["furniture"][0]
    b = p["asset_bindings"][0]
    if change == "rotation":
        f["rotation_deg"] = 90
    if change == "dimensions":
        f["width_m"] = 0.9906
    if change == "category":
        f["category"] = "desk"
    if change == "version":
        b["render_version"] = "2.0.0"
    if change == "digest":
        b["envelope_sha256"] = "0" * 64
    if change == "asset":
        b["asset_id"] = "https://secret/model.glb"
    if change == "extra":
        b["approved"] = True
    if change == "missing":
        p["asset_bindings"].pop()
    if change == "duplicate":
        p["asset_bindings"].append(b)
    if change == "placeholder_claim":
        p["asset_bindings"][-1]["render_version"] = "1.0.0"
    if change == "unavailable":
        p["unavailable_assets"] = ["unknown"]
    with pytest.raises((ValidationError, ValueError)):
        ProductScene.model_validate_json(json.dumps(p))


def test_empty_scene_is_safe():
    d = create_sample_product_room()
    d.furniture = []
    assert product_scene_payload(d, asset_bindings={})["asset_bindings"] == []


def test_pending_approval_cannot_be_supplied_in_scene():
    p = payload()
    p["render_qualified"] = True
    with pytest.raises(ValidationError):
        ProductScene.model_validate_json(json.dumps(p))


def test_product_demo_preserves_active_generation_and_selected_views(monkeypatch):
    from unittest.mock import Mock

    from streamlit.testing.v1 import AppTest

    from archimind.ui import layout_generation as ui

    generator = Mock(wraps=ui.generate_layout_candidates)
    validator = Mock(wraps=ui.validate_accessibility)
    plan = Mock(wraps=ui.render_floorplan)
    plot = Mock(wraps=ui.render_design_3d)
    seen = []
    monkeypatch.setattr(ui, "generate_layout_candidates", generator)
    monkeypatch.setattr(ui, "validate_accessibility", validator)
    monkeypatch.setattr(ui, "render_floorplan", plan)
    monkeypatch.setattr(ui, "render_design_3d", plot)
    monkeypatch.setattr(
        module, "_component", lambda: lambda **kwargs: seen.append(kwargs)
    )
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not seen and not app.exception
    app.button(key="generate_layouts").click().run()
    result = app.session_state[ui.RESULT_KEY]
    before = result.model_dump_json()
    selected = plan.call_args.args[0]
    counts = generator.call_count, validator.call_count
    app.checkbox(key="experimental_chair_enabled").check().run()
    app.radio(key="experimental_scene_mode").set_value("Charles product (08C-R2)").run()
    assert not app.exception
    assert seen[-1]["data"]["schema_version"] == 3
    assert len(seen[-1]["data"]["design"]["furniture"]) == 3
    assert (generator.call_count, validator.call_count) == counts
    assert app.session_state[ui.RESULT_KEY] is result
    assert before == result.model_dump_json()
    assert plan.call_args.args[0] is plot.call_args.args[0] is selected
    app.run()
    assert not app.exception and before == result.model_dump_json()
    assert (generator.call_count, validator.call_count) == counts
