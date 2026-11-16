"""P6 benchmark harness on synthetic habits (real numbers: docs/data/DATASET_HABITS_P6.md)."""

from archimind.datasets.habit_bench import bench_rooms, run_bench
from archimind.datasets.habits import compute_habits

from test_dataset_habits import SNAP, typical_rooms  # noqa: E402


def test_bench_has_24_fixed_unrotated_rooms():
    rooms = bench_rooms()
    assert len(rooms) == 24
    assert len({r.id for r in rooms}) == 24
    assert {"sample", "chat-09a"} <= {r.id for r in rooms}
    for r in rooms:
        assert r.furniture and all(f.rotation_deg == 0 for f in r.furniture)
        assert {f.category for f in r.furniture} <= {"bed", "desk", "storage", "chair"}
    assert bench_rooms() == rooms  # fixed


def test_run_bench_small():
    habits = compute_habits(typical_rooms(200), pack_id="p", snapshot_id=SNAP)
    held = {"val": typical_rooms(5, split="val"), "test": typical_rooms(5, split="test", start=5)}
    rooms = [r for r in bench_rooms() if r.id in ("sample", "chat-09a")]
    report = run_bench(habits, rooms=rooms, seeds=range(3), held_out=held)
    assert report["calls"] == 6
    gen = report["generated"]
    assert gen["candidates"] > 0
    assert set(gen["habit_outcomes"]["bed_edge"]) == {"short_edge", "long_edge_only", "free_standing"}
    assert report["reference"]["val"]["habit_outcomes"]["bed_edge"]["short_edge"] == 0.8
    assert 0 <= gen["layout_score"]["p50"] <= 100
    assert report["timing_ms"]["p95"] >= report["timing_ms"]["p50"] >= 0
    assert set(report["held_out"]) == {"val", "test", "passed"}
    assert report["held_out"]["val"]["rooms_scored"] == 5
