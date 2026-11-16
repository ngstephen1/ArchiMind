"""P5 layout-habit statistics on synthetic scenes with known answers."""

import json
import random

import pytest

from archimind.datasets.canonical import sha256_hex
from archimind.datasets.contracts import (
    CheckResult,
    Footprint,
    RoomExtent,
    SceneObject,
    SceneReference,
)
from archimind.datasets.fixtures import FIXTURE_VERSION, SYNTHETIC_REVISION
from archimind.datasets.habits import (
    MIN_N,
    Rect,
    app_group,
    bed_edge,
    compute_habits,
    habits_bytes,
    on_wall,
    pack_group,
    rect_gap,
    select_split,
)

SNAP = "0" * 64


def obj(oid, category, raw, x, y, w, d, turns=0):
    return SceneObject(
        source_object_id=oid,
        jid=f"jid-{oid}",
        raw_category=raw,
        category=category,
        size_raw=(w, 0.5, d),
        position_raw=(x + w / 2, 0.25, y + d / 2),
        rotation_raw_xyzw=(0.0, 0.0, 0.0, 1.0),
        footprint=Footprint(
            x_m=x, y_m=y, width_m=w, depth_m=d, height_m=0.5, yaw_quarter_turns=turns
        ),
    )


def scene(house, objects, *, dims=(4.0, 4.0), split="train", room="Bedroom-1"):
    return SceneReference(
        reference_id=f"ssr:{house}:{room}",
        source="ssr_3dfront",
        source_revision=SYNTHETIC_REVISION,
        source_sha256=sha256_hex(b"ssr"),
        split=split,
        source_scene_id=house,
        source_room_id=room,
        tier="reference_only",
        room=RoomExtent(width_m=dims[0], depth_m=dims[1], height_m=2.7),
        openings="unknown",
        objects=tuple(objects),
        checks=(CheckResult(name="wall_containment", status="PASS"),),
        transform_version=FIXTURE_VERSION,
        category_map_version=FIXTURE_VERSION,
    )


BED = ("bed", "King-size Bed")
DESK = ("table", "Desk")
WARDROBE = ("cabinet_shelf_desk", "Wardrobe")
STAND = ("cabinet_shelf_desk", "Nightstand")
CHAIR = ("chair", "Dining Chair")
LAMP = ("lighting", "Pendant Lamp")


# ------------------------------------------------------------- mapping


def test_category_mapping_app_and_pack():
    assert pack_group("bed", "Kids Bed") == "bed"
    assert pack_group("table", "Desk") == "desk"
    assert pack_group("table", "Dining Table") is None
    assert pack_group("cabinet_shelf_desk", "Wardrobe") == "storage"
    assert pack_group("cabinet_shelf_desk", "Shelf") == "storage"
    assert pack_group("cabinet_shelf_desk", "Bookcase / jewelry Armoire") == "storage"
    assert pack_group("cabinet_shelf_desk", "Nightstand") == "nightstand"
    assert pack_group("cabinet_shelf_desk", "TV Stand") is None
    assert pack_group("chair", "Dining Chair") == "chair"
    assert pack_group("lighting", "Pendant Lamp") is None
    assert app_group("bed") == "bed"
    assert app_group("desk") == app_group("table") == "desk"
    assert app_group("storage") == app_group("wardrobe") == "storage"
    assert app_group("chair") == "chair"
    assert app_group("lighting") is None


# ------------------------------------------------------------- geometry


@pytest.mark.parametrize(
    ("x", "y", "w", "d", "expected"),
    [
        (0.0, 1.0, 2.0, 1.6, "short_edge"),  # long axis X, west short edge on wall
        (1.0, 0.0, 2.0, 1.6, "long_edge_only"),  # south long edge on wall
        (1.0, 1.0, 2.0, 1.6, "free_standing"),
        (0.0, 0.0, 2.0, 1.6, "short_edge"),  # corner: short edge wins
        (1.0, 2.0, 1.6, 2.0, "short_edge"),  # long axis Y, north short edge on wall
        (1.0, 1.0, 1.5, 1.5, "square"),
        (1.0, 1.0, 1.5, 1.52, "square"),  # within 2% is square
        (1.0, 1.0, 1.5, 1.56, "free_standing"),  # 3.8% apart has a short edge
    ],
)
def test_bed_edge_classes(x, y, w, d, expected):
    assert bed_edge(Rect("bed", x, y, w, d), 4.0, 4.0, 0.10) == expected


def test_tolerance_edges():
    near = Rect("bed", 0.10, 1.0, 2.0, 1.6)
    assert bed_edge(near, 4.0, 4.0, 0.10) == "short_edge"
    assert bed_edge(near, 4.0, 4.0, 0.0999) == "free_standing"
    # Slightly through the wall still touches.
    assert on_wall(Rect("desk", -0.03, 1.0, 1.0, 0.5), 4.0, 4.0, 0.05)
    assert not on_wall(Rect("desk", 1.0, 1.0, 1.0, 0.5), 4.0, 4.0, 0.05)


def test_rect_gap():
    a = Rect("desk", 0.0, 0.0, 1.0, 1.0)
    assert rect_gap(a, Rect("chair", 1.5, 0.0, 0.5, 0.5)) == pytest.approx(0.5)
    assert rect_gap(a, Rect("chair", 0.5, 0.5, 1.0, 1.0)) == 0.0
    assert rect_gap(a, Rect("chair", 4.0, 5.0, 1.0, 1.0)) == pytest.approx(5.0)


# ------------------------------------------------------------- statistics


def typical_rooms(n, *, split="train", start=0):
    """Rooms with a known answer: 3 of 4 beds short edge, 1 of 4 long edge only."""
    out = []
    for i in range(start, start + n):
        if i % 4 == 3:
            bed = obj("b", *BED, 1.0, 0.0, 2.0, 1.6)  # long edge only
        else:
            bed = obj("b", *BED, 0.0, 1.0, 2.0, 1.6)  # short edge
        objects = [
            bed,
            obj("d", *DESK, 2.8, 3.4, 1.0, 0.6),  # on north wall
            obj("c", *CHAIR, 3.0, 2.8, 0.5, 0.5),  # 0.1 m from desk
            obj("w", *WARDROBE, 3.4, 0.5, 0.6, 1.5),  # east wall
            obj("n", *STAND, 0.0, 2.7, 0.4, 0.4),  # 0.1 m from bed
            obj("l", *LAMP, 1.0 + i * 0.001, 2.0, 0.3, 0.3),  # ceiling, ignored; unique
        ]
        out.append(scene(f"h{i}", objects, dims=(4.0, 4.0), split=split))
    return out


def test_known_rates_and_counts():
    habits = compute_habits(typical_rooms(200), pack_id="p", snapshot_id=SNAP)
    bed = habits["habits"]["bed_edge"]
    assert bed["status"] == "ok" and bed["n"] == 200
    assert bed["outcomes"]["short_edge"]["rate"] == pytest.approx(0.75)
    assert bed["outcomes"]["long_edge_only"]["rate"] == pytest.approx(0.25)
    lo, hi = bed["outcomes"]["short_edge"]["ci95"]
    assert lo <= 0.75 <= hi
    assert habits["habits"]["desk_wall"]["outcomes"]["wall"]["rate"] == 1.0
    assert habits["habits"]["storage_wall"]["outcomes"]["wall"]["rate"] == 1.0
    chair = habits["habits"]["chair_desk_gap"]
    assert chair["quantiles_m"]["p50"] == pytest.approx(0.1)
    night = habits["habits"]["nightstand_bed_gap"]
    assert night["usable"] is False and "no nightstand in the app" in night["note"]
    assert night["quantiles_m"]["p50"] == pytest.approx(0.1)
    cov = habits["habits"]["floor_coverage"]
    assert set(cov["by_tercile"]) == {"t1", "t2", "t3"}
    assert habits["split"] == "train" and habits["snapshot_id"] == SNAP
    assert habits["counts"]["rooms"] == 200
    assert "lighting" not in json.dumps(habits["category_map"]["app"])
    assert habits["tolerance_m"] in (0.05, 0.10, 0.15)


def test_insufficient_when_n_below_min():
    habits = compute_habits(typical_rooms(MIN_N - 1), pack_id="p", snapshot_id=SNAP)
    assert habits["habits"]["bed_edge"]["status"] == "insufficient"
    assert habits["habits"]["bed_edge"]["n"] == MIN_N - 1


def test_square_beds_excluded_and_counted():
    rooms = typical_rooms(120)
    rooms.append(scene("sq", [obj("b", *BED, 1.0, 1.0, 1.8, 1.8)]))
    habits = compute_habits(rooms, pack_id="p", snapshot_id=SNAP)
    assert habits["counts"]["square_beds"] == 1
    assert habits["habits"]["bed_edge"]["n"] == 120


def test_objects_outside_room_excluded_and_counted():
    rooms = typical_rooms(120)
    rooms.append(scene("out", [obj("b", *BED, -0.5, 1.0, 2.0, 1.6)]))
    habits = compute_habits(rooms, pack_id="p", snapshot_id=SNAP)
    assert habits["counts"]["objects_outside_room"] == 1
    assert habits["habits"]["bed_edge"]["n"] == 120


def test_aliases_count_once():
    rooms = typical_rooms(120)
    dup = rooms[0].model_copy(
        update={"reference_id": "ssr:dup:Bedroom-1", "source_scene_id": "dup"}
    )
    habits = compute_habits([*rooms, dup], pack_id="p", snapshot_id=SNAP)
    assert habits["counts"]["rooms"] == 120
    assert habits["counts"]["alias_scenes_folded"] == 1


def test_shuffled_input_gives_identical_bytes():
    rooms = typical_rooms(150)
    a = habits_bytes(compute_habits(rooms, pack_id="p", snapshot_id=SNAP))
    random.Random(7).shuffle(rooms)
    b = habits_bytes(compute_habits(rooms, pack_id="p", snapshot_id=SNAP))
    assert a == b and a.endswith(b"\n") and len(a) < 16_000


def test_compute_refuses_held_out_rows():
    with pytest.raises(ValueError, match="split"):
        compute_habits(typical_rooms(3, split="val"), pack_id="p", snapshot_id=SNAP)


class _HeldOut:
    """A held-out row: reading anything but ``split`` is a leak."""

    def __init__(self, split):
        object.__setattr__(self, "split", split)

    def __getattr__(self, name):
        raise AssertionError(f"held-out field read: {name}")


def test_split_filter_cannot_read_held_out_rows():
    train = typical_rooms(2)
    picked = select_split([_HeldOut("val"), train[0], _HeldOut("test"), train[1]])
    assert picked == train
    with pytest.raises(ValueError):
        select_split(train, split="unknown")


def test_leak_free_train_drops_cross_split_aliases():
    from archimind.datasets.habits import leak_free_train

    rooms = typical_rooms(3)
    held = rooms[0].model_copy(
        update={"reference_id": "ssr:v:Bedroom-1", "source_scene_id": "v", "split": "val"}
    )
    train, groups = leak_free_train([*rooms, held])
    assert groups == 1 and train == rooms[1:]
