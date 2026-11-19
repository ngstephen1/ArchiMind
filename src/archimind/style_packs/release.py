"""Verify released pack assets on disk and keep packs inside their size caps."""

import io
import re
from hashlib import sha256
from pathlib import Path

from PIL import Image

from archimind.assets import inspection
from archimind.assets.designer_concepts import approved_pieces

from .models import AssetRelease, StylePack
from .registry import _packs_dir, _tier_bytes, load_releases

PACK_CAP_BYTES = 25 * 1024 * 1024
ALL_PACKS_CAP_BYTES = 120 * 1024 * 1024
_ROLES = {
    "material": {"diffuse", "normal", "roughness", "ao", "metalness"},
    "environment": {"hdr"},
    "model": {"model"},
}
_CC0_HOSTS = r"https://(?:polyhaven\.com|ambientcg\.com)/"


def assets_dir() -> Path:
    return Path(str(_packs_dir().joinpath("assets")))


def notices_path() -> Path:
    return Path(str(_packs_dir().joinpath("THIRD_PARTY_NOTICES.txt")))


def _hdr_size(data: bytes) -> tuple[int, int]:
    if not (data.startswith(b"#?RADIANCE") or data.startswith(b"#?RGBE")):
        raise ValueError("environment is not a Radiance .hdr file")
    head = data[:4096].split(b"\n")
    for line in head[1:]:
        if match := re.fullmatch(rb"-Y (\d+) \+X (\d+)", line.strip()):
            return int(match[2]), int(match[1])
    raise ValueError("environment .hdr has no resolution line")


def _glb_facts(data: bytes) -> dict:
    doc, views = inspection._document(data)
    images, _ = inspection._images(doc, views)
    if any(max(i.width, i.height) > inspection.MAX_TEXTURE_DIMENSION for i in images):
        raise ValueError("model texture exceeds 2048 px")
    bounds, meshes, _, triangles, _ = inspection._geometry(
        doc, inspection._accessors(doc, views)
    )
    if not 0 < triangles <= inspection.MAX_ASSET_TRIANGLES:
        raise ValueError("model exceeds 100,000 triangles")
    return {
        "triangles": triangles,
        "mesh_instances": meshes,
        "bounds_xyz": [list(bounds.min_xyz), list(bounds.max_xyz)],
    }


def verify_release(release: AssetRelease, directory: Path | None = None) -> dict:
    """Raise ValueError naming the problem; return measured facts per model."""
    directory = assets_dir() if directory is None else Path(directory)
    name = release.asset_id
    if release.license == "CC0-1.0" and not re.match(_CC0_HOSTS, release.source_url):
        raise ValueError(f"{name}: CC0 source must be a Poly Haven or ambientCG page")
    roles = {f.role for f in release.files}
    if not roles <= _ROLES[release.kind]:
        raise ValueError(f"{name}: roles {sorted(roles)} do not fit a {release.kind}")
    if release.kind == "material" and "diffuse" not in roles:
        raise ValueError(f"{name}: material has no diffuse map")
    if len({(f.role, f.tier) for f in release.files}) != len(release.files):
        raise ValueError(f"{name}: duplicate role and tier")
    facts = {}
    for file in release.files:
        path = directory / f"{file.sha256}.{file.ext}"
        if not path.is_file():
            raise ValueError(f"{name}: {file.role} file missing ({path.name})")
        data = path.read_bytes()
        if len(data) != file.bytes or sha256(data).hexdigest() != file.sha256:
            raise ValueError(f"{name}: {file.role} file hash or size mismatch")
        if file.ext in ("webp", "jpg", "png"):
            with Image.open(io.BytesIO(data)) as image:
                size = image.size
            if max(size) > inspection.MAX_TEXTURE_DIMENSION:
                raise ValueError(f"{name}: {file.role} texture exceeds 2048 px")
            if size != (file.width_px, file.height_px):
                raise ValueError(
                    f"{name}: {file.role} pixel size {size} differs from record"
                )
        elif file.ext == "hdr":
            size = _hdr_size(data)
            if max(size) > 1024:
                raise ValueError(f"{name}: environment maps ship at 1k only")
            if size != (file.width_px, file.height_px):
                raise ValueError(
                    f"{name}: environment pixel size {size} differs from record"
                )
        elif file.ext == "glb":
            facts[name] = _glb_facts(data)
    return facts


def pack_budget(pack: StylePack, tier: str) -> int:
    """Unique bytes the browser fetches for this pack at a tier (released assets only)."""
    ids = pack.asset_ids()
    total = _tier_bytes(load_releases(), ids, tier)
    pieces = {f"designer:{p.concept_id}@{p.version}": p for p in approved_pieces()}
    total += sum(pieces[a].bytes for a in ids if a in pieces)
    return total
