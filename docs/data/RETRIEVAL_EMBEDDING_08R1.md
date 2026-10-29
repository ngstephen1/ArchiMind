# Offline embedding experiment — Task 08R1

**Offline experiment complete; semantic/hybrid production integration is not recommended.**
Observed 2026-10-29. Baseline `35414083ec2d1ced0fa0901bd9e96e550e5c9614`.
No UI, generation, geometry, rendering, catalog/search text or default dependency
change. Model weights, environment and derived vector files stay outside Git.

## Pinned model and reproducibility

Logical encoder **BAAI/bge-small-en-v1.5**, upstream revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. Official FastEmbed quantized ONNX
representation: `Qdrant/bge-small-en-v1.5-onnx-Q`, revision
`aa8f8b060edb00e03bfdd08813a2949946c8ba55`. FastEmbed **0.9.1**, ONNX Runtime
**1.24.2**, NumPy **2.4.6**, tokenizers **0.23.3**, Python **3.11.13**, Darwin arm64.
Only CPUExecutionProvider, one thread, batch one. CLS pooling; 384 dimensions,
512-token truncation. Documents use exact reviewed search text without a prefix;
queries receive BAAI's retrieval instruction. FastEmbed already normalizes output;
our recorded float64 L2 / float32 storage normalization validates it again.

The ONNX file is **66,465,124 bytes**, SHA-256
`51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431`.
All ten model/tokenizer/configuration/card files total **67,508,369 bytes**.
[Acquisition receipt](ENCODER_ACQUISITION_08R1.json) lists individual hashes and
pinned official URLs; [environment receipt](ENCODER_ENVIRONMENT_08R1.json) records
transitive wheel hashes and separate dependency/storage costs. No furniture asset
or second encoder was acquired. The default project environment was not changed.

Primary evidence: [upstream card](https://huggingface.co/BAAI/bge-small-en-v1.5/blob/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/README.md),
[ONNX port card](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/blob/aa8f8b060edb00e03bfdd08813a2949946c8ba55/README.md),
[FastEmbed pinned implementation](https://github.com/qdrant/fastembed/blob/v0.9.1/fastembed/text/onnx_embedding.py),
[local-path loader](https://github.com/qdrant/fastembed/blob/v0.9.1/fastembed/common/model_management.py).
Both model cards declare MIT; retain applicable copyright/license notices if
redistributing weights later. No weights are redistributed here. The upstream
card declaration is not independent legal adjudication or model-equivalence proof.

## Frozen evaluation and abstention

Original 08R0 cases and judgments are byte-identical: 38 real queries/two products,
24 isolated synthetic queries/eight artificial products. New development: 12 real
and 12 synthetic; new held-out: 16 real and 12 synthetic. All gold judgments were
frozen before real inference, authored by the implementing agent, **without
independent human adjudication**. Synthetic results never count as real evidence.

Development SHA-256: `1800c1932ba13373de8e62a189a53393e71c97699a19fef288047180528fac29`.
Held-out SHA-256: `e219d29f10de791627acfc573bb2108d8074f937d105b72b2a9e534f85ecd088`.
Fixed grid 0.00–1.00 in 0.01 increments: require zero negative-query false positives,
maximize positive recall, then choose the highest threshold. Real and synthetic
calibrate separately. No held-out or original reference query tunes thresholds.
Frozen real threshold **0.75**, synthetic **0.77**; policy SHA-256
`c00951281f3edbc94c014212ded1d59f6736ce7d4edc7e72845d3909aa8ff06d`.
The policy was written read-only before original/held-out scoring. Raw cosine
(minimum −1) is explicitly diagnostic, never the recommended policy.

## Observed semantic results

| Scope | Method | Recall@k | Negative-query false positives |
| --- | --- | ---: | ---: |
| Original real | BM25 / FTS5 | .900 | 0/17 |
| Original real | Raw cosine | 1.000 | 4/17 |
| Original real | Frozen cosine | .350 | 0/17 |
| Held-out real | BM25 / FTS5 | .125 | 0/8 |
| Held-out real | Raw cosine | 1.000 | 4/8 |
| Held-out real | Frozen cosine | .000 | 0/8 |
| Original synthetic | BM25 / FTS5 | .933333 | 0/8 |
| Original synthetic | Raw cosine | 1.000 | 2/8 |
| Original synthetic | Frozen cosine | .700 | 0/8 |
| Held-out synthetic | BM25 / FTS5 | .000 | 0/6 |
| Held-out synthetic | Raw cosine | 1.000 | 4/6 |
| Held-out synthetic | Frozen cosine | .166667 | 1/6 |

The conservative real threshold loses all eight held-out positives; synthetic
abstention also fails one held-out negative. **Do not integrate unrestricted
semantic recommendations into the application on this evidence.** Raw cosine
can bridge paraphrases but cannot reliably reject unsupported furniture intent.
Structured hard filters remain authoritative; all measured methods returned zero
hard-filter violations and unauthorized-ID leakage. Those tests do not make
unstructured negative-query false positives acceptable.

Full P@k/MRR/NDCG, category/version/empty/determinism metrics, individual results,
FP/FN counts and stage timings are in [the receipt](RETRIEVAL_EMBEDDING_08R1.json).
Metric definitions and positive-only/fixed-k denominators remain those in
[08R0](RETRIEVAL_BASELINE_08R0.md). Scores are soft similarities, not probabilities.
Blank queries explicitly browse structured eligible records without inference.

## Isolation and implementation

`embedding_index.py`: immutable float32 rows tied to model/configuration, exact
search text, catalog/evidence versions and hashes. Explicit build/load only;
missing/corrupt/stale snapshots fail safely. `semantic.py`: hard filters before
encoding, current authority checked again before result creation; downstream
`resolve_result()` remains mandatory for any future preparation.

`offline_encoder.py`: verifies exact local files and installed versions, uses
`specific_model_path`, `local_files_only`, offline environment flags and CPU only.
The benchmark installs a Python network/process tripwire after separately timed
SDK bootstrap and before model construction/inference. Accepted runs record zero
attempts. This is not an arbitrary native-code OS sandbox; dependency imports
are outside that tripwire and no whole-process no-socket claim is made.

Initial installation hit ENOSPC; an offline no-compile retry from the same wheels
succeeded without unrelated cleanup. Initial calibration telemetry attempted a
platform processor subprocess, which the guard blocked. Replacing that telemetry
with passive platform fields and repeating into new paths produced **byte-identical
policies**; no gold labels, filters or thresholds were adjusted after test scoring.
These development failures are not reported as successful benchmark receipts.

Checkpoint 2 full suite: **1,732 passed in 117.18s**. Focused suite: **44 passed**, with fixed vectors/inert SDK doubles;
no real model required. Baseline at task start: **1,688 passed in 139.17s**.
Final release verification is recorded below.


## Hybrid method and full test-set comparison

RRF uses equal-weight `1/(60 + rank)` terms, stable-ID ties and an explicit union
of accepted lexical and frozen-semantic hits. It never adds cosine/BM25 scores.
Both rankers use the same hard-eligible universe. An unavailable/stale ranker stops
fusion; an available ranker with zero accepted hits can contribute nothing. Each
hit records which ranks contributed; real component and final hits are resolved
against source authority. No tuning of k or thresholds followed held-out scoring.

| Test scope / method | P@k | Recall@k | MRR@k | NDCG@k | Negative FP | Positive FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original real, BM25 / FTS5 | .475000 | .900000 | .900000 | .900000 | 0/17 | 2/20 |
| Original real, raw cosine | .525000 | 1.000000 | 1.000000 | 1.000000 | 4/17 | 0/20 |
| Original real, frozen cosine | .200000 | .350000 | .350000 | .350000 | 0/17 | 13/20 |
| Original real, RRF | .475000 | .900000 | .900000 | .900000 | 0/17 | 2/20 |
| Held-out real, BM25 / FTS5 | .062500 | .125000 | .125000 | .125000 | 0/8 | 7/8 |
| Held-out real, raw cosine | .500000 | 1.000000 | 1.000000 | 1.000000 | 4/8 | 0/8 |
| Held-out real, frozen cosine | .000000 | .000000 | .000000 | .000000 | 0/8 | 8/8 |
| Held-out real, RRF | .062500 | .125000 | .125000 | .125000 | 0/8 | 7/8 |
| Original synthetic, BM25 / FTS5 | .511111 | .933333 | .933333 | .900721 | 0/8 | 1/15 |
| Original synthetic, raw cosine | .533333 | 1.000000 | .966667 | .964762 | 2/8 | 0/15 |
| Original synthetic, frozen cosine | .355556 | .700000 | .733333 | .689157 | 0/8 | 4/15 |
| Original synthetic, RRF | .511111 | .933333 | .933333 | .893850 | 0/8 | 1/15 |
| Held-out synthetic, BM25 / FTS5 | .000000 | .000000 | .000000 | .000000 | 0/6 | 6/6 |
| Held-out synthetic, raw cosine | .333333 | 1.000000 | 1.000000 | 1.000000 | 4/6 | 0/6 |
| Held-out synthetic, frozen cosine | .055556 | .166667 | .166667 | .166667 | 1/6 | 5/6 |
| Held-out synthetic, RRF | .055556 | .166667 | .166667 | .166667 | 1/6 | 5/6 |

Real k=2, synthetic k=3. Relevance metrics are macro means over positives, using
fixed-k precision and complete gold sets; FN means no relevant ID returned on a
positive query. FP means any result on a negative query. Stale queries are excluded
from these error-rate denominators. Original corpora each contain one stale case;
new splits contain none. Version checks passed both original cases for every
method. Three repeats per query were deterministic. All measured hard-constraint
violations and unauthorized IDs were zero; no provider was unavailable. Category
correctness is 1.0 where returned/category-filtered hits exist, and null where no
such hits exist. Exact denominators and presence/empty correctness are in JSON.

Raw real recall@2 of 1.0 is especially weak evidence: k equals the **entire
2-product corpus**, so returning both eligible products almost guarantees recall.
MRR measures whether the relevant product came first; neither metric excuses
unsupported results. RRF has no real relevance gain, slightly worsens original
synthetic graded ordering and inherits the frozen synthetic held-out false
positive (`synthetic_fixture:held_out09`). Synthetic ordinal-grade limitations
from 08R0 still apply; this is not preference-quality evidence.

### Per-query improvements and regressions

Raw cosine places the appropriate product first for `real:r18` (seating),
`real:r19` (book storage), and `synthetic:s20` (clothes storage). Their signed top
cosines are approximately .606, .614 and .589, below the frozen .75/.77 thresholds.
Consequently both frozen cosine and RRF still miss all three; no deployment gain
can be claimed from the raw diagnostic alone.

Frozen real cosine recovers none of the eight held-out positives, including
paraphrases beyond the known 08R0 misses. It also loses eleven positive original
queries that lexical search handles. Original raw real false positives are
`real:r31`, `r35`, `r36`, `r37`; held-out raw false positives are
`real:held_out12`, `13`, `14`, `16`. These cover unsupported/no-relevant intent;
the corresponding structured filters still reject unsupported attributes and
identities. An explicit future parser is not implemented or evaluated here.
The receipt retains every returned ID, score, reason and ranking shortfall rather
than changing gold labels to hide mistakes.

## CPU cost and equivalent timing definitions

Measured device: **Apple M1**, Darwin 24.6.0 arm64, Python 3.11.13. The default
application environment and isolated encoder environment are distinct. The final
comparison uses the same external end-to-end timer around typed `search()` and
result revalidation for every method. Model initialization/index construction
are separate; there is no query-vector cache. Each original real method has 114
samples, held-out real 48, original synthetic 72 and held-out synthetic 36.

| Real scope / method | End-to-end p50 ms | p95 ms |
| --- | ---: | ---: |
| Original / Python BM25 | 4.88 | 5.22 |
| Original / SQLite FTS5 | 5.06 | 5.83 |
| Original / raw cosine | 14.06 | 24.48 |
| Original / frozen cosine | 13.31 | 22.59 |
| Original / RRF | 45.89 | 61.23 |
| Held-out / Python BM25 | 4.63 | 4.92 |
| Held-out / SQLite FTS5 | 5.39 | 6.17 |
| Held-out / raw cosine | 21.83 | 25.40 |
| Held-out / frozen cosine | 20.47 | 29.13 |
| Held-out / RRF | 47.16 | 54.25 |

Final frozen original-real stage p50/p95: source/evidence checks **9.31/10.46 ms**,
query embedding **3.40/12.42 ms**, exact ranking **.029/.076 ms**. Held-out-real:
**10.05/14.19**, **10.72/15.41**, **.066/.081 ms**, respectively. These stage
percentiles are unconditional (zero for skipped stages) and do not add to total
percentiles. Internal timing excludes some filter/contract overhead; external
end-to-end timing includes it. Hybrid repeats authority checks deliberately;
its overhead is not solely vector arithmetic. No large-corpus speed claim follows.

Successful calibration process: dependency bootstrap **.495 s**, first encoder
instance **.230 s**, second instance **.216 s**. Final comparison process:
**.473 s**, **.205 s**, **.161 s**. The earlier nonhybrid test process measured
**1.536/.820/.212 s**, showing scheduling/cache variability. “First” means first
instance in a fresh process after dependency imports, **not** filesystem-cache
cold; no OS cache was flushed. Both instance times include local artifact hashes.
Accepted development index build: **.121 s real**, **.209 s synthetic**. Peak RSS:
**384,368,640 bytes** in calibration, **431,849,472 bytes** in final comparison;
process-wide peaks include two initializations, benchmark and validation, not
isolated per-query or per-model memory.

Model cache: **67,508,369 bytes**. Raw float32 vectors: **3,072 bytes real** and
**12,288 bytes synthetic**. With manifests, snapshots are **9,615 / 22,337 bytes**.
Dependency wheels: **47,518,038 bytes**; isolated environment logical-file snapshot:
**215,802,829 bytes**. Later filesystem allocated KiB: environment **226,648**,
wheels **46,472**, model **65,952**, indices **36**. Allocated/logical measures
have different definitions; weights' 250 MiB budget excludes dependency storage.
No weights, vectors, binary wheels or environments were committed.

## Technology and admission decision

| Choice | Actual evidence / cost | Decision |
| --- | --- | --- |
| Exact NumPy | Two real vectors; exact ranking under .1 ms at p95 in this run; immutable derived snapshots, no service | Keep for offline experiments; current manifest deliberately bounds corpus to 64 rows |
| Chroma | [Official docs](https://docs.trychroma.com/docs/overview/introduction) describe embedding/document storage and metadata filtering; adds dependency/index/update ownership | Not installed/measured; no demonstrated current benefit |
| PostgreSQL + pgvector | [Official source](https://github.com/pgvector/pgvector) supports vectors alongside transactional relational data and exact/approximate search | Not installed/measured; evaluate when shared transactional catalog joins, concurrent updates, migrations/backups or measured scale justify a service |

A database does not fix coverage, unsupported-intent handling or relevance.
**08R2 unrestricted semantic integration is not ready.** Keep the existing lexical
backend and explicit catalog review. First obtain independent owner/expert labels,
expand qualified bedroom coverage under a separate 08F scope and predeclare a
fresh abstention evaluation. Do not tune to this held-out set or acquire another
encoder under this task. No Chroma, pgvector, AI agent, 08R2 UI or 08F work began.

## Reproduction and release evidence

The task-owned experiment is `/Users/macbook/Hack/.archimind-08r1/`. Use its local
verified model and isolated environment for inference; ordinary `.venv` does not
need the SDK. `ENCODER_ENVIRONMENT_08R1.json` pins actual binary wheel hashes; this
macOS arm64 environment is not a certified Linux binary environment. SDK/source
pins, tokenizer hashes and index manifests are in the receipt. No model outputs
are necessary to run CI; unit tests use inert SDK doubles and tiny fixed vectors.

```bash
# Explicit commands only; never invoked by the application.
# Choose unused output names; neither calibration nor evaluation overwrites files.
PYTHONPATH=src /Users/macbook/Hack/.archimind-08r1/venv/bin/python \
  scripts/evaluate_furniture_embeddings.py calibrate \
  --model-directory /Users/macbook/Hack/.archimind-08r1/model \
  --index-directory /tmp/08r1-new-indices \
  --policy /tmp/08r1-new-policy.json --output /tmp/08r1-new-development.json
# Inspect policy hash and equality to the frozen original before test replay.
PYTHONPATH=src /Users/macbook/Hack/.archimind-08r1/venv/bin/python \
  scripts/evaluate_furniture_embeddings.py evaluate --hybrid \
  --model-directory /Users/macbook/Hack/.archimind-08r1/model \
  --index-directory /Users/macbook/Hack/.archimind-08r1/index-v2 \
  --policy /Users/macbook/Hack/.archimind-08r1/evidence/abstention-v2.json \
  --policy-sha256 c00951281f3edbc94c014212ded1d59f6736ce7d4edc7e72845d3909aa8ff06d \
  --output /tmp/08r1-new-test-replay.json
```

The first command recomputes the same predeclared development grid; it is not
permission to change thresholds after seeing test results. Inference sets offline
flags, verifies local bytes/versions and guards Python network/process events.
The acquisition CLI is separate and never runs automatically. Local snapshot
readers never rebuild on search. Files are task-owned, immutable by convention
and externally hash-bound, not signed security attestations.

Accepted semantic signatures: development
`70b79a32c6340295e45d8f58847b73dfae05693d17532a90a079f1224cd30847`;
nonhybrid original/held-out
`c5adfea4986aae98d520007ed1023a715b9e807e24d3f5451c7695ffaa1d233a`;
final including RRF
`674eae30361ad15e7f4556620170e25026ca35b66a4006bacb84e2b1e18663c0`.
All nonhybrid per-query semantic fields matched across two separate evaluation
processes. The unchanged 08R0 replay matched its original output digest
`6063a66e344188f60f2469453c19b3d21fd7a44ef4bb99b99c89b81bd3b34d31`.

Checkpoint 1: `48746bbc2b3d90810f9ae7fbf328f31ba3d257e9`,
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40817499026).
Checkpoint 2: `e979fc57867b52f068fc13c8a7a6a7a8326aa0ec`,
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40818929444).
The final commit/hash and actual CI outcome belong in the delivery response.
No UI change required a new browser inspection; existing Streamlit/renderer tests
and fresh health checks verify regressions, not a new semantic user experience.


A preservation audit compared **132 existing production/frontend/data/dependency
files** against the starting commit: all byte-identical, including original 08R0
queries, canonical models, geometry, assets, both renderer sources/bundles and
catalog search text. Sorted path/SHA-256 ledger digest:
`a4f140ade91b35a9131c43fc703bffde1b43fdd5ea74e48b4a27cadf2f07273f`.
Only new retrieval implementation, focused/packaging tests, benchmark splits and
documentation were added or updated. `.agents/` and `.claude/` remain untouched.


### Exact changed files across 08R1

- `MANIFEST.in`
- `README.md`
- `data/benchmarks/furniture_embedding_development_08r1.json`
- `data/benchmarks/furniture_embedding_held_out_08r1.json`
- `docs/data/ENCODER_ACQUISITION_08R1.json`
- `docs/data/ENCODER_ENVIRONMENT_08R1.json`
- `docs/data/RETRIEVAL_EMBEDDING_08R1.json`
- `docs/data/RETRIEVAL_EMBEDDING_08R1.md`
- `docs/developer/FURNITURE_RETRIEVAL_ARCHITECTURE.md`
- `docs/developer/STATUS.md`
- `scripts/acquire_furniture_encoder.py`
- `scripts/build_furniture_embedding_index.py`
- `scripts/evaluate_furniture_embeddings.py`
- `src/archimind/retrieval/embedding_experiment.py`
- `src/archimind/retrieval/embedding_index.py`
- `src/archimind/retrieval/hybrid.py`
- `src/archimind/retrieval/offline_encoder.py`
- `src/archimind/retrieval/semantic.py`
- `tests/embedding_helpers.py`
- `tests/test_asset_catalog_packaging.py`
- `tests/test_retrieval_acquisition.py`
- `tests/test_retrieval_embedding_experiment.py`
- `tests/test_retrieval_embedding_index.py`
- `tests/test_retrieval_hybrid.py`
- `tests/test_retrieval_offline_encoder.py`
- `tests/test_retrieval_semantic.py`


### Final local release verification

- **1,754 Python tests passed in 117.49s**, zero failures/skips: all 1,688 baseline
  tests retained plus 66 new cases/tests. Focused retrieval: **173 passed in 8.51s**.
- **75 frontend tests passed**, zero failures/skips; syntax and production build
  passed. Committed viewer assets remain byte-identical. Product registry and
  existing integrity/native-rendering regressions passed.
- Ruff lint passed; **171 files already formatted**. Default and experiment
  `pip check` both report no broken requirements. Fresh Streamlit health was
  **HTTP 200 ok**; the temporary server stopped.
- Real offline source/wheel builds, no-index/no-dependency isolated install and
  outside-repository fixed-vector semantic/hybrid searches passed. Missing model
  cache fails safely; FastEmbed/ONNX Runtime/tokenizers are not imported by these
  installed-package calls. Existing model assets are preserved; no encoder
  weights, vectors or benchmark corpus is included in the wheel. Source archives
  include CLI/tests/reports and frozen query fixtures.
- Real model results are from the separate guarded CPU benchmark, never CI units.
  Original lexical replay and cross-process semantic results remained unchanged.
  No paid/live provider, Codex subprocess, new furniture acquisition or app
  behavior change occurred. Labels still await independent human review.
