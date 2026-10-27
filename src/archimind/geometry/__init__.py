"""Backend-only, zero-rotation containment, collision, and access checks."""

from archimind.geometry.accessibility import (
    MAX_ACCESSIBILITY_OBJECTS,
    AccessibilityConfig,
    AccessibilityIssue,
    AccessibilityValidationReport,
    CheckResult,
    validate_accessibility,
)
from archimind.geometry.footprints import (
    UnsupportedGeometryError,
    furniture_footprint,
    room_footprint,
)
from archimind.geometry.layout_generator import (
    MAX_GENERATION_ATTEMPTS,
    MAX_GENERATION_FURNITURE,
    LayoutCandidate,
    LayoutGenerationResult,
    LayoutScore,
    generate_layout_candidates,
)
from archimind.geometry.validator import (
    DEFAULT_AREA_TOLERANCE_M2,
    SpatialValidationReport,
    SpatialViolation,
    validate_layout,
)

__all__ = [
    "DEFAULT_AREA_TOLERANCE_M2",
    "MAX_ACCESSIBILITY_OBJECTS",
    "MAX_GENERATION_ATTEMPTS",
    "MAX_GENERATION_FURNITURE",
    "AccessibilityConfig",
    "AccessibilityIssue",
    "AccessibilityValidationReport",
    "CheckResult",
    "LayoutCandidate",
    "LayoutGenerationResult",
    "LayoutScore",
    "SpatialValidationReport",
    "SpatialViolation",
    "UnsupportedGeometryError",
    "furniture_footprint",
    "generate_layout_candidates",
    "room_footprint",
    "validate_layout",
    "validate_accessibility",
]
