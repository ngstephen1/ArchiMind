"""Offline envelope authority, exact geometry and backward compatibility."""

import copy
import hashlib
import itertools
import json
import math
import socket
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest
from pydantic import ValidationError

from archimind.assets import CatalogError, furniture_from_catalog, load_catalog
from archimind.assets import planning_envelopes as module
from archimind.assets.planning_envelopes import (
    PlanningEnvelope,
    PlanningEnvelopeError,
    PlanningEnvelopeEvidence,
    qualify_planning_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
CHAIR = "abo-b075x2x4xs-amazon-com"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Envelope metadata attempted external work")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    from archimind.assets import inspection

    monkeypatch.setattr(inspection, "_read_local", forbidden)
    import openai

    monkeypatch.setattr(openai, "OpenAI", forbidden)
    monkeypatch.setattr(openai, "AsyncOpenAI", forbidden)


def digest(raw):
    return hashlib.sha256(
        json.dumps(
            raw,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()


@pytest.fixture
def evidence():
    body = (ROOT / "docs/data/ASSET_QUALIFICATION_08C.json").read_bytes()
    raw = json.loads(body)["inspection"]
    return PlanningEnvelopeEvidence.model_validate_json(
        json.dumps(
            {
                "inspection_receipt_id": "08C:charles:2026-10-28:inspection-v1",
                "inspection_receipt_sha256": digest(raw),
                "qualification_report_sha256": hashlib.sha256(body).hexdigest(),
                "source_glb_sha256": raw["original_sha256"],
                "source_hash_basis": "received_bytes_sha256_in_08C",
                "inspection": raw,
            }
        )
    )


@pytest.fixture
def envelope(evidence):
    return qualify_planning_envelope(CHAIR, evidence=evidence)


def restamp(raw):
    raw = copy.deepcopy(raw)
    raw.pop("metadata_sha256", None)
    raw["metadata_sha256"] = digest(raw)
    return raw


def test_published_mesh_planning_are_distinct_and_original_factory_unchanged(envelope):
    old = furniture_from_catalog(
        CHAIR, furniture_id="old", name="Charles", x_m=0, y_m=0
    )
    assert (old.width_m, old.depth_m, old.height_m) == (0.9906, 0.9906, 0.9652)
    assert envelope.published_dimensions == load_catalog().get_record(CHAIR).dimensions
    assert envelope.measured_mesh_dimensions.wdh == (
        0.996104896068573,
        1.0019413232803345,
        0.976093053817749,
    )
    assert envelope.planning_dimensions.wdh == (
        0.996104896068573,
        1.0019413232803345,
        0.9760930538177491,
    )
    assert not envelope.qualification.render_qualified
    assert not envelope.qualification.natural_front_visually_verified
    assert envelope.evidence.inspection.status == "rejected"


def test_exact_native_corners_are_contained_without_epsilon(envelope):
    placement = envelope.placement
    assert placement.scale_xyz == (1, 1, 1) and placement.furniture_yaw_deg == 0
    assert (
        placement.anchor == "floor_center" and placement.canonical_mapping == "X,-Z,Y"
    )
    native = envelope.evidence.inspection.native_bounds_three
    sizes = tuple(map(Fraction.from_float, envelope.planning_dimensions.wdh))
    delta = tuple(map(Fraction.from_float, placement.normalization_translation_three_m))
    for point in itertools.product(*zip(native.min_xyz, native.max_xyz)):
        x, y, z = (Fraction.from_float(v) + t for v, t in zip(point, delta))
        for v, limit in zip((x + sizes[0] / 2, -z + sizes[1] / 2, y), sizes):
            assert 0 <= v <= limit
    # A real corner exceeds the original height: no inward tolerance hides it.
    assert Fraction.from_float(native.max_xyz[1]) > Fraction("0.9652")


@pytest.mark.parametrize(
    "value", [Fraction(1, 10), Fraction(1, 3), Fraction.from_float(0.976093053817749)]
)
def test_outward_rounding_covers_binary64_and_decimal_geometry(value):
    result = module._outward(value)
    assert Fraction.from_float(result) >= value
    assert Fraction(str(result)) >= value
    previous = math.nextafter(result, -math.inf)
    assert Fraction.from_float(previous) < value or Fraction(str(previous)) < value


def test_rebuild_json_digest_and_deep_immutability(envelope, evidence):
    assert qualify_planning_envelope(CHAIR, evidence=evidence) == envelope
    assert PlanningEnvelope.model_validate_json(envelope.model_dump_json()) == envelope
    raw = envelope.model_dump(mode="json")
    expected = raw.pop("metadata_sha256")
    assert digest(raw) == expected
    for target, name, value in [
        (envelope, "asset_id", "new"),
        (envelope.planning_dimensions, "width_m", 1),
        (envelope.published_dimensions.original[0], "value", 1),
        (envelope.evidence.inspection.native_bounds_three, "min_xyz", (0, 0, 0)),
        (envelope.placement, "scale_xyz", (0.99, 0.99, 0.99)),
        (envelope.qualification, "render_qualified", True),
    ]:
        with pytest.raises(ValidationError):
            setattr(target, name, value)
    with pytest.raises(TypeError):
        envelope.placement.scale_xyz[0] = 2


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), 2),
        (("schema_version",), True),
        (("envelope_version",), "2.0.0"),
        (("catalog_schema_version",), 2),
        (("catalog_id",), "other"),
        (("catalog_version",), "1.1.0"),
        (("asset_version",), "2.0.0"),
        (("catalog_record_sha256",), "0" * 64),
        (("asset_id",), "abo-b07pqs58xn-amazon-com"),
        (("product_id",), "B07PQS58XN"),
        (("model_id",), "B07PQS58XN"),
        (("variant_id",), "B07PQS58XN"),
        (("variant_label",), "Espresso"),
        (("envelope_id",), "other"),
        (("published_dimensions", "width_m"), 0.991),
        (("published_dimensions", "kind"), "package"),
        (("published_dimensions", "axis_map", 0, "source_field"), "height"),
        (("evidence", "source_glb_sha256"), "0" * 64),
        (("evidence", "source_glb_sha256"), "etag"),
        (("evidence", "inspection_receipt_id"), "unverified"),
        (("evidence", "inspection_receipt_sha256"), "0" * 64),
        (("evidence", "qualification_report_sha256"), "0" * 64),
        (("evidence", "inspection", "original_sha256"), "0" * 64),
        (("evidence", "inspection", "native_bounds_three", "max_xyz", 0), 0.5),
        (("evidence", "inspection", "normalized_bounds_three", "max_xyz", 0), 0.5),
        (("qualification", "status"), "unknown"),
        (("qualification", "policy_id"), "policy-c"),
        (("qualification", "policy_version"), "1.1.0"),
        (("qualification", "owner_decision_id"), "unknown"),
        (("qualification", "owner_decision_sha256"), "0" * 64),
        (("qualification", "render_qualified"), True),
        (("qualification", "render_qualified"), 0),
        (("placement", "native_up"), "+Z"),
        (("placement", "native_front"), "-Z"),
        (("placement", "canonical_mapping"), "X,Y,Z"),
        (("placement", "anchor"), "unknown"),
        (("placement", "furniture_yaw_deg"), 90),
        (("placement", "furniture_yaw_deg"), True),
        (("placement", "furniture_yaw_deg"), 0.0),
        (("placement", "scale_xyz", 0), 0.99),
        (("placement", "normalization_translation_three_m", 2), 0),
        (("placement", "envelope_origin_offset_three_m", 0), 0),
        (("planning_dimensions", "width_m"), 0.9906),
        (("planning_dimensions", "depth_m"), 1.01),
        (("planning_dimensions", "height_m"), 0),
        (("planning_dimensions", "height_m"), -1),
        (("rounding_rule",), "2_percent_margin"),
    ],
)
def test_inconsistent_evidence_or_policy_rejected_even_with_new_digest(
    envelope, path, value
):
    raw = envelope.model_dump(mode="json")
    target = raw
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises((ValidationError, PlanningEnvelopeError, CatalogError)):
        PlanningEnvelope.model_validate_json(json.dumps(restamp(raw)))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_rejected(envelope, value):
    raw = envelope.model_dump(mode="json")
    raw["planning_dimensions"]["width_m"] = value
    with pytest.raises((ValidationError, PlanningEnvelopeError)):
        PlanningEnvelope.model_validate_json(json.dumps(raw))


def test_missing_extra_duplicate_and_corrupt_metadata(envelope):
    raw = envelope.model_dump(mode="json")
    for key in ("qualification", "evidence", "placement", "metadata_sha256"):
        changed = copy.deepcopy(raw)
        changed.pop(key)
        with pytest.raises(ValidationError):
            PlanningEnvelope.model_validate_json(json.dumps(changed))
    changed = copy.deepcopy(raw)
    changed["untrusted_url"] = "https://example.com"
    with pytest.raises(ValidationError):
        PlanningEnvelope.model_validate_json(json.dumps(restamp(changed)))
    for payload in ('{"schema_version":1,"schema_version":1}', "broken", b"\xff"):
        with pytest.raises(PlanningEnvelopeError):
            PlanningEnvelope.model_validate_json(payload)
    raw["metadata_sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        PlanningEnvelope.model_validate_json(json.dumps(raw))


def test_public_qualification_is_sanitized_and_does_not_promote_unknown_products(
    evidence,
):
    for asset in ("unknown", "https://example.com/SECRET", "abo-b07pqs58xn-amazon-com"):
        with pytest.raises(PlanningEnvelopeError) as error:
            qualify_planning_envelope(asset, evidence=evidence)
        assert error.value.code == "unqualified_envelope"
        assert "SECRET" not in str(error.value)
    changed = evidence.model_copy(update={"source_glb_sha256": "0" * 64})
    with pytest.raises(PlanningEnvelopeError):
        qualify_planning_envelope(CHAIR, evidence=changed)


def test_catalog_changes_invalidate_stored_envelope_without_editing_it(
    envelope, monkeypatch
):
    before = envelope.model_dump_json()
    catalog = load_catalog().model_copy(update={"catalog_version": "1.1.0"})
    monkeypatch.setattr(module, "load_catalog", lambda: catalog)
    with pytest.raises(ValidationError):
        PlanningEnvelope.model_validate_json(before)
    assert envelope.model_dump_json() == before


def test_fixed_packaged_reference_matches_rebuilt_qualification(envelope):
    from archimind.assets import load_planning_envelope

    loaded = load_planning_envelope(CHAIR)
    assert loaded == envelope
    assert loaded.evidence.inspection.normalization_scale == 1
    assert all(not r.render_qualified for r in load_catalog().records)


@pytest.mark.parametrize(
    "asset",
    [
        "unknown",
        "../secret",
        "https://example.com/secret",
        "abo-b07pqs58xn-amazon-com",
        True,
    ],
)
def test_loader_has_no_unqualified_asset_fallback(asset):
    with pytest.raises(PlanningEnvelopeError) as error:
        module.load_planning_envelope(asset)
    assert error.value.code == "envelope_not_found"


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "oversized",
        "broken",
        "duplicate_key",
        "version",
        "duplicates",
        "hash",
        "missing",
    ],
)
def test_bad_packaged_metadata_fails_completely(monkeypatch, kind):
    import io

    resource = ROOT / "src/archimind/assets/planning_envelopes.json"
    raw = json.loads(resource.read_text())
    if kind == "version":
        raw["schema_version"] = 2
    elif kind == "duplicates":
        raw["envelopes"].append(copy.deepcopy(raw["envelopes"][0]))
    elif kind == "hash":
        raw["envelopes"][0]["evidence"]["source_glb_sha256"] = "0" * 64
    body = json.dumps(raw).encode()
    if kind == "empty":
        body = b""
    elif kind == "oversized":
        body = b" " * (512 * 1024 + 1)
    elif kind == "broken":
        body = b"SECRET_TOKEN"
    elif kind == "duplicate_key":
        body = b'{"schema_version":1,"schema_version":1}'
    original = module.resources.files

    class BadResource:
        def open(self, mode):
            if kind == "missing":
                raise OSError("SECRET_PATH")
            return io.BytesIO(body)

    class Root:
        def joinpath(self, name):
            return (
                BadResource()
                if name == "planning_envelopes.json"
                else original("archimind.assets").joinpath(name)
            )

    monkeypatch.setattr(module.resources, "files", lambda package: Root())
    with pytest.raises(PlanningEnvelopeError) as error:
        module.load_planning_envelope(CHAIR)
    assert error.value.code == "envelope_metadata_unavailable"
    assert "SECRET" not in str(error.value)


def test_fresh_explicit_factory_preserves_inputs_and_immutable_sidecar():
    from archimind.assets import (
        PlanningFurnitureBinding,
        furniture_from_planning_envelope,
    )
    from archimind.models import Furniture

    args = dict(furniture_id="chair instance", name=" Charles A ", x_m=-2.5, y_m=20.0)
    first = furniture_from_planning_envelope(CHAIR, **args)
    second = furniture_from_planning_envelope(CHAIR, **args)
    assert first.furniture is not second.furniture
    assert first.furniture == second.furniture
    f, binding = first
    assert (f.id, f.name, f.x_m, f.y_m, f.rotation_deg) == (
        "chair instance",
        " Charles A ",
        -2.5,
        20,
        0,
    )
    assert (
        f.width_m,
        f.depth_m,
        f.height_m,
    ) == binding.envelope.planning_dimensions.wdh
    assert binding.canonical_dimensions == binding.envelope.planning_dimensions
    assert binding.envelope.published_dimensions.width_m == 0.9906
    assert Furniture.model_validate_json(f.model_dump_json()) == f
    assert (
        PlanningFurnitureBinding.model_validate_json(binding.model_dump_json())
        == binding
    )
    assert binding.metadata_sha256 == second.binding.metadata_sha256
    binding.validate_furniture(f)
    first.furniture.width_m = 0.99
    with pytest.raises(PlanningEnvelopeError):
        binding.validate_furniture(first.furniture)
    assert second.furniture.width_m == 0.996104896068573
    with pytest.raises(ValidationError):
        binding.canonical_dimensions.width_m = 0.99


@pytest.mark.parametrize("rotation", [90, 180, 270, -90, True, 0.0, "0"])
def test_factory_rejects_every_unsupported_yaw(rotation):
    with pytest.raises(PlanningEnvelopeError) as error:
        module.furniture_from_planning_envelope(
            CHAIR, furniture_id="a", name="A", x_m=0, y_m=0, rotation_deg=rotation
        )
    assert error.value.code == "unsupported_yaw"


@pytest.mark.parametrize(
    "changes",
    [
        dict(x_m=float("nan")),
        dict(y_m=float("inf")),
        dict(name=" "),
        dict(furniture_id=""),
        dict(x_m="1"),
    ],
)
def test_factory_rejects_invalid_canonical_inputs(changes):
    values = dict(furniture_id="a", name="A", x_m=0, y_m=0)
    values.update(changes)
    with pytest.raises(PlanningEnvelopeError) as error:
        module.furniture_from_planning_envelope(CHAIR, **values)
    assert error.value.code == "invalid_planning_specification"


def test_factory_performs_no_generation_geometry_or_rendering(monkeypatch):
    from archimind.geometry import accessibility, layout_generator, validator
    from archimind.render import realistic_scene

    def forbidden(*args, **kwargs):
        raise AssertionError("No geometry/generation/rendering from factory")

    monkeypatch.setattr(layout_generator, "generate_layout_candidates", forbidden)
    monkeypatch.setattr(validator, "validate_layout", forbidden)
    monkeypatch.setattr(accessibility, "validate_accessibility", forbidden)
    monkeypatch.setattr(realistic_scene, "render_realistic_scene", forbidden)
    result = module.furniture_from_planning_envelope(
        CHAIR, furniture_id="a", name="A", x_m=100, y_m=-200
    )
    assert (result.furniture.x_m, result.furniture.y_m) == (100, -200)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "other"),
        ("name", "Other"),
        ("category", "desk"),
        ("rotation_deg", 90),
        ("width_m", 0.9906),
        ("depth_m", 0.9906),
        ("height_m", 0.9652),
        ("x_m", float("inf")),
    ],
)
def test_binding_detects_tampered_furniture(field, value):
    result = module.furniture_from_planning_envelope(
        CHAIR, furniture_id="a", name="A", x_m=0, y_m=0
    )
    changed = result.furniture.model_copy(update={field: value})
    with pytest.raises(PlanningEnvelopeError) as error:
        result.binding.validate_furniture(changed)
    assert error.value.code == "furniture_binding_mismatch"


def test_existing_spatial_rules_see_larger_reservation():
    from archimind.geometry import validate_layout
    from archimind.models import Room, RoomDesign

    old = furniture_from_catalog(CHAIR, furniture_id="a", name="A", x_m=0, y_m=0)
    proposed = module.furniture_from_planning_envelope(
        CHAIR, furniture_id="a", name="A", x_m=0, y_m=0
    )
    room = Room(id="room", name="Room", width_m=0.995, depth_m=2, ceiling_height_m=2.7)
    old_design = RoomDesign(room=room, furniture=[old])
    report = validate_layout(old_design)
    assert report.status == "passed"
    before = old_design.model_dump_json(), report.model_dump_json()
    assert (
        validate_layout(RoomDesign(room=room, furniture=[proposed.furniture])).status
        == "failed"
    )
    assert (old_design.model_dump_json(), report.model_dump_json()) == before


def test_existing_candidate_scores_reports_and_specification_stay_unchanged():
    from archimind.examples import create_sample_bedroom
    from archimind.geometry import generate_layout_candidates, validate_accessibility

    design = create_sample_bedroom()
    result = generate_layout_candidates(design.room, design.furniture, seed=42)
    assert result.candidates
    before = design.model_dump_json(), result.model_dump_json()
    proposed = module.furniture_from_planning_envelope(
        CHAIR, furniture_id="new-chair", name="Charles", x_m=1, y_m=1
    )
    proposed.binding.validate_furniture(proposed.furniture)
    assert (design.model_dump_json(), result.model_dump_json()) == before
    for candidate in result.candidates:
        assert validate_accessibility(candidate.design).status == "passed"
    # Explicit generation of a fresh request uses the original unchanged engine.
    new = generate_layout_candidates(design.room, [proposed.furniture], seed=42)
    assert new.candidates
    proposed.binding.validate_furniture(new.candidates[0].design.furniture[0])
    assert (design.model_dump_json(), result.model_dump_json()) == before
