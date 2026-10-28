"""C2 uses real orchestration/geometry, mocked advice, and no network access."""

import json
import os
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APITimeoutError
from pydantic import ValidationError

from archimind.agents import layout_agent, requirements_agent
from archimind.agents.layout_grounding import (
    interpret_layout_proposal,
    prepare_layout_context,
)
from archimind.agents.layout_schemas import (
    LayoutAdviceError,
    LayoutAdviceResult,
    LayoutProposal,
)
from archimind.agents.requirements_schemas import Preference
from archimind.examples import create_sample_bedroom
from archimind.examples.advised_workflow import offline_workflow_comparison
from archimind.examples.interpret_bedroom import offline_interpreter
from archimind.examples.requirements_fixture import SAMPLE_REQUEST, sample_extraction
from archimind.geometry import generate_layout_candidates, validate_accessibility
from archimind.workflow import DesignRequest, WorkflowState, nodes, run_workflow
from archimind.workflow.layout_recommendation import layout_recommendation
from archimind.workflow.state import MAX_NODE_EXECUTIONS

PREFERENCE = "Place the desk closer to the north-facing window."
DEFAULT_NODES = [
    "requirements_interpreter",
    "layout_designer",
    "spatial_critic",
    "interior_stylist",
]
ADVISED_NODES = [*DEFAULT_NODES[:3], "layout_advisor", DEFAULT_NODES[3]]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("C2 tests must never attempt network access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    for name in (
        "ARCHIMIND_ENABLE_OPENAI_LAYOUT",
        "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS",
        "ARCHIMIND_OPENAI_MODEL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    client = Mock(side_effect=AssertionError("No real OpenAI client may be created"))
    monkeypatch.setattr(requirements_agent, "_client", client)
    yield client
    assert not attempts, "Caught networking failures still count as network attempts"


@pytest.fixture
def request_data():
    return DesignRequest(
        specification=create_sample_bedroom(), soft_preferences=[PREFERENCE]
    )


def mocked_advice(request, *, allow_live=False, index=1, abstain=False):
    context = prepare_layout_context(request)
    proposal = LayoutProposal(
        decision="abstain" if abstain else "recommend",
        candidate_index=None if abstain else index,
        rationale_code="no_clear_preference" if abstain else "preference_balance",
        evidence_refs=[],
        preference_assessments=[
            {"preference_index": i, "judgment": "uncertain" if abstain else "favored"}
            for i in range(len(request.soft_preferences))
        ],
        limitation_codes=["limited_candidate_set", "subjective_preferences"],
    )
    return interpret_layout_proposal(context, proposal, mode="offline_fixture")


def advised(monkeypatch, request_data, advisor=None, **options):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")
    return run_workflow(
        request_data,
        use_ai_layout=True,
        layout_advisor=advisor if advisor is not None else mocked_advice,
        **options,
    )


@pytest.mark.parametrize("flag", ["0", "1"])
def test_default_path_never_invokes_adapter_or_injection(
    monkeypatch, request_data, offline, flag
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", flag)
    adapter = Mock(side_effect=AssertionError("No workflow opt-in"))
    monkeypatch.setattr(layout_agent, "recommend_layout", adapter)
    result = run_workflow(request_data, allow_live_layout=True, layout_advisor=adapter)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.selection_source == "deterministic"
    assert result.layout_recommendation.status == "not_requested"
    assert not result.layout_recommendation.executed
    assert [event.node for event in result.trace] == DEFAULT_NODES
    assert "not requested" in result.trace[2].message
    adapter.assert_not_called()
    offline.assert_not_called()


@pytest.mark.parametrize("flag", [None, "0", "true"])
def test_disabled_feature_skips_optional_node_even_with_opt_in_and_injection(
    monkeypatch, request_data, offline, flag
):
    if flag is not None:
        monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", flag)
    advisor = Mock()
    result = run_workflow(
        request_data, use_ai_layout=True, allow_live_layout=True, layout_advisor=advisor
    )
    metadata = result.layout_recommendation
    assert metadata.requested and metadata.status == "disabled"
    assert metadata.reason == "feature_disabled" and not metadata.executed
    assert metadata.deterministic_candidate_index == 0
    assert result.selection_source == "deterministic"
    assert [event.node for event in result.trace] == DEFAULT_NODES
    advisor.assert_not_called()
    offline.assert_not_called()


def test_recommendation_follows_critic_and_styles_exact_original_candidate(
    monkeypatch, request_data, offline
):
    baseline = run_workflow(request_data)
    before = request_data.model_dump_json()
    critic = Mock(wraps=nodes.spatial_critic)
    stylist = Mock(wraps=nodes.interior_stylist)
    generator = Mock(wraps=generate_layout_candidates)
    monkeypatch.setattr(nodes, "spatial_critic", critic)
    monkeypatch.setattr(nodes, "interior_stylist", stylist)
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)

    def advisor(request, *, allow_live):
        assert critic.call_count == 1 and stylist.call_count == 0
        assert allow_live is False
        assert request.generation == baseline.generation
        assert all(
            validate_accessibility(c.design, area_tolerance_m2=0.0) == review.report
            for c, review in zip(request.generation.candidates, baseline.reviews)
        )
        return mocked_advice(request)

    injected = Mock(side_effect=advisor)
    result = advised(monkeypatch, request_data, injected)
    assert result.status == "succeeded"
    assert result.selected_candidate_index == 1
    assert result.selection_source == "ai_recommendation"
    assert result.approved_design == baseline.generation.candidates[1].design
    assert stylist.call_args.args[0].approved_design == result.approved_design
    assert (
        result.generation == baseline.generation and result.reviews == baseline.reviews
    )
    assert result.generation.candidates[1].score.total == 67.614973
    assert request_data.model_dump_json() == before
    assert [event.node for event in result.trace] == ADVISED_NODES
    assert len(result.trace) == MAX_NODE_EXECUTIONS == 5
    assert result.iteration_count == 1
    assert result.layout_recommendation.candidate_indices == [0, 1]
    assert result.layout_recommendation.deterministic_candidate_index == 0
    assert result.layout_recommendation.proposed_candidate_index == 1
    assert result.layout_recommendation.advice.mode == "offline_fixture"
    assert "offline_fixture" in result.trace[3].message
    assert "recommendation accepted" in result.trace[3].message
    assert result.trace[3].decision == "recommended"
    injected.assert_called_once()
    generator.assert_called_once()
    stylist.assert_called_once()
    offline.assert_not_called()


def test_enabled_workflow_without_live_authorization_falls_back_before_client(
    monkeypatch, request_data, offline
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")
    adapter = Mock(wraps=layout_agent.recommend_layout)
    monkeypatch.setattr(layout_agent, "recommend_layout", adapter)
    result = run_workflow(request_data, use_ai_layout=True)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.selection_source == "deterministic"
    assert result.layout_recommendation.status == "unavailable"
    assert result.layout_recommendation.reason == "authorization_required"
    assert result.layout_recommendation.advice.error.code == "authorization_required"
    assert result.trace[3].decision == "fallback"
    assert [event.node for event in result.trace] == ADVISED_NODES
    adapter.assert_called_once()
    offline.assert_not_called()


def test_abstention_preserves_actual_status_and_original_choice(
    monkeypatch, request_data
):
    result = advised(
        monkeypatch,
        request_data,
        lambda request, **kwargs: mocked_advice(request, abstain=True),
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    metadata = result.layout_recommendation
    assert metadata.status == metadata.advice.status == "abstained"
    assert metadata.executed and metadata.reason == "advisor_abstained"
    assert metadata.proposed_candidate_index is None
    assert result.selection_source == "deterministic"
    assert "retained deterministic candidate 0" in result.trace[3].message


@pytest.mark.parametrize(
    "status,code",
    [("error", "timeout"), ("error", "api_error"), ("unavailable", "rate_limit")],
)
def test_typed_failure_preserves_code_but_sanitizes_untrusted_messages(
    monkeypatch, request_data, status, code
):
    advisor = Mock(
        return_value=LayoutAdviceResult(
            status=status,
            rationale="secret-token /private/provider",
            error=LayoutAdviceError(
                code=code, message="secret-token /private/provider"
            ),
        )
    )
    result = advised(monkeypatch, request_data, advisor)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.selection_source == "deterministic"
    assert result.layout_recommendation.status == status
    assert result.layout_recommendation.reason == code
    assert result.layout_recommendation.advice.error.code == code
    assert "secret-token" not in result.model_dump_json()
    assert "/private/provider" not in result.model_dump_json()
    advisor.assert_called_once()


def test_actual_adapter_timeout_is_mapped_without_retry(monkeypatch, request_data):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.side_effect = APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(requirements_agent, "_client", factory)
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    result = run_workflow(request_data, use_ai_layout=True, allow_live_layout=True)
    assert result.layout_recommendation.reason == "timeout"
    assert result.status == "succeeded" and result.selection_source == "deterministic"
    factory.assert_called_once_with("offline-fixture-only")
    client.responses.parse.assert_called_once()
    assert "offline-fixture-only" not in result.model_dump_json()


def test_successful_actual_adapter_with_mock_client_preserves_api_provenance(
    monkeypatch, request_data
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    proposal = LayoutProposal(
        decision="recommend",
        candidate_index=1,
        rationale_code="preference_balance",
        evidence_refs=[],
        preference_assessments=[{"preference_index": 0, "judgment": "favored"}],
        limitation_codes=["subjective_preferences"],
    )
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.return_value = SimpleNamespace(
        status="completed",
        output=[],
        output_parsed=proposal,
        model_dump_json=lambda: proposal.model_dump_json(),
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(requirements_agent, "_client", factory)
    result = run_workflow(request_data, use_ai_layout=True, allow_live_layout=True)
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert result.layout_recommendation.advice.mode == "api_response"
    assert result.layout_recommendation.advice.model == requirements_agent.DEFAULT_MODEL
    assert result.selection_source == "ai_recommendation"
    factory.assert_called_once_with("offline-fixture-only")
    client.responses.parse.assert_called_once()


def test_unexpected_advisor_exception_falls_back_without_retry(
    monkeypatch, request_data
):
    advisor = Mock(side_effect=RuntimeError("secret-token /private/provider"))
    result = advised(monkeypatch, request_data, advisor)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.layout_recommendation.status == "error"
    assert result.layout_recommendation.reason == "advisor_exception"
    assert "secret-token" not in result.model_dump_json()
    advisor.assert_called_once()


@pytest.mark.parametrize(
    "corruption",
    [
        "index",
        "geometry",
        "score",
        "report",
        "feature",
        "evidence",
        "rationale",
        "tradeoff",
        "status",
        "mode",
        "claimed_api",
        "fixture_model",
        "foreign_ref",
    ],
)
def test_forged_inconsistent_or_unverified_recommendations_are_rejected(
    monkeypatch, request_data, corruption
):
    baseline = run_workflow(request_data)

    def advisor(request, **kwargs):
        result = mocked_advice(request)
        if corruption == "index":
            result.proposal.candidate_index = 7
        elif corruption == "geometry":
            result.context.request.generation.candidates[1].design.furniture[
                0
            ].x_m += 0.1
        elif corruption == "score":
            result.context.request.generation.candidates[1].score.total -= 1.0
        elif corruption == "report":
            result.context.request.generation.candidates[1].validation.checks[
                "containment"
            ].message = "Forged report"
        elif corruption == "feature":
            result.context.features[0].value += 1.0
        elif corruption == "evidence":
            result.evidence = [result.context.features[0]]
        elif corruption == "rationale":
            result.rationale = "Invented numerical evidence"
        elif corruption == "tradeoff":
            result.tradeoffs = ["Invented satisfaction guarantee"]
        elif corruption == "status":
            result.status = "abstained"
        elif corruption == "mode":
            result.mode = "not_evaluated"
        elif corruption == "claimed_api":
            result.mode = "api_response"
            result.model = requirements_agent.DEFAULT_MODEL
        elif corruption == "fixture_model":
            result.model = requirements_agent.DEFAULT_MODEL
        else:
            result.proposal.evidence_refs = ["candidate-0.untrusted"]
        return result

    result = advised(monkeypatch, request_data, advisor)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.selection_source == "deterministic"
    assert result.layout_recommendation.status == "rejected"
    assert result.layout_recommendation.reason == "invalid_recommendation"
    assert result.layout_recommendation.advice is None
    assert (
        result.generation == baseline.generation and result.reviews == baseline.reviews
    )
    assert result.approved_design == baseline.approved_design


def test_only_approved_candidates_reach_advisor_with_explicit_source_mapping(
    monkeypatch, request_data
):
    generated = generate_layout_candidates(
        request_data.specification.room, request_data.specification.furniture
    )
    generated.candidates[0].design.furniture[0].x_m = -1.0
    before = generated.model_dump_json()
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
    )

    def advisor(request, **kwargs):
        assert len(request.generation.candidates) == 1
        assert request.generation.candidates[0] == generated.candidates[1]
        return mocked_advice(request, index=0)

    result = advised(monkeypatch, request_data, advisor)
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert [review.accepted for review in result.reviews] == [False, True]
    assert result.layout_recommendation.deterministic_candidate_index == 1
    assert result.layout_recommendation.candidate_indices == [1]
    assert result.layout_recommendation.proposed_candidate_index == 1
    assert result.layout_recommendation.advice.proposal.candidate_index == 0
    assert len(result.generation.candidates) == 2
    assert result.generation.model_dump_json() == before == generated.model_dump_json()
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "case", ["all_rejected", "no_door", "no_candidates", "missing"]
)
def test_no_safe_candidates_terminate_before_advisor(monkeypatch, request_data, case):
    if case == "all_rejected":
        generated = generate_layout_candidates(
            request_data.specification.room, request_data.specification.furniture
        )
        for candidate in generated.candidates:
            candidate.design.furniture[0].x_m = -1.0
        monkeypatch.setattr(
            nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
        )
    elif case == "no_door":
        request_data.specification.room.doors = []
    elif case == "no_candidates":
        request_data.max_attempts = 0
    else:
        request_data.specification = None
    advisor = Mock()
    result = advised(monkeypatch, request_data, advisor)
    assert result.status != "succeeded" and result.selected_candidate_index is None
    assert result.selection_source is None
    assert result.layout_recommendation.status == "skipped"
    assert not result.layout_recommendation.executed
    assert "layout_advisor" not in [event.node for event in result.trace]
    advisor.assert_not_called()


def test_no_preferences_skips_advisor_and_preserves_four_node_path(
    monkeypatch, request_data
):
    request_data.soft_preferences = []
    advisor = Mock()
    result = advised(monkeypatch, request_data, advisor)
    assert result.layout_recommendation.status == "skipped"
    assert result.layout_recommendation.reason == "no_preferences"
    assert [event.node for event in result.trace] == DEFAULT_NODES
    advisor.assert_not_called()


def test_injected_advisor_cannot_mutate_canonical_workflow_inputs(
    monkeypatch, request_data
):
    baseline = run_workflow(request_data)
    before = request_data.model_dump_json()

    def advisor(request, **kwargs):
        result = mocked_advice(request)
        request.specification.room.name = "Mutated copy"
        request.generation.candidates.clear()
        request.soft_preferences.clear()
        return result

    result = advised(monkeypatch, request_data, advisor)
    assert result.selection_source == "ai_recommendation"
    assert result.generation == baseline.generation
    assert result.reviews == baseline.reviews
    assert request_data.model_dump_json() == before


def test_free_text_interpreter_and_layout_advisor_can_be_combined(monkeypatch):
    data = sample_extraction()
    data.soft_preferences = [Preference(text=PREFERENCE, source_text=PREFERENCE)]
    text = SAMPLE_REQUEST + " " + PREFERENCE
    from archimind.agents import prepare_requirements

    prepared = prepare_requirements(data, text).model_copy(
        update={"mode": "offline_fixture"}
    )
    seen = []

    def advisor(request, **kwargs):
        seen.extend(request.soft_preferences)
        return mocked_advice(request)

    result = advised(
        monkeypatch,
        DesignRequest(original_request=text),
        advisor,
        interpret_free_text=True,
        interpreter=lambda *args, **kwargs: prepared,
    )
    assert (
        result.status == "succeeded" and result.interpretation.mode == "offline_fixture"
    )
    assert result.selection_source == "ai_recommendation" and seen == [PREFERENCE]
    assert [event.node for event in result.trace] == ADVISED_NODES
    # Existing offline Requirements Interpreter also remains a valid injection.
    assert offline_interpreter(SAMPLE_REQUEST).status == "ready"


def test_explicit_preferences_take_precedence_over_interpreted_preferences(monkeypatch):
    observed = []

    def advisor(request, **kwargs):
        observed.extend(request.soft_preferences)
        return mocked_advice(request)

    result = advised(
        monkeypatch,
        DesignRequest(original_request=SAMPLE_REQUEST, soft_preferences=[PREFERENCE]),
        advisor,
        interpret_free_text=True,
        interpreter=offline_interpreter,
    )
    assert result.status == "succeeded" and observed == [PREFERENCE]


@pytest.mark.parametrize(
    "options", [{"use_ai_layout": 1}, {"allow_live_layout": "true"}]
)
def test_truthy_nonboolean_options_cannot_authorize_calls(request_data, options):
    with pytest.raises(ValueError, match="boolean"):
        run_workflow(request_data, **options)


def test_json_and_concurrent_runs_are_reproducible_and_isolated(
    monkeypatch, request_data
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")

    def run(_):
        return run_workflow(
            request_data, use_ai_layout=True, layout_advisor=mocked_advice
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(run, range(2)))
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert WorkflowState.model_validate_json(first.model_dump_json()) == first
    first.layout_recommendation.advice.tradeoffs.append("Changed after return")
    assert "Changed after return" not in second.model_dump_json()


def test_legacy_serialized_state_infers_deterministic_provenance(request_data):
    result = run_workflow(request_data)
    old = json.loads(result.model_dump_json())
    del old["layout_recommendation"]
    del old["selection_source"]
    del old["request"]["soft_preferences"]
    restored = WorkflowState.model_validate_json(json.dumps(old))
    assert restored.selection_source == "deterministic"
    assert restored.layout_recommendation.deterministic_candidate_index == 0
    assert restored.approved_design == result.approved_design


@pytest.mark.parametrize("change", ["source", "mapping", "original", "report"])
def test_serialized_state_rejects_inconsistent_selection_provenance(
    monkeypatch, request_data, change
):
    result = advised(monkeypatch, request_data)
    if change == "source":
        result.selection_source = "deterministic"
    elif change == "mapping":
        result.layout_recommendation.candidate_indices = [1, 0]
    elif change == "original":
        result.layout_recommendation.deterministic_candidate_index = None
    else:
        result.reviews[1].report.checks["containment"].message = "Changed report"
    with pytest.raises(ValidationError):
        WorkflowState.model_validate(result)


def critic_state(request):
    state = WorkflowState(request=request)
    for operation in (
        nodes.requirements_interpreter,
        nodes.layout_designer,
        nodes.spatial_critic,
    ):
        state = WorkflowState.model_validate({**dict(state), **operation(state)})
    # Direct node tests opt in after the critic; the public runner owns this setup.
    state.layout_recommendation.requested = True
    state.layout_recommendation.status = "pending"
    return WorkflowState.model_validate(state)


def test_late_disable_cannot_invoke_advisor(monkeypatch, request_data):
    state = critic_state(request_data)
    advisor = Mock()
    result = WorkflowState.model_validate(
        {**dict(state), **layout_recommendation(state, advisor=advisor)}
    )
    assert result.layout_recommendation.status == "disabled"
    assert not result.layout_recommendation.executed
    assert result.selection_source == "deterministic"
    advisor.assert_not_called()


def test_unsafe_fallback_terminates_instead_of_selecting_a_rejected_candidate(
    monkeypatch, request_data
):
    state = critic_state(request_data)
    state.reviews[0].accepted = False
    state.reviews[0].reason = "report_mismatch"
    advisor = Mock()
    result = WorkflowState.model_validate(
        {**dict(state), **layout_recommendation(state, advisor=advisor)}
    )
    assert result.status == "rejected" and result.selected_candidate_index is None
    assert result.error.code == "no_approved_candidates"
    advisor.assert_not_called()


def test_advisor_cannot_execute_twice(monkeypatch, request_data):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")
    state = critic_state(request_data)
    advisor = Mock(side_effect=mocked_advice)
    first = WorkflowState.model_validate(
        {**dict(state), **layout_recommendation(state, advisor=advisor)}
    )
    second = WorkflowState.model_validate(
        {**dict(first), **layout_recommendation(first, advisor=advisor)}
    )
    assert second.status == "failed" and second.error.code == "iteration_limit"
    assert second.selected_candidate_index is None
    advisor.assert_called_once()


def test_offline_demo_reuses_existing_mock_and_restores_environment(
    monkeypatch, offline
):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "0")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-use-real-key")
    before = dict(os.environ)
    deterministic, recommended = offline_workflow_comparison()
    assert dict(os.environ) == before
    assert deterministic.selected_candidate_index == 0
    assert recommended.selected_candidate_index == 1
    assert recommended.layout_recommendation.advice.mode == "offline_fixture"
    assert "do-not-use-real-key" not in recommended.model_dump_json()
    offline.assert_not_called()


@pytest.mark.parametrize("json_output", [False, True])
def test_actual_advised_demo_cli_is_offline_and_reproducible(json_output):
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "archimind.examples.advised_workflow",
            *(["--json"] if json_output else []),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": os.defpath, "PYTHONNOUSERSITE": "1", "LANGSMITH_TRACING": "false"},
    )
    assert process.returncode == 0 and process.stderr == ""
    if json_output:
        payload = json.loads(process.stdout)
        assert payload["mode"] == "offline_mock"
        default = WorkflowState.model_validate_json(
            json.dumps(payload["deterministic"])
        )
        advised = WorkflowState.model_validate_json(json.dumps(payload["recommended"]))
        assert (
            default.selected_candidate_index == 0
            and advised.selected_candidate_index == 1
        )
        assert (
            default.generation == advised.generation
            and default.reviews == advised.reviews
        )
    else:
        assert (
            "OFFLINE MOCK" in process.stdout
            and "zero live OpenAI requests" in process.stdout
        )
        assert "Default: Layout A (index 0)" in process.stdout
        assert "Advised: Layout B (index 1); score 67.614973" in process.stdout
