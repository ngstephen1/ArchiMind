"""Exact fixed-vector rankings preserve hard source eligibility and contract safety."""

import numpy as np
import pytest
from embedding_helpers import FixedEncoder
from retrieval_helpers import offline  # noqa: F401

from archimind.retrieval import (
    FurnitureSearchFilters,
    FurnitureSearchRequest,
    resolve_result,
)
from archimind.retrieval.eligibility import build_index
from archimind.retrieval.embedding_index import EmbeddingError, build_embedding_index
from archimind.retrieval.semantic import (
    AbstentionPolicy,
    SemanticRetrievalProvider,
    rank_cosine,
)


def provider(query=None, threshold=-1):
    encoder = FixedEncoder(query=query)
    index = build_embedding_index(build_index(), encoder)
    return SemanticRetrievalProvider(
        index=index,
        encoder=encoder,
        policy=AbstentionPolicy(
            mode="threshold", minimum_cosine=threshold, method="test_double"
        ),
    )


def test_exact_cosine_ties_contract_and_input_preservation():
    query = np.zeros(384, dtype=np.float32)
    query[:2] = 1
    p = provider(query)
    request = FurnitureSearchRequest(query="seating")
    before = p.index.vector_bytes
    first = p.search(request)
    assert (
        len(first.hits) == 2
        and first.hits[0].reference.asset_id < first.hits[1].reference.asset_id
    )
    assert first.hits[0].score == first.hits[1].score
    assert p.search(request) == first and p.index.vector_bytes == before
    assert len(resolve_result(first)) == 2
    assert type(first).model_validate_json(first.model_dump_json()) == first


@pytest.mark.parametrize(
    "filters,qual,count",
    [
        (dict(category="bed"), "metadata", 0),
        (dict(category="chair"), "metadata", 1),
        (dict(category="storage"), "render", 0),
        (dict(max_width_m=0.5), "metadata", 0),
        (dict(variant="Crimson"), "metadata", 0),
        (dict(materials=("leather",)), "metadata", 0),
        (dict(styles=("modern",)), "metadata", 0),
        (dict(asset_id="unknown"), "metadata", 0),
        (dict(required_use="wardrobe"), "metadata", 0),
    ],
)
def test_hard_filters_before_embedding(filters, qual, count):
    p = provider()
    result = p.search(
        FurnitureSearchRequest(
            query="anything",
            filters=FurnitureSearchFilters(**filters),
            required_qualification=qual,
        )
    )
    assert len(result.hits) == count
    assert bool(p.encoder.query_inputs) == bool(count)
    assert len(resolve_result(result)) == count


def test_threshold_abstains_without_fabricating_fallback():
    q = np.zeros(384, dtype=np.float32)
    q[2] = 1
    p = provider(q, 0.1)
    assert not p.search(FurnitureSearchRequest(query="no relevant item")).hits
    p.policy = AbstentionPolicy(mode="abstain_all", method="unconfigured")
    p.encoder.query_inputs = []
    assert (
        not p.search(FurnitureSearchRequest(query="seat")).hits
        and not p.encoder.query_inputs
    )


def test_stale_model_index_and_bad_vectors_fail_safely():
    p = provider()
    p.encoder.spec = p.encoder.spec.model_copy(update={"onnxruntime_version": "0.0.0"})
    assert p.search(FurnitureSearchRequest(query="chair")).status == "stale_index"
    p = provider()
    p.encoder.query = np.full(384, np.nan)
    assert p.search(FurnitureSearchRequest(query="chair")).status == "unavailable"
    assert (
        p.search(FurnitureSearchRequest(query="chair", catalog_version="0.9.0")).status
        == "stale_index"
    )


def test_unknown_candidate_cannot_enter_vector_ranker():
    p = provider()
    with pytest.raises(EmbeddingError):
        rank_cosine(p.index, np.eye(384, dtype=np.float32)[0], {"unknown"}, -1)


def test_source_change_during_encoding_rejects_old_ranked_ids(monkeypatch):
    from unittest.mock import Mock

    from archimind.retrieval import semantic

    options = semantic.current_options()
    p = provider()
    monkeypatch.setattr(
        semantic, "current_options", Mock(side_effect=[options, options[:1]])
    )
    result = p.search(FurnitureSearchRequest(query="seat"))
    assert result.status == "stale_index" and not result.hits


@pytest.mark.parametrize("query", [np.zeros(384), np.full(384, np.nan), np.ones(383)])
def test_direct_ranker_rejects_invalid_query_vectors(query):
    p = provider()
    with pytest.raises(EmbeddingError):
        rank_cosine(p.index, query, set(p.index.manifest.row_asset_ids), -1)
