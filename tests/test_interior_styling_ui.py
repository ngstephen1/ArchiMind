"""Selected-layout E2 handoff and Streamlit controls; all model calls are mocked."""

import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.agents import requirements_agent as api
from archimind.agents.interior_stylist_catalog import THEMES
from archimind.agents.interior_stylist_grounding import interpret_style_proposal
from archimind.agents.interior_stylist_schemas import (
    InteriorStylistError,
    InteriorStylistResult,
)
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
    assert not app.view.checkbox(key=ui.ENABLE_KEY).value
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


@pytest.mark.parametrize(
    "case", ["outside", "no_door", "score", "report", "rotation", "specification"]
)
@pytest.mark.parametrize("ai", [False, True])
def test_unsafe_selected_layout_cannot_be_styled(
    monkeypatch, generation, request_data, case, ai
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")
    candidate = generation.candidates[0]
    if case == "outside":
        candidate.design.furniture[0].x_m = -1.0
    elif case == "no_door":
        candidate.design.room.doors = []
    elif case == "score":
        candidate.score.total -= 1.0
    elif case == "report":
        candidate.validation.config.walking_clearance_m = 0.7
    elif case == "rotation":
        candidate.design.furniture[0].rotation_deg = 90
    else:
        candidate.design.furniture[0].name = "Changed furniture identity"
    before = generation.model_dump_json()
    callback = Mock()
    result = style_selected_layout(
        request_data,
        generation,
        0,
        use_ai_stylist=ai,
        allow_live_stylist=True,
        interior_stylist=callback,
    )
    assert (
        result.status == "rejected" and result.approved_design is result.styling is None
    )
    assert result.selected_candidate_index is None and result.ai_styling.source is None
    assert result.generation.model_dump_json() == before == generation.model_dump_json()
    callback.assert_not_called()


@pytest.mark.parametrize("index", [-1, 2, 100])
def test_missing_selection_never_defaults_to_layout_a(generation, request_data, index):
    result = style_selected_layout(request_data, generation, index)
    assert result.status == "rejected" and result.selected_candidate_index is None
    assert result.approved_design is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("index", True),
        ("index", "1"),
        ("use_ai_stylist", 1),
        ("allow_live_stylist", "true"),
    ],
)
def test_selected_entry_preserves_strict_option_types(
    generation, request_data, field, value
):
    with pytest.raises(ValueError):
        style_selected_layout(
            request_data,
            generation,
            value if field == "index" else 0,
            **({field: value} if field != "index" else {}),
        )


def test_missing_original_specification_is_a_typed_failure(generation):
    result = style_selected_layout(DesignRequest(), generation, 0)
    assert result.status == "failed" and result.error.code == "missing_specification"


@pytest.mark.parametrize(
    "status,code",
    [
        ("error", "timeout"),
        ("unavailable", "connection"),
        ("unavailable", "rate_limit"),
    ],
)
def test_provider_failure_ui_shows_only_sanitized_explicit_fallback(
    app, monkeypatch, status, code
):
    source = generate(app)
    view = enable_ai(app, monkeypatch)
    response = InteriorStylistResult(
        status=status,
        message="secret-token /private/path",
        error=InteriorStylistError(code=code, message="secret-token /private/path"),
    )
    app.styler.side_effect = lambda *args, **kwargs: style_selected_layout(
        *args, **kwargs, interior_stylist=Mock(return_value=response)
    )
    request_ai(view)
    assert any(
        "Deterministic fixture fallback" in element.value for element in view.warning
    )
    assert not any("AI stylist —" in element.value for element in view.success)
    result = view.session_state[ui.RESULT_KEY][1]
    assert (
        result.ai_styling.result.error.code == code
        and result.ai_styling.result.plan is None
    )
    assert (
        "secret-token" not in result.model_dump_json()
        and "/private/path" not in result.model_dump_json()
    )
    for group in (view.markdown, view.caption, view.error, view.warning):
        assert all(
            "secret-token" not in element.value and "/private/path" not in element.value
            for element in group
        )
    assert view.session_state[layouts.RESULT_KEY] is source
    assert not view.checkbox(key=ui.CONSENT_KEY).value


def test_missing_api_configuration_uses_adapter_preflight_and_fixture(app, monkeypatch):
    generate(app)
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")
    app.view.checkbox(key=ui.ENABLE_KEY).check().run()
    request_ai(app.view)
    result = app.view.session_state[ui.RESULT_KEY][1]
    assert result.ai_styling.reason == "authentication"
    assert (
        result.ai_styling.source == "deterministic_fixture"
        and result.ai_styling.result.plan is None
    )


@pytest.mark.parametrize("field", ["theme", "preferences", "mode"])
def test_input_changes_clear_old_result_and_fresh_consent(app, monkeypatch, field):
    generate(app)
    view = enable_ai(app, monkeypatch)
    request_ai(view)
    view.checkbox(key=ui.CONSENT_KEY).check().run()
    if field == "theme":
        view.selectbox(key=ui.THEME_KEY).select("modern").run()
    elif field == "preferences":
        view.text_area(key=ui.PREFERENCE_KEY).input(
            "Different appearance request."
        ).run()
    else:
        view.checkbox(key=ui.ENABLE_KEY).uncheck().run()
    assert not view.exception and ui.RESULT_KEY not in view.session_state
    if field != "mode":
        assert not view.checkbox(key=ui.CONSENT_KEY).value
    app.styler.assert_called_once()


def test_failed_generation_keeps_prior_styling_and_selection(app, monkeypatch):
    source = generate(app)
    app.view.radio(key=layouts.SELECTION_KEY).set_value("Layout B").run()
    app.view.button(key="show_fixture_styling").click().run()
    prior = app.view.session_state[ui.RESULT_KEY]
    monkeypatch.setattr(
        layouts,
        "_generate",
        Mock(side_effect=RuntimeError("Existing generation failure")),
    )
    app.view.button(key="generate_layouts").click().run()
    assert not app.view.exception
    assert app.view.session_state[layouts.RESULT_KEY] is source
    assert app.view.session_state[layouts.SELECTION_KEY] == "Layout B"
    assert app.view.session_state[ui.RESULT_KEY] == prior
    app.styler.assert_called_once()


def test_ordinary_reruns_switches_and_inputs_do_not_validate_or_call_models(
    app, monkeypatch
):
    generate(app)
    view = enable_ai(app, monkeypatch)
    request_ai(view)
    validator = Mock(side_effect=AssertionError("No validation on view changes"))
    monkeypatch.setattr(nodes, "validate_accessibility", validator)
    monkeypatch.setattr(layouts, "validate_accessibility", validator)
    monkeypatch.setattr(
        "archimind.workflow.interior_styling.validate_accessibility", validator
    )
    view.run()
    view.radio(key=layouts.SELECTION_KEY).set_value("Layout B").run()
    view.text_area(key=ui.PREFERENCE_KEY).input("A changed preference.").run()
    assert not view.exception and ui.RESULT_KEY not in view.session_state
    assert not view.checkbox(key=ui.CONSENT_KEY).value
    validator.assert_not_called()
    app.styler.assert_called_once()
    app.generator.assert_called_once()


def test_duplicate_or_inflight_requests_cannot_reuse_consumed_authorization(
    app, monkeypatch
):
    generate(app)
    view = enable_ai(app, monkeypatch)
    request_ai(view)
    assert view.button(key="request_ai_styling").disabled
    view.run()
    app.styler.assert_called_once()
    view.session_state[ui.INFLIGHT_KEY] = True
    view.checkbox(key=ui.CONSENT_KEY).check().run()
    assert view.button(key="request_ai_styling").disabled
    view.run()
    app.styler.assert_called_once()
    view.session_state[ui.INFLIGHT_KEY] = False
    request_ai(view)
    assert app.styler.call_count == 2 and not view.checkbox(key=ui.CONSENT_KEY).value


@pytest.mark.parametrize("case", ["consent", "mode", "flag", "inflight"])
def test_submit_callback_enforces_server_gates_before_queueing(monkeypatch, case):
    monkeypatch.setenv(
        "ARCHIMIND_ENABLE_OPENAI_STYLIST", "1" if case != "flag" else "0"
    )
    state = {
        ui.ENABLE_KEY: case != "mode",
        ui.CONSENT_KEY: case != "consent",
        ui.INFLIGHT_KEY: case == "inflight",
    }
    monkeypatch.setattr(ui.st, "session_state", state)
    ui._queue("context", True)
    assert ui.PENDING_KEY not in state


def test_unsafe_ui_selection_gets_no_approved_style(app):
    source = generate(app)
    source.candidates[0].design.furniture[0].x_m = -1.0
    app.view.run()
    app.view.button(key="show_fixture_styling").click().run()
    assert not app.view.exception
    result = app.view.session_state[ui.RESULT_KEY][1]
    assert result.status == "rejected" and result.approved_design is None
    assert any(
        "Styling was not approved" in element.value for element in app.view.error
    )
    assert app.view.session_state[layouts.RESULT_KEY] is source
    assert app.view.session_state[layouts.SELECTION_KEY] == "Layout A"


def test_catalog_controls_and_separate_sessions_have_no_shared_results(app):
    generate(app)
    app.view.checkbox(key=ui.ENABLE_KEY).check().run()
    assert app.view.selectbox(key=ui.THEME_KEY).options == [
        theme.label for theme in THEMES.values()
    ]
    app.view.button(key="show_fixture_styling").click().run()
    second = AppTest.from_file(str(APP), default_timeout=30).run()
    second.button(key="generate_layouts").click().run()
    assert ui.RESULT_KEY not in second.session_state
    assert not second.checkbox(key=ui.ENABLE_KEY).value
    assert ui.RESULT_KEY in app.view.session_state


def test_no_other_ai_agent_is_enabled_by_selected_styling(
    monkeypatch, generation, request_data
):
    for role in ("REQUIREMENTS", "LAYOUT", "CRITIC"):
        monkeypatch.setenv(f"ARCHIMIND_ENABLE_OPENAI_{role}", "1")
    result = style_selected_layout(request_data, generation, 1)
    assert result.status == "succeeded" and result.interpretation is None
    assert (
        not result.layout_recommendation.requested
        and not result.spatial_critique.requested
    )


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


@pytest.mark.parametrize("index", [0, 1])
def test_mock_ai_display_preserves_source_and_consumes_consent(app, monkeypatch, index):
    source = generate(app)
    label = f"Layout {'AB'[index]}"
    if index:
        app.view.radio(key=layouts.SELECTION_KEY).set_value(label).run()
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
    assert view.session_state[layouts.SELECTION_KEY] == label
    finishes = next(
        element.value
        for element in view.dataframe
        if "Furniture ID" in element.value.columns
    )
    assert set(finishes["Furniture ID"]) == {
        item.id for item in source.candidates[index].design.furniture
    }
    call = app.styler.call_args
    assert call.args[0].soft_preferences == ["Muted sage accents."]
    assert call.kwargs == {"use_ai_stylist": True, "allow_live_stylist": True}
    view.run()
    app.styler.assert_called_once()
    app.generator.assert_called_once()


@pytest.mark.parametrize("outcome", ["malformed", "clarification", "exception"])
def test_rejected_or_incomplete_ai_output_never_looks_like_ai_success(
    app, monkeypatch, outcome
):
    generate(app)
    view = enable_ai(app, monkeypatch)

    def callback(request, **kwargs):
        if outcome == "exception":
            raise RuntimeError("secret-token /private/path")
        result = offline_interior_stylist(request, **kwargs)
        if outcome == "malformed":
            result.proposal.furniture_finishes[0].furniture_id = "unknown-object"
            return result
        proposal = result.proposal.model_copy(
            update={
                "decision": "request_clarification",
                "theme_id": None,
                "palette_id": None,
                "wall_material_id": None,
                "floor_material_id": None,
                "furniture_finishes": [],
                "accent_ids": [],
                "rationale_code": "clarification_needed",
                "preference_assessments": [
                    {"preference_index": 0, "judgment": "unverified"}
                ],
                "conflict_codes": ["missing_style_details"],
            }
        )
        return interpret_style_proposal(
            result.context, proposal, mode="offline_fixture"
        )

    app.styler.side_effect = lambda *args, **kwargs: style_selected_layout(
        *args, **kwargs, interior_stylist=callback
    )
    request_ai(view)
    result = view.session_state[ui.RESULT_KEY][1]
    assert (
        result.ai_styling.status
        == {
            "malformed": "rejected",
            "clarification": "needs_clarification",
            "exception": "error",
        }[outcome]
    )
    assert result.ai_styling.result.plan is None and result.styling is not None
    assert any(
        "Deterministic fixture fallback" in element.value for element in view.warning
    )
    assert not any("AI stylist —" in element.value for element in view.success)
    assert "secret-token" not in result.model_dump_json()


def test_missing_or_unverified_session_selection_clears_prior_style(app):
    source = generate(app)
    app.view.button(key="show_fixture_styling").click().run()
    source.candidates[0].validation.status = "unverified"
    app.view.run()
    assert ui.RESULT_KEY not in app.view.session_state
    assert not app.view.exception


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
