# P6: habit scorer and generator benchmark (receipt)

Command:

    python -m archimind.datasets habit-bench --pack E:/archimind-data/p2b/pack \
        --habits E:/archimind-data/p5/habits.json --out E:/archimind-data/p5/bench.json

- Generator **unchanged** (`generate_layout_candidates`, default 2 candidates, 500 attempts).
- 24 fixed rooms (sample bedroom, 09A chat room, 3 widths × 3 depths × 2 sets, 4 Belaya/Charles product rooms) × seeds 0–49 = 1,200 calls. All `complete`, so 2,400 candidates, every one passing validation.
- Habits: `habits.json` from P5 (snapshot of the P2b pack, train split, 15 cm tolerance). Reference columns use the held-out `val` split, aliases folded.
- Full numbers: [DATASET_HABITS_P6.json](DATASET_HABITS_P6.json). Everything except `timing_ms` is deterministic.

## Baseline: generated vs real (val)

| Habit | Generated | Real (val) |
|---|---|---|
| Bed: **only a long edge on a wall** | **30.6%** (n 2,400) | **12.9%** (n 210) |
| Bed: short edge on a wall | 57.4% | 81.0% |
| Bed: free-standing | 12.0% | 6.2% |
| Chair within 15 cm of the table | 5.6% (n 1,100) | 90.0% (n 30) |
| Chair 80 cm or more from the table | 76.0% | 0.0% |
| Desk on a wall | 86.4% | 90.3% (n 31) |
| Storage on a wall | 88.8% | 95.3% (n 170) |

Per room, "only a long edge" ranges from 22% to 39% (`per_room` in the JSON).

Existing metrics: `LayoutScore.total` p10/p50/p90 = 41.0 / 57.4 / 68.8. Generation time p50 16 ms, **p95 74 ms**, max 297 ms (this machine).

## Held-out check (P8 gate)

| Rooms | Scored | Median penalty | Share below the generated median |
|---|---|---|---|
| Generated candidates | 2,400 | **0.198** | — |
| Real `val` rooms | 255 | **0.048** | 82% |
| Real `test` rooms | 259 | **0.055** | 71% |

**PASS:** real rooms score better than generated ones on both held-out splits.

## Notes for P8

- The chair gap shows the largest difference, but only 30 val chairs sit in rooms with a table, so the bed edge stays the primary signal.
- Baseline p95 is already 74 ms against P8's 100 ms limit. Widening the pool to K = 12 needs measuring before it can be enabled.
- The penalty uses bed edge 0.6, chair gap 0.2, desk wall 0.1 and storage wall 0.1. Floor coverage is reported with weight 0 (see P5).
