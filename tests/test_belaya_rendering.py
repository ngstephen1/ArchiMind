"""Pinned Belaya rendering and mixed-scene admission, entirely offline."""

import copy
import hashlib
import json
import socket
import subprocess

import pytest

from archimind.assets import furniture_from_planning_envelope, load_catalog
from archimind.assets.render_assets import (
    BELAYA_ID,
    product_asset_path,
    product_projection,
    product_release,
    verify_product_asset,
)
from archimind.assets.render_qualification import CHARLES_ID
from archimind.assets.selection import build_render_bindings
from archimind.examples.sample_product_room import create_sample_product_room
from archimind.render import product_scene


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External work forbidden")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    for name in ("create_connection", "getaddrinfo", "gethostbyname"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def fixture(mixed=False):
    design = create_sample_product_room()
    assignments = {}
    furniture = []
    for i, asset in enumerate((BELAYA_ID, CHARLES_ID if mixed else BELAYA_ID)):
        prepared = furniture_from_planning_envelope(
            asset,
            furniture_id=f"product-{i}",
            name=f"Product {i}",
            x_m=float(i * 2),
            y_m=0.0,
        )
        item = prepared.furniture
        furniture.append(item)
        assignments[item.id] = prepared.binding
    design.furniture = furniture
    return design, assignments


def test_pinned_bytes_native_release_and_historical_metadata():
    release = product_release(BELAYA_ID)
    assert (
        release.source_glb_sha256
        == hashlib.sha256(product_asset_path(BELAYA_ID).read_bytes()).hexdigest()
    )
    assert product_asset_path(BELAYA_ID).stat().st_size == 3135676
    assert verify_product_asset(BELAYA_ID)["renderer_scale"] == 1.0
    assert product_projection()[BELAYA_ID]["dimensions"] == [
        1.6,
        0.8018731772899628,
        0.7516312003135682,
    ]
    assert product_release().asset_id == CHARLES_ID
    assert all(not r.render_qualified for r in load_catalog().records)


def test_adapter_preserves_input_and_explicit_identity():
    design, proofs = fixture()
    before = design.model_dump_json()
    resolved = build_render_bindings(design, planning_bindings=proofs)
    assert all(b.asset_id == BELAYA_ID for b in resolved.bindings)
    assert all(b.asset_id is None for b in build_render_bindings(design).bindings)
    assert design.model_dump_json() == before
    p = product_scene.product_scene_payload(
        design, asset_bindings={b.furniture_id: b.asset_id for b in resolved.bindings}
    )
    assert (
        product_scene.ProductScene.model_validate_json(json.dumps(p)).design == design
    )


def test_mixed_adapter_and_direct_mount_never_inspect_mesh(monkeypatch):
    design, proofs = fixture(mixed=True)
    before = design.model_dump_json()
    resolved = build_render_bindings(design, planning_bindings=proofs)
    assert all(b.asset_id is None for b in resolved.bindings)
    assert {d.reason for d in resolved.diagnostics} == {"mixed_scene_not_yet_qualified"}
    p = product_scene.product_scene_payload(
        design, asset_bindings={key: b.envelope.asset_id for key, b in proofs.items()}
    )
    monkeypatch.setattr(
        product_scene,
        "verify_product_asset",
        lambda *a: pytest.fail("Mixed asset inspection forbidden"),
    )
    seen = []
    monkeypatch.setattr(
        product_scene, "_component", lambda: lambda **kwargs: seen.append(kwargs)
    )
    effective = product_scene.mount_product_payload(p, key="mixed")
    assert effective["unavailable_assets"] == sorted([BELAYA_ID, CHARLES_ID])
    assert seen[-1]["data"] == effective
    assert design.model_dump_json() == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("render_version", "9.0.0"),
        ("envelope_sha256", "0" * 64),
        ("asset_id", CHARLES_ID),
    ],
)
def test_stale_or_substituted_binding_rejected(field, value):
    design, proofs = fixture()
    p = product_scene.product_scene_payload(
        design, asset_bindings=dict.fromkeys(proofs, BELAYA_ID)
    )
    altered = copy.deepcopy(p)
    altered["asset_bindings"][0][field] = value
    with pytest.raises(ValueError):
        product_scene.ProductScene.model_validate(altered)


@pytest.mark.parametrize("content", [None, b"corrupt"])
def test_missing_corrupt_belaya_fallback(monkeypatch, tmp_path, content):
    from archimind.assets import render_assets

    path = tmp_path / "missing.glb"
    if content is not None:
        path.write_bytes(content)
    monkeypatch.setattr(render_assets, "product_asset_path", lambda asset_id: path)
    monkeypatch.setattr(product_scene, "_component", lambda: lambda **kwargs: None)
    design, proofs = fixture()
    p = product_scene.product_scene_payload(
        design, asset_bindings=dict.fromkeys(proofs, BELAYA_ID)
    )
    assert product_scene.mount_product_payload(p, key="fallback")[
        "unavailable_assets"
    ] == [BELAYA_ID]


@pytest.mark.parametrize("kind", ["missing", "release", "visual", "duplicate"])
def test_render_release_and_visual_evidence_fail_closed(monkeypatch, tmp_path, kind):
    from archimind.assets import render_assets

    root = render_assets.resources.files("archimind.assets")
    target = (
        "belaya_visual_review.json"
        if kind == "visual"
        else "belaya_render_release.json"
    )
    file = tmp_path / target
    if kind == "duplicate":
        file.write_text('{"asset_id":"x","asset_id":"y"}')
    elif kind != "missing":
        value = json.loads(root.joinpath(target).read_bytes())
        value["asset_id"] = CHARLES_ID
        file.write_text(json.dumps(value))

    class Files:
        def joinpath(self, name):
            return file if name == target else root.joinpath(name)

    monkeypatch.setattr(render_assets.resources, "files", lambda *args: Files())
    with pytest.raises(ValueError, match="^product_release_unavailable$"):
        product_release(BELAYA_ID)
