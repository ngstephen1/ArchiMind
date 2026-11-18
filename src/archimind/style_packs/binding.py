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


def bind_furniture(design: RoomDesign, pack: StylePack) -> list[PackBinding]:
    """One binding per furniture item, in furniture-ID order."""
    bindings = []
    for item in sorted(design.furniture, key=lambda f: f.id):
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
