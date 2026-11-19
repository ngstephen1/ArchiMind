"""Attach a released chair to the existing validated bedroom reservation."""

from archimind.assets.designer_concepts import (
    approved_chairs,
    approved_collection,
    resolve_chair,
    resolve_collection,
)

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
    validate_home(home)
    del home["id"]
    home["id"] = digest(home)
    if apply:
        if data["preview_id"] != home["id"]:
            raise db.Problem("Preview this concept on the current revision first.", 409)
        return db.apply(q, owner, project, base, home)
    return {"project": project, "base": base, "home": home}
