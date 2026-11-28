"""Validated finish proposals persist on the selected rooms and furniture IDs."""

import re

from . import service
from .design import digest
from .furniture_edit import LOOSE, default_table

FINISHES = ("dark green", "walnut", "warm oak", "linen white", "sage", "terracotta")
MATCH = re.compile(
    r"(?:(?:make|use|apply|paint|finish|change|give) )?(?:(?:the |this |selected |room |home |all |my )*(walls?|floors?|piece|object|table|chair|surface|it) (?:in |to |a )?)?"
    r"(dark green|walnut|warm oak|linen white|sage|terracotta)"
    r"(?: (walls?|floors?|finish))?(?: throughout(?: the home)?| in this room)?[.!]?",
    re.I,
)


def change(q, owner, project, data, applying):
    base = service.project(q, owner, project)
    if not base or data.get("base") != base:
        raise service.Problem("Open the latest saved design.", 409)
    home = service.revision(q, project, base)
    scope = data.get("scope")
    message = data.get("message")
    match = MATCH.fullmatch(message.strip()) if isinstance(message, str) else None
    if not match:
        raise service.Problem("Try dark green walls, walnut floors, or apply sage.")
    first, finish, last = (value.lower() if value else "" for value in match.groups())
    if first and last and last != "finish" and first.rstrip("s") != last.rstrip("s"):
        raise service.Problem("Choose one surface.")
    surface = (first or last).rstrip("s")
    if scope not in ("object", "room", "home"):
        raise service.Problem("Choose an object, room or whole home.")
    if (
        "throughout" in message.lower()
        and scope != "home"
        or "in this room" in message.lower()
        and scope != "room"
    ):
        raise service.Problem("Choose the scope requested in the message.")
    if (
        scope == "object"
        and surface in ("wall", "floor")
        or scope != "object"
        and surface not in ("wall", "floor")
    ):
        raise service.Problem(
            "Choose walls or floors for a room or home, or a finish for the selected piece."
        )
    parts = [
        p
        for p in home["rooms"]
        if scope == "home" or p["design"]["room"]["id"] == data.get("room")
    ]
    if not parts:
        raise service.Problem("Select a room in this revision.")
    if scope == "home" and surface == "floor":
        home["hall_finish"] = finish
    for p in parts:
        overrides = p.setdefault("finish_overrides", {})
        if scope == "object":
            key = data.get("object")
            items = p["design"]["furniture"]
            suite = next((f for f in items if f["id"] == "salon-suite"), None)
            tables = p.get(
                "coffee_tables",
                [default_table(suite)] if suite and not p.get("suite_yaw_deg") else [],
            )
            if not any(f["id"] == key for f in tables) and not any(
                f["id"] == key
                and p.get("piece_edits", {}).get(key, {}).get("source", key) in LOOSE
                for f in items
            ):
                raise service.Problem(
                    "Select a loose furniture piece with an editable finish."
                )
            if any(
                b.get("furniture_id") == key and b.get("asset_id")
                for b in [
                    *p.get("asset_bindings", []),
                    *p.get("style", {}).get("bindings", []),
                ]
            ):
                raise service.Problem("This asset has a specified product finish.")
            overrides.setdefault("objects", {})[key] = finish
        else:
            overrides[surface] = finish
    old_id = home.pop("id")
    home["id"] = digest(home)
    if home["id"] == old_id:
        raise service.Problem("This finish is already applied.")
    if applying:
        if data.get("preview_id") != home["id"]:
            raise service.Problem("Recheck this finish before saving.", 409)
        return service.apply(q, owner, project, base, home)
    return {
        "home": home,
        "summary": f"{finish.title()} · {scope} · {len(parts)} room(s).",
    }
