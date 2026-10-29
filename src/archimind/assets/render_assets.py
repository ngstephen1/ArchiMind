"""Fixed, reviewed product release; the catalog and Policy B remain authoritative.

Only the reviewed receipt can approve rendering. Runtime scenes carry IDs,
versions and digests, never paths, transforms or an approval switch. Historical
metadata/planning qualification states are not rewritten by this render release.
"""

import json
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from archimind.assets import load_catalog, load_planning_envelope
from archimind.assets.render_qualification import (
    CHARLES_ID,
    ProductQualificationError,
    metadata_digest,
    requalify_product,
)

_RELEASE_SHA256 = "a2aa2007730e0276691a7959e71fb50c8af51a34577d1b0c3f6acd0df19480a8"


class ProductRenderRelease(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    schema_version: Literal[1]
    asset_id: Literal["abo-b075x2x4xs-amazon-com"]
    render_version: Literal["1.0.0"]
    render_qualified: Literal[True]
    policy: Literal["native_scale_1_planning_envelope_B"]
    envelope_sha256: str
    inspection_sha256: str
    catalog_record_sha256: str
    source_glb_sha256: str
    filename: Literal["CharlesArmchair.glb"]
    visual_review_sha256: str
    license_id: Literal["CC-BY-4.0"]
    bytes_unchanged: Literal[True]


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def product_release() -> ProductRenderRelease:
    """Fixed packaged metadata only; fail closed on any stale binding or evidence."""
    try:
        root = resources.files("archimind.assets")
        raw = root.joinpath("product_render_release.json").read_bytes()
        if len(raw) > 16384:
            raise ValueError
        value = json.loads(raw, object_pairs_hook=_unique)
        if metadata_digest(value) != _RELEASE_SHA256:
            raise ValueError
        release = ProductRenderRelease.model_validate_json(raw)
        envelope = load_planning_envelope(release.asset_id)
        visual_raw = root.joinpath("charles_visual_review.json").read_bytes()
        if len(visual_raw) > 65536:
            raise ValueError
        visual = json.loads(visual_raw, object_pairs_hook=_unique)
        if (
            release.envelope_sha256 != envelope.metadata_sha256
            or release.catalog_record_sha256 != envelope.catalog_record_sha256
            or release.inspection_sha256 != envelope.evidence.inspection_receipt_sha256
            or release.source_glb_sha256 != envelope.evidence.source_glb_sha256
            or metadata_digest(visual) != release.visual_review_sha256
            or visual["status"] != "passed_with_documented_limits"
            or not all(visual["required_checks"].values())
        ):
            raise ValueError
        return release
    except (ValueError, OSError, KeyError, TypeError):
        raise ProductQualificationError("product_release_unavailable") from None


def product_projection() -> dict:
    """Build-time renderer projection; not a separately authored product database."""
    release = product_release()
    e = load_planning_envelope(release.asset_id)
    i = e.evidence.inspection
    r = load_catalog().get_record(release.asset_id)
    return {
        release.asset_id: {
            "asset_id": release.asset_id,
            "render_version": release.render_version,
            "catalog_id": e.catalog_id,
            "catalog_version": e.catalog_version,
            "asset_version": e.asset_version,
            "product_id": e.product_id,
            "model_id": e.model_id,
            "variant_label": e.variant_label,
            "envelope_sha256": e.metadata_sha256,
            "release_sha256": _RELEASE_SHA256,
            "category": r.category,
            "dimensions": list(e.planning_dimensions.wdh),
            "filename": release.filename,
            "sha256": release.source_glb_sha256,
            "bytes": i.original_size_bytes,
            "native_min": list(i.native_bounds_three.min_xyz),
            "native_max": list(i.native_bounds_three.max_xyz),
            "translation": list(i.normalization_translation_three),
            "triangles": i.triangles_per_instance,
            "texture_bytes": i.estimated_unique_texture_bytes,
            "images": [{"width": v.width, "height": v.height} for v in i.images],
            "mesh_instances": i.mesh_instances,
            "material_count": i.material_count,
        }
    }


def product_asset_path() -> Path:
    """Resolve only the fixed trusted package member; reject symlink escapes."""
    release = product_release()
    directory = Path(__file__).resolve().parents[1] / "_viewer_assets" / "furniture"
    path = directory / release.filename
    if path.is_symlink() or path.resolve().parent != directory.resolve():
        raise ProductQualificationError("product_asset_unavailable")
    return path


def verify_product_asset() -> dict:
    """Fresh integrity and offline inspection; no network, fitting or validation."""
    product_release()
    return requalify_product(product_asset_path(), CHARLES_ID).model_dump(mode="json")
