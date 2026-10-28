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
