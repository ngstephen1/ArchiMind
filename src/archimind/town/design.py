"""Seeded, single-storey gallery houses. All coordinates are metres, east/north."""

import copy
import hashlib
import json
import math
import random
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from archimind.assets import furniture_from_planning_envelope
from archimind.assets.render_assets import BELAYA_ID
from archimind.assets.selection import build_render_bindings
from archimind.geometry import generate_layout_candidates, validate_accessibility
from archimind.models import Door, Furniture, Room, RoomDesign, Window
from archimind.style_packs import (
    DEFAULT_STYLE,
    LEGACY_PALETTE_TO_STYLE,
    STYLE_CLARIFICATION,
    STYLE_TO_LEGACY_PALETTE,
    StyleId,
    load_pack,
    resolve_style_phrase,
    styles_mentioned,
)
from archimind.style_packs.scene import style_payload
from archimind.town.service_layout import (
    FIXTURES,
    design_service_room,
    service_evidence,
)

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


class RoomGoal(BaseModel):
    """A preference scored using straight-line room-center distance in plan."""

    model_config = ConfigDict(extra="forbid")
    room: Kind
    relation: Literal["near", "far"]
    target: Kind


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    width: float = Field(default=13, ge=9, le=15)
    depth: float = Field(default=13, ge=9, le=16)
    priority: Literal[
        "balanced", "quiet bedroom", "bright study", "quiet bedroom and bright study"
    ] = "balanced"
    style: StyleId = DEFAULT_STYLE
    room_goals: list[RoomGoal] = Field(default_factory=list, max_length=4)
    formal_salon: bool = False
    compare_tradeoffs: bool = False
    dining_seats: int = Field(default=0, ge=0, le=100)
    split_dining: bool = False
    service_layout: bool = False
    passage_m: float = Field(default=0.6, ge=0.6, le=2)
    seed: int = Field(default=42, ge=0, le=1000000)
    shift_bedroom_chair: bool = False
    closer_study_desk: bool = False
    locks: list[Kind] = Field(default_factory=list, max_length=6)

    @model_validator(mode="before")
    @classmethod
    def _legacy_palette(cls, data):
        # Stored briefs and older clients send a finish palette; map it to a style.
        if isinstance(data, dict) and "palette" in data:
            data = dict(data)
            palette = data.pop("palette")
            if palette not in LEGACY_PALETTE_TO_STYLE:
                raise ValueError("palette must be oak, sage or terracotta")
            data.setdefault("style", LEGACY_PALETTE_TO_STYLE[palette])
        return data


def apply_style(home, style):
    """Record the home's pack, the palette older readers understand, and dress
    every room (locked ones included) from that pack."""
    pack = load_pack(style)
    home["style_pack"] = {"id": style, "version": pack.version}
    home["palette"] = STYLE_TO_LEGACY_PALETTE[style]
    for part in home["rooms"]:
        design = RoomDesign.model_validate(part["design"])
        # Seeded by the room itself so a re-dress of unchanged geometry is stable.
        seed = int(hashlib.sha256(design.room.id.encode()).hexdigest()[:8], 16)
        # A user-chosen designer chair keeps its reservation.
        designer = {"desk-chair"} if part.get("designer_chair") else set()
        designer |= set(part.get("designer_collection", {}))
        designer.add("belaya")  # Town renders this reserved product or its fallback.
        part["style"] = style_payload(design, pack, seed, designer_ids=designer)
        if home.get("presentation_detail") and design.room.id in ("salon", "bedroom"):
            for item in part["style"]["dressing"]:
                if item["kind"] in ("plant", "curtain"):
                    item["refined"] = True
    return home


_STYLE_MARKERS = r"(?: (?:style|styled|look|finishes|finish|interiors?|vibe|feel))+"


def style_clause(clause):
    """The style a single clause asks for, or None if it is not about style.

    Raises the style clarification when the clause names two styles or an
    unknown one ("gothic style").
    """
    clause = " ".join(clause.lower().strip().rstrip(".!").split())
    if clause == "warm finishes":
        clause = "oak finishes"
    core = re.sub(
        r"^(?:(?:please )?make (?:it|the home|everything) |go |use |(?:a|an|the) )+",
        "",
        clause,
    )
    marked = bool(re.search(_STYLE_MARKERS + "$", core))
    core = re.sub(_STYLE_MARKERS + "$", "", core)
    if core in LEGACY_PALETTE_TO_STYLE:
        return LEGACY_PALETTE_TO_STYLE[core]
    if style := resolve_style_phrase(core):
        return style
    mentioned = styles_mentioned(clause) | {
        LEGACY_PALETTE_TO_STYLE[w]
        for w in clause.split()
        if w in LEGACY_PALETTE_TO_STYLE
    }
    if mentioned or marked or clause.startswith("make it "):
        raise ValueError(STYLE_CLARIFICATION)
    return None


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
    for clause in re.split(r"\s+(?:and|with|in)\s+|[;,]", message):
        clause = " ".join(clause.split())
        clause = re.sub(r"^(?:a|an) ", "", clause)
        if clause == "quiet study":
            values["room_goals"].append(
                dict(room="study", relation="far", target="living")
            )
            continue
        rooms = "|".join(["salon", *PROGRAM])
        pair = re.fullmatch(
            rf"(?:put |place )?(?:the )?({rooms}) (near|away from) (?:the )?({rooms})",
            clause,
        )
        if pair:
            room, relation, target = pair.groups()
            values["room_goals"].append(
                dict(
                    room=room,
                    relation="near" if relation == "near" else "far",
                    target=target,
                )
            )
            continue
        if clause == "move the bedroom desk chair":
            values["shift_bedroom_chair"] = True
            continue
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
        if clause in priorities:
            key, value = "priority", priorities[clause]
        elif match := re.fullmatch(
            r"keep (?:the )?(bedroom|living|study|kitchen-dining|bathroom)(?: where it is)?",
            clause,
        ):
            values["locks"] = sorted(set(values["locks"]) | {match[1]})
            continue
        elif style := style_clause(clause):
            key, value = "style", style
        else:
            raise ValueError(
                "Offline briefs support ‘quiet bedroom’, ‘bright study’, ‘quiet study’, ‘study away from living’, ‘bathroom near bedroom’, a finish, a style, or ‘keep the bedroom’. Revise the request or explicitly enable live interpretation."
            )
        if key == "style" and updates.get(key, value) != value:
            raise ValueError(STYLE_CLARIFICATION)
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


def validate_home(home, *, passage_m=None, measure=False):
    """Verify coverage, portal pairing and connectivity in furnished free space."""
    recorded = home.get("evidence", {}).get("comparison", {}).get("passage_m", 0.6)
    passage_m = max(recorded, passage_m if passage_m is not None else 0.6)
    width, depth = home["width"], home["depth"]
    hall = home["hall"]
    areas = [box(hall, 0, hall + 1.6, depth)]
    solids = []
    targets = {}
    openings = {}
    kinds = []
    service_rooms = {}
    for part in home["rooms"]:
        d = RoomDesign.model_validate(part["design"])
        r = d.room
        if home.get("service_layout") and r.id in FIXTURES:
            service_rooms[r.id] = service_evidence(d, passage_m=passage_m)
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
        if home.get("presentation_detail"):
            for row in part.get("style", {}).get("dressing", []):
                if row["kind"] in {"plant", "floor_lamp", "accent"}:
                    px, py = x + row["x_m"], y + row["y_m"]
                    solids.append(box(px, py, px + row["width_m"], py + row["depth_m"]))
        targets[r.id] = (seam + (0.7 if west else -0.7), low + door.width_m / 2)
        openings[r.id] = door.width_m
    shell = box(0, 0, width, depth)
    coverage = unary_union(areas)
    if (
        sorted(kinds) != sorted(PROGRAM + (["salon"] if "salon" in kinds else []))
        or shell.symmetric_difference(coverage).area > 1e-5
        or sum(a.area for a in areas) - coverage.area > 1e-5
    ):
        raise ValueError("Room partitions must tile the lot.")
    radius = passage_m / 2
    free = shell.buffer(-radius).difference(unary_union(solids).buffer(radius))
    entry = Point(hall + 0.8, max(0.4, radius + 0.001))
    regions = getattr(free, "geoms", [free])
    if not any(
        g.covers(entry) and all(g.covers(Point(t)) for t in targets.values())
        for g in regions
    ):
        raise ValueError(
            f"Entrance cannot reach every furnished room at {passage_m:g} m passage width."
        )
    if measure:
        routes = []
        for a, b in (
            ("study", "living"),
            ("kitchen-dining", "salon"),
            ("bedroom", "bathroom"),
        ):
            if a not in targets or b not in targets:
                continue
            first, last = targets[a], targets[b]
            route = LineString(
                (first, (hall + 0.8, first[1]), (hall + 0.8, last[1]), last)
            )
            if free.covers(route):
                routes.append(dict(room=a, target=b, distance_m=round(route.length, 3)))
        seats = {
            part["design"]["room"]["id"]: 4
            for part in home["rooms"]
            if any(
                f["id"] in ("salon-dining", "breakfast-suite")
                for f in part["design"]["furniture"]
            )
        }
        return dict(
            routes=routes,
            modeled_openings_m=openings,
            dining_places=seats,
            passage_m=passage_m,
            **({"service_rooms": service_rooms} if service_rooms else {}),
        )
    return None


def refresh_geometry_evidence(home):
    """Recheck carried constraints and refresh measurements after an edit."""
    comparison = home["evidence"].get("comparison")
    measurements = validate_home(home, measure=comparison is not None)
    if comparison is not None:
        comparison.update(measurements)


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


def revise_bedroom_chair(brief, previous):
    # check_brief has confirmed the saved home, unlocked bedroom and isolated edit.
    home = copy.deepcopy(previous)
    part = next(p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom")
    furniture = {f["id"]: f for f in part["design"]["furniture"]}
    desk, chair = furniture.get("belaya"), furniture.get("desk-chair")
    if not desk or not chair:
        raise ValueError("The saved bedroom needs a desk and chair.")
    before = chair["x_m"]
    left = desk["x_m"] + 0.10
    right = desk["x_m"] + desk["width_m"] - chair["width_m"] - 0.10
    for x in sorted((left, right), key=lambda x: abs(x - before), reverse=True):
        if abs(x - before) < 0.10:
            continue
        chair["x_m"] = x
        try:
            validate_home(home, passage_m=brief.passage_m)
        except ValueError:
            continue
        apply_style(home, brief.style)
        refresh_geometry_evidence(home)
        home["evidence"]["chair_move_m"] = {
            "from_x": before,
            "to_x": x,
            "y": chair["y_m"],
        }
        home.pop("id")
        home["id"] = digest(home)
        return home
    raise ValueError(
        "No alternate chair position at this desk passed spatial validation."
    )


def revise_study_desk(brief, previous):
    # check_brief has confirmed the saved home, unlocked study and isolated edit.
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
            validate_home(home, passage_m=brief.passage_m)
        except ValueError:
            continue
        apply_style(home, brief.style)
        refresh_geometry_evidence(home)
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


def check_brief(brief, previous=None):
    """Raise ValueError for a brief that generation would reject before searching.

    Town calls this before any layout job so the user can confirm the hard
    requirements in the reviewed brief; ``generate`` applies the same checks.
    """
    _requirement_boundaries(brief, previous)


def _requirement_boundaries(brief, previous):
    pairs = {}
    for goal in brief.room_goals:
        pair = tuple(sorted((goal.room, goal.target)))
        if goal.room == goal.target or (pair in pairs and pairs[pair] != goal.relation):
            raise ValueError("Clarify the conflicting room-distance preferences.")
        pairs[pair] = goal.relation
    if pairs and brief.locks:
        raise ValueError("Unlock rooms before comparing different room placements.")
    if pairs and (brief.shift_bedroom_chair or brief.closer_study_desk):
        raise ValueError(
            "Apply room-distance preferences separately from a furniture move."
        )
    if previous and brief.locks:
        saved_rooms = {part["design"]["room"]["id"] for part in previous["rooms"]}
        missing_locks = set(brief.locks) - saved_rooms
        if missing_locks and not (brief.formal_salon and "salon" not in saved_rooms):
            missing = ", ".join(sorted(missing_locks))
            raise ValueError(
                f"Cannot lock rooms absent from the saved home: {missing}."
            )
    if brief.shift_bedroom_chair or brief.closer_study_desk:
        if brief.service_layout and not (previous or {}).get("service_layout"):
            raise ValueError(
                "Plan kitchen and bathroom fixtures in a separate run before moving furniture."
            )
        if (
            brief.formal_salon
            and previous
            and not any(p["design"]["room"]["id"] == "salon" for p in previous["rooms"])
        ):
            raise ValueError(
                "Add the salon in a separate layout revision before moving furniture."
            )
        carried = (previous or {}).get("evidence", {}).get("comparison", {})
        if (
            brief.dining_seats != carried.get("required_dining_seats", 0)
            or brief.split_dining != carried.get("split_dining", False)
            or brief.passage_m != carried.get("passage_m", 0.6)
        ):
            raise ValueError(
                "Confirm new seating or circulation requirements in a separate design run before moving furniture."
            )
        chair = brief.shift_bedroom_chair
        if not previous or ("bedroom" if chair else "study") in brief.locks:
            raise ValueError(
                "Apply a home and unlock its bedroom before moving the chair."
                if chair
                else "Apply a home and unlock its study before moving the desk."
            )
        if (
            (chair and brief.closer_study_desk)
            or brief.priority != "balanced"
            or (brief.width, brief.depth) != (previous["width"], previous["depth"])
        ):
            raise ValueError(
                "Submit the chair move separately from desk, shell or priority changes."
                if chair
                else "Submit the desk move separately from shell or priority changes."
            )
        return pairs, None
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
    if brief.dining_seats and (
        not salon or brief.dining_seats > (8 if brief.split_dining else 4)
    ):
        raise ValueError(
            "Dining requires up to four places at one table, or up to eight across the two dining rooms after explicit confirmation. Review the seating requirement."
        )
    if not salon and any("salon" in pair for pair in pairs):
        raise ValueError("Include a formal salon before requesting its placement.")
    return pairs, salon


def generate(brief, previous=None, *, on_progress=None):
    pairs, salon = _requirement_boundaries(brief, previous)
    if brief.shift_bedroom_chair or brief.closer_study_desk:
        home = (
            revise_bedroom_chair if brief.shift_bedroom_chair else revise_study_desk
        )(brief, previous)
        if on_progress:
            on_progress("Furnished candidate", home)
        return [home]
    previous_comparison = (previous or {}).get("evidence", {}).get("comparison")
    services = brief.service_layout or bool((previous or {}).get("service_layout"))
    presentation_detail = brief.compare_tradeoffs or (previous or {}).get(
        "presentation_detail"
    )
    measure = (
        brief.compare_tradeoffs
        or services
        or previous_comparison is not None
        or brief.dining_seats > 0
        or brief.passage_m != 0.6
    )
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
                locked = next(
                    room
                    for room in previous["rooms"]
                    if room["design"]["room"]["id"] == k
                )
                # Candidate styling must only change the candidate's room state.
                rooms.append(copy.deepcopy(locked))
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
            room_seed = rng.randrange(100000)
            if services and k in FIXTURES:
                try:
                    design = design_service_room(r)
                except ValueError:
                    break
            else:
                res = generate_layout_candidates(
                    r, items, seed=room_seed, max_candidates=1, max_attempts=40
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
            **({"service_layout": True} if services else {}),
            **(
                {"presentation_detail": "bedroom-salon-v1"}
                if presentation_detail
                else {}
            ),
        )
        apply_style(home, brief.style)
        if len(rooms) != len(PROGRAM) + int(salon):
            continue
        try:
            measures = validate_home(home, passage_m=brief.passage_m, measure=measure)
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
        if measures:
            home["evidence"]["comparison"] = measures
            measures["required_dining_seats"] = brief.dining_seats
            measures["split_dining"] = brief.split_dining
        if salon:
            home["evidence"]["salon"] = {
                "dining_places": 4,
                "chair_pullout_m": 0.5,
                "basis": "A reserved dining group includes a 0.50 m withdrawal strip behind each chair row.",
                "seating": "A three-piece conversation group faces the central coffee table.",
            }
        if pairs:
            centers = {
                r["design"]["room"]["id"]: (
                    r["origin"][0] + r["design"]["room"]["width_m"] / 2,
                    r["origin"][1] + r["design"]["room"]["depth_m"] / 2,
                )
                for r in rooms
            }
            home["evidence"]["room_preferences"] = [
                dict(
                    room=a,
                    target=b,
                    relation=relation,
                    center_distance_m=round(math.dist(centers[a], centers[b]), 3),
                )
                for (a, b), relation in sorted(pairs.items())
            ]
        home["id"] = digest(home)
        if home not in candidates:
            candidates.append(home)
            if on_progress and not pairs and not brief.compare_tradeoffs:
                on_progress("Furnished candidate", home)
        if not pairs and not brief.compare_tradeoffs and len(candidates) == 2:
            break
    if not candidates:
        if salon:
            raise ValueError(
                f"Search exhausted for a connected home with a formal salon on the {brief.width:g} × {brief.depth:g} m lot. Try more space or revise the room program."
            )
        raise ValueError("Search exhausted without a connected furnished home.")
    if "quiet bedroom" in brief.priority:
        candidates.sort(key=lambda c: -c["evidence"]["bedroom_center_from_front_m"])
    if pairs or brief.compare_tradeoffs:

        def cost(candidate):
            return sum(
                row["center_distance_m"] * (1 if row["relation"] == "near" else -1)
                for row in candidate["evidence"].get("room_preferences", [])
            )

        evaluated = len(candidates)
        candidates.sort(key=cost)
        if brief.compare_tradeoffs:
            primary = candidates[0]
            alternate = choose_tradeoff(primary, candidates[1:])
            candidates = [primary, alternate] if alternate else [primary]
        else:
            candidates = candidates[:2]
        if on_progress:
            on_progress(
                "Compared room placements",
                {
                    "validated_alternatives": evaluated,
                    "returned": len(candidates),
                    "method": "Equal-weight sum of room-center distances; nearer or farther as requested.",
                },
            )
            for candidate in candidates:
                on_progress("Furnished candidate", candidate)
    return candidates


def choose_tradeoff(primary, peers):
    """Prefer a reversed route trade-off, then a measurable difference in routes."""

    def routes(home):
        return {
            (r["room"], r["target"]): r["distance_m"]
            for r in home["evidence"]["comparison"]["routes"]
        }

    baseline = routes(primary)
    winner, strongest = None, (False, 0.0)
    for other in peers:
        distances = routes(other)
        common = baseline.keys() & distances.keys()
        deltas = [distances[key] - baseline[key] for key in sorted(common)]
        # Longer study separation and shorter service/night routes are alternative
        # preferences rather than global requirements.
        gains = [
            distances[key] - baseline[key]
            if key == ("study", "living")
            else baseline[key] - distances[key]
            for key in sorted(common)
        ]
        contrast = (
            any(x >= 0.5 for x in gains) and any(x <= -0.5 for x in gains),
            max((abs(x) for x in deltas), default=0.0),
        )
        if contrast[1] >= 0.5 and contrast > strongest:
            winner, strongest = other, contrast
    # Locked shells have fixed routes, but furniture preview remains available.
    return winner
