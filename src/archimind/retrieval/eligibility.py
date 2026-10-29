"""Current catalog authority, qualification filtering and derived-index identity."""

import hashlib
import json
import unicodedata
from decimal import Decimal

from pydantic import Field, model_validator

from archimind.assets.catalog import FurnitureAssetRecord
from archimind.assets.specifications import (
    CatalogProductOption,
    catalog_product_options,
)
from archimind.retrieval.contracts import (
    CatalogReference,
    Frozen,
    FurnitureSearchHit,
    FurnitureSearchRequest,
    IndexIdentity,
)


class RetrievalError(ValueError):
    """Sanitized current-authority or stale-reference error."""


def digest(value) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


class IndexedDocument(Frozen):
    reference: CatalogReference
    text: str = Field(min_length=1, max_length=16384)


class RetrievalIndex(Frozen):
    identity: IndexIdentity
    documents: tuple[IndexedDocument, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def consistent_snapshot(self):
        refs = [d.reference for d in self.documents]
        ids = [r.asset_id for r in refs]
        if ids != sorted(set(ids)):
            raise ValueError("Duplicate or unordered index documents")
        if any(
            (r.catalog_id, r.catalog_version, r.search_document_version)
            != (
                self.identity.catalog_id,
                self.identity.catalog_version,
                self.identity.search_document_version,
            )
            for r in refs
        ):
            raise ValueError("Document identity differs from index")
        if (
            digest([d.model_dump(mode="json") for d in self.documents])
            != self.identity.catalog_digest
            or digest(self.identity.model_dump(mode="json", exclude={"snapshot_id"}))
            != self.identity.snapshot_id
        ):
            raise ValueError("Invalid index digest")
        return self

    @classmethod
    def from_options(cls, options: tuple[CatalogProductOption, ...]):
        if not options:
            raise RetrievalError("Catalog is unavailable")
        first = options[0]
        documents = tuple(
            IndexedDocument(
                reference=reference(o),
                text=" ".join(o.record.search_document().splitlines()),
            )
            for o in options
        )
        docs_digest = digest([d.model_dump(mode="json") for d in documents])
        evidence_digest = digest([o.model_dump(mode="json") for o in options])
        fields = dict(
            scope="real",
            catalog_id=first.catalog_id,
            catalog_version=first.catalog_version,
            catalog_digest=docs_digest,
            evidence_digest=evidence_digest,
            search_document_version=1,
            index_format_version=1,
        )
        return cls(
            identity=IndexIdentity(**fields, snapshot_id=digest(fields)),
            documents=documents,
        )


def current_options() -> tuple[CatalogProductOption, ...]:
    try:
        options = catalog_product_options()
        for o in options:
            FurnitureAssetRecord.model_validate(o.record)
        if (
            not options
            or len({o.record.asset_id for o in options}) != len(options)
            or len({(o.catalog_id, o.catalog_version) for o in options}) != 1
        ):
            raise ValueError
        return tuple(sorted(options, key=lambda o: o.record.asset_id))
    except (ValueError, TypeError, OSError, RecursionError):
        raise RetrievalError("Catalog authority is unavailable") from None


def reference(option: CatalogProductOption) -> CatalogReference:
    r = option.record
    return CatalogReference(
        catalog_id=option.catalog_id,
        catalog_version=option.catalog_version,
        asset_id=r.asset_id,
        asset_version=r.asset_version,
        product_id=r.source.product_id,
        record_digest=digest(r),
        search_document_version=1,
        search_document_digest=r.search_document_sha256,
    )


def build_index() -> RetrievalIndex:
    """In-memory derived text only; no index file or database is written."""
    return RetrievalIndex.from_options(current_options())


def qualification(option: CatalogProductOption) -> str:
    return (
        "render"
        if option.render_qualified
        else "planning"
        if option.planning_dimensions is not None
        else "metadata"
    )


def eligibility_reasons(
    request: FurnitureSearchRequest, option: CatalogProductOption
) -> tuple[str, ...]:
    """Every nonempty reason excludes the product, regardless of lexical score."""
    r, f = option.record, request.filters
    reasons = []
    if request.catalog_id != option.catalog_id or request.catalog_version not in (
        None,
        option.catalog_version,
    ):
        reasons.append("catalog_identity_mismatch")
    if not (r.legal.public_browser_delivery and r.legal.redistribution):
        reasons.append("rights_not_qualified")
    for name, actual in (
        ("category", r.category),
        ("asset_id", r.asset_id),
        ("product_id", r.source.product_id),
        ("variant", r.variant_label),
    ):
        expected = getattr(f, name)
        if expected is not None and normalized(expected) != normalized(actual):
            reasons.append(f"{name}_mismatch")
    uses = {normalized(v) for v in (*r.search.usage_tags, *r.search.aliases, r.subtype)}
    if f.required_use is not None and normalized(f.required_use) not in uses:
        reasons.append("use_not_verified")
    for attr in ("materials", "styles", "colors"):
        actual = {normalized(v.value) for v in (getattr(r.search, attr) or ())}
        if not {normalized(v) for v in getattr(f, attr)} <= actual:
            reasons.append(f"{attr}_not_verified")
    if (
        request.required_qualification in ("planning", "render")
        and option.planning_dimensions is None
    ):
        reasons.append("planning_unavailable")
    if request.required_qualification == "render" and not option.render_qualified:
        reasons.append("render_unavailable")
    if (
        request.dimension_basis == "generation_reservation"
        and not option.preparation_available
    ):
        reasons.append("preparation_unavailable")
    dimensions = (
        option.planning_dimensions
        if request.dimension_basis == "generation_reservation"
        and option.planning_dimensions is not None
        else r.dimensions
    )
    for axis in ("width", "depth", "height"):
        limit = getattr(f, f"max_{axis}_m")
        if limit is not None and Decimal(
            str(getattr(dimensions, f"{axis}_m"))
        ) > Decimal(str(limit)):
            reasons.append(f"{axis}_exceeded")
    if r.rotation_deg != f.rotation_deg:
        reasons.append("orientation_unsupported")
    return tuple(reasons)


def evidence_urls(option: CatalogProductOption) -> tuple[str, ...]:
    r = option.record
    return tuple(
        sorted(
            set(
                (
                    *r.dimensions.evidence_urls,
                    *r.search.evidence_urls,
                    *r.legal.evidence_urls,
                )
            )
        )
    )


def resolve_hit(
    hit: FurnitureSearchHit, identity: IndexIdentity
) -> CatalogProductOption:
    """Resolve current authority before any future 08E handoff; never follow hit URLs."""
    try:
        hit = FurnitureSearchHit.model_validate(hit)
        if hit.scope != "real":
            raise ValueError
        options = current_options()
        if RetrievalIndex.from_options(options).identity != identity:
            raise ValueError
        option = next(o for o in options if o.record.asset_id == hit.reference.asset_id)
        if (
            hit.reference != reference(option)
            or hit.qualification != qualification(option)
            or hit.evidence_urls != evidence_urls(option)
        ):
            raise ValueError
        return option
    except (ValueError, TypeError, StopIteration):
        raise RetrievalError("Retrieval reference is stale or unauthorized") from None


def resolve_result(
    result, *, for_preparation: bool = True
) -> tuple[CatalogProductOption, ...]:
    """Recheck IDs, current evidence and hard filters before a future UI handoff."""
    from archimind.retrieval.contracts import FurnitureSearchResult

    try:
        result = FurnitureSearchResult.model_validate(result)
        if result.identity.scope != "real" or result.status not in ("matches", "empty"):
            raise ValueError
        if (
            for_preparation
            and result.request.dimension_basis != "generation_reservation"
        ):
            raise ValueError
        if build_index().identity != result.identity:
            raise ValueError
        options = tuple(resolve_hit(h, result.identity) for h in result.hits)
        if any(eligibility_reasons(result.request, o) for o in options) or (
            for_preparation and any(not o.preparation_available for o in options)
        ):
            raise ValueError
        return options
    except (ValueError, TypeError):
        raise RetrievalError("Search result is stale or ineligible") from None
