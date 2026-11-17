"""Remote inventories without bulk transfer: Hugging Face trees, Kaggle file lists
and a capped, streaming listing of gzip-compressed tar archives.

Hugging Face LFS entries carry the SHA-256 of the file (``lfs.oid``), so a pinned
revision plus that digest fully identifies the bytes to fetch later. Gzip archives
are not seekable: the only bounded access is reading a prefix, which reveals the
members that happen to be stored first, not members chosen by identity.
"""

import base64
import os
import tarfile
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

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
    url: str,
    *,
    headers=None,
    opener: Opener = _default_opener,
    timeout: float = 60.0,
    reject_pagination: bool = False,
):
    if not url.startswith("https://"):
        raise UnsafeContentError("Only https:// requests are allowed")
    request = make_request(url, headers)
    with opener(request, timeout) as response:
        if reject_pagination and 'rel="next"' in response.headers.get("Link", ""):
            raise UnsafeContentError(
                "Paginated tree requires a bounded pagination implementation"
            )
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
    entries = _get_json(
        url, headers=_hf_headers(), opener=opener, reject_pagination=True
    )
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
    """Single-file download endpoint; Kaggle may serve large files zipped."""
    return f"{KAGGLE_API}/datasets/download/{ref}/{urllib.parse.quote(path)}"


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


def kaggle_files(
    ref: str, *, opener: Opener = _default_opener, max_pages: int = 200
) -> list[RemoteFile]:
    """Paginated file listing (requires Kaggle credentials in the environment)."""
    headers = kaggle_headers()
    files, token = [], None
    for _ in range(max_pages):
        query = {"pageSize": "200"} | ({"pageToken": token} if token else {})
        url = f"{KAGGLE_API}/datasets/list/files/{ref}?{urllib.parse.urlencode(query)}"
        page = _get_json(url, headers=headers, opener=opener)
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
