"""Selected RoomDesign identity, view correspondence and session-state contracts."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from archimind.examples import create_sample_bedroom
from archimind.geometry import LayoutGenerationResult
from archimind.render import render_design_3d, render_room_3d
from archimind.ui import layout_generation as ui

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def spies(monkeypatch):
    result = SimpleNamespace(
        generator=Mock(wraps=ui.generate_layout_candidates),
        validator=Mock(wraps=ui.validate_accessibility),
        plan=Mock(wraps=ui.render_floorplan),
        scene=Mock(wraps=ui.render_design_3d),
    )
    for name, spy in [
        ("generate_layout_candidates", result.generator),
        ("validate_accessibility", result.validator),
        ("render_floorplan", result.plan),
        ("render_design_3d", result.scene),
    ]:
        monkeypatch.setattr(ui, name, spy)
    return result


@pytest.fixture
def app(spies):
    return AppTest.from_file(str(APP_PATH), default_timeout=30).run()


def _figure(app, key):
    return go.Figure(
        json.loads(
            next(
                chart for chart in app.get("plotly_chart") if chart.key == key
            ).proto.spec
        )
    )


def _result(app):
    return app.session_state[ui.RESULT_KEY]


def _generate(app):
    return app.button(key="generate_layouts").click().run()


def _selected_charts(app):
    return [
        chart
        for chart in app.get("plotly_chart")
        if chart.key in {"generated-floorplan", "generated-design-3d"}
    ]


def _assert_selected(app, index, spies):
    candidate = _result(app).candidates[index]
    # Both calls receive the actual stored object; no independent selected-design state.
    assert spies.plan.call_args.args[0] is candidate.design
    assert spies.scene.call_args.args[0] is candidate.design
    plan = _figure(app, "generated-floorplan")
    scene = _figure(app, "generated-design-3d")
    expected_ids = {item.id for item in candidate.design.furniture}
    for figure in (plan, scene):
        assert {
            t.meta["id"] for t in figure.data if t.meta.get("kind") == "furniture"
        } == expected_ids
        assert figure.layout.meta["room_id"] == candidate.design.room.id
    for item in candidate.design.furniture:
        footprint = next(
            t
            for t in plan.data
            if t.meta.get("kind") == "furniture" and t.meta["id"] == item.id
        )
        parts = [
            t
            for t in scene.data
            if t.meta.get("kind") == "furniture" and t.meta["id"] == item.id
        ]
        assert min(footprint.x) == min(v for t in parts for v in t.x) == item.x_m
        assert min(footprint.y) == min(v for t in parts for v in t.y) == item.y_m
        assert max(footprint.x) == pytest.approx(
            max(v for t in parts for v in t.x), abs=1e-12
        )
        assert max(footprint.y) == pytest.approx(
            max(v for t in parts for v in t.y), abs=1e-12
        )
        for part in parts:
            assert part.meta["name"] == item.name
            assert part.meta["category"] == item.category
            assert part.meta["width_m"] == item.width_m
            assert part.meta["depth_m"] == item.depth_m
            assert part.meta["height_m"] == item.height_m
        assert min(v for t in parts for v in t.z) == 0
        assert max(v for t in parts for v in t.z) == item.height_m
    # All room/opening vertices, triangles, IDs, and hover information are retained.
    expected = render_room_3d(candidate.design.room)
    for actual, original in zip(
        scene.data[: len(expected.data)], expected.data, strict=True
    ):
        first, second = actual.to_plotly_json(), original.to_plotly_json()
        first.pop("showlegend", None)
        second.pop("showlegend", None)
        assert first == second
    return candidate


def test_no_selection_before_generation_and_standalone_samples_are_explicit(app, spies):
    assert not app.exception
    assert not _selected_charts(app)
    assert {chart.key for chart in app.get("plotly_chart")} == {
        "sample-floorplan",
        "room-3d",
        "design-3d",
    }
    assert any(
        "Fixed sample bedroom — independent of the selected Layout A/B." in c.value
        for c in app.caption
    )
    spies.generator.assert_not_called()
    spies.validator.assert_not_called()
    spies.plan.assert_not_called()
    spies.scene.assert_not_called()


@pytest.mark.parametrize("label,index", [("Layout A", 0), ("Layout B", 1)])
def test_both_views_receive_exact_selected_design_and_geometry(
    app, spies, label, index
):
    _generate(app)
    before = _result(app).model_dump_json()
    app.radio(key=ui.SELECTION_KEY).set_value(label).run()
    assert not app.exception
    _assert_selected(app, index, spies)
    assert _result(app).model_dump_json() == before
    assert any(
        c.value.startswith(f"{label} · Same furniture and room data")
        for c in app.caption
    )


def test_switching_back_and_rerunning_neither_regenerates_nor_spatially_revalidates(
    app, spies
):
    _generate(app)
    assert spies.validator.call_count == 2
    before = _result(app).model_dump_json()
    first_scene = _figure(app, "generated-design-3d").to_json()
    for label, index in [("Layout B", 1), ("Layout A", 0), ("Layout B", 1)]:
        app.radio(key=ui.SELECTION_KEY).set_value(label).run()
        _assert_selected(app, index, spies)
    assert _figure(app, "generated-design-3d").to_json() != first_scene
    app.run()
    app.run()
    assert not app.exception
    _assert_selected(app, 1, spies)
    spies.generator.assert_called_once()
    assert spies.validator.call_count == 2
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout B"
    assert _result(app).model_dump_json() == before


def test_pending_seed_preserves_both_views_until_explicit_generation(app, spies):
    _generate(app)
    app.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    before = [
        _figure(app, key).to_json()
        for key in ("generated-floorplan", "generated-design-3d")
    ]
    app.number_input(key="layout_seed").set_value(43).run()
    assert before == [
        _figure(app, key).to_json()
        for key in ("generated-floorplan", "generated-design-3d")
    ]
    assert spies.generator.call_count == 1 and spies.validator.call_count == 2
    _generate(app)
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout A"
    assert _result(app).seed == 43
    _assert_selected(app, 0, spies)
    assert spies.generator.call_count == 2 and spies.validator.call_count == 4


@pytest.mark.parametrize("status", ["search_exhausted", "infeasible", "unsupported"])
def test_empty_outcomes_clear_both_selected_views(app, spies, status):
    _generate(app)
    data = _result(app).model_dump()
    data.update(
        status=status,
        candidates=[],
        message="No candidate available.",
        attempts_used=500 if status == "search_exhausted" else 0,
    )
    spies.generator.side_effect = None
    spies.generator.return_value = LayoutGenerationResult.model_validate(data)
    _generate(app)
    assert not app.exception
    assert not _selected_charts(app)
    assert not app.radio
    assert {chart.key for chart in app.get("plotly_chart")} == {
        "sample-floorplan",
        "room-3d",
        "design-3d",
    }


def test_generation_exception_keeps_both_previous_selected_views(app, spies):
    _generate(app)
    app.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    before = _result(app).model_dump_json()
    spies.generator.side_effect = RuntimeError("Simulated generation failure")
    _generate(app)
    assert not app.exception
    assert app.error
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout B"
    _assert_selected(app, 1, spies)
    assert _result(app).model_dump_json() == before


def test_initial_generation_exception_displays_no_selected_views(app, spies):
    spies.generator.side_effect = RuntimeError("Simulated generation failure")
    _generate(app)
    assert not app.exception
    assert app.error and not _selected_charts(app)
    spies.scene.assert_not_called()


def test_partial_generation_renders_its_one_candidate_in_both_views(app, spies):
    _generate(app)
    data = _result(app).model_dump()
    data.update(
        status="search_exhausted",
        candidates=data["candidates"][:1],
        message="One candidate available.",
    )
    spies.generator.side_effect = None
    spies.generator.return_value = LayoutGenerationResult.model_validate(data)
    _generate(app)
    assert not app.exception
    assert app.radio(key=ui.SELECTION_KEY).options == ["Layout A"]
    _assert_selected(app, 0, spies)


def test_bad_candidate_is_not_displayed_as_a_synchronized_layout(app, spies):
    _generate(app)
    damaged = _result(app).model_copy(deep=True)
    damaged.candidates[0].design.furniture[0].x_m = -10.0
    spies.generator.side_effect = None
    spies.generator.return_value = damaged
    # A fresh session must not inherit the prior successful result.
    fresh = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _generate(fresh)
    assert not fresh.exception
    assert fresh.error and not _selected_charts(fresh)


def test_framing_is_deterministic_compact_and_preserves_equal_physical_units():
    source = create_sample_bedroom()
    first, second = render_design_3d(source), render_design_3d(source)
    assert first.to_json() == second.to_json()
    assert first.layout.height < 600
    assert sum(first.layout.margin.to_plotly_json().values()) < 140
    assert [trace.name for trace in first.data if trace.showlegend] == ["Walls"]
    assert first.layout.scene.camera.center.z < 0
    scene = first.layout.scene
    scales = [
        getattr(scene.aspectratio, axis) / (limits[1] - limits[0])
        for axis, limits in zip(
            "xyz",
            [scene.xaxis.range, scene.yaxis.range, scene.zaxis.range],
            strict=True,
        )
    ]
    assert scales == pytest.approx([scales[0]] * 3)
