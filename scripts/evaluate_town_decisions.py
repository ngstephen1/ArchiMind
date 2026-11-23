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


def distinct_holdout(cases, public_cases):
    heldout = brief_keys(cases)
    drafts = {
        (
            " ".join(row["input"]["original_brief"].casefold().split()),
            json.dumps(row["input"]["proposed_brief"], sort_keys=True),
        )
        for row in cases
    }
    return (
        "" not in heldout
        and len(drafts) == len(cases)
        and not heldout.intersection(brief_keys(public_cases))
    )


def reviewed_payload_profile(cases):
    """Distinguish a reviewed app draft from the historical reduced examples."""
    for case in cases:
        payload = case["input"]
        proposed = payload["proposed_brief"]
        if (
            not isinstance(payload["confirmed_controls"], dict)
            or proposed.get("status")
            not in {"confirmed", "needs confirmation", "unsupported"}
            or any(
                not isinstance(proposed.get(field), list)
                for field in (
                    "requirements",
                    "sources",
                    "assumptions",
                    "questions",
                    "preferences",
                    "presentation_requests",
                    "unsupported",
                )
            )
        ):
            return None
        requirements = proposed["requirements"]
        sources = proposed["sources"]
        if (
            not requirements
            or not proposed["assumptions"]
            or len(sources) != len(requirements)
            or any(
                not isinstance(source, dict)
                or source.get("requirement") != requirement
                or source.get("origin")
                not in {"brief", "controls", "default", "saved revision", "interpreted"}
                for source, requirement in zip(sources, requirements, strict=True)
            )
        ):
            return None
    return decisions.APP_PAYLOAD_PROFILE


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
    parser.add_argument(
        "--public-corpus",
        type=Path,
        default=ROOT / "docs/data/town-decisions/public-cases.json",
    )
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
    payload_profile = reviewed_payload_profile(cases)
    public_hash = None
    if args.threshold is not None:
        if len(cases) != 6 or not args.public_receipt:
            parser.error(
                "Held-out evaluation requires six cases and a public calibration receipt."
            )
        raw = args.public_receipt.read_bytes()
        public = json.loads(raw)
        expected_corpus = args.public_corpus.read_bytes()
        public_cases = json.loads(expected_corpus)["cases"]
        if (
            payload_profile != decisions.APP_PAYLOAD_PROFILE
            or len(public_cases) != 36
            or reviewed_payload_profile(public_cases) != payload_profile
            or public.get("payload_profile") != payload_profile
            or public.get("rubric") != decisions.RUBRIC
            or public.get("model") != decisions.MODEL
            or public.get("requests") != 36
            or public.get("responses_complete") is not True
            or public.get("selected_threshold") != args.threshold
            or public.get("public_cases_sha256") != sha256(expected_corpus).hexdigest()
            or not any(
                row.get("threshold") == args.threshold and row.get("passed") is True
                for row in public.get("scores", [])
            )
        ):
            parser.error(
                "Promotion needs a qualifying app-shaped public calibration and matching holdout."
            )
        if not distinct_holdout(cases, public_cases):
            parser.error(
                "Holdout needs distinct brief-and-draft pairs and no public brief reuse."
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
        "payload_profile": payload_profile,
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
