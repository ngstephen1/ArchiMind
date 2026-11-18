"""Seeded, single-storey gallery houses. All coordinates are metres, east/north."""

import copy
import hashlib
import json
import math
import random
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import Point, box
from shapely.ops import unary_union

from archimind.assets import furniture_from_planning_envelope
from archimind.assets.render_assets import BELAYA_ID
from archimind.assets.selection import build_render_bindings
from archimind.geometry import generate_layout_candidates, validate_accessibility
from archimind.models import Door, Furniture, Room, RoomDesign, Window

Kind = Literal["salon", "bedroom", "study", "living", "kitchen-dining", "bathroom"]
PROGRAM = ["bedroom", "study", "living", "kitchen-dining", "bathroom"]
STUDIO_ITEMS = {
    "salon": [
        ("salon-suite", "seating", 2.8, 2.35, 0.94),
        ("salon-dining", "dining", 2.2, 2.92, 1.0),
    ],
    "living": [("media-console", "storage", 1.6, 0.38, 0.64)],
    "study": [("bookcase", "storage", 0.85, 0.34, 1.75)],
}
ITEMS = {
    "salon": [],
    "bedroom": [("queen-bed", "bed", 1.6, 2, 0.6)],
    "living": [
        ("sofa", "sofa", 2, 0.85, 0.86),
        ("coffee-table", "table", 1, 0.54, 0.42),
    ],
    "study": [("work-table", "desk", 1.45, 0.72, 0.76)],
    "kitchen-dining": [
        ("counter", "counter", 2, 0.64, 0.92),
        ("dining-table", "table", 1.3, 0.75, 0.75),
    ],
    "bathroom": [
        ("vanity", "vanity", 0.85, 0.5, 0.85),
        ("tub", "bath", 1.5, 0.72, 0.55),
    ],
}


# Each ensemble reserves the complete arrangement, including the chairs.
STUDIO_ENSEMBLES = {
    "living": [("reading-suite", "seating", 2.85, 2.35, 1.4)],
    "study": [("writing-suite", "desk", 1.75, 1.85, 1.13)],
    "kitchen-dining": [
        ("counter", "counter", 2, 0.64, 0.92),
        ("breakfast-suite", "table", 1.75, 2.4, 0.87),
    ],
}


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    width: float = Field(default=13, ge=9, le=15)
    depth: float = Field(default=13, ge=9, le=16)
    priority: Literal[
        "balanced", "quiet bedroom", "bright study", "quiet bedroom and bright study"
    ] = "balanced"
    formal_salon: bool = False
    palette: Literal["oak", "sage", "terracotta"] = "oak"
    seed: int = Field(default=42, ge=0, le=1000000)
    closer_study_desk: bool = False
    locks: list[Kind] = Field(default_factory=list, max_length=6)


def interpret_offline(brief, text):
    """Accept a small, complete vocabulary. Every requested clause must resolve."""
    if not text.strip():
        return brief
    values = brief.model_dump()
    priorities = {
        "quiet bedroom": "quiet bedroom",
        "move the bedroom away from the entrance": "quiet bedroom",
        "bright study": "bright study",
        "give the study more daylight": "bright study",
        "balanced layout": "balanced",
    }
    updates = {}
    message = text.strip().lower().rstrip(".!")
    message = re.sub(
        r"^(?:please )?(?:design|create) (?:a )?(?:five-room home with )?", "", message
    )
    for clause in re.split(r"\s+(?:and|with)\s+|[;,]", message):
        clause = " ".join(clause.split())
        clause = re.sub(r"^(?:a|an) ", "", clause)
        if clause == "move the study desk closer to its window":
            values["closer_study_desk"] = True
            continue
        if clause in {"formal salon", "entertaining guests", "salon for entertaining"}:
            values["formal_salon"] = True
            continue
        if clause == "quiet work":
            clause = "quiet bedroom and bright study"
            priorities[clause] = clause
        if clause == "compact everyday living":
            values.update(width=10.5, depth=11.5)
            continue
        if clause == "writing desk":
            # Every generated bedroom includes the qualified Belaya.
            continue
        if clause == "warm finishes":
            clause = "oak finishes"
        if clause in priorities:
            key, value = "priority", priorities[clause]
        elif match := re.fullmatch(
            r"(?:use )?(oak|sage|terracotta)(?: finishes)?", clause
        ):
            key, value = "palette", match[1]
        elif match := re.fullmatch(
            r"keep (?:the )?(bedroom|living|study|kitchen-dining|bathroom)(?: where it is)?",
            clause,
        ):
            values["locks"] = sorted(set(values["locks"]) | {match[1]})
            continue
        else:
            raise ValueError(
                "Offline briefs support ‘quiet bedroom’, ‘bright study’, a finish, or ‘keep the bedroom’. Revise the request or explicitly enable live interpretation."
            )
        if key in updates and updates[key] != value:
            if key == "priority" and {updates[key], value} == {
                "quiet bedroom",
                "bright study",
            }:
                value = "quiet bedroom and bright study"
            else:
                raise ValueError(
                    "Choose one compatible priority and one finish per revision."
                )
        updates[key] = value
    return Brief.model_validate(values | updates)


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def opening(wall, offset, name):
    return Door(id=name, wall=wall, offset_m=offset, width_m=1.1, height_m=2.15)


def validate_home(home):
    """Verify coverage, portal pairing and connectivity in furnished free space."""
    width, depth = home["width"], home["depth"]
    hall = home["hall"]
    areas = [box(hall, 0, hall + 1.6, depth)]
    solids = []
    targets = []
    kinds = []
    for part in home["rooms"]:
        d = RoomDesign.model_validate(part["design"])
        r = d.room
        kinds.append(r.id)
        orientation = part.get("suite_yaw_deg", 0)
        if orientation not in (0, 90) or (orientation and r.id != "salon"):
            raise ValueError("Unsupported salon grouping orientation.")
        if r.id == "salon":
            by_id = {f.id: f for f in d.furniture}
            for ident, _, group_width, group_depth, height in STUDIO_ITEMS["salon"]:
                if ident == "salon-suite" and orientation:
                    group_width, group_depth = group_depth, group_width
                item = by_id.get(ident)
                if item is None or (item.width_m, item.depth_m, item.height_m) != (
                    group_width,
                    group_depth,
                    height,
                ):
                    raise ValueError(
                        "Salon furniture must retain the checked group footprint."
                    )
        x, y = part["origin"]
        areas.append(box(x, y, x + r.width_m, y + r.depth_m))
        if len(r.doors) != 1:
            raise ValueError("Each room needs one entrance to the hall.")
        door = r.doors[0]
        west = door.wall == "west"
        seam = x if west else x + r.width_m
        if (
            door.wall not in ("east", "west")
            or abs(seam - (hall + 1.6 if west else hall)) > 1e-6
        ):
            raise ValueError("A doorway does not join the circulation hall.")
        low = y + door.offset_m
        high = low + door.width_m
        if (
            not (y <= low < high <= y + r.depth_m)
            or validate_accessibility(d).status != "passed"
        ):
            raise ValueError("A furnished room failed its spatial checks.")
        for window in r.windows:
            if (
                window.wall != ("east" if west else "west")
                or abs((x + r.width_m - width) if west else x) > 1e-6
            ):
                raise ValueError("Window must open onto an exterior wall.")
        solids.extend(
            [
                box(seam - 0.055, y, seam + 0.055, low),
                box(seam - 0.055, high, seam + 0.055, y + r.depth_m),
            ]
        )
        for side in (y, y + r.depth_m):
            solids.append(box(x, side - 0.055, x + r.width_m, side + 0.055))
        for f in d.furniture:
            solids.append(
                box(x + f.x_m, y + f.y_m, x + f.x_m + f.width_m, y + f.y_m + f.depth_m)
            )
        targets.append(Point(seam + (0.7 if west else -0.7), low + door.width_m / 2))
    shell = box(0, 0, width, depth)
    coverage = unary_union(areas)
    if (
        sorted(kinds) != sorted(PROGRAM + (["salon"] if "salon" in kinds else []))
        or shell.symmetric_difference(coverage).area > 1e-5
        or sum(a.area for a in areas) - coverage.area > 1e-5
    ):
        raise ValueError("Room partitions must tile the lot.")
    free = shell.buffer(-0.3).difference(unary_union(solids).buffer(0.3))
    entry = Point(hall + 0.8, 0.4)
    regions = getattr(free, "geoms", [free])
    if not any(g.covers(entry) and all(g.covers(t) for t in targets) for g in regions):
        raise ValueError("Entrance cannot reach every furnished room.")


def dress_bedroom(design):
    """Place a working chair and bedside light assembly within checked footprints."""
    bed = next(f for f in design.furniture if f.id == "queen-bed")
    desk = next(f for f in design.furniture if f.id == "belaya")
    for dy in (-0.58, desk.depth_m + 0.06):
        chair = Furniture(
            id="desk-chair",
            name="Oak writing chair",
            category="chair",
            width_m=0.48,
            depth_m=0.52,
            height_m=0.83,
            rotation_deg=0,
            x_m=desk.x_m + (desk.width_m - 0.48) / 2,
            y_m=desk.y_m + dy,
        )
        for dx in (-0.52, bed.width_m + 0.04):
            table = Furniture(
                id="bedside-lamp",
                name="Nightstand with reading lamp",
                category="table",
                width_m=0.48,
                depth_m=0.43,
                height_m=1.06,
                rotation_deg=0,
                x_m=bed.x_m + dx,
                y_m=bed.y_m + bed.depth_m - 0.43,
            )
            furnished = design.model_copy(
                update={"furniture": [*design.furniture, chair, table]}
            )
            if validate_accessibility(furnished).status == "passed":
                return furnished
    return None


def revise_study_desk(brief, previous):
    if not previous or "study" in brief.locks:
        raise ValueError("Apply a home and unlock its study before moving the desk.")
    if (brief.width, brief.depth) != (
        previous["width"],
        previous["depth"],
    ) or brief.priority != "balanced":
        raise ValueError(
            "Submit the desk move separately from shell or priority changes."
        )
    home = copy.deepcopy(previous)
    design = next(
        r["design"] for r in home["rooms"] if r["design"]["room"]["id"] == "study"
    )
    room = design["room"]
    desk = next(
        (f for f in design["furniture"] if f["id"] in {"work-table", "writing-suite"}),
        None,
    )
    if not desk or len(room["windows"]) != 1:
        raise ValueError("A unique study desk and window are required.")
    window = room["windows"][0]
    wx = room["width_m"] if window["wall"] == "east" else 0
    wy = window["offset_m"] + window["width_m"] / 2

    def distance(x, y):
        return math.hypot(wx - x - desk["width_m"] / 2, wy - y - desk["depth_m"] / 2)

    before = distance(desk["x_m"], desk["y_m"])
    ymax = room["depth_m"] - desk["depth_m"]
    xmax = room["width_m"] - desk["width_m"]
    points = {
        (x, min(ymax, max(0, wy - desk["depth_m"] / 2 + dy)))
        for x in (0, xmax)
        for dy in (0, -0.3, 0.3, -0.6, 0.6)
    }
    for x, y in sorted(points, key=lambda pt: (distance(*pt), pt)):
        after = distance(x, y)
        if after >= before - 1e-6:
            break
        desk.update(x_m=x, y_m=y)
        try:
            validate_home(home)
        except ValueError:
            continue
        home["palette"] = brief.palette
        home["evidence"]["study_desk_window_center_distance_m"] = {
            "before": before,
            "after": after,
        }
        home.pop("id")
        home["id"] = digest(home)
        return home
    raise ValueError(
        "No validated study desk position closer to this window was found."
    )


def generate(brief, previous=None, *, on_progress=None):
    if brief.closer_study_desk:
        home = revise_study_desk(brief, previous)
        if on_progress:
            on_progress("Furnished candidate", home)
        return [home]
    if brief.locks and not previous:
        raise ValueError("Apply a home before locking rooms.")
    if brief.locks and (brief.width, brief.depth) != (
        previous["width"],
        previous["depth"],
    ):
        raise ValueError("Keep the shell dimensions to preserve locked rooms.")
    salon = brief.formal_salon or bool(
        previous
        and any(p["design"]["room"]["id"] == "salon" for p in previous["rooms"])
    )
    if (
        salon
        and brief.locks
        and not any(p["design"]["room"]["id"] == "salon" for p in previous["rooms"])
    ):
        raise ValueError("Adding a salon requires repartitioning. Unlock rooms first.")
    candidates = []
    for attempt in range(8):
        rng = random.Random(brief.seed + 7919 * attempt)
        hall = round((brief.width - 1.6) * rng.uniform(0.46, 0.54), 3)
        rows = [["living", "bedroom"], ["kitchen-dining", "bathroom", "study"]]
        for row in rows:
            rng.shuffle(row)
        if "quiet bedroom" in brief.priority:
            rows[0] = ["living", "bedroom"]
        if salon:
            rows[0].insert(0, "salon")
        partitions = []
        for side, row in enumerate(rows):
            x = 0 if side == 0 else hall + 1.6
            w = hall if side == 0 else brief.width - x
            weights = [rng.uniform(0.9, 1.2) if k != "bathroom" else 0.78 for k in row]
            y = 0
            for n, (k, weight) in enumerate(zip(row, weights)):
                h = (
                    brief.depth - y
                    if n == len(row) - 1
                    else round(brief.depth * weight / sum(weights), 3)
                )
                partitions.append((k, x, y, w, h))
                y += h
        if brief.locks:
            hall = previous["hall"]
            partitions = [
                (
                    p["design"]["room"]["id"],
                    *p["origin"],
                    p["design"]["room"]["width_m"],
                    p["design"]["room"]["depth_m"],
                )
                for p in previous["rooms"]
            ]
        if on_progress:
            on_progress(
                "Proposed partitions",
                {
                    "width": brief.width,
                    "depth": brief.depth,
                    "rooms": [
                        {"name": k, "x": x, "y": y, "w": w, "d": h}
                        for k, x, y, w, h in partitions
                    ],
                },
            )
        rooms = []
        for k, x, y, w, h in partitions:
            if k in brief.locks:
                rooms.append(
                    next(r for r in previous["rooms"] if r["design"]["room"]["id"] == k)
                )
                continue
            window_width = min(
                h - 0.6,
                2.85
                if k == "salon"
                else 2.5
                if k == "study" and "bright study" in brief.priority
                else 1.4,
            )
            r = Room(
                id=k,
                name=k.title(),
                width_m=w,
                depth_m=h,
                ceiling_height_m=2.8,
                doors=[
                    opening("east" if x == 0 else "west", (h - 1.1) / 2, k + "-door")
                ],
                windows=[
                    Window(
                        id=k + "-window",
                        wall="west" if x == 0 else "east",
                        offset_m=(h - window_width) / 2,
                        width_m=window_width,
                        height_m=1.75 if k == "salon" else 1.15,
                        sill_height_m=0.55 if k == "salon" else 1,
                    )
                ],
            )
            rotate_suite = k == "salon" and brief.seed % 2 == 1
            items = [
                Furniture(
                    id=i,
                    name=i.replace("-", " ").title(),
                    category=c,
                    width_m=b if rotate_suite and i == "salon-suite" else a,
                    depth_m=a if rotate_suite and i == "salon-suite" else b,
                    height_m=z,
                    x_m=0,
                    y_m=0,
                    rotation_deg=0,
                )
                for i, c, a, b, z in (
                    STUDIO_ENSEMBLES.get(k, ITEMS[k]) if salon else ITEMS[k]
                )
                + (STUDIO_ITEMS.get(k, []) if salon else [])
            ]
            proofs = {}
            if k == "bedroom":
                spec = furniture_from_planning_envelope(
                    BELAYA_ID,
                    furniture_id="belaya",
                    name="Belaya writing desk",
                    x_m=0.0,
                    y_m=0.0,
                )
                items.append(spec.furniture)
                proofs[spec.furniture.id] = spec.binding
            res = generate_layout_candidates(
                r, items, seed=rng.randrange(100000), max_candidates=1, max_attempts=40
            )
            if not res.candidates:
                break
            design = res.candidates[0].design
            if k == "bedroom":
                design = dress_bedroom(design)
                if design is None:
                    break
            resolved = build_render_bindings(design, planning_bindings=proofs)
            rooms.append(
                dict(
                    origin=[x, y],
                    **({"suite_yaw_deg": 90} if rotate_suite else {}),
                    asset_bindings=[
                        b.model_dump(mode="json") for b in resolved.bindings
                    ],
                    design=design.model_dump(mode="json"),
                )
            )
        home = dict(
            version=1,
            width=brief.width,
            depth=brief.depth,
            hall=hall,
            rooms=rooms,
            palette=brief.palette,
        )
        if len(rooms) != len(PROGRAM) + int(salon):
            continue
        try:
            validate_home(home)
        except ValueError:
            continue
        bedroom = next(p for p in rooms if p["design"]["room"]["id"] == "bedroom")
        rear = bedroom["origin"][1] + bedroom["design"]["room"]["depth_m"] / 2
        home["evidence"] = {
            "reachable_rooms": len(rooms),
            "bedroom_center_from_front_m": round(rear, 2),
            "study_window_width_m": next(
                p for p in rooms if p["design"]["room"]["id"] == "study"
            )["design"]["room"]["windows"][0]["width_m"],
        }
        if salon:
            home["evidence"]["salon"] = {
                "dining_places": 4,
                "chair_pullout_m": 0.5,
                "basis": "A reserved dining group includes a 0.50 m withdrawal strip behind each chair row.",
                "seating": "A three-piece conversation group faces the central coffee table.",
            }
        home["id"] = digest(home)
        if home not in candidates:
            candidates.append(home)
            if on_progress:
                on_progress("Furnished candidate", home)
        if len(candidates) == 2:
            break
    if not candidates:
        raise ValueError("Search exhausted without a connected furnished home.")
    if "quiet bedroom" in brief.priority:
        candidates.sort(key=lambda c: -c["evidence"]["bedroom_center_from_front_m"])
    return candidates
