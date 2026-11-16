# P2b 3D-FUTURE categories (2026-11-16)

Exact numbers, hashes and the command: [DATASET_FUTURE_P2B.json](DATASET_FUTURE_P2B.json).
All numbers come from real pinned inputs: SSR `b606183e`, MIDI id lists `156fc531`,
and 3D-FUTURE `model_info.json` (Kaggle `tobetheonly/3d-future-model` v1, SHA-256
`7b73e8cb…`). Code: `src/archimind/datasets/future.py`, and the `--future-*`
options of `ssr-build`.

## Result

| | P2a | P2b |
| --- | --- | --- |
| Objects without a category (`unmapped_category`) | 729 | **0** |
| Objects admitted with category and footprint | 18,631 | **19,374** |
| Scene references | 4,168 | **4,172** |
| Canonical / reference_only | 53 / 4,115 | 53 / 4,119 |
| Exclusions | 3,160 | 3,156 (2,903 irregular, 252 duplicate, 1 no quarter-turn object) |

The local pack `ssr-bedrooms-p2b` (11.4 MB) passes `verify-pack`. It records two
sources, `ssr_3dfront` and `future_3d`. Rebuilding it gave a byte-identical pack with
snapshot `8cfb31258aa7c4b7f29ce114661d59c1709d95e4d4ca16f5929e78e5089e9422`. The pack
is not in Git.

## How categories are assigned

1. **3D-FUTURE is the primary source.** Each `model_id` gets its super-category,
   rewritten to the MIDI spelling (`Cabinet/Shelf/Desk` becomes
   `Cabinet_Shelf_Desk`), so one category map serves both sources.
2. **MIDI is a strict cross-check.** All 6,486 MIDI furniture jids are in
   3D-FUTURE and every one agrees. A disagreement would stop the build. No jid is
   known only to MIDI.
3. **`raw_category` is now the finer 3D-FUTURE category.** The most common are
   Nightstand (4,843), King-size Bed (2,978), Pendant Lamp (2,611), Wardrobe (2,290)
   and Ceiling Lamp (1,212). ArchiMind categories still map from super-categories,
   so `cabinet_shelf_desk` still mixes nightstands, wardrobes and TV stands. P3
   search can tell them apart by `raw_category`. 964 `Others` and 4 `Bed` objects
   have no finer category in the source.

## Decisions

- **Mirrored jids are accepted.** About 380 SSR objects use mirrored copies,
  `<uuid>-(-1.0)-(1.0)-(1.0)`, which P2a rejected. SSR records their `size` as
  positive, so their footprints are unaffected. They map to the base model id.
  Only 8 end up admitted, because most sit in irregular rooms. The mirror sign is
  not stored, but it can be recovered from the source row through
  `source_object_id`. Any future mesh rendering must re-read it from there.
- **Floor lamps must touch the floor.** Lighting stays exempt from `floor_contact`
  (ceiling and wall lights), except `Floor Lamp`. Among 166 admitted floor lamps,
  this adds 3 floor-contact failures.
- **Versions:** `category_map_version` and `adapter_version` go from 1.0.0 to 1.1.0.
  Geometry is unchanged, so `transform_version` stays at 1.0.0.

## What moved in the checks

Newly categorized objects now take part in every check, so some rooms that passed
before now fail:

| Check | P2a FAIL | P2b FAIL |
| --- | --- | --- |
| `floor_contact` | 117 | 147 (27 from newly categorized objects, 3 from floor lamps) |
| `solid_overlap` | 2,212 | 2,336 |
| `wall_containment` | 3,178 | 3,226 |

## Correction to P2a

P2a said canonical dropped from 55 to 53 because two rooms held objects with no MIDI
category. That was wrong. With every object categorized, canonical is still 53. The
two rooms counted by P1 are exact geometry duplicates of canonical rooms that are
kept (`7fd782e5…/SecondBedroom-17563` and `b9301a72…/Bedroom-15959`), so
deduplication removes them.

## Open gates

- **Permission.** The `future_3d` source carries a **provisional** record:
  `local_research` allowed and every public use `unknown`. The Kaggle mirror lists
  its license as `Unknown`, and the upstream 3D-FUTURE terms have not been
  reviewed. Only `model_info.json` categories are used, with no meshes or images.
  `build_pack` refuses a public pack until the owner decides.
- **MIDI provenance.** The pack still has no `midi_3dfront` manifest, even though
  MIDI ids supply the `split_agreement` check and the category cross-check. This is
  unchanged from P2a. Add one before any public pack.
