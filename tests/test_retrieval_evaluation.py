"""Auditable gold sets and independently checkable retrieval metric arithmetic."""

import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from retrieval_helpers import offline  # noqa: F401

from archimind.assets.specifications import prepare_catalog_specification
from archimind.examples import create_sample_bedroom
from archimind.retrieval import (
    FurnitureSearchFilters,
    FurnitureSearchRequest,
    FurnitureSearchResult,
    resolve_result,
)
from archimind.retrieval import eligibility as authority
from archimind.retrieval import evaluation as api
from archimind.retrieval.lexical import LexicalRetrievalProvider

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def inputs():
    root = ROOT / "data" / "benchmarks"
    return (
        api.RetrievalBenchmark.model_validate_json(
            (root / "furniture_retrieval_queries.json").read_bytes()
        ),
        api.SyntheticCatalog.model_validate_json(
            (root / "furniture_retrieval_synthetic.json").read_bytes()
        ),
    )


def test_known_metric_arithmetic_and_denominators():
    metrics = api.ranking_metrics(("b", "a"), {"a": 3, "b": 1, "c": 2}, 2)
    assert metrics["precision_at_k"] == 1
    assert metrics["recall_at_k"] == pytest.approx(2 / 3)
    assert metrics["mrr_at_k"] == 1
    assert metrics["ndcg_at_k"] == pytest.approx(
        (1 + 7 / math.log2(3)) / (7 + 3 / math.log2(3))
    )
    missing = api.ranking_metrics(("wrong", "a"), {"a": 1}, 2, complete=False)
    assert (
        missing["precision_at_k"] == 0.5
        and missing["recall_at_k"] is None
        and missing["mrr_at_k"] == 0.5
    )
    assert missing["ndcg_at_k"] == pytest.approx(1 / math.log2(3))
    empty = api.ranking_metrics((), {}, 3)
    assert (
        empty["precision_at_k"] == 0
        and empty["ndcg_at_k"] is None
        and empty["recall_at_k"] is None
    )
    assert api.ranking_metrics(("a",), {"a": 3}, 3)["precision_at_k"] == pytest.approx(
        1 / 3
    )


@pytest.mark.parametrize(
    "returned,judgments,k",
    [
        (("a", "a"), {"a": 1}, 2),
        ((), {}, 0),
        ((), {}, True),
        (("a",), {"a": 0}, 1),
        (("a",), {"a": 4}, 1),
    ],
)
def test_invalid_metric_inputs(returned, judgments, k):
    with pytest.raises(ValueError):
        api.ranking_metrics(returned, judgments, k)


def test_gold_is_explicit_complete_and_separated(inputs):
    benchmark, synthetic = inputs
    assert len(benchmark.cases) == 62 and len(synthetic.products) == 8
    assert len([c for c in benchmark.cases if c.scope == "real"]) == 38
    assert len([c for c in benchmark.cases if c.scope == "synthetic_fixture"]) == 24
    assert all(
        p.asset_id.startswith("synthetic:") and p.qualification == "synthetic_fixture"
        for p in synthetic.products
    )
    assert all(c.judgment_note and c.relevant_set_complete for c in benchmark.cases)
    assert (
        api.RetrievalBenchmark.model_validate_json(benchmark.model_dump_json())
        == benchmark
    )
    raw = synthetic.model_dump(mode="json")
    raw["products"][0]["qualification"] = "render"
    with pytest.raises(ValueError):
        api.SyntheticCatalog.model_validate_json(json.dumps(raw))
    raw = synthetic.model_dump(mode="json")
    raw["products"][0]["asset_id"] = "abo-real-looking"
    with pytest.raises(ValueError):
        api.SyntheticCatalog.model_validate_json(json.dumps(raw))


def test_fixture_hits_cannot_resolve_or_enter_preparation(inputs):
    _, synthetic = inputs
    result = api.SyntheticRetrievalProvider(synthetic).search(
        FurnitureSearchRequest(query="", catalog_id="synthetic:08r0")
    )
    assert result.hits and result.identity.scope == "synthetic_fixture"
    assert all(
        h.qualification == "synthetic_fixture" and not h.evidence_urls
        for h in result.hits
    )
    with pytest.raises(authority.RetrievalError):
        resolve_result(result)
    with pytest.raises(ValueError):
        prepare_catalog_specification(
            create_sample_bedroom(),
            retained_manual_ids=(),
            product_ids=tuple(h.reference.asset_id for h in result.hits),
        )
    rejected = api.SyntheticRetrievalProvider(synthetic).search(
        FurnitureSearchRequest(
            query="", catalog_id="synthetic:08r0", required_qualification="render"
        )
    )
    assert rejected.status == "empty" and not rejected.hits


def test_fixture_ranking_and_dimensions_do_not_use_real_catalog(inputs):
    _, synthetic = inputs
    provider = api.SyntheticRetrievalProvider(synthetic)
    result = provider.search(
        FurnitureSearchRequest(
            query="ＯＡＫ desk",
            catalog_id="synthetic:08r0",
            filters=FurnitureSearchFilters(max_width_m=1.0),
        )
    )
    assert [h.reference.asset_id for h in result.hits] == ["synthetic:desk-oak-small"]
    before = synthetic.model_dump_json()
    assert provider.search(result.request) == result
    assert synthetic.model_dump_json() == before


def test_benchmark_run_actual_counts_safety_and_determinism(inputs):
    benchmark, synthetic = inputs
    first = api.run_benchmark(benchmark, synthetic, repeats=2, historical=True)
    second = api.run_benchmark(benchmark, synthetic, repeats=2, historical=True)
    assert first["semantic_output_digest"] == second["semantic_output_digest"]
    for key, report in first["reports"].items():
        if not report["available"]:
            continue
        s = report["summary"]
        assert (
            s["hard_constraint_violation_rate"]
            == s["unauthorized_asset_leakage_rate"]
            == 0
        )
        assert (
            s["determinism"]
            == s["version_handling_correctness"]
            == s["category_correctness"]
            == 1
        )
        assert (
            s["latency_ms"]["samples"] == s["cases"] * 2 and s["latency_ms"]["p50"] > 0
        )
        if key.startswith("real/"):
            assert (
                s["cases"] == 38
                and s["positive_queries"] == 20
                and s["negative_queries"] == 17
                and s["version_queries"] == 1
            )
            assert s["macro_positive_query_metrics"]["recall_at_k"] == 0.9
            assert s["failures"] == ["real:r18", "real:r19"]
        else:
            assert s["cases"] == 24 and s["failures"] == ["synthetic:s20"]


def test_independent_eligibility_gold_catches_wrong_category(inputs):
    benchmark, _ = inputs
    case = next(c for c in benchmark.cases if c.case_id == "real:r05")
    provider = LexicalRetrievalProvider()
    book = provider.search(FurnitureSearchRequest(query="bookcase")).hits[0]
    bad = FurnitureSearchResult(
        request=case.request,
        identity=provider.index.identity,
        algorithm="fake_v1",
        status="matches",
        hits=(book,),
        reasons=("test_only",),
    )
    fake = SimpleNamespace(search=lambda request: bad)
    report = api.evaluate_provider(
        fake,
        (case,),
        identity=provider.index.identity,
        references={
            d.reference.asset_id: d.reference for d in provider.index.documents
        },
        categories={
            o.record.asset_id: o.record.category for o in authority.current_options()
        },
        repeats=2,
    )
    assert report["summary"]["hard_constraint_violation_rate"] == 1
    assert report["summary"]["category_correctness"] == 0
    assert report["summary"]["unauthorized_asset_leakage_rate"] == 0


def test_stale_benchmark_and_mixed_gold_are_rejected(inputs):
    benchmark, synthetic = inputs
    bad = benchmark.model_copy(update={"synthetic_catalog_digest": "0" * 64})
    with pytest.raises(ValueError, match="stale"):
        api.run_benchmark(bad, synthetic)
    raw = benchmark.model_dump(mode="json")
    raw["cases"][0]["eligible_ids"] = ["synthetic:fake"]
    with pytest.raises(ValueError):
        api.RetrievalBenchmark.model_validate_json(json.dumps(raw))


def test_missing_optional_fts_does_not_hide_python_results(inputs, monkeypatch):
    benchmark, synthetic = inputs
    monkeypatch.setattr(api, "fts5_available", lambda: False)
    result = api.run_benchmark(benchmark, synthetic, repeats=2, historical=True)
    assert result["reports"]["real/python_bm25_v1"]["available"]
    assert not result["reports"]["real/sqlite_fts5_bm25_v1"]["available"]
