import hashlib
import json
from pathlib import Path

import pytest

from archimind.assets import designer_concepts as concepts


def test_packaged_releases_match_the_editable_originals():
    source = Path(__file__).resolve().parents[1]
    chairs = concepts.approved_chairs()
    assert [row.version for row in chairs] == ["1.0.0", "1.1.0"]
    assert len({row.sha256 for row in chairs}) == 2
    for chair in chairs:
        assert (
            concepts.resolve_chair(chair.concept_id, chair.version, chair.sha256)
            == chair
        )
        archive = source / "design" / chair.concept_id / chair.version
        receipt = json.loads((archive / "release.json").read_bytes())
        assert (
            receipt["authoring"]["sha256"]["chair.blend"]
            == hashlib.sha256((archive / "chair.blend").read_bytes()).hexdigest()
        )
        for view in ("front", "three-quarter"):
            data = concepts.preview_bytes(chair, view)
            assert (
                hashlib.sha256(data).hexdigest()
                == receipt["authoring"]["sha256"][view + ".png"]
            )
        mesh = concepts._asset(chair.sha256, "glb")
        facts = concepts.inspect_chair(mesh)
        assert facts["triangles"] == 3712 and facts["mesh_instances"] == 10
        assert json.loads(json.dumps(facts)) == receipt["inspection"]
        with pytest.raises(ValueError):
            concepts.resolve_chair(chair.concept_id, chair.version, "0" * 64)


def test_corrupt_or_missing_release_fails_closed(tmp_path, monkeypatch):
    chair = concepts.approved_chairs()[0]
    (tmp_path / "designer_registry.json").write_bytes(
        concepts._dir().joinpath("designer_registry.json").read_bytes()
    )
    monkeypatch.setattr(concepts, "_dir", lambda: tmp_path)
    with pytest.raises(ValueError):
        concepts.resolve_chair(chair.concept_id, chair.version, chair.sha256)
    (tmp_path / f"designer-{chair.sha256}.glb").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        concepts.resolve_chair(chair.concept_id, chair.version, chair.sha256)
    with pytest.raises(ValueError):
        concepts.preview_bytes(chair, "front")
    (tmp_path / "designer_registry.json").write_text("{}")
    assert concepts.approved_chairs() == ()


def test_collection_geometry_and_editable_originals_match_release_receipts():
    root = Path(__file__).resolve().parents[1]
    records = concepts.approved_collection()
    assert set(concepts.BEDROOM_SIZES) == {row.concept_id for row in records}
    for record in records:
        archive = root / "design" / record.concept_id / record.version
        receipt = json.loads((archive / "release.json").read_bytes())
        assert receipt["authoring"]["reopened"] is True
        assert (
            hashlib.sha256((archive / "editable.blend").read_bytes()).hexdigest()
            == receipt["authoring"]["sha256"]["editable.blend"]
        )
        assert [record.width_m, record.depth_m, record.height_m] == receipt[
            "authoring"
        ]["dimensions_wdh_m"]
        data = concepts._asset(record.sha256, "glb")
        assert receipt["inspection"] == json.loads(
            json.dumps(
                concepts.inspect_concept(
                    data, concepts.BEDROOM_SIZES[record.concept_id]
                )
            )
        )
        with pytest.raises(ValueError):
            concepts.resolve_chair(record.concept_id, record.version, record.sha256)
