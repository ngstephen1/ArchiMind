"""Prepare the exact selected canonical design for the existing V3 renderer."""

from typing import Mapping

from pydantic import BaseModel, ConfigDict

from archimind.assets.planning_envelopes import PlanningFurnitureBinding
from archimind.assets.selection import (
    BindingDiagnostic,
    RenderBindingResolution,
    build_render_bindings,
)
from archimind.models import RoomDesign
from archimind.render.product_scene import ProductScene, mount_product_payload


class PreparedRealisticScene(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    scene: ProductScene
    resolution: RenderBindingResolution


def build_selected_realistic_scene(
    design: RoomDesign,
    *,
    planning_bindings: Mapping[str, PlanningFurnitureBinding] | None = None,
    overrides: Mapping[str, str | None] | None = None,
) -> PreparedRealisticScene:
    """Ephemeral schema conversion only; never save this as another layout."""
    resolution = build_render_bindings(
        design, planning_bindings=planning_bindings, overrides=overrides
    )
    return PreparedRealisticScene(
        scene=ProductScene(design=design, asset_bindings=list(resolution.bindings)),
        resolution=resolution,
    )


def render_selected_realistic_scene(
    design: RoomDesign,
    *,
    planning_bindings: Mapping[str, PlanningFurnitureBinding] | None = None,
    overrides: Mapping[str, str | None] | None = None,
    key: str = "selected-realistic-scene",
) -> PreparedRealisticScene:
    prepared = build_selected_realistic_scene(
        design, planning_bindings=planning_bindings, overrides=overrides
    )
    payload = mount_product_payload(prepared.scene.model_dump(mode="json"), key=key)
    failed = set(payload["unavailable_assets"])
    diagnostics = tuple(
        BindingDiagnostic(
            furniture_id=d.furniture_id,
            status="placeholder",
            reason="asset_unavailable",
        )
        if b.asset_id in failed
        else d
        for b, d in zip(
            prepared.resolution.bindings, prepared.resolution.diagnostics, strict=True
        )
    )
    return PreparedRealisticScene(
        scene=ProductScene.model_validate(payload),
        resolution=RenderBindingResolution(
            bindings=prepared.resolution.bindings, diagnostics=diagnostics
        ),
    )
