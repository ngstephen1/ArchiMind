"""Small immutable appearance catalog; no physical assets or performance data."""

from types import MappingProxyType
from typing import Literal

from pydantic import ConfigDict, Field

from archimind.agents.layout_schemas import Contract

ThemeId = Literal["scandinavian", "modern", "minimalist", "industrial", "neutral"]
PaletteId = Literal[
    "scandi_warm_sage",
    "modern_slate_blue",
    "minimalist_white",
    "industrial_charcoal",
    "neutral_sand",
]
MaterialId = Literal[
    "wall_warm_white",
    "wall_crisp_white",
    "wall_soft_gray",
    "wall_charcoal",
    "wall_sand",
    "floor_light_oak",
    "floor_pale_ash",
    "floor_concrete_gray",
    "floor_warm_stone",
    "finish_light_oak",
    "finish_walnut",
    "finish_matte_white",
    "finish_black_metal",
    "finish_natural_linen",
    "finish_gray_fabric",
]
AccentId = Literal[
    "muted_sage", "warm_taupe", "slate_blue", "terracotta", "charcoal", "ochre"
]


class _Entry(Contract):
    model_config = ConfigDict(frozen=True)


class MaterialSpec(_Entry):
    material_id: MaterialId
    label: str
    surface: Literal["wall", "floor", "furniture"]
    category: Literal[
        "paint_representation",
        "wood_representation",
        "stone_representation",
        "metal_representation",
        "fabric_representation",
    ]
    base_color_hex: str = Field(pattern=r"^#[0-9A-F]{6}$")
    future_mapping: Literal["flat_color_metadata"] = "flat_color_metadata"
    physical_asset_available: Literal[False] = False


class AccentSpec(_Entry):
    accent_id: AccentId
    label: str
    color_hex: str = Field(pattern=r"^#[0-9A-F]{6}$")
    future_mapping: Literal["flat_color_metadata"] = "flat_color_metadata"
    physical_asset_available: Literal[False] = False


class PaletteSpec(_Entry):
    palette_id: PaletteId
    theme_id: ThemeId
    label: str
    wall_material_ids: tuple[MaterialId, ...]
    floor_material_ids: tuple[MaterialId, ...]
    furniture_material_ids: tuple[MaterialId, ...]
    accent_ids: tuple[AccentId, ...]


class ThemeSpec(_Entry):
    theme_id: ThemeId
    label: str
    palette_ids: tuple[PaletteId, ...]


class StyleCatalog(_Entry):
    version: Literal["archimind_style_v1"] = "archimind_style_v1"
    themes: tuple[ThemeSpec, ...]
    palettes: tuple[PaletteSpec, ...]
    materials: tuple[MaterialSpec, ...]
    accents: tuple[AccentSpec, ...]


def _material(identifier, label, surface, category, color):
    return MaterialSpec(
        material_id=identifier,
        label=label,
        surface=surface,
        category=category,
        base_color_hex=color,
    )


MATERIALS = MappingProxyType(
    {
        entry.material_id: entry
        for entry in (
            _material(
                "wall_warm_white",
                "Warm white paint appearance",
                "wall",
                "paint_representation",
                "#F5F1E8",
            ),
            _material(
                "wall_crisp_white",
                "Crisp white paint appearance",
                "wall",
                "paint_representation",
                "#F6F6F4",
            ),
            _material(
                "wall_soft_gray",
                "Soft gray paint appearance",
                "wall",
                "paint_representation",
                "#D5D6D2",
            ),
            _material(
                "wall_charcoal",
                "Charcoal paint appearance",
                "wall",
                "paint_representation",
                "#4B4C4D",
            ),
            _material(
                "wall_sand",
                "Sand paint appearance",
                "wall",
                "paint_representation",
                "#E8DFD0",
            ),
            _material(
                "floor_light_oak",
                "Light oak floor representation",
                "floor",
                "wood_representation",
                "#D4B58C",
            ),
            _material(
                "floor_pale_ash",
                "Pale ash floor representation",
                "floor",
                "wood_representation",
                "#DED6C5",
            ),
            _material(
                "floor_concrete_gray",
                "Gray concrete floor representation",
                "floor",
                "stone_representation",
                "#A9AAA7",
            ),
            _material(
                "floor_warm_stone",
                "Warm stone floor representation",
                "floor",
                "stone_representation",
                "#C7BDAA",
            ),
            _material(
                "finish_light_oak",
                "Light oak furniture finish representation",
                "furniture",
                "wood_representation",
                "#CDB18A",
            ),
            _material(
                "finish_walnut",
                "Walnut furniture finish representation",
                "furniture",
                "wood_representation",
                "#765740",
            ),
            _material(
                "finish_matte_white",
                "Matte white furniture finish representation",
                "furniture",
                "paint_representation",
                "#EEEDE7",
            ),
            _material(
                "finish_black_metal",
                "Black metal furniture finish representation",
                "furniture",
                "metal_representation",
                "#353638",
            ),
            _material(
                "finish_natural_linen",
                "Natural linen furniture finish representation",
                "furniture",
                "fabric_representation",
                "#CBBFA7",
            ),
            _material(
                "finish_gray_fabric",
                "Gray fabric furniture finish representation",
                "furniture",
                "fabric_representation",
                "#8F9492",
            ),
        )
    }
)

ACCENTS = MappingProxyType(
    {
        identifier: AccentSpec(accent_id=identifier, label=label, color_hex=color)
        for identifier, label, color in (
            ("muted_sage", "Muted sage", "#9BAE98"),
            ("warm_taupe", "Warm taupe", "#B5A592"),
            ("slate_blue", "Slate blue", "#71889C"),
            ("terracotta", "Terracotta", "#B7735A"),
            ("charcoal", "Charcoal", "#404346"),
            ("ochre", "Ochre", "#BE984E"),
        )
    }
)

PALETTES = MappingProxyType(
    {
        entry.palette_id: entry
        for entry in (
            PaletteSpec(
                palette_id="scandi_warm_sage",
                theme_id="scandinavian",
                label="Warm white, light oak and sage",
                wall_material_ids=("wall_warm_white", "wall_soft_gray"),
                floor_material_ids=("floor_light_oak", "floor_pale_ash"),
                furniture_material_ids=(
                    "finish_light_oak",
                    "finish_matte_white",
                    "finish_natural_linen",
                ),
                accent_ids=("muted_sage", "warm_taupe", "charcoal"),
            ),
            PaletteSpec(
                palette_id="modern_slate_blue",
                theme_id="modern",
                label="White, walnut and slate blue",
                wall_material_ids=("wall_crisp_white", "wall_soft_gray"),
                floor_material_ids=("floor_pale_ash", "floor_concrete_gray"),
                furniture_material_ids=(
                    "finish_walnut",
                    "finish_matte_white",
                    "finish_black_metal",
                    "finish_gray_fabric",
                ),
                accent_ids=("slate_blue", "charcoal", "warm_taupe"),
            ),
            PaletteSpec(
                palette_id="minimalist_white",
                theme_id="minimalist",
                label="Restrained white and pale wood",
                wall_material_ids=("wall_crisp_white", "wall_warm_white"),
                floor_material_ids=("floor_pale_ash", "floor_light_oak"),
                furniture_material_ids=(
                    "finish_matte_white",
                    "finish_light_oak",
                    "finish_black_metal",
                ),
                accent_ids=("charcoal", "warm_taupe", "muted_sage"),
            ),
            PaletteSpec(
                palette_id="industrial_charcoal",
                theme_id="industrial",
                label="Gray, dark metal and walnut",
                wall_material_ids=("wall_soft_gray", "wall_charcoal"),
                floor_material_ids=("floor_concrete_gray",),
                furniture_material_ids=(
                    "finish_walnut",
                    "finish_black_metal",
                    "finish_gray_fabric",
                ),
                accent_ids=("terracotta", "charcoal", "ochre"),
            ),
            PaletteSpec(
                palette_id="neutral_sand",
                theme_id="neutral",
                label="Sand, natural finishes and muted accents",
                wall_material_ids=("wall_warm_white", "wall_sand"),
                floor_material_ids=("floor_warm_stone", "floor_light_oak"),
                furniture_material_ids=(
                    "finish_light_oak",
                    "finish_natural_linen",
                    "finish_walnut",
                    "finish_matte_white",
                ),
                accent_ids=("warm_taupe", "muted_sage", "terracotta"),
            ),
        )
    }
)
THEMES = MappingProxyType(
    {
        entry.theme_id: entry
        for entry in (
            ThemeSpec(
                theme_id=palette.theme_id,
                label=palette.theme_id.title(),
                palette_ids=(palette.palette_id,),
            )
            for palette in PALETTES.values()
        )
    }
)
CATALOG = StyleCatalog(
    themes=tuple(THEMES.values()),
    palettes=tuple(PALETTES.values()),
    materials=tuple(MATERIALS.values()),
    accents=tuple(ACCENTS.values()),
)
