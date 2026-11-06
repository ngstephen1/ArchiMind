import hashlib
import io
import json
import struct
import tarfile
import zipfile

import numpy as np
import pytest

from archimind.datasets import safe_io
from archimind.datasets.fixtures import synthetic_glb_bytes
from archimind.datasets.safe_io import (
    CapacityError,
    ExtractionLimits,
    UnsafeContentError,
    bounded_download,
    load_npy,
    read_glb_json,
    require_capacity,
    safe_extract,
)

URL = "https://example.invalid/file.bin"


class FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, status=200, length=True):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Length": str(len(body))} if length else {}


def opener_for(body: bytes, *, honours_range=True, length=True, log=None):
    def opener(request, timeout):
        rng = request.get_header("Range")
        if log is not None:
            log.append(rng)
        if rng and honours_range:
            start = int(rng.split("=")[1].rstrip("-"))
            return FakeResponse(body[start:], status=206, length=length)
        return FakeResponse(body, status=200, length=length)

    return opener


@pytest.fixture(autouse=True)
def plenty_of_space(monkeypatch):
    monkeypatch.setattr(safe_io, "free_bytes", lambda _path: 100 * safe_io.GIB)


def test_download_verifies_hash_and_renames(tmp_path):
    body = b"x" * 1000
    receipt = bounded_download(
        URL,
        tmp_path / "f.bin",
        max_bytes=2000,
        expected_sha256=hashlib.sha256(body).hexdigest(),
        opener=opener_for(body),
    )
    assert (tmp_path / "f.bin").read_bytes() == body
    assert receipt.size_bytes == 1000 and not receipt.resumed
    assert not (tmp_path / "f.bin.partial").exists()


def test_only_https_is_allowed(tmp_path):
    with pytest.raises(UnsafeContentError):
        bounded_download("http://example.invalid/x", tmp_path / "f", max_bytes=10)


def test_cap_is_enforced_without_content_length(tmp_path):
    with pytest.raises(UnsafeContentError, match="exceeded"):
        bounded_download(
            URL,
            tmp_path / "f",
            max_bytes=10,
            opener=opener_for(b"y" * 50, length=False),
        )
    assert not (tmp_path / "f.partial").exists() and not (tmp_path / "f").exists()


def test_declared_oversize_is_refused_before_reading(tmp_path):
    with pytest.raises(UnsafeContentError, match="Declared"):
        bounded_download(
            URL, tmp_path / "f", max_bytes=10, opener=opener_for(b"z" * 50)
        )


def test_resume_appends_with_range(tmp_path):
    body = bytes(range(256)) * 4
    (tmp_path / "f.partial").write_bytes(body[:300])
    log = []
    receipt = bounded_download(
        URL, tmp_path / "f", max_bytes=5000, opener=opener_for(body, log=log)
    )
    assert log == ["bytes=300-"] and receipt.resumed
    assert (tmp_path / "f").read_bytes() == body


def test_server_ignoring_range_restarts_from_zero(tmp_path):
    body = b"abcdef" * 100
    (tmp_path / "f.partial").write_bytes(b"GARBAGE")
    receipt = bounded_download(
        URL,
        tmp_path / "f",
        max_bytes=5000,
        opener=opener_for(body, honours_range=False),
    )
    assert not receipt.resumed and (tmp_path / "f").read_bytes() == body


def test_hash_mismatch_discards_partial(tmp_path):
    with pytest.raises(UnsafeContentError, match="SHA-256"):
        bounded_download(
            URL,
            tmp_path / "f",
            max_bytes=100,
            expected_sha256="0" * 64,
            opener=opener_for(b"data"),
        )
    assert not (tmp_path / "f.partial").exists() and not (tmp_path / "f").exists()


def test_capacity_floor_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(safe_io, "free_bytes", lambda _p: 5 * safe_io.GIB)
    with pytest.raises(CapacityError):
        require_capacity(
            tmp_path, floor_bytes=4 * safe_io.GIB, needed_bytes=2 * safe_io.GIB
        )
    assert require_capacity(tmp_path, floor_bytes=4 * safe_io.GIB) == 5 * safe_io.GIB


# ---------------------------------------------------------------- archives


def make_zip(path, members):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


def make_tar(path, members, *, symlink=None):
    with tarfile.open(path, "w") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        if symlink:
            info = tarfile.TarInfo(symlink)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            t.addfile(info)
    return path


def test_zip_extracts_regular_files_with_hashes(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {"m/a.obj": b"v 0 0 0", "m/b.mtl": b"x"})
    files = safe_extract(archive, tmp_path / "out")
    assert [f.path for f in files] == ["m/a.obj", "m/b.mtl"]
    assert files[0].sha256 == hashlib.sha256(b"v 0 0 0").hexdigest()
    assert (tmp_path / "out/m/a.obj").read_bytes() == b"v 0 0 0"


@pytest.mark.parametrize(
    "name", ["../evil", "/abs", "C:/x", "a/../../b", "CON.txt", "dir/nul", "a\\b"]
)
def test_tar_rejects_unsafe_names(tmp_path, name):
    archive = make_tar(tmp_path / "a.tar", {name: b"x"})
    with pytest.raises(UnsafeContentError):
        safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_zip_rejects_traversal(tmp_path):
    archive = make_zip(tmp_path / "a.zip", {"../evil.txt": b"x"})
    with pytest.raises(UnsafeContentError):
        safe_extract(archive, tmp_path / "out")


def test_case_insensitive_duplicates_are_rejected(tmp_path):
    archive = make_tar(tmp_path / "a.tar", {"Model.obj": b"1", "model.obj": b"2"})
    with pytest.raises(UnsafeContentError, match="Duplicate"):
        safe_extract(archive, tmp_path / "out")


def test_links_are_rejected(tmp_path):
    archive = make_tar(tmp_path / "a.tar", {"ok.txt": b"1"}, symlink="link")
    with pytest.raises(UnsafeContentError, match="link"):
        safe_extract(archive, tmp_path / "out")


def test_zip_symlink_entries_are_rejected(tmp_path):
    info = zipfile.ZipInfo("link")
    info.external_attr = (0o120777) << 16  # S_IFLNK
    with zipfile.ZipFile(tmp_path / "l.zip", "w") as z:
        z.writestr(info, "/etc/passwd")
    with pytest.raises(UnsafeContentError, match="link"):
        safe_extract(tmp_path / "l.zip", tmp_path / "out")


def test_expansion_bomb_and_limits(tmp_path):
    archive = make_zip(tmp_path / "bomb.zip", {"zeros.bin": b"\0" * 2_000_000})
    with pytest.raises(UnsafeContentError, match="ratio"):
        safe_extract(archive, tmp_path / "out")
    archive = make_tar(tmp_path / "big.tar", {"a": b"1" * 600, "b": b"1" * 600})
    with pytest.raises(UnsafeContentError, match="budget"):
        safe_extract(
            archive,
            tmp_path / "out",
            limits=ExtractionLimits(max_total_bytes=1000, max_ratio=1e9),
        )
    with pytest.raises(UnsafeContentError, match="too many"):
        safe_extract(archive, tmp_path / "out", limits=ExtractionLimits(max_members=1))


def test_failed_extraction_leaves_previous_output_and_no_staging(tmp_path):
    good = make_zip(tmp_path / "good.zip", {"a.txt": b"1"})
    safe_extract(good, tmp_path / "out")
    bad = make_tar(tmp_path / "bad.tar", {"ok": b"1", "../x": b"2"})
    with pytest.raises(UnsafeContentError):
        safe_extract(bad, tmp_path / "out")
    assert (tmp_path / "out/a.txt").read_bytes() == b"1"
    assert not (tmp_path / "out.extracting").exists()


def test_non_archives_are_rejected(tmp_path):
    (tmp_path / "x.bin").write_bytes(b"not an archive")
    with pytest.raises(UnsafeContentError):
        safe_extract(tmp_path / "x.bin", tmp_path / "out")


# ---------------------------------------------------------------- NPY


def test_numeric_npy_loads(tmp_path):
    np.save(tmp_path / "p.npy", np.zeros((10, 3), dtype="<f4"))
    assert load_npy(tmp_path / "p.npy", ndim=2).shape == (10, 3)


def test_object_arrays_are_never_unpickled(tmp_path):
    np.save(tmp_path / "o.npy", np.array([{"a": 1}], dtype=object), allow_pickle=True)
    with pytest.raises(UnsafeContentError, match="dtype"):
        load_npy(tmp_path / "o.npy")


@pytest.mark.parametrize(
    "array,kwargs,match",
    [
        (np.zeros(4, dtype="<c8"), {}, "dtype"),
        (np.zeros((2, 2), dtype="<f4"), {"ndim": 3}, "dimensions"),
        (np.zeros(100, dtype="<f4"), {"max_elements": 10}, "elements"),
        (np.array([np.nan], dtype="<f8"), {}, "non-finite"),
        (np.zeros(1000, dtype="<f8"), {"max_bytes": 100}, "byte"),
    ],
)
def test_npy_limits(tmp_path, array, kwargs, match):
    np.save(tmp_path / "a.npy", array)
    with pytest.raises(UnsafeContentError, match=match):
        load_npy(tmp_path / "a.npy", **kwargs)


def test_malformed_npy_is_rejected(tmp_path):
    (tmp_path / "bad.npy").write_bytes(b"\x93NUMPY garbage")
    with pytest.raises(UnsafeContentError):
        load_npy(tmp_path / "bad.npy")


# ---------------------------------------------------------------- GLB


def glb_with(document: dict) -> bytes:
    payload = json.dumps(document).encode()
    payload += b" " * (-len(payload) % 4)
    return (
        struct.pack("<III", 0x46546C67, 2, 20 + len(payload))
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
    )


def test_synthetic_glb_is_valid(tmp_path):
    (tmp_path / "a.glb").write_bytes(synthetic_glb_bytes())
    assert read_glb_json(tmp_path / "a.glb")["asset"]["version"] == "2.0"


@pytest.mark.parametrize(
    "document",
    [
        {"asset": {"version": "2.0"}, "buffers": [{"uri": "https://x/y.bin"}]},
        {"asset": {"version": "2.0"}, "images": [{"uri": "../tex.png"}]},
        {"asset": {"version": "2.0"}, "extensionsRequired": ["KHR_draco"]},
    ],
)
def test_glb_external_references_and_required_extensions_rejected(tmp_path, document):
    (tmp_path / "a.glb").write_bytes(glb_with(document))
    with pytest.raises(UnsafeContentError):
        read_glb_json(tmp_path / "a.glb")


def test_glb_container_errors(tmp_path):
    good = synthetic_glb_bytes()
    cases = {
        "magic": b"XXXX" + good[4:],
        "length": good[:8] + struct.pack("<I", len(good) + 4) + good[12:],
        "truncated": good[:10],
    }
    for name, data in cases.items():
        (tmp_path / f"{name}.glb").write_bytes(data)
        with pytest.raises(UnsafeContentError):
            read_glb_json(tmp_path / f"{name}.glb")


def test_credentials_are_not_forwarded_on_redirect():
    from archimind.datasets.safe_io import make_request

    request = make_request(URL, {"Authorization": "Bearer x", "Range": "bytes=1-"})
    assert request.get_header("Authorization") == "Bearer x"
    assert "Authorization" not in request.headers  # ordinary headers are redirected
    assert request.headers["Range"] == "bytes=1-"
    assert "Authorization" in request.unredirected_hdrs


def test_existing_file_with_expected_hash_is_not_refetched(tmp_path):
    body = b"cached-bytes"
    (tmp_path / "f").write_bytes(body)

    def never(request, timeout):
        raise AssertionError("network must not be used")

    receipt = bounded_download(
        URL,
        tmp_path / "f",
        max_bytes=100,
        expected_sha256=hashlib.sha256(body).hexdigest(),
        opener=never,
    )
    assert receipt.cached and receipt.size_bytes == len(body)
    (tmp_path / "f").write_bytes(b"stale")
    receipt = bounded_download(
        URL,
        tmp_path / "f",
        max_bytes=100,
        expected_sha256=hashlib.sha256(body).hexdigest(),
        opener=opener_for(body),
    )
    assert not receipt.cached and (tmp_path / "f").read_bytes() == body
