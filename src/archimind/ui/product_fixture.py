"""Explicit standalone fixture: validate once per session/evidence fingerprint."""

import hashlib
import json
import logging

import streamlit as st

from archimind.assets.render_assets import product_release
from archimind.examples.sample_product_room import create_sample_product_fixture
from archimind.geometry import (
    AccessibilityConfig,
    AccessibilityValidationReport,
    validate_accessibility,
)
from archimind.render.selected_realistic import render_selected_realistic_scene

VALIDATION_KEY = "charles_fixture_validation"


def render_validated_product_fixture() -> None:
    try:
        _render_fixture()
    except Exception:
        logging.getLogger(__name__).exception("Standalone product fixture unavailable")
        st.error(
            "The standalone product fixture or its validation is unavailable. The selected layout is preserved."
        )


def _render_fixture() -> None:
    fixture = create_sample_product_fixture()
    config = AccessibilityConfig()
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "fixture_contract_version": 1,
                "design": fixture.design.model_dump(mode="json"),
                "bindings": [p.metadata_sha256 for p in fixture.planning_bindings],
                "config": config.model_dump(mode="json"),
                "render_release": product_release().model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    cached = st.session_state.get(VALIDATION_KEY)
    report = None
    if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == fingerprint:
        try:
            report = AccessibilityValidationReport.model_validate_json(cached[1])
        except (ValueError, TypeError):
            report = None
    if report is None:
        report = validate_accessibility(
            fixture.design, config=config, area_tolerance_m2=0.0
        )
        # Only report JSON and its fingerprint persist; never a second canonical design.
        st.session_state[VALIDATION_KEY] = (fingerprint, report.model_dump_json())
    if report.status != "passed":
        st.error(
            "The standalone Charles fixture did not pass deterministic spatial checks. No approved fixture rendering is shown."
        )
        return
    st.caption(
        "Standalone Charles fixture · deterministic spatial validation: passed. Not a generated alternative or architectural certification."
    )
    render_selected_realistic_scene(
        fixture.design,
        planning_bindings={p.furniture_id: p for p in fixture.planning_bindings},
        key="experimental-product-room",
    )
