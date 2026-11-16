# Dataset references: implementation plan for the next steps

Status: **proposal for review**. Nothing here is implemented yet.
Scope: local research use only. The ~100 MB of data already on disk is all this plan needs. Nothing new is downloaded.

## Goal

Turn the 4,170 reference bedrooms from "examples shown next to the generator" into **measurable
improvements in generated layouts**, and make every reference previewable. Success is
measured against the current generator on a fixed benchmark, not judged by eye.

## Facts this plan is built on (measured 2026-11-16)

| Fact | Evidence | Consequence |
|---|---|---|
| App furniture has no "front"; the generator places zero-rotation items only and rotation has no meaning | `models/furniture.py`, `geometry/layout_generator.py` docstrings | Only **orientation-free** habits can be scored. "Headboard against the wall" in the strict sense cannot. |
| Real beds: only a long side on a wall in **6–11%**; generated beds: **34–38%** | Probe over 3,551 real beds vs 60–120 generated (sample room, seeds 0–59), wall tolerance 2–15 cm | A clear, tolerance-robust gap that the data can fix |
| Generator already puts beds against a wall 89% of the time (real: 67%) | Same probe, 5 cm tolerance | "Touches a wall" alone would add nothing; use *which edge* touches |
| Desks/tables on a wall 79%, cabinets/wardrobes 74%; generated desk 82%, storage 80% | Probes | Little room to improve; low priority |
| Nightstands have no product or template in the app; chat allows quantity 1 per item | `chat_specifications.procedural_options`, `catalog_conversation.py:291` | Nightstand habits are measurable but **not usable yet**; deferred |
| The generator returns the **first 2** valid layouts (`max_candidates` ≤ 2); one call takes ~10 ms and uses 17 of 500 attempts | Timing probe | Re-ranking 2 layouts changes little. Integration must widen the pool, and the time budget allows it. |
| Generator, validator, models and layout UI are **hash-pinned** (`FURNITURE_EXPANSION_08F1.json`) | Preservation test | Any generator change needs an owner-recorded authorized migration (one phase is gated) |
| Data noise: 1,379 objects lie >5 cm outside their room; beds typically sit 3–15 cm off the wall | Probe | Statistics must be robust (quantiles, tolerance bands), never exact equality |
| 4,117 of 4,170 references are quarter-turn rooms, shown only as a table | P4 | Oriented-footprint drawing unlocks almost every preview |

## Phases

Numbering continues the project phases (P0–P4 are done). P5–P7 need no changes to owner files. P8 needs the owner's agreement. P9 is optional.

### P5: layout-habit statistics from the pack (2–3 days)

New `src/archimind/datasets/habits.py` and the CLI command `habit-stats`.

- **Inputs.** A verified pack and its `train` split only. `val` and `test` are kept for P6 checks. Alias groups
  count once.
- **Measured per habit.** Rate and quantiles, plus a 95% bootstrap interval with a fixed seed:
  1. **Bed wall edge.** Short edge on a wall / only a long edge / free-standing. The tolerance band is calibrated to
     the data (report 5, 10 and 15 cm; pick the smallest band where the free-standing rate stops falling).
  2. **Desk/table and storage on a wall.** The rate of wall contact (low priority; computed for completeness).
  3. **Chair near desk/table.** The gap distribution, for chairs only in rooms that have a desk/table.
  4. **Floor coverage.** Floor-standing footprint area / room area, conditioned on room-area tercile.
  5. **Nightstand to bed gap.** Recorded for later, and flagged "not usable: no nightstand in the app".
- **Category mapping** from app to pack, written in code and tested: `bed→bed`, `desk→table/desk`,
  `storage|wardrobe→cabinet_shelf_desk/wardrobe|shelf|bookcase`, `chair→chair`. `lighting` is ignored
  because it is ceiling-mounted.
- **Output.** A canonical JSON `habits.json`: version, the pack snapshot id, the counts behind every number, and the
  calibrated tolerance. Its size is a few KB and it holds only aggregates.
- **Tests.**
  - Synthetic rooms with known answers.
  - Tolerance edge cases.
  - Square beds (the edge is undefined, so they are excluded and counted).
  - Objects outside the room.
  - Aliases counted once.
  - Shuffled input giving identical output.
  - A split filter that cannot read `val`/`test`.

**Done when:** `habits.json` is reproducible byte for byte from the P2b pack and every rate has n ≥ 100, or is
marked "insufficient".

### P6: habit scorer and generator benchmark (2–3 days)

New `score_layout_habits(design, habits) -> HabitReport` in `habits.py` and the CLI command `habit-bench`.

- **Scorer.** It reads a `RoomDesign` and does not change it.
  - Per item it reports habit facts (e.g. "bed: only a long edge on a wall").
  - It returns a single **habit penalty** in [0, 1]: the weighted log-rarity of each observed outcome under
    `habits.json`, with weights listed in the file.
  - It is orientation-free and refuses designs with nonzero rotation rather than guessing.
- **Benchmark.**
  - 24 fixed rooms: the sample bedroom, the 09A chat fixture, and a grid of 3 widths × 3 depths × 2 furniture
    sets (bed+desk+storage, bed+desk+chair), plus the 4 published Belaya/Charles product footprints.
  - Seeds 0–49, current generator, unchanged.
  - Reported:
    - the habit outcome distributions next to the `val`-split reference rates
    - the existing `LayoutScore` and the validation pass rate
    - generation time
- **Held-out check.** Score `val`/`test` reference rooms (canonical and quarter-turn footprints) and confirm that
  real rooms get lower penalties than generated ones. If they don't, the habit set is wrong and P8 stops.

**Done when:** a committed receipt `DATASET_HABITS_P6.{md,json}` gives the baseline numbers (e.g. "bed only
long edge: 36% generated vs 8% real, val split"), and real rooms score better than generated ones
on the held-out split.

### P7: preview every reference (1 day)

In `ui/dataset_references.py` only (not pinned):

- Draw quarter-turn references with a **new Plotly figure** in our module. Footprints are rectangles; each is labelled
  with its category and "turned 90°". The room outline is drawn, with no doors or windows and the existing
  "not validated" labels.
- Do not route them through `render_floorplan`, which rightly rejects nonzero rotation.
- **Tests.**
  - An AppTest: a quarter-turn hit now shows a chart, and canonical hits still use the existing renderer.
  - Snapshot-free assertions on trace counts and bounds.

**Done when:** all 4,170 references can be previewed as a picture and the P4 tests still pass.

### P8: habit-aware ranking in the generator (owner-gated, 3–4 days)

**Needs:** the owner's agreement, and an authorized-migration record (before/after SHA-256) for each pinned file
touched, following the existing `DESIGN_AGENT_SINGLE.json` pattern.

- **Change.** The generator keeps collecting valid layouts up to a pool of K (proposed 12) within the existing
  `max_attempts`. It then ranks lexicographically:
  1. hard validation (unchanged; it is never traded)
  2. existing `LayoutScore.total`, **rounded to a 5-point band** so that near-ties can be broken
  3. habit penalty (lower is better)
  4. the existing deterministic tie-break

  The output is still 2 candidates.
- **Default.** Off. A server flag `ARCHIMIND_ENABLE_LAYOUT_HABITS=1` and a present, verified `habits.json` are
  both needed. Missing or invalid habits fall back to today's behaviour exactly; a test checks that the bytes are identical.
- **Success criteria (P6 benchmark).**
  - The "bed only long edge" rate falls from ~36% to ≤ 15%.
  - The validation pass rate is unchanged.
  - Median `LayoutScore.total` drops by ≤ 2 points.
  - The p95 generation time stays ≤ 100 ms.

  If any criterion fails, P8 is not enabled.
- **UI.** The candidate caption gains one line, e.g. "Bed: short end on a wall (typical in 69% of reference
  bedrooms)", built from habit facts only. This touches pinned `ui/layout_generation.py` and is part of the same migration.

### P9 (optional): a few realistic 3D models

Defer until realistic rendering is a goal. If taken:

- Convert 3–5 hand-picked 3D-FUTURE models with headless Blender:
  `blender --background --factory-startup --python <repo script>`, with a pinned Blender version and a
  recorded version and settings for every output.
- Blender MCP can be used for exploring, but not inside the pipeline.
- Expected data is ≤ 500 MB, never the 66 GB set.

## Not planned

- More MIDI downloads (1.7 TB), the full 3D-FUTURE set (66 GB), depth/surface data, model training, embeddings.

## Order and effort

| Phase | Owner approval | Effort | Depends on |
|---|---|---|---|
| P5 Habit statistics | No | 2–3 d | P2b pack |
| P6 Scorer and benchmark | No | 2–3 d | P5 |
| P7 Preview every reference | No | 1 d | P4 (done) |
| P8 Habit-aware ranking | **Yes** | 3–4 d | P6 passing its held-out check |
| P9 Realistic models | Yes (viewer files) | later | — |

P5–P7 together take about one week and can be reviewed without the owner. P7 can run in parallel with P5–P6.

---

## Stress test (what was challenged, and what changed)

The first draft of this plan was checked against the code and the real data before it was written up.
These are the findings and how they changed the plan.

1. **"Learn headboard-against-wall" was not implementable.** Neither the app nor the generator has a
   furniture front, and generated items are always unrotated. *Change:* only orientation-free
   habits are used. The bed habit is restated as "which edge of the footprint touches a wall", which needs
   no front and still separates real from generated beds (8% vs 36% "only long edge").
2. **"Bed against a wall" would have been useless.** The generator already does this 89% of the time,
   more than real rooms (67%). *Change:* that habit was dropped, and desk/storage wall contact demoted to low priority.
3. **Nightstand habits looked strongest but cannot affect the app.** There is no nightstand product or template,
   and chat allows one of each item. *Change:* recorded only, marked not usable.
4. **Re-ranking only 2 candidates would barely change results.** `max_candidates` is capped at 2
   and the generator stops at the first 2 valid layouts. *Change:* P8 widens the pool to K inside the
   existing attempt budget. The probe shows 17 of 500 attempts used and about 10 ms per call, so the budget
   exists. The p95 time is a pass/fail criterion.
5. **Habits could override real quality.** If the habit term ranked above the existing score, a layout with
   worse circulation could win. *Change:* lexicographic ranking. Validation is never traded, and the habit term
   only breaks near-ties within a 5-point score band, with a criterion that the median score drops by no more than 2 points.
6. **The data is noisy.** 1,379 objects are more than 5 cm outside their rooms, and the free-standing rate of real beds moves
   from 52% to 10% between 2 cm and 15 cm tolerance. *Change:* the tolerance is calibrated and reported, and the decision
   metric ("only a long edge") was confirmed stable across 2–15 cm (6–11% real vs 34–38% generated).
7. **Evaluation leakage.** Statistics fit and checked on the same rooms would look better than they are. *Change:*
   fit on `train` only, check on `val`/`test`, fold aliases, and test that the split filter cannot read held-out rows.
8. **Pinned files.** The generator and the layout UI are hash-pinned, and a silent edit would fail the owner's
   preservation test. *Change:* P5–P7 touch no pinned file. P8 is explicitly gated on an owner-authorized
   migration with recorded hashes, default off, and falls back to identical bytes.
9. **Square beds** have no short edge. *Change:* they are excluded from the edge habit and counted (11% of real beds).
10. **Small benchmark.** One sample room could overfit. *Change:* 24 fixed rooms × 50 seeds, including both
    furniture sets that the app can actually produce.

### Residual risks (accepted, to watch)

- **Possible dataset bias.** 3D-FRONT rooms are professionally designed Chinese apartments, so the habits may not match every
  user. The penalty is a tie-breaker, never a rule.
- **Bed edge as a proxy.** "Short edge on a wall" stands in for headboard placement. A bed with its foot end on a wall
  also counts as typical. This is acceptable as a first signal and revisited only if a furniture front is ever added
  to the app.
- **Owner capacity.** If the owner declines P8, P5–P7 still deliver a measured diagnosis and better
  previews, and the habit report remains useful as an evaluation tool for any future generator.
