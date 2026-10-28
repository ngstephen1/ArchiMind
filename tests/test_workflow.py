"""Offline tests using the real LangGraph, generator and Shapely APIs."""

import json
import os
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.examples import create_sample_bedroom
from archimind.geometry import (
    AccessibilityConfig,
    generate_layout_candidates,
    validate_accessibility,
)
from archimind.workflow import (
    CandidateReview,
    DesignRequest,
    StylingPreferences,
    WorkflowState,
    nodes,
    run_workflow,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Workflow tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    yield
    assert not attempts, "A network call was attempted, even if its error was caught"


@pytest.fixture
def request_data():
    return DesignRequest(specification=create_sample_bedroom())


def test_complete_workflow_uses_four_roles_and_real_approved_geometry(request_data):
    result = run_workflow(request_data)
    assert result.status == "succeeded" and result.stage == "complete"
    assert result.error is None and result.iteration_count == 1
    assert [item.node for item in result.trace] == [
        "requirements_interpreter",
        "layout_designer",
        "spatial_critic",
        "interior_stylist",
    ]
    assert [item.decision for item in result.trace] == [
        "accepted",
        "generated",
        "approved",
        "styled",
    ]
    assert result.selected_candidate_index == 0
    assert len(result.generation.candidates) == len(result.reviews) == 2
    assert all(review.accepted for review in result.reviews)
    assert result.approved_design == result.generation.candidates[0].design
    assert (
        validate_accessibility(result.approved_design, area_tolerance_m2=0.0)
        == result.reviews[0].report
    )
    assert result.styling.source == "deterministic_fixture"


def test_generator_and_validator_handoffs_are_explicit_and_bounded(
    monkeypatch, request_data
):
    generator = Mock(wraps=generate_layout_candidates)
    validator = Mock(wraps=validate_accessibility)
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    monkeypatch.setattr(nodes, "validate_accessibility", validator)
    result = run_workflow(request_data)
    generator.assert_called_once_with(
        request_data.specification.room,
        request_data.specification.furniture,
        seed=42,
        max_candidates=2,
        max_attempts=500,
        config=request_data.accessibility,
    )
    assert validator.call_count == 2
    for call, candidate in zip(
        validator.call_args_list, result.generation.candidates, strict=True
    ):
        assert call.args == (candidate.design,)
        assert call.kwargs == {
            "config": request_data.accessibility,
            "area_tolerance_m2": 0.0,
        }
        assert call.args[0] is not candidate.design


def test_prose_without_structured_requirements_terminates_before_generation(
    monkeypatch,
):
    generator = Mock()
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    result = run_workflow(DesignRequest(original_request="Make a cozy bedroom"))
    assert result.status == "failed" and result.error.code == "missing_specification"
    assert result.request.original_request == "Make a cozy bedroom"
    assert len(result.trace) == 1 and result.iteration_count == 0
    assert result.approved_design is result.styling is None
    generator.assert_not_called()


@pytest.mark.parametrize(
    "case,expected",
    [
        ("rotation", "unsupported"),
        ("no_door", "unsupported"),
        ("oversize", "infeasible"),
        ("budget", "exhausted"),
    ],
)
def test_unsupported_infeasible_and_exhausted_requests_terminate(
    case, expected, request_data
):
    if case == "rotation":
        request_data.specification.furniture[0].rotation_deg = 90
    elif case == "no_door":
        request_data.specification.room.doors = []
    elif case == "oversize":
        request_data.specification.furniture[0].width_m = 10.0
    else:
        request_data.max_attempts = 0
    result = run_workflow(request_data)
    assert result.status == expected and len(result.trace) == 2
    assert result.iteration_count == 1
    assert result.approved_design is result.styling is None
    assert result.reviews == []
    assert result.generation.attempts_used <= request_data.max_attempts
    assert result.error.node == "layout_designer"


def test_critic_rejects_forged_passing_report_for_invalid_geometry(
    monkeypatch, request_data
):
    forged = generate_layout_candidates(
        request_data.specification.room, request_data.specification.furniture
    )
    for candidate in forged.candidates:
        candidate.design.furniture[0].x_m = -1.0
    # Canonical models permit this data; claimed passing reports alone cannot approve it.
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: forged
    )
    result = run_workflow(request_data)
    assert result.status == "rejected" and len(result.trace) == 3
    assert result.error.code == "no_approved_candidates"
    assert all(
        not review.accepted and review.report.status == "failed"
        for review in result.reviews
    )
    assert result.approved_design is result.styling is None


@pytest.mark.parametrize(
    "function,node_name,length",
    [
        ("generate_layout_candidates", "layout_designer", 2),
        ("validate_accessibility", "spatial_critic", 3),
    ],
)
def test_backend_errors_are_traced_sanitized_and_not_retried(
    monkeypatch, request_data, function, node_name, length
):
    backend = Mock(side_effect=RuntimeError("secret-token /private/path"))
    monkeypatch.setattr(nodes, function, backend)
    result = run_workflow(request_data)
    assert result.status == "failed" and result.error.code == "node_error"
    assert result.error.node == node_name and len(result.trace) == length
    backend.assert_called_once()
    assert result.approved_design is result.styling is None
    assert "secret-token" not in result.model_dump_json()
    assert "/private/path" not in result.model_dump_json()


def test_fixed_seed_is_deterministic_and_input_is_not_mutated(request_data):
    original = request_data.model_dump_json()
    first = run_workflow(request_data)
    second = run_workflow(request_data)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert request_data.model_dump_json() == original
    assert first.request == request_data and first.request is not request_data
    assert first.design == request_data.specification
    assert first.design is not request_data.specification


def test_state_json_roundtrip_retains_canonical_types_and_information(request_data):
    result = run_workflow(request_data)
    payload = result.model_dump_json(indent=2)
    assert json.loads(payload)["approved_design"]["room"]["width_m"] == 5.0
    assert WorkflowState.model_validate_json(payload) == result


@pytest.mark.parametrize(
    "changes", [{"seed": True}, {"max_candidates": 3}, {"max_attempts": 10001}]
)
def test_strict_options_rejected_before_execution(changes):
    with pytest.raises(ValidationError):
        DesignRequest(**changes)


def test_mutated_invalid_design_is_revalidated_before_execution(request_data):
    request_data.specification.room.width_m = float("inf")
    with pytest.raises(ValidationError):
        run_workflow(request_data)


def test_unverified_required_check_can_never_be_approved(monkeypatch, request_data):
    unevaluated = create_sample_bedroom()
    unevaluated.room.doors = []
    report = validate_accessibility(unevaluated, area_tolerance_m2=0.0)
    assert report.status == "unverified"
    assert report.checks["circulation"].status == "not_evaluated"
    monkeypatch.setattr(nodes, "validate_accessibility", lambda *args, **kwargs: report)
    result = run_workflow(request_data)
    assert result.status == "rejected" and result.approved_design is None
    assert all(
        review.reason == "spatial_checks_unverified" and not review.accepted
        for review in result.reviews
    )
    with pytest.raises(ValidationError, match="fully passing"):
        CandidateReview(
            candidate_index=0, report=report, accepted=True, reason="approved"
        )


def test_rejected_first_candidate_does_not_hide_valid_second_candidate(
    monkeypatch, request_data
):
    generated = generate_layout_candidates(
        request_data.specification.room, request_data.specification.furniture
    )
    generated.candidates[0].design.furniture[0].x_m = -1.0
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
    )
    result = run_workflow(request_data)
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert [review.accepted for review in result.reviews] == [False, True]
    assert result.approved_design == generated.candidates[1].design


@pytest.mark.parametrize("change", ["room", "dimensions", "identity"])
def test_geometrically_valid_but_changed_specification_is_rejected(
    monkeypatch, request_data, change
):
    generated = generate_layout_candidates(
        request_data.specification.room, request_data.specification.furniture
    )
    for candidate in generated.candidates:
        if change == "room":
            candidate.design.room.name = "Changed room"
        elif change == "dimensions":
            candidate.design.furniture[0].height_m += 0.1
        else:
            candidate.design.furniture[0].id = "replacement-furniture"
        candidate.validation = validate_accessibility(
            candidate.design, area_tolerance_m2=0.0
        )
        assert candidate.validation.status == "passed"
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
    )
    result = run_workflow(request_data)
    assert result.status == "rejected"
    assert all(review.reason == "specification_mismatch" for review in result.reviews)


def test_report_mismatch_rejected_even_with_valid_geometry(monkeypatch, request_data):
    generated = generate_layout_candidates(
        request_data.specification.room, request_data.specification.furniture
    )
    for candidate in generated.candidates:
        candidate.validation.checks["containment"].message = "Untrusted assertion"
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
    )
    result = run_workflow(request_data)
    assert result.status == "rejected"
    assert all(review.reason == "report_mismatch" for review in result.reviews)


def test_partial_search_result_can_supply_one_independently_approved_layout(
    request_data,
):
    request_data.specification.furniture = []
    result = run_workflow(request_data)
    assert result.status == "succeeded"
    assert result.generation.status == "search_exhausted"
    assert len(result.generation.candidates) == 1
    assert result.approved_design.furniture == [] and result.reviews[0].accepted
    assert "search_exhausted" in result.trace[1].message


def test_one_candidate_and_nondefault_clearance_reuse_existing_apis(request_data):
    request_data.max_candidates = 1
    request_data.seed = 7
    request_data.accessibility = AccessibilityConfig(walking_clearance_m=0.5)
    direct = generate_layout_candidates(
        request_data.specification.room,
        request_data.specification.furniture,
        seed=7,
        max_candidates=1,
        max_attempts=500,
        config=request_data.accessibility,
    )
    result = run_workflow(request_data)
    assert result.status == "succeeded" and result.generation == direct
    assert len(result.reviews) == 1
    assert result.reviews[0].report.config == request_data.accessibility


@pytest.mark.parametrize("theme", ["neutral", "warm", "cool"])
def test_styling_does_not_change_approved_design_or_reports(theme, request_data):
    request_data.styling_preferences = StylingPreferences(theme=theme)
    state = WorkflowState(request=request_data)
    for operation in [
        nodes.requirements_interpreter,
        nodes.layout_designer,
        nodes.spatial_critic,
    ]:
        state = WorkflowState.model_validate({**dict(state), **operation(state)})
    before = state.model_dump_json()
    styled = WorkflowState.model_validate(
        {**dict(state), **nodes.interior_stylist(state)}
    )
    assert state.model_dump_json() == before
    assert styled.approved_design == state.approved_design
    assert styled.generation == state.generation and styled.reviews == state.reviews
    assert (
        styled.styling.theme == theme
        and styled.styling.source == "deterministic_fixture"
    )


def test_iteration_limit_prevents_second_generation(monkeypatch, request_data):
    generator = Mock()
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    state = WorkflowState(
        request=request_data, design=request_data.specification, iteration_count=1
    )
    result = WorkflowState.model_validate(
        {**dict(state), **nodes.layout_designer(state)}
    )
    assert result.status == "failed" and result.error.code == "iteration_limit"
    assert result.iteration_count == 1
    generator.assert_not_called()


def test_stylist_exception_terminates_and_clears_selection(monkeypatch, request_data):
    stylist = Mock(side_effect=RuntimeError("private material configuration"))
    monkeypatch.setattr(nodes, "interior_stylist", stylist)
    result = run_workflow(request_data)
    assert result.status == "failed" and result.error.node == "interior_stylist"
    assert len(result.trace) == 4 and result.reviews[0].accepted
    assert (
        result.selected_candidate_index
        is result.approved_design
        is result.styling
        is None
    )
    assert "private material" not in result.model_dump_json()
    stylist.assert_called_once()


@pytest.mark.parametrize(
    "wrong_options",
    [{"seed": 99}, {"config": AccessibilityConfig(walking_clearance_m=0.5)}],
)
def test_generator_cannot_silently_change_request_options(
    monkeypatch, request_data, wrong_options
):
    generated = generate_layout_candidates(
        request_data.specification.room,
        request_data.specification.furniture,
        **wrong_options,
    )
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
    )
    result = run_workflow(request_data)
    assert result.status == "failed" and result.error.node == "layout_designer"
    assert result.generation is None and result.approved_design is None


def test_state_cannot_claim_success_without_verified_selection(request_data):
    with pytest.raises(ValidationError):
        WorkflowState(request=request_data, status="succeeded", stage="complete")
    with pytest.raises(ValidationError):
        WorkflowState(
            request=request_data,
            approved_design=request_data.specification,
            selected_candidate_index=0,
        )


def test_independent_runs_do_not_share_mutable_state(request_data):
    first = run_workflow(request_data)
    first.styling.palette.append("Changed after return")
    first.approved_design.furniture[0].x_m = -20.0
    first.trace.clear()
    second = run_workflow(request_data)
    assert (
        len(second.trace) == 4 and "Changed after return" not in second.styling.palette
    )
    assert (
        validate_accessibility(second.approved_design, area_tolerance_m2=0.0).status
        == "passed"
    )


def test_concurrent_invocations_have_isolated_requests(request_data):
    other = request_data.model_copy(update={"seed": 7}, deep=True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(run_workflow, [request_data, other]))
    assert first.status == second.status == "succeeded"
    assert first.request.seed == first.generation.seed == 42
    assert second.request.seed == second.generation.seed == 7
    assert first == run_workflow(request_data) and second == run_workflow(other)


def test_remote_tracing_is_disabled_without_changing_callers_context(
    monkeypatch, request_data
):
    from langchain_core.tracers import langchain as tracing
    from langsmith import get_tracing_context, tracing_context

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    tracer = Mock(side_effect=AssertionError("Remote tracing must not be created"))
    monkeypatch.setattr(tracing, "LangChainTracer", tracer)
    with tracing_context(enabled=True):
        result = run_workflow(request_data)
        assert get_tracing_context()["enabled"] is True
    assert result.status == "succeeded"
    tracer.assert_not_called()


def test_workflow_does_not_invoke_optional_codex_or_subprocess(
    monkeypatch, request_data
):
    from archimind.integrations import codex_advisor

    codex = Mock(side_effect=AssertionError("C01 must remain separate"))
    process = Mock(side_effect=AssertionError("No subprocess capability in workflow"))
    monkeypatch.setattr(codex_advisor, "request_codex_advice", codex)
    monkeypatch.setattr(subprocess, "run", process)
    assert run_workflow(request_data).status == "succeeded"
    codex.assert_not_called()
    process.assert_not_called()


@pytest.mark.parametrize(
    "options,code,status",
    [([], 0, "succeeded"), (["--max-attempts", "0"], 1, "exhausted")],
)
def test_actual_cli_outputs_typed_json_and_meaningful_exit_code(options, code, status):
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "archimind.examples.workflow_bedroom",
            "--json",
            *options,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "PATH": os.defpath,
            "PYTHONNOUSERSITE": "1",
            "LANGSMITH_TRACING": "false",
            "LANGCHAIN_TRACING_V2": "false",
        },
    )
    assert process.returncode == code, process.stderr
    result = WorkflowState.model_validate_json(process.stdout)
    assert result.status == status and process.stderr == ""
