"""Selected-layout E2 handoff and Streamlit controls; all model calls are mocked."""

import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.agents import requirements_agent as api
from archimind.examples import create_sample_bedroom
from archimind.examples.style_bedroom import offline_interior_stylist
from archimind.geometry import generate_layout_candidates
from archimind.ui import interior_styling as ui
from archimind.ui import layout_generation as layouts
from archimind.workflow import (
    DesignRequest,
    WorkflowState,
    nodes,
    style_selected_layout,
)

APP = Path(__file__).resolve().parents[1] / "app.py"
STYLE = "Scandinavian bedroom with warm white walls, light oak furniture, and muted sage accents."


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("07F tests forbid network and external processes")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for name in (
        "ARCHIMIND_ENABLE_OPENAI_STYLIST",
        "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS",
        "ARCHIMIND_ENABLE_OPENAI_LAYOUT",
        "ARCHIMIND_ENABLE_OPENAI_CRITIC",
        "OPENAI_API_KEY",
        "ARCHIMIND_OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    client = Mock(side_effect=AssertionError("No live SDK client"))
    monkeypatch.setattr(api, "_client", client)
    yield client
    client.assert_not_called()
    assert not attempts


@pytest.fixture(scope="module")
def source_generation():
    design = create_sample_bedroom()
    return generate_layout_candidates(design.room, design.furniture)


@pytest.fixture
def generation(source_generation):
    return source_generation.model_copy(deep=True)


@pytest.fixture
def request_data():
    return DesignRequest(specification=create_sample_bedroom(), style_request=STYLE)


@pytest.fixture
def app(monkeypatch):
    generator = Mock(wraps=layouts.generate_layout_candidates)
    styler = Mock(wraps=style_selected_layout)
    monkeypatch.setattr(layouts, "generate_layout_candidates", generator)
    monkeypatch.setattr(ui, "style_selected_layout", styler)
    application = AppTest.from_file(str(APP), default_timeout=30).run()
    return SimpleNamespace(view=application, generator=generator, styler=styler)


def generate(app):
    app.view.button(key="generate_layouts").click().run()
    assert not app.view.exception
    return app.view.session_state[layouts.RESULT_KEY]


def enable_ai(app, monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")

    def mocked(*args, **kwargs):
        return style_selected_layout(
            *args, **kwargs, interior_stylist=offline_interior_stylist
        )

    app.styler.side_effect = mocked
    app.view.checkbox(key=ui.ENABLE_KEY).check().run()
    app.view.selectbox(key=ui.THEME_KEY).select("scandinavian").run()
    return app.view


def request_ai(view):
    view.checkbox(key=ui.CONSENT_KEY).check().run()
    view.button(key="request_ai_styling").click().run()
    assert not view.exception


@pytest.mark.parametrize("index", [0, 1])
def test_selected_entry_fixture_preserves_original_indices_and_all_data(
    monkeypatch, generation, request_data, index
):
    before = generation.model_dump_json()
    request_before = request_data.model_dump_json()
    generator = Mock(side_effect=AssertionError("Do not regenerate"))
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    result = style_selected_layout(request_data, generation, index)
    assert result.status == "succeeded" and result.selection_source == "user_selection"
    assert result.selected_candidate_index == index
    assert result.approved_design == generation.candidates[index].design
    assert result.generation.model_dump_json() == before == generation.model_dump_json()
    assert (
        result.request.model_dump_json()
        == request_before
        == request_data.model_dump_json()
    )
    assert (
        result.iteration_count == 0
        and result.layout_recommendation.deterministic_candidate_index is None
    )
    assert [event.node for event in result.trace] == [
        "spatial_critic",
        "interior_stylist",
    ]
    assert (
        not result.layout_recommendation.executed
        and not result.spatial_critique.executed
    )
    assert (
        result.styling.theme == "neutral"
        and result.ai_styling.source == "deterministic_fixture"
    )
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    generator.assert_not_called()


@pytest.mark.parametrize("index", [0, 1])
def test_selected_entry_uses_e1_e2_without_regeneration(
    monkeypatch, generation, request_data, index
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")
    callback = Mock(wraps=offline_interior_stylist)
    result = style_selected_layout(
        request_data,
        generation,
        index,
        use_ai_stylist=True,
        allow_live_stylist=True,
        interior_stylist=callback,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == index
    assert result.generation == generation
    assert result.ai_styling.result.mode == "offline_fixture"
    assert (
        result.ai_styling.result.context.request.candidate
        == generation.candidates[index]
    )
    assert result.ai_styling.result.plan.palette_id == "scandi_warm_sage"
    assert result.styling is None
    callback.assert_called_once()
    assert callback.call_args.kwargs == {"allow_live_usage": True}
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "requested,flag,consent,expected",
    [
        (False, "1", True, "not_requested"),
        (True, "0", True, "disabled"),
        (True, "1", False, "unavailable"),
    ],
)
def test_selected_entry_retains_all_authorization_gates(
    monkeypatch, generation, request_data, requested, flag, consent, expected
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", flag)
    callback = Mock()
    result = style_selected_layout(
        request_data,
        generation,
        1,
        use_ai_stylist=requested,
        allow_live_stylist=consent,
        interior_stylist=callback,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert result.ai_styling.status == expected and not result.ai_styling.executed
    assert result.ai_styling.source == "deterministic_fixture"
    callback.assert_not_called()


def test_panel_inactive_by_default_and_fixture_is_explicit(app):
    assert ui.RESULT_KEY not in app.view.session_state
    app.styler.assert_not_called()
    source = generate(app)
    assert not app.view.checkbox(key=ui.ENABLE_KEY).value
    assert ui.RESULT_KEY not in app.view.session_state
    app.view.run()
    app.styler.assert_not_called()
    before = source.model_dump_json()
    app.view.button(key="show_fixture_styling").click().run()
    assert not app.view.exception
    assert any(
        "Deterministic fixture — AI was not requested" in element.value
        for element in app.view.success
    )
    result = app.view.session_state[ui.RESULT_KEY][1]
    assert result.styling.theme == "neutral"
    assert result.generation.model_dump_json() == before
    assert app.view.session_state[layouts.RESULT_KEY] is source
    app.generator.assert_called_once()
    app.styler.assert_called_once()
    assert app.styler.call_args.kwargs == {
        "use_ai_stylist": False,
        "allow_live_stylist": False,
    }


def test_panel_flag_and_consent_do_not_implicitly_authorize(app, monkeypatch):
    generate(app)
    app.view.checkbox(key=ui.ENABLE_KEY).check().run()
    assert app.view.button(key="request_ai_styling").disabled
    assert app.view.checkbox(key=ui.CONSENT_KEY).disabled
    assert any(
        "not enabled for this deployment" in element.value for element in app.view.info
    )
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")
    app.view.run()
    assert not app.view.checkbox(key=ui.CONSENT_KEY).value
    assert app.view.button(key="request_ai_styling").disabled
    app.view.checkbox(key=ui.CONSENT_KEY).check().run()
    assert not app.view.button(key="request_ai_styling").disabled
    app.styler.assert_not_called()


def test_mock_ai_display_preserves_source_and_consumes_consent(app, monkeypatch):
    source = generate(app)
    before = source.model_dump_json()
    view = enable_ai(app, monkeypatch)
    view.text_area(key=ui.PREFERENCE_KEY).input("Muted sage accents.").run()
    request_ai(view)
    assert any(
        "Mocked AI stylist — offline fixture" in element.value
        for element in view.success
    )
    assert any(
        "not applied to the 2D or 3D" in element.value for element in view.caption
    )
    assert not view.checkbox(key=ui.CONSENT_KEY).value
    assert view.button(key="request_ai_styling").disabled
    assert view.session_state[layouts.RESULT_KEY] is source
    assert source.model_dump_json() == before
    assert view.session_state[layouts.SELECTION_KEY] == "Layout A"
    finishes = next(
        element.value
        for element in view.dataframe
        if "Furniture ID" in element.value.columns
    )
    assert set(finishes["Furniture ID"]) == {
        item.id for item in source.candidates[0].design.furniture
    }
    call = app.styler.call_args
    assert call.args[0].soft_preferences == ["Muted sage accents."]
    assert call.kwargs == {"use_ai_stylist": True, "allow_live_stylist": True}
    view.run()
    app.styler.assert_called_once()
    app.generator.assert_called_once()


def test_layout_switch_clears_result_and_does_not_request_or_generate(app):
    generate(app)
    app.view.button(key="show_fixture_styling").click().run()
    for label in ("Layout B", "Layout A"):
        app.view.radio(key=layouts.SELECTION_KEY).set_value(label).run()
        assert not app.view.exception
        assert ui.RESULT_KEY not in app.view.session_state
        assert any(
            f"No styling requested for {label}" in element.value
            for element in app.view.info
        )
    app.styler.assert_called_once()
    app.generator.assert_called_once()


def test_pending_seed_edit_keeps_styling_bound_to_displayed_generation(app):
    source = generate(app)
    app.view.button(key="show_fixture_styling").click().run()
    app.view.number_input(key="layout_seed").set_value(99).run()
    assert ui.RESULT_KEY in app.view.session_state
    assert app.view.session_state[ui.RESULT_KEY][1].request.seed == source.seed == 42
    app.styler.assert_called_once()
    generate(app)
    assert ui.RESULT_KEY not in app.view.session_state
    assert app.view.session_state[layouts.RESULT_KEY].seed == 99


def test_unexpected_error_is_sanitized_and_retry_keeps_layout(app):
    source = generate(app)
    app.styler.side_effect = RuntimeError("secret-token /private/path")
    app.view.button(key="show_fixture_styling").click().run()
    assert not app.view.exception
    assert any(
        "Could not prepare styling" in element.value for element in app.view.error
    )
    assert all(
        "secret-token" not in element.value and "/private/path" not in element.value
        for element in app.view.error
    )
    assert app.view.session_state[layouts.RESULT_KEY] is source
    assert not app.view.session_state[ui.INFLIGHT_KEY]
    app.styler.side_effect = None
    app.view.button(key="show_fixture_styling").click().run()
    assert not app.view.exception and ui.ERROR_KEY not in app.view.session_state
    assert app.view.session_state[ui.RESULT_KEY][1].status == "succeeded"
    app.generator.assert_called_once()
