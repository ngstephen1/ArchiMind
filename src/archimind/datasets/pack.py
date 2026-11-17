"""Build, verify and load a reference pack: the only dataset artifact the app reads.

Layout (all paths fixed, relative to the pack root)::

    manifest.json        PackManifest, written last
    sources.jsonl        SourceManifest per source
    scenes.jsonl         SceneReference, sorted by reference_id
    exclusions.jsonl     ExclusionRecord, sorted
    assets.jsonl         ReferenceAsset, sorted by asset_id
    assets/<name>.glb    embedded-only GLB files referenced by assets.jsonl

``snapshot_id`` hashes the pack identity, versions and every file digest, not the
build time, so rebuilding identical content yields an identical snapshot.
"""

import re
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from archimind.datasets.canonical import (
    CanonicalError,
    atomic_write_bytes,
    canonical_bytes,
    digest,
    file_sha256,
    iter_jsonl,
    strict_loads,
    write_jsonl,
)
from archimind.datasets.contracts import (
    SCHEMA_VERSION,
    ExclusionRecord,
    PackFile,
    PackManifest,
    ReferenceAsset,
    SceneReference,
    SourceManifest,
)
from archimind.datasets.safe_io import UnsafeContentError, read_glb_json

MANIFEST = "manifest.json"
_RECORD_FILES = {
    "sources.jsonl": ("sources", SourceManifest),
    "scenes.jsonl": ("scenes", SceneReference),
    "exclusions.jsonl": ("exclusions", ExclusionRecord),
    "assets.jsonl": ("assets", ReferenceAsset),
}
MAX_PACK_FILE_BYTES = 64 * 1024 * 1024
_CODE = re.compile(r"^[a-z_]+$")


class PackError(ValueError):
    """The pack is invalid, inconsistent or not eligible for its audience."""


def _validate(model, data):
    """Strict validation in JSON mode, where arrays are accepted for tuples."""
    return model.model_validate_json(canonical_bytes(data))


def _snapshot(manifest_fields: Mapping, files: Sequence[PackFile]) -> str:
    return digest(
        {
            "schema_version": SCHEMA_VERSION,
            **manifest_fields,
            "files": [(f.path, f.kind, f.sha256, f.size_bytes) for f in files],
        }
    )


def _dedupe(records, key):
    unique: dict[str, object] = {}
    for record in records:
        k = key(record)
        if k in unique and canonical_bytes(unique[k]) != canonical_bytes(record):
            raise PackError(f"Conflicting records share identity {k}")
        unique[k] = record
    return [unique[k] for k in sorted(unique)]


def check_audience(
    audience: str,
    sources: Sequence[SourceManifest],
    *,
    has_assets: bool,
) -> None:
    if audience not in ("local", "public"):
        raise PackError("invalid_audience")
    by_source = {s.source: s for s in sources}
    if len(by_source) != len(sources):
        raise PackError("duplicate_source")
    if audience == "public":
        for s in sources:
            if not s.permission.allows("derived_metadata"):
                raise PackError("source_not_public")
        if has_assets and not (
            "future_3d" in by_source
            and by_source["future_3d"].permission.allows("public_geometry")
        ):
            raise PackError("assets_not_public")
    else:
        for s in sources:
            if not s.permission.allows("local_research"):
                raise PackError("source_not_permitted")


def _check_bindings(sources, scenes, exclusions, assets, transform, category_map):
    """Validate relationships as well as individual records, on build AND load."""
    by_source = {s.source: s for s in sources}
    for records, key in (
        (sources, lambda s: s.source),
        (scenes, lambda s: s.reference_id),
        (exclusions, lambda e: (e.source, e.source_id, e.reason)),
        (assets, lambda a: a.asset_id),
    ):
        if len({key(r) for r in records}) != len(records):
            raise PackError("duplicate_record")
    for record in (*scenes, *exclusions):
        if record.source not in by_source:
            raise PackError("missing_source_binding")
    for scene in scenes:
        source = by_source[scene.source]
        if scene.source_revision != source.revision or scene.source_sha256 not in {
            f.sha256 for f in source.files
        }:
            raise PackError("scene_source_mismatch")
        if (
            scene.transform_version != transform
            or scene.category_map_version != category_map
        ):
            raise PackError("scene_version_mismatch")
    if assets and "future_3d" not in by_source:
        raise PackError("missing_asset_source")
    if assets:
        source_files = {f.path: f for f in by_source["future_3d"].files}
        for asset in assets:
            if any(source_files.get(f.path) != f for f in asset.source_files):
                raise PackError("asset_source_mismatch")


def build_pack(
    root: Path,
    *,
    pack_id: str,
    audience: str,
    sources: Sequence[SourceManifest],
    scenes: Sequence[SceneReference],
    exclusions: Sequence[ExclusionRecord],
    assets: Sequence[ReferenceAsset],
    glb_files: Mapping[str, Path],
    transform_version: str,
    category_map_version: str,
    builder: str,
    created_utc: str,
) -> PackManifest:
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise PackError("Pack directory must be new or empty")
    check_audience(audience, sources, has_assets=bool(assets))
    known_sources = {s.source for s in sources}
    for record in (*scenes, *exclusions):
        if record.source not in known_sources:
            raise PackError(f"Record from {record.source} has no source manifest")
    if assets and "future_3d" not in known_sources:
        raise PackError("Assets require a future_3d source manifest")
    for scene in scenes:
        if (
            scene.transform_version != transform_version
            or scene.category_map_version != category_map_version
        ):
            raise PackError("Scene versions differ from the pack versions")

    sources = _dedupe(sources, lambda s: s.source)
    scenes = _dedupe(scenes, lambda s: s.reference_id)
    exclusions = _dedupe(exclusions, lambda e: f"{e.source}|{e.source_id}|{e.reason}")
    assets = _dedupe(assets, lambda a: a.asset_id)
    _check_bindings(
        sources, scenes, exclusions, assets, transform_version, category_map_version
    )
    referenced = {a.glb.path for a in assets}
    if referenced != set(glb_files):
        raise PackError("GLB files must match the assets exactly")

    root.mkdir(parents=True, exist_ok=True)
    try:
        files = []
        for name, records in (
            ("sources.jsonl", sources),
            ("scenes.jsonl", scenes),
            ("exclusions.jsonl", exclusions),
            ("assets.jsonl", assets),
        ):
            sha, count = write_jsonl(root / name, records)
            files.append(
                PackFile(
                    path=name,
                    kind=_RECORD_FILES[name][0],
                    size_bytes=(root / name).stat().st_size,
                    sha256=sha,
                    records=count,
                )
            )
        for asset in assets:
            target = root / asset.glb.path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(glb_files[asset.glb.path], target)
            if (
                file_sha256(target) != asset.glb.sha256
                or target.stat().st_size != asset.glb.size_bytes
            ):
                raise PackError(f"{asset.asset_id} GLB bytes differ from its record")
            read_glb_json(target)
            files.append(
                PackFile(
                    path=asset.glb.path,
                    kind="glb",
                    size_bytes=asset.glb.size_bytes,
                    sha256=asset.glb.sha256,
                )
            )
        files.sort(key=lambda f: f.path)
        identity = {
            "pack_id": pack_id,
            "audience": audience,
            "transform_version": transform_version,
            "category_map_version": category_map_version,
        }
        manifest = PackManifest(
            **identity,
            created_utc=created_utc,
            builder=builder,
            files=tuple(files),
            snapshot_id=_snapshot(identity, files),
        )
        atomic_write_bytes(root / MANIFEST, canonical_bytes(manifest) + b"\n")
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise
    return manifest


@dataclass(frozen=True)
class LoadedPack:
    manifest: PackManifest
    sources: tuple[SourceManifest, ...]
    scenes: tuple[SceneReference, ...]
    exclusions: tuple[ExclusionRecord, ...]
    assets: tuple[ReferenceAsset, ...]


def verify_pack(root: Path) -> LoadedPack:
    """Re-hash every file, re-validate every record and recompute the snapshot."""
    root = Path(root)
    if any(p.is_symlink() for p in root.rglob("*")):
        raise PackError("symlink_in_pack")
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        raise PackError("missing_manifest")
    try:
        manifest = _validate(PackManifest, strict_loads(manifest_path.read_bytes()))
    except (CanonicalError, ValidationError) as error:
        raise PackError("invalid_manifest") from error
    present = {
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    } - {MANIFEST}
    listed = {f.path for f in manifest.files}
    if present != listed:
        raise PackError("pack_files_differ_from_manifest")
    required = set(_RECORD_FILES)
    if not required <= listed:
        raise PackError("missing_record_file")
    loaded: dict[str, list] = {kind: [] for kind, _ in _RECORD_FILES.values()}
    for entry in manifest.files:
        path = root / entry.path
        if path.stat().st_size != entry.size_bytes or entry.size_bytes > (
            MAX_PACK_FILE_BYTES
        ):
            raise PackError("file_size_mismatch")
        if file_sha256(path) != entry.sha256:
            raise PackError("file_digest_mismatch")
        if entry.path in _RECORD_FILES:
            kind, model = _RECORD_FILES[entry.path]
            if entry.kind != kind:
                raise PackError("file_kind_mismatch")
            try:
                records = [_validate(model, r) for r in iter_jsonl(path)]
            except (CanonicalError, ValidationError) as error:
                raise PackError("invalid_record") from error
            if len(records) != entry.records:
                raise PackError("record_count_mismatch")
            loaded[kind] = records
        elif entry.kind == "glb":
            try:
                read_glb_json(path)
            except UnsafeContentError as error:
                raise PackError("unsafe_glb") from error
        else:
            raise PackError("unexpected_file_kind")
    identity = {
        "pack_id": manifest.pack_id,
        "audience": manifest.audience,
        "transform_version": manifest.transform_version,
        "category_map_version": manifest.category_map_version,
    }
    if _snapshot(identity, manifest.files) != manifest.snapshot_id:
        raise PackError("snapshot_mismatch")
    glb_paths = {f.path for f in manifest.files if f.kind == "glb"}
    if {a.glb.path for a in loaded["assets"]} != glb_paths:
        raise PackError("asset_glb_mismatch")
    for asset in loaded["assets"]:
        listed_glb = next(f for f in manifest.files if f.path == asset.glb.path)
        if (
            listed_glb.sha256 != asset.glb.sha256
            or listed_glb.size_bytes != asset.glb.size_bytes
        ):
            raise PackError("asset_digest_mismatch")
    _check_bindings(
        loaded["sources"],
        loaded["scenes"],
        loaded["exclusions"],
        loaded["assets"],
        manifest.transform_version,
        manifest.category_map_version,
    )
    check_audience(
        manifest.audience, loaded["sources"], has_assets=bool(loaded["assets"])
    )
    return LoadedPack(
        manifest=manifest,
        sources=tuple(loaded["sources"]),
        scenes=tuple(loaded["scenes"]),
        exclusions=tuple(loaded["exclusions"]),
        assets=tuple(loaded["assets"]),
    )


@dataclass(frozen=True)
class PackStatus:
    """``ready`` with a pack, or ``unavailable`` with a reason code (never a path)."""

    status: str
    reason: str | None = None
    pack: LoadedPack | None = field(default=None, repr=False)


def load_pack(root: Path | None, *, audience: str = "public") -> PackStatus:
    """Load a verified pack for ``audience``; every failure becomes ``unavailable``."""
    if root is None or not str(root).strip():
        return PackStatus("unavailable", "not_configured")
    if audience not in ("local", "public"):
        return PackStatus("unavailable", "invalid_audience")
    root = Path(root)
    if not root.is_dir():
        return PackStatus("unavailable", "pack_not_found")
    try:
        pack = verify_pack(root)
    except PackError as error:
        code = str(error)
        return PackStatus("unavailable", code if _CODE.match(code) else "invalid_pack")
    except OSError:
        return PackStatus("unavailable", "pack_unreadable")
    except (ValueError, TypeError, RecursionError):
        return PackStatus("unavailable", "invalid_pack")
    if audience == "public" and pack.manifest.audience != "public":
        return PackStatus("unavailable", "pack_not_public")
    return PackStatus("ready", None, pack)
