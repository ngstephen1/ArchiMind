"""Typed experimental scene envelope; architectural data stays in RoomDesign."""

from types import MappingProxyType
from typing import Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archimind.models import RoomDesign
from archimind.render import realistic_viewer

AssetIdentifier = Literal["sheen-chair"]
MAX_SCENE_FURNITURE = 24
MAX_SCENE_OPENINGS = 128


class AssetDefinition(BaseModel):
    """Trusted catalog metadata, not a user-selectable path or URL."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    asset_id: AssetIdentifier
    category: Literal["chair"] = "chair"
    native_up: Literal["+Y"] = "+Y"
    native_front: Literal["+Z"] = "+Z"


ASSET_CATALOG = MappingProxyType(
    {"sheen-chair": AssetDefinition(asset_id="sheen-chair")}
)


class FurnitureAssetBinding(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    furniture_id: str = Field(min_length=1, max_length=256, pattern=r"\S")
    asset_id: AssetIdentifier | None = None


class ArchitecturalScene(BaseModel):
    """Versioned renderer contract; canonical models are reused, never redefined.

    Missing asset IDs produce explicit procedural placeholders. Unsupported
    rotations fail closed. These are rendering limits, not spatial validation.
    Door elevation is zero; window elevation is canonical sill_height_m.
    """

    model_config = ConfigDict(
        strict=True, extra="forbid", revalidate_instances="always"
    )
    schema_version: Literal[2] = 2
    design: RoomDesign
    asset_bindings: list[FurnitureAssetBinding] = Field(max_length=MAX_SCENE_FURNITURE)
    unavailable_assets: list[AssetIdentifier] = Field(
        default_factory=list, max_length=1
    )

    @model_validator(mode="after")
    def validate_render_contract(self) -> Self:
        room = self.design.room
        if self.design.name and len(self.design.name) > 256:
            raise ValueError("Scene name exceeds 256 characters")
        if len(self.design.furniture) > MAX_SCENE_FURNITURE:
            raise ValueError("Experimental room supports at most 24 furniture objects")
        if len(room.doors) + len(room.windows) > MAX_SCENE_OPENINGS:
            raise ValueError("Experimental room supports at most 128 openings")
        if any(
            not 0.1 <= value <= 20
            for value in (room.width_m, room.depth_m, room.ceiling_height_m)
        ):
            raise ValueError("Room rendering dimensions must be between 0.1 and 20 m")
        furniture = {item.id: item for item in self.design.furniture}
        ids = [binding.furniture_id for binding in self.asset_bindings]
        if len(ids) != len(set(ids)) or set(ids) != set(furniture):
            raise ValueError("Asset bindings must match furniture IDs exactly once")
        for item in furniture.values():
            if item.rotation_deg != 0:
                raise ValueError("Experimental room supports only rotation 0")
            if (
                any(
                    not 0.05 <= value <= 10
                    for value in (item.width_m, item.depth_m, item.height_m)
                )
                or max(abs(item.x_m), abs(item.y_m)) > 20
            ):
                raise ValueError("Furniture rendering limits exceeded")
        for item in [room, *room.doors, *room.windows, *furniture.values()]:
            for field in ("id", "name", "category"):
                if len(getattr(item, field, "")) > 256:
                    raise ValueError("Scene labels exceed 256 characters")
        for binding in self.asset_bindings:
            if (
                binding.asset_id
                and furniture[binding.furniture_id].category
                != ASSET_CATALOG[binding.asset_id].category
            ):
                raise ValueError("Asset category does not match furniture category")
        assigned = {b.asset_id for b in self.asset_bindings if b.asset_id}
        if (
            len(set(self.unavailable_assets)) != len(self.unavailable_assets)
            or not set(self.unavailable_assets) <= assigned
        ):
            raise ValueError("Unavailable assets must be unique assigned IDs")
        return self


def scene_payload(
    design: RoomDesign,
    *,
    asset_bindings: Mapping[str, AssetIdentifier | None] | None = None,
) -> dict:
    """Build deterministic JSON without transforming coordinates or mutating input."""
    design = RoomDesign.model_validate(design)
    bindings = {
        item.id: "sheen-chair" if item.category == "chair" else None
        for item in design.furniture
    }
    if asset_bindings is not None:
        if not set(asset_bindings) <= set(bindings):
            raise ValueError("Asset binding references unknown furniture")
        bindings.update(asset_bindings)
    scene = ArchitecturalScene(
        design=design,
        asset_bindings=[
            FurnitureAssetBinding(furniture_id=key, asset_id=value)
            for key, value in sorted(bindings.items())
        ],
    )
    return scene.model_dump(mode="json")


def render_realistic_scene(
    design: RoomDesign,
    *,
    asset_bindings: Mapping[str, AssetIdentifier | None] | None = None,
    key: str = "experimental-room",
) -> None:
    """Mount the shared V2 component; known asset failures become labeled placeholders."""
    payload = scene_payload(design, asset_bindings=asset_bindings)
    if any(binding["asset_id"] for binding in payload["asset_bindings"]):
        try:
            realistic_viewer.verify_asset()
        except realistic_viewer.ViewerAssetError:
            payload["unavailable_assets"] = ["sheen-chair"]
    realistic_viewer._component()(data=payload, key=key)
