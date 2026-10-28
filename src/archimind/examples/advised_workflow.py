"""07C2 OFFLINE MOCK: compare default and advised workflows; no live API calls."""

import argparse
import json
import os
import sys
from unittest.mock import Mock, patch

from archimind.examples import create_sample_bedroom
from archimind.examples.advise_layout import offline_layout_advisor
from archimind.workflow import DesignRequest, WorkflowState, run_workflow


def offline_workflow_comparison() -> tuple[WorkflowState, WorkflowState]:
    """Two fresh seed-42 runs; identical generation/critique, different selection."""
    request = DesignRequest(
        specification=create_sample_bedroom(),
        seed=42,
        soft_preferences=["Place the desk closer to the north-facing window."],
    )
    before = request.model_dump_json()
    advisor = Mock(wraps=offline_layout_advisor)
    with patch.dict(os.environ, {"ARCHIMIND_ENABLE_OPENAI_LAYOUT": "0"}):
        deterministic = run_workflow(request, layout_advisor=advisor)
    advisor.assert_not_called()
    # Opt in to the workflow fixture explicitly. The adapter client is always a
    # mock; neither the public runner nor this CLI authorizes live layout usage.
    with patch.dict(os.environ, {"ARCHIMIND_ENABLE_OPENAI_LAYOUT": "1"}):
        recommended = run_workflow(request, use_ai_layout=True, layout_advisor=advisor)
    advisor.assert_called_once()
    assert advisor.call_args.kwargs == {"allow_live": False}
    assert deterministic.status == recommended.status == "succeeded"
    assert deterministic.selected_candidate_index == 0
    assert deterministic.selection_source == "deterministic"
    assert recommended.selected_candidate_index == 1
    assert recommended.selection_source == "ai_recommendation"
    assert recommended.layout_recommendation.advice.mode == "offline_fixture"
    assert recommended.layout_recommendation.advice.model is None
    assert recommended.generation.candidates[1].score.total == 67.614973
    assert deterministic.generation == recommended.generation
    assert deterministic.reviews == recommended.reviews
    assert recommended.approved_design == recommended.generation.candidates[1].design
    assert all(review.accepted for review in recommended.reviews)
    assert request.model_dump_json() == before
    for result in (deterministic, recommended):
        assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    return deterministic, recommended


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    deterministic, recommended = offline_workflow_comparison()
    if arguments.json:
        print(
            json.dumps(
                {
                    "mode": "offline_mock",
                    "deterministic": deterministic.model_dump(mode="json"),
                    "recommended": recommended.model_dump(mode="json"),
                },
                indent=2,
            )
        )
    else:
        print("Task 07C2 OFFLINE MOCK — zero live OpenAI requests")
        for label, result in (("Default", deterministic), ("Advised", recommended)):
            selected = result.selected_candidate_index
            print(
                f"{label}: Layout {'AB'[selected]} (index {selected}); "
                f"score {result.generation.candidates[selected].score.total:.6f}; "
                f"source {result.selection_source}; {len(result.trace)} nodes"
            )
        print(
            "Generation, both candidate geometries/scores, and critic reports are identical."
        )
        advice = recommended.layout_recommendation.advice
        print(advice.rationale)
        for fact in advice.evidence:
            print(
                f"Candidate {fact.candidate_index}: {fact.furniture_id} → {fact.opening_id} "
                f"planar footprint gap {fact.value:.6f} {fact.unit}"
            )
        print("Advised trace:")
        for event in recommended.trace:
            print(
                f"  {event.sequence}. {event.node} [{event.decision}] {event.message}"
            )
        print(
            "Mock preference judgment only; daylight/ergonomics and live model quality are unverified."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
