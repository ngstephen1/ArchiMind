"""V3 native-scale product demonstration; independent of generated A/B layouts."""

from typing import Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archimind.assets import load_planning_envelope
from archimind.assets.render_assets import product_release, verify_product_asset
from archimind.assets.render_qualification import CHARLES_ID, ProductQualificationError
from archimind.models import RoomDesign
from archimind.render.realistic_scene import ArchitecturalScene
from archimind.render.realistic_viewer import _component


class ProductBinding(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    furniture_id: str = Field(min_length=1, max_length=256)
    asset_id: Literal["abo-b075x2x4xs-amazon-com"] | None
    render_version: Literal["1.0.0"] | None
    envelope_sha256: str | None


class ProductScene(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )
    schema_version: Literal[3] = 3
    design: RoomDesign
    asset_bindings: list[ProductBinding] = Field(max_length=24)
    unavailable_assets: list[Literal["abo-b075x2x4xs-amazon-com"]] = Field(
        default_factory=list, max_length=1
    )

    @model_validator(mode="after")
    def trusted_product_only(self) -> Self:
        # Reuse all canonical structural/limit/coverage checks without assigning
        # the illustrative asset to a product. This does not run spatial checks.
        ArchitecturalScene.model_validate(
            {
                "schema_version": 2,
                "design": self.design,
                "asset_bindings": [
                    {"furniture_id": b.furniture_id, "asset_id": None}
                    for b in self.asset_bindings
                ],
                "unavailable_assets": [],
            }
        )
        furniture = {f.id: f for f in self.design.furniture}
        for b in self.asset_bindings:
            if b.asset_id is None:
                if b.render_version is not None or b.envelope_sha256 is not None:
                    raise ValueError("Placeholder cannot claim a product binding")
                continue
            release = product_release()
            e = load_planning_envelope(b.asset_id)
            f = furniture[b.furniture_id]
            if (
                b.render_version != release.render_version
                or b.envelope_sha256 != e.metadata_sha256
                or f.category != "chair"
                or (f.width_m, f.depth_m, f.height_m) != e.planning_dimensions.wdh
                or f.rotation_deg != 0
            ):
                raise ValueError("Stale or incompatible product binding")
        assigned = {b.asset_id for b in self.asset_bindings if b.asset_id}
        if (
            len(set(self.unavailable_assets)) != len(self.unavailable_assets)
            or not set(self.unavailable_assets) <= assigned
        ):
            raise ValueError("Invalid unavailable product IDs")
        return self


def product_scene_payload(
    design: RoomDesign, *, asset_bindings: Mapping[str, str | None]
) -> dict:
    """Explicit complete ID bindings only; no implicit category substitution."""
    has_products = any(asset_bindings.values())
    release = product_release() if has_products else None
    e = load_planning_envelope(CHARLES_ID) if has_products else None
    return ProductScene(
        design=design,
        asset_bindings=[
            ProductBinding(
                furniture_id=key,
                asset_id=value,
                render_version=release.render_version if value else None,
                envelope_sha256=e.metadata_sha256 if value else None,
            )
            for key, value in sorted(asset_bindings.items())
        ],
    ).model_dump(mode="json")


def render_product_scene(
    design: RoomDesign,
    *,
    asset_bindings: Mapping[str, str | None],
    key: str = "experimental-product-room",
) -> None:
    payload = product_scene_payload(design, asset_bindings=asset_bindings)
    mount_product_payload(payload, key=key)


def mount_product_payload(payload: dict, *, key: str) -> dict:
    """Shared trusted V3 mounting path, including integrity fallback.

    Return the effective payload so wrappers can report actual backend failures.
    No spatial validation or generation is performed here.
    """
    payload = ProductScene.model_validate(payload).model_dump(mode="json")
    if any(b["asset_id"] for b in payload["asset_bindings"]):
        try:
            verify_product_asset()
        except ProductQualificationError:
            payload["unavailable_assets"] = [CHARLES_ID]
    _component()(data=payload, key=key)
    return payload
