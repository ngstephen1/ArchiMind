"""Pure catalog selection and reviewable inputs; no generation or spatial checks."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

from archimind.assets.catalog import (
    FurnitureAssetRecord,
    furniture_from_catalog,
    load_catalog,
)
from archimind.assets.planning_envelopes import (
    PlanningDimensions,
    PlanningFurnitureBinding,
    furniture_from_planning_envelope,
    load_planning_envelope,
)
from archimind.models import Furniture, RoomDesign

CHARLES_ID = "abo-b075x2x4xs-amazon-com"
BOOKCASE_ID = "abo-b07pqs58xn-amazon-com"


class SpecificationError(ValueError):
    """Sanitized preparation failure; never contains provider or filesystem details."""


def fingerprint(value: BaseModel | dict | str) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class _Frozen(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class CatalogProductOption(_Frozen):
    record: FurnitureAssetRecord
    catalog_id: str
    catalog_version: str
    record_digest: str
    planning_dimensions: PlanningDimensions | None
    planning_digest: str | None
    render_qualified: bool
    render_release_digest: str | None
    preparation_available: bool


class ProductAssignment(_Frozen):
    furniture_id: str
    furniture_name: str
    category: Literal["chair", "storage", "desk", "wardrobe", "table"]
    asset_id: str
    asset_version: str
    catalog_id: str
    catalog_version: str
    record_digest: str
    product_id: str
    variant: str
    reviewed_name: str
    source_url: str
    license_id: str
    license_url: str
    dimension_basis: Literal["planning_envelope_B", "published_item_dimensions"]
    dimensions: PlanningDimensions

    def validate_furniture(self, item: Furniture) -> None:
        if (
            item.id,
            item.name,
            item.category,
            item.width_m,
            item.depth_m,
            item.height_m,
            item.rotation_deg,
        ) != (
            self.furniture_id,
            self.furniture_name,
            self.category,
            *self.dimensions.wdh,
            0,
        ):
            raise SpecificationError("Product assignment does not match furniture.")


class PreparedCatalogSpecification(_Frozen):
    source_specification_json: str
    retained_manual_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    assignments: tuple[ProductAssignment, ...]
    planning_bindings: tuple[PlanningFurnitureBinding, ...]
    base_fingerprint: str
    evidence_fingerprint: str
    input_fingerprint: str

    def design(self) -> RoomDesign:
        """Return a fresh input, never an authoritative selected candidate."""
        return RoomDesign.model_validate_json(self.source_specification_json)


def catalog_product_options(
    *, catalog_version: str | None = None
) -> tuple[CatalogProductOption, ...]:
    """Read fixed packaged evidence; unknown planning/render evidence stays unavailable."""
    from archimind.assets.render_assets import product_release

    catalog = load_catalog(version=catalog_version)
    options = []
    for record in catalog.records:
        dimensions, planning_digest, release_digest = None, None, None
        if record.asset_id == CHARLES_ID:
            try:
                envelope = load_planning_envelope(record.asset_id)
                dimensions = envelope.planning_dimensions
                planning_digest = envelope.metadata_sha256
            except (ValueError, OSError):
                pass
            try:
                release = product_release()
                if (
                    release.asset_id == record.asset_id
                    and release.envelope_sha256 == planning_digest
                ):
                    release_digest = fingerprint(release)
            except (ValueError, OSError):
                pass
        options.append(
            CatalogProductOption(
                record=record,
                catalog_id=catalog.catalog_id,
                catalog_version=catalog.catalog_version,
                record_digest=fingerprint(record),
                planning_dimensions=dimensions,
                planning_digest=planning_digest,
                render_qualified=release_digest is not None,
                render_release_digest=release_digest,
                preparation_available=(
                    dimensions is not None
                    if record.asset_id == CHARLES_ID
                    else record.qualification == "metadata_qualified"
                ),
            )
        )
    return tuple(options)


def _unique_ids(values) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise SpecificationError("Invalid selection.")
    items = tuple(values)
    if any(type(v) is not str for v in items) or len(set(items)) != len(items):
        raise SpecificationError("Unknown or duplicate selection.")
    return tuple(sorted(items))


def prepare_catalog_specification(
    base_design: RoomDesign, *, retained_manual_ids, product_ids
) -> PreparedCatalogSpecification:
    """Prepare immutable, explicitly reviewable input. Positions are not validated."""
    try:
        base = RoomDesign.model_validate(base_design)
        if any(f.rotation_deg != 0 for f in base.furniture):
            raise SpecificationError("Preparation supports rotation zero only.")
        retained, products = _unique_ids(retained_manual_ids), _unique_ids(product_ids)
        options = catalog_product_options()
        by_id = {o.record.asset_id: o for o in options}
        manual = {f.id: f for f in base.furniture}
        if not set(retained) <= manual.keys() or not set(products) <= by_id.keys():
            raise SpecificationError("Unknown selection.")
        furniture = [
            f.model_copy(deep=True) for f in base.furniture if f.id in retained
        ]
        assignments, proofs = [], []
        for asset_id in products:
            option = by_id[asset_id]
            if not option.preparation_available:
                raise SpecificationError(
                    "Required product planning evidence is unavailable."
                )
            record = option.record
            fid = f"catalog:{asset_id}:1"
            if fid in manual:
                raise SpecificationError(
                    "Catalog furniture identifier collides with an existing item."
                )
            name = f"{record.subtype.capitalize()} ({record.variant_label})"
            args = dict(furniture_id=fid, name=name, x_m=0.0, y_m=0.0)
            if asset_id == CHARLES_ID:
                item, proof = furniture_from_planning_envelope(asset_id, **args)
                proofs.append(proof)
                basis = "planning_envelope_B"
            else:
                item = furniture_from_catalog(asset_id, **args)
                basis = "published_item_dimensions"
            furniture.append(item)
            assignments.append(
                ProductAssignment(
                    furniture_id=fid,
                    furniture_name=name,
                    category=record.category,
                    asset_id=asset_id,
                    asset_version=record.asset_version,
                    catalog_id=option.catalog_id,
                    catalog_version=option.catalog_version,
                    record_digest=option.record_digest,
                    product_id=record.source.product_id,
                    variant=record.variant_label,
                    reviewed_name=record.search.reviewed_name,
                    source_url=record.source.metadata_url,
                    license_id=record.legal.license_id,
                    license_url=record.legal.license_url,
                    dimension_basis=basis,
                    dimensions=PlanningDimensions(
                        width_m=item.width_m,
                        depth_m=item.depth_m,
                        height_m=item.height_m,
                    ),
                )
            )
        design = RoomDesign(
            name=base.name, room=base.room.model_copy(deep=True), furniture=furniture
        )
        return PreparedCatalogSpecification(
            source_specification_json=design.model_dump_json(),
            retained_manual_ids=retained,
            product_ids=products,
            assignments=tuple(assignments),
            planning_bindings=tuple(proofs),
            base_fingerprint=fingerprint(base),
            evidence_fingerprint=fingerprint(
                {"options": [o.model_dump(mode="json") for o in options]}
            ),
            input_fingerprint=fingerprint(design),
        )
    except SpecificationError:
        raise
    except (ValueError, TypeError, OSError, RecursionError):
        raise SpecificationError(
            "Catalog specification could not be prepared."
        ) from None


def specification_is_current(
    prepared: PreparedCatalogSpecification,
    base_design: RoomDesign,
    *,
    retained_manual_ids,
    product_ids,
) -> bool:
    """Recheck schema/evidence only, without running the layout/spatial engines."""
    try:
        fresh = prepare_catalog_specification(
            base_design,
            retained_manual_ids=retained_manual_ids,
            product_ids=product_ids,
        )
        return type(prepared) is PreparedCatalogSpecification and fresh == prepared
    except (ValueError, TypeError, OSError):
        return False
