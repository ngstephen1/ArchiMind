"""P5/P6: orientation-free layout habits from reference bedrooms.

App furniture has no "front" and the generator places only unrotated items, so only
habits that need no orientation are measured:

* ``bed_edge``: which footprint edge of a bed touches a wall (a short edge, only a
  long edge, or none). Square beds have no short edge and are excluded and counted.
* ``desk_wall`` / ``storage_wall``: wall contact (low priority, for completeness).
* ``chair_desk_gap``: gap from a chair to the nearest table, in rooms with a table.
* ``floor_coverage``: floor-standing footprint area / room area, by room-area tercile.
* ``nightstand_bed_gap``: recorded only. The app has no nightstand, so it is marked
  not usable and never scored.

Statistics are fit on the ``train`` split only, with exact-duplicate aliases folded
(see :func:`archimind.datasets.search.build_index`). The same measuring code runs
on pack scenes and on app designs, so the two cannot drift apart. Outputs are
aggregates only: no identifiers, paths or source text.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from random import Random

from archimind.datasets.canonical import canonical_bytes

HABITS_SCHEMA_VERSION = "1.0.0"
MIN_N = 100
TOLERANCES_M = (0.05, 0.10, 0.15)
STOP_FALLING = 0.02  # the free-standing rate "stops falling" below 2 points
OUTSIDE_LIMIT_M = 0.15  # deeper than this through a wall: excluded, counted
SQUARE_RATIO = 0.02  # |w - d| / max(w, d) at or below this: no short edge (~10% of real beds)
BOOTSTRAP_RESAMPLES = 500
BOOTSTRAP_SEED = 0
GAP_BINS = (("lt_0.15", 0.15), ("0.15_0.40", 0.40), ("0.40_0.80", 0.80), ("ge_0.80", math.inf))
COVERAGE_BINS = (
    ("lt_0.10", 0.10),
    ("0.10_0.20", 0.20),
    ("0.20_0.30", 0.30),
    ("0.30_0.40", 0.40),
    ("0.40_0.50", 0.50),
    ("0.50_0.60", 0.60),
    ("ge_0.60", math.inf),
)
# floor_coverage is recorded with weight 0: for a fixed furniture set it does not
# change with placement, and app rooms hold fewer items than reference rooms, so it
# would only add a constant that makes real rooms look better than any layout.
WEIGHTS = {
    "bed_edge": 0.6,
    "chair_desk_gap": 0.2,
    "desk_wall": 0.1,
    "floor_coverage": 0.0,
    "storage_wall": 0.1,
}
NOT_USABLE = {"nightstand_bed_gap": "not usable: no nightstand in the app"}

# Pack category -> (group, required raw-category tokens or None for any).
PACK_GROUPS: dict[str, tuple[tuple[str, frozenset[str] | None], ...]] = {
    "bed": (("bed", None),),
    "table": (("desk", frozenset({"desk"})),),
    "cabinet_shelf_desk": (
        ("nightstand", frozenset({"nightstand"})),
        ("storage", frozenset({"wardrobe", "shelf", "bookcase"})),
    ),
    "chair": (("chair", None),),
}
APP_GROUPS = {
    "bed": "bed",
    "desk": "desk",
    "table": "desk",
    "storage": "storage",
    "wardrobe": "storage",
    "chair": "chair",
}
IGNORED = frozenset({"lighting"})  # ceiling-mounted: no floor footprint


def pack_group(category: str, raw_category: str) -> str | None:
    from archimind.datasets.search import tokens

    words = tokens(raw_category)
    for group, required in PACK_GROUPS.get(category, ()):
        if required is None or words & required:
            return group
    return None


def app_group(category: str) -> str | None:
    return APP_GROUPS.get(category.casefold())


@dataclass(frozen=True)
class Rect:
    """An axis-aligned footprint in room coordinates (lower-left corner)."""

    group: str | None
    x: float
    y: float
    w: float
    d: float
    table: bool = False  # any table, for the chair habit

    @property
    def area(self) -> float:
        return self.w * self.d


def wall_gaps(r: Rect, width: float, depth: float) -> tuple[float, float, float, float]:
    """West, east, south, north gaps. Negative means past the wall."""
    return (r.x, width - (r.x + r.w), r.y, depth - (r.y + r.d))


def is_outside(r: Rect, width: float, depth: float) -> bool:
    return min(wall_gaps(r, width, depth)) < -OUTSIDE_LIMIT_M


def on_wall(r: Rect, width: float, depth: float, tol: float) -> bool:
    return min(wall_gaps(r, width, depth)) <= tol


def bed_edge(r: Rect, width: float, depth: float, tol: float) -> str:
    if abs(r.w - r.d) / max(r.w, r.d) <= SQUARE_RATIO:
        return "square"
    west, east, south, north = (g <= tol for g in wall_gaps(r, width, depth))
    # Long axis along X: the short edges are the west/east sides.
    short, long_ = ((west or east), (south or north)) if r.w > r.d else (
        (south or north),
        (west or east),
    )
    if short:
        return "short_edge"
    return "long_edge_only" if long_ else "free_standing"


def rect_gap(a: Rect, b: Rect) -> float:
    dx = max(b.x - (a.x + a.w), a.x - (b.x + b.w), 0.0)
    dy = max(b.y - (a.y + a.d), a.y - (b.y + b.d), 0.0)
    return math.hypot(dx, dy)


def _bin(value: float, bins) -> str:
    return next(label for label, upper in bins if value < upper)


# ------------------------------------------------------------- measuring


@dataclass(frozen=True)
class RoomObs:
    """Every habit outcome observed in one room."""

    outcomes: dict  # habit -> list of (outcome label, value or None, item key)
    area: float
    coverage: float
    outside: int
    square_beds: int


def observe_room(rects: list[Rect], width: float, depth: float, tol: float) -> RoomObs:
    """The single measuring routine for pack scenes and app designs alike."""
    inside = [r for r in rects if not is_outside(r, width, depth)]
    outcomes: dict[str, list] = defaultdict(list)
    square = 0
    for i, r in enumerate(inside):
        if r.group == "bed":
            edge = bed_edge(r, width, depth, tol)
            if edge == "square":
                square += 1
            else:
                outcomes["bed_edge"].append((edge, None, i))
        elif r.group in ("desk", "storage"):
            label = "wall" if on_wall(r, width, depth, tol) else "free"
            outcomes[f"{r.group}_wall"].append((label, None, i))
    tables = [r for r in inside if r.table]
    beds = [r for r in inside if r.group == "bed"]
    for i, r in enumerate(inside):
        if r.group == "chair" and tables:
            gap = min(rect_gap(r, t) for t in tables)
            outcomes["chair_desk_gap"].append((_bin(gap, GAP_BINS), gap, i))
        if r.group == "nightstand" and beds:
            gap = min(rect_gap(r, b) for b in beds)
            outcomes["nightstand_bed_gap"].append((_bin(gap, GAP_BINS), gap, i))
    area = width * depth
    coverage = sum(r.area for r in inside) / area
    return RoomObs(dict(outcomes), area, coverage, len(rects) - len(inside), square)


def scene_rects(scene) -> list[Rect]:
    """Floor-standing admitted objects of a SceneReference (any yaw)."""
    out = []
    for o in scene.objects:
        if o.exclusion is not None or o.category in IGNORED:
            continue
        f = o.footprint
        out.append(
            Rect(
                pack_group(o.category, o.raw_category),
                f.x_m,
                f.y_m,
                f.width_m,
                f.depth_m,
                table=o.category == "table",
            )
        )
    return out


def select_split(scenes: Iterable, split: str = "train") -> list:
    """Keep rows of one split, reading nothing but ``split`` from the others."""
    if split not in ("train", "val", "test"):
        raise ValueError("split must be train, val or test")
    return [s for s in scenes if s.split == split]


def fold_aliases(scenes) -> tuple[list, int]:
    from archimind.datasets.search import build_index

    entries = build_index(scenes)
    return [e.scene for e in entries], sum(len(e.aliases) for e in entries)


# ------------------------------------------------------------- statistics


def _quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[round(p * (len(ordered) - 1))]


def _quantiles(values: list[float]) -> dict:
    if not values:
        return {}
    return {f"p{int(p * 100):02d}": round(_quantile(values, p), 6) for p in (0.1, 0.25, 0.5, 0.75, 0.9)}


def _rates(per_room: list[list[str]], labels, rng: Random) -> dict:
    """Rates per outcome with a room-level bootstrap 95% interval."""
    counts = [Counter(r) for r in per_room]
    total = Counter()
    for c in counts:
        total.update(c)
    n = sum(total.values())
    out = {}
    if not n:
        return {label: {"count": 0, "rate": 0.0, "ci95": [0.0, 0.0]} for label in labels}
    samples = {label: [] for label in labels}
    for _ in range(BOOTSTRAP_RESAMPLES):
        picked = rng.choices(counts, k=len(counts))
        acc = Counter()
        for c in picked:
            acc.update(c)
        m = sum(acc.values()) or 1
        for label in labels:
            samples[label].append(acc[label] / m)
    for label in labels:
        s = samples[label]
        out[label] = {
            "count": total[label],
            "rate": round(total[label] / n, 6),
            "ci95": [round(_quantile(s, 0.025), 6), round(_quantile(s, 0.975), 6)],
        }
    return out


def _habit(per_room: list[list[tuple]], labels, rng: Random) -> dict:
    rooms = [[o[0] for o in r] for r in per_room if r]
    n = sum(len(r) for r in rooms)
    values = [o[1] for r in per_room for o in r if o[1] is not None]
    entry = {
        "status": "ok" if n >= MIN_N else "insufficient",
        "n": n,
        "rooms": len(rooms),
        "outcomes": _rates(rooms, labels, rng),
    }
    if values:
        entry["quantiles_m"] = _quantiles(values)
    return entry


LABELS = {
    "bed_edge": ("short_edge", "long_edge_only", "free_standing"),
    "desk_wall": ("wall", "free"),
    "storage_wall": ("wall", "free"),
    "chair_desk_gap": tuple(label for label, _ in GAP_BINS),
    "nightstand_bed_gap": tuple(label for label, _ in GAP_BINS),
}
COVERAGE_LABELS = tuple(label for label, _ in COVERAGE_BINS)


def tercile(area: float, edges) -> str:
    return "t1" if area <= edges[0] else "t2" if area <= edges[1] else "t3"


def _scene_dims(scene) -> tuple[float, float]:
    return scene.room.width_m, scene.room.depth_m


def compute_habits(
    scenes: Iterable, *, pack_id: str, snapshot_id: str, split: str = "train"
) -> dict:
    """``habits.json`` content from one split's scenes. Deterministic in input order."""
    scenes = list(scenes)
    if any(s.split != split for s in scenes) or split != "train":
        raise ValueError("habits are fit on the train split only")
    scenes, folded = fold_aliases(scenes)  # sorted by reference_id
    rects = [scene_rects(s) for s in scenes]
    dims = [_scene_dims(s) for s in scenes]

    calibration = {}
    for tol in TOLERANCES_M:
        obs = [observe_room(r, *d, tol) for r, d in zip(rects, dims)]
        edges = Counter(o[0] for ob in obs for o in ob.outcomes.get("bed_edge", ()))
        n = sum(edges.values())
        calibration[f"{tol:.2f}"] = {
            "n": n,
            "free_standing_rate": round(edges["free_standing"] / n, 6) if n else 0.0,
            "long_edge_only_rate": round(edges["long_edge_only"] / n, 6) if n else 0.0,
        }
    rates = [calibration[f"{t:.2f}"]["free_standing_rate"] for t in TOLERANCES_M]
    chosen = TOLERANCES_M[-1]
    for i in range(len(TOLERANCES_M) - 1):
        if rates[i] - rates[i + 1] < STOP_FALLING:
            chosen = TOLERANCES_M[i]
            break

    obs = [observe_room(r, *d, chosen) for r, d in zip(rects, dims)]
    rng = Random(BOOTSTRAP_SEED)
    habits = {}
    for name, labels in LABELS.items():
        habits[name] = _habit([o.outcomes.get(name, []) for o in obs], labels, rng)
        habits[name]["usable"] = name not in NOT_USABLE
        if name in NOT_USABLE:
            habits[name]["note"] = NOT_USABLE[name]

    areas = [o.area for o in obs]
    edges = (
        [round(_quantile(areas, 1 / 3), 6), round(_quantile(areas, 2 / 3), 6)]
        if areas
        else [0.0, 0.0]
    )
    by_tercile = {}
    for t in ("t1", "t2", "t3"):
        members = [o for o in obs if tercile(o.area, edges) == t]
        per_room = [[(_bin(o.coverage, COVERAGE_BINS), o.coverage, 0)] for o in members]
        by_tercile[t] = _habit(per_room, COVERAGE_LABELS, rng)
    n_cov = sum(v["n"] for v in by_tercile.values())
    habits["floor_coverage"] = {
        "status": "ok"
        if all(v["status"] == "ok" for v in by_tercile.values())
        else "insufficient",
        "n": n_cov,
        "usable": True,
        "tercile_edges_m2": edges,
        "by_tercile": by_tercile,
    }

    return {
        "schema_version": HABITS_SCHEMA_VERSION,
        "pack_id": pack_id,
        "snapshot_id": snapshot_id,
        "split": split,
        "min_n": MIN_N,
        "tolerance_m": chosen,
        "tolerance_calibration": calibration,
        "tolerance_rule": (
            "smallest band where the bed free-standing rate falls by less than "
            f"{STOP_FALLING:.2f} at the next band"
        ),
        "outside_limit_m": OUTSIDE_LIMIT_M,
        "square_ratio": SQUARE_RATIO,
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "unit": "room"},
        "category_map": {
            "pack": {
                c: {g: sorted(req) if req else "*" for g, req in groups}
                for c, groups in PACK_GROUPS.items()
            },
            "app": dict(APP_GROUPS),
            "ignored": sorted(IGNORED),
        },
        "weights": dict(WEIGHTS),
        "counts": {
            "rooms": len(scenes),
            "alias_scenes_folded": folded,
            "objects_outside_room": sum(o.outside for o in obs),
            "square_beds": sum(o.square_beds for o in obs),
        },
        "habits": habits,
    }


def habits_bytes(habits: dict) -> bytes:
    return canonical_bytes(habits) + b"\n"


def leak_free_train(all_scenes) -> tuple[list, int]:
    """Train rows minus any alias group that also has val/test members.

    This guard reads only content fingerprints of held-out rows, never their
    statistics, so a held-out room cannot reach habits through a duplicate.
    """
    from archimind.datasets.search import build_index

    dropped = set()
    groups = 0
    for entry in build_index(all_scenes):
        members = (entry.scene, *entry.aliases)
        if len({m.split for m in members}) > 1:
            groups += 1
            dropped.update(m.reference_id for m in members)
    train = [s for s in select_split(all_scenes) if s.reference_id not in dropped]
    return train, groups
