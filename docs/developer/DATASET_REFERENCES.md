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
| P1 probe (inventory and yield) | SSR PASS, MIDI PASS (bounded prefix), FUTURE NOT RUN | [DATASET_PROBE_P1.md](../data/DATASET_PROBE_P1.md) |
| P2 SSR / FUTURE / MIDI adapters | NOT STARTED | |
| P3 search facade over a real pack | NOT STARTED | |
| P4 app wiring | NOT STARTED | |

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
| `cli.py` | `env`, `sync`, `verify-pack`, `fixture-pack`, `fetch`, `probe-hf`, `probe-kaggle`, `probe-tar-prefix`, `probe-ssr`, `probe-join`. Credentials are never forwarded on redirects. |

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
