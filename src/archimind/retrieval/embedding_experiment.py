"""Explicit benchmark utilities; artificial products never enter real resolution."""

import hashlib
import json
import math
import statistics
import time
from collections import deque
from pathlib import Path

from archimind.retrieval.contracts import FurnitureSearchHit, FurnitureSearchResult
from archimind.retrieval.eligibility import build_index, digest
from archimind.retrieval.embedding_index import normalized_vectors
from archimind.retrieval.evaluation import (
    BenchmarkCase,
    RetrievalBenchmark,
    SyntheticCatalog,
    SyntheticRetrievalProvider,
)
from archimind.retrieval.semantic import AbstentionPolicy, rank_cosine

SPLIT_HASHES = {
    "development": "1800c1932ba13373de8e62a189a53393e71c97699a19fef288047180528fac29",
    "held_out": "e219d29f10de791627acfc573bb2108d8074f937d105b72b2a9e534f85ecd088",
}


def benchmark_inputs(root: Path, *, historical=False):
    def read(name):
        with (root / name).open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Benchmark exceeds limit")
        return raw

    original_bytes = read("furniture_retrieval_queries.json")
    original = RetrievalBenchmark.model_validate_json(original_bytes)
    synthetic = SyntheticCatalog.model_validate_json(
        read("furniture_retrieval_synthetic.json")
    )
    from archimind.retrieval.historical import historical_index

    corpus = historical_index() if historical else build_index()
    if (
        original.real_index_identity != corpus.identity
        or original.synthetic_catalog_digest != digest(synthetic)
    ):
        raise ValueError("Reviewed benchmark corpus is stale")
    splits = {"original": original.cases}
    for partition, checksum in SPLIT_HASHES.items():
        raw = read(f"furniture_embedding_{partition}_08r1.json")
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError("Frozen benchmark changed")
        body = json.loads(raw)
        if (
            body["partition"] != partition
            or body["original_benchmark_sha256"]
            != hashlib.sha256(original_bytes).hexdigest()
            or body["real_index_identity"]
            != original.real_index_identity.model_dump(mode="json")
            or body["synthetic_catalog_digest"] != digest(synthetic)
        ):
            raise ValueError("Benchmark provenance mismatch")
        splits[partition] = tuple(
            BenchmarkCase.model_validate_json(json.dumps(c)) for c in body["cases"]
        )
    return synthetic, splits


class FixtureSemanticProvider:
    """Isolated artificial benchmark adapter; not a product retrieval interface."""

    def __init__(self, catalog, index, encoder, policy):
        if (
            index.manifest.corpus != catalog.index()
            or index.manifest.encoder != encoder.spec
        ):
            raise ValueError("Fixture index mismatch")
        self.base = SyntheticRetrievalProvider(catalog)
        self.index, self.encoder, self.policy = index, encoder, policy
        self.algorithm = "fixture_cosine_v1_" + digest(policy)[:24]
        self.timings = deque(maxlen=4096)

    def search(self, request):
        start = time.perf_counter_ns()
        timing = dict(authority_ms=0.0, embedding_ms=0.0, ranking_ms=0.0)
        browse = self.base.search(request.model_copy(update={"query": "", "top_k": 50}))
        timing["authority_ms"] = (time.perf_counter_ns() - start) / 1e6
        hits = ()
        status = browse.status
        if self.encoder.spec != self.index.manifest.encoder:
            status = "stale_index"
        elif browse.hits:
            if not request.query:
                ranked = tuple((h.reference.asset_id, 0.0) for h in browse.hits)
            elif self.policy.mode == "abstain_all":
                ranked = ()
            else:
                stage = time.perf_counter_ns()
                query = normalized_vectors(
                    self.encoder.encode_queries((request.query,)), rows=1
                )[0]
                timing["embedding_ms"] = (time.perf_counter_ns() - stage) / 1e6
                stage = time.perf_counter_ns()
                ranked = rank_cosine(
                    self.index,
                    query,
                    {h.reference.asset_id for h in browse.hits},
                    self.policy.minimum_cosine,
                )
                timing["ranking_ms"] = (time.perf_counter_ns() - stage) / 1e6
            refs = {h.reference.asset_id: h.reference for h in browse.hits}
            hits = tuple(
                FurnitureSearchHit(
                    reference=refs[key],
                    scope="synthetic_fixture",
                    qualification="synthetic_fixture",
                    rank=i,
                    score=round((cosine + 1) / 2, 12),
                    reasons=("artificial_fixture_only", "exact_cosine_soft_relevance"),
                    evidence_urls=(),
                )
                for i, (key, cosine) in enumerate(ranked[: request.top_k], 1)
            )
            status = "matches" if hits else "empty"
        timing["total_ms"] = (time.perf_counter_ns() - start) / 1e6
        self.timings.append(timing)
        return FurnitureSearchResult(
            request=request,
            identity=self.index.manifest.corpus.identity,
            algorithm=self.algorithm,
            status=status,
            hits=hits,
            reasons=("isolated_synthetic_semantic_experiment",),
        )


def choose_policy(cases, raw_results, development_digest):
    """Fixed grid, zero negative-query FP, max positive recall, highest threshold."""
    if (
        len(cases) != len(raw_results)
        or not cases
        or not any(c.judgments for c in cases)
        or not any(not c.judgments for c in cases)
    ):
        raise ValueError("Development requires positive and negative queries")
    grid = []
    for step in range(101):
        threshold = step / 100
        fp = 0
        recalls = []
        for case, result in zip(cases, raw_results, strict=True):
            if result.status not in ("matches", "empty"):
                raise ValueError("Development inference unavailable")
            ids = {
                h.reference.asset_id
                for h in result.hits
                if not case.request.query or round(h.score * 2 - 1, 8) >= threshold
            }
            relevant = {j.asset_id for j in case.judgments}
            if relevant:
                recalls.append(len(ids & relevant) / len(relevant))
            else:
                fp += bool(ids)
        grid.append(
            dict(
                threshold=threshold,
                false_positive_queries=fp,
                positive_recall=statistics.mean(recalls),
            )
        )
    feasible = [r for r in grid if r["false_positive_queries"] == 0]
    best = (
        max(feasible, key=lambda r: (r["positive_recall"], r["threshold"]))
        if feasible
        else None
    )
    policy = AbstentionPolicy(
        mode="threshold" if best else "abstain_all",
        minimum_cosine=best["threshold"] if best else None,
        development_digest=development_digest,
        method="zero_dev_fp_max_recall_highest_threshold_v1",
    )
    return policy, grid


def add_error_rates(report, cases):
    negatives = [
        r
        for r, c in zip(report["queries"], cases, strict=True)
        if not c.judgments and c.expected_status != "stale_index"
    ]
    positives = [
        r for r, c in zip(report["queries"], cases, strict=True) if c.judgments
    ]
    fp = sum(bool(r["asset_ids"]) for r in negatives)
    fn = sum(
        not any(
            r["metrics"][k] > 0
            for k in ("recall_at_k", "mrr_at_k")
            if r["metrics"][k] is not None
        )
        for r in positives
    )
    report["summary"].update(
        false_positive_queries=fp,
        false_negative_queries=fn,
        negative_query_false_positive_rate=fp / len(negatives) if negatives else None,
        positive_query_false_negative_rate=fn / len(positives) if positives else None,
    )
    return report


def timing_summary(timings):
    return {
        key: dict(
            samples=len(timings),
            p50=statistics.median(values),
            p95=sorted(values)[math.ceil(0.95 * len(values)) - 1],
        )
        for key in ("authority_ms", "embedding_ms", "ranking_ms", "total_ms")
        if (values := [t[key] for t in timings])
    }
