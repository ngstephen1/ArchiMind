"""Evaluate Town's Decisions rubric on labeled brief pairs."""

import argparse
import json
import math
import os
import time
from hashlib import sha256
from pathlib import Path

from run_with_agent import settings_from_dotenv

from archimind.town import decisions

ROOT = Path(__file__).resolve().parents[1]


def score(rows, threshold):
    missed, false_flags = [], []
    for row in rows:
        expected = set(row["expected_flags"])
        flagged = set(decisions.flagged(row["review"], threshold))
        missed.extend([row["case"], flag] for flag in sorted(expected - flagged))
        false_flags.extend([row["case"], flag] for flag in sorted(flagged - expected))
    return {
        "threshold": threshold,
        "missed": missed,
        "false_flags": false_flags,
        "passed": not missed and len(false_flags) <= 1,
    }


def brief_keys(cases):
    return {
        " ".join(row["input"]["original_brief"].casefold().split()) for row in cases
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "docs/data/town-decisions/public-cases.json",
    )
    parser.add_argument("--threshold", type=float, choices=decisions.THRESHOLDS)
    parser.add_argument("--public-receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_bytes())["cases"]
    if not 1 <= len(cases) <= 36 or len({row["case"] for row in cases}) != len(cases):
        parser.error("Expected 1 to 36 cases with distinct IDs.")
    if any(
        not set(row["expected_flags"]) <= decisions.CRITERIA.keys() for row in cases
    ):
        parser.error("Unknown expected flag.")
    print(f"Validated {len(cases)} labeled cases for {decisions.RUBRIC}.")
    if not args.live:
        return
    if not args.output:
        parser.error("--live requires --output for the receipt.")
    cases_hash = sha256(args.cases.read_bytes()).hexdigest()
    public_hash = None
    if args.threshold is not None:
        if len(cases) != 6 or not args.public_receipt:
            parser.error(
                "Held-out evaluation requires six cases and a public calibration receipt."
            )
        raw = args.public_receipt.read_bytes()
        public = json.loads(raw)
        expected_corpus = ROOT / "docs/data/town-decisions/public-cases.json"
        if (
            public.get("rubric") != decisions.RUBRIC
            or public.get("model") != decisions.MODEL
            or public.get("requests") != 36
            or public.get("responses_complete") is not True
            or public.get("selected_threshold") != args.threshold
            or public.get("public_cases_sha256")
            != sha256(expected_corpus.read_bytes()).hexdigest()
            or not any(
                row.get("threshold") == args.threshold and row.get("passed") is True
                for row in public.get("scores", [])
            )
        ):
            parser.error("The public calibration did not qualify this threshold.")
        public_cases = json.loads(expected_corpus.read_bytes())["cases"]
        heldout = brief_keys(cases)
        if (
            "" in heldout
            or len(heldout) != len(cases)
            or heldout & brief_keys(public_cases)
        ):
            parser.error(
                "Held-out briefs must be distinct from each other and the public corpus."
            )
        public_hash = sha256(raw).hexdigest()
    key = os.getenv("OPENAI_API_KEY") or settings_from_dotenv(args.env_file).get(
        "OPENAI_API_KEY"
    )
    if not key:
        parser.error("Server credentials are unavailable.")
    rows = [
        {
            "case": case["case"],
            "expected_flags": case["expected_flags"],
            "review": decisions.audit(
                case["input"], key=key, deadline=time.monotonic() + 20
            ),
        }
        for case in cases
    ]
    scores = [
        score(rows, threshold)
        for threshold in (
            decisions.THRESHOLDS if args.threshold is None else (args.threshold,)
        )
    ]
    complete = all(row["review"]["status"] == "checked" for row in rows)
    durations = sorted(row["review"]["elapsed_ms"] for row in rows)
    p95 = durations[math.ceil(len(durations) * 0.95) - 1]
    selected = (
        max(
            (result["threshold"] for result in scores if result["passed"]), default=None
        )
        if complete
        else None
    )
    receipt = {
        "model": decisions.MODEL,
        "rubric": decisions.RUBRIC,
        "requests": len(rows),
        "public_cases_sha256": cases_hash if public_hash is None else None,
        "public_calibration_sha256": public_hash,
        "responses_complete": complete,
        "input_tokens_reported": sum(
            row["review"]["input_tokens"] or 0 for row in rows
        ),
        "p95_ms": p95,
        "scores": scores,
        "selected_threshold": selected,
        "heldout_gate_passed": bool(public_hash and selected and p95 <= 3000),
        "cases": rows,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        f"{len(rows)} requests. Complete responses {complete}. "
        f"Selected threshold {selected}. P95 {p95} ms."
    )


if __name__ == "__main__":
    main()
