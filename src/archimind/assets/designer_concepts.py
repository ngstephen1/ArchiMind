"""Immutable bindings for original designer concepts reviewed by the operator."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files

from . import inspection


@dataclass(frozen=True)
class DesignerConcept:
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
class DesignerChair(DesignerConcept):
    @property
    def variant_label(self):
        # The reviewed bend is the distinguishing dimension of these releases.
        return {"1.0.0": "Gentle back (42 mm)", "1.1.0": "Deep back (71 mm)"}.get(
            self.version, f"Version {self.version}"
        )


def _dir():
    return files("archimind").joinpath("_viewer_assets")


CHAIR_SIZE = (0.48, 0.52, 0.83)
BEDROOM_SIZES = {
    "upholstered-linen-bed": (1.6, 2.0, 0.6),
    "oak-bedside-lamp": (0.48, 0.43, 1.06),
}


def approved_chairs() -> tuple[DesignerChair, ...]:
    return _approved("chairs", DesignerChair, {"oak-sage-writing-chair": CHAIR_SIZE})


def approved_collection() -> tuple[DesignerConcept, ...]:
    return _approved("bedroom", DesignerConcept, BEDROOM_SIZES)


def _approved(group, record_type, sizes):
    """List released concepts in publication order. Missing registry disables the option."""
    try:
        registry = json.loads(_dir().joinpath("designer_registry.json").read_bytes())
        if registry["schema_version"] != 1:
            return ()
        records = tuple(record_type(**row) for row in registry[group])
        seen = set()
        for row in records:
            if (
                row.concept_id not in sizes
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", row.version)
                or any(
                    not re.fullmatch("[0-9a-f]{64}", h)
                    for h in (row.sha256, row.front_sha256, row.three_quarter_sha256)
                )
                or (row.width_m, row.depth_m, row.height_m) != sizes[row.concept_id]
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
        raise ValueError("Designer chair unavailable") from None
    if sha256(data).hexdigest() != digest:
        raise ValueError("Designer chair integrity check failed")
    return data


def resolve_chair(concept_id, version, sha256) -> DesignerChair:
    return _resolve(approved_chairs(), concept_id, version, sha256)


def resolve_collection(concept_id, version, sha256):
    return _resolve(approved_collection(), concept_id, version, sha256)


def _resolve(records, concept_id, version, sha256):
    for chair in records:
        if (concept_id, version, sha256) == (
            chair.concept_id,
            chair.version,
            chair.sha256,
        ):
            if len(_asset(chair.sha256, "glb")) == chair.bytes:
                return chair
    raise ValueError("Designer chair release unavailable")


def preview_bytes(chair, view):
    digest = {"front": chair.front_sha256, "three-quarter": chair.three_quarter_sha256}[
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
