"""Synthetic, clearly labelled fixtures. They contain no real source rows or meshes.

Used by tests and by ``python -m archimind.datasets fixture-pack`` as an end-to-end
self-check on any machine (including Colab) before real data is processed.
"""

import json
import struct
from pathlib import Path

from archimind.datasets.canonical import sha256_hex
from archimind.datasets.contracts import (
    CheckResult,
    ExclusionRecord,
    Footprint,
    PermissionRecord,
    ReferenceAsset,
    RoomExtent,
    SceneObject,
    SceneReference,
    SourceFile,
    SourceManifest,
)

SYNTHETIC_REVISION = "synthetic0000"
SYNTHETIC_TIME = "2026-01-01T00:00:00Z"
FIXTURE_VERSION = "0.0.1"


def synthetic_glb_bytes(label: str = "synthetic") -> bytes:
    """A minimal, valid glTF 2.0 binary with no external references."""
    document = {"asset": {"version": "2.0", "generator": f"archimind-{label}"}}
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * (-len(payload) % 4)
    total = 12 + 8 + len(payload)
    return (
        struct.pack("<III", 0x46546C67, 2, total)
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
    )


def permission(value: str = "allowed") -> PermissionRecord:
    return PermissionRecord(
        local_research=value,
        derived_metadata=value,
        public_geometry=value,
        public_images=value,
        provider_disclosure="denied",
        evidence="Synthetic fixture; no real data",
        decided_by="fixture",
        decided_utc=SYNTHETIC_TIME,
    )


def source_manifest(source: str, value: str = "allowed") -> SourceManifest:
    data = f"{source}-synthetic".encode()
    return SourceManifest(
        source=source,
        origin_url="https://example.invalid/synthetic",
        revision=SYNTHETIC_REVISION,
        retrieved_utc=SYNTHETIC_TIME,
        files=(SourceFile(path="raw_model.obj", size_bytes=1, sha256=sha256_hex(b"o")),)
        if source == "future_3d"
        else (
            SourceFile(
                path="synthetic.json", size_bytes=len(data), sha256=sha256_hex(data)
            ),
        ),
        permission=permission(value),
    )


def _object(
    oid: str,
    category: str,
    x: float,
    y: float,
    w: float,
    d: float,
    h: float,
    turns: int = 0,
) -> SceneObject:
    return SceneObject(
        source_object_id=oid,
        jid=f"jid-{oid}",
        raw_category=category,
        category={"desk": "table", "nightstand": "cabinet_shelf_desk"}.get(
            category, category
        ),
        size_raw=(w, h, d),
        position_raw=(x + w / 2, h / 2, y + d / 2),
        rotation_raw_xyzw=(0.0, 0.0, 0.0, 1.0),
        footprint=Footprint(
            x_m=x, y_m=y, width_m=w, depth_m=d, height_m=h, yaw_quarter_turns=turns
        ),
    )


def synthetic_scenes() -> list[SceneReference]:
    common = dict(
        source="ssr_3dfront",
        source_revision=SYNTHETIC_REVISION,
        source_sha256=sha256_hex(b"ssr_3dfront-synthetic"),
        split="train",
        transform_version=FIXTURE_VERSION,
        category_map_version=FIXTURE_VERSION,
        openings="unknown",
    )
    checks = (
        CheckResult(name="containment", status="PASS"),
        CheckResult(name="collision", status="PASS"),
        CheckResult(
            name="door_clearance",
            status="NOT_VERIFIABLE",
            detail="Openings are not recorded in the source",
        ),
    )
    return [
        SceneReference(
            reference_id="ssr:synthetic-house-1:bedroom-1",
            source_scene_id="synthetic-house-1",
            source_room_id="bedroom-1",
            tier="canonical",
            room=RoomExtent(width_m=4.0, depth_m=3.5, height_m=2.7),
            objects=(
                _object("bed-1", "bed", 1.0, 1.5, 1.6, 2.0, 0.5),
                _object("nightstand-1", "nightstand", 0.4, 3.0, 0.5, 0.4, 0.55),
            ),
            checks=checks,
            **common,
        ),
        SceneReference(
            reference_id="ssr:synthetic-house-2:bedroom-1",
            source_scene_id="synthetic-house-2",
            source_room_id="bedroom-1",
            tier="reference_only",
            room=RoomExtent(width_m=3.2, depth_m=3.0, height_m=2.6),
            objects=(
                _object("bed-1", "bed", 0.2, 0.5, 2.0, 1.4, 0.5, turns=1),
                _object("desk-1", "desk", 2.0, 2.2, 1.0, 0.6, 0.75),
            ),
            checks=checks,
            **common,
        ),
    ]


def synthetic_exclusions() -> list[ExclusionRecord]:
    return [
        ExclusionRecord(
            source="ssr_3dfront",
            source_id="ssr:synthetic-house-3:bedroom-1",
            reason="irregular_room",
            detail="Synthetic L-shaped floor",
        )
    ]


def synthetic_asset(glb: bytes) -> ReferenceAsset:
    return ReferenceAsset(
        asset_id="future:synthetic-jid-1",
        version="0.0.1",
        source_jid="synthetic-jid-1",
        source_files=(
            SourceFile(path="raw_model.obj", size_bytes=1, sha256=sha256_hex(b"o")),
        ),
        glb=SourceFile(
            path="assets/synthetic-jid-1.glb",
            size_bytes=len(glb),
            sha256=sha256_hex(glb),
        ),
        triangles=12,
        max_texture_px=0,
        bounds_m=(1.0, 1.0, 1.0),
        scale_evidence="Synthetic unit cube",
        converter="none (synthetic)",
        attribution="Synthetic fixture",
    )


def build_synthetic_pack(root: Path, *, audience: str = "local"):
    from archimind.datasets.pack import build_pack

    root = Path(root)
    glb = synthetic_glb_bytes()
    staging = root.with_name(root.name + ".glb-staging")
    staging.mkdir(parents=True, exist_ok=True)
    glb_path = staging / "synthetic-jid-1.glb"
    glb_path.write_bytes(glb)
    try:
        return build_pack(
            root,
            pack_id="synthetic-selfcheck",
            audience=audience,
            sources=[source_manifest("ssr_3dfront"), source_manifest("future_3d")],
            scenes=synthetic_scenes(),
            exclusions=synthetic_exclusions(),
            assets=[synthetic_asset(glb)],
            glb_files={"assets/synthetic-jid-1.glb": glb_path},
            transform_version=FIXTURE_VERSION,
            category_map_version=FIXTURE_VERSION,
            builder="fixture",
            created_utc=SYNTHETIC_TIME,
        )
    finally:
        glb_path.unlink(missing_ok=True)
        staging.rmdir()
