# Dataset references: P0 contracts and harness

Package: `src/archimind/datasets/`. Tests: `tests/datasets/`. Remote runs:
[DATASET_COLAB.md](DATASET_COLAB.md).

Dataset references are **reference material**: they are not products, catalog
records, product bindings or planning approvals. The app will read only a verified
reference pack, and works unchanged when no pack is configured.

## Status

| Phase | State | Evidence |
| --- | --- | --- |
| P0 contracts, safe I/O, stages, pack, CLI | IMPLEMENTED (synthetic only) | `tests/datasets` (offline) |
| P1 probe (inventory and yield) | SSR PASS, MIDI PASS (bounded prefix), FUTURE PASS (Colab `pilot-001`) | [DATASET_PROBE_P1.md](../data/DATASET_PROBE_P1.md) |
| P2a SSR adapter | IMPLEMENTED; real local pack verified (4,168 scenes, 53 canonical); permission provisional | [DATASET_SSR_P2A.md](../data/DATASET_SSR_P2A.md) |
| P2b FUTURE categories | IMPLEMENTED; real local pack verified (4,172 scenes, 53 canonical, 0 unmapped objects); FUTURE permission provisional | [DATASET_FUTURE_P2B.md](../data/DATASET_FUTURE_P2B.md) |
| P2c MIDI adapter | IMPLEMENTED; 5 bedrooms audited locally (alignment, camera, association PASS 5/5); depth units and surfaces not verified | [DATASET_MIDI_P2C.md](../data/DATASET_MIDI_P2C.md) |
| P3 search facade over a real pack | IMPLEMENTED; local pack evaluated (category precision 1.0, deterministic, p50 17 ms); public audience blocked by permissions; no assets yet | [DATASET_SEARCH_P3.md](../data/DATASET_SEARCH_P3.md) |
| P4 app wiring | IMPLEMENTED default-off in Chat bedroom (local packs only; public blocked; no mesh viewer) | [DATASET_APP_P4.md](../data/DATASET_APP_P4.md) |
| P5 layout-habit statistics | IMPLEMENTED; `habits.json` reproducible byte for byte from the P2b train split; every habit n ≥ 100 | [DATASET_HABITS_P5.md](../data/DATASET_HABITS_P5.md) |
| P6 habit scorer and generator benchmark | IMPLEMENTED; baseline bed only-long-edge 30.6% generated vs 12.9% real (val); held-out check PASS (median penalty 0.048 val / 0.055 test vs 0.198 generated) | [DATASET_HABITS_P6.md](../data/DATASET_HABITS_P6.md) |
| P7 preview every reference | IMPLEMENTED; quarter-turn references drawn by an own Plotly figure; all 4,170 real references previewable (0 failures) | [DATASET_PREVIEW_P7.md](../data/DATASET_PREVIEW_P7.md) |
| Chat prompt-variation suite | IMPLEMENTED; 30 val-room prompts in 10 styles, live run 26/30 correct; failures: typos 0/3 (evidence checks), 1 feet case (duplicated hard constraint) | [CHAT_PROMPT_SUITE.md](../data/CHAT_PROMPT_SUITE.md) |

Synthetic fixtures prove the engineering only. They say nothing about real source
schemas, conventions or yield.

## Modules

| Module | Responsibility |
| --- | --- |
| `contracts.py` | Frozen, strict records: `SourceManifest`, `PermissionRecord`, `SceneReference` (tiers `canonical` and `reference_only`), `ExclusionRecord`, `ReferenceAsset`, `PackManifest`. Portable relative paths only. Identifiers are namespaced (`ssr:`, `midi:`, `future:`). |
| `canonical.py` | Canonical JSON (sorted keys, LF, floats rounded to 1e-9, no NaN), strict parsing (duplicate keys rejected) and bounded JSONL. Identical content always has the same digest. |
| `geometry.py` | Recorded `Convention` (basis, quaternion order, pivot, size semantics), rigid basis checks, quaternion sign normalization, quarter-turn classification and canonical lower-left boxes. Tilted and non-quarter-turn objects are rejected, never snapped. |
| `safe_io.py` | `https`-only bounded and resumable downloads, capacity floor, archive extraction safe on Windows (traversal, reserved names, case-insensitive duplicates, links, expansion bombs), numeric-only NPY loading and embedded-only GLB headers. |
| `stages.py` | Content-addressed, resumable stages (`_COMPLETE` with per-file SHA-256) and the atomic `sync_tree` used for Drive checkpoints. |
| `pack.py` | `build_pack`, `verify_pack` and `load_pack`. `load_pack` never raises: it returns `ready`, or `unavailable` with a reason code and no paths. |
| `ssr.py` | Proven SSR conventions, room/object classification, `room_key`, bedroom split parsing and the yield probe. |
| `midi.py` | MIDI id parsing, positional room/furniture index, test-tail check, jid categories and the SSR join report. |
| `remote.py` | Pinned Hugging Face trees (with LFS SHA-256), Kaggle listings and capped streaming listings of `.tar.gz` prefixes. |
| `ssr_adapter.py` | P2a: SSR rows to `SceneReference`/`ExclusionRecord`. Categories from 3D-FUTURE `model_info.json`, cross-checked against MIDI ids. Scale-variant and mirrored jids map through their model id. `raw_category` holds the finer 3D-FUTURE category., tiers, per-scene checks, geometry deduplication with recorded aliases. |
| `future.py` | P2b: validated 3D-FUTURE `model_info.json` (super-categories in MIDI spelling, finer categories) and the strict MIDI cross-check. |
| `glb.py` | P2c: bounded GLB reader (node hierarchy, world bounds, triangles, texture sizes). |
| `midi_adapter.py` | P2c: MIDI room files, object association, view inventory, SSR-to-MIDI similarity fit and camera-convention test; used by `midi-audit`. |
| `search.py` | P3: `load_reference_pack`, `reference_query_from_chat`, `search_references`, `prepare_reference_preview`; deterministic in-memory lexical index with exact-duplicate folding. |
| `search_eval.py` | P3: expected-category, self-retrieval, empty-query, determinism and latency evaluation (`ref-eval`). |
| `habits.py` | P5/P6: orientation-free layout habits (bed wall edge, chair-table gap, wall contact, floor coverage) fit on `train` with aliases folded (`habit-stats`); one measuring routine for pack scenes and app designs. |
| `habit_bench.py` | P6: `score_layout_habits` over 24 fixed rooms × 50 seeds of the unchanged generator plus the held-out `val`/`test` check (`habit-bench`). |
| `prompt_suite.py`, `prompt_eval.py` | Chat prompt-variation cases from reference rooms with known outcomes; record live interpreter answers once and re-score them offline through current rules (`prompt-suite`, `prompt-eval`). |
| `cli.py` | `env`, `sync`, `verify-pack`, `fixture-pack`, `fetch`, `probe-hf`, `probe-kaggle`, `probe-tar-prefix`, `probe-ssr`, `probe-join`, `ssr-build`, `midi-audit`, `ref-search`, `ref-eval`, `habit-stats`, `habit-bench`, `prompt-suite`, `prompt-eval`. Credentials are never forwarded on redirects. |
| `ui/dataset_references.py` | P4: default-off *References for next specification* panel in Chat bedroom; explicit search and preview; separate `dataset_ref*` session state. P7: `reference_figure` draws quarter-turn references. |

## Tiers

- **canonical**: every object is admitted at zero yaw in a rectangular room, so the
  room can become a `RoomDesign` and use the existing spatial checks.
- **reference_only**: objects may be at quarter turns. These are shown as labelled
  oriented footprints, never as validated layouts, and never enter canonical schemas.

Openings that the source does not record are `unknown`. A scene with unknown
openings cannot report door or circulation checks as `PASS`.

## Snapshot identity

`snapshot_id` hashes the pack identity, the transform and category-map versions and
every file's path, kind, size and SHA-256. It does not hash build time or builder,
so rebuilding identical content gives the same snapshot.
