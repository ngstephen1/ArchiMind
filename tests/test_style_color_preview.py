"""Catalog-color mapping changes appearance only; real clients and networking forbidden."""

import json
import socket
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.agents import requirements_agent as api
from archimind.agents.interior_stylist_catalog import PALETTES, THEMES
from archimind.agents.interior_stylist_grounding import (
    interpret_style_proposal,
    prepare_stylist_context,
)
from archimind.agents.interior_stylist_schemas import (
    InteriorStyleProposal,
    InteriorStylistError,
    InteriorStylistRequest,
    InteriorStylistResult,
)
from archimind.examples import create_sample_bedroom
from archimind.examples.style_bedroom import offline_interior_stylist
from archimind.geometry import generate_layout_candidates
from archimind.render import (
    StyleColorPreviewError,
    render_design_3d,
    render_styled_design_3d,
)
from archimind.ui import interior_styling as styling
from archimind.ui import layout_generation as layouts
from archimind.workflow import style_selected_layout

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("No network or real model client")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(api, "_client", forbidden)
    monkeypatch.delenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", raising=False)
    yield
    assert not attempts


@pytest.fixture(scope="module")
def generation():
    design = create_sample_bedroom()
    return generate_layout_candidates(design.room, design.furniture)


def checked_advice(candidate, theme="scandinavian"):
    palette = PALETTES[THEMES[theme].palette_ids[0]]
    request = InteriorStylistRequest(
        candidate=candidate, style_request=f"{THEMES[theme].label} interior."
    )
    proposal = InteriorStyleProposal(
        decision="style",
        theme_id=theme,
        palette_id=palette.palette_id,
        wall_material_id=palette.wall_material_ids[0],
        floor_material_id=palette.floor_material_ids[0],
        furniture_finishes=[
            {"furniture_id": item.id, "material_id": palette.furniture_material_ids[0]}
            for item in candidate.design.furniture
        ],
        accent_ids=[palette.accent_ids[0]],
        rationale_code="coherent_palette",
        preference_assessments=[{"preference_index": 0, "judgment": "favored"}],
        conflict_codes=[],
    )
    return interpret_style_proposal(
        prepare_stylist_context(request), proposal, mode="offline_fixture"
    )


def assert_only_colors_changed(original, preview):
    assert len(original.data) == len(preview.data)
    for first, second in zip(original.data, preview.data, strict=True):
        left, right = first.to_plotly_json(), second.to_plotly_json()
        if first.meta["kind"] in ("wall", "floor", "furniture"):
            right["color"] = left["color"]
        assert left == right
    left, right = original.layout.to_plotly_json(), preview.layout.to_plotly_json()
    del right["meta"]["style_preview"]
    assert left == right


@pytest.mark.parametrize("theme", list(THEMES))
@pytest.mark.parametrize("index", [0, 1])
def test_catalog_colors_preserve_entire_geometry_camera_and_source(
    generation, theme, index
):
    candidate = generation.candidates[index]
    advice = checked_advice(candidate, theme)
    before = generation.model_dump_json(), advice.model_dump_json()
    original = render_design_3d(candidate.design)
    preview = render_styled_design_3d(candidate.design, advice)
    assert_only_colors_changed(original, preview)
    for trace in preview.data:
        if trace.meta["kind"] == "wall":
            assert trace.color == advice.plan.wall_finish.base_color_hex
        elif trace.meta["kind"] == "floor":
            assert trace.color == advice.plan.floor_finish.base_color_hex
        elif trace.meta["kind"] == "furniture":
            assert (
                trace.color
                == advice.plan.furniture_finishes[trace.meta["id"]].base_color_hex
            )
    assert preview.layout.meta["style_preview"]["provenance"] == "offline_fixture"
    assert not preview.layout.meta["style_preview"]["physical_materials"]
    assert not preview.layout.meta["style_preview"]["accents_applied"]
    assert (generation.model_dump_json(), advice.model_dump_json()) == before
    assert advice.plan.rendered is False
    assert render_design_3d(candidate.design) == original


def test_stale_plan_cannot_color_another_candidate(generation):
    with pytest.raises(StyleColorPreviewError):
        render_styled_design_3d(
            generation.candidates[1].design, checked_advice(generation.candidates[0])
        )


@pytest.mark.parametrize(
    "case", ["color", "id", "palette", "catalog", "provenance", "model"]
)
def test_forged_or_unknown_metadata_is_rejected(generation, case):
    candidate = generation.candidates[0]
    advice = checked_advice(candidate)
    if case == "color":
        advice.plan.wall_finish = advice.plan.wall_finish.model_copy(
            update={"base_color_hex": "#000000"}
        )
    elif case == "id":
        advice.plan.furniture_finishes["unknown-object"] = advice.plan.wall_finish
    elif case == "palette":
        advice.plan.palette_id = "neutral_sand"
    elif case == "catalog":
        advice.context.catalog = advice.context.catalog.model_copy(
            update={"version": "fake"}
        )
    elif case == "provenance":
        advice.mode = "not_evaluated"
    else:
        advice.model = "fake-model"
    with pytest.raises(StyleColorPreviewError):
        render_styled_design_3d(candidate.design, advice)


@pytest.mark.parametrize("status", ["error", "unavailable"])
def test_failed_advice_has_no_color_preview(generation, status):
    advice = InteriorStylistResult(
        status=status,
        message="Failure",
        error=InteriorStylistError(code="timeout", message="Failure"),
    )
    with pytest.raises(StyleColorPreviewError):
        render_styled_design_3d(generation.candidates[0].design, advice)


def test_preview_does_not_generate_validate_or_invoke_stylist(monkeypatch, generation):
    candidate = generation.candidates[0]
    advice = checked_advice(candidate)
    forbidden = Mock(
        side_effect=AssertionError("Display changes do not execute backend work")
    )
    monkeypatch.setattr(
        "archimind.agents.interior_stylist_grounding.validate_accessibility", forbidden
    )
    monkeypatch.setattr("archimind.geometry.validate_accessibility", forbidden)
    monkeypatch.setattr("archimind.geometry.generate_layout_candidates", forbidden)
    monkeypatch.setattr(
        "archimind.agents.interior_stylist_agent.recommend_style", forbidden
    )
    assert render_styled_design_3d(candidate.design, advice).layout.meta[
        "style_preview"
    ]
    forbidden.assert_not_called()


def figure(app, key):
    return json.loads(
        next(chart.proto.spec for chart in app.get("plotly_chart") if chart.key == key)
    )


def styled_app(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")
    generator = Mock(wraps=layouts.generate_layout_candidates)
    monkeypatch.setattr(layouts, "generate_layout_candidates", generator)
    styler = Mock(
        side_effect=lambda *args, **kwargs: style_selected_layout(
            *args, **kwargs, interior_stylist=offline_interior_stylist
        )
    )
    monkeypatch.setattr(styling, "style_selected_layout", styler)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="generate_layouts").click().run()
    app.checkbox(key=styling.ENABLE_KEY).check().run()
    app.selectbox(key=styling.THEME_KEY).select("scandinavian").run()
    app.checkbox(key=styling.CONSENT_KEY).check().run()
    app.button(key="request_ai_styling").click().run()
    assert not app.exception
    return app, generator, styler


def test_selected_preview_is_opt_in_reversible_and_keeps_2d_data(monkeypatch):
    app, generator, styler = styled_app(monkeypatch)
    source = app.session_state[layouts.RESULT_KEY]
    before = source.model_dump_json()
    plan = figure(app, "generated-floorplan")
    original = figure(app, "generated-design-3d")
    assert not app.checkbox(key=styling.PREVIEW_KEY).value
    app.checkbox(key=styling.PREVIEW_KEY).check().run()
    assert not app.exception
    colored = figure(app, "generated-design-3d")
    assert colored["layout"]["meta"]["style_preview"]["kind"] == "catalog_flat_color"
    assert figure(app, "generated-floorplan") == plan
    assert source.model_dump_json() == before
    app.run()
    app.checkbox(key=styling.PREVIEW_KEY).uncheck().run()
    assert figure(app, "generated-design-3d") == original
    generator.assert_called_once()
    styler.assert_called_once()


@pytest.mark.parametrize(
    "change", ["selection", "preference", "regeneration", "fixture"]
)
def test_preview_clears_with_replaced_or_fallback_style(monkeypatch, change):
    app, _, styler = styled_app(monkeypatch)
    app.checkbox(key=styling.PREVIEW_KEY).check().run()
    if change == "selection":
        app.radio(key=layouts.SELECTION_KEY).set_value("Layout B").run()
    elif change == "preference":
        app.text_area(key=styling.PREFERENCE_KEY).input("A new preference.").run()
    elif change == "regeneration":
        app.button(key="generate_layouts").click().run()
    else:
        app.button(key="show_fixture_styling").click().run()
    assert not app.exception
    assert "style_preview" not in figure(app, "generated-design-3d")["layout"]["meta"]
    assert not any(box.key == styling.PREVIEW_KEY for box in app.checkbox)
    assert styler.call_count == (2 if change == "fixture" else 1)


def test_offline_demo_verifies_geometry_and_leaves_plan_metadata_unchanged():
    from archimind.examples.preview_style_colors import offline_color_preview

    workflow, advice, figure = offline_color_preview()
    assert workflow.selected_candidate_index == 0
    assert workflow.generation.candidates[0].score.total == 67.721925
    assert advice.mode == "offline_fixture" and advice.plan.rendered is False
    assert figure.layout.meta["style_preview"]["palette_id"] == "scandi_warm_sage"


@pytest.mark.parametrize("as_json", [False, True])
def test_offline_cli_exports_labeled_self_contained_html(
    monkeypatch, tmp_path, capsys, as_json
):
    from archimind.examples.preview_style_colors import main

    output = tmp_path / "color-preview.html"
    monkeypatch.setattr(
        sys,
        "argv",
        ["preview_style_colors", "--output", str(output)]
        + (["--json"] if as_json else []),
    )
    assert main() == 0
    stdout = capsys.readouterr().out
    content = output.read_text()
    assert "Offline mock — catalog-color preview" in content and "plotly.js" in content
    assert "<script src=" not in content
    if as_json:
        payload = json.loads(stdout)
        assert payload["mode"] == "offline_mock" and payload["geometry_unchanged"]
        assert not payload["metadata_rendered"]
    else:
        assert "OFFLINE MOCK" in stdout and "zero live model requests" in stdout
