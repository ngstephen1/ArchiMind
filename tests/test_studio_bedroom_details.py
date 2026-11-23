"""Use the bedroom export and whole-home scene interchangeably for detail studies."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_bedroom_matches_the_saved_whole_home_detail(tmp_path):
    whole = ROOT / "docs/data/nov24-fresh-live/manifest-r2.json"
    bedroom = tmp_path / "bedroom.json"
    bedroom.write_text(json.dumps(json.loads(whole.read_bytes())["bedroom"]))
    for name, manifest in (("whole", whole), ("bedroom", bedroom)):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/studio_bedroom_details.py"),
                str(manifest),
                "--output",
                str(tmp_path / name),
            ],
            check=True,
        )
    for kind in ("svg", "json"):
        name = f"window-and-bed-head.{kind}"
        assert (tmp_path / "whole" / name).read_bytes() == (
            tmp_path / "bedroom" / name
        ).read_bytes()


def test_nonprocedural_headboard_is_not_inferred(tmp_path):
    whole = json.loads(
        (ROOT / "docs/data/nov24-fresh-live/manifest-r2.json").read_bytes()
    )
    bedroom = whole["bedroom"]
    next(item for item in bedroom["furniture"] if item["id"] == "queen-bed")[
        "source"
    ] = {"kind": "concept"}
    for name, manifest in (("whole", whole), ("bedroom", bedroom)):
        source = tmp_path / f"{name}.json"
        source.write_text(json.dumps(manifest))
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/studio_bedroom_details.py"),
                str(source),
                "--output",
                str(tmp_path / name),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "requires the procedural queen bed" in result.stderr
        assert not (tmp_path / name).exists()
