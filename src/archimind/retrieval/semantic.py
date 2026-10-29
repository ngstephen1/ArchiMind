"""Exact cosine over an explicit local snapshot; no auto-build or model initialization."""

import time
from collections import deque
from typing import Literal

from pydantic import Field, model_validator

from archimind.retrieval.contracts import (
    Frozen,
    FurnitureSearchHit,
    FurnitureSearchRequest,
    FurnitureSearchResult,
)
from archimind.retrieval.eligibility import (
    RetrievalError,
    RetrievalIndex,
    current_options,
    digest,
    eligibility_reasons,
    evidence_urls,
    qualification,
    reference,
)
from archimind.retrieval.embedding_index import (
    EmbeddingError,
    EmbeddingIndex,
    TextEncoder,
    normalized_vectors,
    numpy_module,
)


class AbstentionPolicy(Frozen):
    mode: Literal["threshold", "abstain_all"]
    minimum_cosine: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    development_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    method: Literal[
        "unconfigured",
        "raw_reference",
        "zero_dev_fp_max_recall_highest_threshold_v1",
        "test_double",
    ]

    @model_validator(mode="after")
    def declared_threshold(self):
        if (self.mode == "threshold") != (self.minimum_cosine is not None):
            raise ValueError("Invalid abstention policy")
        if self.method.startswith("zero_dev") and self.development_digest is None:
            raise ValueError("Development evidence is required")
        return self


class SemanticRetrievalProvider:
    """Qualification is source authority; cosine is only a soft relevance signal."""

    def __init__(
        self, *, index: EmbeddingIndex, encoder: TextEncoder, policy: AbstentionPolicy
    ):
        self.index = index
        self.encoder = encoder
        self.policy = AbstentionPolicy.model_validate(policy)
        self.timings = deque(maxlen=4096)
        self.algorithm = (
            "cosine_v1_"
            + digest(
                {
                    "encoder": index.manifest.encoder_digest,
                    "policy": policy.model_dump(mode="json"),
                }
            )[:24]
        )

    def search(self, request: FurnitureSearchRequest) -> FurnitureSearchResult:
        request = FurnitureSearchRequest.model_validate(request)
        start = time.perf_counter_ns()
        timing = dict(authority_ms=0.0, embedding_ms=0.0, ranking_ms=0.0, total_ms=0.0)

        def result(status, reasons, hits=()):
            timing["total_ms"] = (time.perf_counter_ns() - start) / 1e6
            self.timings.append(timing)
            return FurnitureSearchResult(
                request=request,
                identity=self.index.manifest.corpus.identity,
                algorithm=self.algorithm,
                status=status,
                hits=hits,
                reasons=reasons,
            )

        corpus = self.index.manifest.corpus
        if self.encoder.spec != self.index.manifest.encoder:
            return result("stale_index", ("encoder_configuration_stale",))
        if corpus.identity.scope != "real":
            return result(
                "unavailable", ("synthetic_requires_isolated_benchmark_provider",)
            )
        try:
            options = current_options()
            current = RetrievalIndex.from_options(options)
        except RetrievalError:
            return result("unavailable", ("catalog_authority_unavailable",))
        timing["authority_ms"] = (time.perf_counter_ns() - start) / 1e6
        if (
            current != corpus
            or request.catalog_id != corpus.identity.catalog_id
            or request.catalog_version not in (None, corpus.identity.catalog_version)
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
                tuple(sorted({v for values in decisions.values() for v in values}))
                or ("no_eligible_products",),
            )
        if self.policy.mode == "abstain_all":
            return result("empty", ("semantic_policy_abstains",))
        try:
            qstart = time.perf_counter_ns()
            query = normalized_vectors(
                self.encoder.encode_queries((request.query,)), rows=1
            )[0]
            timing["embedding_ms"] = (time.perf_counter_ns() - qstart) / 1e6
            rstart = time.perf_counter_ns()
            ranked = rank_cosine(
                self.index, query, set(eligible), self.policy.minimum_cosine
            )
            timing["ranking_ms"] = (time.perf_counter_ns() - rstart) / 1e6
        except (ValueError, TypeError, OSError, RuntimeError, ImportError):
            return result("unavailable", ("local_encoder_unavailable_or_invalid",))
        try:
            after = current_options()
            if RetrievalIndex.from_options(after) != corpus:
                return result("stale_index", ("catalog_changed_during_encoding",))
            eligible = {
                o.record.asset_id: o
                for o in after
                if not eligibility_reasons(request, o)
            }
        except RetrievalError:
            return result("unavailable", ("catalog_authority_unavailable",))
        # Recheck source eligibility before constructing every result as a defense
        # against later ranker changes. Preparation must still resolve_result().
        hits = tuple(
            FurnitureSearchHit(
                reference=reference(eligible[key]),
                scope="real",
                qualification=qualification(eligible[key]),
                rank=i,
                score=round((cosine + 1) / 2, 12),
                reasons=(
                    "hard_filters_passed",
                    "exact_cosine_soft_relevance",
                    "test_double_encoder"
                    if self.encoder.spec.execution_kind == "test_double"
                    else "pinned_local_cpu_encoder",
                ),
                evidence_urls=evidence_urls(eligible[key]),
            )
            for i, (key, cosine) in enumerate(ranked[: request.top_k], 1)
            if not eligibility_reasons(request, eligible[key])
        )
        return result(
            "matches" if hits else "empty",
            ("semantic_ranked_eligible_products",)
            if hits
            else ("semantic_below_frozen_threshold",),
            hits,
        )


def rank_cosine(
    index: EmbeddingIndex, query, eligible_ids: set[str], minimum_cosine: float
):
    np = numpy_module()
    query = np.asarray(query)
    if (
        query.shape != (384,)
        or query.dtype.kind != "f"
        or not np.isfinite(query).all()
        or not np.isclose(
            np.linalg.norm(query.astype(np.float64)), 1.0, rtol=0, atol=1e-6
        )
    ):
        raise EmbeddingError("Invalid normalized query vector")
    if not np.isfinite(minimum_cosine) or not -1 <= minimum_cosine <= 1:
        raise EmbeddingError("Invalid cosine threshold")
    ids = index.manifest.row_asset_ids
    if not eligible_ids <= set(ids):
        raise EmbeddingError("Unknown vector candidate")
    scores = index.vectors().astype(np.float64) @ query.astype(np.float64)
    ranked = []
    for key, score in zip(ids, scores, strict=True):
        value = round(float(np.clip(score, -1, 1)), 8)
        if key in eligible_ids and value >= minimum_cosine:
            ranked.append((key, value))
    return tuple(sorted(ranked, key=lambda pair: (-pair[1], pair[0])))
