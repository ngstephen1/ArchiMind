"""07C1 offline mock: compare real candidates without live API access or workflow edits."""

import argparse
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from archimind.agents import requirements_agent as api
from archimind.agents.layout_agent import recommend_layout
from archimind.agents.layout_grounding import prepare_layout_context
from archimind.agents.layout_schemas import LayoutAdviceRequest, LayoutProposal
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates


def offline_layout_advice():
    """A fixed mock client proposes a candidate using actual fixture geometry.

    This is not model-quality evidence and never substitutes for an unavailable
    real API. The client factory is always mocked and settings are restored.
    """
    design = create_sample_bedroom()
    generation = generate_layout_candidates(design.room, design.furniture)
    request = LayoutAdviceRequest(
        specification=design,
        generation=generation,
        soft_preferences=["Prefer the desk near the north-wall window."],
    )
    before = request.model_dump_json()
    context = prepare_layout_context(request)
    # Deterministic fixture construction, explicitly not a fabricated live response.
    best = min(
        (
            fact
            for fact in context.features
            if fact.kind == "window_planar_gap"
            and fact.furniture_id == "desk"
            and fact.opening_id == "north-window"
        ),
        key=lambda fact: (fact.value, fact.candidate_index),
    )
    proposal = LayoutProposal(
        decision="recommend",
        candidate_index=best.candidate_index,
        rationale_code="window_proximity",
        evidence_refs=[best.ref],
        preference_assessments=[{"preference_index": 0, "judgment": "favored"}],
        limitation_codes=["daylight_not_evaluated", "ergonomics_not_evaluated"],
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
    with patch.dict(
        os.environ,
        {
            "ARCHIMIND_ENABLE_OPENAI_LAYOUT": "1",
            "OPENAI_API_KEY": "offline-fixture-only",
            "ARCHIMIND_OPENAI_MODEL": api.DEFAULT_MODEL,
        },
    ):
        result = recommend_layout(
            request, allow_live=True, client_factory=Mock(return_value=client)
        )
    assert request.model_dump_json() == before
    assert result.context.request.generation == generation
    client.responses.parse.assert_called_once()
    return result.model_copy(
        update={"mode": "offline_fixture", "model": None}, deep=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    result = offline_layout_advice()
    if arguments.json:
        print(result.model_dump_json(indent=2))
    else:
        print("Task 07C1 OFFLINE MOCK — no live OpenAI request")
        print(
            f"Status: {result.status}; proposed candidate: {result.proposal.candidate_index}"
        )
        print(result.rationale)
        print("Computed geometric facts (not subjective judgments):")
        for fact in result.evidence:
            print(
                f"  Candidate {fact.candidate_index}: {fact.furniture_id} to {fact.opening_id} planar footprint gap = {fact.value:.6f} {fact.unit}"
            )
        for index, candidate in enumerate(result.context.request.generation.candidates):
            print(
                f"  Candidate {index}: unchanged heuristic score = {candidate.score.total:.6f}"
            )
        print(
            "Subjective judgment: north-window proximity is favored; daylight and ergonomics are not evaluated."
        )
        print(
            "Recommendation only; independent Spatial Critic approval is still required."
        )
    return 0 if result.status == "recommended" else 1


if __name__ == "__main__":
    sys.exit(main())
