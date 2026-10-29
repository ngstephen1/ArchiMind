# Offline furniture retrieval — 08R0

08R0 adds an offline retrieval contract, current-evidence eligibility, a keyword
baseline and an evaluation harness. It does **not** connect retrieval to Streamlit
or LangGraph. No embedding package, model, vector database, asset or dependency
was acquired. Current catalog JSON remains authoritative; a derived index cannot
supply dimensions, rights, a mesh URL, a room pose or render approval.

## Existing boundaries reused

| Boundary | Existing authority | 08R0 behavior |
| --- | --- | --- |
| Product facts | `assets/catalog.py`, fixed `furniture_catalog.json` | Resolve exact catalog/product/variant IDs and record/document digests |
| Planning reservation | `assets/planning_envelopes.py` and approved Policy B | Read current envelope evidence through `catalog_product_options()` |
| Render qualification | Separate fixed product release | Read approval status; no GLB is opened by retrieval |
| Preparation | `assets/specifications.py` | Return IDs for a later explicit caller; no factory or generation call during retrieval |
| Geometry and selected layouts | Existing generator, validators and 08D/08E UI | Unchanged; no retrieval import or control added |

Two real records exist: Charles/Sod `abo-b075x2x4xs-amazon-com`, and Espresso
bookcase `abo-b07pqs58xn-amazon-com`. Both have checked published item claims.
Charles additionally has Policy B and a current approved render release. The
bookcase has neither. Historical catalog render flags remain false and unchanged;
retrieval consults the separate current release. Render qualification describes
reviewed evidence, not a fresh model-file integrity or availability check. Those
checks remain in the existing renderer.

## Typed interfaces and safety

`archimind.retrieval` exports `FurnitureSearchRequest`, `FurnitureSearchFilters`,
`FurnitureSearchHit`, `FurnitureSearchResult`, `FurnitureRetrievalProvider`,
`LexicalRetrievalProvider`, `build_index`, `resolve_hit`, `resolve_result` and
`RetrievalError`. Pydantic contracts are strict, frozen, deeply immutable and
JSON-serializable. Unknown fields, duplicate JSON keys, nonfinite numbers,
unsupported qualification/orientation, malformed IDs, duplicate hits, inconsistent
ranks/snapshots and invalid ordering are rejected. Request text is bounded to
1,024 characters, top-k to 1–50; corpus snapshots are bounded to 64 documents
and 16,384 characters per document. Output carries IDs and source-document links,
never an arbitrary model location or placement command.

Requests support exact category/product/asset/variant/use, verified attribute
constraints, maximum W/D/H, qualification intent and optional catalog-version
pinning. Rotation is integer zero only. Catalog attributes absent from reviewed
source fields cannot satisfy a filter. `Espresso` is a variant, not a verified
color; original marketing text mentioning leather is excluded from search text.
`required_use` matches reviewed usage tags, aliases or subtype. A bookcase does
not satisfy wardrobe use. No verified bedroom-use field exists, so an explicit
bedroom-use requirement yields no match, rather than invented suitability.

Eligibility precedes ranking. It checks current source identity/version,
public-hosting/redistribution rights, validated item dimensions, category/variant,
verified attributes/use, supported yaw and requested planning/render evidence.
A relevant name never overrides a hard failure. The default dimension basis is
`generation_reservation`: Charles is checked against its larger Policy B box,
and the bookcase against published item dimensions, exactly as 08E would prepare.
Missing Charles planning evidence prevents generation-reservation eligibility.

`dimension_basis="published"` is an explicit metadata-only fact-finding mode.
Planning/render intent cannot use it. `resolve_result()` defaults to preparation
safety and rejects such a result even if its product reference is valid; use
`for_preparation=False` only to inspect facts. A future selection UI must recheck
generation-reservation constraints before proposing that product. No query, hit
or source reference authorizes acquisition, modifies a layout or proves room fit.

A typical **backend-only** call is:

```python
from archimind.retrieval import (
    FurnitureSearchFilters,
    FurnitureSearchRequest,
    LexicalRetrievalProvider,
    resolve_result,
)

provider = LexicalRetrievalProvider()
request = FurnitureSearchRequest(
    query="Charles armchair",
    filters=FurnitureSearchFilters(category="chair", max_width_m=1.0),
    top_k=2,
)
result = provider.search(request)
current_options = resolve_result(result)  # Fresh IDs/evidence AND hard filters
```

`resolve_hit()` verifies current source identity/evidence; `resolve_result()` adds
request constraints and preparation intent. Consumers must use the latter for a
future 08E handoff. These functions do not certify ranking quality or an arbitrary
provider's internal model cache. Invalid/stale evidence is not repaired.

## Index identity and lexical methods

The index is an in-memory immutable projection of reviewed search documents,
not another product catalog. The existing document text/digests and original
catalog stay unchanged. Line breaks are flattened in the derived projection only.
References retain catalog ID/version, asset/product IDs/version, full record SHA,
search-document version and original document SHA. `IndexIdentity` also binds
current planning/render evidence and a reproducible corpus snapshot ID.

Every real search reconstructs the current source/evidence projection and rejects
a mismatching index, edited text, removed product or requested old version with
`stale_index` and no hits. Unavailable authority returns `unavailable`, never a
last-known product substituted as current. Empty eligible/text matches return
`empty` with fixed explainable reasons. Rank changes cannot promote a product.

Two methods implement the same result contract:

- **`python_bm25_v1`**: NFKC + casefold, Unicode alphanumeric tokens, a fixed small
  English stopword set, all meaningful query terms required, then BM25 with
  k1=1.2/b=0.75 over eligible documents. Scores round to 12 decimal places; ties
  use stable asset IDs. Blank query is structured browsing; stopwords-only text
  has no match. No stemming, learned synonyms, attribute extraction or parser is
  implied. Unmatched words intentionally produce no fallback.
- **`sqlite_fts5_bm25_v1`**: optional standard-library `sqlite3` benchmark with an
  in-memory FTS5 table rebuilt per search. The same pre-tokenized eligible text
  and quoted AND terms are bound through SQL parameters; query text is never SQL.
  FTS5's negated BM25 score is adapted to descending scores and the same tie rule.
  There is no file-backed database, migration or extension download. If FTS5 is
  absent, its benchmark is explicitly unavailable; Python stays functional.

Scores are engine-specific, not calibrated probabilities. FTS5 is optional in a
Python installation; feature availability is checked at runtime. The implementation
uses the documented FTS5 full-text and ranking interfaces, not a persistent catalog
store. [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html).

## Evaluation boundary

[Benchmark definitions](../../data/benchmarks/furniture_retrieval_queries.json)
pin the current real source snapshot and an isolated synthetic fixture digest.
There are **38 real queries** over **two real products**, and **24 synthetic
queries** over **eight artificial products**. Judgments were authored by the
implementing agent before the first run; no independent human adjudication or
expert design review is claimed. The synthetic ordinal grades exercise ranking
metrics, and some target preferences are deliberately not fully specified by
query text. Their numbers measure fixture mechanics, not real preference quality.

Synthetic records have `synthetic:` IDs, `synthetic_fixture` scope and qualification,
no evidence URLs and no planning/render qualification. They are never loaded by
normal catalog discovery, included as wheel catalog data, acquired, or resolvable
through `resolve_result()`. Passing their IDs to 08E fails. Separate reporting is
mandatory. Explicit hard-eligible gold sets are checked independently of the
provider's filter implementation. Relevance metrics, safety denominators,
latencies, known misses and replay commands are in the
[baseline findings](../data/RETRIEVAL_BASELINE_08R0.md).

## Proposed embedding/storage stack — not implemented

Recommend **exact NumPy cosine search first**, after a separately authorized
08R1 benchmark. With two records, a persistent vector service has no demonstrated
benefit. Retain Python/FTS baselines and the identical hard gates/qrels. Exact
matrix/vector dot products are available in NumPy; cosine also requires explicit
finite, nonzero vector normalization. This is a proposed implementation, not a
measured vector baseline. [NumPy dot-product reference](https://numpy.org/doc/stable/reference/generated/numpy.dot.html).

FastEmbed with **`BAAI/bge-small-en-v1.5`** is the candidate encoder. The official
model card and FastEmbed list report English text, 384 dimensions, a 512-token
limit and MIT licensing. Reported FastEmbed artifact size is about 0.067 GB, not
measured resident RAM. Its current source exposes local-cache/path and
`local_files_only` controls; pin and test an exact package/model revision before
relying on these options. Nothing was installed or instantiated here.
[FastEmbed model list](https://qdrant.github.io/fastembed/examples/Supported_Models/),
[BAAI model card](https://huggingface.co/BAAI/bge-small-en-v1.5),
[FastEmbed encoder source](https://github.com/qdrant/fastembed/blob/main/fastembed/text/text_embedding.py).

| Candidate | Choose when | Costs, isolation and migration |
| --- | --- | --- |
| Exact NumPy + immutable files | First small CPU benchmark; exact reference ranking fits measured latency/memory budget | Minimal operational state; validate row IDs, vectors and manifests, then rank eligible rows. O(Nd) work; no measured cutoff yet. |
| SQLite + FTS5 | A reviewed durable product-metadata store becomes useful | Future typed migration may make structured SQLite records authoritative; FTS remains derived. Keep source evidence, versions, constraints and atomic transactions. Current JSON authority is not silently replaced or dual-written. |
| Persistent Chroma | Measured corpus/update volume warrants a managed local vector collection | Adds a dependency, storage lifecycle and operational tests. Official client docs position embedded persistence for local development/testing and favor server-backed clients for production. Keep embeddings explicit; do not accidentally trigger a default encoder/download. |
| PostgreSQL + pgvector | A separately planned multi-user backend needs transactional product data, access controls and vectors together | Requires a service, migrations, backup/restore and tenant policy. Supports exact and approximate search plus cosine distance; measure ANN recall and filtering before adopting it. Not warranted by two products. |

These choices are architectural recommendations, not performance conclusions.
[SQLite transactions](https://www.sqlite.org/lang_transaction.html),
[Chroma client documentation](https://docs.trychroma.com/reference/python/client#persistentclient),
[Chroma collection source](https://github.com/chroma-core/chroma/blob/main/chromadb/api/models/Collection.py),
[pgvector official documentation](https://github.com/pgvector/pgvector).
The initially tried Chroma `/docs/run-chroma/persistent-client` route and a guessed
FastEmbed offline-guide route were unavailable; the official references above,
not those failed routes, support the assessment. Source pages are mutable and were
checked on 2026-10-29 UTC; no installed dependency/version is certified from them.

## Future reproducibility and operational gates

Before any vector provider is admitted:

1. Separately authorize a bounded encoder acquisition. Pin package, ONNX Runtime,
   model repository/revision, tokenizer/config/weights hashes, license, CPU provider,
   query/passage instructions, pooling, normalization, batch/thread settings,
   precision and document truncation. Missing local files fail; no runtime network
   fallback or public upload may select paths/models.
2. Create a derived manifest binding the current corpus `IndexIdentity`, stable
   IDs/record/doc versions and digests, model/configuration digests, vector dtype,
   shape `(N,384)`, nonzero finite norms and deterministic row order. Encode the
   provider/configuration manifest identity in its versioned algorithm identifier.
   The public result can retain the same corpus frame and references; a semantic
   provider must additionally verify its own vector manifest before search.
3. Use unchanged reviewed text as input. Do not manufacture materials/styles from
   model output. Apply hard eligibility before ranking and again before 08E.
   Normalize cosine/distance scores to the nonnegative result contract; version
   this mapping. Compare rank fusion against component methods; never add
   uncalibrated BM25 and cosine scores without a declared method.
4. Publish immutable snapshots. Changed/deleted records invalidate their derived
   rows; model/text-policy changes invalidate all affected vectors. Build in a
   staging directory/transaction, verify complete ID coverage/checksums, then
   atomically replace the active pointer. Readers retain a complete old or new
   snapshot, never a mixture. Corruption yields no certified results until a
   verified local rebuild; never trust vector metadata as product facts.
5. Measure cold/warm encoding, search, end-to-end filtering, peak RSS and artifact
   storage on the intended CPU. Float32 384-vectors require 1,536 bytes each before
   IDs/index overhead: 10,000 rows need 15.36 MB, one million 1.536 GB. These are
   arithmetic estimates, excluding encoder/RAM/index/temporary arrays, not device
   measurements. Define latency/memory limits before choosing an ANN service.
6. Keep public catalog snapshots immutable and session-independent. Personal
   preferences, saved selections and query logs need separate session/tenant
   ownership and retention. A shared writable embedded collection is not a tenant
   boundary. A future server deployment needs authentication/access controls,
   concurrency tests, crash recovery and backups; none exist merely because an
   in-memory benchmark passes.

## Task boundaries

**08R1, separately authorized:** one pinned CPU encoder, exact cosine baseline,
lexical/semantic/hybrid comparison on unchanged gold sets plus independently
reviewed held-out paraphrases, same filters, actual resource measurements, no UI
or production indexing. Two real products remain a sanity check only.

**08R2, separately authorized:** parse structured requirements → resolve hard
constraints → retrieve/currently resolve IDs → show evidence → call the existing
`prepare_catalog_specification()` → review → explicit Generate → unchanged
validation → selected renderer. Never update an existing candidate from a hit.
Keep catalog/seed/source/styling state rules from 08E. This pipeline is documented,
not implemented by 08R0.

**08F, separate data work:** qualify more rights-cleared, dimension-grounded
bed/desk/storage products and genuinely sourced attributes before expecting useful
catalog-wide retrieval. Render qualification is independent. No source ingestion,
08R1/R2/08F work, live request, model download or vector indexing is authorized by
this guide.
