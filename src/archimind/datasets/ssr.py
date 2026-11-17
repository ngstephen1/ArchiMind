"""SSR-3DFRONT: pinned conventions, room/object classification and the P1 probe.

Conventions, each proven from ReSpace source code (GradientSpaces/respace at
b1a4b32b, ``src/eval.py``) and the pinned dataset card, not assumed:

* Y-up meters; ``bounds_bottom``/``bounds_top`` are room polygons centered on the
  origin with the floor at ``y = 0``.
* ``size`` is the FULL extent ``[x, y, z]`` (``get_xz_bbox_from_obj`` halves it).
* ``pos`` is the BOTTOM-CENTER pivot: x/z centered, ``y`` is the object's base
  (``obj_y_start = pos[1]``, ``obj_y_end = pos[1] + size[1]``).
* ``rot`` is an ``[x, y, z, w]`` quaternion (``get_y_angle_from_xyzw_quaternion``).
* ``splits`` mixes room-type and combined splits, e.g. ``["bedroom_train",
  "all_val"]`` inside the *val* parquet file. Only the room-type split is used here;
  the parquet file name is NOT the split, or evaluation data would leak.

The dataset card states ReSpace applied augmentation (rotation, perturbation,
boundary shifting); the probe therefore reports duplicate and near-duplicate
identities instead of assuming every row is an independent room.
"""

import math
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from archimind.datasets.canonical import digest
from archimind.datasets.geometry import Y_UP_TO_Z_UP, Convention, GeometryError
from archimind.datasets.geometry import object_box as _object_box

SSR_CONVENTION = Convention(
    name="ssr-3dfront-respace-b1a4b32b",
    basis=Y_UP_TO_Z_UP,
    quaternion_order="xyzw",
    pivot="bottom_center",
    size_semantics="full_extent",
)
COORD_TOLERANCE_M = 1e-6
FLOOR_CONTACT_TOLERANCE_M = 0.01
PROBE_VERSION = "1.1.0"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
MAX_OBJECTS = 64


@dataclass(frozen=True)
class RoomFrame:
    width_m: float
    depth_m: float
    height_m: float
    origin: tuple[float, float, float]  # source point that becomes canonical (0,0,0)


def classify_room(bounds_bottom, bounds_top) -> tuple[RoomFrame | None, str | None]:
    """Return the canonical frame of an axis-aligned rectangular room, or a reason."""
    try:
        bottom = [tuple(float(c) for c in p) for p in bounds_bottom]
        top = [tuple(float(c) for c in p) for p in bounds_top]
    except (TypeError, ValueError):
        return None, "malformed_record"
    if not bottom or any(len(p) != 3 for p in (*bottom, *top)):
        return None, "malformed_record"
    if not all(math.isfinite(c) for p in (*bottom, *top) for c in p):
        return None, "malformed_record"
    floor = {round(p[1] / COORD_TOLERANCE_M) for p in bottom}
    ceiling = {round(p[1] / COORD_TOLERANCE_M) for p in top}
    if len(floor) != 1 or len(ceiling) != 1:
        return None, "non_planar_floor_or_ceiling"
    if sorted((p[0], p[2]) for p in bottom) != sorted((p[0], p[2]) for p in top):
        return None, "non_planar_floor_or_ceiling"
    if len(bottom) != 4:
        return None, "irregular_room"
    xs = sorted({round(p[0] / COORD_TOLERANCE_M) for p in bottom})
    zs = sorted({round(p[2] / COORD_TOLERANCE_M) for p in bottom})
    corners = {
        (round(p[0] / COORD_TOLERANCE_M), round(p[2] / COORD_TOLERANCE_M))
        for p in bottom
    }
    if len(xs) != 2 or len(zs) != 2 or corners != {(x, z) for x in xs for z in zs}:
        return None, "irregular_room"
    min_x = min(p[0] for p in bottom)
    max_x = max(p[0] for p in bottom)
    min_z = min(p[2] for p in bottom)
    max_z = max(p[2] for p in bottom)
    floor_y = bottom[0][1]
    height = top[0][1] - floor_y
    if max_x - min_x <= 0 or max_z - min_z <= 0 or height <= 0:
        return None, "invalid_dimensions"
    return (
        RoomFrame(
            width_m=max_x - min_x,
            depth_m=max_z - min_z,
            height_m=height,
            # canonical (x, y, z) = (X - minX, maxZ - Z, Y - floorY)
            origin=(min_x, floor_y, max_z),
        ),
        None,
    )


def object_box(frame: RoomFrame, obj: dict):
    """Canonical box for one SSR object; raises GeometryError with a reason code."""
    try:
        size = tuple(float(c) for c in obj["size"])
        pos = tuple(float(c) for c in obj["pos"])
        rot = tuple(float(c) for c in obj["rot"])
    except (KeyError, TypeError, ValueError):
        raise GeometryError("malformed_record") from None
    if len(size) != 3 or len(pos) != 3 or len(rot) != 4:
        raise GeometryError("malformed_record")
    return _object_box(
        SSR_CONVENTION, size=size, position=pos, rotation=rot, origin=frame.origin
    )


def room_key(file_id: str, room_id: str) -> str:
    """3D-FRONT identity ``<house uuid>/<room id>``, shared with MIDI-3D room IDs.

    SSR ``file_id`` is ``<house uuid>-<uuid>``; its first 36 characters are the
    3D-FRONT house UUID (verified: 4,080 SSR bedrooms match MIDI room IDs exactly).
    """
    house = file_id[:36]
    if len(file_id) < 36 or not _UUID.fullmatch(house) or not room_id:
        raise ValueError("Unrecognized SSR identity")
    return f"{house}/{room_id}"


def room_type_split(splits, room_type: str = "bedroom") -> str | None:
    """``bedroom_train`` -> ``train``. ``None`` when the row is not that room type."""
    found = {
        s.split("_", 1)[1]
        for s in (splits or [])
        if isinstance(s, str) and s.startswith(room_type + "_")
    }
    if not found:
        return None
    if len(found) > 1:
        return "conflict"
    value = found.pop()
    return value if value in ("train", "val", "test") else "unknown"


def _overlap(a, b) -> bool:
    eps = COORD_TOLERANCE_M
    return (
        a.x_m + eps < b.x_m + b.width_m
        and b.x_m + eps < a.x_m + a.width_m
        and a.y_m + eps < b.y_m + b.depth_m
        and b.y_m + eps < a.y_m + a.depth_m
    )


def _vertical_overlap(a, b) -> bool:
    return (
        a.bottom_z_m + COORD_TOLERANCE_M < b.bottom_z_m + b.height_m
        and b.bottom_z_m + COORD_TOLERANCE_M < a.bottom_z_m + a.height_m
    )


@dataclass(frozen=True)
class RowProfile:
    """Geometry facts about one bedroom row. No descriptions are retained."""

    file_id: str
    room_id: str
    split: str
    room_reason: str | None
    object_count: int
    turns: tuple[int | None, ...]  # per object; None when rejected
    object_reasons: tuple[str, ...]
    outside: int
    floating: int
    footprint_overlaps: int
    solid_overlaps: int
    jids: tuple[str, ...]
    content_digest: str
    dimensions: tuple[float, float, float] | None
    max_protrusion_m: float = 0.0  # furthest an admitted box extends past a wall

    @property
    def tier(self) -> str:
        if self.room_reason is not None:
            return f"excluded:{self.room_reason}"
        if self.object_count == 0 or self.object_count > MAX_OBJECTS:
            return "excluded:invalid_dimensions"
        if self.object_reasons or self.outside or self.solid_overlaps:
            admitted = self.object_count - len(self.object_reasons)
            return "reference_only" if admitted > 0 else "excluded:no_admitted_object"
        if all(t == 0 for t in self.turns):
            return "canonical"
        return "reference_only"


def profile_row(row: dict, room_type: str = "bedroom") -> RowProfile | None:
    """Profile one parquet row; ``None`` when it is not of ``room_type``."""
    split = room_type_split(row.get("splits"), room_type)
    if split is None:
        return None
    scene = row.get("scene") or {}
    objects = scene.get("objects") or []
    geometry = {
        "bounds_bottom": scene.get("bounds_bottom"),
        "bounds_top": scene.get("bounds_top"),
        "objects": [
            {k: o.get(k) for k in ("jid", "size", "pos", "rot")} for o in objects
        ],
    }
    try:
        content = digest(geometry)
    except ValueError:
        content = "malformed"
    frame, room_reason = classify_room(
        scene.get("bounds_bottom") or [], scene.get("bounds_top") or []
    )
    turns: list[int | None] = []
    reasons: list[str] = []
    boxes = []
    outside = floating = 0
    protrusion = 0.0
    if frame is not None:
        for obj in objects:
            try:
                box = object_box(frame, obj)
            except GeometryError as error:
                turns.append(None)
                reasons.append(str(error))
                continue
            turns.append(box.quarter_turns)
            boxes.append(box)
            eps = COORD_TOLERANCE_M
            protrusion = max(
                protrusion,
                -box.x_m,
                -box.y_m,
                box.x_m + box.width_m - frame.width_m,
                box.y_m + box.depth_m - frame.depth_m,
            )
            if (
                box.x_m < -eps
                or box.y_m < -eps
                or box.x_m + box.width_m > frame.width_m + eps
                or box.y_m + box.depth_m > frame.depth_m + eps
                or box.bottom_z_m + box.height_m > frame.height_m + eps
            ):
                outside += 1
            if abs(box.bottom_z_m) > FLOOR_CONTACT_TOLERANCE_M:
                floating += 1
    footprint = solid = 0
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if _overlap(a, b):
                footprint += 1
                if _vertical_overlap(a, b):
                    solid += 1
    return RowProfile(
        file_id=str(row.get("file_id")),
        room_id=str(scene.get("room_id")),
        split=split,
        room_reason=room_reason,
        object_count=len(objects),
        turns=tuple(turns),
        object_reasons=tuple(reasons),
        outside=outside,
        floating=floating,
        footprint_overlaps=footprint,
        solid_overlaps=solid,
        jids=tuple(str(o.get("jid")) for o in objects if o.get("jid")),
        content_digest=content,
        dimensions=(frame.width_m, frame.depth_m, frame.height_m) if frame else None,
        max_protrusion_m=protrusion,
    )


def iter_parquet_rows(path: Path, *, max_rows: int = 200_000) -> Iterator[dict]:
    """Stream rows in bounded batches (pyarrow is imported lazily)."""
    import pyarrow.parquet as pq

    handle = pq.ParquetFile(path)
    if handle.metadata.num_rows > max_rows:
        raise ValueError("Parquet file exceeds the row limit")
    columns = [
        c
        for c in ("file_id", "room_type", "splits", "scene")
        if c in handle.schema_arrow.names
    ]
    for batch in handle.iter_batches(batch_size=512, columns=columns):
        yield from batch.to_pylist()


def _histogram(values: Iterable[float], edges: tuple[float, ...]) -> dict[str, int]:
    counts = Counter()
    for v in values:
        label = next((f"<{e}" for e in edges if v < e), f">={edges[-1]}")
        counts[label] += 1
    return dict(sorted(counts.items()))


def probe(profiles: Iterable[RowProfile]) -> dict:
    """Aggregate yield and identity statistics; deterministic for the same rows."""
    rows = sorted(profiles, key=lambda p: (p.file_id, p.content_digest))
    tiers = Counter(p.tier for p in rows)
    by_split = Counter((p.split, p.tier) for p in rows)
    file_ids = Counter(p.file_id for p in rows)
    digests = Counter(p.content_digest for p in rows)
    room_ids = Counter(p.room_id for p in rows)
    turn_profile = Counter(
        "all_zero"
        if all(t == 0 for t in p.turns)
        else "all_quarter"
        if all(t is not None for t in p.turns)
        else "has_rejected"
        for p in rows
        if p.room_reason is None and p.turns
    )
    object_reasons = Counter(r for p in rows for r in p.object_reasons)
    jids = {j for p in rows for j in p.jids}
    splits_by_digest: dict[str, set[str]] = {}
    for p in rows:
        splits_by_digest.setdefault(p.content_digest, set()).add(p.split)
    rectangular = [p for p in rows if p.room_reason is None]
    eligible = [p for p in rows if p.tier in ("canonical", "reference_only")]
    return {
        "probe_version": PROBE_VERSION,
        "convention": SSR_CONVENTION.name,
        "convention_digest": SSR_CONVENTION.version_digest,
        "bedroom_rows": len(rows),
        "tiers": dict(sorted(tiers.items())),
        "tiers_by_split": {f"{s}|{t}": n for (s, t), n in sorted(by_split.items())},
        "rotation_profile_of_rectangular_rooms": dict(sorted(turn_profile.items())),
        "object_rejections": dict(sorted(object_reasons.items())),
        "objects_outside_room_rows": sum(1 for p in rows if p.outside),
        "objects_floating_rows": sum(1 for p in rows if p.floating),
        "rows_with_footprint_overlap": sum(1 for p in rows if p.footprint_overlaps),
        "rows_with_solid_overlap": sum(1 for p in rows if p.solid_overlaps),
        "identity": {
            "duplicate_file_ids": sum(n - 1 for n in file_ids.values() if n > 1),
            "duplicate_geometry": sum(n - 1 for n in digests.values() if n > 1),
            "room_ids_seen_more_than_once": sum(1 for n in room_ids.values() if n > 1),
            "split_conflicts": sum(1 for p in rows if p.split == "conflict"),
            "duplicate_geometry_across_splits": sum(
                1 for s in splits_by_digest.values() if len(s) > 1
            ),
        },
        "wall_protrusion_m_rectangular_rows": _histogram(
            (p.max_protrusion_m for p in rectangular), (1e-6, 0.02, 0.05, 0.1, 0.2)
        ),
        "unique_jids": len(jids),
        "jids_per_eligible_room": _histogram(
            (len(set(p.jids)) for p in eligible), (3, 5, 8, 12)
        ),
        "eligible_room_area_m2": _histogram(
            (p.dimensions[0] * p.dimensions[1] for p in eligible if p.dimensions),
            (8, 12, 16, 20, 30),
        ),
    }
