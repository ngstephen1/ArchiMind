# Offline embedding experiment — Task 08R1

**Checkpoint 2: semantic experiment complete; hybrid/release verification follows.**
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
Final full regression, hybrid, packaging and technology decision belong to the
third delivery checkpoint.
