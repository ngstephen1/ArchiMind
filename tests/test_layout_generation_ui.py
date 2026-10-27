"""Button-driven Streamlit integration with real seeded layouts and error cases."""

import json
from pathlib import Path
from unittest.mock import Mock

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from archimind.examples import create_sample_bedroom
from archimind.geometry import (
    AccessibilityConfig,
    LayoutGenerationResult,
    generate_layout_candidates,
)
from archimind.ui import layout_generation as ui

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _floorplans(app: AppTest) -> list:
    """Count the 2D previews independently of the new structural 3D chart."""
    return [
        chart
        for chart in app.get("plotly_chart")
        if json.loads(chart.proto.spec)["layout"].get("meta", {}).get("kind")
        != "room_3d"
    ]


@pytest.fixture
def app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=30).run()


@pytest.fixture
def generator_spy(monkeypatch) -> Mock:
    spy = Mock(wraps=generate_layout_candidates)
    monkeypatch.setattr(ui, "generate_layout_candidates", spy)
    return spy


@pytest.fixture(scope="module")
def example_result() -> LayoutGenerationResult:
    specification = create_sample_bedroom()
    return generate_layout_candidates(specification.room, specification.furniture)


def _generate(app: AppTest) -> AppTest:
    return app.button(key="generate_layouts").click().run()


def _result(app: AppTest) -> LayoutGenerationResult:
    return app.session_state[ui.RESULT_KEY]


def _empty_outcome(
    example: LayoutGenerationResult, status: str, *, seed: int = 42
) -> LayoutGenerationResult:
    data = example.model_dump()
    data.update(
        status=status,
        seed=seed,
        candidates=[],
        attempts_used=500 if status == "search_exhausted" else 0,
        rejections={},
        message="No candidates available for this request.",
    )
    return LayoutGenerationResult.model_validate(data)


def _expected_positions(candidate) -> list[dict]:
    return [
        {
            "Furniture": item.name,
            "X (m)": item.x_m,
            "Y (m)": item.y_m,
            "Width (m)": item.width_m,
            "Depth (m)": item.depth_m,
        }
        for item in candidate.design.furniture
    ]


def test_app_loads_without_automatically_generating(
    app: AppTest, generator_spy: Mock
) -> None:
    app.run()
    assert not app.exception
    assert "AI-Assisted Room Layout Generator" in [
        heading.value for heading in app.subheader
    ]
    assert app.number_input(key="layout_seed").value == 42
    assert len(_floorplans(app)) == 1  # Task 03 demonstration remains visible.
    assert len(app.radio) == 0
    assert not app.dataframe
    generator_spy.assert_not_called()
    assert any(
        "5 m wide × 4 m deep × 2.7 m high" in text.value for text in app.markdown
    )
    assert any("deterministic seeded" in text.value for text in app.markdown)


def test_generate_calls_existing_api_with_expected_sample_and_options(
    app: AppTest, generator_spy: Mock
) -> None:
    _generate(app)
    assert not app.exception
    expected = create_sample_bedroom()
    generator_spy.assert_called_once_with(
        expected.room, expected.furniture, seed=42, max_candidates=2, max_attempts=500
    )
    assert _result(app).status == "complete"
    assert _result(app).seed == 42
    assert app.radio(key=ui.SELECTION_KEY).options == ["Layout A", "Layout B"]
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout A"
    assert app.success[0].value == "Generation complete: 2 validated alternatives."


def test_comparison_shows_both_actual_scores_and_report_counts(app: AppTest) -> None:
    _generate(app)
    rows = app.dataframe[0].value.to_dict("records")
    for label, candidate, row in zip("AB", _result(app).candidates, rows, strict=True):
        assert row == {
            "Layout": f"Layout {label}",
            "Score (0–100)": candidate.score.total,
            "Validation": candidate.validation.status,
            "Reported issues": len(candidate.validation.violations),
            "Advisory warnings": sum(
                issue.severity == "warning" for issue in candidate.validation.violations
            ),
        }


@pytest.mark.parametrize(("label", "index"), [("Layout A", 0), ("Layout B", 1)])
def test_selected_layout_table_and_plot_use_actual_generated_coordinates(
    app: AppTest, label: str, index: int
) -> None:
    _generate(app)
    app.radio(key=ui.SELECTION_KEY).set_value(label).run()
    assert not app.exception
    candidate = _result(app).candidates[index]
    assert app.dataframe[1].value.to_dict("records") == _expected_positions(candidate)
    chart = _floorplans(app)[1]
    figure = go.Figure(json.loads(chart.proto.spec))
    for item in candidate.design.furniture:
        trace = next(
            trace
            for trace in figure.data
            if trace.meta.get("kind") == "furniture" and trace.meta["id"] == item.id
        )
        assert min(trace.x) == item.x_m
        assert min(trace.y) == item.y_m
        assert max(trace.x) == pytest.approx(item.x_m + item.width_m)
        assert max(trace.y) == pytest.approx(item.y_m + item.depth_m)
    assert figure.layout.yaxis.scaleanchor == "x"
    assert figure.layout.yaxis.scaleratio == 1


def test_switching_and_normal_reruns_do_not_generate_or_revalidate(
    app: AppTest, generator_spy: Mock, monkeypatch
) -> None:
    validation_spy = Mock(wraps=ui.validate_accessibility)
    monkeypatch.setattr(ui, "validate_accessibility", validation_spy)
    _generate(app)
    assert validation_spy.call_count == 2
    before = _result(app).model_dump_json()
    app.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    app.run()
    app.run()
    generator_spy.assert_called_once()
    assert validation_spy.call_count == 2
    assert _result(app).model_dump_json() == before
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout B"


def test_seed_change_keeps_existing_result_and_selection_until_button_click(
    app: AppTest, generator_spy: Mock
) -> None:
    _generate(app)
    app.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    before = _result(app).model_dump_json()
    app.number_input(key="layout_seed").set_value(43).run()
    assert not app.exception
    generator_spy.assert_called_once()
    assert _result(app).model_dump_json() == before
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout B"
    assert any("still use seed 42" in item.value for item in app.info)


def test_explicit_generation_with_new_seed_replaces_result_and_resets_selection(
    app: AppTest, generator_spy: Mock
) -> None:
    _generate(app)
    app.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    before = _result(app).candidates[0].design.model_dump_json()
    app.number_input(key="layout_seed").set_value(43).run()
    _generate(app)
    assert not app.exception
    assert generator_spy.call_count == 2
    assert generator_spy.call_args.kwargs["seed"] == 43
    assert _result(app).seed == 43
    assert _result(app).candidates[0].design.model_dump_json() != before
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout A"
    assert app.dataframe[1].value.to_dict("records") == _expected_positions(
        _result(app).candidates[0]
    )


def test_validation_summary_and_required_sections_are_displayed(app: AppTest) -> None:
    _generate(app)
    text = [item.value for item in app.markdown]
    for heading in (
        "Room Information",
        "Layout Generation Controls",
        "Generated Alternatives",
        "Selected 2D Floor Plan",
        "Spatial Validation Summary",
    ):
        assert f"### {heading}" in text
    assert any("Validation status: **passed**" in item for item in text)
    assert any("Reported violations: **0**" in item for item in text)
    assert app.dataframe[2].value["Result"].tolist() == ["passed"] * 4
    assert any("Heuristic comparison score" in item.value for item in app.caption)


@pytest.mark.parametrize("status", ["search_exhausted", "infeasible", "unsupported"])
def test_no_candidate_statuses_are_explicit_and_do_not_render_empty_layouts(
    app: AppTest,
    generator_spy: Mock,
    example_result: LayoutGenerationResult,
    status: str,
) -> None:
    generator_spy.side_effect = None
    generator_spy.return_value = _empty_outcome(example_result, status)
    _generate(app)
    assert not app.exception
    assert _result(app).status == status
    assert len(_floorplans(app)) == 1
    assert not app.radio and not app.dataframe
    assert any("No validated alternatives" in item.value for item in app.info)
    if status == "search_exhausted":
        assert "does not prove" in app.warning[0].value
        assert not app.error
    elif status == "infeasible":
        assert "Infeasible under" in app.error[0].value
    else:
        assert "cannot be evaluated" in app.error[0].value


def test_single_valid_candidate_is_displayed_after_search_exhaustion(
    app: AppTest, generator_spy: Mock, example_result: LayoutGenerationResult
) -> None:
    data = example_result.model_dump()
    data.update(
        status="search_exhausted",
        candidates=data["candidates"][:1],
        message="One alternative found within the budget.",
    )
    generator_spy.side_effect = None
    generator_spy.return_value = LayoutGenerationResult.model_validate(data)
    _generate(app)
    assert not app.exception
    assert app.radio(key=ui.SELECTION_KEY).options == ["Layout A"]
    assert len(app.dataframe[0].value) == 1
    assert len(_floorplans(app)) == 2
    assert "1 of 2" in app.warning[0].value
    assert not app.success


def test_advisory_warnings_and_counts_are_shown_without_hiding_passing_status(
    app: AppTest, generator_spy: Mock
) -> None:
    source = create_sample_bedroom()
    config = AccessibilityConfig(advisory_door_depth_m=4.0, advisory_side_margin_m=5.0)
    warning_result = generate_layout_candidates(
        source.room, source.furniture, config=config
    )
    generator_spy.side_effect = None
    generator_spy.return_value = warning_result
    _generate(app)
    assert not app.exception
    candidate = _result(app).candidates[0]
    warnings = candidate.validation.violations
    assert warnings and all(issue.severity == "warning" for issue in warnings)
    assert [warning.value for warning in app.warning] == [
        issue.message for issue in warnings
    ]
    row = app.dataframe[0].value.to_dict("records")[0]
    assert row["Advisory warnings"] == row["Reported issues"] == len(warnings)
    assert row["Validation"] == "passed"


def test_initial_exception_shows_error_without_crashing_or_rendering_candidates(
    app: AppTest, generator_spy: Mock
) -> None:
    generator_spy.side_effect = RuntimeError("Simulated failure")
    _generate(app)
    assert not app.exception
    assert "Could not generate layouts" in app.error[0].value
    assert len(_floorplans(app)) == 1
    assert not app.radio


def test_exception_keeps_previous_result_and_selection_and_successful_retry_clears_error(
    app: AppTest, generator_spy: Mock
) -> None:
    _generate(app)
    app.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    before = _result(app).model_dump_json()
    generator_spy.side_effect = RuntimeError("Simulated failure")
    app.number_input(key="layout_seed").set_value(43).run()
    _generate(app)
    assert not app.exception
    assert _result(app).model_dump_json() == before
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout B"
    assert any("previous generation result" in item.value for item in app.info)
    assert app.error
    generator_spy.side_effect = None
    _generate(app)
    assert not app.exception
    assert not app.error
    assert _result(app).seed == 43
    assert app.radio(key=ui.SELECTION_KEY).value == "Layout A"


def test_normal_failed_result_replaces_prior_alternatives(
    app: AppTest, generator_spy: Mock, example_result: LayoutGenerationResult
) -> None:
    _generate(app)
    generator_spy.side_effect = None
    generator_spy.return_value = _empty_outcome(example_result, "unsupported", seed=43)
    app.number_input(key="layout_seed").set_value(43).run()
    _generate(app)
    assert not app.exception
    assert _result(app).seed == 43
    assert _result(app).candidates == []
    assert not app.radio and not app.dataframe
    assert len(_floorplans(app)) == 1


def test_invalid_geometry_with_a_stale_passing_report_is_not_displayed(
    app: AppTest, generator_spy: Mock, example_result: LayoutGenerationResult
) -> None:
    damaged = example_result.model_copy(deep=True)
    damaged.candidates[0].design.furniture[0].x_m = -10.0
    generator_spy.side_effect = None
    generator_spy.return_value = damaged
    _generate(app)
    assert not app.exception
    assert app.error
    assert not app.radio and not app.dataframe
    assert len(_floorplans(app)) == 1


def test_unsupported_rotation_message_is_preserved(
    app: AppTest, generator_spy: Mock
) -> None:
    source = create_sample_bedroom()
    source.furniture[0].rotation_deg = 90
    generator_spy.side_effect = None
    generator_spy.return_value = generate_layout_candidates(
        source.room, source.furniture
    )
    _generate(app)
    assert not app.exception
    assert any("only 0-degree" in item.value for item in app.caption)
    assert len(_floorplans(app)) == 1


def test_separate_sessions_do_not_share_generation_results(generator_spy: Mock) -> None:
    first = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    _generate(first)
    second = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not second.exception
    assert len(_floorplans(second)) == 1
    assert not second.radio
    generator_spy.assert_called_once()
