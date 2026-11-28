"""Validated edits of loose Town furnishings, with canonical saved footprints."""

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat
from shapely.geometry import Point, box
from shapely.ops import unary_union

from . import designer_chair, service
from .design import refresh_geometry_evidence

LOOSE = {
    "coffee-table",
    "side-table",
    "console-table",
    "library-table",
    "library-chair",
    "reading-light",
    "towel-bench",
}
CATALOG = {
    "round": ("Round oak coffee table", "table", 0.66, 0.66, 0.40),
    "rectangular": ("Rectangular oak coffee table", "table", 1.03, 0.48, 0.38),
}


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    base: int = Field(gt=0)
    room: str
    object: str
    action: Literal["move", "rotate", "replace", "duplicate", "remove"]
    x_m: FiniteFloat | None = None
    y_m: FiniteFloat | None = None
    replacement: Literal["round", "rectangular"] | None = None
    sofa_route: bool = False
    preview_id: str | None = None


def rect(f):
    return box(f["x_m"], f["y_m"], f["x_m"] + f["width_m"], f["y_m"] + f["depth_m"])


def suite_geometry(s):
    x, y, w, d = (s[k] for k in ("x_m", "y_m", "width_m", "depth_m"))
    sofa = box(x + w / 2 - 0.99, y + d - 0.8, x + w / 2 + 0.99, y + d)
    chairs = [
        box(x + 0.02, y, x + 0.80, y + 0.68),
        box(x + w - 0.80, y, x + w - 0.02, y + 0.68),
    ]
    return sofa, chairs


def default_table(s):
    return dict(
        id="salon-coffee-table",
        name="Marble coffee table",
        category="table",
        x_m=s["x_m"] + (s["width_m"] - 1.03) / 2,
        y_m=s["y_m"] + 0.83,
        width_m=1.03,
        depth_m=0.48,
        height_m=0.38,
        rotation_deg=0,
    )


def check_saved_sofa_route(part):
    route = part.get("sofa_route")
    if not route:
        return
    room = part["design"]["room"]
    items = part["design"]["furniture"]
    suite = next((f for f in items if f["id"] == route["to"]), None)
    door = next((d for d in room["doors"] if d["id"] == route["from"]), None)
    if (
        not suite
        or part.get("suite_yaw_deg")
        or not door
        or door["wall"] not in {"east", "west"}
    ):
        raise ValueError("Cannot verify the saved 90 cm door-to-sofa route.")
    shell = box(0, 0, room["width_m"], room["depth_m"])
    sofa, chairs = suite_geometry(suite)
    obstacles = [sofa, *chairs]
    obstacles.extend(rect(f) for f in items if f is not suite)
    obstacles.extend(rect(f) for f in part.get("coffee_tables", [default_table(suite)]))
    obstacles.extend(
        rect(f)
        for f in part.get("style", {}).get("dressing", [])
        if f["kind"] in {"plant", "accent", "floor_lamp"}
    )
    radius = 0.45
    start = Point(
        radius if door["wall"] == "west" else room["width_m"] - radius,
        door["offset_m"] + door["width_m"] / 2,
    )
    free = shell.buffer(-radius).difference(
        unary_union(obstacles).buffer(radius, quad_segs=12)
    )
    region = next(
        (g for g in getattr(free, "geoms", [free]) if g.buffer(1e-7).covers(start)),
        None,
    )
    # A visitor can approach within one body radius of the sofa footprint.
    if (
        door["width_m"] < 0.9
        or region is None
        or region.distance(sofa) > radius + 0.002
    ):
        raise ValueError(
            "The model cannot verify a 90 cm door-to-sofa route for this arrangement."
        )


def checked_furniture(part):
    """Include edited freestanding coffee tables in ordinary geometry validation."""
    items = part["design"]["furniture"]
    check_saved_sofa_route(part)
    if not part.get("coffee_tables"):
        return items
    suite = next((f for f in items if f["id"] == "salon-suite"), None)
    if not suite or part.get("suite_yaw_deg"):
        raise ValueError(
            "The edited coffee group needs its original salon reservation."
        )
    envelope = rect(suite)
    sofa, chairs = suite_geometry(suite)
    blockers = [sofa, *chairs]
    extra = []
    room = part["design"]["room"]
    for table in part["coffee_tables"]:
        shape = rect(table)
        if not box(0, 0, room["width_m"], room["depth_m"]).covers(shape) or any(
            shape.intersection(b).area > 1e-8 for b in blockers
        ):
            raise ValueError(
                "Coffee table overlaps another furnishing or the room boundary."
            )
        if not envelope.covers(shape):
            if envelope.intersection(shape).area > 1e-8:
                raise ValueError(
                    "Place the entire table inside or outside the lounge reservation."
                )
            extra.append(table)
        blockers.append(shape)
    return [*items, *extra]


def edit(home, change):
    h = deepcopy(home)
    part = next(
        (p for p in h["rooms"] if p["design"]["room"]["id"] == change.room), None
    )
    if not part:
        raise ValueError("Select a room in the current revision.")
    room = part["design"]["room"]
    items = part["design"]["furniture"]
    suite = next((f for f in items if f["id"] == "salon-suite"), None)
    coffee = part.get(
        "coffee_tables",
        [default_table(suite)] if suite and not part.get("suite_yaw_deg") else [],
    )
    primary = next((f for f in items if f["id"] == change.object), None)
    nested = next((f for f in coffee if f["id"] == change.object), None)
    styles = part.setdefault("piece_edits", {})
    target = primary or nested
    if not target or (
        primary
        and styles.get(change.object, {}).get("source", change.object) not in LOOSE
    ):
        raise ValueError(
            "Select an editable loose piece; fitted furniture and reserved suites are protected."
        )
    bindings = part.get("asset_bindings", []) + part.get("style", {}).get(
        "bindings", []
    )
    if any(b["furniture_id"] == change.object and b.get("asset_id") for b in bindings):
        raise ValueError("This piece has a protected asset binding.")
    if (change.action == "replace") != bool(change.replacement):
        raise ValueError("Choose a table model only for a replacement.")
    if (change.action in ("move", "duplicate")) != (
        change.x_m is not None and change.y_m is not None
    ) or ((change.x_m is None) != (change.y_m is None)):
        raise ValueError(
            "Specify the southwest x and y coordinates only for moves and duplicates."
        )
    group = coffee if nested else items
    if nested:
        part["coffee_tables"] = coffee
    ident = target["id"]
    if change.action == "duplicate":
        ids = {f["id"] for f in items + coffee}
        i = 2
        while f"{ident}-copy-{i}" in ids:
            i += 1
        target = deepcopy(target)
        target["id"] = f"{ident}-copy-{i}"
        group.append(target)
        overrides = part.get("finish_overrides", {}).get("objects", {})
        if ident in overrides:
            overrides[target["id"]] = overrides[ident]
        styles[target["id"]] = dict(
            styles.get(ident, {}), source=styles.get(ident, {}).get("source", ident)
        )
    if change.action in ("move", "duplicate"):
        target.update(x_m=change.x_m, y_m=change.y_m)
    elif change.action in ("replace", "rotate"):
        cx = target["x_m"] + target["width_m"] / 2
        cy = target["y_m"] + target["depth_m"] / 2
        meta = styles.setdefault(ident, {"source": ident})
        if change.action == "rotate":
            target["depth_m"], target["width_m"] = target["width_m"], target["depth_m"]
            meta["yaw"] = (meta.get("yaw", 0) + 90) % 360
        else:
            name, cat, w, d, height = CATALOG[change.replacement]
            target.update(
                name=name, category=cat, width_m=w, depth_m=d, height_m=height
            )
            meta.update(model=change.replacement, yaw=0)
        target.update(x_m=cx - target["width_m"] / 2, y_m=cy - target["depth_m"] / 2)
    elif change.action == "remove":
        group.remove(target)
        styles.pop(ident, None)
        part.get("finish_overrides", {}).get("objects", {}).pop(ident, None)
        for rows in (
            part.get("asset_bindings", []),
            part.get("style", {}).get("bindings", []),
        ):
            rows[:] = [b for b in rows if b["furniture_id"] != ident]
    shell = box(0, 0, room["width_m"], room["depth_m"])
    decor = [
        rect(a)
        for a in part.get("style", {}).get("dressing", [])
        if a["kind"] in ("plant", "accent", "floor_lamp")
    ]
    obstacles = [rect(f) for f in items if f is not suite] + decor
    if suite and not part.get("suite_yaw_deg"):
        sofa, chairs = suite_geometry(suite)
        obstacles.extend([sofa, *chairs])
    else:
        if suite:
            obstacles.append(rect(suite))
    for f in coffee:
        footprint = rect(f)
        if not shell.covers(footprint) or any(
            footprint.intersection(o).area > 1e-8 for o in obstacles
        ):
            raise ValueError(
                "Coffee table conflicts with the room boundary or a saved furnishing."
            )
        obstacles.append(footprint)
    if change.action != "remove" and any(
        rect(target).intersection(o).area > 1e-8 for o in decor
    ):
        raise ValueError("This position overlaps an existing floor accessory.")
    passage = h.get("evidence", {}).get("study_passage")
    if (
        passage
        and change.room == "study"
        and ident == passage.get("to")
        and change.action != "duplicate"
    ):
        # Moving or removing the measured destination invalidates the old corridor.
        h["evidence"].pop("study_passage")
        passage = None
    if (
        passage
        and change.room == "study"
        and change.action != "remove"
        and rect(target).intersection(box(*passage["room_local_bounds_m"])).area > 1e-8
    ):
        raise ValueError("This edit obstructs the saved study passage.")
    summary = f"{change.action.capitalize()} · {target['name']} ({target['id']})"
    if change.sofa_route:
        if not suite or part.get("suite_yaw_deg") or not room["doors"]:
            raise ValueError(
                "The 90 cm check needs the supported salon sofa and its entrance."
            )
        part["sofa_route"] = {
            "from": room["doors"][0]["id"],
            "to": suite["id"],
            "width_m": 0.90,
        }
        summary += " · 90 cm modeled door-to-sofa route verified"
    refresh_geometry_evidence(h)
    return h, summary


def request(q, owner, p, data, apply):
    spec = Change.model_validate(data)
    if service.project(q, owner, p) != spec.base:
        raise service.Problem("Reopen the latest revision.", 409)
    try:
        home, summary = edit(service.revision(q, p, spec.base), spec)
    except ValueError as exc:
        raise service.Problem(str(exc)) from exc
    result = designer_chair.finish_preview(
        q, owner, p, spec.base, home, spec.model_dump(), apply
    )
    return {**result, "summary": summary}
