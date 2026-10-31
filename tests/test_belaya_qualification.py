"""Belaya qualification without network, quarantine paths or provider execution."""

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

from archimind.assets import load_catalog
from archimind.assets import planning_envelopes as module
from archimind.assets.planning_envelopes import (
    BELAYA_ID,
    PlanningEnvelope,
    PlanningEnvelopeError,
    PlanningEnvelopeEvidence,
    PlanningFurnitureBinding,
    furniture_from_planning_envelope,
    load_planning_envelope,
    qualify_planning_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/archimind/assets"
CHARLES = "abo-b075x2x4xs-amazon-com"
GLB_HASH = "2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External execution forbidden")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    import openai

    monkeypatch.setattr(openai, "OpenAI", forbidden)
    monkeypatch.setattr(openai, "AsyncOpenAI", forbidden)


def candidate():
    return json.loads((ASSETS / "belaya_planning_envelope.json").read_text())[
        "envelopes"
    ][0]


def restamp(raw):
    raw["metadata_sha256"] = module._digest(
        {k: v for k, v in raw.items() if k != "metadata_sha256"}
    )
    return json.dumps(raw)


def test_inspected_identity_and_receipt_are_pinned():
    e = load_planning_envelope(BELAYA_ID)
    r = load_catalog().get_record(BELAYA_ID)
    assert (e.product_id, e.model_id, e.variant_label) == (
        "B074L4976T",
        "B074L4976T",
        "Oak",
    )
    assert r.source.manufacturer_model_numbers == ("T80505PL05LVO",)
    assert e.catalog_version == "1.1.0" and e.catalog_schema_version == 2
    assert e.evidence.source_glb_sha256 == GLB_HASH
    assert e.evidence.inspection.original_size_bytes == 3135676
    receipt = (ASSETS / "belaya_qualification.json").read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == e.evidence.qualification_report_sha256
    assert json.loads(receipt)["inspection"] == e.evidence.inspection.model_dump(
        mode="json"
    )
    assert qualify_planning_envelope(BELAYA_ID, evidence=e.evidence) == e
    assert not e.qualification.render_qualified


def test_independent_exact_corner_and_outward_checks():
    e = load_planning_envelope(BELAYA_ID)
    i = e.evidence.inspection
    assert e.planning_dimensions.wdh == (1.6, 0.8018731772899628, 0.7516312003135682)
    assert e.measured_mesh_dimensions.wdh == (
        1.5999999046325684,
        0.8018731772899628,
        0.7516312003135681,
    )
    assert e.placement.scale_xyz == (1.0, 1.0, 1.0)
    assert e.placement.normalization_translation_three_m == (
        0.0,
        0.0,
        -0.08341898024082184,
    )
    w, d, h = map(Fraction.from_float, e.planning_dimensions.wdh)
    delta = tuple(
        map(Fraction.from_float, e.placement.normalization_translation_three_m)
    )
    points = list(
        itertools.product(
            *zip(i.native_bounds_three.min_xyz, i.native_bounds_three.max_xyz)
        )
    )
    assert len(points) == 8
    for point in points:
        x, y, z = (Fraction.from_float(v) + t for v, t in zip(point, delta))
        assert all(
            0 <= v <= limit for v, limit in zip((x + w / 2, -z + d / 2, y), (w, d, h))
        )
    assert min(i.native_bounds_three.min_xyz[1:2]) == 0
    assert Fraction(str(float(h))) >= Fraction.from_float(
        i.native_bounds_three.max_xyz[1]
    )
    gates = {g.name: g.status for g in i.gates}
    assert gates["canonical_envelope"] == "failed"
    assert all(v == "passed" for k, v in gates.items() if k != "canonical_envelope")


@pytest.mark.parametrize("axis", ["width_m", "depth_m", "height_m"])
def test_inward_rounding_rejected_even_with_restamped_digest(axis):
    raw = candidate()
    raw["planning_dimensions"][axis] = math.nextafter(
        raw["planning_dimensions"][axis], -math.inf
    )
    with pytest.raises(ValueError):
        PlanningEnvelope.model_validate_json(restamp(raw))


@pytest.mark.parametrize(
    "path,value",
    [
        (("asset_id",), "abo-b07h8jn9qf-amazon-co-uk"),
        (("model_id",), "B07H8JN9QF"),
        (("variant_label",), "Oak Sonoma"),
        (("catalog_version",), "1.0.0"),
        (("catalog_record_sha256",), "0" * 64),
        (("evidence", "source_glb_sha256"), "0" * 64),
        (("evidence", "inspection_receipt_sha256"), "0" * 64),
        (("evidence", "inspection", "expected_hash_checked"), False),
        (
            ("evidence", "inspection", "native_bounds_three", "max_xyz"),
            [0.8, 0.75, 0.4],
        ),
        (("placement", "scale_xyz"), [0.99, 0.99, 0.99]),
        (("placement", "normalization_translation_three_m"), [0, 0, 0]),
        (("placement", "furniture_yaw_deg"), 90),
        (("qualification", "render_qualified"), True),
    ],
)
def test_forged_or_stale_candidate_fails(path, value):
    raw = copy.deepcopy(candidate())
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        PlanningEnvelope.model_validate_json(restamp(raw))


def test_candidate_flag_cannot_bypass_release_gate(monkeypatch):
    raw = candidate()
    e = PlanningEnvelope.model_validate_json(json.dumps(raw))
    item, proof = furniture_from_planning_envelope(
        BELAYA_ID, furniture_id="desk", name="Belaya", x_m=-1.0, y_m=20.0
    )
    monkeypatch.setattr(module, "_BELAYA_RELEASE_SHA256", "0" * 64)
    # Pure candidate rebuilding is still possible; public use is denied.
    assert qualify_planning_envelope(BELAYA_ID, evidence=e.evidence) == e
    with pytest.raises(PlanningEnvelopeError, match="planning_release_unavailable"):
        load_planning_envelope(BELAYA_ID)
    with pytest.raises(ValueError):
        PlanningFurnitureBinding.model_validate(proof)
    with pytest.raises(PlanningEnvelopeError):
        furniture_from_planning_envelope(
            BELAYA_ID, furniture_id=item.id, name=item.name, x_m=0, y_m=0
        )
    assert load_planning_envelope(CHARLES).asset_id == CHARLES


@pytest.mark.parametrize(
    "failure", ["missing_release", "altered_release", "altered_receipt"]
)
def test_fixed_resources_are_required(monkeypatch, tmp_path, failure):
    original = module.resources.files("archimind.assets")
    target = (
        "belaya_qualification.json"
        if failure == "altered_receipt"
        else "belaya_planning_release.json"
    )
    replacement = tmp_path / target
    if failure != "missing_release":
        replacement.write_bytes(b'{"status":"planning_release_approved"}')

    class Resource:
        def joinpath(self, name):
            return replacement if name == target else original.joinpath(name)

    monkeypatch.setattr(module.resources, "files", lambda _: Resource())
    with pytest.raises(PlanningEnvelopeError, match="planning_release_unavailable"):
        load_planning_envelope(BELAYA_ID)


def test_unknown_receipt_cannot_self_approve():
    raw = candidate()["evidence"]
    raw["inspection"]["asset_id"] = "abo-b07h8jn9qf-amazon-co-uk"
    raw["inspection_receipt_sha256"] = module._digest(raw["inspection"])
    with pytest.raises(ValueError):
        PlanningEnvelopeEvidence.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize(
    "asset_id", ["abo-b07h8jn9qf-amazon-co-uk", "abo-b07b4vxxjc-amazon-com"]
)
def test_other_products_remain_metadata_only(asset_id):
    assert not load_catalog().get_record(asset_id).render_qualified
    with pytest.raises(PlanningEnvelopeError):
        load_planning_envelope(asset_id)


def test_published_box_and_unsupported_yaw_are_rejected():
    raw = candidate()
    raw["planning_dimensions"] = dict(width_m=1.6, depth_m=0.8, height_m=0.75)
    with pytest.raises(ValueError):
        PlanningEnvelope.model_validate_json(restamp(raw))
    with pytest.raises(PlanningEnvelopeError, match="unsupported_yaw"):
        furniture_from_planning_envelope(
            BELAYA_ID, furniture_id="desk", name="Belaya", x_m=0, y_m=0, rotation_deg=90
        )


def test_original_catalogs_and_charles_envelope_are_unchanged():
    assert (
        hashlib.sha256((ASSETS / "furniture_catalog.json").read_bytes()).hexdigest()
        == "3535c9911ec0f4f844d82647c12af615965b8daef106d16ba753dc98a7d439ad"
    )
    assert (
        hashlib.sha256(
            (ASSETS / "furniture_catalog_1_0_0.json").read_bytes()
        ).hexdigest()
        == "c1116a65558b2781f1ac979920dbd0b0b683dfdcc314681a70d8639ed87880dd"
    )
    old = load_planning_envelope(CHARLES)
    assert qualify_planning_envelope(CHARLES, evidence=old.evidence) == old
