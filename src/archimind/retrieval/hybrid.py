"""Experimental union RRF over source-validated hits; never add model/BM25 scores."""

from archimind.retrieval.contracts import FurnitureSearchRequest, FurnitureSearchResult
from archimind.retrieval.eligibility import (
    build_index,
    digest,
    resolve_result,
)


def reciprocal_rank_fusion(rankings, *, k=60):
    """Version-one fusion: equal ranker weights, fixed k=60, stable ID ties."""
    if type(k) is not int or k != 60:
        raise ValueError("RRF v1 requires k=60")
    totals, contributors = {}, {}
    for ranker, ids in enumerate(rankings, 1):
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate RRF product")
        for rank, key in enumerate(ids, 1):
            totals[key] = totals.get(key, 0.0) + 1 / (k + rank)
            contributors.setdefault(key, []).append(f"ranker_{ranker}_rank_{rank}")
    return tuple(
        (key, totals[key], tuple(contributors[key]))
        for key in sorted(totals, key=lambda key: (-totals[key], key))
    )


class HybridRetrievalProvider:
    """Both rankers must be available; explicit union may use just one contribution."""

    def __init__(self, lexical, semantic, *, corpus, fixture_catalog=None):
        self.lexical, self.semantic, self.corpus = lexical, semantic, corpus
        self.fixture_gate = None
        if corpus.identity.scope == "synthetic_fixture":
            from archimind.retrieval.evaluation import SyntheticRetrievalProvider

            if fixture_catalog is None or fixture_catalog.index() != corpus:
                raise ValueError("Isolated fixture catalog required")
            self.fixture_gate = SyntheticRetrievalProvider(fixture_catalog)
        self.algorithm = (
            "rrf60_union_v1_"
            + digest(
                {
                    "lexical": lexical.algorithm,
                    "semantic": semantic.algorithm,
                    "scope": corpus.identity.scope,
                }
            )[:24]
        )

    def search(self, request):
        request = FurnitureSearchRequest.model_validate(request)

        def result(status, hits=(), reason="explicit_rank_union"):
            return FurnitureSearchResult(
                request=request,
                identity=self.corpus.identity,
                algorithm=self.algorithm,
                status=status,
                hits=hits,
                reasons=(reason,),
            )

        expanded = request.model_copy(update={"top_k": 50})
        try:
            if self.fixture_gate is None and build_index() != self.corpus:
                return result("stale_index", reason="hybrid_catalog_stale")
            outcomes = tuple(
                FurnitureSearchResult.model_validate(p.search(expanded))
                for p in (self.lexical, self.semantic)
            )
            for outcome in outcomes:
                if outcome.status in ("stale_index", "unavailable"):
                    return result(
                        outcome.status, reason="hybrid_component_not_available"
                    )
                if (
                    outcome.request != expanded
                    or outcome.identity != self.corpus.identity
                ):
                    raise ValueError
            allowed = None
            if self.fixture_gate is not None:
                allowed = self.fixture_gate.search(
                    expanded.model_copy(update={"query": ""})
                )
                if allowed.status not in ("matches", "empty"):
                    return result(
                        allowed.status, reason="fixture_hard_gate_unavailable"
                    )
                allowed = {h.reference.asset_id: h for h in allowed.hits}
            refs = {d.reference.asset_id: d.reference for d in self.corpus.documents}
            candidates = {}
            for outcome in outcomes:
                if self.fixture_gate is None:
                    resolve_result(outcome, for_preparation=False)
                for hit in outcome.hits:
                    key = hit.reference.asset_id
                    if refs.get(key) != hit.reference or (
                        allowed is not None
                        and (
                            key not in allowed
                            or hit.qualification != "synthetic_fixture"
                        )
                    ):
                        raise ValueError
                    if (
                        key in candidates
                        and candidates[key].qualification != hit.qualification
                    ):
                        raise ValueError
                    candidates[key] = hit
            rankings = [tuple(h.reference.asset_id for h in o.hits) for o in outcomes]
            fused = reciprocal_rank_fusion(rankings)
            hits = tuple(
                candidates[key].model_copy(
                    update={
                        "rank": rank,
                        "score": score,
                        "reasons": (
                            "hard_filters_passed",
                            "rrf60_equal_weight_rank_union",
                            *contributors,
                        ),
                    }
                )
                for rank, (key, score, contributors) in enumerate(
                    fused[: request.top_k], 1
                )
            )
            final = result("matches" if hits else "empty", hits)
            if self.fixture_gate is None:
                resolve_result(final, for_preparation=False)
            return final
        except (ValueError, TypeError, OSError, RuntimeError, ImportError):
            return result("unavailable", reason="hybrid_source_validation_failed")
