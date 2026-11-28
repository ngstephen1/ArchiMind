"""Reconfigure the existing salon dining reservation for six place settings."""

import re
from copy import deepcopy

from .design import refresh_geometry_evidence


def edit(home: dict, message: str) -> tuple[dict, str]:
    if not isinstance(message, str) or not re.fullmatch(
        r"(?:please )?seat (?:six|6) (?:people )?at one table in the salon"
        r"(?: and keep the lounge seating unchanged)?[.!]?",
        message.strip(),
        re.I,
    ):
        raise ValueError(
            "Try: Seat six at one table in the salon and keep the lounge seating unchanged."
        )
    home = deepcopy(home)
    salon = next(
        (r for r in home["rooms"] if r["design"]["room"]["id"] == "salon"), None
    )
    furniture = salon["design"]["furniture"] if salon else []
    table = next((f for f in furniture if f["id"] == "salon-dining"), None)
    if not table or table["category"] != "dining" or table["rotation_deg"] != 0:
        raise ValueError("The home needs a supported salon dining reservation.")
    # Two rows of three chairs and a 0.50 m withdrawal strip behind each row.
    if table["width_m"] < 2.04 or table["depth_m"] < 2.90 or table["height_m"] < 0.84:
        raise ValueError("The six-place dining group exceeds its saved reservation.")
    if salon.get("dining_variant") == "six-place":
        raise ValueError("Six places are already set at the salon table.")
    if any(
        b["furniture_id"] == table["id"] and b.get("asset_id")
        for b in salon.get("style", {}).get("bindings", [])
        + salon.get("asset_bindings", [])
    ):
        raise ValueError("The dining reservation already has a bound furniture model.")
    salon["dining_variant"] = "six-place"
    table["name"] = "Extendable salon table with six dining chairs"
    home["evidence"].setdefault("salon", {}).update(
        dining_places=6,
        chair_pullout_m=0.50,
        tabletop_width_m=2.04,
        basis="One extended tabletop with three modeled chairs on each side. The group retains 0.50 m withdrawal space behind both chair rows.",
    )
    refresh_geometry_evidence(home)
    return (
        home,
        "Extended the salon table from 1.58 to 2.04 m and set six places at one table. Lounge seating is unchanged.",
    )
