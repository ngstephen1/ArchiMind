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
