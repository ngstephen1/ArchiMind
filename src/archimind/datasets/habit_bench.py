"""P6: habit benchmark of the current, unchanged layout generator.

24 fixed rooms x seeds 0-49. Every generated candidate is scored with
:func:`archimind.datasets.habits.score_layout_habits`; held-out reference rooms
(``val``/``test``) are scored the same way. Real rooms must get lower penalties
than generated ones, or the habit set is wrong and P8 stops.

This module imports the generator, so it is loaded only by ``habit-bench``.
"""

import time
from collections import Counter
from dataclasses import dataclass

from archimind.datasets.habits import (
    LABELS,
    _quantile,
    _scene_dims,
    fold_aliases,
    observe_room,
    scene_rects,
    score_layout_habits,
    score_scene_habits,
)

BELAYA_ID = "abo-b074l4976t-amazon-co-uk"
CHARLES_ID = "abo-b075x2x4xs-amazon-com"
SCORED = ("bed_edge", "chair_desk_gap", "desk_wall", "storage_wall")


@dataclass(frozen=True)
class BenchRoom:
    id: str
    room: object
    furniture: tuple


def _item(fid, category, w, d, h):
    from archimind.models import Furniture

    return Furniture(
        id=fid, name=fid, category=category, x_m=0.0, y_m=0.0,
        width_m=w, depth_m=d, height_m=h,
    )


def _room(rid, width, depth):
    from archimind.models import Door, Room

    door = Door(id="south-door", wall="south", offset_m=0.6, width_m=0.85, height_m=2.1)
    return Room(
        id=rid, name=rid, width_m=width, depth_m=depth, ceiling_height_m=2.7,
        doors=[door],
    )


def bench_rooms() -> list[BenchRoom]:
    """The fixed benchmark: sample, 09A chat, 3x3x2 grid and 4 product rooms."""
    from archimind.assets.planning_envelopes import load_planning_envelope
    from archimind.examples.sample_bedroom import create_sample_bedroom

    sample = create_sample_bedroom()
    by_id = {f.id: f for f in sample.furniture}
    bed = _item("bed", "bed", 1.6, 2.0, 0.6)
    desk = _item("desk", "desk", 1.2, 0.6, 0.75)
    storage = _item("storage", "storage", 1.5, 0.6, 2.0)
    charles = load_planning_envelope(CHARLES_ID).planning_dimensions
    belaya = load_planning_envelope(BELAYA_ID).planning_dimensions
    chair = _item("charles-chair", "chair", *charles.wdh)
    belaya_desk = _item("belaya-desk", "desk", *belaya.wdh)
    sets = {"a": (bed, desk, storage), "b": (bed, desk, chair)}

    rooms = [
        BenchRoom(
            "sample",
            sample.room,
            tuple(by_id[k] for k in ("queen-bed", "desk", "wardrobe")),
        ),
        # 09A chat fixture: 5 x 4 m, south door 0.6/0.85, no windows, queen bed + desk.
        BenchRoom("chat-09a", _room("chat-09a", 5.0, 4.0), (bed, desk)),
    ]
    for w in (3.5, 4.0, 5.0):
        for d in (3.5, 4.0, 4.5):
            for name, items in sets.items():
                rid = f"grid-{w:.1f}x{d:.1f}-{name}"
                rooms.append(BenchRoom(rid, _room(rid, w, d), items))
    for w, d in ((5.0, 4.0), (4.0, 4.0)):
        for name, items in (
            ("belaya-storage", (bed, belaya_desk, storage)),
            ("belaya-charles", (bed, belaya_desk, chair)),
        ):
            rid = f"product-{w:.1f}x{d:.1f}-{name}"
            rooms.append(BenchRoom(rid, _room(rid, w, d), items))
    return rooms


def _dist(labels: list[str], names) -> dict:
    counts = Counter(labels)
    n = sum(counts.values())
    return {k: round(counts[k] / n, 6) if n else 0.0 for k in names}


def _summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "p10": round(_quantile(values, 0.1), 6),
        "p50": round(_quantile(values, 0.5), 6),
        "p90": round(_quantile(values, 0.9), 6),
        "mean": round(sum(values) / len(values), 6),
    }


def reference_rates(scenes, habits: dict) -> dict:
    scenes, _ = fold_aliases(list(scenes))
    labels: dict[str, list[str]] = {h: [] for h in SCORED}
    for s in scenes:
        obs = observe_room(scene_rects(s), *_scene_dims(s), habits["tolerance_m"])
        for h in SCORED:
            labels[h].extend(o[0] for o in obs.outcomes.get(h, ()))
    return {
        "rooms": len(scenes),
        "n": {h: len(v) for h, v in labels.items()},
        "habit_outcomes": {h: _dist(v, LABELS[h]) for h, v in labels.items()},
    }


def held_out_penalties(scenes, habits: dict) -> list[float]:
    scenes, _ = fold_aliases(list(scenes))
    out = []
    for s in scenes:
        report = score_scene_habits(s, habits)
        if report.status == "scored":
            out.append(report.penalty)
    return out


def run_bench(
    habits: dict,
    *,
    rooms=None,
    seeds=range(50),
    held_out: dict | None = None,
    clock=time.perf_counter,
) -> dict:
    from archimind.geometry.layout_generator import generate_layout_candidates

    rooms = bench_rooms() if rooms is None else rooms
    statuses: Counter = Counter()
    labels: dict[str, list[str]] = {h: [] for h in SCORED}
    scores, penalties, times = [], [], []
    per_room = {}
    calls = with_candidate = candidates = 0
    for room in rooms:
        room_labels = []
        for seed in seeds:
            start = clock()
            result = generate_layout_candidates(room.room, list(room.furniture), seed=seed)
            times.append((clock() - start) * 1000)
            calls += 1
            statuses[result.status] += 1
            with_candidate += bool(result.candidates)
            for cand in result.candidates:
                candidates += 1
                scores.append(cand.score.total)
                report = score_layout_habits(cand.design, habits)
                if report.status == "scored":
                    penalties.append(report.penalty)
                for f in report.facts:
                    if f.habit in labels:
                        labels[f.habit].append(f.outcome)
                        if f.habit == "bed_edge":
                            room_labels.append(f.outcome)
        per_room[room.id] = {
            "bed_long_edge_only": _dist(room_labels, LABELS["bed_edge"])["long_edge_only"],
            "bed_observations": len(room_labels),
        }
    times.sort()
    report = {
        "schema_version": "1.0.0",
        "habits_snapshot_id": habits["snapshot_id"],
        "rooms": len(rooms),
        "seeds": [min(seeds), max(seeds)] if len(seeds) else [],
        "calls": calls,
        "status_counts": dict(sorted(statuses.items())),
        "call_pass_rate": round(with_candidate / calls, 6) if calls else 0.0,
        "generated": {
            "candidates": candidates,
            "n": {h: len(v) for h, v in labels.items()},
            "habit_outcomes": {h: _dist(v, LABELS[h]) for h, v in labels.items()},
            "layout_score": _summary(scores),
            "habit_penalty": _summary(penalties),
        },
        "per_room": per_room,
        "timing_ms": {
            "p50": round(_quantile(times, 0.5), 3) if times else 0.0,
            "p95": round(_quantile(times, 0.95), 3) if times else 0.0,
            "max": round(times[-1], 3) if times else 0.0,
        },
    }
    if held_out is not None:
        report["reference"] = {k: reference_rates(v, habits) for k, v in held_out.items()}
        gen_p50 = report["generated"]["habit_penalty"].get("p50")
        check = {}
        for split, scenes in held_out.items():
            values = held_out_penalties(scenes, habits)
            s = _summary(values)
            check[split] = {
                "rooms_scored": len(values),
                "penalty": s,
                "share_below_generated_median": round(
                    sum(v < gen_p50 for v in values) / len(values), 6
                )
                if values and gen_p50 is not None
                else None,
            }
        check["passed"] = gen_p50 is not None and all(
            check[k]["rooms_scored"] and check[k]["penalty"]["p50"] < gen_p50
            for k in held_out
        )
        report["held_out"] = check
    return report
