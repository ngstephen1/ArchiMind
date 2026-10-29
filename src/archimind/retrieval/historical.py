"""Explicit two-product research replay; never application preparation authority.

No global version switch, context mutation, snapshot rebuild or model invocation.
Current providers/resolvers still reject these results after catalog admission.
"""

from archimind.assets.specifications import catalog_product_options
from archimind.retrieval.eligibility import (
    RetrievalError,
    RetrievalIndex,
    _resolve_hit,
    _resolve_result,
)
from archimind.retrieval.hybrid import HybridRetrievalProvider
from archimind.retrieval.lexical import LexicalRetrievalProvider
from archimind.retrieval.semantic import SemanticRetrievalProvider


def historical_options():
    options = catalog_product_options(catalog_version="1.0.0")
    # Complete source/planning/release identity from the frozen 08R0 benchmark.
    if RetrievalIndex.from_options(options).identity.snapshot_id != HISTORICAL_SNAPSHOT:
        raise RetrievalError("Historical qualification snapshot changed")
    return options


def historical_index():
    return RetrievalIndex.from_options(historical_options())


def resolve_historical_hit(hit, identity):
    return _resolve_hit(hit, identity, historical_options())


def resolve_historical_result(result, *, for_preparation=False):
    if for_preparation:
        raise RetrievalError("Historical replay cannot authorize preparation")
    return _resolve_result(result, options=historical_options(), for_preparation=False)


class HistoricalLexicalProvider(LexicalRetrievalProvider):
    def __init__(self, *, index=None, algorithm="python_bm25_v1"):
        super().__init__(
            index=historical_index() if index is None else index, algorithm=algorithm
        )

    def _options(self):
        return historical_options()


class HistoricalSemanticProvider(SemanticRetrievalProvider):
    def _options(self):
        return historical_options()


class HistoricalHybridProvider(HybridRetrievalProvider):
    def _current_index(self):
        return historical_index()

    def _resolve(self, result):
        return resolve_historical_result(result)


HISTORICAL_SNAPSHOT = "75868dd7f81ac7b3300959e866cec0393338e93f5450886106a2d8eb2da440f8"
