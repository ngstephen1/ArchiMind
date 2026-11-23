import hashlib
import json
import runpy
import struct
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def test_edited_photographs_must_match_the_packed_proof(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    api = runpy.run_path(str(SCRIPTS / "package_town_release.py"))
    board = {"home_id": "home", "revision": 2}
    proof = {"manifest_sha256": "r2", "files": {"home.blend": "native"}}
    shots = []
    for name in api["VIEWS"]:
        # The packager checks the published header and bytes, while Blender
        # and the independent image inspection own actual decode and appearance.
        header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR"
        data = header + struct.pack(">II", 1920, 1080)
        (tmp_path / name).write_bytes(data)
        shots.append({"file": name, "sha256": digest(data)})
    sources = {}
    for name in api["NOTICES"]:
        data = name.encode()
        (tmp_path / name).write_bytes(data)
        sources[name] = digest(data)
    receipt = tmp_path / "eye-view-receipt.json"
    eyes = {
        "home_id": "home",
        "revision": 2,
        "manifest_sha256": "r2",
        "camera_manifest_sha256": "r1",
        "proof_blend_sha256": "native",
        "resolution": [1920, 1080],
        "shots": shots,
        "source_notices": sources,
    }
    receipt.write_text(json.dumps(eyes))
    files = api["check_photos"](tmp_path, board, proof, "r1")
    assert files["salon-overview.png"].is_file()

    eyes["proof_blend_sha256"] = "other-scene"
    receipt.write_text(json.dumps(eyes))
    with pytest.raises(ValueError, match="approved edited scene"):
        api["check_photos"](tmp_path, board, proof, "r1")

    eyes["proof_blend_sha256"] = "native"
    path = tmp_path / "bedroom-desk.png"
    data = path.read_bytes()[:16] + struct.pack(">II", 960, 540)
    path.write_bytes(data)
    shots[1]["sha256"] = digest(data)
    receipt.write_text(json.dumps(eyes))
    with pytest.raises(ValueError, match="1920 × 1080 PNG"):
        api["check_photos"](tmp_path, board, proof, "r1")


def test_book_receipt_must_bind_the_project_photos_and_inspected_pages(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    api = runpy.run_path(str(SCRIPTS / "package_town_release.py"))
    monkeypatch.setattr("subprocess.check_output", lambda *args, **kwargs: "Pages: 2\n")
    photo_paths = {}
    for name in api["VIEWS"]:
        path = tmp_path / name
        path.write_text(name)
        photo_paths[name] = path
    book = tmp_path / "Client-Book.pdf"
    book.write_text("book")
    proof_path = tmp_path / "receipt.json"
    proof_path.write_text("after proof")
    qa_path = tmp_path / "book-qa.json"
    qa = dict(
        project="first",
        revision=2,
        home_id="home",
        photography=True,
        revisions=[{"manifest_sha256": "r1"}, {"manifest_sha256": "r2"}],
        source_receipt_sha256=digest(proof_path.read_bytes()),
        images={
            name: ["before", digest(f"bedroom-{name}.png".encode())]
            for name in ("doorway", "desk")
        },
        hero_sha256=digest(b"salon-overview.png"),
        book_sha256=digest(book.read_bytes()),
        inspection=[{"page": 1}, {"page": 2}],
    )
    board = {"project": "first", "revision": 2, "home_id": "home"}
    proofs = [{"manifest_sha256": "r1"}, {"manifest_sha256": "r2"}]
    qa_path.write_text(json.dumps(qa))
    arguments = book, qa_path, board, proofs, tmp_path, photo_paths
    assert api["check_book"](*arguments) == 2

    qa["project"] = "other"
    qa_path.write_text(json.dumps(qa))
    with pytest.raises(ValueError, match="exact revisions"):
        api["check_book"](*arguments)

    qa["project"] = "first"
    qa["hero_sha256"] = "other-image"
    qa_path.write_text(json.dumps(qa))
    with pytest.raises(ValueError, match="different edited photographs"):
        api["check_book"](*arguments)

    qa["hero_sha256"] = digest(b"salon-overview.png")
    qa["inspection"].pop()
    qa_path.write_text(json.dumps(qa))
    with pytest.raises(ValueError, match="every PDF page"):
        api["check_book"](*arguments)
