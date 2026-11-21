"""The render workflow accepts only exact, bounded exports from its repository."""

import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "stage_studio_manifest.py"
SPEC = importlib.util.spec_from_file_location("stage_studio_manifest", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.mark.parametrize(
    "source",
    [
        "main:docs/data/after.json",
        "0" * 40 + ":docs/data/../../.env.json",
        "0" * 40 + ":src/private.json",
        "0" * 40 + ":docs/data/asset.glb",
        "0" * 40 + ":docs/data/cmd;id.json",
    ],
)
def test_unpinned_or_outside_data_is_rejected_before_fetch(
    tmp_path, monkeypatch, source
):
    fetch = Mock()
    monkeypatch.setattr(module.subprocess, "run", fetch)
    with pytest.raises(ValueError):
        module.stage(source, tmp_path / "manifest.json")
    fetch.assert_not_called()


def test_only_bounded_exact_blob_is_staged(tmp_path, monkeypatch):
    ref = "a" * 40
    spec = ref + ":docs/data/sprint/before.json"
    out = tmp_path / "manifest.json"
    fetch, read = Mock(), Mock(side_effect=[b"2", b"{}"])
    monkeypatch.setattr(module.subprocess, "run", fetch)
    monkeypatch.setattr(module.subprocess, "check_output", read)
    module.stage(spec, out)
    fetch.assert_called_once_with(
        ["git", "fetch", "--no-tags", "--depth=1", "origin", ref], check=True
    )
    assert read.call_args_list[-1].args == (["git", "cat-file", "blob", spec],)
    assert out.read_bytes() == b"{}"


@pytest.mark.parametrize("size", [0, 4 * 1024 * 1024 + 1])
def test_export_bounds_fail_before_reading_blob(tmp_path, monkeypatch, size):
    monkeypatch.setattr(module.subprocess, "run", Mock())
    read = Mock(return_value=str(size).encode())
    monkeypatch.setattr(module.subprocess, "check_output", read)
    out = tmp_path / "manifest.json"
    with pytest.raises(ValueError):
        module.stage("a" * 40 + ":docs/data/export.json", out)
    read.assert_called_once()
    assert not out.exists()


def test_saved_style_content_must_still_match_home_id():
    home = {"rooms": [{"style": {"dressing": []}}], "width": 15.0}
    home["id"] = hashlib.sha256(
        json.dumps(home, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    module.verify_snapshot(json.dumps({"home": home}).encode())
    home["rooms"][0]["style"]["dressing"].append({"kind": "rug"})
    with pytest.raises(ValueError, match="home ID"):
        module.verify_snapshot(json.dumps({"home": home}).encode())
