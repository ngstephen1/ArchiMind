"""Run with: python -m archimind.examples.generate_bedroom [--output result.json].

JSON includes the original room/furniture request, complete alternatives A/B,
spatial reports, and score components. Timing is sent to stderr, separately from
the deterministic JSON. The existing renderer can consume candidate.design.
"""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

from archimind.examples.sample_bedroom import create_sample_bedroom
from archimind.geometry.layout_generator import generate_layout_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-attempts", type=int, default=500)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    original = create_sample_bedroom()
    started = perf_counter()
    result = generate_layout_candidates(
        original.room,
        original.furniture,
        seed=arguments.seed,
        max_attempts=arguments.max_attempts,
    )
    elapsed = perf_counter() - started
    payload = (
        json.dumps(
            {
                "original_request": original.model_dump(mode="json"),
                "generation": result.model_dump(mode="json"),
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    if arguments.output:
        arguments.output.write_text(payload)
    else:
        print(payload, end="")
    print(
        f"{result.status}: {len(result.candidates)} alternatives in "
        f"{result.attempts_used} attempts; {elapsed:.6f} seconds",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
