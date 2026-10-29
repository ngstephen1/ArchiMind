"""Offline requalification against Policy B; never grants visual approval."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from archimind.assets.catalog import load_catalog
from archimind.assets.inspection import AssetInspection, inspect_furniture_asset
from archimind.assets.planning_envelopes import (
    PlanningEnvelope,
    load_planning_envelope,
)

CHARLES_ID = "abo-b075x2x4xs-amazon-com"


def metadata_digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class ProductQualificationError(ValueError):
    """Fixed diagnostic, without paths or arbitrary source text."""


class TechnicalQualification(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    status: Literal["automated_pass_visual_pending"] = "automated_pass_visual_pending"
    render_qualified: Literal[False] = False
    inspection: AssetInspection
    envelope: PlanningEnvelope
    corner_check: Literal["eight_corners_exact_rational_no_epsilon"] = (
        "eight_corners_exact_rational_no_epsilon"
    )
    renderer_scale: Literal[1.0] = 1.0


def requalify_product(path: Path, asset_id: str = CHARLES_ID) -> TechnicalQualification:
    """Inspect current local bytes, then revalidate the exact reviewed envelope.

    The historical inspector still rejects the published physical box. Only
    that gate is superseded by the owner-approved, independently checked B box.
    Image decoding, natural front and appearance remain pending browser review.
    """
    try:
        envelope = load_planning_envelope(asset_id)
        envelope = PlanningEnvelope.model_validate_json(envelope.model_dump_json())
        record = load_catalog().get_record(asset_id)
        inspection = inspect_furniture_asset(
            path, record, expected_sha256=envelope.evidence.source_glb_sha256
        )
        if (
            not inspection.expected_hash_checked
            or metadata_digest(inspection.model_dump(mode="json"))
            != envelope.evidence.inspection_receipt_sha256
            or any(
                gate.status != "passed"
                for gate in inspection.gates
                if gate.name != "canonical_envelope"
            )
        ):
            raise ValueError
        return TechnicalQualification(inspection=inspection, envelope=envelope)
    except (ValueError, OSError, KeyError, TypeError):
        raise ProductQualificationError("product_requalification_failed") from None
