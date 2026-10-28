"""Isolated one-asset Components V2 experiment; no Plotly or spatial-engine changes.

Only checked-in JS/CSS/HTML and the allowlisted local GLB are served. Never accepts
asset URLs, uploaded meshes, HTML or JS from users. V2 components are trusted app
code, not a security sandbox. Canonical data is passed as JSON, not interpolated
into executable content. This performs schema/asset checks, not spatial checks.
"""

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path

from archimind.models import RoomDesign

ASSET_DIR = Path(__file__).resolve().parents[1] / "_viewer_assets"
ASSET_NAME = "SheenChair.glb"
MAX_ASSET_BYTES = 15 * 1024 * 1024


class ViewerAssetError(ValueError):
    """The fixed bundled asset is missing or failed structural/integrity checks."""


def asset_path(name: str = ASSET_NAME) -> Path:
    """Allow one fixed filename; prevent traversal, URLs, and symlink escapes."""
    if name != ASSET_NAME:
        raise ViewerAssetError("Only the bundled Sheen Chair asset is supported.")
    directory = ASSET_DIR / "furniture"
    path = directory / name
    if path.is_symlink() or path.resolve().parent != directory.resolve():
        raise ViewerAssetError("Asset path is outside the bundled directory.")
    return path


def _glb_document(data: bytes) -> dict:
    """Bounded lightweight GLB 2 structural check, not a full glTF validator."""
    try:
        magic, version, length = struct.unpack_from("<4sII", data)
        if magic != b"glTF" or version != 2 or length != len(data):
            raise ValueError
        offset, chunks = 12, []
        while offset < length:
            size, kind = struct.unpack_from("<II", data, offset)
            offset += 8
            if size % 4 or offset + size > length:
                raise ValueError
            chunks.append((kind, data[offset : offset + size]))
            offset += size
        if len(chunks) != 2 or chunks[0][0] != 0x4E4F534A or chunks[1][0] != 0x004E4942:
            raise ValueError
        document = json.loads(chunks[0][1])
        if document["asset"]["version"] != "2.0" or len(document["buffers"]) != 1:
            raise ValueError
        buffer = document["buffers"][0]
        if "uri" in buffer or not 0 <= len(chunks[1][1]) - buffer["byteLength"] <= 3:
            raise ValueError
        for view in document["bufferViews"]:
            if (
                view.get("buffer", 0) != 0
                or view.get("byteOffset", 0) < 0
                or view["byteLength"] <= 0
            ):
                raise ValueError
            if view.get("byteOffset", 0) + view["byteLength"] > buffer["byteLength"]:
                raise ValueError
        if not document.get("meshes") or not document.get("images"):
            raise ValueError
        for image in document["images"]:
            if "uri" in image or image["mimeType"] not in ("image/jpeg", "image/png"):
                raise ValueError
            if not 0 <= image["bufferView"] < len(document["bufferViews"]):
                raise ValueError
        return document
    except (ValueError, KeyError, TypeError, struct.error, UnicodeError) as exc:
        raise ViewerAssetError("Bundled chair has an invalid GLB structure.") from exc


def verify_asset() -> dict:
    """Validate the local file and provenance checksum without any network access."""
    try:
        path = asset_path()
        if not path.is_file() or not 0 < path.stat().st_size <= MAX_ASSET_BYTES:
            raise ViewerAssetError(
                "Bundled chair is missing or exceeds the size limit."
            )
        metadata = json.loads((path.parent / "PROVENANCE.json").read_text())
        data = path.read_bytes()
        if (
            len(data) != metadata["size_bytes"]
            or hashlib.sha256(data).hexdigest() != metadata["sha256"]
        ):
            raise ViewerAssetError("Bundled chair failed its integrity check.")
        _glb_document(data)
        return metadata
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise ViewerAssetError(
            "Bundled chair or its provenance is unavailable."
        ) from exc


def viewer_payload(design: RoomDesign) -> dict:
    """Return bounded JSON for exactly one chair; never edits canonical objects."""
    design = RoomDesign.model_validate(design)
    if len(design.furniture) != 1:
        raise ValueError("Experimental viewer supports exactly one chair.")
    f, r = design.furniture[0], design.room
    if f.category != "chair" or f.rotation_deg != 0:
        raise ValueError("Experimental viewer supports one chair at rotation 0.")
    if any(not 0.1 <= v <= 20 for v in (r.width_m, r.depth_m, r.ceiling_height_m)):
        raise ValueError("Experimental room dimensions must be between 0.1 and 20 m.")
    if (
        any(not 0.05 <= v <= 10 for v in (f.width_m, f.depth_m, f.height_m))
        or max(abs(f.x_m), abs(f.y_m)) > 20
    ):
        raise ValueError(
            "Experimental furniture dimensions or coordinates exceed limits."
        )
    if any(len(v) > 256 for v in (r.id, r.name, f.id, f.name)):
        raise ValueError("Experimental viewer labels exceed the length limit.")
    return {
        "schema_version": 1,
        "asset_id": "sheen-chair",
        "room": r.model_dump(
            include={"id", "name", "width_m", "depth_m", "ceiling_height_m"}
        ),
        "furniture": f.model_dump(mode="json"),
    }


@lru_cache(maxsize=1)
def _component():
    import streamlit.components.v2 as components

    return components.component(
        "archimind.realistic_viewer",
        js="viewer.js",
        css="viewer.css",
    )


def render_realistic_viewer(
    design: RoomDesign, *, key: str = "experimental-chair"
) -> None:
    """Mount the trusted local component after input and bundled-asset checks."""
    payload = viewer_payload(design)
    verify_asset()
    _component()(data=payload, key=key)
