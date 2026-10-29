"""Qualified product metadata; independent of rendering and placement engines."""

from archimind.assets.catalog import (
    CatalogError,
    FurnitureAssetRecord,
    FurnitureCatalog,
    furniture_from_catalog,
    load_catalog,
)
from archimind.assets.planning_envelopes import (
    PlanningDimensions,
    PlanningEnvelope,
    PlanningEnvelopeError,
    PlanningEnvelopeEvidence,
    PlanningEnvelopePlacement,
    PlanningEnvelopeQualification,
    PlanningFurnitureBinding,
    PlanningFurnitureSpecification,
    furniture_from_planning_envelope,
    load_planning_envelope,
    qualify_planning_envelope,
)

__all__ = [
    "CatalogError",
    "FurnitureAssetRecord",
    "FurnitureCatalog",
    "furniture_from_catalog",
    "load_catalog",
    "PlanningDimensions",
    "PlanningEnvelope",
    "PlanningEnvelopeError",
    "PlanningEnvelopeEvidence",
    "PlanningEnvelopePlacement",
    "PlanningEnvelopeQualification",
    "PlanningFurnitureBinding",
    "PlanningFurnitureSpecification",
    "furniture_from_planning_envelope",
    "load_planning_envelope",
    "qualify_planning_envelope",
]
