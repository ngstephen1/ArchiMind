import io
import json
import tarfile

import pytest

from archimind.datasets.remote import (
    gzip_tar_prefix,
    hf_resolve_url,
    hf_tree,
    kaggle_dataset_view,
    kaggle_download_url,
    kaggle_files,
    kaggle_headers,
)
from archimind.datasets.safe_io import UnsafeContentError

REV = "b606183e56d972f85850125f9191932cbea654c3"


class Response(io.BytesIO):
    status = 200
    headers: dict = {}


def json_opener(pages, log=None):
    def opener(request, timeout):
        if log is not None:
            log.append((request.full_url, request.get_header("Authorization")))
        return Response(json.dumps(pages.pop(0)).encode())

    return opener


def test_hf_tree_records_lfs_digests_and_skips_directories(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_secret")
    log = []
    tree = [
        {"type": "directory", "path": "data"},
        {"type": "file", "path": "data/b.parquet", "size": 5, "lfs": {"oid": "f" * 64}},
        {"type": "file", "path": "README.md", "size": 3},
    ]
    files = hf_tree("org/ds", REV, opener=json_opener([tree], log))
    assert [f.path for f in files] == ["README.md", "data/b.parquet"]
    assert files[1].sha256 == "f" * 64 and files[0].sha256 is None
    assert REV in log[0][0] and log[0][1] == "Bearer hf_secret"


def test_hf_tree_requires_a_pinned_revision():
    with pytest.raises(ValueError):
        hf_tree("org/ds", "main")


def test_hf_resolve_url_is_pinned_and_quoted():
    assert hf_resolve_url("org/ds", REV, "data/a b.json") == (
        f"https://huggingface.co/datasets/org/ds/resolve/{REV}/data/a%20b.json"
    )


def test_kaggle_files_paginates_and_needs_credentials(monkeypatch):
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    with pytest.raises(PermissionError):
        kaggle_files("o/d", opener=json_opener([{}]))
    monkeypatch.setenv("KAGGLE_USERNAME", "u")
    monkeypatch.setenv("KAGGLE_KEY", "k")
    pages = [
        {"datasetFiles": [{"name": "b.zip", "totalBytes": 2}], "nextPageToken": "t"},
        {"datasetFiles": [{"name": "a.json", "totalBytes": 1}]},
    ]
    log = []
    files = kaggle_files("o/d", opener=json_opener(pages, log), sleep=lambda _: None)
    assert [f.path for f in files] == ["a.json", "b.zip"]
    assert "pageToken=t" in log[1][0] and log[0][1].startswith("Basic ")
    assert log[0][0].startswith("https://www.kaggle.com/api/v1/datasets/list/o/d?")


def test_kaggle_headers_bearer_for_new_tokens_basic_for_legacy(monkeypatch):
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    monkeypatch.setenv("KAGGLE_USERNAME", "u")
    monkeypatch.setenv("KAGGLE_KEY", "KGAT_" + "a" * 32)
    assert kaggle_headers()["Authorization"] == "Bearer KGAT_" + "a" * 32
    monkeypatch.setenv("KAGGLE_KEY", "k" * 32)
    assert kaggle_headers()["Authorization"].startswith("Basic ")


def test_kaggle_dataset_view_sends_credentials(monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "u")
    monkeypatch.setenv("KAGGLE_KEY", "k")
    log = []
    info = kaggle_dataset_view(
        "o/d", opener=json_opener([{"ref": "o/d", "totalBytes": 5}], log)
    )
    assert info["ref"] == "o/d" and log[0][1].startswith("Basic ")


def test_listing_size_limit(monkeypatch):
    monkeypatch.setattr("archimind.datasets.remote.MAX_LISTING_BYTES", 10)
    with pytest.raises(UnsafeContentError):
        hf_tree("org/ds", REV, opener=json_opener([[{"type": "file"}] * 5]))


def targz(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def bytes_opener(body: bytes):
    return lambda request, timeout: Response(body)


def test_prefix_lists_complete_small_archive():
    body = targz({"S/h/r.glb": b"g" * 100, "S/h/r/Bed_x_1.glb": b"b" * 50})
    listing = gzip_tar_prefix(
        "https://x/a.tar.gz", max_bytes=10**6, opener=bytes_opener(body)
    )
    assert listing.complete
    assert [m[0] for m in listing.members] == ["S/h/r.glb", "S/h/r/Bed_x_1.glb"]


def test_prefix_stops_at_the_cap_without_error():
    import os

    body = targz({f"S/f{i}.bin": os.urandom(20_000) for i in range(20)})
    listing = gzip_tar_prefix(
        "https://x/a.tar.gz", max_bytes=60_000, opener=bytes_opener(body)
    )
    assert not listing.complete
    assert listing.bytes_read == 60_000
    assert 0 < len(listing.members) < 20


def test_prefix_requires_https():
    with pytest.raises(UnsafeContentError):
        gzip_tar_prefix("http://x/a.tar.gz", max_bytes=10)


def test_kaggle_files_retries_rate_limits_then_gives_up(monkeypatch):
    import email.message
    import urllib.error

    monkeypatch.setenv("KAGGLE_USERNAME", "u")
    monkeypatch.setenv("KAGGLE_KEY", "k")

    def http_error(code, retry_after=None):
        headers = email.message.Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        return urllib.error.HTTPError("https://x", code, "err", headers, None)

    page = {"datasetFiles": [{"name": "a.json", "totalBytes": 1}]}
    responses = [http_error(429, "7"), http_error(503), page]

    def opener(request, timeout):
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return Response(json.dumps(item).encode())

    slept = []
    files = kaggle_files("o/d", opener=opener, sleep=slept.append)
    assert [f.path for f in files] == ["a.json"]
    assert slept == [7.0, 4.0]  # Retry-After honoured, then exponential backoff

    def always_404(request, timeout):
        raise http_error(404)

    with pytest.raises(urllib.error.HTTPError):
        kaggle_files("o/d", opener=always_404, sleep=slept.append)


def test_kaggle_download_url_encodes_subdirectory_slashes():
    assert kaggle_download_url("o/d", "dir/sub file.json") == (
        "https://www.kaggle.com/api/v1/datasets/download/o/d/dir%2Fsub%20file.json"
    )
