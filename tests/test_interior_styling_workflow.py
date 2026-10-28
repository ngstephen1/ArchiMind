"""E2 exercises the real graph and geometry with trusted mocks and no network."""

import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.agents import requirements_agent as api
from archimind.agents.interior_stylist_grounding import (
    interpret_style_proposal,
    prepare_stylist_context,
)
from archimind.agents.interior_stylist_schemas import (
    InteriorStyleProposal,
    InteriorStylistError,
    InteriorStylistResult,
)
from archimind.agents.requirements_schemas import Preference
from archimind.agents.spatial_critic_grounding import (
    interpret_critic_proposal,
    prepare_critic_context,
)
from archimind.agents.spatial_critic_schemas import SpatialCriticProposal
from archimind.examples import create_sample_bedroom
from archimind.examples.advise_layout import offline_layout_advisor
from archimind.examples.critique_layout import offline_spatial_critic
from archimind.examples.interpret_bedroom import offline_interpreter
from archimind.examples.requirements_fixture import SAMPLE_REQUEST, sample_extraction
from archimind.geometry import validate_accessibility
from archimind.workflow import (
    AIStylingState,
    DesignRequest,
    WorkflowState,
    nodes,
    run_workflow,
)
from archimind.workflow.graph import _guard
from archimind.workflow.interior_styling import interior_styling
from archimind.workflow.state import MAX_NODE_EXECUTIONS

STYLE = "Scandinavian bedroom with warm white walls, light oak furniture, and muted sage accents."
PROTECTED = {
    "request",
    "design",
    "generation",
    "reviews",
    "selected_candidate_index",
    "selection_source",
    "approved_design",
    "layout_recommendation",
    "spatial_critique",
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("E2 tests cannot use network services")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    for name in (
        "ARCHIMIND_ENABLE_OPENAI_STYLIST",
        "ARCHIMIND_ENABLE_OPENAI_LAYOUT",
        "ARCHIMIND_ENABLE_OPENAI_CRITIC",
        "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS",
        "ARCHIMIND_OPENAI_MODEL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    client = Mock(side_effect=AssertionError("No live OpenAI client"))
    monkeypatch.setattr(api, "_client", client)
    yield client
    assert not attempts, "Caught network failures still count as unauthorized attempts"


@pytest.fixture
def request_data():
    return DesignRequest(specification=create_sample_bedroom(), style_request=STYLE)


def proposal_for(request):
    return InteriorStyleProposal(
        decision="style",
        theme_id="scandinavian",
        palette_id="scandi_warm_sage",
        wall_material_id="wall_warm_white",
        floor_material_id="floor_light_oak",
        furniture_finishes=[
            {"furniture_id": item.id, "material_id": "finish_light_oak"}
            for item in request.candidate.design.furniture
        ],
        accent_ids=["muted_sage"],
        rationale_code="finish_consistency",
        preference_assessments=[
            {
                "preference_index": index,
                "judgment": "favored" if index == 0 else "unverified",
            }
            for index in range(1 + len(request.soft_preferences))
        ],
        conflict_codes=[],
    )


def mock_stylist(request, *, allow_live_usage=False):
    assert allow_live_usage is True
    return interpret_style_proposal(
        prepare_stylist_context(request), proposal_for(request), mode="offline_fixture"
    )


def mock_critic(request, *, allow_live_usage=False):
    if request.layout_recommendation is not None:
        return offline_spatial_critic(request)
    return interpret_critic_proposal(
        prepare_critic_context(request),
        SpatialCriticProposal(
            decision="abstain",
            observations=[],
            preference_assessments=[
                {
                    "preference_index": index,
                    "judgment": "unverified",
                    "observation_indices": [],
                }
                for index in range(len(request.layout.soft_preferences))
            ],
            recommendation_stance="not_provided",
            stance_observation_indices=[],
        ),
        mode="offline_fixture",
    )


def enabled(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", "1")


def styled(request, **kwargs):
    return run_workflow(request, use_ai_stylist=True, allow_live_stylist=True, **kwargs)


def handoff(request):
    state = run_workflow(request)
    return WorkflowState.model_validate(
        {
            **dict(state),
            "status": "running",
            "stage": "spatial_critic",
            "styling": None,
            "trace": state.trace[:-1],
            "ai_styling": AIStylingState(requested=True, status="pending"),
        }
    )


def test_default_fixture_unchanged_even_with_all_flags_and_injections(
    monkeypatch, request_data, offline
):
    for role in ("STYLIST", "LAYOUT", "CRITIC", "REQUIREMENTS"):
        monkeypatch.setenv(f"ARCHIMIND_ENABLE_OPENAI_{role}", "1")
    callbacks = [Mock() for _ in range(4)]
    result = run_workflow(
        request_data,
        interior_stylist=callbacks[0],
        layout_advisor=callbacks[1],
        spatial_critic=callbacks[2],
        interpreter=callbacks[3],
    )
    assert result.status == "succeeded" and len(result.trace) == 4
    assert result.styling.palette == ["ivory", "slate", "natural oak"]
    assert result.ai_styling == AIStylingState(source="deterministic_fixture")
    assert result.selected_candidate_index == 0
    assert result.generation.candidates[0].score.total == 67.721925
    assert (
        result.trace[-1].message
        == "Attached deterministic neutral styling metadata; geometry unchanged."
    )
    for callback in [*callbacks, offline]:
        callback.assert_not_called()


@pytest.mark.parametrize(
    "flag,authorization,status,reason",
    [
        (None, True, "disabled", "feature_disabled"),
        ("0", True, "disabled", "feature_disabled"),
        ("true", True, "disabled", "feature_disabled"),
        ("1", False, "unavailable", "authorization_required"),
    ],
)
def test_gates_skip_ai_node_and_explicitly_label_fixture(
    monkeypatch, request_data, flag, authorization, status, reason
):
    if flag is not None:
        monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STYLIST", flag)
    callback = Mock()
    result = run_workflow(
        request_data,
        use_ai_stylist=True,
        allow_live_stylist=authorization,
        interior_stylist=callback,
    )
    assert result.status == "succeeded" and len(result.trace) == 4
    assert result.ai_styling.status == status and result.ai_styling.reason == reason
    assert result.ai_styling.requested and not result.ai_styling.executed
    assert result.ai_styling.source == result.styling.source == "deterministic_fixture"
    assert result.ai_styling.result is None
    assert reason in result.trace[-1].message
    callback.assert_not_called()


def test_success_is_separate_checked_metadata_and_preserves_all_authority(
    monkeypatch, request_data, offline
):
    enabled(monkeypatch)
    baseline = run_workflow(request_data)
    before = request_data.model_dump_json()
    callback = Mock(wraps=mock_stylist)
    generator = Mock(wraps=nodes.generate_layout_candidates)
    monkeypatch.setattr(nodes, "generate_layout_candidates", generator)
    result = styled(request_data, interior_stylist=callback)
    callback.assert_called_once()
    assert callback.call_args.kwargs == {"allow_live_usage": True}
    generator.assert_called_once()
    assert result.status == "succeeded" and result.styling is None
    assert result.ai_styling.status == "styled" and result.ai_styling.source == "ai"
    assert (
        result.ai_styling.result.mode == "offline_fixture"
        and result.ai_styling.result.model is None
    )
    assert result.ai_styling.result.plan.palette_id == "scandi_warm_sage"
    assert not result.ai_styling.result.plan.rendered
    assert result.model_dump(include=PROTECTED) == baseline.model_dump(
        include=PROTECTED
    )
    assert request_data.model_dump_json() == before
    assert [event.node for event in result.trace] == [
        "requirements_interpreter",
        "layout_designer",
        "spatial_critic",
        "ai_interior_stylist",
    ]
    assert (
        result.trace[-1].decision == "styled"
        and "offline_fixture" in result.trace[-1].message
    )
    assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    offline.assert_not_called()


@pytest.mark.parametrize(
    "advisor,critic,failure,count",
    [
        (False, False, False, 4),
        (True, False, False, 5),
        (False, True, False, 5),
        (True, True, False, 6),
        (True, True, True, 7),
    ],
)
def test_conditional_order_with_existing_roles_and_maximum_bound(
    monkeypatch, request_data, advisor, critic, failure, count
):
    enabled(monkeypatch)
    for role in ("LAYOUT", "CRITIC"):
        monkeypatch.setenv(f"ARCHIMIND_ENABLE_OPENAI_{role}", "1")
    request_data.soft_preferences = [
        "Prefer the desk near the north-facing window while maintaining a spacious room."
    ]
    callback = (
        Mock(side_effect=RuntimeError("secret-token"))
        if failure
        else Mock(wraps=mock_stylist)
    )
    result = styled(
        request_data,
        use_ai_layout=advisor,
        layout_advisor=offline_layout_advisor,
        use_ai_critic=critic,
        spatial_critic=mock_critic,
        interior_stylist=callback,
    )
    assert (
        result.status == "succeeded"
        and len(result.trace) == count <= MAX_NODE_EXECUTIONS == 7
    )
    assert result.selected_candidate_index == (1 if advisor else 0)
    target = callback.call_args.args[0]
    assert (
        target.candidate
        == result.generation.candidates[result.selected_candidate_index]
    )
    assert target.critique == (result.spatial_critique.result if critic else None)
    if failure:
        assert (
            result.ai_styling.source == "deterministic_fixture"
            and result.ai_styling.result.plan is None
        )
        assert [event.node for event in result.trace][-2:] == [
            "ai_interior_stylist",
            "interior_stylist",
        ]
    else:
        assert result.ai_styling.source == "ai" and result.styling is None


@pytest.mark.parametrize(
    "status,code",
    [
        ("unavailable", "authentication"),
        ("unavailable", "rate_limit"),
        ("error", "timeout"),
        ("error", "refusal"),
        ("error", "invalid_response"),
        ("error", "oversized_output"),
        ("error", "api_error"),
    ],
)
def test_typed_failures_are_sanitized_and_never_fabricate_ai_plan(
    monkeypatch, request_data, status, code
):
    enabled(monkeypatch)
    callback = Mock(
        return_value=InteriorStylistResult(
            status=status,
            message="secret-token /private/path",
            error=InteriorStylistError(code=code, message="secret-token /private/path"),
        )
    )
    baseline = run_workflow(request_data)
    result = styled(request_data, interior_stylist=callback)
    assert result.status == "succeeded" and len(result.trace) == 5
    assert result.ai_styling.status == status and result.ai_styling.reason == code
    assert result.ai_styling.result.error.code == code
    assert (
        result.ai_styling.result.plan is None
        and result.ai_styling.result.context is None
    )
    assert result.ai_styling.source == result.styling.source == "deterministic_fixture"
    assert result.model_dump(include=PROTECTED) == baseline.model_dump(
        include=PROTECTED
    )
    assert (
        "secret-token" not in result.model_dump_json()
        and "/private/path" not in result.model_dump_json()
    )


@pytest.mark.parametrize(
    "case",
    [
        "palette",
        "material",
        "unknown_id",
        "hex",
        "explanation",
        "context",
        "catalog",
        "model",
        "provenance",
        "raw_dict",
    ],
)
def test_malformed_or_forged_plans_fall_back_explicitly(
    monkeypatch, request_data, case
):
    enabled(monkeypatch)

    def callback(request, **kwargs):
        result = mock_stylist(request, **kwargs)
        if case == "palette":
            result.proposal.palette_id = "unknown-palette"
        elif case == "material":
            result.proposal.wall_material_id = "finish_light_oak"
        elif case == "unknown_id":
            result.proposal.furniture_finishes[0].furniture_id = "invented"
        elif case == "hex":
            result.plan.wall_finish = result.plan.wall_finish.model_copy(
                update={"base_color_hex": "#000000"}
            )
        elif case == "explanation":
            result.plan.explanation = (
                "secret-token /private/path fabricated explanation"
            )
        elif case == "context":
            result.context.request.style_request = "Modern"
        elif case == "catalog":
            result.context.catalog = result.context.catalog.model_copy(
                update={"version": "forged"}
            )
        elif case == "model":
            result.model = "unsupported-model"
        elif case == "provenance":
            result.mode = "not_evaluated"
        else:
            return {"status": "styled", "message": "secret-token"}
        return result

    result = styled(request_data, interior_stylist=callback)
    assert result.status == "succeeded" and result.ai_styling.status == "rejected"
    assert (
        result.ai_styling.reason == "invalid_style"
        and result.ai_styling.result.plan is None
    )
    assert (
        result.ai_styling.source == "deterministic_fixture" and len(result.trace) == 5
    )
    assert "secret-token" not in result.model_dump_json()


def test_existing_adapter_preflight_authentication_and_no_style_clarification(
    monkeypatch, request_data, offline
):
    enabled(monkeypatch)
    result = styled(request_data)
    assert (
        result.ai_styling.status == "unavailable"
        and result.ai_styling.reason == "authentication"
    )
    request_data.style_request = None
    result = styled(request_data)
    assert result.ai_styling.status == "needs_clarification"
    assert result.ai_styling.result.mode == "not_evaluated"
    assert result.ai_styling.result.clarification_reasons == ["missing_style_details"]
    assert (
        result.ai_styling.source == "deterministic_fixture"
        and result.styling is not None
    )
    offline.assert_not_called()


def test_model_clarification_is_checked_before_fixture(monkeypatch, request_data):
    enabled(monkeypatch)

    def clarify(request, **kwargs):
        proposal = InteriorStyleProposal(
            decision="request_clarification",
            theme_id=None,
            palette_id=None,
            wall_material_id=None,
            floor_material_id=None,
            furniture_finishes=[],
            accent_ids=[],
            rationale_code="clarification_needed",
            preference_assessments=[{"preference_index": 0, "judgment": "unverified"}],
            conflict_codes=["missing_style_details"],
        )
        return interpret_style_proposal(
            prepare_stylist_context(request), proposal, mode="offline_fixture"
        )

    result = styled(request_data, interior_stylist=clarify)
    assert result.ai_styling.status == "needs_clarification"
    assert result.ai_styling.result.proposal.decision == "request_clarification"
    assert result.ai_styling.result.plan is None and result.styling is not None


def test_existing_adapter_with_mocked_sdk_preserves_api_provenance(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-only")
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)

    def parse(**kwargs):
        from archimind.agents.interior_stylist_schemas import InteriorStylistContext

        context = InteriorStylistContext.model_validate_json(
            kwargs["input"][0]["content"]
        )
        proposal = proposal_for(context.request)
        return SimpleNamespace(
            status="completed",
            output=[],
            output_parsed=proposal,
            model_dump_json=lambda: proposal.model_dump_json(),
        )

    client.responses.parse.side_effect = parse
    monkeypatch.setattr(api, "_client", Mock(return_value=client))
    result = styled(request_data)
    assert result.ai_styling.status == "styled"
    assert (
        result.ai_styling.result.mode == "api_response"
        and result.ai_styling.result.model == api.DEFAULT_MODEL
    )
    client.responses.parse.assert_called_once()


@pytest.mark.parametrize(
    "case",
    ["invalid", "unverified", "missing_selection", "missing_generation", "score"],
)
def test_unsafe_handoffs_stop_before_adapter_without_fixture(
    monkeypatch, request_data, case
):
    enabled(monkeypatch)
    state = handoff(request_data)
    if case in ("invalid", "unverified", "score"):
        candidate = state.generation.candidates[state.selected_candidate_index]
        if case == "invalid":
            candidate.design.furniture[0].x_m = -1.0
        elif case == "unverified":
            candidate.design.room.doors = []
        else:
            candidate.score.total = 999.0
        state.approved_design = candidate.design.model_copy(deep=True)
    elif case == "missing_selection":
        state.selected_candidate_index = state.approved_design = (
            state.selection_source
        ) = None
    else:
        state.generation = None
    callback = Mock()
    updates = interior_styling(state, allow_live=True, stylist=callback)
    assert updates["status"] == "rejected" and updates["approved_design"] is None
    assert (
        updates["ai_styling"].reason == "unsafe_selection"
        and not updates["ai_styling"].executed
    )
    assert updates["styling"] is None
    callback.assert_not_called()


@pytest.mark.parametrize("case", ["empty", "unsupported", "missing", "forged"])
def test_generation_failures_skip_stylist(monkeypatch, request_data, case):
    enabled(monkeypatch)
    if case == "empty":
        request_data.max_attempts = 0
    elif case == "unsupported":
        request_data.specification.room.doors = []
    elif case == "missing":
        request_data.specification = None
    else:
        generated = nodes.generate_layout_candidates(
            request_data.specification.room, request_data.specification.furniture
        )
        for candidate in generated.candidates:
            candidate.design.furniture[0].x_m = -1.0
        monkeypatch.setattr(
            nodes, "generate_layout_candidates", lambda *args, **kwargs: generated
        )
    callback = Mock()
    result = styled(request_data, interior_stylist=callback)
    assert result.status != "succeeded" and result.selected_candidate_index is None
    assert result.ai_styling.status == "skipped" and not result.ai_styling.executed
    assert result.ai_styling.source is None and result.styling is None
    callback.assert_not_called()


def test_injected_callback_can_mutate_only_its_own_copy(monkeypatch, request_data):
    enabled(monkeypatch)
    baseline = run_workflow(request_data)

    def callback(request, **kwargs):
        result = mock_stylist(request, **kwargs)
        request.candidate.design.furniture.clear()
        request.candidate.design.room.name = "Mutated copy"
        return result

    result = styled(request_data, interior_stylist=callback)
    assert result.ai_styling.status == "styled"
    assert result.model_dump(include=PROTECTED) == baseline.model_dump(
        include=PROTECTED
    )


@pytest.mark.parametrize("outcome", ["success", "exception", "failure"])
def test_no_safe_fallback_if_authoritative_data_changes_during_callback(
    monkeypatch, request_data, outcome
):
    enabled(monkeypatch)
    state = handoff(request_data)

    def callback(request, **kwargs):
        result = mock_stylist(request, **kwargs)
        candidate = state.generation.candidates[state.selected_candidate_index]
        candidate.design.furniture[0].x_m = -1.0
        state.approved_design = candidate.design.model_copy(deep=True)
        if outcome == "exception":
            raise RuntimeError("secret-token")
        if outcome == "failure":
            return InteriorStylistResult(
                status="error",
                message="secret-token",
                error=InteriorStylistError(code="timeout", message="secret-token"),
            )
        return result

    updates = interior_styling(state, allow_live=True, stylist=callback)
    assert (
        updates["status"] == "rejected" and updates["selected_candidate_index"] is None
    )
    assert (
        updates["ai_styling"].reason == "unsafe_selection"
        and updates["ai_styling"].executed
    )
    assert updates["ai_styling"].source is None and updates["styling"] is None
    assert "secret-token" not in str(updates)


def test_fresh_verification_before_and_after_invocation(monkeypatch, request_data):
    enabled(monkeypatch)
    state = handoff(request_data)
    validator = Mock(wraps=validate_accessibility)
    monkeypatch.setattr(
        "archimind.workflow.interior_styling.validate_accessibility", validator
    )
    result = _guard(
        "ai_interior_stylist",
        lambda state: interior_styling(state, allow_live=True, stylist=mock_stylist),
    )(state)
    assert result["status"] == "succeeded" and validator.call_count == 2
    assert all(
        call.kwargs["area_tolerance_m2"] == 0.0 for call in validator.call_args_list
    )


def test_interpreted_style_is_used_without_enabling_unrequested_roles(monkeypatch):
    enabled(monkeypatch)
    request = DesignRequest(original_request=SAMPLE_REQUEST + " " + STYLE)
    extraction = sample_extraction()
    extraction.style = Preference(text=STYLE, source_text=STYLE)
    monkeypatch.setattr(
        "archimind.examples.interpret_bedroom.sample_extraction", lambda: extraction
    )
    callback = Mock(wraps=mock_stylist)
    # Explicit extraction evidence, not a newly inferred theme.
    result = styled(
        request,
        interpret_free_text=True,
        interpreter=offline_interpreter,
        interior_stylist=callback,
    )
    assert (
        callback.call_args.args[0].style_request
        == result.interpretation.extraction.style.text
    )
    assert result.ai_styling.status == "styled"
    assert (
        not result.layout_recommendation.executed
        and not result.spatial_critique.executed
    )


def test_legacy_json_defaults_and_deterministic_isolated_runs(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    original_environment = dict(os.environ)
    baseline = run_workflow(request_data)
    old = baseline.model_dump(mode="json")
    del old["ai_styling"]
    del old["request"]["style_request"]
    restored = WorkflowState.model_validate_json(json.dumps(old))
    assert restored.ai_styling == AIStylingState(source="deterministic_fixture")
    assert restored.styling == baseline.styling
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: styled(request_data, interior_stylist=mock_stylist), range(2)
            )
        )
    assert (
        results[0] == results[1]
        and results[0].model_dump_json() == results[1].model_dump_json()
    )
    assert dict(os.environ) == original_environment


@pytest.mark.parametrize("field", ["use_ai_stylist", "allow_live_stylist"])
@pytest.mark.parametrize("value", [1, "true", None])
def test_modes_require_exact_booleans(request_data, field, value):
    with pytest.raises(ValueError, match="boolean"):
        run_workflow(request_data, **{field: value})


def test_stylist_runs_at_most_once(monkeypatch, request_data):
    enabled(monkeypatch)
    first = styled(request_data, interior_stylist=mock_stylist)
    callback = Mock()
    updates = interior_styling(first, allow_live=True, stylist=callback)
    assert (
        updates["error"].code == "iteration_limit"
        and updates["approved_design"] is None
    )
    assert WorkflowState.model_validate({**dict(first), **updates}).status == "failed"
    callback.assert_not_called()


@pytest.mark.parametrize("failure", [False, True])
def test_changed_fresh_check_after_call_never_allows_success_or_fallback(
    monkeypatch, request_data, failure
):
    enabled(monkeypatch)
    state = handoff(request_data)
    unevaluated = state.approved_design.model_copy(deep=True)
    unevaluated.room.doors = []
    report = validate_accessibility(unevaluated, area_tolerance_m2=0.0)
    original = state.generation.candidates[0].validation
    monkeypatch.setattr(
        "archimind.workflow.interior_styling.validate_accessibility",
        Mock(side_effect=[original, report]),
    )
    callback = (
        Mock(side_effect=RuntimeError("secret-token")) if failure else mock_stylist
    )
    updates = interior_styling(state, allow_live=True, stylist=callback)
    result = WorkflowState.model_validate({**dict(state), **updates})
    assert (
        result.status == "rejected" and result.ai_styling.reason == "unsafe_selection"
    )
    assert result.approved_design is result.styling is None


def test_canonical_but_oversized_stylist_input_uses_safe_fixture(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    for item in request_data.specification.furniture:
        item.id = "x" * 101 + item.id
    callback = Mock()
    result = styled(request_data, interior_stylist=callback)
    assert result.status == "succeeded" and result.ai_styling.status == "rejected"
    assert (
        result.ai_styling.reason == "invalid_input" and not result.ai_styling.executed
    )
    assert result.styling is not None
    callback.assert_not_called()


def test_state_rejects_ai_plan_for_different_selected_candidate(
    monkeypatch, request_data
):
    enabled(monkeypatch)
    result = styled(request_data, interior_stylist=mock_stylist)
    result.ai_styling.candidate_index = 1
    with pytest.raises(ValidationError, match="selected source candidate"):
        WorkflowState.model_validate(result)
