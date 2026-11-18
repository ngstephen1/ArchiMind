"""Load the five packaged style packs and the asset release records they use."""

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from archimind.assets.designer_concepts import approved_pieces

from .models import STYLE_IDS, AssetRelease, StyleId, StylePack

DEFAULT_STYLE: StyleId = "scandinavian"
LEGACY_PALETTE_TO_STYLE: dict[str, StyleId] = {
    "oak": "scandinavian",
    "sage": "japandi",
    "terracotta": "mid_century",
}
# Readers that only know palettes keep working on new homes.
STYLE_TO_LEGACY_PALETTE: dict[str, str] = {
    "scandinavian": "oak",
    "modern_classic": "oak",
    "industrial_loft": "oak",
    "japandi": "sage",
    "mid_century": "terracotta",
}
STYLE_CLARIFICATION = "Choose one style: modern classic, industrial loft, Scandinavian, Japandi or mid-century."
_TIER_ORDER = {"low": ("low", "both", "high"), "high": ("high", "both", "low")}


def _packs_dir():
    return files("archimind").joinpath("_viewer_assets", "packs")


@cache
def load_pack(style_id: str) -> StylePack:
    if style_id not in STYLE_IDS:
        raise ValueError(f"Unknown style pack: {style_id}")
    raw = json.loads(_packs_dir().joinpath(f"{style_id}.json").read_bytes())
    pack = StylePack.model_validate(raw)
    if pack.id != style_id:
        raise ValueError(f"Style pack file {style_id}.json declares {pack.id}")
    return pack


def all_packs() -> tuple[StylePack, ...]:
    return tuple(load_pack(style_id) for style_id in STYLE_IDS)


def load_releases() -> dict[str, AssetRelease]:
    rows = json.loads(_packs_dir().joinpath("releases.json").read_bytes())
    releases = {}
    for row in rows:
        release = AssetRelease.model_validate(row)
        if release.asset_id in releases:
            raise ValueError(f"Duplicate asset release: {release.asset_id}")
        releases[release.asset_id] = release
    return releases


def _designer_released(asset_id: str) -> bool:
    match = re.fullmatch(r"designer:([a-z0-9-]+)@([0-9.]+)", asset_id)
    return bool(match) and any(
        (p.concept_id, p.version) == match.groups() for p in approved_pieces()
    )


def _tier_bytes(releases, ids, tier) -> int:
    seen, total = set(), 0
    for asset_id in ids:
        release = releases.get(asset_id)
        if not release:
            continue
        for role in dict.fromkeys(f.role for f in release.files):
            for t in _TIER_ORDER[tier]:
                chosen = next(
                    (f for f in release.files if f.role == role and f.tier == t), None
                )
                if chosen:
                    if chosen.sha256 not in seen:
                        seen.add(chosen.sha256)
                        total += chosen.bytes
                    break
    return total


@dataclass(frozen=True)
class PackStatus:
    released: bool
    missing: tuple[str, ...]
    high_bytes: int
    low_bytes: int


def pack_status(
    pack: StylePack, releases: dict[str, AssetRelease] | None = None
) -> PackStatus:
    """A pack is released only when every asset it references is released."""
    releases = load_releases() if releases is None else releases
    ids = pack.asset_ids()
    missing = tuple(
        a
        for a in ids
        if a not in releases
        and not (a.startswith("designer:") and _designer_released(a))
    )
    return PackStatus(
        released=not missing,
        missing=missing,
        high_bytes=_tier_bytes(releases, ids, "high"),
        low_bytes=_tier_bytes(releases, ids, "low"),
    )


def _normalise(text: str) -> str:
    return " ".join(re.sub(r"[^a-z -]+", " ", text.lower()).replace("-", " ").split())


@cache
def _alias_table() -> dict[str, str]:
    table = {}
    for pack in all_packs():
        for phrase in (*pack.aliases, pack.name, pack.id.replace("_", " ")):
            key = _normalise(phrase)
            if table.get(key, pack.id) != pack.id:
                raise ValueError(f"Style alias {phrase!r} names two packs")
            table[key] = pack.id
    return table


def resolve_style_phrase(text: str) -> StyleId | None:
    """The style an exact phrase names ('make it' / 'style' / 'finishes' trimmed)."""
    return _alias_table().get(_normalise(text))


def styles_mentioned(text: str) -> set[str]:
    """Every style whose alias appears as whole words anywhere in ``text``."""
    words = f" {_normalise(text)} "
    return {style for alias, style in _alias_table().items() if f" {alias} " in words}
