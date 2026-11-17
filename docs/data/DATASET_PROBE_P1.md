# P1 dataset probe (2026-11-06)

Exact numbers, hashes and commands: [DATASET_PROBE_P1.json](DATASET_PROBE_P1.json).
Every number below is from real pinned data, not fixtures.

| Source | Gate | Revision / version | Size |
| --- | --- | --- | --- |
| SSR-3DFRONT | **PASS** | HF `b606183e56d972f85850125f9191932cbea654c3` | 29.3 MB (3 parquet shards, 7.4 MB) |
| MIDI-3D / 3D-Front | **PASS, bounded prefix only** | HF `156fc5312ea613d4e92cbf5da1fddfa61bbad3b2` | 1.685 TB, all gzip |
| 3D-FUTURE (Kaggle mirror) | **PASS** (Colab run `pilot-001`, 2026-11-16) | `tobetheonly/3d-future-model` v1 | 65.9 GB, 87,908 files |

## Conventions (proven, not assumed)

SSR conventions come from ReSpace's own code (`get_xz_bbox_from_obj`,
`get_y_angle_from_xyzw_quaternion` at `b1a4b32b`):

- Y-up meters. Room bounds are centered on the origin, with the floor at `y = 0`.
- `size` is the full extent, and `pos` is the bottom-center of the object.
- `rot` is `[x, y, z, w]`.

ReSpace's 2D footprint rotates in the opposite sense to its own yaw. That makes no
difference for quarter-turn boxes, but facing must be read from the quaternion.

## SSR bedroom yield (7,328 bedroom rows)

| Result | Rows |
| --- | --- |
| Irregular (non-rectangular) room | 2,903 (40%) |
| Rectangular, every object at zero yaw, inside the walls, no solid overlap: **canonical** | **55** |
| Rectangular, at least one admitted object: **reference_only** | 4,369 |
| No admitted object | 1 |

- Of the rectangular rooms, 76% have objects only at quarter turns, and 4.8% have
  objects only at zero yaw. Without the reference-only tier, almost no real bedroom
  would be usable.
- Objects poking past walls are mostly flush placement: the median object is 3.5 cm
  inside the wall, and only 0.1% of objects poke out more than 20 cm. Zero tolerance
  keeps these rooms out of the canonical tier. They stay reference-only with a
  labelled containment result.
- About 20% of objects sit 1.9 to 2.5 m above the floor (ceiling and wall lights).
  The category map must separate lighting from floor furniture.
- 372 rows duplicate another row's geometry, and 84 of those duplicate groups span
  splits. The pack must deduplicate and record aliases.
- **Split rule:** rows carry both a room-type split and a combined split. For
  example, `["bedroom_train", "all_val"]` appears inside the *val* parquet file.
  Only `bedroom_*` is used.

## SSR ↔ MIDI identity join

`file_id[:36] + "/" + room_id` equals the MIDI room id exactly, so the join needs no
name or shape matching.

- **4,080 of 7,328** SSR bedroom rows are MIDI rooms. That includes **52 of the 55**
  canonical rooms.
- **Split disagreement:** 483 SSR-train bedrooms are MIDI-test rooms, and 252
  SSR-test bedrooms are MIDI-train rooms. Any evaluation that combines the two
  sources leaks. The pack records both splits.
- MIDI furniture ids give the real 3D-FUTURE super-category for **3,047 of 7,722**
  SSR jids. The rest wait for FUTURE's `model_info.json`. SSR descriptions are
  untrusted text and are never used as categories.

## MIDI geometry access

The geometry archives are gzip-compressed. The first bytes (`1f8b`) were checked
for `3D-FRONT-SCENE.partaa`, `3D-FRONT-SURFACE.partaa`, `3D-FRONT-RENDER.tar.gz` and
`3D-FRONT-TEST-SCENE.tar.gz`. The later `.partab`… files continue those gzip
streams. Gzip has no random access, so a specific room cannot be fetched on its own. Streaming a
prefix is bounded and works:

- A 64 MiB prefix of `3D-FRONT-TEST-SCENE.tar.gz` held 6 complete rooms: 43 GLBs,
  81 MB expanded, read and then discarded.
- Each room has a room GLB, a `_full` GLB and one GLB per object, named with its
  MIDI furniture id.
- All 4 bedrooms in the prefix exist in SSR. All are in the MIDI test split.

This means MIDI rooms are "whatever comes first in the archive", not chosen rooms.
P2c streams at most 1 GiB and keeps only bedrooms that join SSR.

## 3D-FUTURE (Colab run `pilot-001`, 2026-11-16)

The run used `ce22f92` plus notebook hotfix cells. Those fixes are now commit
`3d9971be`, so later runs no longer need the hotfix cells. The same run also repeated
the SSR and MIDI probes. Every SSR number matched the local run, the shard SHA-256
values were identical, and the MIDI id lists were the same sizes.

- **Layout:** 16,563 model directories under `3D-FUTURE-model/`. Each has `image.jpg`,
  `model.mtl`, `raw_model.obj` and (almost always) `texture.png` and
  `normalized_model.obj`. Only 5,095 have `bbox_vertices.npy`. There are two
  top-level files: `categories.py` and `model_info.json`.
- **`model_info.json`** (4.0 MB, SHA-256 `7b73e8cb…`): 16,563 rows with unique
  `model_id`s, one for each model directory, with no directories missing a row. The
  fields are `super-category`, `category` (50 values), `style`, `theme` and
  `material`.
- **MIDI join:** all 6,486 MIDI furniture jids are in `model_info.json`. Their
  super-categories agree once separators are normalized: MIDI writes
  `Cabinet_Shelf_Desk` and `Pier_Stool`, while 3D-FUTURE writes `Cabinet/Shelf/Desk`
  and `Pier/Stool`.
- **SSR bedroom coverage:** `model_info.json` categorizes **7,699 of 7,722** SSR jids,
  matched directly or through their base model id. MIDI alone covers 6,440. Coverage
  by tier is 108/108 canonical and 5,043/5,051 reference_only. All 23 unresolved jids
  are mirror variants, `<uuid>-(-1.0)-(1.0)-(1.0)`. `base_jid` rejects the negative
  scale, but every base uuid is in `model_info.json`.
- **Access:** the file list comes from `GET /datasets/list/{owner}/{slug}`, at most
  200 files per page. Kaggle rate-limits (429) partway through, and one retry clears
  it. A single file comes from `/datasets/download/{owner}/{slug}/{path}` with `/`
  encoded as `%2F`. That redirects to the file on its own, not to the 66 GB bundle.
- The license field is still `Unknown` on the mirror. It stays local research only,
  like the other sources, until the owner records a permission decision.

## Decisions for P2

1. **SSR (P2a)** runs locally, because the whole source is 29 MB. It produces
   canonical and reference_only `SceneReference`s, keeps both splits, and
   deduplicates by geometry digest.
2. **Categories** come from MIDI ids now, then FUTURE `model_info.json`. Unmapped
   objects are excluded from footprints and keep their `jid`.
3. **MIDI (P2c)** streams at most 1 GiB in Colab and keeps up to 5 bedrooms that
   join SSR.
4. **FUTURE (P2b)** is unblocked. It maps jids to categories from
   `model_info.json`, with MIDI as a cross-check. It must decide how mirror variants
   (negative scale) are handled before admitting them.
