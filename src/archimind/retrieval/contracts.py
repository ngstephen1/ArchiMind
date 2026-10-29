"""Immutable retrieval messages. Identifiers are references, never mesh approval."""

import json
from typing import Annotated, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictInt,
    field_validator,
    model_validator,
)

Text = Annotated[str, Field(max_length=1024)]
Identifier = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9:_-]*$")
]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
Qualification = Literal["metadata", "planning", "render"]
Scope = Literal["real", "synthetic_fixture"]


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate retrieval JSON key")
        result[key] = value
    return result


class Frozen(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @field_validator("*", mode="after")
    @classmethod
    def text_hygiene(cls, value):
        if isinstance(value, str) and (
            value != value.strip() or any(ord(c) < 32 for c in value)
        ):
            raise ValueError("Retrieval text must be trimmed and single-line")
        return value

    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        try:
            json.loads(
                json_data,
                object_pairs_hook=_unique,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
        except (ValueError, TypeError, UnicodeError):
            raise ValueError("Invalid retrieval JSON") from None
        return super().model_validate_json(json_data, **kwargs)


class FurnitureSearchFilters(Frozen):
    category: Identifier | None = None
    asset_id: Identifier | None = None
    product_id: Identifier | None = None
    variant: Text | None = None
    required_use: Text | None = None
    materials: tuple[Text, ...] = ()
    styles: tuple[Text, ...] = ()
    colors: tuple[Text, ...] = ()
    max_width_m: FiniteFloat | None = Field(default=None, gt=0)
    max_depth_m: FiniteFloat | None = Field(default=None, gt=0)
    max_height_m: FiniteFloat | None = Field(default=None, gt=0)
    rotation_deg: StrictInt = Field(default=0, ge=0, le=0)

    @field_validator("materials", "styles", "colors")
    @classmethod
    def unique_attributes(cls, values):
        if (
            len(values) > 16
            or any(
                not v.strip() or v != v.strip() or any(ord(c) < 32 for c in v)
                for v in values
            )
            or len({v.casefold() for v in values}) != len(values)
        ):
            raise ValueError("Invalid or duplicate attribute constraints")
        return tuple(sorted(values, key=str.casefold))

    @field_validator("variant", "required_use")
    @classmethod
    def nonblank_filter(cls, value):
        if value is not None and not value:
            raise ValueError("An exact text filter cannot be empty")
        return value


class FurnitureSearchRequest(Frozen):
    query: Text
    filters: FurnitureSearchFilters = FurnitureSearchFilters()
    required_qualification: Qualification = "metadata"
    dimension_basis: Literal["generation_reservation", "published"] = (
        "generation_reservation"
    )
    catalog_id: Identifier = "archimind-furniture"
    catalog_version: Version | None = None
    top_k: StrictInt = Field(default=5, ge=1, le=50)

    @model_validator(mode="after")
    def safe_dimension_intent(self):
        if (
            self.dimension_basis == "published"
            and self.required_qualification != "metadata"
        ):
            raise ValueError("Planning/render searches require generation reservations")
        return self


class CatalogReference(Frozen):
    catalog_id: Identifier
    catalog_version: Version
    asset_id: Identifier
    asset_version: Version
    product_id: Identifier
    record_digest: Digest
    search_document_version: StrictInt = Field(ge=1)
    search_document_digest: Digest


class IndexIdentity(Frozen):
    scope: Scope
    catalog_id: Identifier
    catalog_version: Version
    catalog_digest: Digest
    evidence_digest: Digest
    search_document_version: StrictInt = Field(ge=1)
    index_format_version: StrictInt = Field(default=1, ge=1, le=1)
    snapshot_id: Digest

    @model_validator(mode="after")
    def isolated_namespace(self):
        if self.catalog_id.startswith("synthetic:") != (
            self.scope == "synthetic_fixture"
        ):
            raise ValueError("Synthetic namespace and scope must agree")
        return self


class FurnitureSearchHit(Frozen):
    reference: CatalogReference
    scope: Scope
    qualification: Literal["metadata", "planning", "render", "synthetic_fixture"]
    rank: StrictInt = Field(ge=1, le=50)
    score: FiniteFloat = Field(ge=0)
    reasons: tuple[Text, ...] = Field(min_length=1, max_length=16)
    evidence_urls: tuple[Text, ...] = Field(max_length=32)

    @model_validator(mode="after")
    def no_asset_or_fixture_promotion(self):
        synthetic = self.scope == "synthetic_fixture"
        if synthetic != self.reference.catalog_id.startswith(
            "synthetic:"
        ) or synthetic != self.reference.asset_id.startswith("synthetic:"):
            raise ValueError("Mixed real/synthetic identity")
        if synthetic != (self.qualification == "synthetic_fixture") or (
            synthetic and self.evidence_urls
        ):
            raise ValueError(
                "Synthetic fixtures cannot claim qualification or source rights"
            )
        if len(set(self.evidence_urls)) != len(self.evidence_urls):
            raise ValueError("Duplicate evidence")
        for url in self.evidence_urls:
            p = urlsplit(url)
            if (
                p.scheme != "https"
                or not p.hostname
                or p.username is not None
                or p.password is not None
                or p.query
                or p.path.lower().endswith((".glb", ".gltf", ".obj", ".fbx"))
            ):
                raise ValueError("Evidence links cannot supply model locations")
        return self


class FurnitureSearchResult(Frozen):
    request: FurnitureSearchRequest
    identity: IndexIdentity
    algorithm: Identifier
    status: Literal["matches", "empty", "stale_index", "unavailable"]
    hits: tuple[FurnitureSearchHit, ...] = Field(max_length=50)
    reasons: tuple[Text, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def consistent_hits(self):
        if (
            bool(self.hits) != (self.status == "matches")
            or len(self.hits) > self.request.top_k
        ):
            raise ValueError("Result status/count mismatch")
        ids = [h.reference.asset_id for h in self.hits]
        if len(ids) != len(set(ids)) or [h.rank for h in self.hits] != list(
            range(1, len(self.hits) + 1)
        ):
            raise ValueError("Duplicate or invalid hit ranks")
        if list(self.hits) != sorted(
            self.hits, key=lambda h: (-h.score, h.reference.asset_id)
        ):
            raise ValueError("Hits must be ordered by score and stable ID")
        for h in self.hits:
            r = h.reference
            if (
                r.catalog_id,
                r.catalog_version,
                r.search_document_version,
                h.scope,
            ) != (
                self.identity.catalog_id,
                self.identity.catalog_version,
                self.identity.search_document_version,
                self.identity.scope,
            ):
                raise ValueError("Hit identity differs from its index")
            if (
                self.request.catalog_id != r.catalog_id
                or self.request.catalog_version not in (None, r.catalog_version)
            ):
                raise ValueError("Hit does not satisfy requested catalog identity")
            if h.scope == "real" and ["metadata", "planning", "render"].index(
                h.qualification
            ) < ["metadata", "planning", "render"].index(
                self.request.required_qualification
            ):
                raise ValueError("Hit lacks required qualification")
            if (
                h.scope == "synthetic_fixture"
                and self.request.required_qualification != "metadata"
            ):
                raise ValueError("Fixtures cannot qualify planning or rendering")
        return self


class FurnitureRetrievalProvider(Protocol):
    def search(self, request: FurnitureSearchRequest) -> FurnitureSearchResult: ...
