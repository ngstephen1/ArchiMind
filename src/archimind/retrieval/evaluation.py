"""Offline, explicitly separated real and artificial retrieval evaluation."""

import hashlib
import math
import platform
import statistics
import time
from typing import Literal

from pydantic import Field, StrictBool, StrictInt, model_validator

from archimind.retrieval.contracts import (
    CatalogReference,
    Frozen,
    FurnitureSearchHit,
    FurnitureSearchRequest,
    FurnitureSearchResult,
    IndexIdentity,
    Scope,
)
from archimind.retrieval.eligibility import (
    IndexedDocument,
    RetrievalIndex,
    build_index,
    digest,
    normalized,
    resolve_hit,
)
from archimind.retrieval.lexical import (
    FTS5Unavailable,
    LexicalRetrievalProvider,
    fts5_available,
    rank_documents,
    sqlite3,
)


class SyntheticProduct(Frozen):
    asset_id: str = Field(pattern=r"^synthetic:[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(pattern=r"^[a-z]+$")
    variant: str
    width_m: float = Field(gt=0, allow_inf_nan=False)
    depth_m: float = Field(gt=0, allow_inf_nan=False)
    height_m: float = Field(gt=0, allow_inf_nan=False)
    uses: tuple[str, ...]
    materials: tuple[str, ...]
    styles: tuple[str, ...]
    colors: tuple[str, ...]
    qualification: Literal["synthetic_fixture"]

    def text(self):
        return " ".join(
            (
                self.name,
                self.category,
                self.variant,
                *self.uses,
                *self.materials,
                *self.styles,
                *self.colors,
            )
        )


class SyntheticCatalog(Frozen):
    schema_version: StrictInt = Field(ge=1, le=1)
    catalog_id: Literal["synthetic:08r0"]
    catalog_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    scope: Literal["synthetic_fixture"]
    notice: str
    products: tuple[SyntheticProduct, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_artificial_ids(self):
        ids = [p.asset_id for p in self.products]
        if ids != sorted(set(ids)):
            raise ValueError("Duplicate or unordered fixture IDs")
        return self

    def index(self):
        docs = tuple(
            IndexedDocument(
                reference=CatalogReference(
                    catalog_id=self.catalog_id,
                    catalog_version=self.catalog_version,
                    asset_id=p.asset_id,
                    asset_version="1.0.0",
                    product_id=p.asset_id,
                    record_digest=digest(p),
                    search_document_version=1,
                    search_document_digest=hashlib.sha256(
                        p.text().encode()
                    ).hexdigest(),
                ),
                text=p.text(),
            )
            for p in self.products
        )
        fields = dict(
            scope="synthetic_fixture",
            catalog_id=self.catalog_id,
            catalog_version=self.catalog_version,
            catalog_digest=digest([d.model_dump(mode="json") for d in docs]),
            evidence_digest=digest(self),
            search_document_version=1,
            index_format_version=1,
        )
        return RetrievalIndex(
            identity=IndexIdentity(**fields, snapshot_id=digest(fields)), documents=docs
        )


class SyntheticRetrievalProvider:
    """Benchmark-only mechanics. IDs cannot resolve in the authoritative catalog."""

    def __init__(self, catalog: SyntheticCatalog, *, algorithm="python_bm25_v1"):
        self.catalog = SyntheticCatalog.model_validate(catalog)
        self.index = self.catalog.index()
        self.algorithm = algorithm

    def search(self, request: FurnitureSearchRequest):
        request = FurnitureSearchRequest.model_validate(request)

        def result(status, hits=(), reason="fixture_only"):
            return FurnitureSearchResult(
                request=request,
                identity=self.index.identity,
                algorithm=self.algorithm,
                status=status,
                hits=hits,
                reasons=(reason,),
            )

        if (
            request.catalog_id != self.catalog.catalog_id
            or request.catalog_version not in (None, self.catalog.catalog_version)
        ):
            return result("stale_index", reason="fixture_version_mismatch")
        if request.required_qualification != "metadata":
            return result("empty", reason="fixtures_never_planning_or_render_qualified")
        f = request.filters
        eligible = []
        for p in self.catalog.products:
            exact = (
                (f.asset_id, p.asset_id),
                (f.product_id, p.asset_id),
                (f.category, p.category),
                (f.variant, p.variant),
            )
            if any(
                want is not None and normalized(want) != normalized(actual)
                for want, actual in exact
            ):
                continue
            if f.required_use is not None and normalized(f.required_use) not in {
                normalized(v) for v in p.uses
            }:
                continue
            if any(
                not {normalized(v) for v in getattr(f, a)}
                <= {normalized(v) for v in getattr(p, a)}
                for a in ("materials", "styles", "colors")
            ):
                continue
            if any(
                getattr(f, "max_" + axis + "_m") is not None
                and getattr(p, axis + "_m") > getattr(f, "max_" + axis + "_m")
                for axis in ("width", "depth", "height")
            ):
                continue
            eligible.append(p.asset_id)
        docs = tuple(
            d for d in self.index.documents if d.reference.asset_id in eligible
        )
        try:
            ranked = rank_documents(docs, request.query, self.algorithm)
        except FTS5Unavailable:
            return result("unavailable", reason="fts5_unavailable")
        refs = {d.reference.asset_id: d.reference for d in docs}
        hits = tuple(
            FurnitureSearchHit(
                reference=refs[key],
                scope="synthetic_fixture",
                qualification="synthetic_fixture",
                rank=i,
                score=score,
                reasons=("artificial_fixture_only", "structured_filters_passed"),
                evidence_urls=(),
            )
            for i, (key, score) in enumerate(ranked[: request.top_k], 1)
        )
        return result("matches" if hits else "empty", hits)


class Judgment(Frozen):
    asset_id: str
    grade: StrictInt = Field(ge=1, le=3)


class BenchmarkCase(Frozen):
    case_id: str
    scope: Scope
    request: FurnitureSearchRequest
    judgments: tuple[Judgment, ...]
    eligible_ids: tuple[str, ...]
    relevant_set_complete: StrictBool
    expected_status: Literal["matches", "empty", "stale_index"]
    judgment_note: str

    @model_validator(mode="after")
    def consistent_gold(self):
        ids = [j.asset_id for j in self.judgments]
        synthetic = self.scope == "synthetic_fixture"
        if (
            ids != sorted(set(ids))
            or list(self.eligible_ids) != sorted(set(self.eligible_ids))
            or not set(ids) <= set(self.eligible_ids)
        ):
            raise ValueError("Inconsistent gold judgments")
        if self.request.catalog_id.startswith("synthetic:") != synthetic or any(
            i.startswith("synthetic:") != synthetic for i in (*ids, *self.eligible_ids)
        ):
            raise ValueError("Mixed fixture and real gold")
        if bool(ids) != (self.expected_status == "matches"):
            raise ValueError("Gold status and judgments disagree")
        return self


class RetrievalBenchmark(Frozen):
    schema_version: StrictInt = Field(ge=1, le=1)
    benchmark_version: str
    real_index_identity: IndexIdentity
    synthetic_catalog_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    judgment_policy: str
    cases: tuple[BenchmarkCase, ...] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_cases(self):
        ids = [c.case_id for c in self.cases]
        if ids != sorted(set(ids)) or self.real_index_identity.scope != "real":
            raise ValueError("Invalid benchmark identities")
        return self


def ranking_metrics(
    returned: tuple[str, ...], judgments: dict[str, int], k: int, *, complete=True
):
    """Fixed-k precision; recall only for complete gold; MRR and exponential NDCG."""
    if (
        type(k) is not int
        or k < 1
        or len(returned) != len(set(returned))
        or any(type(g) is not int or not 1 <= g <= 3 for g in judgments.values())
    ):
        raise ValueError("Invalid ranking metric input")
    ranked = returned[:k]
    relevant = sum(key in judgments for key in ranked)
    first = next((i for i, key in enumerate(ranked, 1) if key in judgments), None)
    dcg = sum(
        (2 ** judgments.get(key, 0) - 1) / math.log2(i + 1)
        for i, key in enumerate(ranked, 1)
    )
    ideal = sum(
        (2**g - 1) / math.log2(i + 1)
        for i, g in enumerate(sorted(judgments.values(), reverse=True)[:k], 1)
    )
    return dict(
        precision_at_k=relevant / k,
        recall_at_k=relevant / len(judgments) if judgments and complete else None,
        mrr_at_k=1 / first if first else 0.0 if judgments else None,
        ndcg_at_k=dcg / ideal if ideal else None,
    )


def evaluate_provider(provider, cases, *, identity, references, categories, repeats=3):
    if type(repeats) is not int or not 2 <= repeats <= 20:
        raise ValueError("Use 2..20 determinism repetitions")
    records = []
    latencies = []
    for case in cases:
        outcomes = []
        timings = []
        for _ in range(repeats):
            start = time.perf_counter_ns()
            result = FurnitureSearchResult.model_validate(provider.search(case.request))
            timings.append((time.perf_counter_ns() - start) / 1e6)
            outcomes.append(result)
        result = outcomes[0]
        latencies.extend(timings)
        ids = tuple(h.reference.asset_id for h in result.hits)
        metrics = ranking_metrics(
            ids,
            {j.asset_id: j.grade for j in case.judgments},
            case.request.top_k,
            complete=case.relevant_set_complete,
        )
        unauthorized = 0
        for hit in result.hits:
            bad = (
                hit.scope != identity.scope
                or result.identity != identity
                or references.get(hit.reference.asset_id) != hit.reference
            )
            if not bad and hit.scope == "real":
                try:
                    resolve_hit(hit, result.identity)
                except ValueError:
                    bad = True
            unauthorized += int(bad)
        category_hits = [
            key for key in ids if case.request.filters.category is not None
        ]
        records.append(
            dict(
                case_id=case.case_id,
                scope=case.scope,
                expected_status=case.expected_status,
                status=result.status,
                asset_ids=ids,
                scores=tuple(h.score for h in result.hits),
                result_reasons=result.reasons,
                semantic_digest=digest(result),
                metrics=metrics,
                returned_hits=len(ids),
                category_hits=len(category_hits),
                correct_category_hits=sum(
                    categories.get(key) == case.request.filters.category
                    for key in category_hits
                ),
                hard_constraint_violations=sum(
                    key not in case.eligible_ids for key in ids
                ),
                unauthorized_assets=unauthorized,
                empty_correct=(
                    bool(ids) == bool(case.judgments)
                    and result.status in ("matches", "empty")
                )
                if case.expected_status != "stale_index"
                else None,
                version_correct=result.status == "stale_index"
                if case.expected_status == "stale_index"
                else None,
                deterministic=all(o == result for o in outcomes),
                latency_ms=timings,
            )
        )
    positives = [r for r, c in zip(records, cases, strict=True) if c.judgments]
    valid = [r for r in records if r["empty_correct"] is not None]
    versions = [r for r in records if r["version_correct"] is not None]
    hits = sum(r["returned_hits"] for r in records)
    cats = sum(r["category_hits"] for r in records)
    ordered = sorted(latencies)

    def ratio(num, denom):
        return num / denom if denom else None

    macro = {
        key: statistics.mean(values)
        if (
            values := [
                r["metrics"][key] for r in positives if r["metrics"][key] is not None
            ]
        )
        else None
        for key in ("precision_at_k", "recall_at_k", "mrr_at_k", "ndcg_at_k")
    }
    summary = dict(
        cases=len(records),
        positive_queries=len(positives),
        negative_queries=sum(
            not c.judgments and c.expected_status != "stale_index" for c in cases
        ),
        version_queries=len(versions),
        macro_positive_query_metrics=macro,
        returned_hits=hits,
        category_checked_hits=cats,
        category_correctness=ratio(
            sum(r["correct_category_hits"] for r in records), cats
        ),
        hard_constraint_violation_rate=ratio(
            sum(r["hard_constraint_violations"] for r in records), hits
        ),
        unauthorized_asset_leakage_rate=ratio(
            sum(r["unauthorized_assets"] for r in records), hits
        ),
        empty_result_correctness=ratio(
            sum(r["empty_correct"] for r in valid), len(valid)
        ),
        version_handling_correctness=ratio(
            sum(r["version_correct"] for r in versions), len(versions)
        ),
        determinism=sum(r["deterministic"] for r in records) / len(records),
        unavailable_queries=sum(r["status"] == "unavailable" for r in records),
        latency_ms=dict(
            samples=len(latencies),
            p50=statistics.median(latencies),
            p95=ordered[math.ceil(0.95 * len(ordered)) - 1],
            max=max(latencies),
        ),
        ranking_shortfalls=[
            r["case_id"] for r in positives if r["metrics"]["ndcg_at_k"] < 1.0
        ],
        failures=[
            r["case_id"]
            for r in records
            if r["empty_correct"] is False
            or r["version_correct"] is False
            or r["hard_constraint_violations"]
            or r["unauthorized_assets"]
            or not r["deterministic"]
        ],
    )
    return dict(summary=summary, queries=records)


def run_benchmark(
    benchmark: RetrievalBenchmark, synthetic: SyntheticCatalog, *, repeats=3
):
    benchmark = RetrievalBenchmark.model_validate(benchmark)
    synthetic = SyntheticCatalog.model_validate(synthetic)
    real_index = build_index()
    if (
        benchmark.real_index_identity != real_index.identity
        or benchmark.synthetic_catalog_digest != digest(synthetic)
    ):
        raise ValueError(
            "Benchmark source snapshot is stale; review judgments before updating"
        )
    available_fts = fts5_available()
    reports = {}
    for scope in ("real", "synthetic_fixture"):
        cases = tuple(c for c in benchmark.cases if c.scope == scope)
        index = real_index if scope == "real" else synthetic.index()
        refs = {d.reference.asset_id: d.reference for d in index.documents}
        from archimind.retrieval.eligibility import current_options

        categories = (
            {o.record.asset_id: o.record.category for o in current_options()}
            if scope == "real"
            else {p.asset_id: p.category for p in synthetic.products}
        )
        if any(
            not set((*c.eligible_ids, *(j.asset_id for j in c.judgments)))
            <= refs.keys()
            for c in cases
        ):
            raise ValueError("Benchmark has unknown product judgments")
        for algorithm in ("python_bm25_v1", "sqlite_fts5_bm25_v1"):
            key = scope + "/" + algorithm
            if algorithm == "sqlite_fts5_bm25_v1" and not available_fts:
                reports[key] = {
                    "available": False,
                    "reason": "SQLite runtime lacks FTS5; Python baseline remains functional",
                }
                continue
            provider = (
                LexicalRetrievalProvider(index=index, algorithm=algorithm)
                if scope == "real"
                else SyntheticRetrievalProvider(synthetic, algorithm=algorithm)
            )
            reports[key] = {
                "available": True,
                "identity": index.identity.model_dump(mode="json"),
                **evaluate_provider(
                    provider,
                    cases,
                    identity=index.identity,
                    references=refs,
                    categories=categories,
                    repeats=repeats,
                ),
            }
    deterministic = {
        key: (
            {k: v for k, v in report.items() if k not in ("queries", "summary")}
            | {
                "queries": [
                    {k: v for k, v in q.items() if k != "latency_ms"}
                    for q in report.get("queries", [])
                ]
            }
        )
        for key, report in reports.items()
    }
    return dict(
        task="08R0",
        benchmark_version=benchmark.benchmark_version,
        benchmark_digest=digest(benchmark),
        synthetic_fixture_digest=digest(synthetic),
        semantic_output_digest=digest(deterministic),
        environment=dict(
            python=platform.python_version(),
            system=platform.system(),
            machine=platform.machine(),
            sqlite=sqlite3.sqlite_version if sqlite3 is not None else None,
            fts5=available_fts,
        ),
        repeats=repeats,
        latency_scope="Sequential local CPU end-to-end search plus result schema validation; real searches include fresh metadata/evidence checks; FTS5 rebuilds an in-memory table per query. Not model or production latency.",
        reports=reports,
    )
