"""Offline Task 07A demo: python -m archimind.examples.workflow_bedroom [--json]."""

import argparse
import sys

from pydantic import ValidationError

from archimind.examples.sample_bedroom import create_sample_bedroom
from archimind.workflow import (
    DesignRequest,
    StylingPreferences,
    WorkflowState,
    run_workflow,
)


def readable_result(result: WorkflowState) -> str:
    """Keep presentation separate from the deterministic, JSON-ready state."""
    lines = [
        "Task 07A deterministic workflow (no LLM calls)",
        f"Status: {result.status}",
    ]
    if result.generation is not None:
        generation = result.generation
        lines.append(
            f"Generation: {generation.status}; {len(generation.candidates)} candidates; "
            f"{generation.attempts_used}/{generation.max_attempts} attempts"
        )
    if result.approved_design is not None:
        lines.append(
            f"Selected candidate: {result.selected_candidate_index} (zero-based)"
        )
        review = next(
            item
            for item in result.reviews
            if item.candidate_index == result.selected_candidate_index
        )
        lines.append(f"Independent spatial checks: {review.report.status}")
        for item in result.approved_design.furniture:
            lines.append(
                f"  {item.id}: X/Y ({item.x_m:g}, {item.y_m:g}) m; "
                f"W/D/H {item.width_m:g}/{item.depth_m:g}/{item.height_m:g} m"
            )
    if result.styling is not None:
        lines.append(f"Styling: {result.styling.theme} ({result.styling.source})")
    if result.error is not None:
        lines.append(f"Error: {result.error.code}: {result.error.message}")
    lines.append("Trace:")
    for activity in result.trace:
        lines.append(
            f"  {activity.sequence}. {activity.node} [{activity.decision}] {activity.message}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-attempts", type=int, default=500)
    parser.add_argument(
        "--theme", choices=["neutral", "warm", "cool"], default="neutral"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full typed result as JSON"
    )
    arguments = parser.parse_args()
    try:
        request = DesignRequest(
            specification=create_sample_bedroom(),
            seed=arguments.seed,
            max_attempts=arguments.max_attempts,
            styling_preferences=StylingPreferences(theme=arguments.theme),
        )
    except ValidationError:
        parser.error("Seed or attempt budget exceeds supported limits.")
    result = run_workflow(request)
    print(
        result.model_dump_json(indent=2) if arguments.json else readable_result(result)
    )
    return 0 if result.status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
