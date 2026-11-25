"""Calibrate and check independent Town Decisions review rubrics."""

import argparse
import json
import math
import os
from hashlib import sha256
from pathlib import Path

from run_with_agent import settings_from_dotenv

from archimind.town import decision_review, decisions

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/data/town-decision-reviews"
THRESHOLDS = decision_review.THRESHOLDS
COUNTS = decision_review.CASE_COUNTS
PRIOR = CORPUS / "revision-1.json"
CURRENT = ROOT / "docs/data/live-quality-proof/live-snapshot-r2.json"


def summary(kind, rows, threshold):
    expected = [row["expected"] for row in rows]
    selected = [
        row["label"] if row["confidence"] >= threshold else None for row in rows
    ]
    count = len(rows)
    correct = sum(
        guess == label for guess, label in zip(selected, expected, strict=True)
    )
    accepted = sum(guess is not None for guess in selected)
    p95 = sorted(row["elapsed_ms"] for row in rows)[math.ceil(0.95 * count) - 1]
    result = {
        "count": count,
        "correct": correct,
        "accepted": accepted,
        "p95_ms": p95,
        "complete": all(row["status"] == "checked" for row in rows),
    }
    if kind == "route":
        unsafe = [
            row["case"]
            for row, guess in zip(rows, selected, strict=True)
            if row["expected"] in ("answer", "compare") and guess in ("edit", "new")
        ]
        result.update(
            precision=correct / accepted if accepted else 0,
            coverage=accepted / count,
            saved_questions_routed_to_write=unsafe,
        )
    else:
        false_supported = [
            row["case"]
            for row, guess in zip(rows, selected, strict=True)
            if row["expected"] != "supported" and guess == "supported"
        ]
        result.update(recognition=correct / count, false_supported=false_supported)
    result["passed"] = decision_review.meets_gate(kind, result, count)
    return result


def collect(kind, cases, facts, key):
    rows = []
    for row in cases:
        result = decision_review.evaluate(
            kind, row["message"], facts=facts, claims=row.get("claims", ()), key=key
        )
        answer = result["answers"].get("intent" if kind == "route" else "claim_0") or {}
        rows.append(
            {
                "case": row["id"],
                "expected": row["expected"],
                "label": answer.get("label"),
                "confidence": answer.get("confidence", 0),
                "status": result["status"],
                "reason": result["reason"],
                "elapsed_ms": result["elapsed_ms"],
                "input_tokens": result["input_tokens"],
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=COUNTS)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--locked-threshold", type=float, choices=THRESHOLDS)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    kind = args.kind
    raw = (CORPUS / f"{kind}-cases.json").read_bytes()
    cases = json.loads(raw)
    dev = [row for row in cases if row["split"] == "development"]
    hold = [row for row in cases if row["split"] == "holdout"]
    labels = decision_review.ROUTES if kind == "route" else decision_review.CLAIM_LABELS
    if (
        (len(dev), len(hold)) != COUNTS[kind]
        or len(cases) != len(dev) + len(hold)
        or len({row["id"] for row in cases}) != len(cases)
        or any(
            {row["expected"] for row in split} != labels.keys() for split in (dev, hold)
        )
    ):
        parser.error("Invalid case manifest.")
    print(
        f"{kind}: validated {len(dev)} development and {len(hold)} holdout cases.",
        flush=True,
    )
    if not args.live:
        return
    if not args.output:
        parser.error("--live requires --output.")
    key = os.getenv("OPENAI_API_KEY") or settings_from_dotenv(args.env_file).get(
        "OPENAI_API_KEY"
    )
    if not key:
        parser.error("OpenAI credentials are unavailable.")
    facts = None
    if kind == "evidence":
        prior = json.loads(PRIOR.read_bytes())
        current = json.loads(CURRENT.read_bytes())
        if (
            prior["project"] != current["project"]
            or current["revision"] != prior["revision"] + 1
        ):
            parser.error("The evidence fixture revisions are unrelated.")
        facts = decision_review.evidence(
            current["home"], current["revision"], prior["home"]
        )

    development = collect(kind, dev, facts, key)
    metrics = {cutoff: summary(kind, development, cutoff) for cutoff in THRESHOLDS}
    # Freeze the cutoff before making any request for a holdout case.
    eligible = [
        cutoff
        for cutoff, stats in metrics.items()
        if stats["passed"]
        and (args.locked_threshold is None or cutoff == args.locked_threshold)
    ]
    threshold = (
        max(eligible, key=lambda cutoff: (metrics[cutoff]["accepted"], cutoff))
        if eligible
        else None
    )
    diagnostic_threshold = max(
        THRESHOLDS, key=lambda cutoff: (metrics[cutoff]["correct"], cutoff)
    )
    print(
        f"{kind}: frozen threshold {threshold}; diagnostic {diagnostic_threshold}.",
        flush=True,
    )
    holdout = collect(kind, hold, facts, key)
    heldout = summary(
        kind, holdout, threshold if threshold is not None else diagnostic_threshold
    )
    receipt = {
        "model": decisions.MODEL,
        "rubric": decision_review.RUBRICS[kind],
        "corpus_sha256": sha256(raw).hexdigest(),
        "source_fixture_sha256": (
            {
                path.name: sha256(path.read_bytes()).hexdigest()
                for path in (PRIOR, CURRENT)
            }
            if facts
            else None
        ),
        "evidence_schema": decision_review.EVIDENCE_SCHEMA if facts else None,
        "evidence_sha256": sha256(
            json.dumps(facts, sort_keys=True).encode()
        ).hexdigest()
        if facts
        else None,
        "threshold": threshold,
        "locked_threshold": args.locked_threshold,
        "diagnostic_threshold": diagnostic_threshold,
        "heldout_passed": bool(threshold is not None and heldout["passed"]),
        "development_metrics": metrics,
        "holdout_metrics": heldout,
        "development": development,
        "holdout": holdout,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(heldout), flush=True)


if __name__ == "__main__":
    main()
