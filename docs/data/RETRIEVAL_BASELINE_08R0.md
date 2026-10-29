# Retrieval baseline findings — Task 08R0

**Offline contract/baseline complete; no semantic model, vector database or UI integration.**
Observed on 2026-10-29 UTC. Baseline: `3f4f4b9f3615170c9f190082188c08bb554fdbf4`.
The unchanged baseline passed **1,581 tests in 121.48s**. Current implementation
and final verification are described below; historical 08E behavior remains intact.

## Corpus and judgments

The benchmark has **38 real queries over two products**: 20 positive, 17 negative,
and one stale-version case. All 38 are evaluated by both lexical methods. It also
has **24 isolated synthetic queries over eight artificial products**: 15 positive,
eight negative and one stale-version case. Synthetic scores never count toward
real effectiveness. This is 62 authored query cases, not 62 real products.

Source JSON:

- `data/benchmarks/furniture_retrieval_queries.json`: fixed real snapshot, complete
  relevance sets, independent hard-eligible gold IDs, status judgments and rationale.
- `data/benchmarks/furniture_retrieval_synthetic.json`: visibly artificial IDs,
  categories, dimensions and attributes, with no real rights or render approval.
- `docs/data/RETRIEVAL_BASELINE_08R0.json`: actual per-query IDs, scores, reasons,
  metrics, repeated timings, signatures and environment. This is an evaluation
  receipt, not an index or a product catalog.

Judgments were authored by the implementing agent before the first run. There
was **no independent human adjudication**. Real positive judgments follow reviewed
names, identities, aliases, functions and structured constraints. Two paraphrases
exercise semantic gaps. Some unequal synthetic grades are artificial ordinal
targets for metric arithmetic and do not encode fully specified user preferences;
their NDCG must not be sold as real preference accuracy. Adding explanatory notes
later did not change any request, relevance grade or eligible-ID set.

## Methods and exact definitions

Both methods first require current catalog/evidence identity and all hard filters.
Default size checks use the actual 08E generation reservation, including Charles's
larger Policy B box. Published-only fact finding is explicit and cannot directly
pass `resolve_result()` for preparation. Metadata-only bookcase hits are legitimate
metadata candidates, never mesh approval.

`python_bm25_v1` uses NFKC/casefold, a fixed English stopword list, alphanumeric
tokens, conjunctive meaningful terms, BM25 k1=1.2/b=0.75 and stable-ID ties.
`sqlite_fts5_bm25_v1` ranks the same filtered/tokenized corpus through an in-memory
FTS5 table; scores are engine-specific. Unsupported vocabulary returns empty;
there is no learned paraphrase matching or unqualified substitute. No file-backed
database or extension is created. FTS5 absence is reported, not silently disguised
as a successful FTS run; Python remains usable.

Definitions and denominators:

- **Precision@k:** relevant returned IDs in the first k divided by fixed k.
  Fewer returned hits leave empty slots; this is not precision per returned hit.
- **Recall@k:** relevant returned IDs divided by the complete positive gold set;
  null for absent/incomplete defensible gold. All present gold sets are exhaustive
  within their tiny declared corpora.
- **MRR@k:** reciprocal of the first relevant rank in the returned top-k, or zero
  for a positive query with no relevant hit. It is truncated at k, not full-list MRR.
- **NDCG@k:** gain `(2^grade - 1)/log2(rank + 1)`, divided by ideal gain from sorted
  graded judgments. Undefined when no positive judgments exist.
- Relevance metrics are macro-averaged over **positive queries only** (20 real,
  15 synthetic). **Real k=2; synthetic k=3.** Negative queries do not lower those
  relevance averages merely because a correct empty answer has no positive hit.
- **Category correctness:** matching authoritative/fixture category among returned
  hits whose request supplied a category. Denominators per method: **2 real hits**,
  **9 synthetic hits**. This small denominator is not broad category validation.
- **Hard-constraint violation rate:** returned IDs outside independently authored
  hard-eligible gold sets, divided by all returned hits. **Unauthorized leakage:**
  unknown/wrong-scope/forged-reference IDs or failed current real-authority
  resolution, divided by returned hits. Denominators: **19 real**, **23 synthetic**
  per method. A known product can be authorized but still violate a query filter.
- **Empty-result correctness:** correct presence/absence of results on valid
  positive and negative queries (37 real, 23 synthetic); unavailable responses
  cannot count as correct. It does not establish that any returned ID is relevant.
  Relevance, hard constraints and leakage are checked separately.
- **Version handling:** correct explicit stale response on the one stale-version
  case per corpus. Invalid contract objects are rejected before this metric.
- **Determinism:** identical typed results across three repeated calls per query.
  Latency is outside result messages/signatures and is not expected to repeat.

## Observed results

| Corpus / algorithm | P@k | Recall@k | MRR@k | NDCG@k | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real/python_bm25_v1 | 0.475000 | 0.900000 | 0.900000 | 0.900000 | 4.659 | 5.564 |
| real/sqlite_fts5_bm25_v1 | 0.475000 | 0.900000 | 0.900000 | 0.900000 | 5.105 | 5.705 |
| synthetic_fixture/python_bm25_v1 | 0.511111 | 0.933333 | 0.933333 | 0.900721 | 0.156 | 0.310 |
| synthetic_fixture/sqlite_fts5_bm25_v1 | 0.511111 | 0.933333 | 0.933333 | 0.900721 | 0.319 | 0.495 |

For both real methods, category correctness was **2/2**, hard violations **0/19**,
unauthorized leakage **0/19**, version handling **1/1** and determinism **38/38**.
All **17 negative queries returned empty**. Overall presence/empty correctness
was **35/37**, because two positive paraphrases were missed. For both synthetic
methods: category **9/9**, hard violations **0/23**, leakage **0/23**, version
**1/1**, determinism **24/24**, eight negative empty answers correct and overall
presence/empty correctness **22/23**. There were no unavailable queries in this
local run. These zero observed leakage counts do not prove universal safety.

Real precision@2 of 0.475 reflects the fixed denominator: most positive queries
have only one relevant product, even when retrieval succeeds. It must not be
confused with a 47.5% classification accuracy. None of these tiny-corpus numbers
establishes general architectural retrieval quality.

Known relevance failures are retained:

- `real:r18`, **“something to sit on”**: Charles is the source-grounded seating
  candidate; neither lexical method handles the paraphrase.
- `real:r19`, **“somewhere to put books”**: bookcase is the storage candidate;
  neither method bridges the wording.
- `synthetic:s20`, **“put my clothes away”**: the artificial wardrobe is missed.
- Synthetic `s03`, `s04` and `s22` have nonideal graded ordering relative to their
  artificial ordinal targets. See the synthetic-grade caveat above.

Negative cases include missing bed/desk, wardrobe versus bookcase, wrong variants,
unknown product IDs, unverified material/style/color, contradictory category/ID,
name matches that fail dimensions, a published-versus-reservation edge, render
intent for the metadata-only bookcase, unsupported room-use evidence and an
unauthorized model URL. Contract tests separately reject URL-shaped product IDs,
model URLs in evidence, duplicate hits/keys and fabricated render qualification.

## Timing and reproducibility

Measured environment: Python **3.11.13**, **Darwin arm64**, SQLite **3.54.0**, FTS5 **available**. Each real method has **114 timing samples**, each synthetic method **72** (three repetitions/query). Timings include end-to-end search plus result schema validation; real searches freshly validate packaged source/planning/render metadata. FTS5 builds an in-memory table per query. One local serial run is not a production throughput, RSS or multi-user benchmark. No encoder latency was measured.

The latency table is descriptive, not proof that either baseline is faster at
scale or better than vectors. Schema/evidence checking dominates this two-item
workload; local scheduling/caching can change these values. Python/FTS scores
have different scales. No vector implementation was measured, so there is no
lexical-versus-vector superiority claim.

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python scripts/evaluate_furniture_retrieval.py --output /tmp/08r0-replay.json
python -m pytest -q tests/test_retrieval_contracts.py tests/test_retrieval_lexical.py tests/test_retrieval_evaluation.py
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
python scripts/check_health.py
python scripts/build_product_registry.py --check
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run build
git diff --exit-code -- src/archimind/_viewer_assets
python -m pytest -q tests/test_asset_catalog_packaging.py
```

The CLI reads only fixed local benchmark files (at most 1 MiB each), emits JSON
and refuses to overwrite an existing output. Delete nothing to run it: choose a
new output filename. Output timestamps are unnecessary; environment and latency
may differ. Compare the semantic signature, not whole-file equality. Corpus or
evidence changes stop evaluation until judgments/snapshots are explicitly reviewed.

Recorded semantic output SHA-256: `6063a66e344188f60f2469453c19b3d21fd7a44ef4bb99b99c89b81bd3b34d31`.
Benchmark definition digest: `d13d69e5031e2f92970c655ecd26fc39e6516fed8fb1fac4b2c97f449497afea`.
Synthetic fixture digest: `bd1883030cc4f2631abe4bd8edc2d6ad301e94cd63e0daae098a15ff2efa32a5`.

## Verification and preservation

Checkpoint 2 full local suite: **1,678 passed in 112.51s**, including **97 retrieval
tests** and all 1,581 baseline tests. Final hardening adds URL/size/nested-message
checks; final suite and packaging results are recorded at the end of this file
once executed. Deterministic units block socket operations, providers, process
dispatch, geometry/generation and product-GLB inspection. Offline source/wheel
builds and controlled Streamlit health subprocesses are separate activities.

No UI, LangGraph, canonical model, spatial validator, layout generator, scoring,
08E preparation/selected state, renderer, GLB, original catalog/search text,
planning receipt or dependency changed. No embedding/vector library was installed
or imported by the new runtime package. Synthetic JSON is included in the source
archive as a labeled benchmark fixture, and excluded from wheel catalog resources.
Installed-wheel tests import retrieval outside the repository and confirm that no
optional model package is loaded by catalog search.

Read-only preservation check compared **124 baseline production/frontend/catalog/dependency files** byte-for-byte against `3f4f4b9`. The sorted `(path, SHA-256)` ledger digest is `e68f4893813a6df5bf580f6833f52d797e15b8bee7fd680f790ad337ad7e0b5f`. The existing asset-integrity and registry checks additionally verify approved packaged bytes. `.agents/` and `.claude/` remain untouched and untracked.

## Delivery and decision

- Contracts/eligibility: `2031b7ae8e5493fdb666a34d5215fd354807b1fe`,
  [CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40812757714).
- Lexical/evaluation: `7471c3c746c08a8c0b4e93d080ad57c3c4310f61`,
  [CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40813892586).
- Final release commit/CI are reported in the delivery response; this file cannot
  contain its own future commit hash without changing that hash.

A separately scoped **08R1** can benchmark one pinned offline CPU encoder against
these lexical baselines, with unchanged safety filters and transparently separated
real/synthetic results. Add independent held-out relevance review rather than tune
on the three known paraphrase failures. Start with exact cosine; a persistent
vector database has no demonstrated benefit here. In parallel, separately scope
**08F** rights/dimension/attribute qualification for more useful bedroom coverage.
The [architecture guide](../developer/FURNITURE_RETRIEVAL_ARCHITECTURE.md) states
source-based stack choices, future synchronization/recovery requirements and the
08R2 integration boundary. None of those later tasks was implemented.


## Final local release verification

- **1,688 Python tests passed in 108.64s** (107 new retrieval cases/tests; all
  1,581 baseline tests preserved). No failures/skips in the full local summary.
- Focused final retrieval suite: **107 passed in 4.19s**.
- Frontend: **75 passed, 0 failed, 0 skipped**; syntax and production build passed.
  The built bundle remained byte-identical to the baseline.
- Ruff lint passed; **155 files already formatted**. `pip check`: no broken
  requirements. Streamlit health returned **HTTP 200 ok** and the temporary
  server stopped. Registry and existing asset integrity/packaging checks passed.
- Real source/wheel builds, no-index/no-dependency isolated installation and
  outside-repository retrieval loading/search passed. Synthetic JSON is absent
  from wheel catalog resources; source fixtures/CLI/docs are included in the
  source archive. The installed API resolves Charles, rejects a queen-bed search
  and does not promote the bookcase to render qualification or import model SDKs.
- Final replay matched the recorded semantic signature. Hardening includes stale
  empty-result rejection, malformed evidence links, bounded index documents,
  unknown index types, nested-message sanitation and missing SQLite capability.
  No gold judgments/eligible sets were changed to hide observed ranking misses.
- No UI change required new visual acceptance. Existing Streamlit AppTest,
  renderer/frontend regressions and a fresh real health check passed; historical
  08E browser evidence is not presented as a new 08R0 visual inspection.

### Exact changed files across 08R0

- `MANIFEST.in`
- `README.md`
- `data/benchmarks/furniture_retrieval_queries.json`
- `data/benchmarks/furniture_retrieval_synthetic.json`
- `docs/data/RETRIEVAL_BASELINE_08R0.json`
- `docs/data/RETRIEVAL_BASELINE_08R0.md`
- `docs/developer/FURNITURE_RETRIEVAL_ARCHITECTURE.md`
- `docs/developer/STATUS.md`
- `scripts/evaluate_furniture_retrieval.py`
- `src/archimind/retrieval/__init__.py`
- `src/archimind/retrieval/contracts.py`
- `src/archimind/retrieval/eligibility.py`
- `src/archimind/retrieval/evaluation.py`
- `src/archimind/retrieval/lexical.py`
- `tests/retrieval_helpers.py`
- `tests/test_asset_catalog_packaging.py`
- `tests/test_retrieval_contracts.py`
- `tests/test_retrieval_evaluation.py`
- `tests/test_retrieval_lexical.py`
