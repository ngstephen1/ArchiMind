"""Attach a released chair to the existing validated bedroom reservation."""

from archimind.assets.designer_concepts import (
    approved_chairs,
    approved_collection,
    resolve_chair,
    resolve_collection,
)
from archimind.geometry import validate_accessibility
from archimind.models import Furniture, RoomDesign

from . import service as db
from .design import apply_style, digest, validate_home


def chair_options(*, collection=False):
    return [
        {
            "concept_id": chair.concept_id,
            "version": chair.version,
            "sha256": chair.sha256,
            "name": chair.name,
            "variant_label": "" if collection else chair.variant_label,
            "width_m": chair.width_m,
            "depth_m": chair.depth_m,
            "height_m": chair.height_m,
        }
        for chair in (approved_collection() if collection else approved_chairs())
    ]


def chair_change(q, owner, project, data, *, apply, collection=False):
    base = data.get("base")
    head = db.project(q, owner, project)
    expected_keys = {"base", "binding", "preview_id"} if apply else {"base", "binding"}
    binding = data.get("binding")
    if (
        set(data) != expected_keys
        or type(base) is not int
        or base < 1
        or not isinstance(binding, dict)
        or set(binding) != {"concept_id", "version", "sha256"}
        or not all(isinstance(v, str) for v in binding.values())
    ):
        raise db.Problem("Choose a released chair for a saved revision.")
    if base != head:
        raise db.Problem("A newer revision exists. Reopen the current design.", 409)
    try:
        chair = (resolve_collection if collection else resolve_chair)(**binding)
    except ValueError:
        raise db.Problem("This furniture release is unavailable.", 409) from None
    home = db.revision(q, project, base)
    bedroom = next(
        (p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom"), None
    )
    items = bedroom["design"]["furniture"] if bedroom else []
    slot, category = (
        {
            "upholstered-linen-bed": ("queen-bed", "bed"),
            "oak-bedside-lamp": ("bedside-lamp", "table"),
        }[chair.concept_id]
        if collection
        else ("desk-chair", "chair")
    )
    seat = next((item for item in items if item["id"] == slot), None)
    if not seat or seat["category"] != category or seat["rotation_deg"] != 0:
        raise db.Problem("This bedroom has no matching furniture reservation.")
    dimensions = (chair.width_m, chair.depth_m, chair.height_m)
    if any(
        value > seat[key]
        for value, key in zip(
            dimensions, ("width_m", "depth_m", "height_m"), strict=True
        )
    ):
        raise db.Problem("The native concept exceeds this bedroom's reservation.")
    previous = (
        bedroom.get("designer_collection", {}).get(slot, {})
        if collection
        else bedroom.get("designer_chair", {})
    )
    if previous.get("binding") == binding:
        raise db.Problem("This concept is already applied to the bedroom.", 409)
    record = {
        "binding": binding,
        "name": chair.name,
        "dimensions_wdh_m": list(dimensions),
        "variant_label": "" if collection else chair.variant_label,
    }
    if collection:
        bedroom.setdefault("designer_collection", {})[slot] = record
    else:
        bedroom["designer_chair"] = record
    if home.get("style_pack"):
        # Re-dress so no pack model is bound to the chosen chair's reservation.
        apply_style(home, home["style_pack"]["id"])
    return finish_preview(q, owner, project, base, home, data, apply)


def chair_pullout(q, owner, project, data, *, apply):
    """Preview a measured pull away from the writing desk on the current home."""
    head = db.project(q, owner, project)
    base = data.get("base")
    keys = {"base", "preview_id"} if apply else {"base"}
    if set(data) != keys or type(base) is not int or base < 1:
        raise db.Problem("Choose a saved bedroom revision to move its chair.")
    if base != head:
        raise db.Problem("A newer revision exists. Reopen the current design.", 409)
    home = db.revision(q, project, base)
    bedroom = next(
        (p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom"), None
    )
    items = {f["id"]: f for f in bedroom["design"]["furniture"]} if bedroom else {}
    chair, desk = items.get("desk-chair"), items.get("belaya")
    if not chair or not desk or chair["rotation_deg"] or desk["rotation_deg"]:
        raise db.Problem(
            "This edit requires the bedroom writing chair and its unrotated desk."
        )
    overlaps_width = max(chair["x_m"], desk["x_m"]) < min(
        chair["x_m"] + chair["width_m"], desk["x_m"] + desk["width_m"]
    )
    start = chair["y_m"]
    if not overlaps_width:
        raise db.Problem("The chair must face the writing desk to preview this move.")
    if start >= desk["y_m"] + desk["depth_m"]:
        end = start + 0.30
    elif start + chair["depth_m"] <= desk["y_m"]:
        end = start - 0.30
    else:
        raise db.Problem("The chair must be on one side of the writing desk.")
    chair["y_m"] = end
    # Use the floor objects already saved with this room, including vintage packs.
    # Rugs and wall/ceiling treatments do not reserve walking space.
    floor_decor = [
        Furniture(
            id="decor:" + d["id"],
            name=d["kind"],
            category="decor",
            **{k: d[k] for k in ("x_m", "y_m", "width_m", "depth_m", "height_m")},
        )
        for d in bedroom.get("style", {}).get("dressing", [])
        if d["kind"] in {"plant", "floor_lamp", "accent"}
    ]
    if floor_decor:
        room = RoomDesign.model_validate(bedroom["design"])
        dressed = room.model_copy(update={"furniture": [*room.furniture, *floor_decor]})
        if validate_accessibility(dressed).status != "passed":
            raise db.Problem(
                "The saved floor furnishings leave insufficient room for this chair move."
            )
    home["evidence"]["chair_move_m"] = {
        "from_x": chair["x_m"],
        "to_x": chair["x_m"],
        "from_y": start,
        "to_y": end,
    }
    try:
        return finish_preview(q, owner, project, base, home, data, apply)
    except ValueError as exc:
        raise db.Problem(
            "There is insufficient validated space for a 30 cm chair move."
        ) from exc


def finish_preview(q, owner, project, base, home, data, apply):
    validate_home(home)
    del home["id"]
    home["id"] = digest(home)
    if apply:
        if data["preview_id"] != home["id"]:
            raise db.Problem("Preview this edit on the current revision first.", 409)
        return db.apply(q, owner, project, base, home)
    return {"project": project, "base": base, "home": home}
