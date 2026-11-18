"""Attach a released chair to the existing validated bedroom reservation."""

from archimind.assets.designer_concepts import approved_chairs, resolve_chair

from . import service as db
from .design import apply_style, digest, validate_home


def chair_options():
    return [
        {
            "concept_id": chair.concept_id,
            "version": chair.version,
            "sha256": chair.sha256,
            "name": chair.name,
            "variant_label": chair.variant_label,
            "width_m": chair.width_m,
            "depth_m": chair.depth_m,
            "height_m": chair.height_m,
        }
        for chair in approved_chairs()
    ]


def chair_change(q, owner, project, data, *, apply):
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
        chair = resolve_chair(**binding)
    except ValueError:
        raise db.Problem("This chair release is unavailable.", 409) from None
    home = db.revision(q, project, base)
    bedroom = next(
        (p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom"), None
    )
    items = bedroom["design"]["furniture"] if bedroom else []
    seat = next((item for item in items if item["id"] == "desk-chair"), None)
    if not seat or seat["category"] != "chair" or seat["rotation_deg"] != 0:
        raise db.Problem("This bedroom has no supported desk-chair reservation.")
    dimensions = (chair.width_m, chair.depth_m, chair.height_m)
    if any(
        value > seat[key]
        for value, key in zip(
            dimensions, ("width_m", "depth_m", "height_m"), strict=True
        )
    ):
        raise db.Problem("The native chair exceeds this bedroom's reservation.")
    if bedroom.get("designer_chair", {}).get("binding") == binding:
        raise db.Problem("This chair is already applied to the bedroom.", 409)
    bedroom["designer_chair"] = {
        "binding": binding,
        "name": chair.name,
        "dimensions_wdh_m": list(dimensions),
        "variant_label": chair.variant_label,
    }
    if home.get("style_pack"):
        # Re-dress so no pack model is bound to the chosen chair's reservation.
        apply_style(home, home["style_pack"]["id"])
    validate_home(home)
    del home["id"]
    home["id"] = digest(home)
    if apply:
        if data["preview_id"] != home["id"]:
            raise db.Problem("Preview this chair on the current revision first.", 409)
        return db.apply(q, owner, project, base, home)
    return {"project": project, "base": base, "home": home}
