"""D2: actual LangGraph/geometry, trusted offline fixtures, no network access."""

import json
import socket
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import APITimeoutError
from pydantic import ValidationError

from archimind.agents import requirements_agent as api
from archimind.agents import spatial_critic_agent
from archimind.agents.layout_grounding import (
    interpret_layout_proposal,
    prepare_layout_context,
)
from archimind.agents.layout_schemas import (
    LayoutAdviceError,
    LayoutAdviceResult,
    LayoutProposal,
)
from archimind.agents.spatial_critic_grounding import (
    interpret_critic_proposal,
    prepare_critic_context,
)
from archimind.agents.spatial_critic_schemas import (
    CriticObservationProposal,
    SpatialCriticError,
    SpatialCriticProposal,
    SpatialCriticRequest,
    SpatialCriticResult,
)
from archimind.examples import create_sample_bedroom
from archimind.examples.interpret_bedroom import offline_interpreter
from archimind.examples.requirements_fixture import SAMPLE_REQUEST
from archimind.geometry import generate_layout_candidates
from archimind.workflow import (
    DesignRequest,
    SpatialCritiqueState,
    WorkflowState,
    nodes,
    run_workflow,
)
from archimind.workflow.spatial_critique import spatial_critique
from archimind.workflow.state import MAX_NODE_EXECUTIONS

PREFERENCE = (
    "Prefer the desk near the north-facing window while maintaining a spacious room."
)
BASE_NODES = ["requirements_interpreter", "layout_designer", "spatial_critic"]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("D2 integration tests cannot use network services")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    for name in (
        "ARCHIMIND_ENABLE_OPENAI_CRITIC",
        "ARCHIMIND_ENABLE_OPENAI_LAYOUT",
        "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS",
        "ARCHIMIND_OPENAI_MODEL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    client = Mock(side_effect=AssertionError("No live OpenAI client"))
    monkeypatch.setattr(api, "_client", client)
    yield client
    assert not attempts, "Caught network errors still count as unauthorized attempts"


@pytest.fixture
def request_data():
    return DesignRequest(
        specification=create_sample_bedroom(), soft_preferences=[PREFERENCE]
    )


def mock_advisor(request, *, allow_live=False):
    return interpret_layout_proposal(
        prepare_layout_context(request),
        LayoutProposal(
            decision="recommend",
            candidate_index=len(request.generation.candidates) - 1,
            rationale_code="preference_balance",
            evidence_refs=[],
            preference_assessments=[
                {"preference_index": i, "judgment": "favored"}
                for i in range(len(request.soft_preferences))
            ],
            limitation_codes=["subjective_preferences"],
        ),
        mode="offline_fixture",
    )


def mock_critic(
    request, *, allow_live_usage=False, stance="supports", decision="critique"
):
    context = prepare_critic_context(request)
    advice = request.layout_recommendation
    if advice is None:
        stance = "not_provided"
    if decision in ("abstain", "request_information"):
        proposal = SpatialCriticProposal(
            decision=decision,
            observations=[]
            if decision == "abstain"
            else [
                {
                    "category": "missing_evidence",
                    "candidate_indices": [],
                    "furniture_ids": [],
                    "evidence_refs": [],
                    "relation": "unknown",
                    "missing_topic": "ergonomics",
                }
            ],
            preference_assessments=[
                {
                    "preference_index": i,
                    "judgment": "unverified",
                    "observation_indices": [],
                }
                for i in range(len(request.layout.soft_preferences))
            ],
            recommendation_stance="not_provided"
            if advice is None
            else "cannot_evaluate",
            stance_observation_indices=[],
        )
    elif len(request.layout.generation.candidates) == 1:
        proposal = SpatialCriticProposal(
            decision="critique",
            observations=[
                {
                    "category": "spatial_validation",
                    "candidate_indices": [0],
                    "furniture_ids": [],
                    "evidence_refs": ["candidate-0.check.circulation"],
                    "relation": "reported",
                    "missing_topic": "none",
                }
            ],
            preference_assessments=[
                {
                    "preference_index": i,
                    "judgment": "unverified",
                    "observation_indices": [],
                }
                for i in range(len(request.layout.soft_preferences))
            ],
            recommendation_stance="not_provided"
            if advice is None
            else "cannot_evaluate",
            stance_observation_indices=[],
        )
    else:

        def compare(category, kind):
            desk_ids = {
                item.id
                for item in request.layout.specification.furniture
                if item.category == "desk"
            }
            facts = [
                fact
                for fact in context.features
                if fact.kind == kind
                and (kind != "window_planar_gap" or fact.furniture_id in desk_ids)
            ]
            first, second = [
                next(fact for fact in facts if fact.candidate_index == i)
                for i in (1, 0)
            ]
            return {
                "category": category,
                "candidate_indices": [1, 0],
                "furniture_ids": [first.furniture_id] if first.furniture_id else [],
                "evidence_refs": [first.ref, second.ref],
                "relation": "less"
                if first.value < second.value
                else "greater"
                if first.value > second.value
                else "equal",
                "missing_topic": "none",
            }

        proposal = SpatialCriticProposal(
            decision="critique",
            observations=[
                compare("window_proximity", "window_planar_gap"),
                compare("heuristic_score", "heuristic_score"),
                compare("usable_center_space", "usable_center_space_ratio"),
            ],
            preference_assessments=[
                {
                    "preference_index": i,
                    "judgment": "tradeoff",
                    "observation_indices": [0, 2],
                }
                for i in range(len(request.layout.soft_preferences))
            ],
            recommendation_stance=stance,
            stance_observation_indices=[0]
            if stance == "supports"
            else [1, 2]
            if stance == "challenges"
            else [],
        )
    return interpret_critic_proposal(context, proposal, mode="offline_fixture")


def enabled(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_CRITIC", "1")
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_LAYOUT", "1")


@pytest.mark.parametrize(
    "advisor_on,critic_on,count",
    [(False, False, 4), (True, False, 5), (False, True, 5), (True, True, 6)],
)
def test_all_four_modes_preserve_selection_data_and_execution_bounds(
    monkeypatch, request_data, offline, advisor_on, critic_on, count
):
    baseline = run_workflow(request_data)
    before = request_data.model_dump_json()
    enabled(monkeypatch)
    advisor, critic = Mock(side_effect=mock_advisor), Mock(side_effect=mock_critic)
    result = run_workflow(
        request_data,
        use_ai_layout=advisor_on,
        use_ai_critic=critic_on,
        layout_advisor=advisor,
        spatial_critic=critic,
    )
    assert result.status == "succeeded"
    assert len(result.trace) == count <= MAX_NODE_EXECUTIONS == 6
    expected_nodes = (
        BASE_NODES
        + (["layout_advisor"] if advisor_on else [])
        + (["ai_spatial_critic"] if critic_on else [])
        + ["interior_stylist"]
    )
    assert [event.node for event in result.trace] == expected_nodes
    assert len({event.node for event in result.trace}) == count
    selected = 1 if advisor_on else 0
    assert result.selected_candidate_index == selected
    assert result.selection_source == (
        "ai_recommendation" if advisor_on else "deterministic"
    )
    assert result.approved_design == baseline.generation.candidates[selected].design
    assert (
        result.generation == baseline.generation and result.reviews == baseline.reviews
    )
    assert request_data.model_dump_json() == before
    assert advisor.call_count == int(advisor_on) and critic.call_count == int(critic_on)
    if critic_on:
        metadata = result.spatial_critique
        assert metadata.executed and metadata.status == "evaluated"
        assert metadata.candidate_index == selected and metadata.candidate_indices == [
            0,
            1,
        ]
        assert metadata.result.context.request.reviewed_candidate_index == selected
        assert metadata.result.context.request.layout_recommendation == (
            result.layout_recommendation.advice if advisor_on else None
        )
        assert metadata.result.recommendation_stance == (
            "supports" if advisor_on else "not_provided"
        )
        assert "offline_fixture" in result.trace[-2].message
        assert f"selection unchanged at {selected}" in result.trace[-2].message
        assert f"Final selected candidate {selected}" in result.trace[-1].message
    else:
        assert result.spatial_critique.status == "not_requested"
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    offline.assert_not_called()


def test_critic_runs_after_independent_approval_and_advisor_before_styling(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    deterministic = Mock(wraps=nodes.spatial_critic)
    stylist = Mock(wraps=nodes.interior_stylist)
    generator = Mock(wraps=generate_layout_candidates)
    advisor = Mock(side_effect=mock_advisor)
    monkeypatch.setattr(nodes, "spatial_critic", deterministic)
    monkeypatch.setattr(nodes, "interior_stylist", stylist)
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)

    def critic(request, **kwargs):
        assert deterministic.call_count == advisor.call_count == 1
        assert stylist.call_count == 0 and request.reviewed_candidate_index == 1
        assert all(
            candidate.validation.status == "passed"
            for candidate in request.layout.generation.candidates
        )
        return mock_critic(request)

    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=advisor,
        spatial_critic=critic,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert (
        stylist.call_args.args[0].spatial_critique.result
        == result.spatial_critique.result
    )
    generator.assert_called_once()
    deterministic.assert_called_once()
    stylist.assert_called_once()


def test_grounded_challenge_records_tradeoffs_without_switching_candidate(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=mock_advisor,
        spatial_critic=lambda request, **kwargs: mock_critic(
            request, stance="challenges"
        ),
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert result.selection_source == "ai_recommendation"
    assert result.spatial_critique.result.recommendation_stance == "challenges"
    assert result.spatial_critique.result.observations[1].evidence[0].value == 67.614973
    assert result.spatial_critique.result.observations[1].evidence[1].value == 67.721925
    assert "stance=challenges" in result.trace[-2].message
    assert result.approved_design == result.generation.candidates[1].design


@pytest.mark.parametrize(
    "decision,status", [("abstain", "abstained"), ("request_information", "evaluated")]
)
def test_abstention_and_information_request_are_advisory(
    monkeypatch, request_data, decision, status
):
    enabled(monkeypatch)
    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=mock_advisor,
        spatial_critic=lambda request, **kwargs: mock_critic(
            request, decision=decision
        ),
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert result.spatial_critique.status == status
    assert result.spatial_critique.result.proposal.decision == decision
    assert result.spatial_critique.result.recommendation_stance == "cannot_evaluate"
    assert result.selection_source == "ai_recommendation"


@pytest.mark.parametrize(
    "code,status",
    [
        ("timeout", "error"),
        ("refusal", "error"),
        ("invalid_response", "error"),
        ("authentication", "unavailable"),
        ("rate_limit", "unavailable"),
    ],
)
def test_typed_failure_preserves_selected_candidate_and_sanitizes_messages(
    monkeypatch, request_data, code, status
):
    enabled(monkeypatch)
    critic = Mock(
        return_value=SpatialCriticResult(
            status=status,
            assessment="secret-token /private/path",
            error=SpatialCriticError(code=code, message="secret-token /private/path"),
        )
    )
    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=mock_advisor,
        spatial_critic=critic,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert (
        result.spatial_critique.status == status
        and result.spatial_critique.reason == code
    )
    assert result.spatial_critique.result.error.code == code
    assert (
        "secret-token" not in result.model_dump_json()
        and "/private/path" not in result.model_dump_json()
    )
    assert (
        result.trace[-2].decision == "fallback"
        and "Advisory feedback only" in result.trace[-2].message
    )
    critic.assert_called_once()


def test_unexpected_exception_is_sanitized_without_retry(monkeypatch, request_data):
    enabled(monkeypatch)
    critic = Mock(side_effect=RuntimeError("secret-token /private/path"))
    result = run_workflow(request_data, use_ai_critic=True, spatial_critic=critic)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.spatial_critique.reason == "critic_exception"
    assert result.spatial_critique.result.error.code == "api_error"
    assert "secret-token" not in result.model_dump_json()
    critic.assert_called_once()


@pytest.mark.parametrize(
    "corruption",
    [
        "target",
        "missing_target",
        "geometry",
        "report",
        "score",
        "feature",
        "object",
        "ref",
        "explanation",
        "stance",
        "mode",
        "fake_api",
        "model",
        "no_candidates",
    ],
)
def test_unknown_or_inconsistent_critique_is_rejected_without_selection_change(
    monkeypatch, request_data, corruption
):
    enabled(monkeypatch)

    def critic(request, **kwargs):
        result = mock_critic(request)
        if corruption == "target":
            result.context.request.reviewed_candidate_index = 0
        elif corruption == "missing_target":
            result.context.request.reviewed_candidate_index = None
        elif corruption == "geometry":
            result.context.request.layout.generation.candidates[1].design.furniture[
                0
            ].x_m += 0.1
        elif corruption == "report":
            result.context.request.layout.generation.candidates[1].validation.checks[
                "circulation"
            ].message = "Forged report"
        elif corruption == "score":
            result.context.request.layout.generation.candidates[1].score.total -= 1.0
        elif corruption == "feature":
            result.context.features[0].value += 1.0
        elif corruption == "object":
            result.proposal.observations[0].furniture_ids = ["unknown-furniture"]
        elif corruption == "ref":
            result.proposal.observations[0].evidence_refs = ["candidate-9.forged"]
        elif corruption == "explanation":
            result.observations[0].explanation = "Invented daylight measurement"
        elif corruption == "stance":
            result.recommendation_stance = "challenges"
        elif corruption == "mode":
            result.mode = "not_evaluated"
        elif corruption == "fake_api":
            result.mode = "api_response"
            result.model = api.DEFAULT_MODEL
        elif corruption == "model":
            result.model = api.DEFAULT_MODEL
        else:
            return SpatialCriticResult(
                status="no_candidates", assessment="Unexpected empty packet"
            )
        return result

    baseline = run_workflow(request_data)
    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=mock_advisor,
        spatial_critic=critic,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert result.spatial_critique.status == "rejected"
    assert (
        result.spatial_critique.reason
        == result.spatial_critique.result.error.code
        == "invalid_evidence"
    )
    assert result.spatial_critique.result.context is None
    assert (
        result.generation == baseline.generation and result.reviews == baseline.reviews
    )


@pytest.mark.parametrize("flag", [None, "0", "true"])
def test_disabled_critic_skips_node_and_injection_even_with_authorization(
    monkeypatch, request_data, offline, flag
):
    if flag is not None:
        monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_CRITIC", flag)
    critic = Mock()
    result = run_workflow(
        request_data, use_ai_critic=True, allow_live_critic=True, spatial_critic=critic
    )
    assert len(result.trace) == 4 and result.spatial_critique.status == "disabled"
    assert (
        result.spatial_critique.reason == "feature_disabled"
        and not result.spatial_critique.executed
    )
    assert (
        result.selected_candidate_index == 0
        and result.selection_source == "deterministic"
    )
    critic.assert_not_called()
    offline.assert_not_called()


def test_workflow_opt_in_and_call_authorization_are_independent(
    monkeypatch, request_data, offline
):
    enabled(monkeypatch)
    critic = Mock()
    skipped = run_workflow(request_data, allow_live_critic=True, spatial_critic=critic)
    assert (
        len(skipped.trace) == 4 and skipped.spatial_critique.status == "not_requested"
    )
    critic.assert_not_called()
    adapter = Mock(wraps=spatial_critic_agent.critique_design)
    monkeypatch.setattr(spatial_critic_agent, "critique_design", adapter)
    result = run_workflow(request_data, use_ai_critic=True)
    assert len(result.trace) == 5 and result.selected_candidate_index == 0
    assert result.spatial_critique.status == "unavailable"
    assert result.spatial_critique.reason == "authorization_required"
    adapter.assert_called_once()
    offline.assert_not_called()


@pytest.mark.parametrize(
    "options", [{"use_ai_critic": 1}, {"allow_live_critic": "true"}]
)
def test_critic_flags_reject_truthy_nonbooleans(request_data, options):
    with pytest.raises(ValueError, match="boolean"):
        run_workflow(request_data, **options)


def test_actual_adapter_timeout_is_handled_and_selection_retained(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.side_effect = APITimeoutError(
        request=httpx2.Request("POST", "https://api.openai.com/v1/responses")
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(api, "_client", factory)
    result = run_workflow(request_data, use_ai_critic=True, allow_live_critic=True)
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.spatial_critique.reason == "timeout"
    client.responses.parse.assert_called_once()
    factory.assert_called_once()


def test_actual_adapter_with_mock_client_keeps_verified_api_provenance(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)

    def parse(**options):
        context_request = json.loads(options["input"][0]["content"])["request"]
        request = SpatialCriticRequest.model_validate_json(json.dumps(context_request))
        proposal = mock_critic(request).proposal
        return SimpleNamespace(
            status="completed",
            output=[],
            output_parsed=proposal,
            model_dump_json=lambda: proposal.model_dump_json(),
        )

    client.responses.parse.side_effect = parse
    monkeypatch.setattr(api, "_client", Mock(return_value=client))
    result = run_workflow(request_data, use_ai_critic=True, allow_live_critic=True)
    assert (
        result.status == "succeeded" and result.spatial_critique.status == "evaluated"
    )
    assert result.spatial_critique.result.mode == "api_response"
    assert result.spatial_critique.result.model == api.DEFAULT_MODEL
    client.responses.parse.assert_called_once()


@pytest.mark.parametrize("both", [False, True])
def test_only_approved_candidates_reach_critic_with_original_index_mapping(
    monkeypatch, request_data, both
):
    enabled(monkeypatch)
    generated = generate_layout_candidates(
        request_data.specification.room, request_data.specification.furniture
    )
    generated.candidates[0].design.furniture[0].x_m = -1.0
    before = generated.model_dump_json()
    monkeypatch.setattr(
        nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
    )

    def critic(request, **kwargs):
        assert len(request.layout.generation.candidates) == 1
        assert request.layout.generation.candidates[0] == generated.candidates[1]
        assert request.reviewed_candidate_index == 0
        return mock_critic(request)

    result = run_workflow(
        request_data,
        use_ai_layout=both,
        use_ai_critic=True,
        layout_advisor=mock_advisor,
        spatial_critic=critic,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 1
    assert (
        result.spatial_critique.candidate_index == 1
        and result.spatial_critique.candidate_indices == [1]
    )
    assert [review.accepted for review in result.reviews] == [False, True]
    assert result.generation.model_dump_json() == before == generated.model_dump_json()
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("case", ["all_rejected", "empty", "unsupported", "missing"])
def test_missing_or_unsafe_candidates_terminate_before_critic(
    monkeypatch, request_data, case
):
    enabled(monkeypatch)
    if case == "all_rejected":
        generated = generate_layout_candidates(
            request_data.specification.room, request_data.specification.furniture
        )
        for candidate in generated.candidates:
            candidate.design.furniture[0].x_m = -1.0
        monkeypatch.setattr(
            nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
        )
    elif case == "empty":
        request_data.max_attempts = 0
    elif case == "unsupported":
        request_data.specification.room.doors = []
    else:
        request_data.specification = None
    critic = Mock()
    result = run_workflow(request_data, use_ai_critic=True, spatial_critic=critic)
    assert result.status != "succeeded" and result.selected_candidate_index is None
    assert (
        result.spatial_critique.status == "skipped"
        and not result.spatial_critique.executed
    )
    assert "ai_spatial_critic" not in [item.node for item in result.trace]
    critic.assert_not_called()


@pytest.mark.parametrize("failure", ["error", "abstained", "rejected"])
def test_failed_or_abstained_layout_advice_is_not_invented_as_a_recommendation(
    monkeypatch, request_data, failure
):
    enabled(monkeypatch)

    def advisor(request, **kwargs):
        if failure == "error":
            return LayoutAdviceResult(
                status="error",
                rationale="Failure",
                error=LayoutAdviceError(code="timeout", message="Failure"),
            )
        result = mock_advisor(request)
        if failure == "rejected":
            result.rationale = "Forged rationale"
            return result
        proposal = result.proposal.model_copy(
            update={
                "decision": "abstain",
                "candidate_index": None,
                "rationale_code": "no_clear_preference",
                "preference_assessments": [
                    {"preference_index": 0, "judgment": "uncertain"}
                ],
            }
        )
        return interpret_layout_proposal(
            result.context, proposal, mode="offline_fixture"
        )

    def critic(request, **kwargs):
        assert (
            request.layout_recommendation is None
            and request.reviewed_candidate_index == 0
        )
        return mock_critic(request)

    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=advisor,
        spatial_critic=critic,
    )
    assert result.status == "succeeded" and result.selected_candidate_index == 0
    assert result.selection_source == "deterministic" and len(result.trace) == 6
    assert result.spatial_critique.result.recommendation_stance == "not_provided"


def test_injected_critic_cannot_mutate_request_or_candidate_data(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    baseline = run_workflow(request_data)
    before = request_data.model_dump_json()

    def critic(request, **kwargs):
        result = mock_critic(request)
        request.layout.generation.candidates.clear()
        request.layout.specification.room.name = "Mutated copy"
        return result

    result = run_workflow(request_data, use_ai_critic=True, spatial_critic=critic)
    assert result.spatial_critique.status == "evaluated"
    assert (
        result.generation == baseline.generation and result.reviews == baseline.reviews
    )
    assert result.approved_design == baseline.approved_design
    assert request_data.model_dump_json() == before


def test_free_text_requirements_compatibility(monkeypatch):
    enabled(monkeypatch)
    request = DesignRequest(
        original_request=SAMPLE_REQUEST, soft_preferences=[PREFERENCE]
    )
    result = run_workflow(
        request,
        interpret_free_text=True,
        interpreter=offline_interpreter,
        use_ai_layout=True,
        layout_advisor=mock_advisor,
        use_ai_critic=True,
        spatial_critic=mock_critic,
    )
    assert (
        result.status == "succeeded" and result.interpretation.mode == "offline_fixture"
    )
    assert len(result.trace) == 6 and result.selected_candidate_index == 1
    assert (
        result.spatial_critique.result.context.request.layout.specification
        == result.interpretation.specification
    )


def test_no_preferences_skips_critic_without_an_adapter_call(monkeypatch, request_data):
    enabled(monkeypatch)
    request_data.soft_preferences = []
    critic = Mock()
    result = run_workflow(request_data, use_ai_critic=True, spatial_critic=critic)
    assert result.status == "succeeded" and len(result.trace) == 4
    assert (
        result.spatial_critique.status == "skipped"
        and result.spatial_critique.reason == "no_preferences"
    )
    critic.assert_not_called()


def test_legacy_state_json_defaults_to_no_ai_critique(request_data):
    baseline = run_workflow(request_data)
    payload = json.loads(baseline.model_dump_json())
    del payload["spatial_critique"]
    assert WorkflowState.model_validate_json(json.dumps(payload)) == baseline


@pytest.mark.parametrize("corruption", ["target", "mapping", "advice", "selection"])
def test_serialized_state_rejects_inconsistent_review_provenance(
    monkeypatch, request_data, corruption
):
    enabled(monkeypatch)
    result = run_workflow(
        request_data,
        use_ai_layout=True,
        use_ai_critic=True,
        layout_advisor=mock_advisor,
        spatial_critic=mock_critic,
    )
    if corruption == "target":
        result.spatial_critique.candidate_index = 0
    elif corruption == "mapping":
        result.spatial_critique.candidate_indices = [1, 0]
    elif corruption == "advice":
        result.spatial_critique.result.context.request.layout_recommendation = None
    else:
        result.selected_candidate_index = 0
        result.approved_design = result.generation.candidates[0].design
    with pytest.raises(ValidationError):
        WorkflowState.model_validate(result)


def test_reproducible_concurrent_runs_have_isolated_json_state(
    monkeypatch, request_data
):
    enabled(monkeypatch)

    def run(_):
        return run_workflow(
            request_data,
            use_ai_layout=True,
            use_ai_critic=True,
            layout_advisor=mock_advisor,
            spatial_critic=mock_critic,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(run, range(2)))
    assert first == second and first.model_dump_json() == second.model_dump_json()
    first.spatial_critique.result.limitations.append("Changed after return")
    assert "Changed after return" not in second.model_dump_json()


def critic_state(request):
    state = WorkflowState(
        request=request,
        spatial_critique=SpatialCritiqueState(requested=True, status="pending"),
    )
    for operation in (
        nodes.requirements_interpreter,
        nodes.layout_designer,
        nodes.spatial_critic,
    ):
        state = WorkflowState.model_validate({**dict(state), **operation(state)})
    return state


def test_critic_cannot_execute_twice(monkeypatch, request_data):
    enabled(monkeypatch)
    state = critic_state(request_data)
    critic = Mock(side_effect=mock_critic)
    first = WorkflowState.model_validate(
        {**dict(state), **spatial_critique(state, critic=critic)}
    )
    second = WorkflowState.model_validate(
        {**dict(first), **spatial_critique(first, critic=critic)}
    )
    assert second.status == "failed" and second.error.code == "iteration_limit"
    assert second.selected_candidate_index is None
    critic.assert_called_once()


def test_no_safe_selection_prevents_advisory_fallback(monkeypatch, request_data):
    enabled(monkeypatch)
    state = critic_state(request_data)
    state.reviews[0].accepted, state.reviews[0].reason = False, "report_mismatch"
    critic = Mock()
    result = WorkflowState.model_validate(
        {**dict(state), **spatial_critique(state, critic=critic)}
    )
    assert result.status == "rejected" and result.error.code == "no_approved_candidates"
    assert result.selected_candidate_index is None
    critic.assert_not_called()


def test_late_feature_disable_skips_critic_invocation(monkeypatch, request_data):
    enabled(monkeypatch)
    state = critic_state(request_data)
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_CRITIC", "0")
    critic = Mock()
    result = WorkflowState.model_validate(
        {**dict(state), **spatial_critique(state, critic=critic)}
    )
    assert (
        result.spatial_critique.status == "disabled"
        and not result.spatial_critique.executed
    )
    assert result.selected_candidate_index == 0
    critic.assert_not_called()


def test_explicit_target_prevents_a_critique_of_only_another_candidate(
    monkeypatch, request_data
):
    enabled(monkeypatch)

    def critic(request, **kwargs):
        context = prepare_critic_context(request)
        proposal = mock_critic(request).proposal
        proposal.observations = [
            CriticObservationProposal(
                category="heuristic_score",
                candidate_indices=[1],
                furniture_ids=[],
                evidence_refs=["candidate-1.heuristic-score"],
                relation="reported",
                missing_topic="none",
            )
        ]
        proposal.preference_assessments[0].judgment = "unverified"
        proposal.preference_assessments[0].observation_indices = []
        # D1 itself rejects this before the workflow can accept an irrelevant review.
        with pytest.raises(ValueError, match="requested candidate"):
            interpret_critic_proposal(context, proposal, mode="offline_fixture")
        return mock_critic(request)

    result = run_workflow(request_data, use_ai_critic=True, spatial_critic=critic)
    assert (
        result.spatial_critique.status == "evaluated"
        and result.selected_candidate_index == 0
    )
