"""Bounded downloads, safe archive extraction, numeric NPY loading and GLB headers.

Nothing here executes downloaded content. Every reader enforces explicit byte,
member and shape limits instead of trusting sizes declared by the file or server.
"""

import json
import os
import re
import shutil
import stat
import struct
import tarfile
import urllib.request
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from archimind.datasets.canonical import CanonicalError, file_sha256, strict_loads
from archimind.datasets.contracts import SourceFile, check_relative_path

GIB = 1024**3


class CapacityError(RuntimeError):
    """Free disk would fall below the reserved floor. Never resumed automatically."""


class UnsafeContentError(ValueError):
    """Input violates a safety or size rule."""


def free_bytes(path: Path) -> int:
    probe = Path(path)
    while not probe.exists():
        probe = probe.parent
    return shutil.disk_usage(probe).free


def require_capacity(path: Path, *, floor_bytes: int, needed_bytes: int = 0) -> int:
    """Raise :class:`CapacityError` unless ``needed_bytes`` fit above the floor."""
    available = free_bytes(path)
    if available - needed_bytes < floor_bytes:
        raise CapacityError(
            f"Free {available} B minus needed {needed_bytes} B is below the "
            f"{floor_bytes} B floor"
        )
    return available


# ---------------------------------------------------------------- downloads


@dataclass(frozen=True)
class DownloadReceipt:
    url: str
    path: str
    size_bytes: int
    sha256: str
    resumed: bool
    cached: bool = False  # already present with the expected SHA-256; not fetched


Opener = Callable[[urllib.request.Request, float], object]
SENSITIVE_HEADERS = frozenset({"authorization", "cookie"})


def make_request(url: str, headers: Mapping[str, str] | None = None):
    """Build a request whose credentials are never forwarded on redirects.

    Hugging Face and Kaggle answer downloads with redirects to storage hosts.
    ``urllib`` copies ordinary headers to the redirected request, so credentials
    are added as *unredirected* headers and stay with the original host only.
    """
    request = urllib.request.Request(url)
    for name, value in (headers or {}).items():
        if name.lower() in SENSITIVE_HEADERS:
            request.add_unredirected_header(name, value)
        else:
            request.add_header(name, value)
    return request


def _default_opener(request: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (https only)


def bounded_download(
    url: str,
    dest: Path,
    *,
    max_bytes: int,
    timeout_s: float = 60.0,
    expected_sha256: str | None = None,
    headers: Mapping[str, str] | None = None,
    floor_bytes: int = 4 * GIB,
    opener: Opener = _default_opener,
    chunk: int = 1024 * 1024,
) -> DownloadReceipt:
    """Stream ``url`` to ``dest`` with a hard byte cap and resumable partials.

    A ``dest.partial`` file is resumed with a Range request. A server that ignores
    Range (status 200) restarts the file from zero. The cap is enforced on bytes
    actually received, so a missing or false Content-Length cannot exceed it.
    ``headers`` may carry an auth token; it is never stored in the receipt.
    """
    if not url.startswith("https://"):
        raise UnsafeContentError("Only https:// downloads are allowed")
    if max_bytes <= 0 or chunk <= 0 or floor_bytes < 0:
        raise UnsafeContentError("Invalid download budget")
    dest = Path(dest)
    if expected_sha256 is not None and dest.is_file():
        if file_sha256(dest) == expected_sha256:
            size = dest.stat().st_size
            if size > max_bytes:
                raise UnsafeContentError("Cached file exceeds the byte budget")
            return DownloadReceipt(url, dest.name, size, expected_sha256, False, True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > max_bytes:
        partial.unlink()
        offset = 0
    request = make_request(url, headers)
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    with opener(request, timeout_s) as response:
        status = getattr(response, "status", 200)
        if status not in (200, 206):
            raise UnsafeContentError(f"Unexpected HTTP status {status}")
        resumed = bool(offset) and status == 206
        total = None
        if status == 206:
            match = re.fullmatch(
                r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", "")
            )
            if not match:
                raise UnsafeContentError("Missing or invalid Content-Range")
            start, end, total = map(int, match.groups())
            if start != offset or end < start or end + 1 != total or total > max_bytes:
                raise UnsafeContentError("Inconsistent Content-Range")
        if not resumed:
            offset = 0
        declared = response.headers.get("Content-Length")
        if declared is not None and declared.isdigit():
            if offset + int(declared) > max_bytes:
                raise UnsafeContentError("Declared size exceeds the byte budget")
            require_capacity(
                dest.parent, floor_bytes=floor_bytes, needed_bytes=int(declared)
            )
        else:
            require_capacity(dest.parent, floor_bytes=floor_bytes)
        received = offset
        with open(partial, "ab" if resumed else "wb") as handle:
            while block := response.read(chunk):
                received += len(block)
                if received > max_bytes:
                    handle.close()
                    partial.unlink()
                    raise UnsafeContentError("Download exceeded the byte budget")
                require_capacity(
                    dest.parent, floor_bytes=floor_bytes, needed_bytes=len(block)
                )
                handle.write(block)
    if (
        declared is not None
        and declared.isdigit()
        and received - offset != int(declared)
    ):
        raise UnsafeContentError("Incomplete response body")
    if total is not None and received != total:
        raise UnsafeContentError("Incomplete ranged response")
    digest_hex = file_sha256(partial)
    if expected_sha256 is not None and digest_hex != expected_sha256:
        partial.unlink()
        raise UnsafeContentError("Downloaded bytes do not match the expected SHA-256")
    os.replace(partial, dest)
    return DownloadReceipt(url, dest.name, received, digest_hex, resumed)


# ---------------------------------------------------------------- archives


@dataclass(frozen=True)
class ExtractionLimits:
    max_members: int = 10_000
    max_total_bytes: int = 2 * GIB
    max_member_bytes: int = 512 * 1024 * 1024
    max_ratio: float = 200.0  # expanded / compressed, per archive


def _member_path(name: str) -> str:
    try:
        return check_relative_path(name.rstrip("/"))
    except ValueError as error:
        raise UnsafeContentError(f"Unsafe archive path: {error}") from None


def _copy_bounded(src, dst_path: Path, limit: int) -> int:
    written = 0
    with open(dst_path, "wb") as out:
        while block := src.read(1024 * 1024):
            written += len(block)
            if written > limit:
                raise UnsafeContentError("Archive member exceeds its size limit")
            out.write(block)
    return written


def safe_extract(
    archive: Path,
    dest: Path,
    *,
    limits: ExtractionLimits = ExtractionLimits(),
    floor_bytes: int = 4 * GIB,
) -> tuple[SourceFile, ...]:
    """Extract regular files only, validating every member before writing any.

    Rejects traversal, absolute or drive paths, backslashes, Windows-reserved names,
    case-insensitive duplicates, links, devices and expansion bombs. Sizes are
    counted while writing, never trusted from the archive header alone.
    """
    archive = Path(archive)
    dest = Path(dest)
    compressed = archive.stat().st_size
    if zipfile.is_zipfile(archive):
        members = _zip_members(archive)
    elif tarfile.is_tarfile(archive):
        members = _tar_members(archive)
    else:
        raise UnsafeContentError("Unsupported archive format")
    if len(members) > limits.max_members:
        raise UnsafeContentError("Archive has too many members")
    seen: set[str] = set()
    declared_total = 0
    for name, size in members:
        key = name.casefold()
        if key in seen:
            raise UnsafeContentError("Duplicate archive path")
        seen.add(key)
        declared_total += size
    if declared_total > limits.max_total_bytes:
        raise UnsafeContentError("Archive expands beyond the byte budget")
    if compressed and declared_total / compressed > limits.max_ratio:
        raise UnsafeContentError("Archive compression ratio looks like a bomb")
    require_capacity(dest, floor_bytes=floor_bytes, needed_bytes=declared_total)

    staging = dest.with_name(dest.name + ".extracting")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    total = 0
    records = []
    try:
        opened = (
            zipfile.ZipFile(archive)
            if zipfile.is_zipfile(archive)
            else tarfile.open(archive)
        )
        with opened as handle:
            if isinstance(handle, zipfile.ZipFile):
                index = {i.filename.rstrip("/"): i for i in handle.infolist()}
            else:
                index = {i.name.rstrip("/"): i for i in handle.getmembers()}
            for name, _ in members:
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                remaining = min(limits.max_member_bytes, limits.max_total_bytes - total)
                if isinstance(handle, zipfile.ZipFile):
                    src = handle.open(index[name])
                else:
                    src = handle.extractfile(index[name])
                with src:
                    total += _copy_bounded(src, target, remaining)
                records.append(
                    SourceFile(
                        path=name,
                        size_bytes=target.stat().st_size,
                        sha256=file_sha256(target),
                    )
                )
        if dest.exists():
            shutil.rmtree(dest)
        os.replace(staging, dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return tuple(sorted(records, key=lambda r: r.path))


def _zip_members(archive: Path) -> list[tuple[str, int]]:
    result = []
    with zipfile.ZipFile(archive) as handle:
        for info in handle.infolist():
            mode = info.external_attr >> 16
            if info.is_dir():
                _member_path(info.filename)
                continue
            file_type = stat.S_IFMT(mode)  # 0 when the archiver stored no type
            if file_type and file_type != stat.S_IFREG:
                raise UnsafeContentError("Archive contains a link or special file")
            if info.flag_bits & 0x1:
                raise UnsafeContentError("Encrypted archive members are not supported")
            result.append((_member_path(info.filename), info.file_size))
    return result


def _tar_members(archive: Path) -> list[tuple[str, int]]:
    result = []
    with tarfile.open(archive) as handle:
        for info in handle.getmembers():
            if info.isdir():
                _member_path(info.name)
                continue
            if not info.isreg():
                raise UnsafeContentError("Archive contains a link or special file")
            result.append((_member_path(info.name), info.size))
    return result


# ---------------------------------------------------------------- NPY


def load_npy(
    path: Path,
    *,
    allowed_dtypes: tuple[str, ...] = ("<f4", "<f8", "<i4", "<i8", "|u1", "<u2"),
    max_bytes: int = 256 * 1024 * 1024,
    max_elements: int = 50_000_000,
    ndim: int | None = None,
):
    """Load a numeric array after validating its header; pickles are never allowed."""
    import numpy as np  # numpy ships with shapely; imported lazily on purpose
    from numpy.lib import format as npy_format

    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise UnsafeContentError("NPY file exceeds the byte limit")
    with open(path, "rb") as handle:
        try:
            version = npy_format.read_magic(handle)
            if version == (1, 0):
                shape, _, dtype = npy_format.read_array_header_1_0(handle)
            elif version == (2, 0):
                shape, _, dtype = npy_format.read_array_header_2_0(handle)
            else:
                raise UnsafeContentError("Unsupported NPY version")
        except ValueError as error:
            raise UnsafeContentError("Malformed NPY header") from error
    if dtype.hasobject or dtype.str not in allowed_dtypes:
        raise UnsafeContentError(f"NPY dtype {dtype.str} is not allowed")
    if ndim is not None and len(shape) != ndim:
        raise UnsafeContentError("NPY has an unexpected number of dimensions")
    elements = 1
    for dim in shape:
        elements *= dim
    if elements > max_elements:
        raise UnsafeContentError("NPY has too many elements")
    array = np.load(path, allow_pickle=False, mmap_mode=None)
    if not np.all(np.isfinite(array)) and array.dtype.kind == "f":
        raise UnsafeContentError("NPY contains non-finite values")
    return array


# ---------------------------------------------------------------- GLB

GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A


def read_glb_json(
    path: Path, *, max_bytes: int = 15 * 1024 * 1024, max_json_bytes: int = 4 * 1024**2
) -> dict:
    """Validate the GLB container and return its JSON chunk.

    Rejects external buffer/image URIs (only embedded data is allowed), so a reference
    asset can never trigger a network or filesystem fetch when it is rendered.
    """
    path = Path(path)
    size = path.stat().st_size
    if size > max_bytes:
        raise UnsafeContentError("GLB exceeds the byte limit")
    with open(path, "rb") as handle:
        header = handle.read(12)
        if len(header) != 12:
            raise UnsafeContentError("Truncated GLB header")
        magic, version, length = struct.unpack("<III", header)
        if magic != GLB_MAGIC or version != 2 or length != size:
            raise UnsafeContentError("Not a self-consistent glTF 2.0 binary")
        chunk_header = handle.read(8)
        if len(chunk_header) != 8:
            raise UnsafeContentError("Truncated GLB chunk")
        chunk_len, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != JSON_CHUNK or chunk_len > max_json_bytes or chunk_len % 4:
            raise UnsafeContentError("Invalid GLB JSON chunk")
        if 20 + chunk_len > size:
            raise UnsafeContentError("Truncated GLB JSON chunk")
        try:
            document = strict_loads(handle.read(chunk_len).rstrip(b" "))
        except CanonicalError as error:
            raise UnsafeContentError("Invalid GLB JSON") from error
        while handle.tell() < size:
            header = handle.read(8)
            if len(header) != 8:
                raise UnsafeContentError("Truncated GLB chunk")
            length, _ = struct.unpack("<II", header)
            if length % 4 or handle.tell() + length > size:
                raise UnsafeContentError("Invalid GLB chunk length")
            handle.seek(length, 1)
    if not isinstance(document, dict):
        raise UnsafeContentError("GLB JSON must be an object")
    for kind in ("buffers", "images"):
        items = document.get(kind, [])
        if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
            raise UnsafeContentError(f"GLB {kind} must be an array of objects")
        for item in items:
            uri = item.get("uri")
            if uri is not None:
                raise UnsafeContentError(f"GLB {kind} must be embedded, not URIs")
    if document.get("extensionsRequired"):
        raise UnsafeContentError(
            "GLB requires extensions: " + json.dumps(document["extensionsRequired"])
        )
    return document
