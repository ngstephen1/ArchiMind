"""RRF uses ranks, source authority, explicit empty union and unavailable gates."""

import pytest
from embedding_helpers import FixedEncoder
from retrieval_helpers import offline  # noqa: F401

from archimind.retrieval import (
    FurnitureSearchFilters,
    FurnitureSearchRequest,
    LexicalRetrievalProvider,
    resolve_result,
)
from archimind.retrieval.eligibility import build_index
from archimind.retrieval.embedding_index import build_embedding_index
from archimind.retrieval.hybrid import HybridRetrievalProvider, reciprocal_rank_fusion
from archimind.retrieval.semantic import AbstentionPolicy, SemanticRetrievalProvider


def rankers():
    corpus = build_index()
    encoder = FixedEncoder()
    semantic = SemanticRetrievalProvider(
        index=build_embedding_index(corpus, encoder),
        encoder=encoder,
        policy=AbstentionPolicy(
            mode="threshold", minimum_cosine=-1.0, method="test_double"
        ),
    )
    return corpus, LexicalRetrievalProvider(index=corpus), semantic


def test_rrf_exact_arithmetic_stable_ties_no_score_addition():
    actual = reciprocal_rank_fusion((("b", "a"), ("a", "c")))
    assert [r[0] for r in actual] == ["a", "b", "c"]
    assert actual[0][1] == 1 / 62 + 1 / 61
    assert actual[0][2] == ("ranker_1_rank_2", "ranker_2_rank_1")
    assert reciprocal_rank_fusion((("b",), ("a",)))[0][0] == "a"
    with pytest.raises(ValueError):
        reciprocal_rank_fusion((("a", "a"),))
    with pytest.raises(ValueError):
        reciprocal_rank_fusion((("a",),), k=0)


def test_real_hybrid_preserves_refs_and_uses_explicit_union():
    corpus, lexical, semantic = rankers()
    provider = HybridRetrievalProvider(lexical, semantic, corpus=corpus)
    request = FurnitureSearchRequest(query="Charles armchair")
    result = provider.search(request)
    assert len(result.hits) == 2 and len(resolve_result(result)) == 2
    assert result.hits[0].reference.asset_id == "abo-b075x2x4xs-amazon-com"
    assert result.hits[0].score == 2 / 61
    assert "ranker_2_rank_2" in result.hits[1].reasons
    assert provider.search(request) == result
    assert type(result).model_validate_json(result.model_dump_json()) == result
    # Changing raw component score magnitudes cannot affect RRF.
    original = lexical.search
    lexical.search = lambda r: original(r).model_copy(
        update={
            "hits": tuple(
                h.model_copy(update={"score": 12345.0}) for h in original(r).hits
            )
        }
    )
    assert provider.search(request) == result


@pytest.mark.parametrize(
    "filters,qual",
    [
        (dict(category="bed"), "metadata"),
        (dict(category="storage"), "render"),
        (dict(materials=("leather",)), "metadata"),
        (dict(variant="Crimson"), "metadata"),
        (dict(max_width_m=0.2), "metadata"),
    ],
)
def test_hybrid_hard_filters_never_gain_substitutes(filters, qual):
    corpus, lexical, semantic = rankers()
    request = FurnitureSearchRequest(
        query="chair",
        filters=FurnitureSearchFilters(**filters),
        required_qualification=qual,
    )
    result = HybridRetrievalProvider(lexical, semantic, corpus=corpus).search(request)
    assert result.status == "empty" and not result.hits
    assert not semantic.encoder.query_inputs


@pytest.mark.parametrize("status", ["unavailable", "stale_index"])
def test_no_silent_component_fallback(status):
    corpus, lexical, semantic = rankers()
    original = semantic.search
    semantic.search = lambda r: original(r).model_copy(
        update={"status": status, "hits": ()}
    )
    result = HybridRetrievalProvider(lexical, semantic, corpus=corpus).search(
        FurnitureSearchRequest(query="Charles")
    )
    assert result.status == status and not result.hits


def test_forged_eligible_reference_is_rejected():
    corpus, lexical, semantic = rankers()
    original = semantic.search

    def forged(request):
        result = original(request)
        return result.model_copy(
            update={
                "hits": tuple(
                    h.model_copy(
                        update={
                            "reference": h.reference.model_copy(
                                update={"record_digest": "f" * 64}
                            )
                        }
                    )
                    for h in result.hits
                )
            }
        )

    semantic.search = forged
    assert (
        HybridRetrievalProvider(lexical, semantic, corpus=corpus)
        .search(FurnitureSearchRequest(query="chair"))
        .status
        == "unavailable"
    )


def test_synthetic_requires_explicit_isolated_gate():
    from pathlib import Path

    from archimind.retrieval.embedding_experiment import (
        FixtureSemanticProvider,
        benchmark_inputs,
    )
    from archimind.retrieval.evaluation import SyntheticRetrievalProvider

    catalog, _ = benchmark_inputs(
        Path(__file__).resolve().parents[1] / "data/benchmarks"
    )
    corpus = catalog.index()
    lexical = SyntheticRetrievalProvider(catalog)
    encoder = FixedEncoder()
    semantic = FixtureSemanticProvider(
        catalog,
        build_embedding_index(corpus, encoder),
        encoder,
        AbstentionPolicy(mode="threshold", minimum_cosine=-1.0, method="test_double"),
    )
    with pytest.raises(ValueError):
        HybridRetrievalProvider(lexical, semantic, corpus=corpus)
    provider = HybridRetrievalProvider(
        lexical, semantic, corpus=corpus, fixture_catalog=catalog
    )
    result = provider.search(
        FurnitureSearchRequest(catalog_id="synthetic:08r0", query="reading chair")
    )
    assert result.hits and all(h.scope == "synthetic_fixture" for h in result.hits)
    with pytest.raises(ValueError):
        resolve_result(result)


def test_stale_authority_after_ranker_call_rejected(monkeypatch):
    import archimind.retrieval.hybrid as module

    corpus, lexical, semantic = rankers()
    monkeypatch.setattr(
        module, "build_index", lambda: corpus.model_copy(update={"documents": ()})
    )
    assert (
        HybridRetrievalProvider(lexical, semantic, corpus=corpus)
        .search(FurnitureSearchRequest(query="Charles"))
        .status
        == "stale_index"
    )


def test_known_product_that_fails_filters_cannot_be_injected():
    corpus, lexical, semantic = rankers()
    original = semantic.search
    broad = original(FurnitureSearchRequest(query="anything", top_k=50))
    bookcase = next(
        h for h in broad.hits if h.reference.asset_id.endswith("b07pqs58xn-amazon-com")
    )

    def injected(request):
        valid = original(request)
        return valid.model_copy(
            update={"hits": (bookcase.model_copy(update={"rank": 1}),)}
        )

    semantic.search = injected
    request = FurnitureSearchRequest(
        query="chair", filters=FurnitureSearchFilters(category="chair")
    )
    result = HybridRetrievalProvider(lexical, semantic, corpus=corpus).search(request)
    assert result.status == "unavailable" and not result.hits


def test_final_resolution_failure_and_private_exception_are_sanitized(monkeypatch):
    import archimind.retrieval.hybrid as module

    corpus, lexical, semantic = rankers()
    original = module.resolve_result
    calls = []

    def changed(result, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            raise ValueError("secret-evidence-change")
        return original(result, **kwargs)

    monkeypatch.setattr(module, "resolve_result", changed)
    result = HybridRetrievalProvider(lexical, semantic, corpus=corpus).search(
        FurnitureSearchRequest(query="Charles")
    )
    assert result.status == "unavailable" and "secret" not in result.model_dump_json()

    def failure(request):
        raise RuntimeError("sk-private-key")

    semantic.search = failure
    result = HybridRetrievalProvider(lexical, semantic, corpus=corpus).search(
        FurnitureSearchRequest(query="Charles")
    )
    assert (
        result.status == "unavailable" and "sk-private" not in result.model_dump_json()
    )
