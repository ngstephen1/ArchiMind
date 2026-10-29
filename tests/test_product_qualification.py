"""No acquisitions or live services in qualification tests."""

import socket
import subprocess

import pytest

from archimind.assets import load_planning_envelope
from archimind.assets import render_qualification as module
from archimind.assets.render_qualification import (
    CHARLES_ID,
    ProductQualificationError,
    metadata_digest,
    requalify_product,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External work forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def test_current_byte_inspection_and_exact_envelope(monkeypatch, tmp_path):
    envelope = load_planning_envelope(CHARLES_ID)
    observed = []

    def inspect(path, record, *, expected_sha256):
        observed.append((path, record.asset_id, expected_sha256))
        return envelope.evidence.inspection

    monkeypatch.setattr(module, "inspect_furniture_asset", inspect)
    result = requalify_product(tmp_path / "fixture.glb")
    assert result.envelope == envelope
    assert not result.render_qualified
    assert result.renderer_scale == 1.0
    assert result.corner_check == "eight_corners_exact_rational_no_epsilon"
    assert observed[0][1:] == (CHARLES_ID, envelope.evidence.source_glb_sha256)
    assert metadata_digest(result.inspection.model_dump(mode="json")) == (
        envelope.evidence.inspection_receipt_sha256
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("original_sha256", "0" * 64),
        ("expected_hash_checked", False),
        ("triangles_per_instance", 1),
    ],
)
def test_changed_receipt_rejected(monkeypatch, tmp_path, field, value):
    inspection = load_planning_envelope(CHARLES_ID).evidence.inspection
    monkeypatch.setattr(
        module,
        "inspect_furniture_asset",
        lambda *a, **k: inspection.model_copy(update={field: value}),
    )
    with pytest.raises(
        ProductQualificationError, match="^product_requalification_failed$"
    ):
        requalify_product(tmp_path / "secret.glb")


@pytest.mark.parametrize("asset_id", ["unknown", "abo-b00tagi4se-amazon-com"])
def test_unknown_or_unapproved_asset(tmp_path, asset_id):
    with pytest.raises(ProductQualificationError):
        requalify_product(tmp_path / "secret.glb", asset_id)


def test_missing_current_bytes(tmp_path):
    with pytest.raises(
        ProductQualificationError, match="^product_requalification_failed$"
    ):
        requalify_product(tmp_path / "secret.glb")
