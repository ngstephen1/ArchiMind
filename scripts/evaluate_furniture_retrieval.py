"""Run fixed local 08R0 fixtures; never download or write an index/database."""

import argparse
import json
from pathlib import Path

from archimind.retrieval.evaluation import (
    RetrievalBenchmark,
    SyntheticCatalog,
    run_benchmark,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Create a new JSON result file; existing files are not overwritten",
    )
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "data" / "benchmarks"

    def read(name):
        with (root / name).open("rb") as stream:
            value = stream.read(1024 * 1024 + 1)
        if len(value) > 1024 * 1024:
            raise ValueError("Benchmark exceeds size limit")
        return value

    benchmark = RetrievalBenchmark.model_validate_json(
        read("furniture_retrieval_queries.json")
    )
    fixtures = SyntheticCatalog.model_validate_json(
        read("furniture_retrieval_synthetic.json")
    )
    result = run_benchmark(benchmark, fixtures, repeats=args.repeats)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(encoded)
        print("Created offline benchmark result:", args.output)
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
