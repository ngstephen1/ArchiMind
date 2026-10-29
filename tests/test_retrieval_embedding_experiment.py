"""Frozen splits and declared calibration mechanics with fixed artificial vectors."""

from pathlib import Path

import pytest
from embedding_helpers import FixedEncoder
from retrieval_helpers import offline  # noqa: F401

from archimind.retrieval.contracts import FurnitureSearchRequest
from archimind.retrieval.embedding_experiment import (
    FixtureSemanticProvider,
    benchmark_inputs,
    choose_policy,
)
from archimind.retrieval.embedding_index import build_embedding_index
from archimind.retrieval.semantic import AbstentionPolicy


def inputs():
    return benchmark_inputs(Path(__file__).resolve().parents[1] / "data/benchmarks")


def test_frozen_split_counts_and_distinct_case_ids():
    _, splits = inputs()
    assert {k: len(v) for k, v in splits.items()} == {
        "original": 62,
        "development": 24,
        "held_out": 28,
    }
    ids = [c.case_id for group in splits.values() for c in group]
    assert len(ids) == len(set(ids))


def test_fixture_provider_is_isolated_and_structured_empty_query_never_encodes():
    catalog, _ = inputs()
    encoder = FixedEncoder()
    index = build_embedding_index(catalog.index(), encoder)
    provider = FixtureSemanticProvider(
        catalog,
        index,
        encoder,
        AbstentionPolicy(mode="abstain_all", method="unconfigured"),
    )
    result = provider.search(
        FurnitureSearchRequest(catalog_id="synthetic:08r0", query="", top_k=50)
    )
    assert len(result.hits) == 8 and not encoder.query_inputs
    assert all(h.scope == "synthetic_fixture" for h in result.hits)
    assert (
        provider.search(FurnitureSearchRequest(query="chair")).status == "stale_index"
    )
    from archimind.retrieval import resolve_result

    with pytest.raises(ValueError):
        resolve_result(result)


def test_declared_threshold_grid_uses_development_only():
    catalog, splits = inputs()
    cases = tuple(c for c in splits["development"] if c.scope == "synthetic_fixture")
    encoder = FixedEncoder()
    provider = FixtureSemanticProvider(
        catalog,
        build_embedding_index(catalog.index(), encoder),
        encoder,
        AbstentionPolicy(mode="threshold", minimum_cosine=-1.0, method="raw_reference"),
    )
    results = [provider.search(c.request) for c in cases]
    policy, grid = choose_policy(cases, results, "a" * 64)
    assert len(grid) == 101 and grid[0]["threshold"] == 0 and grid[-1]["threshold"] == 1
    feasible = [g for g in grid if g["false_positive_queries"] == 0]
    if feasible:
        best = max(feasible, key=lambda r: (r["positive_recall"], r["threshold"]))
        assert policy.minimum_cosine == best["threshold"]
    else:
        assert policy.mode == "abstain_all"
    with pytest.raises(ValueError):
        choose_policy(cases, [], "a" * 64)


def test_calibration_exact_boundary_and_all_abstain_fallback():
    from types import SimpleNamespace

    positive = SimpleNamespace(
        judgments=(SimpleNamespace(asset_id="p"),),
        request=SimpleNamespace(query="seat"),
    )
    negative = SimpleNamespace(
        judgments=(), request=SimpleNamespace(query="unavailable")
    )

    def result(score):
        return SimpleNamespace(
            status="matches",
            hits=(
                SimpleNamespace(reference=SimpleNamespace(asset_id="p"), score=score),
            ),
        )

    policy, _ = choose_policy(
        (positive, negative), (result(0.9), result(0.8)), "a" * 64
    )
    assert policy.minimum_cosine == 0.8  # .6 < threshold <= .8; highest wins.
    policy, _ = choose_policy(
        (positive, negative), (result(0.9), result(1.0)), "a" * 64
    )
    assert policy.mode == "abstain_all" and policy.minimum_cosine is None
