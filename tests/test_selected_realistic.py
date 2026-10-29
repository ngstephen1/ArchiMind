"""Evidence-only adapters: no acquisition, providers, generation or spatial work."""

import json
import socket
import subprocess

import pytest

from archimind.assets import furniture_from_planning_envelope, selection
from archimind.assets.render_qualification import CHARLES_ID, ProductQualificationError
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates
from archimind.models import RoomDesign
from archimind.render import product_scene
from archimind.render.selected_realistic import (
    build_selected_realistic_scene,
    render_selected_realistic_scene,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External operation forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def product():
    spec = furniture_from_planning_envelope(
        CHARLES_ID, furniture_id="charles", name="Charles", x_m=1.0, y_m=1.0
    )
    design = create_sample_bedroom()
    design.furniture = [spec.furniture]
    return design, {spec.furniture.id: spec.binding}


def test_exact_geometry_room_openings_order_and_serialization():
    design = create_sample_bedroom()
    design.furniture.reverse()
    before = design.model_dump_json()
    prepared = build_selected_realistic_scene(design)
    assert prepared.scene.design.model_dump_json() == before
    assert design.model_dump_json() == before
    assert prepared.scene.schema_version == 3
    assert [b.furniture_id for b in prepared.resolution.bindings] == sorted(
        f.id for f in design.furniture
    )
    assert all(b.asset_id is None for b in prepared.resolution.bindings)
    assert all(
        d.reason == "no_explicit_binding" for d in prepared.resolution.diagnostics
    )
    assert (
        prepared.model_dump_json()
        == build_selected_realistic_scene(design).model_dump_json()
    )
    assert type(prepared).model_validate_json(prepared.model_dump_json()) == prepared


def test_exact_size_chair_without_explicit_evidence_is_placeholder():
    design, _ = product()
    assert (
        build_selected_realistic_scene(design).resolution.bindings[0].asset_id is None
    )
    assert (
        build_selected_realistic_scene(design, overrides={"charles": CHARLES_ID})
        .resolution.bindings[0]
        .asset_id
        is None
    )


def test_explicit_binding_preserves_current_provenance_and_pose():
    design, proofs = product()
    f = design.furniture[0]
    f.x_m, f.y_m = -2.0, 12.0
    before = design.model_dump_json()
    result = build_selected_realistic_scene(design, planning_bindings=proofs)
    binding = result.resolution.bindings[0]
    diagnostic = result.resolution.diagnostics[0]
    assert binding.asset_id == CHARLES_ID
    assert binding.envelope_sha256 == proofs[f.id].envelope.metadata_sha256
    assert binding.render_version == "1.0.0"
    assert diagnostic.status == "approved_product" and diagnostic.reason is None
    assert diagnostic.provenance == proofs[f.id]
    assert result.scene.design.furniture[0].x_m == -2.0
    assert result.scene.design.furniture[0].y_m == 12.0
    assert before == design.model_dump_json()


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "different"),
        ("name", "different"),
        ("category", "desk"),
        ("width_m", 0.9906),
        ("height_m", 0.9652),
    ],
)
def test_mismatched_canonical_object_has_reasoned_placeholder(field, value):
    design, proofs = product()
    # Keep the lookup ID correct so the ID mismatch is checked inside evidence.
    if field == "id":
        proofs = {"different": proofs["charles"]}
    setattr(design.furniture[0], field, value)
    result = build_selected_realistic_scene(design, planning_bindings=proofs)
    assert result.resolution.bindings[0].asset_id is None
    assert result.resolution.diagnostics[0].reason == "invalid_planning_binding"


@pytest.mark.parametrize(
    "change",
    [
        "catalog_version",
        "asset_version",
        "envelope_hash",
        "source_hash",
        "inspection_hash",
        "binding_digest",
    ],
)
def test_stale_or_forged_sidecar_is_never_approved(change):
    design, proofs = product()
    proof = proofs["charles"]
    e = proof.envelope
    if change == "catalog_version":
        e = e.model_copy(update={"catalog_version": "9.0.0"})
    if change == "asset_version":
        e = e.model_copy(update={"asset_version": "9.0.0"})
    if change == "envelope_hash":
        e = e.model_copy(update={"metadata_sha256": "0" * 64})
    if change in ("source_hash", "inspection_hash"):
        key = (
            "source_glb_sha256"
            if change == "source_hash"
            else "inspection_receipt_sha256"
        )
        e = e.model_copy(
            update={"evidence": e.evidence.model_copy(update={key: "0" * 64})}
        )
    proof = proof.model_copy(update={"envelope": e})
    if change == "binding_digest":
        proof = proof.model_copy(update={"metadata_sha256": "0" * 64})
    result = build_selected_realistic_scene(
        design, planning_bindings={"charles": proof}
    )
    assert result.resolution.bindings[0].asset_id is None
    assert result.resolution.diagnostics[0].reason == "invalid_planning_binding"


@pytest.mark.parametrize(
    "override",
    [None, "sheen-chair", "unknown", "https://invalid/model.glb", "../model.glb", 42],
)
def test_overrides_never_substitute_another_product(override):
    design, proofs = product()
    result = build_selected_realistic_scene(
        design, planning_bindings=proofs, overrides={"charles": override}
    )
    assert result.resolution.bindings[0].asset_id is None
    assert result.resolution.diagnostics[0].status == "placeholder"


def test_matching_override_still_requires_valid_evidence():
    design, proofs = product()
    assert (
        build_selected_realistic_scene(
            design, planning_bindings=proofs, overrides={"charles": CHARLES_ID}
        )
        .resolution.bindings[0]
        .asset_id
        == CHARLES_ID
    )


@pytest.mark.parametrize("argument", ["planning_bindings", "overrides"])
def test_unknown_furniture_reference_rejected(argument):
    with pytest.raises(ValueError, match="unknown furniture"):
        build_selected_realistic_scene(
            create_sample_bedroom(), **{argument: {"missing": None}}
        )


def test_empty_and_placeholder_only_need_no_product_release(monkeypatch):
    def forbidden():
        raise AssertionError("No product metadata should be needed")

    monkeypatch.setattr(selection, "product_release", forbidden)
    monkeypatch.setattr(product_scene, "product_release", forbidden)
    for design in (
        create_sample_bedroom(),
        RoomDesign(room=create_sample_bedroom().room, furniture=[]),
    ):
        result = build_selected_realistic_scene(design)
        payload = product_scene.product_scene_payload(
            design, asset_bindings={f.id: None for f in design.furniture}
        )
        assert payload == result.scene.model_dump(mode="json")


def test_unavailable_release_downgrades_explicit_product(monkeypatch):
    design, proofs = product()

    def unavailable():
        raise ProductQualificationError("product_release_unavailable")

    monkeypatch.setattr(selection, "product_release", unavailable)
    result = build_selected_realistic_scene(design, planning_bindings=proofs)
    assert result.resolution.diagnostics[0].reason == "asset_release_unavailable"


def test_unsupported_rotation_fails_without_coercion():
    design = create_sample_bedroom()
    design.furniture[0].rotation_deg = 90
    before = design.model_dump_json()
    with pytest.raises(ValueError, match="rotation zero"):
        build_selected_realistic_scene(design)
    assert design.model_dump_json() == before


def test_aggregate_budget_falls_back_before_loading():
    design, _ = product()
    items = [
        furniture_from_planning_envelope(
            CHARLES_ID, furniture_id=f"c-{i}", name=f"Charles {i}", x_m=1.0, y_m=1.0
        )
        for i in range(8)
    ]
    design.furniture = [item.furniture for item in items]
    result = build_selected_realistic_scene(
        design, planning_bindings={p.furniture.id: p.binding for p in items}
    )
    assert all(b.asset_id is None for b in result.resolution.bindings)
    assert all(
        d.reason == "scene_budget_exceeded" for d in result.resolution.diagnostics
    )


def test_shared_mount_reports_binary_failure_without_layout_mutation(monkeypatch):
    design, proofs = product()
    before = design.model_dump_json()
    observed = []
    monkeypatch.setattr(
        product_scene, "_component", lambda: lambda **kwargs: observed.append(kwargs)
    )

    def unavailable():
        raise ProductQualificationError("asset_unavailable")

    monkeypatch.setattr(product_scene, "verify_product_asset", unavailable)
    result = render_selected_realistic_scene(design, planning_bindings=proofs)
    assert observed[0]["data"]["unavailable_assets"] == [CHARLES_ID]
    assert result.resolution.diagnostics[0].reason == "asset_unavailable"
    assert design.model_dump_json() == before


def test_candidate_geometry_reports_scores_and_order_unchanged(monkeypatch):
    design = create_sample_bedroom()
    generation = generate_layout_candidates(
        design.room, design.furniture, seed=42, max_candidates=2, max_attempts=500
    )
    before = generation.model_dump_json()
    import archimind.geometry as geometry

    def forbidden(*args, **kwargs):
        raise AssertionError("Rendering must not execute backend work")

    monkeypatch.setattr(geometry, "generate_layout_candidates", forbidden)
    monkeypatch.setattr(geometry, "validate_accessibility", forbidden)
    monkeypatch.setattr(product_scene, "_component", lambda: lambda **kwargs: None)
    for candidate in generation.candidates:
        rendered = render_selected_realistic_scene(candidate.design)
        assert rendered.scene.design.model_dump(
            mode="json"
        ) == candidate.design.model_dump(mode="json")
    assert generation.model_dump_json() == before
    assert (
        json.loads(before)["candidates"]
        == generation.model_dump(mode="json")["candidates"]
    )
