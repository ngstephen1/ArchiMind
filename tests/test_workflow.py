"""Offline tests using the real LangGraph, generator and Shapely APIs."""

import json
import socket
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates, validate_accessibility
from archimind.workflow import DesignRequest, WorkflowState, nodes, run_workflow


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
