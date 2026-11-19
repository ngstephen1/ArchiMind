"""Compare actual local Town retrieval, GBrain, and lexical search on identical passages."""

import argparse
import csv
import json
import math
import os
import re
import statistics
import time
from collections import Counter
from pathlib import Path

from archimind.design_evidence import ROOT, corpus, search_design_evidence, stamp, terms
from archimind.town.agents import search


def lexical(words, pages):
    # TF-IDF cosine similarity, with the same input terms and index text as GBrain.
    docs = {
        k: Counter(re.findall(r"[a-z0-9]+", (p["title"] + " " + p["excerpt"]).lower()))
        for k, p in pages.items()
    }
    idf = {
        w: 1 + math.log((1 + len(docs)) / (1 + sum(w in d for d in docs.values())))
        for w in set().union(*docs.values())
    }
    scores = {}
    for key, counts in docs.items():
        numerator = sum(counts[w] * idf.get(w, 0) ** 2 for w in words)
        if numerator:
            scores[key] = numerator / math.sqrt(
                sum((n * idf[w]) ** 2 for w, n in counts.items())
            )
    return sorted(scores, key=lambda key: (-scores[key], key))[:3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.environ["ARCHIMIND_ENABLE_DATASET_REFERENCES"] = "0"
    pages = corpus(ROOT)
    records = []
    with (ROOT / "data/benchmarks/design_evidence.tsv").open() as source:
        for case in csv.DictReader(source, delimiter="\t"):
            q = case["question"]
            native = search(q)
            start = time.monotonic()
            result = search_design_evidence(q)
            elapsed = time.monotonic() - start
            if result["status"] not in {"empty", "found"}:
                raise RuntimeError(f"Benchmark incomplete: {result['status']}")
            records.append(
                {
                    **case,
                    "gbrain": [h["id"] for h in result["hits"]],
                    "lexical": lexical(terms(q), pages),
                    "town_products": native["catalog_matches"],
                    "seconds": round(elapsed, 3),
                }
            )
    answerable = [r for r in records if r["expected_passage"] != "-"]
    unknown = [r for r in records if r["expected_passage"] == "-"]
    metrics = {
        engine: {
            "top_three": sum(r["expected_passage"] in r[engine] for r in answerable),
            "empty_on_unsupported": sum(not r[engine] for r in unknown),
        }
        for engine in ("gbrain", "lexical")
    }
    report = {
        "manifest": stamp(pages),
        "answerable": len(answerable),
        "unsupported": len(unknown),
        "metrics": metrics,
        "gbrain_median_seconds": statistics.median(r["seconds"] for r in records),
        "rows": records,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
