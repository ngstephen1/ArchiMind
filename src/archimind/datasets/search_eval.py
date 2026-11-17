"""P3 index evaluation: retrieval checks, empty queries, determinism and latency.

These metrics cover only the retrieval mechanics. They say nothing about
generated layout quality, because the generator does not change.
"""

import dataclasses
import statistics
import time
from collections import Counter

from archimind.datasets.canonical import digest
from archimind.datasets.search import (
    CategoryRequest,
    ReferencePack,
    ReferenceQuery,
    index_pack,
    search_references,
)

FINE_TERMS = (
    ("cabinet_shelf_desk", "nightstand"),
    ("cabinet_shelf_desk", "wardrobe"),
    ("table", "desk"),
    ("cabinet_shelf_desk", "bookcase"),
    ("sofa", "armchair"),
)


def self_query(entry) -> ReferenceQuery:
    """Room size plus admitted super-category counts of one scene (capped at 8)."""
    counts = Counter(category for category, _ in entry.objects)
    return ReferenceQuery(
        room=entry.scene.room,
        categories=tuple(
            CategoryRequest(category=c, count=min(n, 8))
            for c, n in sorted(counts.items())
        )[:8],
        max_scene_hits=10,
        max_asset_hits=0,
    )


def _timed(query, pack):
    start = time.perf_counter()
    result = search_references(query, pack=pack)
    return result, (time.perf_counter() - start) * 1000


def evaluate(pack: ReferencePack, *, reference_only_sample: int = 200) -> dict:
    if pack.status != "ready":
        return {"status": "unavailable", "reason": pack.reason}
    entries = pack.entries
    canonical = [e for e in entries if e.scene.tier == "canonical"]
    others = sorted(
        (e for e in entries if e.scene.tier == "reference_only"),
        key=lambda e: digest(e.scene.reference_id),
    )[:reference_only_sample]
    latencies, digests = [], []

    # 1. Self-retrieval: a scene's own size and category counts should find it.
    ranks = {"canonical": [], "reference_only": []}
    for entry in (*canonical, *others):
        result, ms = _timed(self_query(entry), pack)
        latencies.append(ms)
        digests.append(digest(result.model_dump()))
        ids = [h.reference_id for h in result.scene_hits]
        rank = (
            ids.index(entry.scene.reference_id) + 1
            if entry.scene.reference_id in ids
            else None
        )
        ranks[entry.scene.tier].append(rank)

    def recall(values, k):
        return (
            round(sum(1 for r in values if r is not None and r <= k) / len(values), 4)
            if values
            else None
        )

    # 2. Expected-category retrieval: every hit must hold the requested category.
    category_checks = {}
    categories = sorted({c for e in entries for c, _ in e.objects})
    requests = [(c, None) for c in categories] + list(FINE_TERMS)
    for category, term in requests:
        query = ReferenceQuery(
            categories=(CategoryRequest(category=category, term=term, count=1),),
            max_scene_hits=10,
            max_asset_hits=0,
        )
        result, ms = _timed(query, pack)
        latencies.append(ms)
        holds = [
            any(
                c == category and (term is None or term in words)
                for c, words in next(
                    e for e in entries if e.scene.reference_id == h.reference_id
                ).objects
            )
            for h in result.scene_hits
        ]
        category_checks[f"{category}/{term}" if term else category] = {
            "hits": len(holds),
            "precision": round(sum(holds) / len(holds), 4) if holds else None,
            "candidates": result.candidates,
        }

    # 3. Empty query.
    empty = search_references(ReferenceQuery(), pack=pack)

    # 4. Determinism: the same queries over an index built from reversed input.
    reversed_pack = index_pack(
        dataclasses.replace(pack.loaded, scenes=tuple(reversed(pack.loaded.scenes))),
        pack.root,
    )
    replay = [
        digest(search_references(self_query(e), pack=reversed_pack).model_dump())
        for e in (*canonical, *others)
    ]

    latencies.sort()
    return {
        "status": "evaluated",
        "pack_id": pack.pack_id,
        "snapshot_id": pack.snapshot_id,
        "indexed_scenes": len(entries),
        "folded_duplicates": sum(len(e.aliases) for e in entries),
        "self_retrieval": {
            tier: {
                "queries": len(values),
                "recall_at_1": recall(values, 1),
                "recall_at_3": recall(values, 3),
                "recall_at_10": recall(values, 10),
                "not_in_top_10": sum(1 for r in values if r is None),
            }
            for tier, values in ranks.items()
        },
        "expected_category": category_checks,
        "empty_query": {"status": empty.status, "reason": empty.reason},
        "deterministic_under_reordering": replay == digests,
        "latency_ms": {
            "queries": len(latencies),
            "p50": round(statistics.median(latencies), 2),
            "p95": round(latencies[int(0.95 * (len(latencies) - 1))], 2),
            "max": round(latencies[-1], 2),
        },
    }
