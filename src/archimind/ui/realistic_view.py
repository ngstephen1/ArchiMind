"""Generation-bound metadata and presentation; never a second selected design."""

import hashlib
import json
import logging
from typing import Mapping

import streamlit as st
from pydantic import BaseModel, ConfigDict, Field

from archimind.assets.planning_envelopes import PlanningFurnitureBinding
from archimind.geometry import LayoutGenerationResult
from archimind.models import RoomDesign
from archimind.render.selected_realistic import render_selected_realistic_scene

VIEW_KEY = "selected_3d_view"
REVISION_KEY = "realistic_generation_revision"
SNAPSHOT_KEY = "realistic_generation_bindings"
PLOTLY_VIEW = "Plotly schematic"
THREE_VIEW = "Realistic Three.js"


class GenerationRenderSnapshot(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    revision: int = Field(ge=1)
    generation_digest: str
    specification_digest: str
    bindings: tuple[PlanningFurnitureBinding, ...]
    invalid_evidence: bool = False


def digest(value: BaseModel) -> str:
    return hashlib.sha256(
        json.dumps(
            value.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def snapshot_generation(
    specification: RoomDesign,
    result: LayoutGenerationResult,
    revision: int,
    planning_bindings: Mapping[str, PlanningFurnitureBinding] | None,
) -> GenerationRenderSnapshot:
    """Capture submitted evidence only after successful generation acceptance."""
    furniture = {f.id: f for f in specification.furniture}
    accepted, invalid = [], False
    for key, value in (planning_bindings or {}).items():
        try:
            proof = PlanningFurnitureBinding.model_validate(value)
            if key != proof.furniture_id or key not in furniture:
                raise ValueError
            proof.validate_furniture(furniture[key])
        except (ValueError, TypeError, RecursionError):
            invalid = True
        else:
            accepted.append(proof)
    return GenerationRenderSnapshot(
        revision=revision,
        generation_digest=digest(result),
        specification_digest=digest(specification),
        bindings=tuple(sorted(accepted, key=lambda p: p.furniture_id)),
        invalid_evidence=invalid,
    )


def stored_bindings(result: LayoutGenerationResult) -> tuple[dict, bool]:
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if not isinstance(snapshot, GenerationRenderSnapshot):
        return {}, snapshot is not None
    if snapshot.revision != st.session_state.get(
        REVISION_KEY
    ) or snapshot.generation_digest != digest(result):
        return {}, True
    return {p.furniture_id: p for p in snapshot.bindings}, snapshot.invalid_evidence


def render_selected_layout_view(
    design: RoomDesign, result: LayoutGenerationResult, label: str
) -> None:
    """Read stored generation metadata; pending controls cannot rebind old results."""
    proofs, invalid = stored_bindings(result)
    if invalid:
        st.warning(
            "Stored product evidence is stale or incompatible. Unmatched items use placeholders."
        )
    st.caption(
        f"{label} · Exact selected canonical geometry. Three.js uses original product materials and procedural placeholders. Styling colors remain available in Plotly."
    )
    try:
        prepared = render_selected_realistic_scene(
            design,
            planning_bindings=proofs,
            key=f"selected-realistic-{st.session_state.get(REVISION_KEY, 0)}",
        )
    except Exception:
        logging.getLogger(__name__).exception("Selected realistic scene unavailable")
        st.error(
            "The realistic view cannot display this layout or its render configuration. The stored layout is preserved; choose Plotly to use the schematic view."
        )
        return
    approved = sum(
        d.status == "approved_product" for d in prepared.resolution.diagnostics
    )
    st.caption(
        f"{label} · Approved product bindings: {approved} · Placeholders: {len(prepared.resolution.diagnostics) - approved}. Client loading status is shown inside the viewer."
    )
    if prepared.resolution.diagnostics:
        st.dataframe(
            [
                {
                    "Furniture ID": d.furniture_id,
                    "Representation": d.status.replace("_", " "),
                    "Reason": d.reason.replace("_", " ")
                    if d.reason
                    else "Explicit planning evidence and current render release",
                }
                for d in prepared.resolution.diagnostics
            ],
            hide_index=True,
            key="selected_realistic_bindings",
            width="stretch",
        )
    if approved:
        st.caption(
            "Charles, Sod — ABO B075X2X4XS · Amazon.com · CC BY 4.0 · Original GLB unchanged; native scale 1.0. Dataset builders: Matthieu Guillaumin, Thomas Dideriksen, Kenan Deng, Himanshu Arora, Jasmine Collins and Jitendra Malik. No endorsement implied."
        )
        st.markdown(
            "[ABO source](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)"
        )
