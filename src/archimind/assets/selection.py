"""Explicit, evidence-bound render selection; never infer a product from shape."""

from collections import Counter
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict

from archimind.assets.inspection import assess_scene_budget
from archimind.assets.planning_envelopes import PlanningFurnitureBinding
from archimind.assets.render_assets import product_release
from archimind.models import RoomDesign
from archimind.render.product_scene import ProductBinding

Reason = Literal[
    "no_explicit_binding",
    "procedural_requested",
    "invalid_planning_binding",
    "unapproved_asset",
    "override_mismatch",
    "asset_release_unavailable",
    "scene_budget_exceeded",
    "asset_unavailable",
]


class BindingDiagnostic(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    furniture_id: str
    status: Literal["approved_product", "placeholder"]
    reason: Reason | None = None
    provenance: PlanningFurnitureBinding | None = None


class RenderBindingResolution(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    bindings: tuple[ProductBinding, ...]
    diagnostics: tuple[BindingDiagnostic, ...]


def build_render_bindings(
    design: RoomDesign,
    *,
    planning_bindings: Mapping[str, PlanningFurnitureBinding] | None = None,
    overrides: Mapping[str, str | None] | None = None,
) -> RenderBindingResolution:
    """Resolve complete bindings without generation, spatial checks or file reads.

    Fixed packaged qualification metadata is authoritative. Matching dimensions
    without an explicit planning sidecar never establishes a product association.
    Unknown furniture references are errors; invalid evidence for an existing
    object becomes a reasoned placeholder, with no alternative product search.
    """
    design = RoomDesign.model_validate(design)
    if any(f.rotation_deg != 0 for f in design.furniture):
        raise ValueError("Realistic rendering supports only rotation zero")
    proofs = dict(planning_bindings or {})
    choices = dict(overrides or {})
    ids = {f.id for f in design.furniture}
    if not (proofs.keys() | choices.keys()) <= ids:
        raise ValueError("Render binding references unknown furniture")
    bindings, diagnostics, inspections = [], [], {}
    for f in sorted(design.furniture, key=lambda item: item.id):
        reason, proof, release = None, None, None
        if f.id in choices and choices[f.id] is None:
            reason = "procedural_requested"
        elif f.id not in proofs:
            reason = "no_explicit_binding"
        else:
            try:
                proof = PlanningFurnitureBinding.model_validate(proofs[f.id])
                proof.validate_furniture(f)
            except (ValueError, TypeError, RecursionError):
                reason = "invalid_planning_binding"
            if reason is None:
                try:
                    release = product_release()
                except (ValueError, OSError, RecursionError):
                    reason = "asset_release_unavailable"
                if release is not None:
                    e = proof.envelope
                    if e.asset_id != release.asset_id:
                        reason = "unapproved_asset"
                    elif (
                        e.metadata_sha256 != release.envelope_sha256
                        or e.catalog_record_sha256 != release.catalog_record_sha256
                        or e.evidence.inspection_receipt_sha256
                        != release.inspection_sha256
                        or e.evidence.source_glb_sha256 != release.source_glb_sha256
                    ):
                        reason = "invalid_planning_binding"
                    elif f.id in choices and choices[f.id] != release.asset_id:
                        reason = "override_mismatch"
        approved = reason is None
        bindings.append(
            ProductBinding(
                furniture_id=f.id,
                asset_id=release.asset_id if approved else None,
                render_version=release.render_version if approved else None,
                envelope_sha256=release.envelope_sha256 if approved else None,
            )
        )
        diagnostics.append(
            BindingDiagnostic(
                furniture_id=f.id,
                status="approved_product" if approved else "placeholder",
                reason=reason,
                provenance=proof if approved else None,
            )
        )
        if approved:
            inspections[release.asset_id] = proof.envelope.evidence.inspection
    counts = Counter(b.asset_id for b in bindings if b.asset_id)
    budget = assess_scene_budget(
        tuple((inspections[key], count) for key, count in sorted(counts.items()))
    )
    if not budget.passed:
        bindings = [
            ProductBinding(
                furniture_id=b.furniture_id,
                asset_id=None,
                render_version=None,
                envelope_sha256=None,
            )
            for b in bindings
        ]
        diagnostics = [
            BindingDiagnostic(
                furniture_id=d.furniture_id,
                status="placeholder",
                reason="scene_budget_exceeded",
            )
            if d.status == "approved_product"
            else d
            for d in diagnostics
        ]
    return RenderBindingResolution(
        bindings=tuple(bindings), diagnostics=tuple(diagnostics)
    )
