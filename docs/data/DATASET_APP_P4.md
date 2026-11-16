# P4: dataset references in Chat bedroom (default off)

Status: **IMPLEMENTED as a thin integration, with local research packs only.** Public use is blocked by
permissions. There is no reference-mesh viewer because no qualified meshes exist.

## Base

- The branch `data/dataset-reference-pilot` is based on `origin/main` `fc19b0b`, which already contains the
  owner's merged and reviewed 09A checkpoint (PR #6, "Record verified 09A checkpoint") and PR #7. No rebase was
  needed and there were no conflicts.
- **Hash-pinned files are untouched.** These are the 142 files pinned by `FURNITURE_EXPANSION_08F1.json`, including `app.py`, every other
  UI module and the whole `frontend/realistic_viewer`.
- **Only shared file edited: `src/archimind/ui/bedroom_chat.py`.** It is not hash-pinned. The edit adds one call that mounts the panel once a
  draft is ready, and makes *New conversation* also clear the `dataset_ref*` keys.

## Behaviour

| Server setting | Effect |
|---|---|
| `ARCHIMIND_ENABLE_DATASET_REFERENCES` unset or `0` (default) | Nothing is rendered and no pack is loaded |
| `=1`, no `ARCHIMIND_DATASET_REFERENCE_ROOT` | Panel shows "No reference pack is configured" |
| `=1`, a local research pack, default `public` audience | "approved for local research only" (blocked) |
| `=1`, a local pack and `ARCHIMIND_DATASET_REFERENCE_AUDIENCE=local` | Search and previews work |
| Corrupt or changed pack | "The reference pack is unavailable"; chat, choices and generation still work |

- **References for next specification** appears under the ready draft, separate from product choices
  and from the displayed A/B results. Nothing is searched until the user clicks **Find bedroom references**.
- **Each hit** shows its source and scene identity, split, tier, room size, matched categories (found/requested), opening
  knowledge, the factual reasons and any identical aliases. Pack attribution and limitations are listed below the hits.
- **Preview reference** shows one hit at a time.
  - Canonical hits are drawn with the existing Plotly floor-plan renderer, labelled as unvalidated
    footprints with unknown doors and windows.
  - Hits with quarter-turn furniture are not drawn, and the panel says why; a footprint table is shown instead.
  - A preview is refused when the pack snapshot has changed since the search.
- **State.** Reference state lives only under the `dataset_ref*` session keys.
  - A changed draft (new measurements or requests) clears the reference result and leaves layouts alone.
  - Reset clears references but keeps the displayed A/B results.
- **No new calls.** Reference controls make no model, provider, network, acquisition or generator calls.

## Evidence

- **`tests/test_dataset_references_ui.py`** (5 AppTests, with the same offline socket/OpenAI guards as the 09A UI tests) covers:
  - default off with no pack load
  - unconfigured, local-only and corrupt packs
  - search, both preview kinds and exactly one preview per run
  - preparation and layout results kept by identity, with 1 interpretation call and 1 generation call
  - reset
  - changed measurements invalidating only references
- **Real pack** (`ssr-bedrooms-p2b`, local audience, AppTest):
  - The 09A fixture draft (5 × 4 × 2.7 m, bed + desk) returned 3 hits with full coverage and a 1.9–2.7% size difference.
  - The top hit has quarter turns, so the footprint table was shown and no floor plan was drawn. There was no exception.
  - The first click, including verifying and indexing the pack, took 4.4 s. A cached preview click took 0.8 s.
  - Interpretation ran once; the generator ran 0 times.
- **Full suite on Windows** (`PYTHONUTF8=1`, with the loopback plugin):
  - Baseline (clean worktree of the P3 commit): 17 failed, 2,164 passed, 55 errors.
  - With P4: 18 failed, 2,168 passed, 55 errors.
  - The one failure that appears only with P4 is the owner's file-preservation test. It is caused by
    this checkout's CRLF line endings: `furniture_assets.py` is unchanged, and its CR-stripped bytes match the pin.
    The LF worktree passes.
  - Every other failure exists in both trees and none involve datasets. Details are in `DATASET_APP_P4.json`.

## Windows note

The app's UI tests forbid `socket.bind`. On Windows, asyncio builds its loopback self-pipe with
`bind`, so those tests fail on Windows before any app code runs. This is the source of the roughly 85 failures and
106 errors seen in earlier phases. It does not occur on the owner's macOS. Local runs here used a
scratchpad-only pytest plugin that builds just that loopback pair. All other guards stay in force. Some catalog
tests also need `PYTHONUTF8=1` on Windows, because `read_text()` defaults to cp1252.

## Not done

- **Reference-mesh viewer.** The separate Components V2 viewer for qualified GLBs was not built: no reference
  mesh is qualified (M3 not run), and the viewer sources and `build.mjs` are hash-pinned owner files.
- **Browser screenshots.** Browser checks at 1440 × 1000 and 390 × 844 were not taken. The evidence is AppTest only.
- **Public demo.** It stays blocked until the source permissions allow public use.
- **README.** `README.md` was not edited. The flags are documented in `docs/developer/DATASET_SETUP.md`.
