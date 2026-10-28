"""Task 07D2 OFFLINE MOCK: default, supported B and challenged B; never live."""

import argparse
import json
import os
import sys
from functools import partial
from unittest.mock import Mock, patch

from archimind.examples import create_sample_bedroom
from archimind.examples.advise_layout import offline_layout_advisor
from archimind.examples.critique_layout import offline_spatial_critic
from archimind.workflow import DesignRequest, WorkflowState, run_workflow


def offline_critiqued_workflows() -> dict[str, WorkflowState]:
    request = DesignRequest(
        specification=create_sample_bedroom(),
        seed=42,
        soft_preferences=[
            "Prefer the desk near the north-facing window while maintaining a spacious room."
        ],
    )
    before = request.model_dump_json()
    advisor = Mock(wraps=offline_layout_advisor)
    supporter = Mock(wraps=offline_spatial_critic)
    challenger = Mock(wraps=partial(offline_spatial_critic, stance="challenges"))
    with patch.dict(
        os.environ,
        {
            "ARCHIMIND_ENABLE_OPENAI_LAYOUT": "0",
            "ARCHIMIND_ENABLE_OPENAI_CRITIC": "0",
        },
    ):
        deterministic = run_workflow(
            request, layout_advisor=advisor, spatial_critic=supporter
        )
    advisor.assert_not_called()
    supporter.assert_not_called()
    with patch.dict(
        os.environ,
        {
            "ARCHIMIND_ENABLE_OPENAI_LAYOUT": "1",
            "ARCHIMIND_ENABLE_OPENAI_CRITIC": "1",
        },
    ):
        supported = run_workflow(
            request,
            use_ai_layout=True,
            use_ai_critic=True,
            layout_advisor=advisor,
            spatial_critic=supporter,
        )
        challenged = run_workflow(
            request,
            use_ai_layout=True,
            use_ai_critic=True,
            layout_advisor=advisor,
            spatial_critic=challenger,
        )
    assert advisor.call_count == 2
    supporter.assert_called_once()
    challenger.assert_called_once()
    assert (
        supporter.call_args.kwargs
        == challenger.call_args.kwargs
        == {"allow_live_usage": False}
    )
    assert all(call.kwargs == {"allow_live": False} for call in advisor.call_args_list)
    scenarios = {
        "scenario_a": deterministic,
        "scenario_b": supported,
        "scenario_c": challenged,
    }
    assert deterministic.selected_candidate_index == 0 and len(deterministic.trace) == 4
    assert (
        not deterministic.spatial_critique.executed
        and not deterministic.layout_recommendation.executed
    )
    for result, stance in ((supported, "supports"), (challenged, "challenges")):
        assert result.status == "succeeded" and len(result.trace) == 6
        assert (
            result.selected_candidate_index
            == result.spatial_critique.candidate_index
            == 1
        )
        assert result.selection_source == "ai_recommendation"
        assert result.approved_design == deterministic.generation.candidates[1].design
        assert result.spatial_critique.result.recommendation_stance == stance
        assert result.spatial_critique.result.mode == "offline_fixture"
        assert result.spatial_critique.result.model is None
        assert result.generation.candidates[1].score.total == 67.614973
    for result in scenarios.values():
        assert (
            result.generation == deterministic.generation
            and result.reviews == deterministic.reviews
        )
        assert all(review.accepted for review in result.reviews)
        assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    assert request.model_dump_json() == before
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    scenarios = offline_critiqued_workflows()
    if arguments.json:
        print(
            json.dumps(
                {
                    "mode": "offline_mock",
                    **{
                        name: result.model_dump(mode="json")
                        for name, result in scenarios.items()
                    },
                },
                indent=2,
            )
        )
    else:
        print("Task 07D2 OFFLINE MOCK — zero live OpenAI requests")
        for label, result in zip("ABC", scenarios.values(), strict=True):
            selected = result.selected_candidate_index
            critique = result.spatial_critique.result
            print(
                f"Scenario {label}: Layout {'AB'[selected]} (index {selected}); score {result.generation.candidates[selected].score.total:.6f}; "
                f"{len(result.trace)} nodes; source {result.selection_source}; critic {critique.recommendation_stance if critique else 'not invoked'}"
            )
        print(
            "B and C retain Layout B after independent spatial approval. A challenge never switches selection."
        )
        for observation in scenarios["scenario_b"].spatial_critique.result.observations:
            print(observation.explanation)
        print(
            "Scenario C: "
            + scenarios["scenario_c"].spatial_critique.result.recommendation_explanation
        )
        print(
            "Both candidate geometries/scores and authoritative critic reports are identical across all scenarios."
        )
        print(
            "Advisory mock only; actual daylight, ergonomics, usability and code compliance remain unverified."
        )
        print("Scenario C trace:")
        for event in scenarios["scenario_c"].trace:
            print(
                f"  {event.sequence}. {event.node} [{event.decision}] {event.message}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
