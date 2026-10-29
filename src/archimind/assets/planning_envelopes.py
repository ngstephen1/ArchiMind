"""Policy B metadata for fresh specifications, independent of render approval.

Only reviewed receipt digests are trusted. A source hash in metadata binds to
historically inspected bytes; it does not verify a currently available GLB.
No file acquisition, model scaling, geometry checks or generation occurs here.
"""

import hashlib
import itertools
import json
import math
from fractions import Fraction
from importlib import resources
from typing import Literal, NamedTuple, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictInt,
    field_validator,
    model_validator,
)

from archimind.assets.catalog import (
    SHA256,
    CatalogError,
    PhysicalDimensions,
    ProductId,
    Text,
    Version,
    load_catalog,
)
from archimind.assets.inspection import AssetInspection
from archimind.models import Furniture

POLICY_ID = "archimind-conservative-planning-envelope"
POLICY_VERSION = "1.0.0"
OWNER_DECISION_SHA256 = (
    "cca6bcd209c2859dd461dcc565d5e8e2886dc96717c825e7ff08f660e8ae0ff7"
)
_RECEIPT_ID = "08C:charles:2026-10-28:inspection-v1"
_INSPECTION_SHA256 = "3ab3b103e8cbaa4b93cd05b825d0a5d4ab819cd62e12b2e5b253aa07c479fd5d"
_REPORT_SHA256 = "76572768405747a5a29b62a762ef69c5d991e8375fba24e415197471b2d727ac"
Vector = tuple[FiniteFloat, FiniteFloat, FiniteFloat]


class PlanningEnvelopeError(ValueError):
    """Sanitized, typed rejection at public qualification/loading/factory APIs."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PlanningEnvelopeError("invalid_metadata")
        result[key] = value
    return result


def _nonfinite(value):
    raise PlanningEnvelopeError("invalid_metadata")


class _Frozen(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @classmethod
    def model_validate_json(cls, json_data, **kwargs):
        try:
            json.loads(json_data, object_pairs_hook=_unique, parse_constant=_nonfinite)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            raise PlanningEnvelopeError("invalid_metadata") from None
        return super().model_validate_json(json_data, **kwargs)


class PlanningDimensions(_Frozen):
    """Metric geometric extents; these fields do not assert product measurements."""

    width_m: FiniteFloat = Field(gt=0)
    depth_m: FiniteFloat = Field(gt=0)
    height_m: FiniteFloat = Field(gt=0)

    @property
    def wdh(self) -> tuple[float, float, float]:
        return self.width_m, self.depth_m, self.height_m


class PlanningEnvelopeEvidence(_Frozen):
    inspection_receipt_id: Text
    inspection_receipt_sha256: SHA256
    qualification_report_sha256: SHA256
    source_glb_sha256: SHA256
    source_hash_basis: Literal["received_bytes_sha256_in_08C"]
    inspection: AssetInspection

    @model_validator(mode="after")
    def reviewed_evidence_only(self) -> Self:
        # Explicit release trust anchor, not a user-supplied assertion of approval.
        # Adding a receipt requires a reviewed new qualification/release.
        if (
            self.inspection_receipt_id != _RECEIPT_ID
            or self.inspection_receipt_sha256 != _INSPECTION_SHA256
            or self.qualification_report_sha256 != _REPORT_SHA256
            or _digest(self.inspection.model_dump(mode="json")) != _INSPECTION_SHA256
            or self.source_glb_sha256 != self.inspection.original_sha256
            or not self.inspection.expected_hash_checked
        ):
            raise ValueError("Unreviewed or mismatched inspection evidence.")
        return self


class PlanningEnvelopeQualification(_Frozen):
    status: Literal["planning_approved"]
    policy_id: Literal["archimind-conservative-planning-envelope"]
    policy_version: Literal["1.0.0"]
    owner_decision_id: Literal["08C-R1-policy-B"]
    owner_decision_sha256: Literal[
        "cca6bcd209c2859dd461dcc565d5e8e2886dc96717c825e7ff08f660e8ae0ff7"
    ]
    scope: Literal["fresh_backend_specifications_only"]
    orientation_evidence: Literal["08C_numeric_axes_and_source_front_convention"]
    natural_front_visually_verified: Literal[False]
    functional_clearance_evaluated: Literal[False]
    render_qualified: Literal[False]

    @field_validator(
        "natural_front_visually_verified",
        "functional_clearance_evaluated",
        "render_qualified",
        mode="before",
    )
    @classmethod
    def explicit_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError("Qualification flags require explicit booleans.")
        return value


class PlanningEnvelopePlacement(_Frozen):
    """Native glTF -> normalized Three -> object-local canonical coordinates.

    Identity orientation/scale. Translate the complete mesh to center X/Z and
    floor Y=0, then place at (W/2, 0, -D/2) in Three coordinates. Canonical
    (X,Y,Z) = (three_X, -three_Z, three_Y). Room position is supplied later by
    the canonical Furniture, never a cached independent placement object.
    """

    units: Literal["meters"]
    native_up: Literal["+Y"]
    native_front: Literal["+Z"]
    canonical_mapping: Literal["X,-Z,Y"]
    anchor: Literal["floor_center"]
    furniture_yaw_deg: StrictInt = Field(ge=0, le=0)
    scale_xyz: Vector
    normalization_translation_three_m: Vector
    envelope_origin_offset_three_m: Vector

    @model_validator(mode="after")
    def native_scale_only(self) -> Self:
        if self.scale_xyz != (1.0, 1.0, 1.0):
            raise ValueError("Policy B requires native scale.")
        return self


def _fraction(value: float) -> Fraction:
    return Fraction.from_float(value)


def _outward(value: Fraction) -> float:
    """Smallest nearby binary64 covering both exact and decimal-meter inputs.

    The geometry engine uses Fraction(str(dimension)); render consumers use
    binary64 JSON numbers. Neither representation may round below the minimum.
    This adds at most adjacent float steps, never a percentage or clearance.
    """
    result = float(value)
    for _ in range(3):
        if not math.isfinite(result) or result <= 0:
            break
        if _fraction(result) >= value and Fraction(str(result)) >= value:
            return result
        result = math.nextafter(result, math.inf)
    raise ValueError("Unsupported envelope numeric range.")


def _translated_bounds(
    inspection: AssetInspection, placement: PlanningEnvelopePlacement
):
    native = inspection.native_bounds_three
    low, high = (
        tuple(map(_fraction, native.min_xyz)),
        tuple(map(_fraction, native.max_xyz)),
    )
    if any(a >= b for a, b in zip(low, high)):
        raise ValueError("Degenerate native bounds.")
    expected = tuple(
        float(-(a + b) / 2) if i != 1 else float(-a)
        for i, (a, b) in enumerate(zip(low, high))
    )
    if placement.normalization_translation_three_m != expected:
        raise ValueError("Ambiguous or incorrect floor/center anchor.")
    t = tuple(map(_fraction, placement.normalization_translation_three_m))
    translated_low = tuple(a + b for a, b in zip(low, t))
    translated_high = tuple(a + b for a, b in zip(high, t))
    normalized = inspection.normalized_bounds_three
    if (
        translated_low[1] != 0
        or placement.normalization_translation_three_m
        != inspection.normalization_translation_three
        or any(_fraction(a) > b for a, b in zip(normalized.min_xyz, translated_low))
        or any(_fraction(a) < b for a, b in zip(normalized.max_xyz, translated_high))
    ):
        raise ValueError("Normalized bounds do not enclose the anchored native mesh.")
    return translated_low, translated_high


def _minimum_dimensions(
    published: PhysicalDimensions,
    inspection: AssetInspection,
    placement: PlanningEnvelopePlacement,
) -> PlanningDimensions:
    low, high = _translated_bounds(inspection, placement)
    native = inspection.native_bounds_three
    native_sizes = tuple(
        _fraction(b) - _fraction(a) for a, b in zip(native.min_xyz, native.max_xyz)
    )
    required = (
        max(
            Fraction(str(published.width_m)),
            native_sizes[0],
            2 * abs(low[0]),
            2 * abs(high[0]),
        ),
        max(
            Fraction(str(published.depth_m)),
            native_sizes[2],
            2 * abs(low[2]),
            2 * abs(high[2]),
        ),
        max(Fraction(str(published.height_m)), native_sizes[1], high[1]),
    )
    return PlanningDimensions(
        **dict(zip(("width_m", "depth_m", "height_m"), map(_outward, required)))
    )


class PlanningEnvelope(_Frozen):
    schema_version: StrictInt = Field(ge=1, le=1)
    envelope_id: Text
    envelope_version: Literal["1.0.0"]
    catalog_id: Literal["archimind-furniture"]
    catalog_schema_version: StrictInt = Field(ge=1, le=1)
    catalog_version: Version
    catalog_record_sha256: SHA256
    asset_id: Text
    asset_version: Version
    product_id: ProductId
    model_id: ProductId
    variant_id: ProductId
    variant_label: Text
    published_dimensions: PhysicalDimensions
    evidence: PlanningEnvelopeEvidence
    qualification: PlanningEnvelopeQualification
    placement: PlanningEnvelopePlacement
    planning_dimensions: PlanningDimensions
    rounding_rule: Literal["outward_binary64_and_decimal_meters_v1"]
    metadata_sha256: SHA256

    @model_validator(mode="after")
    def conservative_and_current(self) -> Self:
        catalog = load_catalog(version=self.catalog_version)
        record = catalog.get_record(self.asset_id)
        # An old release proof survives only while the active record is identical.
        if load_catalog().get_record(self.asset_id) != record:
            raise ValueError("Planning evidence no longer matches active product.")
        inspection = self.evidence.inspection
        if (
            (self.catalog_id, self.catalog_schema_version, self.catalog_version)
            != (catalog.catalog_id, catalog.schema_version, catalog.catalog_version)
            or self.catalog_record_sha256 != _digest(record.model_dump(mode="json"))
            or self.asset_version != record.asset_version
            or (self.product_id, self.model_id, self.variant_id, self.variant_label)
            != (
                record.source.product_id,
                record.source.model_id,
                record.source.product_id,
                record.variant_label,
            )
            or self.envelope_id != f"{self.asset_id}:planning-envelope"
            or self.published_dimensions != record.dimensions
            or (
                inspection.asset_id,
                inspection.asset_version,
                inspection.source_product_id,
                inspection.source_model_id,
                inspection.source_model_url,
            )
            != (
                record.asset_id,
                record.asset_version,
                record.source.product_id,
                record.source.model_id,
                record.source.model_url,
            )
            or inspection.physical_dimensions_wdh_m
            != (
                record.dimensions.width_m,
                record.dimensions.depth_m,
                record.dimensions.height_m,
            )
        ):
            raise ValueError(
                "Catalog, product, variant or inspection binding mismatch."
            )
        minimum = _minimum_dimensions(
            self.published_dimensions, inspection, self.placement
        )
        w, d, h = self.planning_dimensions.wdh
        if (
            self.planning_dimensions != minimum
            or self.placement.envelope_origin_offset_three_m != (w / 2, 0.0, -d / 2)
        ):
            raise ValueError(
                "Envelope must use the exact outward minimum and fixed anchor."
            )
        low, high = _translated_bounds(inspection, self.placement)
        wf, df, hf = map(_fraction, (w, d, h))
        # Exact rational arithmetic on every AABB corner, with NO inward epsilon.
        for x, y, z in itertools.product(*zip(low, high)):
            canonical = (x + wf / 2, -z + df / 2, y)
            if any(a < 0 or a > b for a, b in zip(canonical, (wf, df, hf))):
                raise ValueError("Transformed mesh extends outside reserved volume.")
        if self.metadata_sha256 != _digest(
            self.model_dump(mode="json", exclude={"metadata_sha256"})
        ):
            raise ValueError("Envelope metadata digest mismatch.")
        return self

    @property
    def measured_mesh_dimensions(self) -> PlanningDimensions:
        low, high = (
            self.evidence.inspection.native_bounds_three.min_xyz,
            self.evidence.inspection.native_bounds_three.max_xyz,
        )
        return PlanningDimensions(
            width_m=high[0] - low[0],
            depth_m=high[2] - low[2],
            height_m=high[1] - low[1],
        )


def qualify_planning_envelope(
    asset_id: str, *, evidence: PlanningEnvelopeEvidence
) -> PlanningEnvelope:
    """Rebuild from explicitly trusted historical evidence; never inspect a file.

    Approval covers this static, zero-yaw planning volume only. Room validity,
    functional use, natural-front appearance and render approval remain separate.
    """
    try:
        evidence = PlanningEnvelopeEvidence.model_validate(evidence)
        # Existing owner-approved Policy B evidence belongs to release 1.0.0.
        # New metadata cannot manufacture a planning qualification.
        catalog = load_catalog(version="1.0.0")
        record = catalog.get_record(asset_id)
        placement = PlanningEnvelopePlacement(
            units="meters",
            native_up="+Y",
            native_front="+Z",
            canonical_mapping="X,-Z,Y",
            anchor="floor_center",
            furniture_yaw_deg=0,
            scale_xyz=(1.0, 1.0, 1.0),
            normalization_translation_three_m=evidence.inspection.normalization_translation_three,
            envelope_origin_offset_three_m=(0.0, 0.0, 0.0),
        )
        dimensions = _minimum_dimensions(
            record.dimensions, evidence.inspection, placement
        )
        placement = placement.model_copy(
            update={
                "envelope_origin_offset_three_m": (
                    dimensions.width_m / 2,
                    0.0,
                    -dimensions.depth_m / 2,
                )
            }
        )
        data = dict(
            schema_version=1,
            envelope_id=f"{asset_id}:planning-envelope",
            envelope_version="1.0.0",
            catalog_id=catalog.catalog_id,
            catalog_schema_version=catalog.schema_version,
            catalog_version=catalog.catalog_version,
            catalog_record_sha256=_digest(record.model_dump(mode="json")),
            asset_id=record.asset_id,
            asset_version=record.asset_version,
            product_id=record.source.product_id,
            model_id=record.source.model_id,
            variant_id=record.source.product_id,
            variant_label=record.variant_label,
            published_dimensions=record.dimensions,
            evidence=evidence,
            placement=placement,
            planning_dimensions=dimensions,
            rounding_rule="outward_binary64_and_decimal_meters_v1",
            qualification=PlanningEnvelopeQualification(
                status="planning_approved",
                policy_id=POLICY_ID,
                policy_version=POLICY_VERSION,
                owner_decision_id="08C-R1-policy-B",
                owner_decision_sha256=OWNER_DECISION_SHA256,
                scope="fresh_backend_specifications_only",
                orientation_evidence="08C_numeric_axes_and_source_front_convention",
                natural_front_visually_verified=False,
                functional_clearance_evaluated=False,
                render_qualified=False,
            ),
        )
        serializable = {
            k: v.model_dump(mode="json") if isinstance(v, BaseModel) else v
            for k, v in data.items()
        }
        return PlanningEnvelope(**data, metadata_sha256=_digest(serializable))
    except (ValueError, TypeError, OverflowError, RecursionError, CatalogError):
        raise PlanningEnvelopeError("unqualified_envelope") from None


class PlanningEnvelopeLibrary(_Frozen):
    schema_version: StrictInt = Field(ge=1, le=1)
    envelopes: tuple[PlanningEnvelope, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_ordered_ids(self) -> Self:
        ids = [item.asset_id for item in self.envelopes]
        if ids != sorted(set(ids)):
            raise ValueError("Duplicate or unordered planning-envelope identities.")
        return self


def load_planning_envelope(asset_id: str) -> PlanningEnvelope:
    """Resolve a fixed packaged record; no caller path/URL or runtime GLB read."""
    try:
        resource = resources.files("archimind.assets").joinpath(
            "planning_envelopes.json"
        )
        with resource.open("rb") as stream:
            data = stream.read(512 * 1024 + 1)
        if not 0 < len(data) <= 512 * 1024:
            raise ValueError
        library = PlanningEnvelopeLibrary.model_validate_json(data)
    except (OSError, ValueError, TypeError, RecursionError):
        raise PlanningEnvelopeError("envelope_metadata_unavailable") from None
    for envelope in library.envelopes:
        if type(asset_id) is str and envelope.asset_id == asset_id:
            return envelope
    raise PlanningEnvelopeError("envelope_not_found")


class PlanningFurnitureBinding(_Frozen):
    """Immutable evidence paired with a fresh, mutable canonical Furniture.

    Position remains authoritative in the canonical object. An explicit future
    generation may place the item elsewhere while keeping its ID and geometry;
    this binding neither stores an independent pose nor approves that placement.
    """

    schema_version: StrictInt = Field(ge=1, le=1)
    furniture_id: str = Field(min_length=1, pattern=r"\S")
    furniture_name: str = Field(min_length=1, pattern=r"\S")
    category: Literal["chair", "storage"]
    canonical_dimensions: PlanningDimensions
    envelope: PlanningEnvelope
    metadata_sha256: SHA256

    @model_validator(mode="after")
    def preserve_reservation(self) -> Self:
        record = load_catalog().get_record(self.envelope.asset_id)
        if (
            self.canonical_dimensions != self.envelope.planning_dimensions
            or self.category != record.category
            or self.metadata_sha256
            != _digest(self.model_dump(mode="json", exclude={"metadata_sha256"}))
        ):
            raise ValueError("Binding geometry, category or digest mismatch.")
        return self

    def validate_furniture(self, furniture: Furniture) -> None:
        """Check current metadata/geometry correspondence, not spatial validity."""
        try:
            binding = type(self).model_validate(self)
            furniture = Furniture.model_validate(furniture)
            if (
                (furniture.id, furniture.name, furniture.category)
                != (binding.furniture_id, binding.furniture_name, binding.category)
                or (furniture.width_m, furniture.depth_m, furniture.height_m)
                != binding.canonical_dimensions.wdh
                or furniture.rotation_deg != 0
            ):
                raise ValueError
        except (ValueError, TypeError, RecursionError):
            raise PlanningEnvelopeError("furniture_binding_mismatch") from None


class PlanningFurnitureSpecification(NamedTuple):
    furniture: Furniture
    binding: PlanningFurnitureBinding


def furniture_from_planning_envelope(
    asset_id: str,
    *,
    furniture_id: str,
    name: str,
    x_m: float,
    y_m: float,
    rotation_deg: int = 0,
) -> PlanningFurnitureSpecification:
    """Explicitly propose a NEW envelope-sized item plus immutable evidence.

    Preserves supplied ID/name/position. Never updates an existing design, calls
    room validation or generation, reads a GLB, or grants rendering approval.
    """
    if type(rotation_deg) is not int or rotation_deg != 0:
        raise PlanningEnvelopeError("unsupported_yaw")
    try:
        envelope = load_planning_envelope(asset_id)
        record = load_catalog().get_record(asset_id)
        dimensions = envelope.planning_dimensions
        furniture = Furniture(
            id=furniture_id,
            name=name,
            category=record.category,
            x_m=x_m,
            y_m=y_m,
            width_m=dimensions.width_m,
            depth_m=dimensions.depth_m,
            height_m=dimensions.height_m,
            rotation_deg=0,
        )
        data = dict(
            schema_version=1,
            furniture_id=furniture.id,
            furniture_name=furniture.name,
            category=furniture.category,
            canonical_dimensions=dimensions,
            envelope=envelope,
        )
        raw = {
            k: v.model_dump(mode="json") if isinstance(v, BaseModel) else v
            for k, v in data.items()
        }
        binding = PlanningFurnitureBinding(**data, metadata_sha256=_digest(raw))
        binding.validate_furniture(furniture)
        return PlanningFurnitureSpecification(furniture=furniture, binding=binding)
    except PlanningEnvelopeError:
        raise
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise PlanningEnvelopeError("invalid_planning_specification") from None
