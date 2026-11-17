# P5: layout-habit statistics (receipt)

Command (run twice; outputs byte-identical):

    python -m archimind.datasets habit-stats --pack E:/archimind-data/p2b/pack --out E:/archimind-data/p5/habits.json

- Pack `ssr-bedrooms-p2b` (local), `train` split only: 3,602 rooms after folding 2 exact-duplicate aliases; 0 cross-split alias groups.
- `habits.json` SHA-256 `8dbf28032ed2b7f6d4aeb1fd1b11c3b68dc9e0bd59d5b71a2aaf051f796321ec`, 4.4 KB, aggregates only. The copy is [DATASET_HABITS_P5.json](DATASET_HABITS_P5.json).
- 33 objects lie more than 15 cm through a wall and are excluded. 309 beds are square (sides within 2%) and are excluded from the edge habit.

## Wall tolerance calibration (beds, n = 2,757)

| Tolerance | Free-standing | Only a long edge |
|---|---|---|
| 5 cm | 33.3% | 8.9% |
| 10 cm | 18.0% | 10.1% |
| 15 cm | 10.7% | 11.7% |

The free-standing rate never stops falling (each step drops it by more than 2 points), so the rule picks the widest band, 15 cm.

## Habits at 15 cm (rate, room-level bootstrap 95% CI in the JSON)

| Habit | n | Result | Used in penalty |
|---|---|---|---|
| Bed edge | 2,757 | short edge 77.6%, only long edge 11.7%, free 10.7% | weight 0.6 |
| Chair to table gap | 291 | < 15 cm 89.0% (median 0 cm) | weight 0.2 |
| Desk on a wall | 349 | 89.1% | weight 0.1 |
| Storage on a wall | 2,314 | 96.4% | weight 0.1 |
| Floor coverage by area tercile (edges 10.9 / 13.4 m²) | 3,602 | median 52% / 46% / 38% | recorded, weight 0 |
| Nightstand to bed gap | 3,794 | < 15 cm 85.6% | **not usable: no nightstand in the app** |

Every habit has n ≥ 100 (status `ok`).
