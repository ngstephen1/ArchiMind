"""Review regressions: untrusted packs and interrupted/bounded acquisition."""

import io
import json
import struct

import pytest

from archimind.datasets import safe_io
from archimind.datasets.canonical import canonical_bytes, file_sha256
from archimind.datasets.contracts import PackFile
from archimind.datasets.fixtures import build_synthetic_pack
from archimind.datasets.pack import _snapshot, load_pack
from archimind.datasets.remote import hf_tree
from archimind.datasets.stages import run_stage


class FakeResponse(io.BytesIO):
    def __init__(self, body, status=200, length=True):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Length": str(len(body))} if length else {}


def rewrite_pack(root, name, change):
    """Rehash a structurally valid pack: hashes alone do not prove bindings."""
    path = root / name
    records = [json.loads(line) for line in path.read_text().splitlines()]
    change(records)
    path.write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in records))
    manifest = json.loads((root / "manifest.json").read_text())
    for f in manifest["files"]:
        if f["path"] == name:
            f.update(
                sha256=file_sha256(path),
                size_bytes=path.stat().st_size,
                records=len(records),
            )
    identity = {
        k: manifest[k]
        for k in ("pack_id", "audience", "transform_version", "category_map_version")
    }
    manifest["snapshot_id"] = _snapshot(
        identity,
        [PackFile.model_validate_json(canonical_bytes(f)) for f in manifest["files"]],
    )
    (root / "manifest.json").write_bytes(canonical_bytes(manifest))


@pytest.mark.parametrize(
    "case", ["missing_source", "revision", "digest", "version", "duplicate"]
)
def test_rehashed_pack_cannot_bypass_source_and_version_bindings(tmp_path, case):
    root = tmp_path / "p"
    build_synthetic_pack(root, audience="public")
    if case == "missing_source":
        rewrite_pack(root, "sources.jsonl", lambda r: r.pop(1))
    else:

        def change(records):
            if case == "duplicate":
                records.append(records[0])
            else:
                key, value = {
                    "revision": ("source_revision", "different-revision"),
                    "digest": ("source_sha256", "0" * 64),
                    "version": ("transform_version", "9.0.0"),
                }[case]
                records[0][key] = value

        rewrite_pack(root, "scenes.jsonl", change)
    assert load_pack(root).status == "unavailable"


def test_pack_rejects_symlinked_files(tmp_path):
    root = tmp_path / "p"
    build_synthetic_pack(root)
    path = root / "scenes.jsonl"
    outside = tmp_path / "outside.jsonl"
    path.rename(outside)
    path.symlink_to(outside)
    assert load_pack(root, audience="local").status == "unavailable"


def test_pack_loader_handles_invalid_utf8(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    (root / "manifest.json").write_bytes(b"\xff")
    assert load_pack(root).status == "unavailable"


@pytest.mark.parametrize("response_range", [None, "bytes 0-2/6", "bytes 3-5/9"])
def test_download_rejects_unverified_resume(tmp_path, monkeypatch, response_range):
    monkeypatch.setattr(safe_io, "free_bytes", lambda p: 100 * safe_io.GIB)
    dest = tmp_path / "f"
    (tmp_path / "f.partial").write_bytes(b"abc")
    response = FakeResponse(b"def", status=206)
    if response_range:
        response.headers["Content-Range"] = response_range
    with pytest.raises(safe_io.UnsafeContentError):
        safe_io.bounded_download(
            "https://example.invalid/f", dest, max_bytes=20, opener=lambda *a: response
        )
    assert not dest.exists()


def test_download_does_not_promote_short_response(tmp_path, monkeypatch):
    monkeypatch.setattr(safe_io, "free_bytes", lambda p: 100 * safe_io.GIB)
    response = FakeResponse(b"abc")
    response.headers["Content-Length"] = "6"
    with pytest.raises(safe_io.UnsafeContentError):
        safe_io.bounded_download(
            "https://example.invalid/f",
            tmp_path / "f",
            max_bytes=20,
            opener=lambda *a: response,
        )
    assert not (tmp_path / "f").exists()


def test_capacity_is_checked_during_unknown_length_download(tmp_path, monkeypatch):
    free = iter([100, 100, 10])
    monkeypatch.setattr(safe_io, "free_bytes", lambda p: next(free, 10))
    with pytest.raises(safe_io.CapacityError):
        safe_io.bounded_download(
            "https://example.invalid/f",
            tmp_path / "f",
            max_bytes=20,
            floor_bytes=10,
            chunk=2,
            opener=lambda *a: FakeResponse(b"abcdef", length=False),
        )
    assert not (tmp_path / "f").exists()


@pytest.mark.parametrize("document", [{"buffers": 1}, {"images": [3]}, []])
def test_malformed_glb_json_is_a_controlled_rejection(tmp_path, document):
    payload = json.dumps(document).encode()
    payload += b" " * (-len(payload) % 4)
    data = (
        struct.pack(
            "<IIIII", 0x46546C67, 2, 20 + len(payload), len(payload), 0x4E4F534A
        )
        + payload
    )
    path = tmp_path / "bad.glb"
    path.write_bytes(data)
    with pytest.raises(safe_io.UnsafeContentError):
        safe_io.read_glb_json(path)


@pytest.mark.parametrize("name", ["../outside", "/absolute", "nested/stage"])
def test_stage_name_cannot_escape_root(tmp_path, name):
    with pytest.raises(ValueError):
        run_stage(tmp_path, name, "1", {}, lambda p: pytest.fail("must not build"))


def test_incomplete_hf_inventory_is_not_silently_reported_complete():
    response = FakeResponse(b"[]")
    response.headers["Link"] = '<https://example.invalid/next>; rel="next"'
    with pytest.raises(safe_io.UnsafeContentError, match="Paginated"):
        hf_tree("org/ds", "a" * 40, opener=lambda *a: response)
