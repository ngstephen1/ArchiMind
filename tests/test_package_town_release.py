import hashlib
import json
import runpy
import struct
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def salon_cover(camera="overview"):
    return [{"room": {"id": "salon"}, "cameras": [{"id": camera}]}]


def test_edited_photographs_must_match_the_packed_proof(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    api = runpy.run_path(str(SCRIPTS / "package_town_release.py"))
    board = {"home_id": "home", "revision": 2, "rooms": salon_cover()}
    proof = {"manifest_sha256": "r2", "files": {"home.blend": "native"}}
    shots = []
    for name in api["views_for"](board):
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
    board = {
        "project": "first",
        "revision": 2,
        "home_id": "home",
        "rooms": salon_cover(),
    }
    photo_paths = {}
    for name in api["views_for"](board):
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


@pytest.mark.parametrize("salon_camera", ["overview", "doorway"])
def test_build_writes_verified_zip_and_refuses_to_replace_it(
    tmp_path, monkeypatch, salon_camera
):
    import zipfile

    monkeypatch.syspath_prepend(str(SCRIPTS))
    api = runpy.run_path(str(SCRIPTS / "package_town_release.py"))
    source = SCRIPTS.parent / "docs/data/conference-live-final"
    boards, proofs = [], []
    native = b"synthetic Blender bytes"
    for revision, name in enumerate(("before.json", "manifest.json"), start=1):
        folder = tmp_path / f"r{revision}"
        folder.mkdir()
        data = (source / name).read_bytes()
        board = json.loads(data)
        cover = next(part for part in board["rooms"] if part["room"]["id"] == "salon")
        cover["cameras"][0]["id"] = salon_camera
        data = json.dumps(board).encode()
        (folder / "manifest.json").write_bytes(data)
        (folder / "home.blend").write_bytes(native)
        proof = {
            "home_id": board["home_id"],
            "revision": revision,
            "manifest_sha256": digest(data),
            "files": {"manifest.json": digest(data), "home.blend": digest(native)},
        }
        if salon_camera == "doorway":
            finish = f"procedural materials for revision {revision}".encode()
            (folder / api["FINISH_NOTICE"]).write_bytes(finish)
            proof["files"][api["FINISH_NOTICE"]] = digest(finish)
        (folder / "receipt.json").write_text(json.dumps(proof))
        boards.append(board)
        proofs.append(proof)
    photos = tmp_path / "photos"
    photos.mkdir()
    image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" + struct.pack(">II", 1920, 1080)
    shots = []
    for name in api["views_for"](boards[1]):
        (photos / name).write_bytes(image)
        shots.append({"file": name, "sha256": digest(image)})
    notices = {}
    for name in api["NOTICES"]:
        (photos / name).write_text(name)
        notices[name] = digest(name.encode())
    (photos / "eye-view-receipt.json").write_text(
        json.dumps(
            {
                "home_id": boards[1]["home_id"],
                "revision": 2,
                "manifest_sha256": proofs[1]["manifest_sha256"],
                "camera_manifest_sha256": proofs[1]["manifest_sha256"],
                "proof_blend_sha256": digest(native),
                "resolution": [1920, 1080],
                "shots": shots,
                "source_notices": notices,
            }
        )
    )
    book = tmp_path / "Client-Book.pdf"
    book.write_text("synthetic PDF bytes")
    qa = tmp_path / "book.json"
    qa.write_text(
        json.dumps(
            {
                "project": boards[1]["project"],
                "revision": 2,
                "home_id": boards[1]["home_id"],
                "revisions": proofs,
                "source_receipt_sha256": digest(
                    (tmp_path / "r2/receipt.json").read_bytes()
                ),
                "before_receipt_sha256": digest(
                    (tmp_path / "r1/receipt.json").read_bytes()
                ),
                "images": {
                    name: {"fixed_camera": True, "sha256": ["before", digest(image)]}
                    for name in ("desk", "doorway")
                },
                "hero_sha256": digest(image),
                "book_sha256": digest(book.read_bytes()),
                "inspection": [{"page": 1}],
            }
        )
    )
    monkeypatch.setattr("subprocess.check_output", lambda *args, **kwargs: "Pages: 1\n")

    destination = tmp_path / "handoff.zip"
    arguments = (
        tmp_path / "r1",
        tmp_path / "r2",
        photos,
        book,
        qa,
        destination,
        "a" * 40,
    )
    receipt = json.loads(qa.read_bytes())
    receipt.pop("inspection")
    original = tmp_path / "original-book.json"
    original.write_text(json.dumps(receipt, indent=2))
    api["build"](*arguments, original_book_receipt=original)
    with zipfile.ZipFile(destination) as archive:
        assert archive.read("presentation/Client-Book.json") == original.read_bytes()
        if salon_camera == "doorway":
            for revision in (1, 2):
                notice = f"sources/r{revision}-{api['FINISH_NOTICE']}"
                assert (
                    archive.read(notice)
                    == f"procedural materials for revision {revision}".encode()
                )
        assert set(archive.namelist()) >= {
            "START-HERE.md",
            "revisions/r1-manifest.json",
            "revisions/r2-manifest.json",
            "presentation/Client-Book.pdf",
            f"presentation/salon-{salon_camera}.png",
            "drawings/bedroom-concept-shell.dxf",
            "native/home.blend",
            "SHA256SUMS.txt",
        }
        sums = archive.read("SHA256SUMS.txt").decode().splitlines()
        assert len(sums) == len(archive.namelist()) - 1
        for row in sums:
            expected, name = row.split("  ", 1)
            assert digest(archive.read(name)) == expected
    before = digest(destination.read_bytes())
    with pytest.raises(FileExistsError, match="fresh destination"):
        api["build"](*arguments)
    assert digest(destination.read_bytes()) == before

    # Same manifest, different proof bytes. The print's binding must catch it.
    mismatched_proof = dict(proofs[0])
    mismatched_proof["files"] = {**proofs[0]["files"], "home.blend": digest(b"other")}
    (tmp_path / "r1/receipt.json").write_text(json.dumps(mismatched_proof))
    with pytest.raises(ValueError, match="receipt.json"):
        api["build"](*arguments[:-2], tmp_path / "wrong-proof.zip", arguments[-1])
