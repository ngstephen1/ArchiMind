"""Exercise the two-project identity boundary and drawing measurements."""

import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts/publish_revision_study.py"))


def proof(directory, board_name):
    directory.mkdir()
    manifest = directory / "manifest.json"
    manifest.write_bytes(
        (ROOT / "docs/data/conference-sprint" / board_name).read_bytes()
    )
    board = json.loads(manifest.read_bytes())
    files = {"manifest.json": MODULE["digest"](manifest)}
    for view in ("desk", "doorway"):
        image = directory / f"bedroom-{view}.png"
        image.write_bytes(b"test image bytes")
        files[image.name] = MODULE["digest"](image)
    receipt = {key: board[key] for key in ("home_id", "revision")}
    receipt.update(files=files, manifest_sha256=files["manifest.json"])
    (directory / "receipt.json").write_text(json.dumps(receipt))
    return directory


def test_recomputes_physical_measures_and_checks_camera(tmp_path):
    one = proof(tmp_path / "r1", "before.json")
    two = proof(tmp_path / "r2", "manifest.json")
    dest = tmp_path / "study.html"
    MODULE["build"]((one, two), (None, None), dest)
    doc = json.loads(dest.with_suffix(".json").read_bytes())
    assert doc["displacement_m"] == pytest.approx(0.3)
    assert [r["chair_desk_gap_m"] for r in doc["revisions"]] == pytest.approx(
        [0.06, 0.36]
    )
    assert [
        r["desk_center_to_window_midpoint_m"] for r in doc["revisions"]
    ] == pytest.approx([4.46, 4.46], abs=0.001)
    assert doc["images"]["doorway"]["fixed_camera"]
    assert not doc["images"]["desk"]["fixed_camera"]
    (two / "bedroom-desk.png").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="digest mismatch"):
        MODULE["build"]((one, two), (None, None), dest)


def test_same_design_in_a_different_project_rejected(tmp_path):
    one = proof(tmp_path / "r1", "before.json")
    two = proof(tmp_path / "r2", "manifest.json")
    manifest = two / "manifest.json"
    board = json.loads(manifest.read_bytes())
    board["project"] = board["bedroom"]["project"] = "a different project"
    manifest.write_text(json.dumps(board))
    receipt = two / "receipt.json"
    doc = json.loads(receipt.read_bytes())
    doc["manifest_sha256"] = doc["files"]["manifest.json"] = MODULE["digest"](manifest)
    receipt.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="same project"):
        MODULE["build"]((one, two), (None, None), tmp_path / "study.html")


def test_room_move_changes_home_coordinate_but_preserves_desk_gap():
    board = json.loads(
        (ROOT / "docs/data/conference-sprint/manifest.json").read_bytes()
    )
    bedroom = next(p for p in board["rooms"] if p["room"]["id"] == "bedroom")
    before = MODULE["measurements"](board)
    bedroom["origin"][0] += 1.25
    after = MODULE["measurements"](board)
    assert before["chair_xy_m"] == after["chair_xy_m"]
    assert after["chair_home_xy_m"][0] - before["chair_home_xy_m"][0] == pytest.approx(
        1.25
    )
    assert before["chair_desk_gap_m"] == after["chair_desk_gap_m"]


def test_updated_transfer_rejects_another_project_or_portfolio(tmp_path):
    from hashlib import sha256

    api = runpy.run_path(str(ROOT / "scripts/package_designer_demo.py"))
    (tmp_path / "receipt.json").write_bytes(b"proof")
    (tmp_path / "Studio-House-Presentation.pdf").write_bytes(b"portfolio")
    portfolio = sha256(b"portfolio").hexdigest()
    qa = dict(
        inspection=[{}] * 16,
        input_sources=[dict(pages=10, sha256=portfolio)],
        source_receipt_sha256=sha256(b"proof").hexdigest(),
        project="first",
        revisions=[dict(manifest_sha256=api["R1"]), dict(manifest_sha256=api["R2"])],
        portfolio_sha256=portfolio,
    )
    api["check_book_sources"](qa, {"project": "first"}, tmp_path, tmp_path)
    with pytest.raises(ValueError, match="Book sources differ"):
        api["check_book_sources"](qa, {"project": "second"}, tmp_path, tmp_path)
    del qa["source_receipt_sha256"]
    with pytest.raises(ValueError, match="requires a revision-bound"):
        api["check_book_sources"](qa, {"project": "first"}, tmp_path, tmp_path)


def test_printed_receipt_and_both_appendix_pages(tmp_path):
    import shutil
    import subprocess
    import sys

    from PIL import Image

    chrome = next(
        (browser for browser in ("google-chrome", "chromium") if shutil.which(browser)),
        None,
    )
    if not chrome or not shutil.which("pdfunite") or not shutil.which("pdftotext"):
        pytest.skip("PDF integration uses headless Chrome and Poppler.")
    folders = [
        proof(tmp_path / "before", "before.json"),
        proof(tmp_path / "after", "manifest.json"),
    ]
    for folder in folders:
        b, p = MODULE["load_revision"](folder)
        names = {
            r["room"]["id"] + "-" + c["id"] for r in b["rooms"] for c in r["cameras"]
        }
        names.update(["salon-overview-drawing", "salon-overview-evening"])
        for name in names:
            path = folder / (name + ".png")
            Image.new("RGB", (160, 90), (89, 112, 91)).save(path)
            p["files"][path.name] = MODULE["digest"](path)
        (folder / "receipt.json").write_text(json.dumps(p))
    output = tmp_path / "book.pdf"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/print_revision_book.py"),
            *map(str, folders),
            str(output),
            "--chrome",
            chrome,
        ],
        check=True,
        timeout=200,
    )
    result = json.loads(output.with_suffix(".json").read_bytes())
    assert result["page_count"] == 12 and result["book_sha256"] == MODULE["digest"](
        output
    )
    assert result["displacement_m"] == pytest.approx(0.3)


@pytest.mark.parametrize(
    ("receipt_size", "image_size", "failure"),
    [
        ((1920, 1080), (1920, 1080), None),
        (None, (1920, 1080), "receipts"),
        ((960, 540), (960, 540), "receipts"),
        ((1920, 1080), (960, 540), "PNGs"),
    ],
)
def test_matched_hd_receipts_without_room_field(
    tmp_path, receipt_size, image_size, failure
):
    import struct

    one = proof(tmp_path / "r1", "before.json")
    two = proof(tmp_path / "r2", "manifest.json")
    boards, receipts = zip(*(MODULE["load_revision"](folder) for folder in (one, two)))
    eyes = (tmp_path / "eye1", tmp_path / "eye2")
    for folder, board, receipt in zip(eyes, boards, receipts, strict=True):
        folder.mkdir()
        shots = []
        for view in ("desk", "doorway"):
            image = folder / f"bedroom-{view}.png"
            image.write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR"
                + struct.pack(">II", *image_size)
            )
            shots.append(
                dict(
                    view=view,
                    file=image.name,
                    sha256=MODULE["digest"](image),
                    camera={"eye": [1, 2, 3]},
                )
            )
        receipt["files"]["home.blend"] = "scene digest"
        eye_receipt = dict(
            home_id=board["home_id"],
            revision=board["revision"],
            manifest_sha256=receipt["manifest_sha256"],
            camera_manifest_sha256=receipts[0]["manifest_sha256"],
            proof_blend_sha256=receipt["files"]["home.blend"],
            resolution=receipt_size,
            shots=shots,
        )
        (folder / "eye-view-receipt.json").write_text(
            json.dumps(eye_receipt if receipt_size else {})
        )
    if failure:
        with pytest.raises(ValueError, match=failure):
            MODULE["matched_frames"](boards, receipts, (one, two), eyes)
        return
    assert (
        len(MODULE["matched_frames"](boards, receipts, (one, two), eyes)["desk"]) == 2
    )


def test_living_room_book_uses_distinct_saved_cameras():
    select = runpy.run_path(str(ROOT / "scripts/publish_studio_board.py"))[
        "living_room_views"
    ]
    board = json.loads(
        (ROOT / "docs/data/nov24-fresh-live/manifest-r2.json").read_bytes()
    )
    views = next(p["cameras"] for p in board["rooms"] if p["room"]["id"] == "living")
    assert [view["id"] for view in select(views, {})] == ["overview", "media-console"]
    assert [view["id"] for view in select(views[:2], {})] == ["overview"]


def test_living_room_book_keeps_the_doorway_overview_fallback():
    select = runpy.run_path(str(ROOT / "scripts/publish_studio_board.py"))[
        "living_room_views"
    ]
    board = json.loads(
        (ROOT / "docs/data/nov24-fresh-live/manifest-r2.json").read_bytes()
    )
    overview, ensemble, detail = next(
        p["cameras"] for p in board["rooms"] if p["room"]["id"] == "living"
    )
    views = [
        {**overview, "reason": "Unobstructed doorway fallback"},
        {**ensemble, "reason": "Unobstructed doorway fallback"},
        detail,
    ]
    assert [view["id"] for view in select(views, {})] == ["overview", "media-console"]
