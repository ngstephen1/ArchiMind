import json
from pathlib import Path

import pytest

from archimind.town.design import validate_home
from archimind.town.renovation import edit


def source():
    return json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/data/furnished-residence/home.json"
        ).read_text()
    )


def request(**changes):
    return (
        dict(
            south="kitchen-dining",
            north="study",
            kind="door",
            delta_m=0,
            width_m=1,
            offset_m=2,
        )
        | changes
    )


def test_paired_door_opening_wall_and_clearance():
    before = source()
    revised, _ = edit(before, request())
    pair = [
        d
        for p in revised["rooms"]
        for d in p["design"]["room"]["doors"]
        if d["id"].startswith("partition-")
    ]
    assert len(pair) == 2 and {d["wall"] for d in pair} == {"north", "south"}
    assert all(d["width_m"] == 1 and d["height_m"] == 2.10 for d in pair)
    revised, _ = edit(revised, request(kind="opening"))
    assert revised["rooms"][-1]["design"]["room"]["doors"][1]["height_m"] == 2.45
    restored, _ = edit(revised, request(kind="wall"))
    assert not any(
        d["id"].startswith("partition-")
        for p in restored["rooms"]
        for d in p["design"]["room"]["doors"]
    )
    assert before == source()
    revised["rooms"][-1]["design"]["room"]["doors"][1]["offset_m"] += 0.12
    with pytest.raises(ValueError, match="coincide"):
        validate_home(revised)


def test_partition_shift_keeps_adjacent_furniture_and_exterior_openings_world_fixed():
    before = source()
    revised, _ = edit(
        before, request(south="salon", north="living", kind="wall", delta_m=0.03)
    )
    assert (revised["width"], revised["depth"]) == (before["width"], before["depth"])
    for old, new in zip(before["rooms"], revised["rooms"], strict=True):
        r, s = old["design"]["room"], new["design"]["room"]
        if r["id"] not in {"salon", "living"}:
            assert old == new
        else:
            assert s["depth_m"] - r["depth_m"] == pytest.approx(
                0.03 if r["id"] == "salon" else -0.03
            )
            for a, b in zip(
                old["design"]["furniture"], new["design"]["furniture"], strict=True
            ):
                assert old["origin"][1] + a["y_m"] == pytest.approx(
                    new["origin"][1] + b["y_m"]
                )
            assert old["origin"][1] + r["windows"][0]["offset_m"] == pytest.approx(
                new["origin"][1] + s["windows"][0]["offset_m"]
            )
    assert revised["evidence"]["room_areas_m2"]["salon"] == pytest.approx(
        33.04, abs=0.01
    )
    with pytest.raises(ValueError):
        edit(before, request(offset_m=0))
    with pytest.raises(ValueError):
        edit(before, request(south="living", north="kitchen-dining"))
    with pytest.raises(ValueError):
        edit(before, request(delta_m=1.8))
