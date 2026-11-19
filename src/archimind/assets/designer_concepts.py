"""Immutable bindings for original designer pieces reviewed by the operator."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files

from . import inspection

CATEGORIES = frozenset(
    {"chair", "armchair", "sofa", "bed", "table", "desk", "storage", "lamp", "decor"}
)
# The PR #21 designer-chair feature is bound to this concept and reservation.
WRITING_CHAIR_ID = "oak-sage-writing-chair"
WRITING_CHAIR_WDH_M = (0.48, 0.52, 0.83)
CHAIR_SIZE = WRITING_CHAIR_WDH_M
BEDROOM_SIZES = {
    "upholstered-linen-bed": (1.6, 2.0, 0.6),
    "oak-bedside-lamp": (0.48, 0.43, 1.06),
}
_PIECE_BOUND_TOLERANCE_M = 5e-4


@dataclass(frozen=True)
class DesignerConcept:
    """A released bedroom-collection concept (registry group ``bedroom``)."""

    concept_id: str
    version: str
    name: str
    sha256: str
    front_sha256: str
    three_quarter_sha256: str
    width_m: float
    depth_m: float
    height_m: float
    bytes: int


@dataclass(frozen=True)
class DesignerPiece:
    concept_id: str
    version: str
    name: str
    category: str
    sha256: str
    front_sha256: str
    three_quarter_sha256: str
    width_m: float
    depth_m: float
    height_m: float
    bytes: int

    @property
    def variant_label(self):
        # The reviewed bend is the distinguishing dimension of the chair releases.
        if self.concept_id == WRITING_CHAIR_ID:
            labels = {"1.0.0": "Gentle back (42 mm)", "1.1.0": "Deep back (71 mm)"}
            return labels.get(self.version, f"Version {self.version}")
        return f"Version {self.version}"


# Kept for PR #21 callers; every chair is a designer piece of category "chair".
DesignerChair = DesignerPiece


def _dir():
    return files("archimind").joinpath("_viewer_assets")


def _registry():
    return json.loads(_dir().joinpath("designer_registry.json").read_bytes())


def _valid(row):
    return bool(
        row.category in CATEGORIES
        and isinstance(row.concept_id, str)
        and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", row.concept_id)
        and isinstance(row.version, str)
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", row.version)
        and isinstance(row.name, str)
        and row.name
        and all(
            isinstance(h, str) and re.fullmatch("[0-9a-f]{64}", h)
            for h in (row.sha256, row.front_sha256, row.three_quarter_sha256)
        )
        and all(
            type(v) in (int, float) and 0 < v <= 4
            for v in (row.width_m, row.depth_m, row.height_m)
        )
        and type(row.bytes) is int
        and 0 < row.bytes <= inspection.MAX_GLB_BYTES
    )


def approved_pieces(category: str | None = None) -> tuple[DesignerPiece, ...]:
    """Released pieces in publication order. Any invalid record disables the registry.

    Schema 1 (key ``chairs``) is still read; its records are chairs.
    """
    try:
        registry = _registry()
        if registry["schema_version"] == 1:
            rows = [{**row, "category": "chair"} for row in registry["chairs"]]
        elif registry["schema_version"] == 2:
            rows = registry["pieces"]
        else:
            return ()
        records = tuple(DesignerPiece(**row) for row in rows)
        seen = set()
        for row in records:
            if not _valid(row) or (row.concept_id, row.version) in seen:
                return ()
            if row.concept_id == WRITING_CHAIR_ID and (
                row.category != "chair"
                or (row.width_m, row.depth_m, row.height_m) != WRITING_CHAIR_WDH_M
            ):
                return ()
            seen.add((row.concept_id, row.version))
    except (OSError, ValueError, KeyError, TypeError):
        return ()
    if category is None:
        return records
    return tuple(row for row in records if row.category == category)


def approved_chairs() -> tuple[DesignerPiece, ...]:
    """The released writing-chair versions offered by the designer-chair feature."""
    return tuple(
        p for p in approved_pieces("chair") if p.concept_id == WRITING_CHAIR_ID
    )


def approved_collection() -> tuple[DesignerConcept, ...]:
    """Released bedroom-collection concepts (``bedroom`` group, schema 1 or 2)."""
    try:
        registry = _registry()
        if registry["schema_version"] not in (1, 2):
            return ()
        records = tuple(DesignerConcept(**row) for row in registry["bedroom"])
        seen = set()
        for row in records:
            if (
                row.concept_id not in BEDROOM_SIZES
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", row.version)
                or any(
                    not re.fullmatch("[0-9a-f]{64}", h)
                    for h in (row.sha256, row.front_sha256, row.three_quarter_sha256)
                )
                or (row.width_m, row.depth_m, row.height_m)
                != BEDROOM_SIZES[row.concept_id]
                or not 0 < row.bytes <= inspection.MAX_GLB_BYTES
                or (row.concept_id, row.version) in seen
            ):
                return ()
            seen.add((row.concept_id, row.version))
        return records
    except (OSError, ValueError, KeyError, TypeError):
        return ()


def _asset(digest, suffix):
    if not re.fullmatch("[0-9a-f]{64}", digest):
        raise ValueError("Invalid designer asset digest")
    try:
        data = inspection._read_local(_dir().joinpath(f"designer-{digest}.{suffix}"))
    except OSError:
        raise ValueError("Designer piece unavailable") from None
    if sha256(data).hexdigest() != digest:
        raise ValueError("Designer piece integrity check failed")
    return data


def _resolve(records, concept_id, version, sha256):
    for record in records:
        if (concept_id, version, sha256) == (
            record.concept_id,
            record.version,
            record.sha256,
        ):
            if len(_asset(record.sha256, "glb")) == record.bytes:
                return record
    raise ValueError("Designer piece release unavailable")


def resolve_piece(concept_id, version, sha256) -> DesignerPiece:
    return _resolve(approved_pieces(), concept_id, version, sha256)


def resolve_chair(concept_id, version, sha256) -> DesignerPiece:
    if concept_id == WRITING_CHAIR_ID:
        piece = resolve_piece(concept_id, version, sha256)
        if piece.category == "chair":
            return piece
    raise ValueError("Designer chair release unavailable")


def resolve_collection(concept_id, version, sha256) -> DesignerConcept:
    return _resolve(approved_collection(), concept_id, version, sha256)


def preview_bytes(piece, view):
    digest = {"front": piece.front_sha256, "three-quarter": piece.three_quarter_sha256}[
        view
    ]
    return _asset(digest, "png")


def inspect_chair(data):
    return inspect_concept(data, CHAIR_SIZE)


def inspect_concept(data, dimensions):
    """Measure actual transformed vertices and qualify the material-only concept."""
    if not 0 < len(data) <= inspection.MAX_GLB_BYTES:
        raise ValueError("Designer asset byte limit")
    doc, views = inspection._document(data)
    if any(doc.get(k) for k in ("extensionsUsed", "images", "textures", "cameras")):
        raise ValueError("Unsupported designer chair resources")
    bounds, meshes, _, triangles, _ = inspection._geometry(
        doc, inspection._accessors(doc, views)
    )
    actual = (*bounds.min_xyz, *bounds.max_xyz)
    w, d, h = dimensions
    expected = (-w / 2, 0.0, -d / 2, w / 2, h, d / 2)
    if any(abs(a - b) > 1e-6 for a, b in zip(actual, expected, strict=True)):
        raise ValueError(
            "Designer geometry must fit its native floor-centred reservation"
        )
    if not 0 < triangles <= inspection.MAX_ASSET_TRIANGLES:
        raise ValueError("Designer chair triangle limit")
    return {
        "bounds_xyz": [bounds.min_xyz, bounds.max_xyz],
        "mesh_instances": meshes,
        "triangles": triangles,
        "materials": len(doc.get("materials", [])),
        "textures": 0,
    }


def inspect_piece(data, wdh_m):
    """Measure transformed vertices of a released piece against its reservation.

    The piece must be floor-centred at native size: its bounds equal
    ``(-w/2, 0, -d/2, w/2, h, d/2)`` within 0.5 mm. Unlike the chair, embedded
    PNG/JPEG textures up to 2048 px are allowed; extensions, cameras and
    external resources are not.
    """
    if not 0 < len(data) <= inspection.MAX_GLB_BYTES:
        raise ValueError("Designer asset byte limit")
    width, depth, height = (float(v) for v in wdh_m)
    doc, views = inspection._document(data)
    if doc.get("cameras"):
        raise ValueError("Unsupported designer piece resources")
    images, texture_bytes = inspection._images(doc, views)
    if any(max(i.width, i.height) > inspection.MAX_TEXTURE_DIMENSION for i in images):
        raise ValueError("Designer piece texture exceeds 2048 px")
    bounds, meshes, _, triangles, _ = inspection._geometry(
        doc, inspection._accessors(doc, views)
    )
    actual = (*bounds.min_xyz, *bounds.max_xyz)
    expected = (-width / 2, 0.0, -depth / 2, width / 2, height, depth / 2)
    if any(
        abs(a - b) > _PIECE_BOUND_TOLERANCE_M
        for a, b in zip(actual, expected, strict=True)
    ):
        raise ValueError("Designer piece must fit its native floor-centred reservation")
    if not 0 < triangles <= inspection.MAX_ASSET_TRIANGLES:
        raise ValueError("Designer piece triangle limit")
    return {
        "bounds_xyz": [bounds.min_xyz, bounds.max_xyz],
        "mesh_instances": meshes,
        "triangles": triangles,
        "materials": len(doc.get("materials", [])),
        "textures": len(doc.get("textures", [])),
        "images_px": [[i.width, i.height] for i in images],
        "estimated_texture_bytes": texture_bytes,
    }
