"""Move the folio table and its chair as a group and measure the study route."""

from copy import deepcopy
from re import fullmatch

from shapely.geometry import box

from .design import digest, refresh_geometry_evidence


def footprint(item):
    x, y = item["x_m"], item["y_m"]
    return box(x, y, x + item["width_m"], y + item["depth_m"])


def edit(home: dict, message: str):
    request = " ".join(message.lower().strip(" .!?").split())
    if not fullmatch(
        r"move the study (?:folio )?table and chair together to clear a "
        r"(?:90 cm|90cm|0\.9 m) passage from the door to the window-side table",
        request,
    ):
        raise ValueError(
            "Specify a 90 cm passage from the study door to the window-side table."
        )
    candidate = deepcopy(home)
    study = next(
        (p for p in candidate["rooms"] if p["design"]["room"]["id"] == "study"), None
    )
    if study is None:
        raise ValueError("A furnished study is required.")
    room = study["design"]["room"]
    items = {i["id"]: i for i in study["design"]["furniture"]}
    moving = ("library-table", "library-chair")
    # Gallery homes enter the study from the hall on an east or west wall.
    hall_doors = [d for d in room["doors"] if d["wall"] in {"east", "west"}]
    if not all(key in items for key in (*moving, "side-table")) or len(hall_doors) != 1:
        raise ValueError(
            "A unique study entrance, folio table, chair and side table are required."
        )
    door = hall_doors[0]
    west = door["wall"] == "west"
    side = footprint(items["side-table"])
    mid = door["offset_m"] + door["width_m"] / 2
    if (
        door["width_m"] < 0.90
        or not side.bounds[1] <= mid <= side.bounds[3]
        or not any(
            w["wall"] == ("east" if west else "west")
            and w["offset_m"] <= mid <= w["offset_m"] + w["width_m"]
            for w in room["windows"]
        )
    ):
        raise ValueError(
            "The doorway and window-side table do not align for a straight 90 cm route."
        )
    start, finish = (0, side.bounds[0]) if west else (room["width_m"], side.bounds[2])
    corridor = box(min(start, finish), mid - 0.45, max(start, finish), mid + 0.45)
    floor_items = [
        *items.values(),
        *(
            row
            for row in study.get("style", {}).get("dressing", [])
            if row["kind"] in {"plant", "floor_lamp", "accent"}
        ),
    ]

    def blockers():
        return [
            f["id"]
            for f in floor_items
            if footprint(f).intersection(corridor).area > 1e-8
        ]

    before = blockers()
    if not before:
        raise ValueError("The straight 90 cm passage is already clear.")
    if set(before) - set(moving):
        raise ValueError("Other fixed objects obstruct the requested study passage.")
    base = {key: items[key]["y_m"] for key in moving}
    # Test the shorter translation first. Retain a 20 mm margin to the passage.
    south = mid - 0.47 - max(base[key] + items[key]["depth_m"] for key in moving)
    north = mid + 0.47 - min(base.values())
    for dy in sorted((south, north), key=abs):
        for key in moving:
            items[key]["y_m"] = round(base[key] + dy, 4)
        if blockers():
            continue
        if any(
            footprint(items[key]).intersection(footprint(f)).area > 1e-8
            for key in moving
            for f in floor_items
            if f["id"] not in moving
        ):
            continue
        try:
            refresh_geometry_evidence(candidate)
        except ValueError:
            continue
        candidate["evidence"]["study_passage"] = {
            "from": door["id"],
            "to": "side-table",
            "width_m": 0.90,
            "length_m": round(abs(finish - start), 3),
            "before_blockers": before,
            "after_blockers": [],
            "moved": list(moving),
            "translation_y_m": round(dy, 4),
            "room_local_bounds_m": list(corridor.bounds),
        }
        candidate.pop("id", None)
        candidate["id"] = digest(candidate)
        return candidate, (
            f"Moved the folio table and chair {abs(dy):.2f} m {'north' if dy > 0 else 'south'} "
            f"together. Cleared a 90 cm wide, {abs(finish - start):.2f} m long modeled "
            "passage from the study door to the window-side table."
        )
    raise ValueError("The group cannot move far enough while retaining its clearances.")
