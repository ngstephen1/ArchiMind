"""Place a pack's decor around an approved layout without changing it.

Every item is an axis-aligned box in room coordinates: ``(x_m, y_m)`` is the
lower-left corner of its floor footprint, ``width_m`` runs along X (east),
``depth_m`` along Y (north), ``z_m`` is the height of its underside and
``height_m`` its vertical size. ``wall`` names the wall a wall-mounted item is
on; ``rotation_deg`` is the direction the item faces (0 north, 90 east, 180
south, 270 west). Flat items (rug, art, curtain, moulding, pendant) never enter
circulation checks; floor items (plant, floor lamp, accent furniture) are only
kept where the whole room still passes ``validate_accessibility``.
"""

import math
import random
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from shapely import box

from archimind.geometry import validate_accessibility
from archimind.geometry.accessibility import _clearance_zone
from archimind.models import Furniture, RoomDesign
from archimind.models.room import Wall

from .models import StylePack

Kind = Literal[
    "rug", "art", "curtain", "moulding", "pendant", "plant", "floor_lamp", "accent"
]
FLOOR_KINDS = frozenset({"plant", "floor_lamp", "accent"})
WET_CATEGORIES = frozenset({"bath", "vanity"})
WALLS: tuple[Wall, ...] = ("north", "east", "south", "west")
FACING = {"south": 0, "west": 90, "north": 180, "east": 270}
DOOR_ZONE_DEPTH_M = 0.9
DOOR_ZONE_MARGIN_M = 0.15
TALL_FURNITURE_M = 1.2
PLANT = (0.45, 0.45, 1.1)
FLOOR_LAMP = (0.4, 0.4, 1.6)


class DressingItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: Kind
    asset_id: str | None
    x_m: float
    y_m: float
    z_m: float = Field(ge=0)
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    wall: Wall | None
    rotation_deg: Literal[0, 90, 180, 270]


class Dressing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DressingItem]
    skipped: list[str]


def _r(value):
    return round(value, 4)


def _wall_length(room, wall):
    return room.width_m if wall in ("north", "south") else room.depth_m


def _wall_box(room, wall, start, length, depth, gap):
    """(x, y, width, depth) of a strip lying against ``wall``."""
    if wall == "north":
        return start, room.depth_m - gap - depth, length, depth
    if wall == "south":
        return start, gap, length, depth
    if wall == "east":
        return room.width_m - gap - depth, start, depth, length
    return gap, start, depth, length


def _item(id, kind, asset_id, rect, z, height, wall=None, rotation=0):
    x, y, w, d = rect
    return DressingItem(
        id=id,
        kind=kind,
        asset_id=asset_id,
        x_m=_r(x),
        y_m=_r(y),
        z_m=_r(z),
        width_m=_r(w),
        depth_m=_r(d),
        height_m=_r(height),
        wall=wall,
        rotation_deg=rotation,
    )


def _shape(x, y, w, d):
    return box(x, y, x + w, y + d)


def _bbox(items):
    return (
        min(f.x_m for f in items),
        min(f.y_m for f in items),
        max(f.x_m + f.width_m for f in items),
        max(f.y_m + f.depth_m for f in items),
    )


def _door_zones(room):
    return [
        _clearance_zone(room, d, DOOR_ZONE_DEPTH_M, DOOR_ZONE_MARGIN_M)
        for d in room.doors
    ]


def _place_rug(design, pack, zones):
    furniture = design.furniture
    beds = [f for f in furniture if f.category == "bed"]
    sofas = [f for f in furniture if f.category == "sofa"]
    tables = sorted(
        (f for f in furniture if f.category == "table"),
        key=lambda f: -f.width_m * f.depth_m,
    )
    if beds:
        group = [max(beds, key=lambda f: f.width_m * f.depth_m)]
    elif sofas:
        sofa = max(sofas, key=lambda f: f.width_m * f.depth_m)
        near = _shape(sofa.x_m, sofa.y_m, sofa.width_m, sofa.depth_m).buffer(1.2)
        group = [
            sofa,
            *(
                t
                for t in tables
                if near.intersects(_shape(t.x_m, t.y_m, t.width_m, t.depth_m))
            ),
        ]
    elif tables:
        group = [tables[0]]
    else:
        return None, "rug:no_anchor"
    room = design.room
    left, bottom, right, top = _bbox(group)
    for margin in (0.45, 0.25, 0.0):
        x0, y0 = max(0.15, left - margin), max(0.15, bottom - margin)
        x1, y1 = (
            min(room.width_m - 0.15, right + margin),
            min(room.depth_m - 0.15, top + margin),
        )
        if x1 - x0 < 0.6 or y1 - y0 < 0.6:
            continue
        rug = box(x0, y0, x1, y1)
        if all(rug.intersection(z).area <= 1e-9 for z in zones):
            return _item(
                "rug", "rug", pack.decor.rug, (x0, y0, x1 - x0, y1 - y0), 0, 0.012
            ), None
    return None, "rug:door_zone"


def _blocked(room, wall, design, margin):
    spans = [
        (o.offset_m - margin, o.offset_m + o.width_m + margin)
        for o in (*room.doors, *room.windows)
        if o.wall == wall
    ]
    for f in design.furniture:
        if f.height_m <= TALL_FURNITURE_M:
            continue
        near = {
            "north": room.depth_m - (f.y_m + f.depth_m),
            "south": f.y_m,
            "east": room.width_m - (f.x_m + f.width_m),
            "west": f.x_m,
        }[wall]
        if near <= 0.3:
            along = (
                (f.x_m, f.x_m + f.width_m)
                if wall in ("north", "south")
                else (f.y_m, f.y_m + f.depth_m)
            )
            spans.append((along[0] - 0.1, along[1] + 0.1))
    return sorted(spans)


def _free_spans(room, wall, design):
    cursor, end, free = 0.1, _wall_length(room, wall) - 0.1, []
    for lo, hi in _blocked(room, wall, design, 0.25):
        if lo > cursor:
            free.append((cursor, min(lo, end)))
        cursor = max(cursor, hi)
    if cursor < end:
        free.append((cursor, end))
    return [(a, b) for a, b in free if b - a > 1e-6]


def _place_art(design, pack):
    room = design.room
    spans = [
        (b - a, -i, wall, a, b)
        for i, wall in enumerate(WALLS)
        for a, b in _free_spans(room, wall, design)
    ]
    if not spans:
        return None, "art:no_free_wall"
    length, _, wall, a, b = max(spans)
    if length < 0.6:
        return None, "art:no_free_wall"
    width = min(1.2, 0.6 * length)
    height = min(0.9, width * 0.75)
    z = min(1.5 - height / 2, room.ceiling_height_m - 0.25 - height)
    start = (a + b) / 2 - width / 2
    rect = _wall_box(room, wall, start, width, 0.03, 0.0)
    return _item(
        "art", "art", pack.decor.art, rect, z, height, wall, FACING[wall]
    ), None


def _place_curtains(design, pack):
    room = design.room
    out = []
    for window in room.windows:
        wall = window.wall
        lo = max(0.0, window.offset_m - 0.15)
        hi = min(_wall_length(room, wall), window.offset_m + window.width_m + 0.15)
        for door in room.doors:
            if door.wall == wall:
                if door.offset_m + door.width_m <= window.offset_m:
                    lo = max(lo, door.offset_m + door.width_m)
                elif door.offset_m >= window.offset_m + window.width_m:
                    hi = min(hi, door.offset_m)
        rect = _wall_box(room, wall, lo, hi - lo, 0.08, 0.06)
        height = room.ceiling_height_m - 0.14
        out.append(
            _item(
                f"curtain:{window.id}",
                "curtain",
                pack.decor.curtain,
                rect,
                0.02,
                height,
                wall,
                FACING[wall],
            )
        )
    return out


def _place_mouldings(design):
    room = design.room
    height = 0.09
    return [
        _item(
            f"moulding:{wall}",
            "moulding",
            None,
            _wall_box(room, wall, 0.0, _wall_length(room, wall), 0.05, 0.0),
            room.ceiling_height_m - height,
            height,
            wall,
            FACING[wall],
        )
        for wall in WALLS
    ]


def _place_pendant(design, pack):
    room = design.room
    tables = [
        f
        for f in design.furniture
        if f.category == "table" and f.width_m * f.depth_m >= 0.45
    ]
    beds = [f for f in design.furniture if f.category == "bed"]
    target = max(tables or beds, key=lambda f: f.width_m * f.depth_m, default=None)
    cx, cy = (
        (target.x_m + target.width_m / 2, target.y_m + target.depth_m / 2)
        if target
        else (room.width_m / 2, room.depth_m / 2)
    )
    size, drop = 0.45, 0.7
    return _item(
        "pendant",
        "pendant",
        pack.decor.pendant,
        (cx - size / 2, cy - size / 2, size, size),
        room.ceiling_height_m - drop,
        drop,
    )


def _spots(room, w, d, rng):
    inset = 0.05
    corners = [
        (inset, inset),
        (room.width_m - inset - w, inset),
        (inset, room.depth_m - inset - d),
        (room.width_m - inset - w, room.depth_m - inset - d),
    ]
    rng.shuffle(corners)
    walls = []
    for t in (0.25, 0.5, 0.75):
        walls += [
            (room.width_m * t - w / 2, inset),
            (room.width_m * t - w / 2, room.depth_m - inset - d),
            (inset, room.depth_m * t - d / 2),
            (room.width_m - inset - w, room.depth_m * t - d / 2),
        ]
    rng.shuffle(walls)
    return [(x, y) for x, y in corners + walls if x >= 0 and y >= 0]


def _place_floor_items(design, pack, rng, density, flat):
    wanted = [
        ("plant", pack.decor.plant, PLANT),
        ("floor_lamp", pack.decor.floor_lamp, FLOOR_LAMP),
    ]
    wanted += [
        ("accent", c.asset_id, (c.width_m, c.depth_m, c.height_m))
        for c in pack.decor.accents
    ]
    wanted = wanted[: math.ceil(len(wanted) * density)]
    room = design.room
    placed, rows, skipped = [], [], []
    if any(f.category in WET_CATEGORIES for f in design.furniture):
        # Bathrooms keep a plant but no lamps or loose furniture.
        skipped += [f"{kind}:wet_room" for kind, _, _ in wanted if kind != "plant"]
        wanted = [w for w in wanted if w[0] == "plant"]
    for n, (kind, asset_id, (w, d, h)) in enumerate(wanted):
        item_id = kind if kind != "accent" else f"accent:{n}"
        found = None
        for x, y in _spots(room, w, d, rng):
            if x + w > room.width_m or y + d > room.depth_m:
                continue
            here = _shape(x, y, w, d)
            if any(
                other.kind != "rug"
                and other.z_m < h
                and here.intersection(
                    _shape(other.x_m, other.y_m, other.width_m, other.depth_m)
                ).area
                > 1e-9
                for other in (*flat, *placed)
            ):
                continue
            row = Furniture(
                id=f"decor:{item_id}",
                name=kind,
                category="decor",
                x_m=_r(x),
                y_m=_r(y),
                width_m=_r(w),
                depth_m=_r(d),
                height_m=_r(h),
            )
            trial = RoomDesign(room=room, furniture=[*design.furniture, *rows, row])
            if validate_accessibility(trial).status == "passed":
                found = row
                break
        if found is None:
            skipped.append(f"{kind}:{asset_id or 'procedural'}:no_free_spot")
            continue
        rows.append(found)
        placed.append(
            _item(
                item_id,
                kind,
                asset_id,
                (found.x_m, found.y_m, found.width_m, found.depth_m),
                0,
                found.height_m,
            )
        )
    return placed, skipped


def place_dressing(
    design: RoomDesign, pack: StylePack, seed: int, density: float = 1.0
) -> Dressing:
    """Deterministic for (design, pack, seed, density); never edits ``design``."""
    rng = random.Random(seed)
    zones = _door_zones(design.room)
    items, skipped = [], []
    rug, why = _place_rug(design, pack, zones)
    items += [rug] if rug else []
    skipped += [why] if why else []
    art, why = _place_art(design, pack)
    items += [art] if art else []
    skipped += [why] if why else []
    items += _place_curtains(design, pack)
    if pack.decor.mouldings:
        items += _place_mouldings(design)
    items.append(_place_pendant(design, pack))
    floor, missed = _place_floor_items(design, pack, rng, density, items)
    return Dressing(items=items + floor, skipped=skipped + missed)
