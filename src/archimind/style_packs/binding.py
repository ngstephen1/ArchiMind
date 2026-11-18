"""Bind each furniture reservation to the first pack model that fits inside it."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from archimind.models import RoomDesign

from .models import StylePack

# Fitted kitchen and bathroom pieces stay procedural; pack surfaces style them.
PROCEDURAL_CATEGORIES = frozenset({"counter", "vanity", "bath"})
_EPS = 1e-9


class PackBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    furniture_id: str
    asset_id: str | None
    reason: Literal["pack", "designer", "procedural_fallback"]


# A model must cover this share of its reservation's footprint and height,
# so a small piece never stands in for a large one.
MIN_FILL = 0.5


def _fills(choice, item) -> bool:
    footprint = (choice.width_m * choice.depth_m) / (item.width_m * item.depth_m)
    return footprint >= MIN_FILL and choice.height_m >= MIN_FILL * item.height_m


def bind_furniture(
    design: RoomDesign, pack: StylePack, *, designer_ids=frozenset()
) -> list[PackBinding]:
    """One binding per furniture item, in furniture-ID order. Reservations in
    ``designer_ids`` keep the designer piece the user chose: no pack model."""
    bindings = []
    for item in sorted(design.furniture, key=lambda f: f.id):
        if item.id in designer_ids:
            bindings.append(
                PackBinding(furniture_id=item.id, asset_id=None, reason="designer")
            )
            continue
        choices = (
            ()
            if item.category in PROCEDURAL_CATEGORIES
            else pack.furniture.get(item.category, ())
        )
        choice = next(
            (
                c
                for c in choices
                if c.width_m <= item.width_m + _EPS
                and c.depth_m <= item.depth_m + _EPS
                and c.height_m <= item.height_m + _EPS
                and _fills(c, item)
            ),
            None,
        )
        if choice is None:
            bindings.append(
                PackBinding(
                    furniture_id=item.id, asset_id=None, reason="procedural_fallback"
                )
            )
        else:
            reason = "designer" if choice.asset_id.startswith("designer:") else "pack"
            bindings.append(
                PackBinding(
                    furniture_id=item.id, asset_id=choice.asset_id, reason=reason
                )
            )
    return bindings
