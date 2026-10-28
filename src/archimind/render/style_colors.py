"""Opt-in catalog colors on existing Plotly meshes; no geometry or physical assets."""

import plotly.graph_objects as go
from pydantic import ValidationError

from archimind.agents.interior_stylist_catalog import CATALOG
from archimind.agents.interior_stylist_schemas import InteriorStylistResult
from archimind.agents.requirements_agent import SUPPORTED_MODELS
from archimind.models import RoomDesign
from archimind.render.design_3d import render_design_3d


class StyleColorPreviewError(ValueError):
    """Appearance metadata cannot be bound to this design safely."""


def render_styled_design_3d(
    design: RoomDesign, advice: InteriorStylistResult
) -> go.Figure:
    """Recolor existing wall/floor/furniture meshes from an E1 style result.

    Strict schema/catalog validation and exact source-design equality prevent
    cross-layout reuse or arbitrary colors. Spatial approval remains the workflow's
    responsibility; this renderer performs no generation, validation-engine or
    model calls. It does not turn rendering into spatial/code certification.
    One finish colors every part of its furniture object. Glass, openings, lighting,
    opacity, camera and all geometry stay unchanged. Accents have no mesh targets.
    The input plan remains metadata with rendered=False; figure metadata separately
    records this explicit preview. No textures, PBR or physical materials are added.
    """
    try:
        design = RoomDesign.model_validate(design)
        advice = InteriorStylistResult.model_validate(advice)
        if (
            advice.status != "styled"
            or advice.context.catalog != CATALOG
            or advice.context.request.candidate.design != design
            or (advice.mode == "offline_fixture" and advice.model is not None)
            or (advice.mode == "api_response" and advice.model not in SUPPORTED_MODELS)
            or advice.mode not in ("offline_fixture", "api_response")
        ):
            raise ValueError("Style result does not match its source")
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise StyleColorPreviewError(
            "Color preview requires a checked catalog plan for this exact layout."
        ) from None
    plan = advice.plan
    figure = render_design_3d(design)
    for trace in figure.data:
        kind = trace.meta.get("kind")
        if kind == "wall":
            trace.color = plan.wall_finish.base_color_hex
        elif kind == "floor":
            trace.color = plan.floor_finish.base_color_hex
        elif kind == "furniture":
            trace.color = plan.furniture_finishes[trace.meta["id"]].base_color_hex
    figure.update_layout(
        meta={
            **figure.layout.meta,
            "style_preview": {
                "kind": "catalog_flat_color",
                "catalog_version": plan.catalog_version,
                "theme_id": plan.theme_id,
                "palette_id": plan.palette_id,
                "provenance": advice.mode,
                "physical_materials": False,
                "accents_applied": False,
            },
        }
    )
    return figure
