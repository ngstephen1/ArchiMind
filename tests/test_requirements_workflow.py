"""07B integration: live-capable path mocked, existing path unchanged, no network."""

import json
import os
import socket
import subprocess
import sys
from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from archimind.agents import interpret_requirements, prepare_requirements
from archimind.agents.requirements_schemas import Preference
from archimind.examples import create_sample_bedroom
from archimind.examples.interpret_bedroom import offline_interpreter
from archimind.examples.requirements_fixture import SAMPLE_REQUEST, sample_extraction
from archimind.geometry import validate_accessibility
from archimind.workflow import DesignRequest, WorkflowState, nodes, run_workflow


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("No integration-test networking")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.delenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ARCHIMIND_OPENAI_MODEL", raising=False)
    yield
    assert not attempts


def test_offline_mock_interpretation_completes_actual_langgraph_and_spatial_checks():
    original = DesignRequest(original_request=SAMPLE_REQUEST)
    before = original.model_dump_json()
    interpreter = Mock(wraps=offline_interpreter)
    result = run_workflow(original, interpret_free_text=True, interpreter=interpreter)
    assert result.status == "succeeded" and result.iteration_count == 1
    assert (
        result.interpretation.status == "ready"
        and result.interpretation.mode == "offline_fixture"
    )
    assert result.interpretation.model is None
    assert result.design == result.interpretation.specification
    assert result.request == original and original.model_dump_json() == before
    interpreter.assert_called_once_with(SAMPLE_REQUEST, allow_live=False)
    assert len(result.trace) == 4 and len(result.generation.candidates) == 2
    assert "offline_fixture" in result.trace[0].message
    assert "catalog defaults" in result.trace[0].message
    for review, candidate in zip(
        result.reviews, result.generation.candidates, strict=True
    ):
        assert review.accepted and review.report == validate_accessibility(
            candidate.design, area_tolerance_m2=0.0
        )
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result


def test_structured_inputs_always_bypass_interpreter_even_if_enabled(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    interpreter = Mock(side_effect=AssertionError("Structured input must bypass API"))
    request = DesignRequest(
        specification=create_sample_bedroom(), original_request="metadata"
    )
    baseline = run_workflow(request)
    result = run_workflow(
        request,
        interpret_free_text=True,
        allow_live_requirements=True,
        interpreter=interpreter,
    )
    assert result == baseline and result.interpretation is None
    interpreter.assert_not_called()


def test_legacy_prose_metadata_path_remains_unchanged():
    result = run_workflow(DesignRequest(original_request=SAMPLE_REQUEST))
    assert result.status == "failed" and result.error.code == "missing_specification"
    assert result.interpretation is None


def test_enabled_free_text_mode_reports_unavailable_when_feature_disabled(monkeypatch):
    generator = Mock()
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    result = run_workflow(
        DesignRequest(original_request=SAMPLE_REQUEST),
        interpret_free_text=True,
        allow_live_requirements=True,
    )
    assert (
        result.status == "unavailable"
        and result.error.code == "requirements_unavailable"
    )
    assert result.interpretation.error.code == "disabled"
    assert len(result.trace) == 1 and result.iteration_count == 0
    generator.assert_not_called()


def test_feature_flag_does_not_supply_per_call_authorization(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    factory = Mock(side_effect=AssertionError("No unauthorized client"))
    interpreter = partial(interpret_requirements, client_factory=factory)
    result = run_workflow(
        DesignRequest(original_request=SAMPLE_REQUEST),
        interpret_free_text=True,
        interpreter=interpreter,
    )
    assert (
        result.status == "unavailable"
        and result.interpretation.error.code == "authorization_required"
    )
    factory.assert_not_called()


@pytest.mark.parametrize(
    "case,expected",
    [("missing", "needs_clarification"), ("unsupported", "unsupported")],
)
def test_clarification_and_unsupported_requirements_terminate_before_generation(
    monkeypatch, case, expected
):
    data = sample_extraction()
    if case == "missing":
        data.ceiling_height = None
    else:
        data.furniture[0].catalog_key = "unsupported"

    def interpreter(text, **kwargs):
        return prepare_requirements(data, text)

    generator = Mock()
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    result = run_workflow(
        DesignRequest(original_request=SAMPLE_REQUEST),
        interpret_free_text=True,
        interpreter=interpreter,
    )
    assert result.status == expected and result.design is result.approved_design is None
    assert len(result.trace) == 1 and result.interpretation.status == expected
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    generator.assert_not_called()


def test_style_preferences_and_assumptions_are_retained_without_changing_other_nodes():
    data = sample_extraction()
    text = SAMPLE_REQUEST + " Use Scandinavian style and keep the desk near the window."
    data.style = Preference(text="Scandinavian", source_text="Scandinavian style")
    data.soft_preferences = [
        Preference(text="desk near window", source_text="desk near the window")
    ]
    prepared = prepare_requirements(data, text)
    result = run_workflow(
        DesignRequest(original_request=text),
        interpret_free_text=True,
        interpreter=lambda *args, **kwargs: prepared,
    )
    assert result.status == "succeeded"
    assert "Scandinavian" in result.trace[0].message
    assert "not enforced" in result.trace[0].message
    assert (
        result.interpretation.extraction.soft_preferences[0].text == "desk near window"
    )
    assert result.styling.source == "deterministic_fixture"
    direct = run_workflow(DesignRequest(specification=prepared.specification))
    assert result.generation == direct.generation and result.reviews == direct.reviews
    assert (
        result.styling == direct.styling
        and result.approved_design == direct.approved_design
    )


def test_inconsistent_injected_canonical_result_cannot_be_accepted():
    prepared = prepare_requirements(sample_extraction(), SAMPLE_REQUEST)
    prepared.specification.room.width_m = 6.0
    result = run_workflow(
        DesignRequest(original_request=SAMPLE_REQUEST),
        interpret_free_text=True,
        interpreter=lambda *args, **kwargs: prepared,
    )
    assert result.status == "failed" and result.error.code == "node_error"
    assert result.approved_design is None and len(result.trace) == 1


def test_mocked_api_is_called_once_and_only_by_requirements_node(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    data = sample_extraction()
    response = SimpleNamespace(
        status="completed",
        output=[],
        output_parsed=data,
        model_dump_json=lambda: data.model_dump_json(),
    )
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.return_value = response
    result = run_workflow(
        DesignRequest(original_request=SAMPLE_REQUEST),
        interpret_free_text=True,
        allow_live_requirements=True,
        interpreter=partial(
            interpret_requirements, client_factory=Mock(return_value=client)
        ),
    )
    assert result.status == "succeeded" and result.interpretation.mode == "api_response"
    client.responses.parse.assert_called_once()
    assert result.styling.source == "deterministic_fixture"


@pytest.mark.parametrize(
    "options", [{"interpret_free_text": "true"}, {"allow_live_requirements": 1}]
)
def test_truthy_non_boolean_workflow_flags_cannot_authorize_api_calls(options):
    with pytest.raises(ValueError, match="boolean"):
        run_workflow(DesignRequest(original_request=SAMPLE_REQUEST), **options)


def test_offline_demo_restores_environment_and_is_reproducible(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-use-fixture")
    tracked = (
        "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS",
        "OPENAI_API_KEY",
        "ARCHIMIND_OPENAI_MODEL",
    )
    before = {key: os.environ.get(key) for key in tracked}
    first = offline_interpreter(SAMPLE_REQUEST)
    second = offline_interpreter(SAMPLE_REQUEST)
    assert first == second and {key: os.environ.get(key) for key in tracked} == before
    assert "do-not-use-fixture" not in first.model_dump_json()


def test_actual_offline_cli_produces_typed_json_without_credentials():
    process = subprocess.run(
        [sys.executable, "-m", "archimind.examples.interpret_bedroom", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": os.defpath, "PYTHONNOUSERSITE": "1", "LANGSMITH_TRACING": "false"},
    )
    assert process.returncode == 0 and process.stderr == ""
    result = WorkflowState.model_validate_json(process.stdout)
    assert (
        result.status == "succeeded" and result.interpretation.mode == "offline_fixture"
    )
    assert json.loads(process.stdout)["interpretation"]["model"] is None
