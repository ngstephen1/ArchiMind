"""Generation-bound metadata and presentation; never a second selected design."""

import hashlib
import json
import logging
from typing import Mapping

import streamlit as st
from pydantic import BaseModel, ConfigDict, Field

from archimind.assets.planning_envelopes import PlanningFurnitureBinding
from archimind.assets.selection import build_render_bindings
from archimind.assets.specifications import ProductAssignment
from archimind.geometry import LayoutGenerationResult
from archimind.models import RoomDesign
from archimind.render.selected_realistic import render_selected_realistic_scene

VIEW_KEY = "selected_3d_view"
REVISION_KEY = "realistic_generation_revision"
SNAPSHOT_KEY = "realistic_generation_bindings"
OVERRIDES_KEY = "realistic_product_overrides"
PLOTLY_VIEW = "Plotly schematic"
THREE_VIEW = "Realistic Three.js"


class GenerationRenderSnapshot(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    revision: int = Field(ge=1)
    generation_digest: str
    specification_digest: str
    bindings: tuple[PlanningFurnitureBinding, ...]
    invalid_evidence: bool = False
    source_specification_json: str | None = None
    assignments: tuple[ProductAssignment, ...] = ()
    source_mode: str = "Procedural bedroom"


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
    *,
    assignments: tuple[ProductAssignment, ...] = (),
    source_mode: str = "Procedural bedroom",
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
    if len({a.furniture_id for a in assignments}) != len(assignments):
        raise ValueError("Duplicate product assignments")
    for assignment in assignments:
        assignment.validate_furniture(furniture[assignment.furniture_id])
    return GenerationRenderSnapshot(
        revision=revision,
        generation_digest=digest(result),
        specification_digest=digest(specification),
        bindings=tuple(sorted(accepted, key=lambda p: p.furniture_id)),
        invalid_evidence=invalid,
        source_specification_json=specification.model_dump_json(),
        assignments=assignments,
        source_mode=source_mode,
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


def stored_source_specification(
    result: LayoutGenerationResult, legacy: RoomDesign
) -> RoomDesign:
    """Styling reads the committed input, never the next specification controls."""
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if snapshot is None:
        return legacy
    if not isinstance(
        snapshot, GenerationRenderSnapshot
    ) or snapshot.revision != st.session_state.get(REVISION_KEY):
        raise ValueError("Stored generation context is stale")
    if snapshot.source_specification_json is None:
        return legacy
    # Candidate tampering is rejected by the explicit styling workflow checks.
    # Keep its review action available using the unchanged submitted source.
    source = RoomDesign.model_validate_json(snapshot.source_specification_json)
    if digest(source) != snapshot.specification_digest:
        raise ValueError("Stored source specification is stale")
    return source


def render_stored_provenance(result: LayoutGenerationResult) -> None:
    snapshot = st.session_state.get(SNAPSHOT_KEY)
    if not isinstance(
        snapshot, GenerationRenderSnapshot
    ) or snapshot.generation_digest != digest(result):
        return
    st.caption(
        f"Currently displayed results: {snapshot.source_mode} · Generation revision {snapshot.revision}. Pending selections do not change these results."
    )
    if snapshot.assignments:
        with st.expander("Products in the displayed generation"):
            for a in snapshot.assignments:
                st.write(
                    f"{a.furniture_name} · {a.reviewed_name} · {a.product_id} · {a.dimension_basis.replace('_', ' ')}"
                )
                st.caption(
                    f"Catalog {a.catalog_version} / asset {a.asset_version} · {a.license_id}. Published claims and planning reservations are separate; this provenance does not approve a mesh."
                )
                st.markdown(f"[Source]({a.source_url}) · [License]({a.license_url})")
                if a.dimension_basis == "published_item_dimensions":
                    st.caption(
                        "Metadata-only bookcase: correctly sized storage placeholder; no wardrobe or approved product mesh."
                        if a.asset_id == "abo-b07pqs58xn-amazon-com"
                        else f"Metadata-only {a.furniture_name}: published-sized procedural placeholder; no approved planning envelope or product mesh."
                    )


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
    choices = dict(st.session_state.get(OVERRIDES_KEY, {}))
    try:
        available = build_render_bindings(design, planning_bindings=proofs)
        for item in available.bindings:
            if item.asset_id is None:
                continue
            name = next(f.name for f in design.furniture if f.id == item.furniture_id)
            labels = ["Approved product mesh", "Procedural placeholder"]
            choice = st.selectbox(
                f"Representation — {name}",
                labels,
                index=1
                if item.furniture_id in choices and choices[item.furniture_id] is None
                else 0,
                key=f"product_representation:{st.session_state.get(REVISION_KEY, 0)}:{item.furniture_id}",
            )
            choices[item.furniture_id] = item.asset_id if choice == labels[0] else None
        st.session_state[OVERRIDES_KEY] = choices
        prepared = render_selected_realistic_scene(
            design,
            planning_bindings=proofs,
            overrides=choices,
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
