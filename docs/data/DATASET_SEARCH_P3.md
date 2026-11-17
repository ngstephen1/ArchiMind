# P3: reference search facade

Machine-readable receipt: [DATASET_SEARCH_P3.json](DATASET_SEARCH_P3.json).

**Status: implemented and evaluated on the real local pack.** The public audience is blocked by
permissions, as designed. The app is not wired up (P4), no product or catalog code changed, and
nothing makes a model call.

## Facade (`src/archimind/datasets/search.py`)

| Function | Behaviour |
|---|---|
| `load_reference_pack(root, *, audience="public")` | Re-verifies the pack (hashes, records, snapshot, permissions) and builds the in-memory index. It never raises. Any failure returns `unavailable` with a reason code and no path. |
| `reference_query_from_chat(draft)` | Turns a ready `CatalogChatDraft` into a `ReferenceQuery`. Room W/D/H come from the draft's validated room. Furniture comes only from intents quoted in user turns, and keywords are alphanumeric tokens of those quotes. Unquoted or unsupported intents are dropped and recorded in `notes`. |
| `search_references(query, *, pack)` | Returns separate scene and asset hits (default 3, at most 10), with status `matches`, `empty` or `unavailable`, plus the snapshot id and a query digest. |
| `prepare_reference_preview(hit, *, pack)` | Returns footprint facts for a scene hit. Hits from another snapshot are rejected (`stale_snapshot`). For asset hits, the GLB is re-hashed first (`asset_missing` / `asset_digest_changed`). |

**Ranking.** Scenes are ordered by requested-category coverage (descending), then relative room-size
difference (ascending; width/depth swaps are allowed and reported), then keyword overlap
(descending), then reference id. Assets rank separately: compatible category, then keyword overlap,
then asset id. An asset's category comes only from scene objects that share its jid.

**Constraints are not silently broadened.** When categories are requested, a scene with zero
coverage is not returned. Partial matches show `found` against `requested` for every request.
Keywords affect ranking only.

**Identity.** Scenes with byte-identical content are folded into one hit, with the extra ids and
their splits listed as `aliases` / `alias_splits`. The real pack has 2 such pairs. They are the
same 2 duplicates noted in P2a, and in both cases the alias is also in the `train` split. Scenes
that only look alike are never merged.

**Untrusted text.** Explanations are built from checked facts: counts, dimensions, tier and
openings. Source text such as `raw_category` is never echoed, so an injection-like category string
cannot reach the output. Results contain no filesystem paths and no URLs.

## Evaluation on `ssr-bedrooms-p2b` (snapshot `8cfb3125…`, local audience)

The load + verify + index step took 1.9 s and indexed 4,170 scenes (4,172 minus 2 folded duplicates).

| Check | Result |
|---|---|
| Expected-category retrieval, 13 requests (8 super-categories + nightstand, wardrobe, bookcase, desk, armchair) | precision 1.0 for every request, 10 hits each |
| Self-retrieval, canonical (53) | recall@1 0.566, @3 0.736, @10 0.925 |
| Self-retrieval, reference_only (200-scene deterministic sample) | recall@1 0.58, @3 0.77, @10 0.97 |
| Empty query | `empty` / `empty_query`; no arbitrary scenes |
| Same queries over an index built from reversed input | identical result digests |
| Latency (266 queries, CPU) | p50 17 ms, p95 90 ms, max 188 ms |
| Public audience | `unavailable` / `pack_not_public` |

**Self-retrieval misses are ties, not ranking errors.** The self-retrieval query is a scene's own
room size and category counts. All 23 canonical rank-1 misses are other scenes that tie exactly
(coverage 1.0, size difference 0.0), and the reference id breaks the tie, as specified. Many
bedrooms share standard sizes (e.g. 4.0 × 3.5 × 2.6 m).

**Category mapping was corrected from evidence.** In 3D-FUTURE, *Desk* falls under *Table* (416
objects) and *armchair* under *Sofa* (34 objects). So the chat functions `desk` and `armchair` map to
`table/desk` and `sofa/armchair`. Before that fix, both requests returned 0 hits.

Sample search: a 4.0 × 3.5 × 2.7 m room with a bed, 2 nightstands and a desk. The top hit is
`ssr:6417999f…:MasterBedroom-6822`. It covers all requests, its size difference is 2.2%, and it is
`reference_only`. Its preview shows oriented footprints, with labels saying the layout is not
validated, doors and windows are unknown, and no meshes are approved.

## Gate

- **Shuffled input.** Shuffled input gives the same snapshot and byte-identical results (tests and real pack).
- **Failure cases covered by tests.** Stale snapshots, ineligible audiences, missing or tampered packs, missing or changed asset files, exact versus near duplicates, empty queries, no matches and injection-like source text.
- **Product code untouched.** No file outside `src/archimind/datasets/` and `tests/datasets/` changed. `FurnitureSearchRequest`, `resolve_result()` and the ABO product path are as they were. A FUTURE hit is an `AssetHit` with no product or binding fields.
- **Infrastructure fix.** `atomic_write_bytes` now retries `os.replace` briefly (bounded to about 1.3 s) on Windows sharing violations. Without this, the new tests failed intermittently with `WinError 32`.

## Not done / blocked

- **No reference meshes.** The pack has no `ReferenceAsset`s because M3 (FUTURE mesh qualification) was not run. Asset search is implemented and tested on synthetic data only.
- **No public pack.** Public use needs a documented public permission for SSR derived metadata. Every public use is still `unknown`.
- **Openings unknown.** The source records no openings, so door and circulation checks are unverified in every hit.
- **No layout-quality claims.** These metrics describe retrieval only. The generator is unchanged.
