"""Archive regressions run in CI; geometric round trips use the optional CAD operator."""

import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAD = runpy.run_path(str(ROOT / "scripts/author_rhino_chair.py"))


@pytest.mark.parametrize("variant", ("gentle", "deep"))
def test_archived_chair_is_bound_to_pinned_glb_and_cad(variant):
    meta, glb = CAD["released"](variant)
    folder = ROOT / "design" / meta["concept_id"] / meta["version"] / "cad"
    file = folder / "chair.3dm"
    result = json.loads((folder / "cad-evidence.json").read_bytes())
    assert file.read_bytes()[:32].rstrip() == b"3D Geometry File Format       80"
    assert result["cad_sha256"] == CAD["digest"](file)
    assert result["cad_author_script_sha256"] == CAD["digest"](
        ROOT / "scripts/author_rhino_chair.py"
    )
    assert result["released_glb_sha256"] == CAD["digest"](glb)
    assert result["glb_mm"] == CAD["measurements"](CAD["glb_measurements"](glb))
    assert result["cad_mm"] == {
        "width": 480,
        "depth": 520,
        "height": 830,
        "seat_height": 455,
    }
    assert max(result["absolute_deltas_mm"].values()) <= result["tolerance_mm"] == 1


@pytest.mark.parametrize("variant", ("gentle", "deep"))
def test_optional_operator_rebuilds_reopens_and_rejects_wrong_variant(
    tmp_path, variant
):
    pytest.importorskip("rhino3dm")
    candidate = tmp_path / variant
    result = CAD["create"](variant, candidate)
    file = candidate / "chair.3dm"
    assert CAD["verify_cad"](file, variant) == result
    assert result["closed_mesh_parts"] == result["editable_nurbs_side_skins"] == 10
    assert result["quadratic_backrest_bend_mm"] == {"gentle": 42, "deep": 71}[variant]
    wrong = "deep" if variant == "gentle" else "gentle"
    with pytest.raises(ValueError, match="identity"):
        CAD["verify_cad"](file, wrong)
    with pytest.raises(FileExistsError):
        CAD["create"](variant, candidate)


def test_optional_operator_rejects_a_shifted_seat_with_the_same_overall_bounds(
    tmp_path,
):
    rhino = pytest.importorskip("rhino3dm")
    file = ROOT / "design/oak-sage-writing-chair/1.0.0/cad/chair.3dm"
    doc = rhino.File3dm.Read(str(file))
    seat = next(
        o.Geometry for o in doc.Objects if o.Attributes.Name == "Sage seat cushion"
    )
    assert seat.Translate(rhino.Vector3d(0, 0, 10))
    altered = tmp_path / "seat-shifted.3dm"
    assert doc.Write(str(altered), 8)
    with pytest.raises(ValueError, match="more than 1 mm"):
        CAD["verify_cad"](altered, "gentle")
