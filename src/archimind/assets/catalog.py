"""Strict, offline product catalog; no asset acquisition or render approval.

Published item measurements are reviewed claims, not independent metrology.
All containers are immutable. Source URLs are evidence strings, never fetched.
The factory proposes unrotated furniture; only explicit downstream operations
can generate layouts or establish spatial validity.
"""

import hashlib
import json
from decimal import Decimal
from importlib import resources
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from archimind.models import Furniture


def _single_line(value: str) -> str:
    if value != value.strip() or any(ord(ch) < 32 for ch in value):
        raise ValueError("Catalog text must be trimmed and single-line.")
    return value


Text = Annotated[
    str,
    Field(min_length=1, max_length=2048, pattern=r"\S"),
    AfterValidator(_single_line),
]
Version = Annotated[str, Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")]
SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ProductId = Annotated[str, Field(pattern=r"^[A-Z0-9]{10}$")]
SourceAxis = Literal["width", "length", "height"]
CanonicalAxis = Literal["width_m", "depth_m", "height_m"]
Unit = Literal["meters", "centimeters", "millimeters", "inches"]
MAX_CATALOG_BYTES = 512 * 1024
_ABO = "https://amazon-berkeley-objects.s3.amazonaws.com/"


class CatalogError(ValueError):
    """A sanitized public failure; never contains source payloads or paths."""


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError("Duplicate catalog JSON key.")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise CatalogError("Non-finite catalog JSON value.")


def _https(value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Evidence must be HTTPS without credentials.")
    return value


EvidenceURL = Annotated[Text, Field(max_length=2048)]


class _Frozen(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @field_validator("*", mode="after")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str) and (
            value != value.strip() or any(ord(ch) < 32 for ch in value)
        ):
            raise ValueError("Catalog text must be trimmed and single-line.")
        return value

    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        # Validate keys/constants before Pydantic's JSON parser can discard them.
        try:
            json.loads(
                json_data,
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_constant,
            )
        except (ValueError, TypeError, UnicodeError):
            raise CatalogError("Invalid catalog JSON.") from None
        return super().model_validate_json(json_data, **kwargs)


class SourceProvenance(_Frozen):
    dataset: Literal["Amazon Berkeley Objects"]
    product_id: ProductId
    model_id: ProductId
    marketplace_domain: Annotated[str, Field(pattern=r"^amazon\.[a-z.]+$")]
    manufacturer_model_numbers: tuple[Text, ...] = Field(min_length=1)
    variant_label: Text
    original_category: Literal["CHAIR", "SHELF"]
    original_title: Text
    metadata_url: EvidenceURL
    model_url: EvidenceURL
    source_revision: Text | None
    source_last_modified: Text
    source_etag: Text
    listing_line: StrictInt = Field(gt=0)
    listing_record_sha256: SHA256
    metadata_snapshot_sha256: SHA256
    model_index_sha256: SHA256
    qualification_candidate_id: Text
    qualification_revision: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    qualification_file_sha256: SHA256
    qualification_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]

    @field_validator("metadata_url", "model_url")
    @classmethod
    def official_source(cls, value: str) -> str:
        if not _https(value).startswith(_ABO):
            raise ValueError("Unsupported source reference.")
        return value

    @model_validator(mode="after")
    def identity_agrees(self) -> Self:
        expected = (
            f"abo-{self.product_id.lower()}-{self.marketplace_domain.replace('.', '-')}"
        )
        if (
            self.product_id != self.model_id
            or self.qualification_candidate_id != expected
            or not self.model_url.endswith(f"/{self.model_id}.glb")
            or len(set(self.manufacturer_model_numbers))
            != len(self.manufacturer_model_numbers)
        ):
            raise ValueError("Conflicting source identity or variant evidence.")
        return self


class LegalProvenance(_Frozen):
    status: Literal["verified"]
    license_id: Literal["CC-BY-4.0"]
    license_url: Literal[
        "https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt"
    ]
    copyright: Text
    creator: Text | None
    attribution: Text
    modification_notice: Text
    restrictions: tuple[Text, ...]
    evidence_urls: tuple[EvidenceURL, ...] = Field(min_length=1)
    public_browser_delivery: StrictBool
    redistribution: StrictBool
    commercial_use: StrictBool

    @field_validator("evidence_urls")
    @classmethod
    def public_evidence(cls, values):
        for value in values:
            _https(value)
        return values

    @model_validator(mode="after")
    def rights_agree(self) -> Self:
        if not (
            self.public_browser_delivery and self.redistribution and self.commercial_use
        ):
            raise ValueError("Rights are incompatible with the approved license.")
        if self.license_url not in self.evidence_urls:
            raise ValueError("Missing authoritative license evidence.")
        return self


class Measurement(_Frozen):
    source_field: SourceAxis
    value: FiniteFloat = Field(gt=0)
    unit: Unit


class AxisAssignment(_Frozen):
    target: CanonicalAxis
    source_field: SourceAxis


class PhysicalDimensions(_Frozen):
    status: Literal["verified"]
    kind: Literal["item"]
    uncertainty: Literal["published_claim_not_independent_measurement"]
    original: tuple[Measurement, ...] = Field(min_length=3, max_length=3)
    axis_map: tuple[AxisAssignment, ...] = Field(min_length=3, max_length=3)
    axis_evidence: Text
    evidence_urls: tuple[EvidenceURL, ...] = Field(min_length=1)
    width_m: FiniteFloat = Field(gt=0)
    depth_m: FiniteFloat = Field(gt=0)
    height_m: FiniteFloat = Field(gt=0)

    @field_validator("evidence_urls")
    @classmethod
    def public_evidence(cls, values):
        return LegalProvenance.public_evidence(values)

    @model_validator(mode="after")
    def normalization_agrees(self) -> Self:
        original = {m.source_field: m for m in self.original}
        assignments = {a.target: a.source_field for a in self.axis_map}
        if (
            set(original) != {"width", "length", "height"}
            or set(assignments) != {"width_m", "depth_m", "height_m"}
            or set(assignments.values()) != set(original)
            or assignments["height_m"] != "height"
        ):
            raise ValueError("Ambiguous dimension axes.")
        factors = {
            "meters": Decimal("1"),
            "centimeters": Decimal("0.01"),
            "millimeters": Decimal("0.001"),
            "inches": Decimal("0.0254"),
        }
        for target, source_field in assignments.items():
            measurement = original[source_field]
            expected = float(
                Decimal(str(measurement.value)) * factors[measurement.unit]
            )
            if getattr(self, target) != expected:
                raise ValueError("Incorrect dimension conversion.")
        return self


class QualifiedText(_Frozen):
    value: Text
    origin: Literal["source_verified"]
    source_field: Text
    evidence_urls: tuple[EvidenceURL, ...] = Field(min_length=1)

    @field_validator("evidence_urls")
    @classmethod
    def public_evidence(cls, values):
        return LegalProvenance.public_evidence(values)


class SearchMetadata(_Frozen):
    reviewed_name: Text
    evidence_urls: tuple[EvidenceURL, ...] = Field(min_length=1)
    aliases: tuple[Text, ...] = Field(min_length=1)
    usage_tags: tuple[Text, ...] = Field(min_length=1)
    description: QualifiedText | None
    materials: tuple[QualifiedText, ...] | None
    colors: tuple[QualifiedText, ...] | None
    styles: tuple[QualifiedText, ...] | None

    @field_validator("evidence_urls")
    @classmethod
    def public_evidence(cls, values):
        return LegalProvenance.public_evidence(values)

    @field_validator("aliases", "usage_tags")
    @classmethod
    def unique_terms(cls, values):
        if len(set(v.casefold() for v in values)) != len(values):
            raise ValueError("Duplicate search terms.")
        return values

    @field_validator("materials", "colors", "styles")
    @classmethod
    def explicit_unknown(cls, values):
        if values == ():
            raise ValueError("Unknown attributes must be null.")
        return values

    @model_validator(mode="after")
    def attributes_have_independent_fields(self) -> Self:
        for name, source_field in (
            ("materials", "material"),
            ("colors", "color"),
            ("styles", "style"),
        ):
            values = getattr(self, name)
            if values is not None and any(
                v.source_field != source_field for v in values
            ):
                raise ValueError("Attributes require their own reviewed source field.")
        return self


class SourceConventions(_Frozen):
    status: Literal["source_reported_uninspected"]
    units: Literal["meters"]
    up: Literal["+Y"]
    front: Literal["+Z"]
    floor_anchor: Text
    evidence_url: EvidenceURL

    @field_validator("evidence_url")
    @classmethod
    def public_evidence(cls, value):
        return _https(value)


class RenderQualification(_Frozen):
    """08B cannot assert render approval; 08C must introduce its evidence contract."""

    status: Literal["not_evaluated"]
    model_asset_id: None
    model_sha256: None
    verified_bounds: None
    verified_orientation: None
    verified_anchor: None
    local_glb_path: None


class FurnitureAssetRecord(_Frozen):
    asset_id: Text
    asset_version: Version
    qualification: Literal["metadata_qualified"]
    category: Literal["chair", "storage"]
    subtype: Literal["armchair", "bookcase"]
    variant_label: Text
    rotation_deg: StrictInt = Field(ge=0, le=0)
    source: SourceProvenance
    dimensions: PhysicalDimensions
    legal: LegalProvenance
    search: SearchMetadata
    source_conventions: SourceConventions
    rendering: RenderQualification

    @model_validator(mode="after")
    def qualification_agrees(self) -> Self:
        rules = {
            "CHAIR": ("chair", "armchair", {"armchair", "accent chair"}, {"seating"}),
            "SHELF": (
                "storage",
                "bookcase",
                {"bookcase", "bookshelf"},
                {"book storage"},
            ),
        }
        category, subtype, aliases, uses = rules[self.source.original_category]
        if (
            self.asset_id != self.source.qualification_candidate_id
            or self.variant_label != self.source.variant_label
            or (self.category, self.subtype) != (category, subtype)
            or not set(self.search.aliases) <= aliases
            or not set(self.search.usage_tags) <= uses
            or self.source.metadata_url not in self.dimensions.evidence_urls
            or self.source.metadata_url not in self.search.evidence_urls
            or {a.target: a.source_field for a in self.dimensions.axis_map}
            != {"width_m": "width", "depth_m": "length", "height_m": "height"}
        ):
            raise ValueError("Inconsistent product qualification evidence.")
        return self

    @property
    def render_qualified(self) -> bool:
        return False

    def search_document(self) -> str:
        """Stable reviewed text; never promotes marketing titles into attributes."""
        parts = [
            ("Name", self.search.reviewed_name),
            ("Category", self.category),
            ("Type", self.subtype),
            ("Aliases", "; ".join(sorted(self.search.aliases))),
            ("Usage", "; ".join(sorted(self.search.usage_tags))),
            ("Variant", self.variant_label),
            ("Asset ID", self.asset_id),
            ("Product ID", self.source.product_id),
            ("Source model ID", self.source.model_id),
        ]
        if self.search.description is not None:
            parts.append(("Description", self.search.description.value))
        for name in ("materials", "colors", "styles"):
            values = getattr(self.search, name)
            if values is not None:
                parts.append(
                    (name.capitalize(), "; ".join(sorted(v.value for v in values)))
                )
        return "\n".join(f"{name}: {value}" for name, value in parts)

    @property
    def search_document_sha256(self) -> str:
        return hashlib.sha256(self.search_document().encode("utf-8")).hexdigest()


class FurnitureCatalog(_Frozen):
    schema_version: StrictInt = Field(ge=1, le=1)
    catalog_id: Literal["archimind-furniture"]
    catalog_version: Version
    search_document_version: StrictInt = Field(ge=1, le=1)
    records: tuple[FurnitureAssetRecord, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_records(self) -> Self:
        ids = [record.asset_id for record in self.records]
        identities = [
            (r.source.product_id, r.source.marketplace_domain, r.variant_label)
            for r in self.records
        ]
        if (
            ids != sorted(ids)
            or len(ids) != len(set(ids))
            or len(set(identities)) != len(ids)
        ):
            raise ValueError("Duplicate or unordered catalog identities.")
        return self

    def get_record(self, asset_id: str) -> FurnitureAssetRecord:
        for record in self.records:
            if type(asset_id) is str and record.asset_id == asset_id:
                return record
        raise CatalogError("Catalog asset was not found.")


def load_catalog() -> FurnitureCatalog:
    """Load the fixed package resource, never a caller-supplied path or URL."""
    try:
        data = (
            resources.files("archimind.assets")
            .joinpath("furniture_catalog.json")
            .read_bytes()
        )
        if not 0 < len(data) <= MAX_CATALOG_BYTES:
            raise CatalogError("Invalid catalog size.")
        return FurnitureCatalog.model_validate_json(data)
    except (OSError, ValueError, TypeError, RecursionError):
        raise CatalogError("Furniture catalog is unavailable or invalid.") from None


def furniture_from_catalog(
    asset_id: str, *, furniture_id: str, name: str, x_m: float, y_m: float
) -> Furniture:
    """Create a fresh southwest-anchored specification; no room-fit assertion."""
    record = load_catalog().get_record(asset_id)
    try:
        return Furniture(
            id=furniture_id,
            name=name,
            category=record.category,
            x_m=x_m,
            y_m=y_m,
            width_m=record.dimensions.width_m,
            depth_m=record.dimensions.depth_m,
            height_m=record.dimensions.height_m,
            rotation_deg=0,
        )
    except ValidationError:
        raise CatalogError("Invalid catalog furniture specification.") from None
