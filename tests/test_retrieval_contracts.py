"""Typed, immutable search messages and current source-authority checks."""

import json

import pytest
from pydantic import ValidationError
from retrieval_helpers import offline  # noqa: F401

from archimind.assets.specifications import BOOKCASE_ID, CHARLES_ID
from archimind.retrieval import eligibility as api
from archimind.retrieval.contracts import (
    FurnitureSearchFilters,
    FurnitureSearchHit,
    FurnitureSearchRequest,
    FurnitureSearchResult,
)


def make_hit(asset=CHARLES_ID, **kwargs):
    option = next(o for o in api.current_options() if o.record.asset_id == asset)
    return FurnitureSearchHit(
        reference=api.reference(option),
        scope="real",
        qualification=api.qualification(option),
        rank=1,
        score=1.0,
        reasons=("structured_filters_passed",),
        evidence_urls=api.evidence_urls(option),
        **kwargs,
    )


def test_frozen_messages_and_strict_roundtrip():
    request = FurnitureSearchRequest(
        query="Charles armchair",
        filters=FurnitureSearchFilters(category="chair", max_width_m=1.0),
    )
    index = api.build_index()
    result = FurnitureSearchResult(
        request=request,
        identity=index.identity,
        algorithm="test_v1",
        status="matches",
        hits=(make_hit(),),
        reasons=("eligible",),
    )
    assert type(result).model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        result.request.filters.category = "storage"
    with pytest.raises(ValidationError):
        result.hits[0].reference.asset_id = "bad"
    assert (
        api.resolve_hit(result.hits[0], result.identity).record.asset_id == CHARLES_ID
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(top_k=0),
        dict(top_k=True),
        dict(top_k=51),
        dict(query="a\nsecret"),
        dict(extra=True),
        dict(required_qualification="unknown"),
        dict(dimension_basis="mesh"),
        dict(required_qualification="render", dimension_basis="published"),
    ],
)
def test_invalid_requests(kwargs):
    with pytest.raises(ValueError):
        FurnitureSearchRequest(**({"query": "chair"} | kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(max_width_m=0),
        dict(max_depth_m=float("nan")),
        dict(max_height_m=float("inf")),
        dict(rotation_deg=90),
        dict(rotation_deg=False),
        dict(materials=("oak", "Oak")),
        dict(styles=("",)),
        dict(asset_id="https://evil.invalid/f.glb"),
        dict(variant=""),
        dict(category=" chair"),
    ],
)
def test_invalid_filters(kwargs):
    with pytest.raises(ValueError):
        FurnitureSearchFilters(**kwargs)


def test_duplicate_keys_unknown_fields_and_wrong_hit_rank():
    with pytest.raises(ValueError):
        FurnitureSearchRequest.model_validate_json('{"query":"chair","query":"bed"}')
    with pytest.raises(ValueError):
        FurnitureSearchRequest.model_validate_json('{"query":"chair","top_k":NaN}')
    h = make_hit()
    raw = h.model_dump(mode="json")
    raw["model_url"] = "https://evil.invalid/f.glb"
    with pytest.raises(ValueError):
        FurnitureSearchHit.model_validate_json(json.dumps(raw))
    index = api.build_index()
    for hits in (
        (h, h),
        (h.model_copy(update={"rank": 2}),),
        (h.model_copy(update={"score": float("nan")}),),
    ):
        with pytest.raises(ValueError):
            FurnitureSearchResult(
                request=FurnitureSearchRequest(query=""),
                identity=index.identity,
                algorithm="test_v1",
                status="matches",
                hits=hits,
                reasons=("test",),
            )


def test_index_identity_digests_and_duplicate_rejection():
    index = api.build_index()
    assert api.build_index() == index
    assert type(index).model_validate_json(index.model_dump_json()) == index
    with pytest.raises(ValueError):
        type(index)(
            identity=index.identity, documents=index.documents + index.documents
        )
    with pytest.raises(ValueError):
        type(index)(
            identity=index.identity.model_copy(update={"snapshot_id": "0" * 64}),
            documents=index.documents,
        )
    assert (
        index.documents[0].reference.search_document_digest
        == api.current_options()[0].record.search_document_sha256
    )


@pytest.mark.parametrize(
    "asset,filters,reasons",
    [
        (CHARLES_ID, {"max_width_m": 0.9906}, ("width_exceeded",)),
        (CHARLES_ID, {"variant": "Blue"}, ("variant_mismatch",)),
        (BOOKCASE_ID, {"category": "bed"}, ("category_mismatch",)),
        (BOOKCASE_ID, {"required_use": "wardrobe"}, ("use_not_verified",)),
        (CHARLES_ID, {"materials": ("leather",)}, ("materials_not_verified",)),
        (BOOKCASE_ID, {"colors": ("Espresso",)}, ("colors_not_verified",)),
        (CHARLES_ID, {"styles": ("classic",)}, ("styles_not_verified",)),
    ],
)
def test_hard_filters_do_not_invent_evidence(asset, filters, reasons):
    o = next(o for o in api.current_options() if o.record.asset_id == asset)
    assert (
        api.eligibility_reasons(
            FurnitureSearchRequest(query="", filters=FurnitureSearchFilters(**filters)),
            o,
        )
        == reasons
    )


def test_dimensions_qualification_and_verified_uses():
    chair, book = (
        next(o for o in api.current_options() if o.record.asset_id == key)
        for key in (CHARLES_ID, BOOKCASE_ID)
    )
    assert not api.eligibility_reasons(
        FurnitureSearchRequest(
            query="", filters=FurnitureSearchFilters(required_use="accent chair")
        ),
        chair,
    )
    assert not api.eligibility_reasons(
        FurnitureSearchRequest(
            query="", filters=FurnitureSearchFilters(required_use="book storage")
        ),
        book,
    )
    assert not api.eligibility_reasons(
        FurnitureSearchRequest(
            query="",
            dimension_basis="published",
            filters=FurnitureSearchFilters(max_width_m=0.9906),
        ),
        chair,
    )
    assert api.eligibility_reasons(
        FurnitureSearchRequest(query="", required_qualification="render"), book
    ) == ("planning_unavailable", "render_unavailable")
    assert not api.eligibility_reasons(
        FurnitureSearchRequest(query="", required_qualification="render"), chair
    )
    assert (
        api.qualification(chair) == "render" and api.qualification(book) == "metadata"
    )


def test_stale_or_poisoned_references_cannot_resolve():
    h = make_hit()
    identity = api.build_index().identity
    for bad in (
        h.model_copy(
            update={
                "reference": h.reference.model_copy(
                    update={"asset_id": "abo-nonexistent"}
                )
            }
        ),
        h.model_copy(update={"qualification": "metadata"}),
        h.model_copy(update={"evidence_urls": ("https://evil.invalid/notice",)}),
    ):
        with pytest.raises(api.RetrievalError):
            api.resolve_hit(bad, identity)
    with pytest.raises(api.RetrievalError):
        api.resolve_hit(h, identity.model_copy(update={"snapshot_id": "0" * 64}))
    with pytest.raises(ValueError):
        h.model_copy(
            update={"evidence_urls": ("https://evil.invalid/model.glb",)}
        ).__class__.model_validate(
            h.model_copy(update={"evidence_urls": ("https://evil.invalid/model.glb",)})
        )


def test_current_authority_rejects_invalid_rights_and_dimensions(monkeypatch):
    options = api.current_options()
    bad = options[0].record.model_copy(
        update={
            "legal": options[0].record.legal.model_copy(
                update={"public_browser_delivery": False}
            )
        }
    )
    monkeypatch.setattr(
        api,
        "catalog_product_options",
        lambda: (options[0].model_copy(update={"record": bad}), options[1]),
    )
    with pytest.raises(api.RetrievalError, match="authority"):
        api.current_options()


def test_unknown_planning_stays_unevaluated(monkeypatch):
    from archimind.assets import specifications

    def missing(*args):
        raise ValueError("private unavailable path")

    monkeypatch.setattr(specifications, "load_planning_envelope", missing)
    chair, book = (
        next(o for o in api.current_options() if o.record.asset_id == key)
        for key in (CHARLES_ID, BOOKCASE_ID)
    )
    assert not chair.preparation_available and not chair.render_qualified
    assert "preparation_unavailable" in api.eligibility_reasons(
        FurnitureSearchRequest(query=""), chair
    )
    assert not api.eligibility_reasons(
        FurnitureSearchRequest(query="", dimension_basis="published"), chair
    )
    assert not api.eligibility_reasons(FurnitureSearchRequest(query=""), book)


def test_result_resolution_rechecks_filters_not_only_product_identity():
    request = FurnitureSearchRequest(
        query="Charles", filters=FurnitureSearchFilters(max_width_m=0.5)
    )
    result = FurnitureSearchResult(
        request=request,
        identity=api.build_index().identity,
        algorithm="forged_v1",
        status="matches",
        hits=(make_hit(),),
        reasons=("claimed_match",),
    )
    with pytest.raises(api.RetrievalError, match="ineligible"):
        api.resolve_result(result)


@pytest.mark.parametrize(
    "url",
    [
        "https://evidence.invalid:bad/notice",
        "https://evidence.invalid:8080/notice",
        "https://user:secret@evidence.invalid/notice",
        "https://evidence.invalid/model.gltf",
    ],
)
def test_invalid_source_locations_are_not_search_evidence(url):
    h = make_hit()
    with pytest.raises(ValueError):
        FurnitureSearchHit.model_validate(
            h.model_copy(update={"evidence_urls": (url,)})
        )


def test_nested_messages_are_single_line_and_models_cannot_be_promoted():
    h = make_hit()
    with pytest.raises(ValueError):
        FurnitureSearchHit.model_validate(
            h.model_copy(update={"reasons": ("line\nbreak",)})
        )
    book = make_hit(BOOKCASE_ID).model_copy(update={"qualification": "render"})
    with pytest.raises(api.RetrievalError):
        api.resolve_hit(book, api.build_index().identity)


def test_index_input_size_is_bounded():
    from archimind.retrieval.eligibility import IndexedDocument

    index = api.build_index()
    with pytest.raises(ValueError):
        IndexedDocument(reference=index.documents[0].reference, text="x" * 16385)


def test_empty_results_still_require_current_identity():
    index = api.build_index()
    result = FurnitureSearchResult(
        request=FurnitureSearchRequest(query="queen bed"),
        identity=index.identity,
        algorithm="test_v1",
        status="empty",
        hits=(),
        reasons=("no_match",),
    )
    assert api.resolve_result(result) == ()
    stale = result.model_copy(
        update={
            "identity": result.identity.model_copy(update={"snapshot_id": "0" * 64})
        }
    )
    with pytest.raises(api.RetrievalError):
        api.resolve_result(stale)


def test_empty_response_cannot_disguise_requested_version_mismatch():
    with pytest.raises(ValueError):
        FurnitureSearchResult(
            request=FurnitureSearchRequest(query="chair", catalog_version="0.9.0"),
            identity=api.build_index().identity,
            algorithm="test_v1",
            status="empty",
            hits=(),
            reasons=("no_match",),
        )
