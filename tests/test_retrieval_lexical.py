"""Lexical mechanics never outrank current hard eligibility or source identity."""

import sqlite3

import pytest
from retrieval_helpers import offline  # noqa: F401

from archimind.assets.specifications import BOOKCASE_ID, CHARLES_ID
from archimind.retrieval import (
    FurnitureSearchFilters,
    FurnitureSearchRequest,
    resolve_result,
)
from archimind.retrieval import eligibility as authority
from archimind.retrieval import lexical as api


@pytest.fixture(params=["python_bm25_v1", "sqlite_fts5_bm25_v1"])
def provider(request):
    if request.param == "sqlite_fts5_bm25_v1" and not api.fts5_available():
        pytest.skip("SQLite lacks optional FTS5")
    return api.LexicalRetrievalProvider(algorithm=request.param)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Charles armchair", (CHARLES_ID,)),
        ("ＳＯＤ accent chair", (CHARLES_ID,)),
        ("bookshelf", (BOOKCASE_ID,)),
        ("B07PQS58XN", (BOOKCASE_ID,)),
        ("queen bed", ()),
        ("writing desk", ()),
        ("wardrobe", ()),
        ("Charles Blue", ()),
        ("leather armchair", ()),
        ("https://evil.invalid/model.glb", ()),
        ("chair OR 1 1 DROP TABLE", ()),
        ("the", ()),
    ],
)
def test_keyword_matching_no_substitution(provider, query, expected):
    result = provider.search(FurnitureSearchRequest(query=query))
    assert tuple(h.reference.asset_id for h in result.hits) == expected
    assert result.status == ("matches" if expected else "empty")


@pytest.mark.parametrize(
    "filters,qual,expected",
    [
        (dict(category="chair"), "metadata", (CHARLES_ID,)),
        (dict(category="storage"), "metadata", (BOOKCASE_ID,)),
        (dict(category="storage"), "render", ()),
        (dict(category="chair", max_width_m=0.9906), "metadata", ()),
        (dict(required_use="wardrobe"), "metadata", ()),
        (dict(materials=("leather",)), "metadata", ()),
        (dict(styles=("classic",)), "metadata", ()),
        (dict(colors=("Espresso",)), "metadata", ()),
        (dict(product_id="B07PQS58XN", variant="Sod"), "metadata", ()),
        (dict(max_depth_m=0.4), "metadata", (BOOKCASE_ID,)),
    ],
)
def test_hard_filter_before_ranking(provider, filters, qual, expected):
    result = provider.search(
        FurnitureSearchRequest(
            query="",
            filters=FurnitureSearchFilters(**filters),
            required_qualification=qual,
        )
    )
    assert tuple(h.reference.asset_id for h in result.hits) == expected
    assert tuple(o.record.asset_id for o in resolve_result(result)) == expected


def test_published_fact_search_does_not_authorize_smaller_generation(provider):
    request = FurnitureSearchRequest(
        query="Charles",
        dimension_basis="published",
        filters=FurnitureSearchFilters(max_width_m=0.9906),
    )
    result = provider.search(request)
    assert result.hits[0].reference.asset_id == CHARLES_ID
    with pytest.raises(authority.RetrievalError):
        resolve_result(result)
    assert (
        resolve_result(result, for_preparation=False)[0].record.dimensions.width_m
        == 0.9906
    )


def test_tie_order_top_k_and_serialization_are_deterministic(provider):
    request = FurnitureSearchRequest(query="", top_k=1)
    before = provider.index.model_dump_json()
    results = [provider.search(request).model_dump_json() for _ in range(3)]
    assert results == [results[0]] * 3
    assert provider.search(request).hits[0].reference.asset_id == CHARLES_ID
    assert before == provider.index.model_dump_json()
    assert (
        provider.search(FurnitureSearchRequest(query="", top_k=2))
        .hits[1]
        .reference.asset_id
        == BOOKCASE_ID
    )


def test_stale_versions_documents_and_evidence_are_not_repaired(monkeypatch):
    provider = api.LexicalRetrievalProvider()
    for request in [
        FurnitureSearchRequest(query="chair", catalog_version="0.9.0"),
        FurnitureSearchRequest(query="chair", catalog_id="not-our-catalog"),
    ]:
        result = provider.search(request)
        assert result.status == "stale_index" and not result.hits
    original = provider.index
    provider.index = original.model_copy(
        update={
            "documents": (
                original.documents[0].model_copy(update={"text": "forged chair"}),
                *original.documents[1:],
            )
        }
    )
    assert (
        provider.search(FurnitureSearchRequest(query="chair")).status == "stale_index"
    )
    provider.index = original
    options = authority.current_options()
    monkeypatch.setattr(
        api,
        "current_options",
        lambda: tuple(
            o.model_copy(update={"record_digest": "0" * 64}) for o in options
        ),
    )
    assert (
        provider.search(FurnitureSearchRequest(query="chair")).status == "stale_index"
    )
    assert provider.index == original


def test_missing_authority_is_sanitized_and_fts_failure_has_no_silent_substitute(
    monkeypatch,
):
    provider = api.LexicalRetrievalProvider()
    original_authority = api.current_options

    def missing():
        raise authority.RetrievalError("private-secret-path")

    monkeypatch.setattr(api, "current_options", missing)
    result = provider.search(FurnitureSearchRequest(query="chair"))
    assert (
        result.status == "unavailable"
        and "private-secret" not in result.model_dump_json()
    )
    monkeypatch.setattr(api, "current_options", original_authority)

    def no_sqlite(*args, **kwargs):
        raise sqlite3.OperationalError("no such module: fts5")

    monkeypatch.setattr(api.sqlite3, "connect", no_sqlite)
    assert not api.fts5_available()
    assert (
        api.LexicalRetrievalProvider()
        .search(FurnitureSearchRequest(query="chair"))
        .hits
    )
    assert (
        api.LexicalRetrievalProvider(algorithm="sqlite_fts5_bm25_v1")
        .search(FurnitureSearchRequest(query="chair"))
        .status
        == "unavailable"
    )


def test_document_digest_excludes_marketing_and_source_model_locations():
    index = authority.build_index()
    for doc in index.documents:
        assert "https://" not in doc.text and ".glb" not in doc.text
        assert "leather" not in doc.text.lower()
        option = next(
            o
            for o in authority.current_options()
            if o.record.asset_id == doc.reference.asset_id
        )
        assert (
            doc.reference.search_document_digest == option.record.search_document_sha256
        )
    with pytest.raises(ValueError):
        api.LexicalRetrievalProvider(algorithm="arbitrary-command")


def test_missing_entire_sqlite_capability_preserves_python_baseline(monkeypatch):
    monkeypatch.setattr(api, "sqlite3", None)
    assert not api.fts5_available()
    assert (
        api.LexicalRetrievalProvider()
        .search(FurnitureSearchRequest(query="chair"))
        .hits
    )
    result = api.LexicalRetrievalProvider(algorithm="sqlite_fts5_bm25_v1").search(
        FurnitureSearchRequest(query="chair")
    )
    assert result.status == "unavailable" and not result.hits


def test_untyped_index_is_not_an_authority_override():
    for value in ({}, "index-file", False):
        with pytest.raises(authority.RetrievalError):
            api.LexicalRetrievalProvider(index=value)
