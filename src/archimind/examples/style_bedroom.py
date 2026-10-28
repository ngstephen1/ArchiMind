"""Task 07E1 OFFLINE MOCK: catalog style metadata, no live calls or rendering."""

import argparse
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from archimind.agents import requirements_agent as api
from archimind.agents.interior_stylist_agent import recommend_style
from archimind.agents.interior_stylist_schemas import (
    InteriorStyleProposal,
    InteriorStylistRequest,
    InteriorStylistResult,
)
from archimind.examples import create_sample_bedroom
from archimind.workflow import DesignRequest, WorkflowState, run_workflow


def offline_style_bedroom() -> tuple[WorkflowState, InteriorStylistResult]:
    """Style the default graph's selected candidate outside LangGraph.

    The API client is always a mock, regardless of existing environment settings.
    This is fixed fixture evidence, never a fallback for an unavailable provider.
    """
    workflow = run_workflow(
        DesignRequest(specification=create_sample_bedroom(), seed=42)
    )
    before = workflow.model_dump_json()
    selected = workflow.selected_candidate_index
    request = InteriorStylistRequest(
        candidate=workflow.generation.candidates[selected],
        style_request="Scandinavian bedroom with warm white walls, light oak furniture, and muted sage accents.",
    )
    request_before = request.model_dump_json()
    proposal = InteriorStyleProposal(
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
        preference_assessments=[{"preference_index": 0, "judgment": "favored"}],
        conflict_codes=[],
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
            "ARCHIMIND_ENABLE_OPENAI_STYLIST": "1",
            "OPENAI_API_KEY": "offline-fixture-only",
            "ARCHIMIND_OPENAI_MODEL": api.DEFAULT_MODEL,
        },
    ):
        result = recommend_style(request, allow_live_usage=True, client_factory=factory)
    factory.assert_called_once_with("offline-fixture-only")
    client.responses.parse.assert_called_once()
    result = InteriorStylistResult.model_validate(
        result.model_copy(update={"mode": "offline_fixture", "model": None}, deep=True)
    )
    assert result.status == "styled" and result.plan.rendered is False
    assert workflow.model_dump_json() == before
    assert request.model_dump_json() == request_before
    assert result.context.request.candidate == workflow.generation.candidates[selected]
    assert result.context.request.candidate.design == workflow.approved_design
    assert (
        result.context.request.candidate.validation == workflow.reviews[selected].report
    )
    assert result.context.request.candidate.score.total == 67.721925
    assert workflow.selected_candidate_index == 0 and len(workflow.trace) == 4
    assert workflow.styling.source == "deterministic_fixture"
    assert InteriorStylistResult.model_validate_json(result.model_dump_json()) == result
    return workflow, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    workflow, result = offline_style_bedroom()
    if arguments.json:
        print(
            json.dumps(
                {
                    "mode": "offline_mock",
                    "workflow": workflow.model_dump(mode="json"),
                    "styling": result.model_dump(mode="json"),
                },
                indent=2,
            )
        )
    else:
        plan = result.plan
        print("Task 07E1 OFFLINE MOCK — zero live OpenAI requests")
        print(
            "Original room: 5 × 4 × 2.7 m; selected Layout A/index 0; spatial checks passed; original score 67.721925."
        )
        print(f"Theme: {plan.theme_id}; palette: {plan.palette_id}")
        for label, finish in (
            ("Walls", plan.wall_finish),
            ("Floor", plan.floor_finish),
        ):
            print(
                f"{label}: {finish.material_id}; {finish.base_color_hex}; {finish.label}"
            )
        for identifier, finish in plan.furniture_finishes.items():
            print(
                f"Furniture {identifier}: {finish.material_id}; {finish.base_color_hex}"
            )
        for accent in plan.accents:
            print(f"Accent: {accent.accent_id}; {accent.color_hex}")
        print(plan.explanation)
        for note in plan.preference_notes:
            print(note.explanation)
        print(
            "Geometry, coordinates, selected candidate, validation and scores are identical before/after styling."
        )
        print(
            "Existing LangGraph stylist fixture is unchanged; this is separate standalone metadata."
        )
        for limitation in plan.limitations:
            print("Limitation: " + limitation)
    return 0


if __name__ == "__main__":
    sys.exit(main())
