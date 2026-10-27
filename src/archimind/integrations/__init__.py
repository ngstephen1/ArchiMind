"""Optional local integrations; importing this package performs no subprocess work."""

from archimind.integrations.codex_advisor import request_codex_advice
from archimind.integrations.codex_schemas import (
    CodexAdvice,
    CodexAdviceResult,
    FurniturePlacementSuggestion,
)

__all__ = [
    "CodexAdvice",
    "CodexAdviceResult",
    "FurniturePlacementSuggestion",
    "request_codex_advice",
]
