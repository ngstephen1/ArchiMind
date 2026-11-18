"""Decor placement: flat dressing and floor items that never break the layout."""

import copy
import json

import pytest

from archimind.geometry import validate_accessibility
from archimind.models import Door, Furniture, Room, RoomDesign, Window
from archimind.style_packs import load_pack
from archimind.style_packs.decor import FLOOR_KINDS, place_dressing
from archimind.style_packs.models import FurnitureChoice
from archimind.style_packs.scene import style_payload
from archimind.town.design import Brief, generate, validate_home


def study_design(width_m=2.4, depth_m=2.6):
    room = Room(
        id="study",
        name="Study",
        width_m=width_m,
        depth_m=depth_m,
        ceiling_height_m=2.7,
        doors=[Door(id="door", wall="west", offset_m=0.2, width_m=0.9, height_m=2.1)],
        windows=[
            Window(
                id="window",
                wall="east",
                offset_m=0.6,
                width_m=1.2,
                height_m=1.3,
                sill_height_m=0.9,
            )
        ],
    )
    furniture = [
        Furniture(
            id="desk",
            name="Desk",
            category="desk",
            x_m=0.8,
            y_m=depth_m - 0.7,
            width_m=1.4,
            depth_m=0.7,
            height_m=0.75,
        ),
        Furniture(
            id="chair",
            name="Chair",
            category="chair",
            x_m=1.25,
            y_m=depth_m - 1.25,
            width_m=0.48,
            depth_m=0.52,
            height_m=0.83,
        ),
        Furniture(
            id="bookcase",
            name="Bookcase",
            category="storage",
            x_m=width_m - 1.4,
            y_m=0.0,
            width_m=1.4,
            depth_m=0.35,
            height_m=1.8,
        ),
        Furniture(
            id="files",
            name="Filing cabinet",
            category="storage",
            x_m=0.0,
            y_m=depth_m - 0.55,
            width_m=0.5,
            depth_m=0.55,
            height_m=0.7,
        ),
    ]
    return RoomDesign(room=room, furniture=furniture)


def living_design():
    room = Room(
        id="living",
        name="Living",
        width_m=5.0,
        depth_m=4.2,
        ceiling_height_m=2.7,
        doors=[Door(id="door", wall="south", offset_m=0.3, width_m=0.9, height_m=2.1)],
        windows=[
            Window(
                id="w1",
                wall="north",
                offset_m=1.0,
                width_m=1.6,
                height_m=1.4,
                sill_height_m=0.8,
            ),
            Window(
                id="w2",
                wall="east",
                offset_m=1.2,
                width_m=1.2,
                height_m=1.4,
                sill_height_m=0.8,
            ),
        ],
    )
    furniture = [
        Furniture(
            id="sofa",
            name="Sofa",
            category="sofa",
            x_m=1.5,
            y_m=3.2,
            width_m=2.0,
            depth_m=0.85,
            height_m=0.86,
        ),
        Furniture(
            id="coffee-table",
            name="Coffee table",
            category="table",
            x_m=2.0,
            y_m=2.2,
            width_m=1.0,
            depth_m=0.54,
            height_m=0.42,
        ),
        Furniture(
            id="cabinet",
            name="Cabinet",
            category="storage",
            x_m=0.0,
            y_m=1.4,
            width_m=0.45,
            depth_m=1.6,
            height_m=1.8,
        ),
    ]
    return RoomDesign(room=room, furniture=furniture)


def with_floor_items(design, dressing):
    rows = [
        Furniture(
            id=item.id,
            name=item.kind,
            category="decor",
            x_m=item.x_m,
            y_m=item.y_m,
            width_m=item.width_m,
            depth_m=item.depth_m,
            height_m=item.height_m,
        )
        for item in dressing.items
        if item.kind in FLOOR_KINDS
    ]
    return RoomDesign(room=design.room, furniture=[*design.furniture, *rows])


def _japandi_with_accent():
    pack = load_pack("japandi")
    accent = FurnitureChoice(
        asset_id="polyhaven:fixture_stool", width_m=0.4, depth_m=0.4, height_m=0.45
    )
    return pack.model_copy(
        update={"decor": pack.decor.model_copy(update={"accents": (accent,)})}
    )


def test_tiny_study_skips_floor_items_and_stays_valid():
    d = study_design(width_m=2.4, depth_m=2.6)
    out = place_dressing(d, _japandi_with_accent(), seed=42)
    assert {"plant", "accent"} & {s.split(":")[0] for s in out.skipped}
    placed = [i for i in out.items if i.kind in FLOOR_KINDS]
    assert len(placed) < len(FLOOR_KINDS) + 1  # not every floor item fits
    assert validate_accessibility(with_floor_items(d, out)).status == "passed"


def test_roomy_living_room_places_floor_items_in_valid_spots():
    d = living_design()
    out = place_dressing(d, _japandi_with_accent(), seed=42)
    kinds = [i.kind for i in out.items]
    assert {"rug", "art", "curtain", "pendant", "plant"} <= set(kinds)
    assert kinds.count("curtain") == 2
    assert validate_accessibility(with_floor_items(d, out)).status == "passed"


def test_dressing_never_moves_furniture():
    d = living_design()
    before = d.model_dump(mode="json")
    place_dressing(d, load_pack("modern_classic"), seed=3)
    assert d.model_dump(mode="json") == before


def _span(item):
    return (
        (item.x_m, item.x_m + item.width_m)
        if item.wall in ("north", "south")
        else (item.y_m, item.y_m + item.depth_m)
    )


def test_art_avoids_openings_and_curtains_cover_each_window():
    d = living_design()
    out = place_dressing(d, load_pack("scandinavian"), seed=1)
    (art,) = [i for i in out.items if i.kind == "art"]
    openings = [
        (o.wall, o.offset_m, o.offset_m + o.width_m)
        for o in (*d.room.doors, *d.room.windows)
    ]
    lo, hi = _span(art)
    for wall, start, end in openings:
        if wall == art.wall:
            assert hi <= start or lo >= end
    curtains = {i.id: i for i in out.items if i.kind == "curtain"}
    for window in d.room.windows:
        c = curtains[f"curtain:{window.id}"]
        lo, hi = _span(c)
        assert (
            c.wall == window.wall
            and lo <= window.offset_m
            and hi >= window.offset_m + window.width_m
        )
    # Mouldings follow the pack switch.
    assert not [i for i in out.items if i.kind == "moulding"]
    classic = place_dressing(d, load_pack("modern_classic"), seed=1)
    assert sorted(i.wall for i in classic.items if i.kind == "moulding") == [
        "east",
        "north",
        "south",
        "west",
    ]


def test_rug_sits_under_the_anchor_group_and_clear_of_the_door():
    d = living_design()
    out = place_dressing(d, load_pack("japandi"), seed=1)
    (rug,) = [i for i in out.items if i.kind == "rug"]
    assert rug.z_m == 0 and rug.height_m <= 0.02
    sofa, table = d.furniture[0], d.furniture[1]
    for f in (sofa, table):
        assert rug.x_m <= f.x_m and rug.x_m + rug.width_m >= f.x_m + f.width_m
    door = d.room.doors[0]
    # The south door's 0.9 m approach zone stays clear of the rug.
    overlaps_x = (
        rug.x_m < door.offset_m + door.width_m and rug.x_m + rug.width_m > door.offset_m
    )
    assert not (overlaps_x and rug.y_m < 0.9)


def test_same_seed_same_dressing_different_seed_may_differ():
    d = living_design()
    pack = _japandi_with_accent()
    a = place_dressing(d, pack, seed=5).model_dump(mode="json")
    assert a == place_dressing(d, pack, seed=5).model_dump(mode="json")
    layouts = {
        json.dumps(
            place_dressing(d, pack, seed=s).model_dump(mode="json"), sort_keys=True
        )
        for s in range(8)
    }
    assert len(layouts) > 1


def test_density_reduces_floor_items():
    d = living_design()
    pack = _japandi_with_accent()
    full = [i for i in place_dressing(d, pack, seed=2).items if i.kind in FLOOR_KINDS]
    half = [
        i
        for i in place_dressing(d, pack, seed=2, density=0.5).items
        if i.kind in FLOOR_KINDS
    ]
    assert len(half) < len(full)


def test_style_payload_carries_dressing():
    d = living_design()
    payload = style_payload(d, load_pack("japandi"), 7)
    out = place_dressing(d, load_pack("japandi"), seed=7)
    assert payload["dressing"] == [i.model_dump(mode="json") for i in out.items]
    assert payload["skipped"] == out.skipped


@pytest.mark.parametrize("style", ["scandinavian", "modern_classic"])
def test_every_town_room_dressing_passes_whole_home_validation(style):
    home = generate(Brief(style=style), None)[0]
    furnished = copy.deepcopy(home)
    for part in furnished["rooms"]:
        floor = [i for i in part["style"]["dressing"] if i["kind"] in FLOOR_KINDS]
        part["design"]["furniture"] += [
            {
                "id": i["id"],
                "name": i["kind"],
                "category": "decor",
                "x_m": i["x_m"],
                "y_m": i["y_m"],
                "width_m": i["width_m"],
                "depth_m": i["depth_m"],
                "height_m": i["height_m"],
                "rotation_deg": 0,
            }
            for i in floor
        ]
    validate_home(furnished)
    assert any(
        i["kind"] == "rug" for p in home["rooms"] for i in p["style"]["dressing"]
    )


def test_bathrooms_get_no_floor_lamp_or_accent_furniture():
    home = generate(Brief(), None)[0]
    (bath,) = [p for p in home["rooms"] if p["design"]["room"]["id"] == "bathroom"]
    kinds = {i["kind"] for i in bath["style"]["dressing"]}
    assert not kinds & {"floor_lamp", "accent"}
    assert "floor_lamp:wet_room" in bath["style"]["skipped"]
