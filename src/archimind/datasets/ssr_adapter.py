"""P2a: SSR-3DFRONT bedroom rows -> ``SceneReference`` / ``ExclusionRecord``.

Rules (each from the P1 probe, docs/data/DATASET_PROBE_P1.md):

* Geometry uses :mod:`archimind.datasets.ssr` unchanged (proven conventions).
* Categories come ONLY from MIDI-3D furniture ids (3D-FUTURE super-categories),
  joined by jid. SSR ``desc`` text is untrusted and never read. An object whose jid
  has no MIDI category is kept with ``exclusion="unmapped_category"``; it has no
  footprint, so it cannot reach a layout.
* SSR jids may carry a scale-variant suffix (``<uuid>-(0.74)-(0.74)-(0.74)``).
  The stored ``jid`` is the 36-character 3D-FUTURE model id; the real extent stays
  in ``size_raw``.
* ``canonical``: every object admitted at zero yaw, inside the walls, no solid
  overlap. ``reference_only``: at least one admitted object. Otherwise excluded.
* Rows with identical geometry are deduplicated: the smallest ``reference_id`` is
  kept and every other row becomes a ``duplicate_identity`` exclusion naming it.
* The MIDI split is recorded as the ``split_agreement`` check, because SSR and MIDI
  disagree for 735 joined bedrooms and combining them would leak evaluation data.
"""

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from archimind.datasets.contracts import (
    CheckResult,
    ExclusionRecord,
    Footprint,
    RoomExtent,
    SceneObject,
    SceneReference,
    namespaced,
)
from archimind.datasets.geometry import GeometryError
from archimind.datasets.ssr import (
    COORD_TOLERANCE_M,
    FLOOR_CONTACT_TOLERANCE_M,
    MAX_OBJECTS,
    SSR_CONVENTION,
    _overlap,
    _vertical_overlap,
    classify_room,
    object_box,
    profile_row,
    room_key,
    room_type_split,
)

TRANSFORM_VERSION = "1.0.0"
CATEGORY_MAP_VERSION = "1.0.0"
ADAPTER_VERSION = "1.0.0"
SOURCE = "ssr_3dfront"

# MIDI-3D / 3D-FUTURE super-category -> ArchiMind reference category.
CATEGORY_MAP: Mapping[str, str] = {
    "Bed": "bed",
    "Cabinet_Shelf_Desk": "cabinet_shelf_desk",
    "Chair": "chair",
    "Lighting": "lighting",
    "Others": "other",
    "Pier_Stool": "stool",
    "Sofa": "sofa",
    "Table": "table",
}
# Categories that legitimately hang above the floor (ceiling and wall lights).
NOT_FLOOR_STANDING = frozenset({"lighting"})
_GEOMETRY_CODES = frozenset(
    {"tilted_object", "non_quarter_turn_rotation", "invalid_dimensions"}
)

_BASE_JID = re.compile(
    r"^(?P<base>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(?P<variant>(?:-\([0-9.]{1,16}\))*)$"
)


def base_jid(jid) -> str | None:
    """3D-FUTURE model id of an SSR jid, or ``None`` when it is unrecognized."""
    match = _BASE_JID.fullmatch(jid) if isinstance(jid, str) else None
    return match["base"] if match else None


def lookup_category(jid, jid_categories: Mapping[str, str]) -> str | None:
    """MIDI super-category by exact jid, then by the base model id."""
    if not isinstance(jid, str):
        return None
    if jid in jid_categories:
        return jid_categories[jid]
    base = base_jid(jid)
    return jid_categories.get(base) if base else None


@dataclass(frozen=True)
class RowResult:
    """One parquet row's outcome: a scene, or a single exclusion."""

    reference_id: str
    content_digest: str
    split: str
    scene: SceneReference | None = None
    exclusion: ExclusionRecord | None = None


def _check(name: str, ok: bool, detail: str | None = None) -> CheckResult:
    return CheckResult(name=name, status="PASS" if ok else "FAIL", detail=detail)


def _exclude(reference_id, digest_, split, reason, detail) -> RowResult:
    return RowResult(
        reference_id=reference_id,
        content_digest=digest_,
        split=split,
        exclusion=ExclusionRecord(
            source=SOURCE, source_id=reference_id, reason=reason, detail=detail
        ),
    )


def convert_row(
    row: dict,
    *,
    revision: str,
    source_sha256: str,
    jid_categories: Mapping[str, str],
    midi_splits: Mapping[str, str],
    room_type: str = "bedroom",
) -> RowResult | None:
    """Convert one parquet row; ``None`` when the row is not of ``room_type``."""
    split = room_type_split(row.get("splits"), room_type)
    if split is None:
        return None
    scene = row.get("scene") or {}
    file_id = str(row.get("file_id"))
    room_id = str(scene.get("room_id"))
    try:
        key = room_key(file_id, room_id)
    except ValueError:
        return _exclude(
            namespaced(SOURCE, "malformed", re.sub(r"[^A-Za-z0-9._-]", "_", file_id)),
            "malformed",
            "unknown",
            "malformed_record",
            "row identity is not <house uuid>/<room id>",
        )
    house, room = key.split("/", 1)
    reference_id = namespaced(SOURCE, house, room)
    profile = profile_row(row, room_type)
    digest_ = profile.content_digest
    if split not in ("train", "val", "test"):
        return _exclude(
            reference_id, digest_, "unknown", "malformed_record", f"split {split}"
        )
    frame, room_reason = classify_room(
        scene.get("bounds_bottom") or [], scene.get("bounds_top") or []
    )
    if frame is None:
        return _exclude(
            reference_id, digest_, split, room_reason, "room is not an axis-aligned box"
        )
    objects = scene.get("objects") or []
    if not objects or len(objects) > MAX_OBJECTS:
        return _exclude(
            reference_id,
            digest_,
            split,
            "invalid_dimensions",
            f"{len(objects)} objects (allowed 1-{MAX_OBJECTS})",
        )

    records, boxes = [], []
    for index, obj in enumerate(objects):
        raw_jid = obj.get("jid")
        jid = base_jid(raw_jid)
        super_category = lookup_category(raw_jid, jid_categories)
        category = CATEGORY_MAP.get(super_category) if super_category else None
        try:
            size = tuple(float(c) for c in obj["size"])
            pos = tuple(float(c) for c in obj["pos"])
            rot = tuple(float(c) for c in obj["rot"])
            if len(size) != 3 or len(pos) != 3 or len(rot) != 4:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return _exclude(
                reference_id,
                digest_,
                split,
                "malformed_record",
                f"object o{index:02d} has malformed size/pos/rot",
            )
        footprint, exclusion, box = None, None, None
        try:
            box = object_box(frame, obj)
        except GeometryError as error:
            code = str(error)
            exclusion = code if code in _GEOMETRY_CODES else "malformed_record"
        if exclusion is None and category is None:
            exclusion = "unmapped_category"
        if exclusion is None:
            footprint = Footprint(
                x_m=box.x_m,
                y_m=box.y_m,
                width_m=box.width_m,
                depth_m=box.depth_m,
                height_m=box.height_m,
                yaw_quarter_turns=box.quarter_turns,
            )
            boxes.append((category, box))
        records.append(
            SceneObject(
                source_object_id=f"o{index:02d}",
                jid=jid,
                raw_category=super_category or "unmapped",
                category=category if exclusion is None else None,
                size_raw=size,
                position_raw=pos,
                rotation_raw_xyzw=rot,
                footprint=footprint,
                exclusion=exclusion,
            )
        )

    if not boxes:
        reasons = Counter(o.exclusion for o in records)
        reason, _ = min(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
        return _exclude(
            reference_id,
            digest_,
            split,
            reason,
            f"no admitted object ({len(records)} objects, most often {reason})",
        )

    eps = COORD_TOLERANCE_M
    outside = [
        b
        for _, b in boxes
        if b.x_m < -eps
        or b.y_m < -eps
        or b.x_m + b.width_m > frame.width_m + eps
        or b.y_m + b.depth_m > frame.depth_m + eps
        or b.bottom_z_m + b.height_m > frame.height_m + eps
    ]
    protrusion = max(
        (
            max(
                -b.x_m,
                -b.y_m,
                b.x_m + b.width_m - frame.width_m,
                b.y_m + b.depth_m - frame.depth_m,
            )
            for _, b in boxes
        ),
        default=0.0,
    )
    solid = sum(
        1
        for i, (_, a) in enumerate(boxes)
        for _, b in boxes[i + 1 :]
        if _overlap(a, b) and _vertical_overlap(a, b)
    )
    floating = sum(
        1
        for category, b in boxes
        if category not in NOT_FLOOR_STANDING
        and abs(b.bottom_z_m) > FLOOR_CONTACT_TOLERANCE_M
    )
    midi_split = midi_splits.get(key)
    checks = [
        _check(
            "wall_containment",
            not outside,
            f"{len(outside)} admitted objects past a wall; max {max(protrusion, 0.0):.3f} m",
        ),
        _check("solid_overlap", solid == 0, f"{solid} overlapping object pairs"),
        _check(
            "floor_contact",
            floating == 0,
            f"{floating} floor-standing objects off the floor by more than "
            f"{FLOOR_CONTACT_TOLERANCE_M} m",
        ),
        CheckResult(
            name="door_clearance",
            status="NOT_VERIFIABLE",
            detail="the source does not record doors or windows",
        ),
        CheckResult(
            name="split_agreement",
            status="NOT_VERIFIABLE"
            if midi_split is None
            else ("PASS" if midi_split == split else "FAIL"),
            detail="room not in MIDI-3D"
            if midi_split is None
            else f"ssr {split}, midi {midi_split}",
        ),
    ]
    admitted = [o for o in records if o.exclusion is None]
    canonical = (
        len(admitted) == len(records)
        and all(o.footprint.yaw_quarter_turns == 0 for o in admitted)
        and not outside
        and solid == 0
    )
    return RowResult(
        reference_id=reference_id,
        content_digest=digest_,
        split=split,
        scene=SceneReference(
            reference_id=reference_id,
            source=SOURCE,
            source_revision=revision,
            source_sha256=source_sha256,
            split=split,
            source_scene_id=house,
            source_room_id=room,
            tier="canonical" if canonical else "reference_only",
            room=RoomExtent(
                width_m=frame.width_m, depth_m=frame.depth_m, height_m=frame.height_m
            ),
            openings="unknown",
            objects=tuple(records),
            checks=tuple(checks),
            transform_version=TRANSFORM_VERSION,
            category_map_version=CATEGORY_MAP_VERSION,
        ),
    )


def deduplicate(
    results: Iterable[RowResult],
) -> tuple[list[SceneReference], list[ExclusionRecord]]:
    """Keep one scene per geometry digest; record every other row as an alias."""
    results = sorted(results, key=lambda r: r.reference_id)
    if len({r.reference_id for r in results}) != len(results):
        raise ValueError("Duplicate SSR reference_id")
    groups: dict[str, list[RowResult]] = {}
    for r in results:
        if r.scene is not None and r.content_digest != "malformed":
            groups.setdefault(r.content_digest, []).append(r)
    scenes, exclusions = [], [r.exclusion for r in results if r.exclusion]
    for group in groups.values():
        keep, *aliases = group  # sorted, so the smallest reference_id is kept
        scenes.append(keep.scene)
        for alias in aliases:
            exclusions.append(
                ExclusionRecord(
                    source=SOURCE,
                    source_id=alias.reference_id,
                    reason="duplicate_identity",
                    detail=f"same geometry as {keep.reference_id} "
                    f"(splits {alias.split} and {keep.split})",
                )
            )
    scenes.sort(key=lambda s: s.reference_id)
    exclusions.sort(key=lambda e: (e.source_id, e.reason))
    return scenes, exclusions


def build_report(
    scenes: Iterable[SceneReference], exclusions: Iterable[ExclusionRecord]
) -> dict:
    """Deterministic yield summary of an adapter run."""
    scenes, exclusions = list(scenes), list(exclusions)
    objects = [o for s in scenes for o in s.objects]
    checks = Counter(f"{c.name}|{c.status}" for s in scenes for c in s.checks)
    return {
        "adapter_version": ADAPTER_VERSION,
        "convention": SSR_CONVENTION.name,
        "convention_digest": SSR_CONVENTION.version_digest,
        "transform_version": TRANSFORM_VERSION,
        "category_map_version": CATEGORY_MAP_VERSION,
        "scenes": len(scenes),
        "tiers": dict(sorted(Counter(s.tier for s in scenes).items())),
        "tiers_by_split": dict(
            sorted(Counter(f"{s.split}|{s.tier}" for s in scenes).items())
        ),
        "exclusions": len(exclusions),
        "exclusion_reasons": dict(
            sorted(Counter(e.reason for e in exclusions).items())
        ),
        "objects": len(objects),
        "objects_admitted": sum(1 for o in objects if o.exclusion is None),
        "object_exclusions": dict(
            sorted(Counter(o.exclusion for o in objects if o.exclusion).items())
        ),
        "admitted_categories": dict(
            sorted(Counter(o.category for o in objects if o.category).items())
        ),
        "checks": dict(sorted(checks.items())),
    }
