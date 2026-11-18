"""The per-room ``style`` payload both viewers read (Studio scene, Town room part)."""

from archimind.assets.designer_concepts import approved_pieces
from archimind.models import RoomDesign

from .binding import bind_furniture
from .decor import place_dressing
from .models import StylePack
from .registry import load_releases


def style_payload(
    design: RoomDesign, pack: StylePack, seed: int, *, designer_ids=frozenset()
) -> dict:
    """Exactly {style_pack, bindings, dressing, skipped}; deterministic for a seed."""
    dressing = place_dressing(design, pack, seed)
    return {
        "style_pack": {"id": pack.id, "version": pack.version},
        "bindings": [
            b.model_dump(mode="json")
            for b in bind_furniture(design, pack, designer_ids=designer_ids)
        ],
        "dressing": [i.model_dump(mode="json") for i in dressing.items],
        "skipped": dressing.skipped,
    }


def asset_hashes(asset_ids) -> dict[str, tuple[str, ...]]:
    """SHA-256 of every released file behind each bound asset (unreleased ones omitted)."""
    releases = load_releases()
    pieces = {f"designer:{p.concept_id}@{p.version}": p for p in approved_pieces()}
    out = {}
    for asset_id in sorted(set(asset_ids) - {None}):
        if asset_id in pieces:
            out[asset_id] = (pieces[asset_id].sha256,)
        elif asset_id in releases:
            out[asset_id] = tuple(sorted(f.sha256 for f in releases[asset_id].files))
    return out
