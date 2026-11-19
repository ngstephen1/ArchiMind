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


def _piece_row(concept_id, version, category, wdh, fill):
    return {
        "concept_id": concept_id,
        "version": version,
        "name": concept_id.replace("-", " "),
        "category": category,
        "sha256": fill * 64,
        "front_sha256": "a" * 64,
        "three_quarter_sha256": "b" * 64,
        "width_m": wdh[0],
        "depth_m": wdh[1],
        "height_m": wdh[2],
        "bytes": 1000,
    }


def _write_registry(tmp_path, monkeypatch, registry):
    (tmp_path / "designer_registry.json").write_text(json.dumps(registry))
    monkeypatch.setattr(concepts, "_dir", lambda: tmp_path)


def test_registry_v2_lists_pieces_by_category(tmp_path, monkeypatch):
    _write_registry(
        tmp_path,
        monkeypatch,
        {
            "schema_version": 2,
            "pieces": [
                _piece_row(
                    "oak-sage-writing-chair", "1.0.0", "chair", (0.48, 0.52, 0.83), "1"
                ),
                _piece_row(
                    "green-velvet-tub-armchair",
                    "1.0.0",
                    "armchair",
                    (0.78, 0.74, 0.76),
                    "2",
                ),
            ],
        },
    )
    armchairs = concepts.approved_pieces("armchair")
    assert [p.concept_id for p in armchairs] == ["green-velvet-tub-armchair"]
    assert armchairs[0].category == "armchair"
    assert len(concepts.approved_pieces()) == 2
    assert [c.concept_id for c in concepts.approved_chairs()] == [
        "oak-sage-writing-chair"
    ]


def test_v1_registry_still_loads_as_chairs(tmp_path, monkeypatch):
    row = _piece_row(
        "oak-sage-writing-chair", "1.0.0", "chair", (0.48, 0.52, 0.83), "1"
    )
    del row["category"]
    _write_registry(tmp_path, monkeypatch, {"schema_version": 1, "chairs": [row]})
    pieces = concepts.approved_pieces()
    assert len(pieces) == 1 and pieces[0].category == "chair"
    assert concepts.approved_chairs() == pieces


def test_unknown_category_disables_registry(tmp_path, monkeypatch):
    _write_registry(
        tmp_path,
        monkeypatch,
        {
            "schema_version": 2,
            "pieces": [
                _piece_row("gothic-throne", "1.0.0", "throne", (0.8, 0.8, 1.4), "3")
            ],
        },
    )
    assert concepts.approved_pieces() == ()
    assert concepts.approved_chairs() == ()


def test_inspect_piece_measures_released_chair_and_rejects_off_reservation_bounds():
    chair = concepts.approved_chairs()[0]
    data = concepts._asset(chair.sha256, "glb")
    facts = concepts.inspect_piece(data, (0.48, 0.52, 0.83))
    assert facts["triangles"] == 3712
    with pytest.raises(ValueError):
        concepts.inspect_piece(data, (0.5, 0.52, 0.83))


def test_packaged_registry_is_v2_and_keeps_chair_releases():
    registry = json.loads(
        concepts._dir().joinpath("designer_registry.json").read_bytes()
    )
    assert registry["schema_version"] == 2 and "chairs" not in registry
    categories = {p["category"] for p in registry["pieces"]}
    assert "chair" in categories and categories <= concepts.CATEGORIES
    piece = concepts.approved_pieces("chair")[1]
    assert (
        concepts.resolve_piece(piece.concept_id, piece.version, piece.sha256) == piece
    )


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
