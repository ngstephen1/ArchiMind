# P2a SSR adapter (2026-11-08)

Exact numbers, hashes and the command: [DATASET_SSR_P2A.json](DATASET_SSR_P2A.json).
All numbers come from the real pinned shards (SSR `b606183e`, MIDI id lists `156fc531`).
Code: `src/archimind/datasets/ssr_adapter.py`, CLI `ssr-build`.

## Result

| | Count |
| --- | --- |
| SSR bedroom rows | 7,328 |
| Scene references | **4,168** (53 canonical, 4,115 reference_only) |
| Exclusions | 3,160: 2,903 irregular rooms, 252 duplicate geometry, 3 no mapped object, 2 no quarter-turn object |
| Objects in scenes | 20,437, of which 18,631 are admitted with a category and footprint |

The local pack (`ssr-bedrooms-p2a`, 11.9 MB) passes `verify-pack`. Rebuilding it from
the same inputs gives the same `snapshot_id`
(`e0f2496e2cbf1e74019366e89afcb90325cb84d7dfc9bee244341033f2c01654`). The pack is
not in Git. Rebuild it with the command in the JSON receipt.

## What changed from the P1 probe

- **Category coverage is much higher than P1 predicted.** P1 found MIDI categories for
  3,047 of 7,722 SSR jids by exact match. Most other jids are scale variants of the
  same model (`<uuid>-(0.74)-(1.0)-(0.68)`). Looking up the 36-character model id
  maps all but 729 objects. The stored `jid` is that model id, and the real extent
  stays in `size_raw`.
- **Canonical drops from 55 to 53.** A canonical room needs every object categorized,
  and two rooms contain an object that has no MIDI category.
- **252 duplicates, not 372.** P1 counted duplicates among all rows. Here the 120 other
  duplicates are in rooms that were already excluded for other reasons.

## Checks recorded per scene

| Check | Result |
| --- | --- |
| `wall_containment` | 990 PASS, 3,178 FAIL (zero tolerance; mostly flush placement, see P1) |
| `solid_overlap` | 1,956 PASS, 2,212 FAIL |
| `floor_contact` (lights excluded) | 4,051 PASS, 117 FAIL |
| `door_clearance` | NOT_VERIFIABLE for all: the source records no openings |
| `split_agreement` with MIDI | 1,789 PASS, 604 FAIL, 1,775 not in MIDI |

Only canonical scenes may become a `RoomDesign`. Reference-only scenes are labelled
footprints with these check results attached.

## Open gates

- **Permission.** The SSR card's metadata says `mit`, but its text defers to the
  3D-FRONT terms. The local pack was built with a **provisional** record:
  `local_research` allowed and every public use `unknown`. `build_pack` therefore
  refuses a public pack (`source_not_public`). The owner must decide the permission
  record before any public use.
- **729 unmapped objects** wait for 3D-FUTURE `model_info.json` (P2b, blocked on
  Kaggle credentials). Mapping them requires a `category_map_version` bump.
