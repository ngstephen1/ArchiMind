"""Typed contract for style packs and released assets.

Field names are shared with the browser loader (``frontend/realistic_viewer/
src/style_pack.js``): ``surfaces.<role>.{asset_id, tiling_m, fallback_color}``,
``lighting.{environment_asset_id, environment_intensity, exposure, sun, fill}``
and release ``files[].{role, tier, sha256, ext, bytes}``.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

StyleId = Literal[
    "modern_classic", "industrial_loft", "scandinavian", "japandi", "mid_century"
]
STYLE_IDS: tuple[str, ...] = StyleId.__args__
SurfaceRole = Literal[
    "floor",
    "wall",
    "ceiling",
    "trim",
    "door",
    "window_frame",
    "worktop",
    "tile",
    "metal",
]
SURFACE_ROLES: tuple[str, ...] = SurfaceRole.__args__
FurnitureCategory = Literal[
    "bed", "sofa", "table", "desk", "chair", "storage", "armchair", "lamp"
]

Hex = Annotated[str, StringConstraints(pattern=r"^#[0-9a-f]{6}$")]
AssetId = Annotated[
    str,
    StringConstraints(
        pattern=r"^(polyhaven|ambientcg|designer):[A-Za-z0-9_.@-]+$", max_length=128
    ),
]
SemVer = Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Metres = Annotated[float, Field(gt=0, le=10)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SurfaceSpec(_Strict):
    asset_id: AssetId
    tiling_m: Metres
    fallback_color: Hex
    # Multiplies a released texture (brass from brushed steel, painted trim).
    tint: Hex | None = None


class FurnitureChoice(_Strict):
    asset_id: AssetId
    width_m: Metres
    depth_m: Metres
    height_m: Metres


class DecorRules(_Strict):
    """Which dressing kinds a pack uses and the asset for each (None = procedural)."""

    rug: AssetId | None
    art: AssetId | None
    curtain: AssetId | None
    pendant: AssetId | None
    plant: AssetId | None
    floor_lamp: AssetId | None
    mouldings: bool
    accents: tuple[FurnitureChoice, ...] = Field(max_length=6)


class Sun(_Strict):
    direction: tuple[float, float, float]
    intensity: Annotated[float, Field(ge=0, le=10)]
    kelvin: Annotated[int, Field(ge=1800, le=12000)]


class Fill(_Strict):
    sky_color: Hex
    ground_color: Hex
    intensity: Annotated[float, Field(ge=0, le=5)]


class Lighting(_Strict):
    environment_asset_id: AssetId | None
    environment_intensity: Annotated[float, Field(ge=0, le=3)]
    exposure: Annotated[float, Field(gt=0, le=4)]
    sun: Sun
    fill: Fill


class PlanTheme(_Strict):
    wall_fill: Hex
    wall_stroke: Hex
    floor_fill: Hex
    furniture_fill: Hex
    furniture_stroke: Hex
    label_color: Hex
    door_color: Hex
    window_color: Hex


class TierQuality(_Strict):
    texture_px: Literal[1024, 2048]
    decor_density: Annotated[float, Field(gt=0, le=1)]


class Quality(_Strict):
    high: TierQuality
    low: TierQuality


class StylePack(_Strict):
    id: StyleId
    version: SemVer
    name: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    aliases: tuple[
        Annotated[str, StringConstraints(pattern=r"^[a-z][a-z -]*[a-z]$")], ...
    ] = Field(min_length=1, max_length=16)
    surfaces: dict[SurfaceRole, SurfaceSpec]
    furniture: dict[FurnitureCategory, tuple[FurnitureChoice, ...]]
    decor: DecorRules
    lighting: Lighting
    plan_theme: PlanTheme
    quality: Quality

    def asset_ids(self) -> tuple[str, ...]:
        """Every asset this pack references, in a stable order, without duplicates."""
        ids = [s.asset_id for s in self.surfaces.values()]
        ids += [c.asset_id for choices in self.furniture.values() for c in choices]
        decor = self.decor
        ids += [
            a
            for a in (
                decor.rug,
                decor.art,
                decor.curtain,
                decor.pendant,
                decor.plant,
                decor.floor_lamp,
            )
            if a
        ]
        ids += [c.asset_id for c in decor.accents]
        if self.lighting.environment_asset_id:
            ids.append(self.lighting.environment_asset_id)
        return tuple(dict.fromkeys(ids))


class AssetFile(_Strict):
    role: Literal["diffuse", "normal", "roughness", "ao", "metalness", "hdr", "model"]
    tier: Literal["low", "high", "both"]
    sha256: Sha256
    ext: Literal["webp", "jpg", "png", "hdr", "glb"]
    bytes: Annotated[int, Field(gt=0, le=15 * 1024 * 1024)]
    width_px: Annotated[int, Field(gt=0, le=2048)] | None = None
    height_px: Annotated[int, Field(gt=0, le=2048)] | None = None


class AssetRelease(_Strict):
    asset_id: AssetId
    kind: Literal["material", "environment", "model"]
    license: Literal["CC0-1.0", "original-blender"]
    source_url: Annotated[str, StringConstraints(pattern=r"^https://", max_length=300)]
    upstream_checksum: Annotated[str, StringConstraints(max_length=128)] | None
    files: tuple[AssetFile, ...] = Field(min_length=1, max_length=16)
