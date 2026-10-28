"""Task 07E2 OFFLINE MOCK: fixture, mock catalog plan and explicit safe fallback."""

import argparse
import json
import os
import sys
from unittest.mock import Mock, patch

from archimind.agents.interior_stylist_schemas import (
    InteriorStylistError,
    InteriorStylistResult,
)
from archimind.examples import create_sample_bedroom
from archimind.examples.style_bedroom import offline_interior_stylist
from archimind.workflow import DesignRequest, WorkflowState, run_workflow


def offline_styled_workflows() -> dict[str, WorkflowState]:
    """Always inject the fixed E1 mock; no CLI option can enable a live client."""
    request = DesignRequest(
        specification=create_sample_bedroom(),
        seed=42,
        style_request="Scandinavian bedroom with warm white walls, light oak furniture, and muted sage accents.",
    )
    before = request.model_dump_json()
    stylist = Mock(wraps=offline_interior_stylist)
    unavailable = Mock(
        return_value=InteriorStylistResult(
            status="unavailable",
            message="Offline simulated timeout; no provider request was made.",
            error=InteriorStylistError(
                code="timeout",
                message="Offline simulated timeout; no provider request was made.",
            ),
        )
    )
    with patch.dict(os.environ, {"ARCHIMIND_ENABLE_OPENAI_STYLIST": "0"}):
        default = run_workflow(request, interior_stylist=stylist)
    stylist.assert_not_called()
    with patch.dict(os.environ, {"ARCHIMIND_ENABLE_OPENAI_STYLIST": "1"}):
        mocked = run_workflow(
            request,
            use_ai_stylist=True,
            allow_live_stylist=True,
            interior_stylist=stylist,
        )
        fallback = run_workflow(
            request,
            use_ai_stylist=True,
            allow_live_stylist=True,
            interior_stylist=unavailable,
        )
    stylist.assert_called_once()
    unavailable.assert_called_once()
    assert (
        stylist.call_args.kwargs
        == unavailable.call_args.kwargs
        == {"allow_live_usage": True}
    )
    assert (
        default.styling.source == default.ai_styling.source == "deterministic_fixture"
    )
    assert not default.ai_styling.executed and len(default.trace) == 4
    assert mocked.ai_styling.source == "ai" and mocked.styling is None
    assert (
        mocked.ai_styling.result.mode == "offline_fixture"
        and mocked.ai_styling.result.model is None
    )
    assert (
        mocked.ai_styling.result.plan.palette_id == "scandi_warm_sage"
        and len(mocked.trace) == 4
    )
    assert (
        fallback.ai_styling.status == "unavailable"
        and fallback.ai_styling.reason == "timeout"
    )
    assert (
        fallback.ai_styling.result.plan is None
        and fallback.ai_styling.source == "deterministic_fixture"
    )
    assert fallback.styling == default.styling and len(fallback.trace) == 5
    scenarios = {"scenario_a": default, "scenario_b": mocked, "scenario_c": fallback}
    for result in scenarios.values():
        assert result.status == "succeeded"
        assert result.selected_candidate_index == default.selected_candidate_index == 0
        assert result.selection_source == default.selection_source == "deterministic"
        assert result.approved_design == default.approved_design
        assert (
            result.generation == default.generation
            and result.reviews == default.reviews
        )
        assert result.generation.candidates[0].score.total == 67.721925
        assert (
            not result.layout_recommendation.executed
            and not result.spatial_critique.executed
        )
        assert WorkflowState.model_validate_json(result.model_dump_json()) == result
    assert request.model_dump_json() == before
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    scenarios = offline_styled_workflows()
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
        print("Task 07E2 OFFLINE MOCK — zero live OpenAI requests")
        for label, result in zip("ABC", scenarios.values(), strict=True):
            print(
                f"Scenario {label}: Layout A/index 0; score 67.721925; {len(result.trace)} nodes; style source {result.ai_styling.source}; status {result.ai_styling.status}; mode {result.ai_styling.result.mode if result.ai_styling.result else 'not_evaluated'}"
            )
        plan = scenarios["scenario_b"].ai_styling.result.plan
        print(
            f"B is explicitly MOCKED: theme {plan.theme_id}; palette {plan.palette_id}; wall {plan.wall_finish.material_id}; floor {plan.floor_finish.material_id}."
        )
        for identifier, finish in plan.furniture_finishes.items():
            print(
                f"Furniture {identifier}: {finish.material_id}; {finish.base_color_hex}"
            )
        print(
            "C simulates a timeout, retains its typed failure and runs the deterministic fixture; no AI plan is fabricated."
        )
        print(
            "Selection, room/openings, furniture IDs/coordinates/dimensions/rotations, original scores and complete validation reports are identical across A/B/C."
        )
        print(
            "Metadata only; no appearance is applied to either renderer. No live model behavior is verified."
        )
        for event in scenarios["scenario_c"].trace:
            print(
                f"  {event.sequence}. {event.node} [{event.decision}] {event.message}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
