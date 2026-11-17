"""P2c: MIDI-3D rooms -> modality manifest, object associations and alignment.

Conventions proven on real rooms (docs/data/DATASET_MIDI_P2C.md):

* Scene archive: ``<top>/<house>/<room>.glb`` (furniture only),
  ``<top>/<house>/<room>_full.glb`` (furniture plus structure) and
  ``<top>/<house>/<room>/<furniture id>.glb`` per object, plus structure parts
  (``ceil``, ``floor``, ``wall``, ``others``). Object GLBs already carry world
  placement: their boxes reflect each object's yaw.
* Normalization: per room, MIDI = s * (SSR - t) with no axis change (both Y-up).
  The furniture union box is centred on the origin and its longest side is 1.9.
* Render archive: ``<top>/<house>/<room>/{render,rerender,normal,semantic}_k`` and
  ``depth_k.exr`` for k = 0..10, plus ``meta.json``. Image k belongs to
  ``locations[k]``; the frame names inside ``meta.json`` are stale and ignored.
  ``transform_matrix`` is camera-to-world in a Z-up world: a glTF point
  ``(x, y, z)`` is ``(x, -z, y)`` there. Cameras look along -Z with +Y up, and the
  horizontal field of view is ``camera_angle_x``.

Nothing here joins by names, captions or appearance: objects join SSR only through
the jid inside their MIDI furniture id, and rooms only through the room key.
"""

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from archimind.datasets.midi import FurnitureId, parse_furniture_id

ADAPTER_VERSION = "1.0.0"
NORMALIZED_EXTENT = 1.9
STRUCTURE_PARTS = frozenset({"ceil", "floor", "wall", "others"})
VIEW_KINDS = ("render", "rerender", "normal", "semantic", "depth")
VIEW_SUFFIX = {"semantic": ".png", "depth": ".exr"}
_VIEW = re.compile(r"^(?P<kind>[a-z]+)_(?P<index>\d{4})\.(?P<ext>webp|png|exr)$")

Vec3 = tuple[float, float, float]


class MidiAlignmentError(ValueError):
    """Inputs are inconsistent (for example, nothing joins)."""


# ------------------------------------------------------------- room files


@dataclass(frozen=True)
class RoomFiles:
    room_glb: str | None
    full_glb: str | None
    objects: Mapping[str, str]  # furniture id -> member path
    structure: tuple[str, ...]
    unrecognized: tuple[str, ...]


def classify_room_files(room: str, names: Iterable[str]) -> RoomFiles:
    """Sort a room's archive members (paths relative to the house directory)."""
    objects, structure, unrecognized = {}, [], []
    room_glb = full_glb = None
    for name in sorted(names):
        if name == f"{room}.glb":
            room_glb = name
        elif name == f"{room}_full.glb":
            full_glb = name
        elif name.startswith(f"{room}/") and name.endswith(".glb"):
            stem = name[len(room) + 1 : -4]
            if stem in STRUCTURE_PARTS:
                structure.append(name)
                continue
            try:
                parse_furniture_id(stem)
            except ValueError:
                unrecognized.append(name)
                continue
            objects[stem] = name
        else:
            unrecognized.append(name)
    return RoomFiles(room_glb, full_glb, objects, tuple(structure), tuple(unrecognized))


@dataclass(frozen=True)
class Association:
    matched: tuple[str, ...]
    missing: tuple[str, ...]  # listed for the room, no GLB
    orphans: tuple[str, ...]  # GLB present, not listed for the room
    duplicates: tuple[str, ...]  # listed more than once


def associate(listed: Sequence[str], present: Iterable[str]) -> Association:
    """Compare a room's MIDI furniture list with the object GLBs present."""
    counts: dict[str, int] = {}
    for f in listed:
        counts[f] = counts.get(f, 0) + 1
    present = set(present)
    return Association(
        matched=tuple(sorted(set(counts) & present)),
        missing=tuple(sorted(set(counts) - present)),
        orphans=tuple(sorted(present - set(counts))),
        duplicates=tuple(sorted(f for f, n in counts.items() if n > 1)),
    )


def view_inventory(names: Iterable[str], locations: int) -> dict:
    """Per view kind: indices present, missing and unexpected (names only)."""
    present: dict[str, set[int]] = {k: set() for k in VIEW_KINDS}
    unexpected = []
    for name in names:
        match = _VIEW.fullmatch(name)
        kind = match["kind"] if match else None
        if kind not in present or "." + match["ext"] != VIEW_SUFFIX.get(kind, ".webp"):
            if name != "meta.json":
                unexpected.append(name)
            continue
        present[kind].add(int(match["index"]))
    expected = set(range(locations))
    return {
        "locations": locations,
        "kinds": {
            k: {
                "present": len(v & expected),
                "missing": sorted(expected - v),
                "extra": sorted(v - expected),
            }
            for k, v in present.items()
        },
        "unexpected": sorted(unexpected),
    }


# ------------------------------------------------------------- SSR geometry


def ssr_world_box(size, pos, rot_xyzw) -> tuple[Vec3, Vec3] | None:
    """Centre and axis-aligned extent of an SSR object (Y-up, bottom-centre pivot).

    ``None`` for a tilted object: only rotations about +Y have an exact box here.
    """
    x, y, z, w = (float(v) for v in rot_xyzw)
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm == 0 or abs(x) / norm > 1e-6 or abs(z) / norm > 1e-6:
        return None
    yaw = 2 * math.atan2(y / norm, w / norm)
    c, s = abs(math.cos(yaw)), abs(math.sin(yaw))
    sx, sy, sz = (float(v) for v in size)
    extent = (c * sx + s * sz, sy, s * sx + c * sz)
    centre = (float(pos[0]), float(pos[1]) + sy / 2, float(pos[2]))
    return centre, extent


def predicted_normalization(boxes: Sequence[tuple[Vec3, Vec3]]) -> tuple[float, Vec3]:
    """(s, t) implied by the furniture union box, if SSR lists the same objects."""
    if not boxes:
        raise MidiAlignmentError("No SSR boxes to predict the normalization from")
    lo = [min(c[i] - e[i] / 2 for c, e in boxes) for i in range(3)]
    hi = [max(c[i] + e[i] / 2 for c, e in boxes) for i in range(3)]
    longest = max(h - lo_ for lo_, h in zip(lo, hi, strict=True))
    centre = tuple((a + b) / 2 for a, b in zip(lo, hi, strict=True))
    return NORMALIZED_EXTENT / longest, centre


# ------------------------------------------------------------- alignment


@dataclass(frozen=True)
class ObjectPair:
    furniture_id: str
    ssr_object_id: str
    midi_centre: Vec3
    midi_extent: Vec3
    ssr_centre: Vec3
    ssr_extent: Vec3


@dataclass(frozen=True)
class Similarity:
    scale: float  # MIDI units per metre
    translation: Vec3  # SSR point that maps to the MIDI origin

    def to_ssr(self, p: Vec3) -> Vec3:
        return tuple(
            v / self.scale + t for v, t in zip(p, self.translation, strict=True)
        )


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def fit_similarity(pairs: Sequence[ObjectPair]) -> Similarity:
    """Robust (median) uniform scale and translation, from matched objects."""
    ratios = [
        m / e
        for p in pairs
        for m, e in zip(p.midi_extent, p.ssr_extent, strict=True)
        if e > 0.05  # thin extents carry little scale information
    ]
    if not ratios:
        raise MidiAlignmentError("No matched object to fit the alignment")
    scale = _median(ratios)
    translation = tuple(
        _median([p.ssr_centre[i] - p.midi_centre[i] / scale for p in pairs])
        for i in range(3)
    )
    return Similarity(scale=scale, translation=translation)


def residuals(pair: ObjectPair, fit: Similarity) -> dict:
    """Centre and extent errors of one pair, in metres."""
    centre = fit.to_ssr(pair.midi_centre)
    return {
        "centre_m": max(
            abs(a - b) for a, b in zip(centre, pair.ssr_centre, strict=True)
        ),
        "extent_m": max(
            abs(m / fit.scale - e)
            for m, e in zip(pair.midi_extent, pair.ssr_extent, strict=True)
        ),
    }


def match_objects(
    midi: Mapping[str, tuple[Vec3, Vec3]],
    ssr: Mapping[str, tuple[str | None, tuple[Vec3, Vec3] | None]],
) -> tuple[list[ObjectPair], list[str], list[str]]:
    """Pair MIDI objects with SSR objects that share a jid.

    ``midi`` maps furniture ids to (centre, extent); ``ssr`` maps SSR object ids to
    (base jid, box or None). Unique jids pair directly. Repeated jids are assigned
    by nearest centre under the fit from the unique pairs; with no unique pair
    they stay unmatched rather than guessed. Returns pairs, unmatched furniture
    ids and unmatched SSR object ids.
    """
    by_jid_midi: dict[str, list[str]] = {}
    for fid in midi:
        by_jid_midi.setdefault(_base(parse_furniture_id(fid)), []).append(fid)
    by_jid_ssr: dict[str, list[str]] = {}
    for oid, (jid, box) in ssr.items():
        if jid and box is not None:
            by_jid_ssr.setdefault(jid, []).append(oid)

    def pair(fid, oid):
        (mc, me), (_, (sc, se)) = midi[fid], ssr[oid]
        return ObjectPair(fid, oid, mc, me, sc, se)

    pairs = [
        pair(fids[0], by_jid_ssr[jid][0])
        for jid, fids in sorted(by_jid_midi.items())
        if len(fids) == 1 and len(by_jid_ssr.get(jid, [])) == 1
    ]
    repeated = [
        jid
        for jid, fids in sorted(by_jid_midi.items())
        if len(by_jid_ssr.get(jid, [])) and not (len(fids) == 1 == len(by_jid_ssr[jid]))
    ]
    if repeated and pairs:
        fit = fit_similarity(pairs)
        for jid in repeated:
            options = [
                (_distance(fit.to_ssr(midi[f][0]), ssr[o][1][0]), f, o)
                for f in by_jid_midi[jid]
                for o in by_jid_ssr[jid]
            ]
            used_f, used_o = set(), set()
            for _, f, o in sorted(options):
                if f not in used_f and o not in used_o:
                    pairs.append(pair(f, o))
                    used_f.add(f)
                    used_o.add(o)
    paired_f = {p.furniture_id for p in pairs}
    paired_o = {p.ssr_object_id for p in pairs}
    pairs.sort(key=lambda p: p.furniture_id)
    return (
        pairs,
        sorted(f for f in midi if f not in paired_f),
        sorted(o for o in ssr if o not in paired_o),
    )


def _base(fid: FurnitureId) -> str:
    return fid.jid[:36]


def _distance(a: Vec3, b: Vec3) -> float:
    return math.dist(a, b)


# ------------------------------------------------------------- cameras


def gltf_to_camera_world(p: Vec3) -> Vec3:
    """glTF Y-up point -> the Z-up world of ``meta.json`` camera matrices."""
    x, y, z = p
    return (x, -z, y)


def project(
    c2w: Sequence[Sequence[float]], angle_x: float, width: int, height: int, p: Vec3
) -> tuple[float, float] | None:
    """Pixel (u right, v down) of a camera-world point; ``None`` behind the camera."""
    if len(c2w) < 3 or any(len(row) < 4 for row in c2w[:3]):
        raise MidiAlignmentError("transform_matrix must be 4x4")
    if not 0 < angle_x < math.pi:
        raise MidiAlignmentError("camera_angle_x must be in (0, pi)")
    d = [p[i] - c2w[i][3] for i in range(3)]
    xc, yc, zc = (sum(c2w[i][j] * d[i] for i in range(3)) for j in range(3))
    if zc >= -1e-9:
        return None
    focal = (width / 2) / math.tan(angle_x / 2)
    return (width / 2 + focal * xc / -zc, height / 2 - focal * yc / -zc)


def projected_box(
    c2w,
    angle_x: float,
    width: int,
    height: int,
    lo: Vec3,
    hi: Vec3,
    to_world=gltf_to_camera_world,
    min_px: float = 2.0,
) -> tuple[float, float, float, float] | None:
    """Clipped image box of a glTF-space box.

    ``None`` if any corner is behind the camera or the clipped box is narrower
    than ``min_px`` (off-screen).
    """
    points = []
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            for z in (lo[2], hi[2]):
                q = project(c2w, angle_x, width, height, to_world((x, y, z)))
                if q is None:
                    return None
                points.append(q)
    us, vs = [q[0] for q in points], [q[1] for q in points]
    box = (
        max(0.0, min(us)),
        max(0.0, min(vs)),
        min(width, max(us)),
        min(height, max(vs)),
    )
    return box if box[2] - box[0] >= min_px and box[3] - box[1] >= min_px else None


def box_iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


# ------------------------------------------------------------- reports

CENTRE_TOLERANCE_M = 0.02
EXTENT_TOLERANCE_M = 0.02


def furniture_name(f: FurnitureId) -> str:
    return f"{f.category}_{f.jid}_{f.instance}"


def is_quarter_turn(rot_xyzw, tolerance_rad: float = 1e-3) -> bool:
    _, y, _, w = (float(v) for v in rot_xyzw)
    quarters = 2 * math.atan2(y, w) / (math.pi / 2)
    return abs(quarters - round(quarters)) * (math.pi / 2) <= tolerance_rad


def alignment_report(
    midi: Mapping[str, tuple[Vec3, Vec3]], ssr_objects: Sequence[Mapping]
) -> dict:
    """Fit, residuals and the PASS/FAIL verdict for one room.

    ``ssr_objects`` are SceneReference objects (dicts with ``source_object_id``,
    ``jid``, ``size_raw``, ``position_raw`` and ``rotation_raw_xyzw``). Extents
    are compared only for objects at a quarter turn: the box of a mesh at any
    other yaw is smaller than the rotated SSR box.
    """
    ssr = {
        o["source_object_id"]: (
            o.get("jid"),
            ssr_world_box(o["size_raw"], o["position_raw"], o["rotation_raw_xyzw"]),
        )
        for o in ssr_objects
    }
    rotations = {o["source_object_id"]: o["rotation_raw_xyzw"] for o in ssr_objects}
    pairs, unmatched_midi, unmatched_ssr = match_objects(midi, ssr)
    if not pairs:
        return {
            "status": "NOT_VERIFIABLE",
            "detail": "no MIDI object shares a jid with an SSR object",
            "unmatched_midi": unmatched_midi,
            "unmatched_ssr": unmatched_ssr,
        }
    fit = fit_similarity(pairs)
    rows, failures = [], 0
    for p in pairs:
        r = residuals(p, fit)
        comparable = is_quarter_turn(rotations[p.ssr_object_id])
        ok = r["centre_m"] <= CENTRE_TOLERANCE_M and (
            not comparable or r["extent_m"] <= EXTENT_TOLERANCE_M
        )
        failures += not ok
        rows.append(
            {
                "furniture_id": p.furniture_id,
                "ssr_object_id": p.ssr_object_id,
                "centre_error_m": round(r["centre_m"], 4),
                "extent_error_m": round(r["extent_m"], 4) if comparable else None,
                "status": "PASS" if ok else "FAIL",
            }
        )
    predicted = predicted_normalization([b for _, b in ssr.values() if b is not None])
    return {
        "status": "PASS" if failures == 0 else "FAIL",
        "scale_midi_per_m": round(fit.scale, 6),
        "translation_m": [round(v, 4) for v in fit.translation],
        "predicted_from_ssr": {
            "scale_midi_per_m": round(predicted[0], 6),
            "translation_m": [round(v, 4) for v in predicted[1]],
            "agrees": abs(predicted[0] / fit.scale - 1) <= 0.01,
        },
        "tolerance_m": {"centre": CENTRE_TOLERANCE_M, "extent": EXTENT_TOLERANCE_M},
        "pairs": rows,
        "unmatched_midi": unmatched_midi,
        "unmatched_ssr": unmatched_ssr,
    }


CAMERA_HYPOTHESES = {
    # name: (glTF -> camera-world mapping, image k -> location index rule)
    "documented": (gltf_to_camera_world, "same_index"),
    "y_up_world": (lambda p: p, "same_index"),
    "sorted_frame_names": (gltf_to_camera_world, "sorted_frames"),
    "y_up_and_sorted": (lambda p: p, "sorted_frames"),
}


def _frame_number(location: Mapping) -> int:
    frames = location.get("frames") or [{}]
    match = re.search(r"_(\d+)\.", str(frames[0].get("name", "")))
    return int(match.group(1)) if match else 0


def camera_report(
    meta: Mapping,
    objects: Mapping[str, tuple[Vec3, Vec3]],
    label_boxes: Sequence[Mapping[int, tuple[float, float, float, float]]],
    *,
    width: int,
    height: int,
) -> dict:
    """Score each camera hypothesis by projected-object vs semantic-region overlap.

    ``objects`` maps furniture ids to glTF (min, max) boxes; ``label_boxes[k]`` maps
    the semantic labels of image k to their pixel boxes. PASS means the documented
    convention scores best, so the convention is evidenced, not assumed.
    """
    locations = meta.get("locations") or []
    angle = meta.get("camera_angle_x")
    if len(label_boxes) != len(locations) or not isinstance(angle, int | float):
        raise MidiAlignmentError("Views and camera locations do not line up")
    order = sorted(range(len(locations)), key=lambda j: _frame_number(locations[j]))
    scores = {}
    for name, (to_world, rule) in CAMERA_HYPOTHESES.items():
        values = []
        for k, labels in enumerate(label_boxes):
            location = locations[k if rule == "same_index" else order[k]]
            for lo, hi in objects.values():
                box = projected_box(
                    location["transform_matrix"], angle, width, height, lo, hi, to_world
                )
                if box is None:
                    continue  # behind the camera or off-screen
                values.append(
                    max((box_iou(box, b) for b in labels.values()), default=0.0)
                )
        scores[name] = {
            "objects_in_view": len(values),
            "median_iou": round(_median(values), 4) if values else 0.0,
        }
    highest = max(row["median_iou"] for row in scores.values())
    winners = [name for name, row in scores.items() if row["median_iou"] == highest]
    best = winners[0] if highest > 0 and len(winners) == 1 else None
    return {
        "status": "NOT_VERIFIABLE"
        if best is None
        else ("PASS" if best == "documented" else "FAIL"),
        "best": best,
        "hypotheses": scores,
        "camera_angle_x": angle,
        "locations": len(locations),
    }


def topdown_svg(
    room: Mapping[str, float], ssr_boxes: Mapping[str, tuple[Vec3, Vec3]],
    midi_in_ssr: Mapping[str, tuple[Vec3, Vec3]], *, px_per_m: float = 100.0,
) -> str:  # fmt: skip
    """Top view (x right, z down) of SSR boxes (solid) and fitted MIDI boxes (dashed).

    Boxes are (centre, extent) in SSR raw metres; the room is centred on the origin.
    """
    w, d = room["width_m"], room["depth_m"]
    margin = 0.5
    size_x, size_z = (w + 2 * margin) * px_per_m, (d + 2 * margin) * px_per_m

    def rect(centre, extent, style):
        x = (centre[0] - extent[0] / 2 + w / 2 + margin) * px_per_m
        z = (centre[2] - extent[2] / 2 + d / 2 + margin) * px_per_m
        return (
            f'<rect x="{x:.1f}" y="{z:.1f}" width="{extent[0] * px_per_m:.1f}" '
            f'height="{extent[2] * px_per_m:.1f}" {style}/>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size_x:.0f}" height="{size_z:.0f}">',
        f'<rect width="{size_x:.0f}" height="{size_z:.0f}" fill="white"/>',
        rect(
            (0.0, 0.0, 0.0), (w, 0.0, d), 'fill="none" stroke="black" stroke-width="2"'
        ),
    ]
    for centre, extent in ssr_boxes.values():
        parts.append(
            rect(centre, extent, 'fill="#4a90d9" fill-opacity="0.25" stroke="#1f5fa8"')
        )
    for centre, extent in midi_in_ssr.values():
        parts.append(
            rect(
                centre,
                extent,
                'fill="none" stroke="#d0452f" stroke-dasharray="6 4" stroke-width="2"',
            )
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
