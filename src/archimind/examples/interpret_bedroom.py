"""Task 07B offline mock demonstration. This CLI cannot issue a live model call."""

import argparse
import os
import sys
from unittest.mock import Mock, patch

from archimind.agents.requirements_agent import DEFAULT_MODEL, interpret_requirements
from archimind.examples.requirements_fixture import SAMPLE_REQUEST, sample_extraction
from archimind.workflow import DesignRequest, run_workflow


def offline_interpreter(description: str, *, allow_live: bool = False):
    """Exercise the gated API adapter with a fixed mock, never a real client.

    Test-only authorization/key are scoped and restored. The supplied factory
    always returns a mock and cannot fall back to a real SDK client.
    """
    parsed = sample_extraction()
    response = Mock()
    response.status, response.output, response.output_parsed = "completed", [], parsed
    response.model_dump_json.return_value = parsed.model_dump_json()
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.return_value = response
    factory = Mock(return_value=client)
    with patch.dict(
        os.environ,
        {
            "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS": "1",
            "OPENAI_API_KEY": "offline-fixture-only",
            "ARCHIMIND_OPENAI_MODEL": DEFAULT_MODEL,
        },
    ):
        result = interpret_requirements(
            description, allow_live=True, client_factory=factory
        )
    client.responses.parse.assert_called_once()
    return result.model_copy(
        update={"mode": "offline_fixture", "model": None}, deep=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Print the full workflow state"
    )
    arguments = parser.parse_args()
    state = run_workflow(
        DesignRequest(original_request=SAMPLE_REQUEST),
        interpret_free_text=True,
        interpreter=offline_interpreter,
    )
    if arguments.json:
        print(state.model_dump_json(indent=2))
    else:
        print("Task 07B OFFLINE MOCK — no live OpenAI request")
        print(
            f"Interpretation: {state.interpretation.status} ({state.interpretation.mode})"
        )
        print(f"Workflow: {state.status}")
        if state.generation:
            print(
                f"Generation: {len(state.generation.candidates)} candidates; {state.generation.attempts_used}/{state.generation.max_attempts} attempts"
            )
        print(f"Selected candidate: {state.selected_candidate_index} (zero-based)")
        for entry in state.trace:
            print(f"{entry.sequence}. {entry.node} [{entry.decision}] {entry.message}")
    return 0 if state.status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
