"""Qualified product metadata; independent of rendering and placement engines."""

from archimind.assets.catalog import (
    CatalogError,
    FurnitureAssetRecord,
    FurnitureCatalog,
    furniture_from_catalog,
    load_catalog,
)

__all__ = [
    "CatalogError",
    "FurnitureAssetRecord",
    "FurnitureCatalog",
    "furniture_from_catalog",
    "load_catalog",
]
