"""Remote inventories without bulk transfer: Hugging Face trees, Kaggle file lists
and a capped, streaming listing of gzip-compressed tar archives.

Hugging Face LFS entries carry the SHA-256 of the file (``lfs.oid``), so a pinned
revision plus that digest fully identifies the bytes to fetch later. Gzip archives
are not seekable: the only bounded access is reading a prefix, which reveals the
members that happen to be stored first, not members chosen by identity.
"""

import base64
import os
import shutil
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from archimind.datasets.canonical import strict_loads
from archimind.datasets.safe_io import UnsafeContentError, make_request

HF_API = "https://huggingface.co/api/datasets"
HF_RESOLVE = "https://huggingface.co/datasets"
KAGGLE_API = "https://www.kaggle.com/api/v1"
MAX_LISTING_BYTES = 8 * 1024 * 1024

Opener = Callable[[urllib.request.Request, float], object]


def _default_opener(request, timeout):
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (https only)


def _get_json(
    url: str, *, headers=None, opener: Opener = _default_opener, timeout: float = 60.0
):
    if not url.startswith("https://"):
        raise UnsafeContentError("Only https:// requests are allowed")
    request = make_request(url, headers)
    with opener(request, timeout) as response:
        data = response.read(MAX_LISTING_BYTES + 1)
    if len(data) > MAX_LISTING_BYTES:
        raise UnsafeContentError("Listing exceeds the size limit")
    return strict_loads(data)


def _hf_headers() -> dict:
    token = os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


@dataclass(frozen=True)
class RemoteFile:
    path: str
    size_bytes: int
    sha256: str | None  # None when the host does not publish a digest


def hf_dataset_revision(repo: str, *, opener: Opener = _default_opener) -> dict:
    info = _get_json(f"{HF_API}/{repo}", headers=_hf_headers(), opener=opener)
    return {
        "repo": repo,
        "revision": info["sha"],
        "gated": info.get("gated"),
        "license": (info.get("cardData") or {}).get("license"),
        "last_modified": info.get("lastModified"),
    }


def hf_tree(
    repo: str,
    revision: str,
    *,
    opener: Opener = _default_opener,
    max_entries: int = 5000,
) -> list[RemoteFile]:
    """Recursive file listing of a dataset at an exact revision."""
    if len(revision) != 40:
        raise ValueError("Pin a full 40-character revision")
    url = f"{HF_API}/{repo}/tree/{revision}?recursive=true"
    entries = _get_json(url, headers=_hf_headers(), opener=opener)
    if not isinstance(entries, list) or len(entries) > max_entries:
        raise UnsafeContentError("Unexpected Hugging Face tree listing")
    files = []
    for e in entries:
        if e.get("type") != "file":
            continue
        lfs = e.get("lfs") or {}
        files.append(
            RemoteFile(
                path=e["path"], size_bytes=int(e.get("size", 0)), sha256=lfs.get("oid")
            )
        )
    return sorted(files, key=lambda f: f.path)


def hf_resolve_url(repo: str, revision: str, path: str) -> str:
    return f"{HF_RESOLVE}/{repo}/resolve/{revision}/{urllib.parse.quote(path)}"


def kaggle_download_url(ref: str, path: str) -> str:
    """Single-file download endpoint; Kaggle may serve large files zipped.

    The file path is one URL segment, so ``/`` inside it must be ``%2F``: the
    unencoded form 404s for files in subdirectories.
    """
    return f"{KAGGLE_API}/datasets/download/{ref}/{urllib.parse.quote(path, safe='')}"


def kaggle_headers() -> dict:
    """Kaggle auth headers, read from the environment by name.

    Newer ``KGAT_`` API tokens use Bearer auth; legacy 32-hex keys use Basic
    ``username:key``. Either way the value is never printed.
    """
    key = os.environ.get("KAGGLE_KEY") or os.environ.get("KAGGLE_API_TOKEN") or ""
    key = key.strip()
    user = (os.environ.get("KAGGLE_USERNAME") or "").strip()
    if key.startswith("KGAT_"):
        return {"Authorization": f"Bearer {key}"}
    if not user or not key:
        raise PermissionError("KAGGLE_USERNAME and KAGGLE_KEY are required")
    token = base64.b64encode(f"{user}:{key}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def kaggle_dataset_view(ref: str, *, opener: Opener = _default_opener) -> dict:
    info = _get_json(
        f"{KAGGLE_API}/datasets/view/{ref}", headers=kaggle_headers(), opener=opener
    )
    return {
        "ref": info.get("ref"),
        "version": info.get("currentVersionNumber"),
        "total_bytes": info.get("totalBytes"),
        "license": info.get("licenseName"),
        "last_updated": info.get("lastUpdated"),
    }


RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


def _retry_delay(error: urllib.error.HTTPError, attempt: int, cap: float) -> float:
    retry_after = (error.headers.get("Retry-After") or "") if error.headers else ""
    if retry_after.strip().isdigit():
        return min(cap, float(retry_after.strip()))
    return min(cap, 2.0 * 2**attempt)


def _get_json_retrying(
    url: str,
    *,
    headers,
    opener: Opener,
    sleep: Callable[[float], None],
    retries: int = 8,
    max_delay: float = 120.0,
):
    """``_get_json`` that backs off on rate limits and transient server errors,
    honouring ``Retry-After`` when the server sends one."""
    for attempt in range(retries + 1):
        try:
            return _get_json(url, headers=headers, opener=opener)
        except urllib.error.HTTPError as error:
            if error.code not in RETRY_STATUS or attempt == retries:
                raise
            sleep(_retry_delay(error, attempt, max_delay))
    raise AssertionError("unreachable")


def kaggle_files(
    ref: str,
    *,
    opener: Opener = _default_opener,
    max_pages: int = 2000,
    page_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> list[RemoteFile]:
    """Paginated file listing (requires Kaggle credentials in the environment).

    Endpoint is ``/datasets/list/{owner}/{slug}`` (``/datasets/list/files/...``
    404s). The server caps ``pageSize`` at 200, so large datasets such as
    3D-FUTURE need hundreds of pages: requests are paced by ``page_delay`` and
    429/5xx responses are retried with backoff.
    """
    headers = kaggle_headers()
    files, token = [], None
    for page_number in range(max_pages):
        if page_number:
            sleep(page_delay)
        query = {"pageSize": "200"} | ({"pageToken": token} if token else {})
        url = f"{KAGGLE_API}/datasets/list/{ref}?{urllib.parse.urlencode(query)}"
        page = _get_json_retrying(url, headers=headers, opener=opener, sleep=sleep)
        for f in page.get("datasetFiles") or []:
            files.append(
                RemoteFile(
                    path=f["name"], size_bytes=int(f.get("totalBytes", 0)), sha256=None
                )
            )
        token = page.get("nextPageToken")
        if not token:
            return sorted(files, key=lambda f: f.path)
    raise UnsafeContentError("Kaggle listing exceeded the page limit")


class _CappedReader:
    """File-like wrapper that stops after ``limit`` bytes instead of failing."""

    def __init__(self, raw, limit: int):
        self.raw, self.limit, self.read_bytes = raw, limit, 0

    def read(self, size: int = -1) -> bytes:
        remaining = self.limit - self.read_bytes
        if remaining <= 0:
            return b""
        size = remaining if size is None or size < 0 else min(size, remaining)
        data = self.raw.read(size)
        self.read_bytes += len(data)
        return data


@dataclass(frozen=True)
class PrefixListing:
    url: str
    bytes_read: int
    complete: bool  # True only if the archive ended within the cap
    members: tuple[tuple[str, int, str], ...]  # (name, size, type)


def gzip_tar_prefix(
    url: str,
    *,
    max_bytes: int,
    max_members: int = 100_000,
    headers=None,
    opener: Opener = _default_opener,
    timeout: float = 120.0,
) -> PrefixListing:
    """List members of a ``.tar.gz`` (or the first part of a split one) from a
    streamed, capped prefix. Nothing is written to disk and no member is opened."""
    if not url.startswith("https://"):
        raise UnsafeContentError("Only https:// requests are allowed")
    request = make_request(url, headers)
    members: list[tuple[str, int, str]] = []
    complete = False
    with opener(request, timeout) as response:
        capped = _CappedReader(response, max_bytes)
        try:
            with tarfile.open(fileobj=capped, mode="r|gz") as archive:
                for info in archive:
                    kind = (
                        "file" if info.isreg() else "dir" if info.isdir() else "other"
                    )
                    members.append((info.name, info.size, kind))
                    if len(members) >= max_members:
                        break
                else:
                    complete = capped.read_bytes < max_bytes
        except (tarfile.ReadError, EOFError, OSError):
            complete = False  # the cap cut the stream mid-member: expected
    return PrefixListing(
        url=url, bytes_read=capped.read_bytes, complete=complete, members=tuple(members)
    )


@dataclass(frozen=True)
class SelectedMembers:
    url: str
    bytes_read: int
    files: tuple  # SourceFile records, sorted by path
    missing: tuple[str, ...]  # wanted names not found before the cap


def gzip_tar_select(
    url: str,
    dest: Path,
    wanted: Mapping[str, int],
    *,
    max_bytes: int,
    max_member_bytes: int = 64 * 1024 * 1024,
    headers=None,
    opener: Opener = _default_opener,
    timeout: float = 120.0,
) -> SelectedMembers:
    """Stream a ``.tar.gz`` prefix and keep only the exactly named members.

    ``wanted`` maps member names (from an earlier prefix listing) to their expected
    sizes. Streaming stops as soon as every wanted member is written, or at
    ``max_bytes`` of compressed input. Every name is checked as a portable relative
    path, every member must be a regular file of the listed size, and nothing is
    written outside ``dest``. Files land in a staging directory that replaces
    ``dest`` only when the stream ends without error.
    """
    from archimind.datasets.canonical import file_sha256
    from archimind.datasets.contracts import SourceFile, check_relative_path

    if not url.startswith("https://"):
        raise UnsafeContentError("Only https:// requests are allowed")
    for name, size in wanted.items():
        try:
            check_relative_path(name)
        except ValueError as error:
            raise UnsafeContentError(f"Unsafe wanted member: {error}") from None
        if not isinstance(size, int) or not 0 <= size <= max_member_bytes:
            raise UnsafeContentError(f"Wanted member {name} exceeds its size limit")
    if len({n.casefold() for n in wanted}) != len(wanted):
        raise UnsafeContentError("Wanted members collide case-insensitively")
    dest = Path(dest)
    staging = dest.with_name(dest.name + ".selecting")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    remaining = dict(wanted)
    records = []
    request = make_request(url, headers)
    try:
        with opener(request, timeout) as response:
            capped = _CappedReader(response, max_bytes)
            try:
                with tarfile.open(fileobj=capped, mode="r|gz") as archive:
                    for info in archive:
                        if info.name not in remaining:
                            continue
                        if not info.isreg() or info.size != remaining[info.name]:
                            raise UnsafeContentError(
                                f"{info.name} is not a regular file of the listed size"
                            )
                        target = staging / info.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source = archive.extractfile(info)
                        with source, open(target, "wb") as out:
                            written = 0
                            while block := source.read(1024 * 1024):
                                written += len(block)
                                if written > info.size:
                                    raise UnsafeContentError("Member overran its size")
                                out.write(block)
                        if written != info.size:
                            raise UnsafeContentError(f"{info.name} was truncated")
                        records.append(
                            SourceFile(
                                path=info.name,
                                size_bytes=written,
                                sha256=file_sha256(target),
                            )
                        )
                        del remaining[info.name]
                        if not remaining:
                            break
            except (tarfile.ReadError, EOFError, OSError):
                pass  # the cap cut the stream: whatever is still wanted is reported
        if dest.exists():
            shutil.rmtree(dest)
        os.replace(staging, dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return SelectedMembers(
        url=url,
        bytes_read=capped.read_bytes,
        files=tuple(sorted(records, key=lambda r: r.path)),
        missing=tuple(sorted(remaining)),
    )
