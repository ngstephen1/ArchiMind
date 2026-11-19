"""Release a reviewed non-chair designer piece into a scratch checkout."""

import hashlib
import json
import runpy
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from archimind.assets import designer_concepts as concepts

ROOT = Path(__file__).resolve().parents[1]
RELEASE = runpy.run_path(str(ROOT / "scripts" / "release_designer_piece.py"))


def _png():
    out = BytesIO()
    Image.new("RGB", (600, 640), "white").save(out, "PNG")
    return out.getvalue()


def _candidate(tmp_path, wdh):
    chair = concepts.approved_chairs()[0]
    payload = {
        "piece.glb": concepts._asset(chair.sha256, "glb"),
        "piece.blend": b"BLENDER-v501 stand-in",
        "front.png": _png(),
        "three-quarter.png": _png(),
    }
    candidate = tmp_path / "candidates" / "side-table"
    candidate.mkdir(parents=True)
    for name, data in payload.items():
        (candidate / name).write_bytes(data)
    digests = {k: hashlib.sha256(v).hexdigest() for k, v in payload.items()}
    meta = {
        "schema_version": 2,
        "concept_id": "walnut-side-table",
        "version": "1.0.0",
        "name": "Walnut side table",
        "category": "table",
        "dimensions_wdh_m": list(wdh),
        "blender_version": "5.1.0",
        "attribution": "Original ArchiMind piece.",
        "sha256": digests,
    }
    (candidate / "authoring.json").write_text(json.dumps(meta))
    (candidate.parent / "operator.json").write_text(
        json.dumps({"walnut-side-table@1.0.0": {"sha256": digests}})
    )
    root = tmp_path / "checkout"
    assets = root / "src/archimind/_viewer_assets"
    assets.mkdir(parents=True)
    (assets / "designer_registry.json").write_bytes(
        concepts._dir().joinpath("designer_registry.json").read_bytes()
    )
    return candidate, root, digests


def test_release_piece_appends_v2_record_with_category(tmp_path):
    candidate, root, digests = _candidate(tmp_path, (0.48, 0.52, 0.83))
    path = root / "src/archimind/_viewer_assets/designer_registry.json"
    original = json.loads(path.read_text())
    chairs = [r for r in original["pieces"] if r["category"] == "chair"]
    path.write_text(
        json.dumps(
            {"schema_version": 1, "chairs": chairs, "bedroom": original["bedroom"]}
        )
    )
    record = RELEASE["release"](
        candidate,
        root,
        "local-operator:2026-11-17",
        category="table",
        wdh=(0.48, 0.52, 0.83),
    )
    assert record["category"] == "table" and record["sha256"] == digests["piece.glb"]
    registry = json.loads(
        (root / "src/archimind/_viewer_assets/designer_registry.json").read_text()
    )
    assert registry["schema_version"] == 2
    assert registry["bedroom"] == original["bedroom"]
    assert registry["pieces"] == [*chairs, record]
    archive = root / "design/walnut-side-table/1.0.0"
    assert (archive / "piece.blend").exists()
    receipt = json.loads((archive / "release.json").read_text())
    assert receipt["inspection"]["triangles"] == 3712


def test_release_piece_rejects_declared_size_mismatch(tmp_path):
    candidate, root, _ = _candidate(tmp_path, (0.6, 0.52, 0.83))
    with pytest.raises(ValueError):
        RELEASE["release"](
            candidate,
            root,
            "local-operator:2026-11-17",
            category="table",
            wdh=(0.6, 0.52, 0.83),
        )
    with pytest.raises(ValueError):
        RELEASE["release"](
            candidate,
            root,
            "local-operator:2026-11-17",
            category="sofa",
            wdh=(0.6, 0.52, 0.83),
        )
