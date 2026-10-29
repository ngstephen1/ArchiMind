"""Offline retrieval contracts; no UI, generation or model provider integration."""

from archimind.retrieval.contracts import (
    FurnitureRetrievalProvider,
    FurnitureSearchFilters,
    FurnitureSearchHit,
    FurnitureSearchRequest,
    FurnitureSearchResult,
)
from archimind.retrieval.eligibility import (
    RetrievalError,
    build_index,
    resolve_hit,
    resolve_result,
)

__all__ = [
    "FurnitureRetrievalProvider",
    "FurnitureSearchFilters",
    "FurnitureSearchHit",
    "FurnitureSearchRequest",
    "FurnitureSearchResult",
    "RetrievalError",
    "build_index",
    "resolve_hit",
    "resolve_result",
]

from archimind.retrieval.lexical import LexicalRetrievalProvider

__all__ += ["LexicalRetrievalProvider"]
