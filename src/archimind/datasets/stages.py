"""Content-addressed, resumable stages and atomic directory sync (Drive checkpoints).

A stage's key is the digest of its name, code version and inputs. Its outputs live
in ``<root>/<name>/<key>/`` next to a ``_COMPLETE`` file listing every output and
its SHA-256. A stage is skipped only when that file exists *and* every listed output
still verifies, so a half-copied checkpoint is redone instead of trusted.
"""

import os
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from archimind.datasets.canonical import (
    atomic_write_bytes,
    canonical_bytes,
    digest,
    file_sha256,
    strict_loads,
)
from archimind.datasets.contracts import check_relative_path

COMPLETE = "_COMPLETE"


def stage_key(name: str, version: str, inputs: Mapping) -> str:
    return digest({"name": name, "version": version, "inputs": inputs})


def _inventory(directory: Path) -> dict[str, dict]:
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != COMPLETE:
            rel = path.relative_to(directory).as_posix()
            files[rel] = {
                "size_bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
    return files


def verify_stage(directory: Path) -> bool:
    marker = directory / COMPLETE
    if not marker.is_file():
        return False
    try:
        recorded = strict_loads(marker.read_bytes())["files"]
    except (ValueError, KeyError, TypeError):
        return False
    return recorded == _inventory(directory)


@dataclass(frozen=True)
class StageResult:
    name: str
    key: str
    directory: Path
    skipped: bool


def run_stage(
    root: Path,
    name: str,
    version: str,
    inputs: Mapping,
    build: Callable[[Path], None],
) -> StageResult:
    """Run ``build(out_dir)`` unless an identical verified result already exists."""
    check_relative_path(name)
    if "/" in name:
        raise ValueError("Stage name must be a single portable component")
    key = stage_key(name, version, inputs)
    final = Path(root) / name / key
    if verify_stage(final):
        return StageResult(name, key, final, skipped=True)
    work = final.with_name(key + ".work")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        build(work)
        marker = {"name": name, "version": version, "key": key, "inputs": inputs}
        marker["files"] = _inventory(work)
        atomic_write_bytes(work / COMPLETE, canonical_bytes(marker))
        if final.exists():
            shutil.rmtree(final)
        os.replace(work, final)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    return StageResult(name, key, final, skipped=False)


@dataclass(frozen=True)
class SyncReport:
    copied: int
    unchanged: int
    bytes_copied: int


def sync_tree(src: Path, dst: Path) -> SyncReport:
    """Copy new or changed files from ``src`` to ``dst`` atomically, never deleting.

    Files are compared by size, then SHA-256 (Drive does not keep mtimes reliably).
    Each copy goes to ``.<name>.partial`` and is renamed only after it is complete.
    Leftover ``.partial`` files and unfinished ``*.work`` stage directories are
    never copied.
    """
    src, dst = Path(src), Path(dst)
    if not src.is_dir():
        return SyncReport(0, 0, 0)
    copied = unchanged = total = 0
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if not path.is_file() or path.name.endswith(".partial"):
            continue
        if any(part.endswith((".work", ".extracting")) for part in rel.parts[:-1]):
            continue  # unfinished stage or extraction; never checkpointed
        target = dst / rel
        size = path.stat().st_size
        if (
            target.is_file()
            and target.stat().st_size == size
            and file_sha256(target) == file_sha256(path)
        ):
            unchanged += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f".{target.name}.partial")
        shutil.copyfile(path, partial)
        os.replace(partial, target)
        copied += 1
        total += size
    return SyncReport(copied, unchanged, total)
