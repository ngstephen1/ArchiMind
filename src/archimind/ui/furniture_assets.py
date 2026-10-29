"""Pending selection/review controls, isolated from currently displayed layouts."""

from typing import NamedTuple

import streamlit as st

from archimind.assets.specifications import (
    PreparedCatalogSpecification,
    catalog_product_options,
    prepare_catalog_specification,
    specification_is_current,
)
from archimind.models import RoomDesign

MODE_KEY = "next_specification_mode"
PREPARED_KEY = "prepared_catalog_specification"
PROCEDURAL = "Procedural bedroom"
CATALOG = "Catalog selection"


class PendingSpecification(NamedTuple):
    catalog_mode: bool
    prepared: PreparedCatalogSpecification | None


def metric(values) -> str:
    return (
        " × ".join(f"{v:.4f}".rstrip("0").rstrip(".") for v in values)
        + " m (W × D × H)"
    )


def _retain_hidden_choices() -> None:
    # Streamlit discards widget-owned keys when their panel cannot be rendered.
    for key in list(st.session_state):
        if key.startswith(("keep_manual:", "catalog_product:")):
            st.session_state[key] = st.session_state[key]


def render_furniture_assets(base: RoomDesign) -> PendingSpecification:
    """Preparing changes only pending state. Generate remains the confirmation."""
    mode = st.selectbox(
        "Specification for next generation", [PROCEDURAL, CATALOG], key=MODE_KEY
    )
    if mode == PROCEDURAL:
        _retain_hidden_choices()
        return PendingSpecification(False, None)
    st.caption(
        "Next specification only. Current alternatives stay unchanged until Generate Layouts returns a new outcome."
    )
    retained, products = [], []
    try:
        options = catalog_product_options()
    except Exception:
        _retain_hidden_choices()
        st.error(
            "The furniture catalog is unavailable. Choose the procedural specification or try again."
        )
        return PendingSpecification(True, None)
    with st.expander("Real Furniture Catalog", expanded=True):
        st.write("Include procedural items")
        for f in base.furniture:
            if st.checkbox(f"Keep {f.name}", value=True, key=f"keep_manual:{f.id}"):
                retained.append(f.id)
        st.write("Add catalog products (one of each)")
        for option in options:
            record = option.record
            if st.checkbox(
                record.search.reviewed_name,
                key=f"catalog_product:{record.asset_id}",
                disabled=not option.preparation_available,
            ):
                products.append(record.asset_id)
            d = record.dimensions
            st.caption(
                f"{record.source.product_id} · Metadata qualified · Published: {metric((d.width_m, d.depth_m, d.height_m))}"
            )
            if option.planning_dimensions:
                st.caption(
                    f"Policy B planning reservation: {metric(option.planning_dimensions.wdh)} · Approved product mesh: {'yes' if option.render_qualified else 'unavailable'}"
                )
            else:
                st.caption(
                    "Published item dimensions used for planning · Product mesh: unavailable; procedural placeholder only."
                )
            if not option.preparation_available:
                st.warning(
                    "Required planning evidence is unavailable; this product cannot be prepared."
                )
            with st.expander(f"Technical details — {record.source.product_id}"):
                st.write(
                    "Dimensions are checked published claims, not independent physical measurements. No material, color or style qualification is inferred from variant names."
                )
                st.json(
                    {
                        "published_dimensions_m": d.model_dump(mode="json"),
                        "planning_dimensions_m": option.planning_dimensions.model_dump(
                            mode="json"
                        )
                        if option.planning_dimensions
                        else None,
                        "catalog_version": option.catalog_version,
                        "record_version": record.asset_version,
                        "record_digest": option.record_digest,
                    }
                )
                st.markdown(
                    f"[Product metadata]({record.source.metadata_url}) · [{record.legal.license_id}]({record.legal.license_url})"
                )
                st.caption(record.legal.attribution)
    if st.button("Prepare new specification", key="prepare_catalog"):
        try:
            st.session_state[PREPARED_KEY] = prepare_catalog_specification(
                base, retained_manual_ids=retained, product_ids=products
            )
        except Exception:
            st.session_state.pop(PREPARED_KEY, None)
            st.error(
                "The selected specification could not be prepared. Check the product evidence and selections."
            )
    prepared = st.session_state.get(PREPARED_KEY)
    current = isinstance(
        prepared, PreparedCatalogSpecification
    ) and specification_is_current(
        prepared, base, retained_manual_ids=retained, product_ids=products
    )
    if not current:
        st.info(
            "Prepare the current selections before generating. Changed selections, room geometry or evidence require a new review; seed edits do not."
        )
        return PendingSpecification(True, None)
    st.markdown("#### Review next specification")
    design = prepared.design()
    removed = [
        f.name for f in base.furniture if f.id not in prepared.retained_manual_ids
    ]
    st.write("Removed procedural items: " + (", ".join(removed) or "none"))
    assignments = {p.furniture_id: p for p in prepared.assignments}
    st.dataframe(
        [
            {
                "Item": f.name,
                "Identity": assignments[f.id].product_id
                if f.id in assignments
                else f.id,
                "Dimension basis": {
                    "planning_envelope_B": "Policy B planning reservation",
                    "published_item_dimensions": "Published item dimensions",
                }[assignments[f.id].dimension_basis]
                if f.id in assignments
                else "retained manual dimensions",
                "Generation size": metric((f.width_m, f.depth_m, f.height_m)),
            }
            for f in design.furniture
        ],
        hide_index=True,
        key="next_specification_review",
        width="stretch",
    )
    st.caption(
        "Room and openings are preserved. New catalog items start at (0, 0) as unvalidated inputs; the explicit Generate action determines their positions."
    )
    if not design.furniture:
        st.info(
            "Empty specification reviewed. The engine can produce only one distinct empty arrangement, so a request for two alternatives will be partial."
        )
    return PendingSpecification(True, prepared)
