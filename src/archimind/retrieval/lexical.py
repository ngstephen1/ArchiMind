"""Conjunctive keyword baselines; no semantic inference, persistent DB or download."""

import math
import re

try:
    import sqlite3
except ImportError:  # Some Python builds omit the optional SQLite extension.
    sqlite3 = None
from collections import Counter
from contextlib import closing
from typing import Literal

from archimind.retrieval.contracts import (
    FurnitureSearchHit,
    FurnitureSearchRequest,
    FurnitureSearchResult,
)
from archimind.retrieval.eligibility import (
    IndexedDocument,
    RetrievalError,
    RetrievalIndex,
    build_index,
    current_options,
    eligibility_reasons,
    evidence_urls,
    normalized,
    qualification,
    reference,
)

Algorithm = Literal["python_bm25_v1", "sqlite_fts5_bm25_v1"]
_STOP = frozenset("a an the for and of to in me show find please i want with".split())


def tokens(text: str) -> tuple[str, ...]:
    return tuple(t for t in re.findall(r"[^\W_]+", normalized(text)) if t not in _STOP)


def fts5_available() -> bool:
    if sqlite3 is None:
        return False
    try:
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
        return True
    except sqlite3.Error:
        return False


class FTS5Unavailable(RuntimeError):
    """Optional local ranking capability is unavailable; no automatic substitute."""


def _sqlite_rank(corpus, terms):
    if sqlite3 is None:
        raise FTS5Unavailable("SQLite is unavailable")
    try:
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute(
                "CREATE VIRTUAL TABLE docs USING fts5(asset_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 0')"
            )
            db.executemany(
                "INSERT INTO docs VALUES (?,?)",
                [(key, " ".join(value)) for key, value in corpus.items()],
            )
            if terms:
                expression = " AND ".join('"' + t + '"' for t in terms)
                rows = db.execute(
                    "SELECT asset_id, -bm25(docs) FROM docs WHERE docs MATCH ?",
                    (expression,),
                ).fetchall()
            else:
                rows = [(key, 0.0) for key in corpus]
        return rows
    except sqlite3.Error:
        raise FTS5Unavailable("FTS5 is unavailable") from None


def rank_documents(
    documents: tuple[IndexedDocument, ...], query: str, algorithm: Algorithm
) -> tuple[tuple[str, float], ...]:
    """Rank an already eligible corpus, with all normalized query terms required.

    Blank query is a structured browse. Unsupported vocabulary has no substitute.
    Scores have algorithm-specific meanings and must not be compared across engines.
    """
    terms = tuple(sorted(set(tokens(query))))
    if query and not terms:
        return ()
    corpus = {d.reference.asset_id: tokens(d.text) for d in documents}
    if algorithm == "sqlite_fts5_bm25_v1":
        rows = _sqlite_rank(corpus, terms)
    elif algorithm == "python_bm25_v1":
        rows = []
        avg = sum(map(len, corpus.values())) / len(corpus) if corpus else 1.0
        df = {t: sum(t in value for value in corpus.values()) for t in terms}
        for key, value in corpus.items():
            counts = Counter(value)
            if not set(terms) <= counts.keys():
                continue
            score = sum(
                math.log1p((len(corpus) - df[t] + 0.5) / (df[t] + 0.5))
                * counts[t]
                * 2.2
                / (counts[t] + 1.2 * (0.25 + 0.75 * len(value) / avg))
                for t in terms
            )
            rows.append((key, score))
    else:
        raise ValueError("Unsupported offline ranking algorithm")
    return tuple(
        sorted(
            ((key, round(float(score), 12)) for key, score in rows),
            key=lambda pair: (-pair[1], pair[0]),
        )
    )


class LexicalRetrievalProvider:
    """Read-only derived snapshot with fresh source/qualification checks per search."""

    def __init__(
        self,
        *,
        index: RetrievalIndex | None = None,
        algorithm: Algorithm = "python_bm25_v1",
    ):
        if algorithm not in ("python_bm25_v1", "sqlite_fts5_bm25_v1"):
            raise ValueError("Unsupported offline ranking algorithm")
        if index is not None and not isinstance(index, RetrievalIndex):
            raise RetrievalError("Invalid retrieval snapshot")
        self.index = index if index is not None else build_index()
        self.algorithm = algorithm

    def search(self, request: FurnitureSearchRequest) -> FurnitureSearchResult:
        request = FurnitureSearchRequest.model_validate(request)

        def result(status, reasons, hits=()):
            return FurnitureSearchResult(
                request=request,
                identity=self.index.identity,
                algorithm=self.algorithm,
                status=status,
                hits=hits,
                reasons=reasons,
            )

        try:
            options = current_options()
            current = RetrievalIndex.from_options(options)
        except RetrievalError:
            return result("unavailable", ("catalog_authority_unavailable",))
        if (
            self.index != current
            or request.catalog_id != current.identity.catalog_id
            or request.catalog_version not in (None, current.identity.catalog_version)
        ):
            return result("stale_index", ("catalog_or_index_stale",))
        decisions = {
            o.record.asset_id: eligibility_reasons(request, o) for o in options
        }
        eligible = {
            o.record.asset_id: o for o in options if not decisions[o.record.asset_id]
        }
        if not eligible:
            return result(
                "empty",
                tuple(
                    sorted(
                        {reason for reasons in decisions.values() for reason in reasons}
                    )
                )
                or ("no_eligible_products",),
            )
        documents = tuple(
            d for d in current.documents if d.reference.asset_id in eligible
        )
        try:
            ranked = rank_documents(documents, request.query, self.algorithm)
        except FTS5Unavailable:
            return result("unavailable", ("fts5_unavailable",))
        hits = tuple(
            FurnitureSearchHit(
                reference=reference(eligible[key]),
                scope="real",
                qualification=qualification(eligible[key]),
                rank=rank,
                score=score,
                reasons=(
                    "hard_filters_passed",
                    "all_query_terms_matched" if request.query else "structured_browse",
                    f"dimensions_checked_{request.dimension_basis}",
                ),
                evidence_urls=evidence_urls(eligible[key]),
            )
            for rank, (key, score) in enumerate(ranked[: request.top_k], 1)
        )
        return result(
            "matches" if hits else "empty",
            ("ranked_eligible_products",) if hits else ("no_lexical_match",),
            hits,
        )
