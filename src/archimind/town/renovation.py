"""Concept-level edits to shared partitions on Town's rectangular gallery shell."""

from copy import deepcopy
from math import isclose, isfinite

PREFIX = "partition-"


def shared(south, north):
    a, b = [p["design"]["room"] for p in (south, north)]
    return (
        isclose(south["origin"][1] + a["depth_m"], north["origin"][1], abs_tol=1e-6)
        and isclose(south["origin"][0], north["origin"][0], abs_tol=1e-6)
        and isclose(a["width_m"], b["width_m"], abs_tol=1e-6)
    )


def paired_openings(home):
    """Verify that every new threshold is a coincident pair on adjoining rooms."""
    pairs = {}
    for part in home["rooms"]:
        room = part["design"]["room"]
        for door in room["doors"]:
            if door["id"].startswith(PREFIX):
                pairs.setdefault(door["id"], []).append((part, door))
    for key, sides in pairs.items():
        if len(sides) != 2:
            raise ValueError("Partition opening needs two matching sides.")
        (south, a), (north, b) = sorted(sides, key=lambda item: item[0]["origin"][1])
        if (
            not shared(south, north)
            or a["wall"] != "north"
            or b["wall"] != "south"
            or any(a[k] != b[k] for k in ("width_m", "height_m", "offset_m"))
            or key
            != partition_id(
                south["design"]["room"]["id"], north["design"]["room"]["id"]
            )
        ):
            raise ValueError("Partition openings must coincide on a shared wall.")
    return pairs


def partition_id(a, b):
    return f"{PREFIX}{a}--{b}"


def edit(home, request):
    from .design import refresh_geometry_evidence

    updated = deepcopy(home)
    rooms = {p["design"]["room"]["id"]: p for p in updated["rooms"]}
    south, north = (rooms.get(request.get(k)) for k in ("south", "north"))
    if not south or not north or not shared(south, north):
        raise ValueError("Choose two rooms that share a full interior partition.")
    a, b = [p["design"]["room"] for p in (south, north)]
    delta = request.get("delta_m")
    kind = request.get("kind")
    if (
        type(delta) not in (int, float)
        or not isfinite(delta)
        or abs(delta) > 5
        or kind not in ("wall", "door", "opening")
    ):
        raise ValueError(
            "Choose a wall, door or opening and a finite partition move within 5 m."
        )
    if (
        home.get("service_layout")
        and delta
        and {a["id"], b["id"]} & {"bathroom", "kitchen-dining"}
    ):
        raise ValueError(
            "Moving a coordinated service-room boundary requires a revised service study."
        )
    if home.get("zoning") == "service-core" and {a["id"], b["id"]} == {
        "salon",
        "kitchen-dining",
    }:
        raise ValueError(
            "The service-core scheme requires its existing paired service passage."
        )
    key = partition_id(a["id"], b["id"])
    previous = next((d for d in a["doors"] if d["id"] == key), None)
    if min(a["depth_m"] + delta, b["depth_m"] - delta) < 1:
        raise ValueError("Both rooms must retain positive usable depth.")
    for decor in south.get("style", {}).get("dressing", []):
        if decor["kind"] == "art" and isclose(
            decor["y_m"] + decor["depth_m"], a["depth_m"], abs_tol=0.002
        ):
            decor["y_m"] = round(decor["y_m"] + delta, 6)
    a["depth_m"] = round(a["depth_m"] + delta, 6)
    b["depth_m"] = round(b["depth_m"] - delta, 6)
    north["origin"][1] = round(north["origin"][1] + delta, 6)
    for f in (
        north["design"]["furniture"]
        + north.get("style", {}).get("dressing", [])
        + north.get("coffee_tables", [])
    ):
        f["y_m"] = round(f["y_m"] - delta, 6)
    for d in b["doors"] + b["windows"]:
        if d["wall"] in ("east", "west"):
            d["offset_m"] = round(d["offset_m"] - delta, 6)
    for part in (south, north):
        r = part["design"]["room"]
        for f in part["design"]["furniture"] + part.get("style", {}).get(
            "dressing", []
        ):
            if f["y_m"] < -1e-6 or f["y_m"] + f["depth_m"] > r["depth_m"] + 1e-6:
                raise ValueError(
                    "The partition would cross a fixed furnishing or finish."
                )
        r["doors"] = [d for d in r["doors"] if d["id"] != key]
    width = 0.0
    if kind != "wall":
        width = request.get("width_m")
        offset = request.get("offset_m")
        if (
            any(type(v) not in (int, float) or not isfinite(v) for v in (offset, width))
            or width < 0.6
            or offset < 0
            or offset + width > a["width_m"]
        ):
            raise ValueError("The opening must fit within the selected wall.")
        height = min(
            2.10 if kind == "door" else 2.45,
            a["ceiling_height_m"],
            b["ceiling_height_m"],
        )
        for r, wall in ((a, "north"), (b, "south")):
            r["doors"].append(
                dict(
                    id=key,
                    wall=wall,
                    offset_m=float(offset),
                    width_m=float(width),
                    height_m=height,
                )
            )
    if (
        north["design"]["room"]["id"] == "study"
        and delta
        and "study_passage" in updated["evidence"]
    ):
        route = updated["evidence"]["study_passage"]["room_local_bounds_m"]
        route[1] -= delta
        route[3] -= delta
    current = next((d for d in a["doors"] if d["id"] == key), None)
    if (
        not delta
        and previous == current
        and home.get("partitions", {}).get(key, "wall") == kind
    ):
        raise ValueError("The requested partition already exists.")
    updated.setdefault("partitions", {})[key] = kind
    refresh_geometry_evidence(updated)
    ev = updated["evidence"]
    ev["room_areas_m2"] = {
        k: round(p["design"]["room"]["width_m"] * p["design"]["room"]["depth_m"], 3)
        for k, p in rooms.items()
    }
    bedroom = rooms.get("bedroom")
    if bedroom and "bedroom_center_from_front_m" in ev:
        ev["bedroom_center_from_front_m"] = round(
            bedroom["origin"][1] + bedroom["design"]["room"]["depth_m"] / 2, 2
        )
    for pref in ev.get("room_preferences", []):
        if delta and pref.get("room") in rooms and pref.get("target") in rooms:
            from math import hypot

            def center(k):
                p = rooms[k]
                r = p["design"]["room"]
                return (
                    p["origin"][0] + r["width_m"] / 2,
                    p["origin"][1] + r["depth_m"] / 2,
                )

            x, y = center(pref["room"])
            xx, yy = center(pref["target"])
            if "center_distance_m" in pref:
                pref["center_distance_m"] = round(hypot(xx - x, yy - y), 3)
    return updated, (
        f"{a['name']} {ev['room_areas_m2'][a['id']]:.2f} m² · "
        f"{b['name']} {ev['room_areas_m2'][b['id']]:.2f} m² · "
        + (
            f"{width:.2f} m {kind}, crossing checked."
            if width
            else "Solid wall; hall routes checked."
        )
    )
