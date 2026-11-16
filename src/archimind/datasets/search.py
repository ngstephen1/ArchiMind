"""P3: deterministic reference search over a verified pack.

Four pure functions make up the facade:

- ``load_reference_pack(root, audience=...)``: the server picks ``root``. Users and
  models never supply a path or URL.
- ``reference_query_from_chat(draft)``: builds a query only from facts in a typed
  chat draft that are backed by quotes.
- ``search_references(query, pack=...)``: bounded, ranked scene and asset hits.
- ``prepare_reference_preview(hit, pack=...)``: footprint facts for one hit. It
  refuses hits from another snapshot.

The module makes no model calls, has no embeddings and uses no network, database or
filesystem paths in its output. A hit is a reference only. It is not a product,
not a planning approval and not proof that a layout fits. Explanations are built
from checked facts (categories, dimensions, tier, openings) and never quote source
text, so descriptions embedded in a pack cannot inject instructions.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, StrictBool, StrictInt, model_validator

from archimind.datasets.canonical import digest, file_sha256
from archimind.datasets.contracts import (
    Frozen,
    Identifier,
    RoomExtent,
    SceneReference,
    Split,
    Tier,
)
from archimind.datasets.pack import LoadedPack, load_pack

SEARCH_SCHEMA_VERSION = "1.0.0"
INDEX_VERSION = "1.0.0"
DEFAULT_HITS, MAX_HITS = 3, 10
MAX_KEYWORDS = 16

# Pack categories (the real packs use the MIDI super-categories, e.g. "bed").
Category = Annotated[str, Field(pattern=r"^[a-z][a-z_]{1,31}$")]
Keyword = Annotated[str, Field(pattern=r"^[a-z0-9]{2,24}$")]

# Chat furniture functions -> (pack category, required finer-category token).
# Evidence (P2b pack): 3D-FUTURE files Desk under Table and armchair under Sofa.
CHAT_FUNCTIONS: dict[str, tuple[str, str | None]] = {
    "bed": ("bed", None),
    "desk": ("table", "desk"),
    "wardrobe": ("cabinet_shelf_desk", "wardrobe"),
    "nightstand": ("cabinet_shelf_desk", "nightstand"),
    "bookcase": ("cabinet_shelf_desk", "bookcase"),
    "chair": ("chair", None),
    "armchair": ("sofa", "armchair"),
}
_STOPWORDS = frozenset(
    "a an and the of for with in on to my our some two one three".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


def _singular(token: str) -> str:
    """Naive plural folding, applied to queries and the index alike."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokens(text: str) -> frozenset[str]:
    """Lower-case alphanumeric tokens of 2-24 characters, singular, no stopwords."""
    return frozenset(
        _singular(t)
        for t in _TOKEN.findall(text.casefold())
        if 2 <= len(t) <= 24 and t not in _STOPWORDS
    )


# --------------------------------------------------------------- records


class CategoryRequest(Frozen):
    category: Category
    term: Keyword | None = None
    count: StrictInt = Field(ge=1, le=8)


class ReferenceQuery(Frozen):
    schema_version: Literal["1.0.0"] = SEARCH_SCHEMA_VERSION
    room: RoomExtent | None = None
    categories: tuple[CategoryRequest, ...] = Field(default=(), max_length=8)
    keywords: tuple[Keyword, ...] = Field(default=(), max_length=MAX_KEYWORDS)
    tiers: tuple[Tier, ...] = ("canonical", "reference_only")
    max_scene_hits: StrictInt = Field(default=DEFAULT_HITS, ge=1, le=MAX_HITS)
    max_asset_hits: StrictInt = Field(default=DEFAULT_HITS, ge=0, le=MAX_HITS)
    notes: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def _canonical_order(self) -> Self:
        keys = [(c.category, c.term or "") for c in self.categories]
        if keys != sorted(keys) or len(set(keys)) != len(keys):
            raise ValueError("Category requests must be unique and sorted")
        if list(self.keywords) != sorted(set(self.keywords)):
            raise ValueError("Keywords must be unique and sorted")
        if not self.tiers or list(self.tiers) != sorted(set(self.tiers)):
            raise ValueError("Tiers must be non-empty, unique and sorted")
        return self

    @property
    def is_empty(self) -> bool:
        return self.room is None and not self.categories and not self.keywords


class CategoryMatch(Frozen):
    category: Category
    term: Keyword | None
    requested: StrictInt = Field(ge=1)
    found: StrictInt = Field(ge=0)


class CheckSummary(Frozen):
    name: Identifier
    status: Literal["PASS", "FAIL", "NOT_VERIFIABLE"]


class SceneHit(Frozen):
    rank: StrictInt = Field(ge=1)
    reference_id: Identifier
    snapshot_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    source: Literal["ssr_3dfront", "midi_3dfront"]
    split: Split
    tier: Tier
    room: RoomExtent
    openings: Literal["known", "unknown"]
    admitted_objects: StrictInt = Field(ge=1)
    category_matches: tuple[CategoryMatch, ...]
    coverage: FiniteFloat = Field(ge=0, le=1)
    size_distance: FiniteFloat | None = Field(default=None, ge=0)
    room_axes: Literal["as_recorded", "swapped"] | None = None
    matched_keywords: tuple[Keyword, ...]
    unmatched_keywords: tuple[Keyword, ...]
    aliases: tuple[Identifier, ...]
    alias_splits: tuple[Split, ...]
    checks: tuple[CheckSummary, ...]
    reasons: tuple[str, ...]


class AssetHit(Frozen):
    rank: StrictInt = Field(ge=1)
    asset_id: Identifier
    snapshot_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    category: Category | None
    matched_keywords: tuple[Keyword, ...]


class ReferenceSearchResult(Frozen):
    schema_version: Literal["1.0.0"] = SEARCH_SCHEMA_VERSION
    status: Literal["matches", "empty", "unavailable"]
    reason: Identifier | None = None
    pack_id: Identifier | None = None
    audience: Literal["local", "public"] | None = None
    snapshot_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    index_version: Literal["1.0.0"] = INDEX_VERSION
    query_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    eligible_scenes: StrictInt = Field(default=0, ge=0)
    candidates: StrictInt = Field(default=0, ge=0)
    scene_hits: tuple[SceneHit, ...] = ()
    asset_hits: tuple[AssetHit, ...] = ()
    asset_status: Literal["matches", "empty", "no_assets_in_pack", "not_requested"] = (
        "not_requested"
    )
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if (self.status == "matches") != bool(self.scene_hits or self.asset_hits):
            raise ValueError("Only 'matches' results carry hits")
        if self.status != "matches" and self.reason is None:
            raise ValueError("Empty and unavailable results need a reason")
        return self


class PreviewObject(Frozen):
    category: Category
    x_m: FiniteFloat
    y_m: FiniteFloat
    width_m: FiniteFloat
    depth_m: FiniteFloat
    height_m: FiniteFloat
    yaw_quarter_turns: Literal[0, 1, 2, 3]


class ReferencePreview(Frozen):
    schema_version: Literal["1.0.0"] = SEARCH_SCHEMA_VERSION
    status: Literal["ready", "unavailable"]
    reason: Identifier | None = None
    reference_id: Identifier | None = None
    snapshot_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    tier: Tier | None = None
    display: Literal["canonical_footprints", "oriented_footprints"] | None = None
    room: RoomExtent | None = None
    objects: tuple[PreviewObject, ...] = ()
    excluded_objects: StrictInt = Field(default=0, ge=0)
    openings: Literal["known", "unknown"] | None = None
    checks: tuple[CheckSummary, ...] = ()
    asset_previews: StrictBool = False
    asset_id: Identifier | None = None
    asset_bounds_m: tuple[FiniteFloat, FiniteFloat, FiniteFloat] | None = None
    asset_triangles: StrictInt | None = None
    asset_glb_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    asset_attribution: str | None = None
    labels: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if (self.status == "ready") != (self.reason is None):
            raise ValueError("Only unavailable previews carry a reason")
        return self


# --------------------------------------------------------------- index


@dataclass(frozen=True)
class _Entry:
    scene: SceneReference
    objects: tuple[tuple[str, frozenset[str]], ...]  # admitted (category, tokens)
    vocabulary: frozenset[str]
    aliases: tuple[SceneReference, ...]


def _fingerprint(scene: SceneReference) -> str:
    """Content identity without the record identity, for verified exact duplicates."""
    data = scene.model_dump(
        exclude={"reference_id", "source_scene_id", "source_room_id", "split"}
    )
    objects = [dict(obj) for obj in data["objects"]]
    for obj in objects:
        obj.pop("source_object_id")
    data["objects"] = sorted(objects, key=digest)
    return digest(data)


def build_index(scenes) -> tuple[_Entry, ...]:
    """Entries in reference-id order; exact content duplicates fold into aliases.

    Only byte-identical content (room, objects, checks, versions, source) folds.
    Scenes that merely look alike stay separate. The lowest id is the primary
    and every alias keeps its own split, so evaluation leakage stays visible.
    """
    groups: dict[str, list[SceneReference]] = defaultdict(list)
    for scene in scenes:
        groups[_fingerprint(scene)].append(scene)
    entries = []
    for members in groups.values():
        primary, *aliases = sorted(members, key=lambda s: s.reference_id)
        objects = tuple(
            (o.category, tokens(o.raw_category))
            for o in primary.objects
            if o.exclusion is None
        )
        vocabulary = frozenset().union(
            *(t | {c} for c, t in objects), *(set(c.split("_")) for c, _ in objects)
        )
        entries.append(_Entry(primary, objects, vocabulary, tuple(aliases)))
    return tuple(sorted(entries, key=lambda e: e.scene.reference_id))


@dataclass(frozen=True)
class ReferencePack:
    """A loaded pack plus its index. ``status`` is ``ready`` or ``unavailable``."""

    status: Literal["ready", "unavailable"]
    reason: str | None = None
    audience: str | None = None
    pack_id: str | None = None
    snapshot_id: str | None = None
    entries: tuple[_Entry, ...] = field(default=(), repr=False)
    by_category: dict = field(default_factory=dict, repr=False)
    by_token: dict = field(default_factory=dict, repr=False)
    assets: tuple = field(default=(), repr=False)
    loaded: LoadedPack | None = field(default=None, repr=False)
    root: Path | None = field(default=None, repr=False)  # server-side only


def index_pack(loaded: LoadedPack, root: Path | None = None) -> ReferencePack:
    entries = build_index(loaded.scenes)
    by_category: dict[str, set[int]] = defaultdict(set)
    by_token: dict[str, set[int]] = defaultdict(set)
    for i, entry in enumerate(entries):
        for category, _ in entry.objects:
            by_category[category].add(i)
        for token in entry.vocabulary:
            by_token[token].add(i)
    return ReferencePack(
        status="ready",
        audience=loaded.manifest.audience,
        pack_id=loaded.manifest.pack_id,
        snapshot_id=loaded.manifest.snapshot_id,
        entries=entries,
        by_category={k: frozenset(v) for k, v in by_category.items()},
        by_token={k: frozenset(v) for k, v in by_token.items()},
        assets=_asset_entries(loaded),
        loaded=loaded,
        root=None if root is None else Path(root),
    )


def _asset_entries(loaded: LoadedPack) -> tuple:
    """(asset, category or None, vocabulary) by asset id.

    The category comes only from scene objects with the same jid, and only when
    they agree on one category. Nothing is inferred from names or images.
    """
    by_jid: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for scene in loaded.scenes:
        for o in scene.objects:
            if o.exclusion is None and o.jid is not None:
                by_jid[o.jid].add((o.category, o.raw_category))
    out = []
    for asset in sorted(loaded.assets, key=lambda a: a.asset_id):
        seen = by_jid.get(asset.source_jid, set())
        categories = {c for c, _ in seen}
        category = next(iter(categories)) if len(categories) == 1 else None
        vocabulary = frozenset().union(*(tokens(r) | {c} for c, r in seen))
        out.append((asset, category, vocabulary))
    return tuple(out)


def load_reference_pack(
    root: Path | None, *, audience: str = "public"
) -> ReferencePack:
    """Verify and index the pack at a server-configured ``root``. Never raises.

    A public audience needs a public pack, so a local research pack is
    ``unavailable`` with reason ``pack_not_public``.
    """
    if audience not in ("public", "local"):
        return ReferencePack("unavailable", "invalid_audience")
    status = load_pack(root, audience=audience)
    if status.status != "ready":
        return ReferencePack("unavailable", status.reason, audience)
    try:
        return index_pack(status.pack, Path(root))
    except (ValueError, TypeError):
        return ReferencePack("unavailable", "index_failed", audience)


# --------------------------------------------------------------- queries


def _quoted(quote, turns) -> bool:
    return (
        quote is not None
        and bool(quote.text.strip())
        and any(
            t.id == quote.turn_id
            and t.role == "user"
            and quote.text.casefold() in t.content.casefold()
            for t in turns
        )
    )


def reference_query_from_chat(
    draft, *, max_scene_hits: int = DEFAULT_HITS
) -> ReferenceQuery:
    """Build a query from a ready ``CatalogChatDraft``.

    Room W/D/H come from the draft's validated room. Furniture counts on intents
    and keyword tokens come only from user quotes that are present in the turns.
    Anything dropped is recorded in ``notes``. Free text is never copied.
    """
    room = draft.room()
    turns = draft.turns
    counts: dict[tuple[str, str | None], int] = defaultdict(int)
    words: set[str] = set()
    notes: set[str] = set()
    for item in draft.extraction.furniture:
        if not _quoted(item.source, turns):
            notes.add("unquoted_furniture_skipped")
            continue
        mapped = CHAT_FUNCTIONS.get(item.function)
        if mapped is None:
            notes.add("unsupported_furniture_skipped")
            continue
        counts[mapped] = min(8, counts[mapped] + (item.quantity or 1))
        words |= tokens(item.source.text)
        if item.variant is not None and _quoted(item.variant.source, turns):
            words |= tokens(item.variant.value)
    if len(words) > MAX_KEYWORDS:
        notes.add("keywords_truncated")
    return ReferenceQuery(
        room=RoomExtent(
            width_m=room.width_m, depth_m=room.depth_m, height_m=room.ceiling_height_m
        ),
        categories=tuple(
            CategoryRequest(category=c, term=t, count=n)
            for (c, t), n in sorted(
                counts.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")
            )
        ),
        keywords=tuple(sorted(words)[:MAX_KEYWORDS]),
        max_scene_hits=max_scene_hits,
        notes=tuple(sorted(notes)),
    )


# --------------------------------------------------------------- search

LIMITATIONS = (
    "References are examples from public research datasets, not products or approvals.",
    "A match does not prove fit, intent or product availability.",
    "Where openings are unknown, door and circulation checks are unverified.",
)


def _plan(requests) -> list[tuple[int, str, str | None, int]]:
    """(position, category, term, count) with specific terms matched first."""
    plan = [(i, r.category, r.term, r.count) for i, r in enumerate(requests)]
    return sorted(plan, key=lambda x: (x[2] is None, x[1], x[2] or ""))


def _assign(entry: _Entry, plan, n_requests: int) -> list[int]:
    """Found counts per request; each admitted object satisfies at most one."""
    used: set[int] = set()
    found = [0] * n_requests
    for position, want_category, term, count in plan:
        n = 0
        for i, (category, words) in enumerate(entry.objects):
            if n == count:
                break
            if i in used or category != want_category:
                continue
            if term is not None and term not in words:
                continue
            used.add(i)
            n += 1
        found[position] = n
    return found


def _size(room: RoomExtent, want: RoomExtent) -> tuple[float, str]:
    def rel(a, b):
        return abs(a - b) / b

    h = rel(room.height_m, want.height_m)
    straight = (
        rel(room.width_m, want.width_m) + rel(room.depth_m, want.depth_m) + h
    ) / 3
    swapped = (
        rel(room.depth_m, want.width_m) + rel(room.width_m, want.depth_m) + h
    ) / 3
    if swapped < straight:
        return round(swapped, 6), "swapped"
    return round(straight, 6), "as_recorded"


def _reasons(scene, matches, size, axes, keywords) -> tuple[str, ...]:
    out = []
    for m in matches:
        label = m.term or m.category.replace("_", "/")
        out.append(f"Has {m.found} of {m.requested} requested {label}.")
    r = scene.room
    if size is not None:
        note = " (width and depth swapped)" if axes == "swapped" else ""
        out.append(
            f"Room {r.width_m:.2f} x {r.depth_m:.2f} x {r.height_m:.2f} m; "
            f"relative size difference {size:.1%}{note}."
        )
    if keywords:
        out.append("Matching terms: " + ", ".join(keywords) + ".")
    if scene.tier == "canonical":
        out.append(
            "Canonical tier: every object admitted at zero yaw (not a layout approval)."
        )
    else:
        out.append("Reference only: oriented footprints, not a validated layout.")
    if scene.openings == "unknown":
        out.append("Doors and windows are not recorded by the source.")
    return tuple(out)


def _asset_hits(query: ReferenceQuery, pack: ReferencePack) -> tuple:
    """Assets: compatible category desc, keyword overlap desc, asset id asc."""
    wanted_categories = {c.category for c in query.categories}
    wanted = set(query.keywords)
    scored = []
    for asset, category, vocabulary in pack.assets:
        compatible = category is not None and category in wanted_categories
        words = tuple(sorted(wanted & vocabulary))
        if compatible or words:
            scored.append(
                ((not compatible, -len(words), asset.asset_id), asset, category, words)
            )
    scored.sort(key=lambda s: s[0])
    return tuple(
        AssetHit(
            rank=rank,
            asset_id=asset.asset_id,
            snapshot_id=pack.snapshot_id,
            category=category,
            matched_keywords=words,
        )
        for rank, (_, asset, category, words) in enumerate(
            scored[: query.max_asset_hits], start=1
        )
    )


def search_references(
    query: ReferenceQuery, *, pack: ReferencePack
) -> ReferenceSearchResult:
    """Rank scenes: coverage desc, size distance asc, keyword overlap desc, id asc."""
    qdigest = digest(query.model_dump())
    if pack.status != "ready":
        return ReferenceSearchResult(
            status="unavailable",
            reason=pack.reason or "unavailable",
            query_digest=qdigest,
        )
    base = dict(
        pack_id=pack.pack_id,
        audience=pack.audience,
        snapshot_id=pack.snapshot_id,
        query_digest=qdigest,
        limitations=LIMITATIONS,
    )
    eligible = [i for i, e in enumerate(pack.entries) if e.scene.tier in query.tiers]
    asset_status = (
        "not_requested"
        if query.max_asset_hits == 0
        else ("no_assets_in_pack" if not pack.assets else "empty")
    )
    if query.is_empty:
        return ReferenceSearchResult(
            status="empty",
            reason="empty_query",
            eligible_scenes=len(eligible),
            asset_status=asset_status,
            **base,
        )
    wanted = set(query.keywords)
    if query.categories:
        pool = frozenset().union(
            *(pack.by_category.get(c.category, frozenset()) for c in query.categories)
        )
    elif wanted:
        pool = frozenset().union(*(pack.by_token.get(w, frozenset()) for w in wanted))
    else:
        pool = frozenset(eligible)
    candidates = sorted(set(eligible) & pool)
    plan = _plan(query.categories)
    total = sum(c.count for c in query.categories)
    asset_hits = _asset_hits(query, pack) if query.max_asset_hits else ()
    if asset_hits:
        asset_status = "matches"
    scored = []
    for i in candidates:
        entry = pack.entries[i]
        found = _assign(entry, plan, len(query.categories))
        coverage = round(sum(found) / total, 6) if total else 0.0
        if query.categories and coverage == 0:
            continue
        hit_words = tuple(sorted(wanted & entry.vocabulary))
        if not query.categories and wanted and not hit_words:
            continue
        size, axes = (
            _size(entry.scene.room, query.room)
            if query.room is not None
            else (None, None)
        )
        key = (
            -coverage,
            size if size is not None else 0.0,
            -len(hit_words),
            entry.scene.reference_id,
        )
        scored.append((key, entry, found, coverage, size, axes, hit_words))
    scored.sort(key=lambda s: s[0])
    hits = []
    for rank, (_, entry, found, coverage, size, axes, hit_words) in enumerate(
        scored[: query.max_scene_hits], start=1
    ):
        scene = entry.scene
        matches = tuple(
            CategoryMatch(category=r.category, term=r.term, requested=r.count, found=n)
            for r, n in zip(query.categories, found, strict=True)
        )
        hits.append(
            SceneHit(
                rank=rank,
                reference_id=scene.reference_id,
                snapshot_id=pack.snapshot_id,
                source=scene.source,
                split=scene.split,
                tier=scene.tier,
                room=scene.room,
                openings=scene.openings,
                admitted_objects=len(entry.objects),
                category_matches=matches,
                coverage=coverage,
                size_distance=size,
                room_axes=axes,
                matched_keywords=hit_words,
                unmatched_keywords=tuple(sorted(wanted - set(hit_words))),
                aliases=tuple(a.reference_id for a in entry.aliases),
                alias_splits=tuple(a.split for a in entry.aliases),
                checks=tuple(
                    CheckSummary(name=c.name, status=c.status) for c in scene.checks
                ),
                reasons=_reasons(scene, matches, size, axes, hit_words),
            )
        )
    return ReferenceSearchResult(
        status="matches" if hits or asset_hits else "empty",
        reason=None if hits or asset_hits else "no_matches",
        eligible_scenes=len(eligible),
        candidates=len(candidates),
        scene_hits=tuple(hits),
        asset_hits=asset_hits,
        asset_status=asset_status,
        **base,
    )


# --------------------------------------------------------------- preview


def _asset_preview(hit: AssetHit, pack: ReferencePack) -> ReferencePreview:
    """Asset facts after re-hashing its GLB; a changed or missing file is unavailable."""
    asset = next((a for a, _, _ in pack.assets if a.asset_id == hit.asset_id), None)
    if asset is None:
        return ReferencePreview(status="unavailable", reason="reference_not_found")
    if pack.root is None:
        return ReferencePreview(status="unavailable", reason="asset_not_rechecked")
    path = pack.root / asset.glb.path
    try:
        current = file_sha256(path) if path.is_file() else None
    except OSError:
        current = None
    if current is None:
        return ReferencePreview(status="unavailable", reason="asset_missing")
    if current != asset.glb.sha256:
        return ReferencePreview(status="unavailable", reason="asset_digest_changed")
    return ReferencePreview(
        status="ready",
        snapshot_id=pack.snapshot_id,
        asset_previews=True,
        asset_id=asset.asset_id,
        asset_bounds_m=asset.bounds_m,
        asset_triangles=asset.triangles,
        asset_glb_sha256=asset.glb.sha256,
        asset_attribution=asset.attribution,
        labels=(
            "Visual reference mesh from a research dataset; not a purchasable product.",
            "Shown at its recorded scale; never resized to fit.",
        ),
    )


def prepare_reference_preview(
    hit: SceneHit | AssetHit, *, pack: ReferencePack
) -> ReferencePreview:
    """Preview facts for ``hit``; stale snapshots and missing records are unavailable."""
    if pack.status != "ready":
        return ReferencePreview(
            status="unavailable", reason=pack.reason or "unavailable"
        )
    if hit.snapshot_id != pack.snapshot_id:
        return ReferencePreview(status="unavailable", reason="stale_snapshot")
    if isinstance(hit, AssetHit):
        return _asset_preview(hit, pack)
    entry = next(
        (e for e in pack.entries if e.scene.reference_id == hit.reference_id), None
    )
    if entry is None:
        return ReferencePreview(status="unavailable", reason="reference_not_found")
    scene = entry.scene
    objects = sorted(
        (
            PreviewObject(
                category=o.category,
                x_m=o.footprint.x_m,
                y_m=o.footprint.y_m,
                width_m=o.footprint.width_m,
                depth_m=o.footprint.depth_m,
                height_m=o.footprint.height_m,
                yaw_quarter_turns=o.footprint.yaw_quarter_turns,
            )
            for o in scene.objects
            if o.exclusion is None
        ),
        key=lambda p: (p.category, p.x_m, p.y_m, p.width_m, p.depth_m),
    )
    canonical = scene.tier == "canonical"
    excluded = sum(1 for o in scene.objects if o.exclusion is not None)
    labels = [
        "Reference example from a research dataset; not a product or approval.",
        "Axis-aligned footprints at zero yaw; see checks for what was verified."
        if canonical
        else "Oriented footprints only; not a validated layout.",
        "Doors and windows unknown: door and circulation checks not verified."
        if scene.openings == "unknown"
        else "Doors and windows recorded by the source.",
        "No reference meshes are approved for preview.",
    ]
    if excluded:
        noun = "object" if excluded == 1 else "objects"
        labels.append(f"{excluded} source {noun} excluded and not shown.")
    return ReferencePreview(
        status="ready",
        reference_id=scene.reference_id,
        snapshot_id=pack.snapshot_id,
        tier=scene.tier,
        display="canonical_footprints" if canonical else "oriented_footprints",
        room=scene.room,
        objects=tuple(objects),
        excluded_objects=excluded,
        openings=scene.openings,
        checks=tuple(CheckSummary(name=c.name, status=c.status) for c in scene.checks),
        labels=tuple(labels),
    )
