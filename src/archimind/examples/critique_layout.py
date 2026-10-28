"""Task 07D1 OFFLINE MOCK: standalone critique, no live API calls or graph changes."""

import argparse
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from archimind.agents import requirements_agent as api
from archimind.agents.layout_schemas import LayoutAdviceRequest
from archimind.agents.spatial_critic_agent import critique_design
from archimind.agents.spatial_critic_schemas import (
    SpatialCriticProposal,
    SpatialCriticRequest,
    SpatialCriticResult,
)
from archimind.examples import create_sample_bedroom
from archimind.examples.advise_layout import offline_layout_advisor
from archimind.workflow import DesignRequest, WorkflowState, run_workflow


def offline_spatial_critic(
    request: SpatialCriticRequest,
    *,
    allow_live_usage: bool = False,
    stance: str = "supports",
) -> SpatialCriticResult:
    """Reusable D1 mock for the canonical two-candidate bedroom, never live.

    This is fixed fixture evidence, not model-quality evaluation or an automatic
    substitute for failed live requests. The client is always mocked. The usage
    argument is accepted for workflow DI compatibility, not used to enable live
    access. Settings are restored; candidates are supplied, never regenerated.
    """
    if stance not in ("supports", "challenges"):
        raise ValueError("Fixture supports only grounded support/challenge cases")
    request_before = request.model_dump_json()

    # The model fixture selects existing refs and qualitative codes only. Python
    # independently verifies these comparisons and supplies every numeric value.
    def comparison(category, suffix, furniture_ids):
        return {
            "category": category,
            "candidate_indices": [1, 0],
            "furniture_ids": furniture_ids,
            "evidence_refs": [f"candidate-{index}.{suffix}" for index in (1, 0)],
            "relation": "less",
            "missing_topic": "none",
        }

    proposal = SpatialCriticProposal(
        decision="critique",
        observations=[
            comparison(
                "window_proximity", "window-gap.furniture-0.opening-0", ["desk"]
            ),
            comparison("heuristic_score", "heuristic-score", []),
            comparison("usable_center_space", "usable-center-ratio", []),
        ],
        preference_assessments=[
            {
                "preference_index": 0,
                "judgment": "tradeoff",
                "observation_indices": [0, 2],
            }
        ],
        recommendation_stance=stance,
        stance_observation_indices=[0] if stance == "supports" else [1, 2],
    )
    response = SimpleNamespace(
        status="completed",
        output=[],
        output_parsed=proposal,
        model_dump_json=lambda: proposal.model_dump_json(),
    )
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.return_value = response
    factory = Mock(return_value=client)
    with patch.dict(
        os.environ,
        {
            "ARCHIMIND_ENABLE_OPENAI_CRITIC": "1",
            "OPENAI_API_KEY": "offline-fixture-only",
            "ARCHIMIND_OPENAI_MODEL": api.DEFAULT_MODEL,
        },
    ):
        result = critique_design(request, allow_live_usage=True, client_factory=factory)
    factory.assert_called_once_with("offline-fixture-only")
    client.responses.parse.assert_called_once()
    result = SpatialCriticResult.model_validate(
        result.model_copy(
            update={"mode": "offline_fixture", "model": None},
            deep=True,
        )
    )
    assert result.status == "evaluated" and result.recommendation_stance == stance
    assert request.model_dump_json() == request_before
    assert SpatialCriticResult.model_validate_json(result.model_dump_json()) == result
    return result


def offline_critique() -> tuple[WorkflowState, SpatialCriticResult]:
    """Original standalone demo; default graph selection stays separate from advice."""
    workflow = run_workflow(
        DesignRequest(specification=create_sample_bedroom(), seed=42)
    )
    before = workflow.model_dump_json()
    layout = LayoutAdviceRequest(
        specification=workflow.design,
        generation=workflow.generation,
        soft_preferences=[
            "Prefer the desk near the north-facing window while maintaining a spacious room."
        ],
    )
    advice = offline_layout_advisor(layout)
    assert advice.mode == "offline_fixture" and advice.proposal.candidate_index == 1
    result = offline_spatial_critic(
        SpatialCriticRequest(layout=layout, layout_recommendation=advice)
    )
    assert result.context.request.layout.generation == workflow.generation
    assert workflow.model_dump_json() == before
    assert len(workflow.trace) == 4 and workflow.selected_candidate_index == 0
    assert result.context.request.layout_recommendation == advice
    assert workflow.generation.candidates[1].score.total == 67.614973
    assert all(review.accepted for review in workflow.reviews)
    return workflow, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    workflow, result = offline_critique()
    if arguments.json:
        print(
            json.dumps(
                {
                    "mode": "offline_mock",
                    "workflow": workflow.model_dump(mode="json"),
                    "critique": result.model_dump(mode="json"),
                },
                indent=2,
            )
        )
    else:
        print("Task 07D1 OFFLINE MOCK — zero live OpenAI requests")
        print(
            "Canonical 5 × 4 m bedroom; seed 42; both independent spatial reports passed."
        )
        print(
            "Layout Designer mock: recommends Layout B (index 1), original score 67.614973."
        )
        print(f"AI critic mock: {result.recommendation_stance}; {result.assessment}")
        for index, observation in enumerate(result.observations):
            print(f"  {index}. {observation.explanation}")
        print(result.recommendation_explanation)
        for preference in result.preference_feedback:
            print(preference.explanation)
        print(
            "Confirmed proxies: B has the smaller desk/window gap; A has the higher existing score and usable-space ratio."
        )
        print(
            "Unverified: actual daylight, ergonomics, desk usability, code compliance and full preference satisfaction."
        )
        print(
            "Standalone advisory output: workflow selection remains Layout A (index 0); designer proposal remains B."
        )
        print("Geometry, dimensions, scores, reports and graph routing are unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
