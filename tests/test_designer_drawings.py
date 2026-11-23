"""Check plan, elevation and section geometry against the saved conference home."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from archimind.designer_handoff.drawings import write_drawings
from archimind.designer_handoff.survey import Survey


@pytest.fixture
def board():
    source = (
        Path(__file__).resolve().parents[1]
        / "docs/data/conference-sprint/manifest.json"
    )
    return json.loads(source.read_text())


def bedroom(board):
    return next(row for row in board["rooms"] if row["room"]["id"] == "bedroom")


def test_revision_and_geometry_across_drawings(board, tmp_path):
    plan, elevations, section = [
        ET.parse(p) for p in write_drawings(board, tmp_path, provenance="demonstration")
    ]
    for drawing in (plan, elevations, section):
        content = " ".join(drawing.getroot().itertext())
        assert board["project"] in content
        assert board["home_id"] in content
        assert "REVISION 2" in content
        assert "demonstration geometry" in content
    assert "6.398 m" in " ".join(plan.getroot().itertext())
    assert "4.906 m" in " ".join(plan.getroot().itertext())
    assert "Sill 1.000   Head 2.150" in " ".join(plan.getroot().itertext())
    assert {r.get("data-furniture") for r in plan.findall(".//*[@data-furniture]")} == {
        f["id"] for f in bedroom(board)["furniture"]
    }
    for key in ("bedroom-door", "bedroom-window"):
        assert elevations.find(f".//*[@data-opening='{key}']") is not None
    desk = next(f for f in bedroom(board)["furniture"] if f["id"] == "belaya")
    cut = desk["x_m"] + desk["width_m"] / 2
    expected = {
        f["id"]
        for f in bedroom(board)["furniture"]
        if f["x_m"] <= cut <= f["x_m"] + f["width_m"]
    }
    assert (
        set(el.get("data-furniture") for el in section.findall(".//*[@data-furniture]"))
        == expected
    )
    assert f"X = {cut:.3f} m" in " ".join(section.getroot().itertext())


def test_viewing_east_mirrors_south_origin_offset(board, tmp_path):
    room = bedroom(board)["room"]
    door = room["doors"][0]
    door["offset_m"] = 0.2
    w, d = room["width_m"], room["depth_m"]
    window = room["windows"][0]
    survey = Survey.model_validate(
        {
            "source_kind": "measured",
            "project_id": board["project"],
            "surveyed_on": "2026-11-23",
            "vertices_m": [(0, 0), (w, 0), (w, d), (0, d)],
            "height_m": room["ceiling_height_m"],
            "geometry_source": "test",
            "fixture_inventory_source": "test",
            "checks": [
                {
                    "start": 0,
                    "end": 2,
                    "length_m": (w * w + d * d) ** 0.5,
                    "tolerance_m": 0.001,
                    "source": "test",
                }
            ],
            "sources": [{"id": "test", "description": "Synthetic test measurements"}],
            "openings": [
                {
                    **door,
                    "kind": "door",
                    "wall": 1,
                    "sill_m": 0,
                    "source": "test",
                    "hinge": "end",
                    "swing": "inward",
                },
                {
                    "id": window["id"],
                    "kind": "window",
                    "wall": 3,
                    "sill_m": window["sill_height_m"],
                    "height_m": window["height_m"],
                    "width_m": window["width_m"],
                    "source": "test",
                    "offset_m": d - window["offset_m"] - window["width_m"],
                },
            ],
        }
    )
    with pytest.raises(ValueError, match="required"):
        write_drawings(board, tmp_path, provenance="survey-linked")
    for missing_binding in ({"project_id": None}, {"surveyed_on": None}):
        with pytest.raises(ValueError, match="dated survey"):
            write_drawings(
                board,
                tmp_path,
                provenance="survey-linked",
                survey=survey.model_copy(update=missing_binding),
            )
    with pytest.raises(ValueError, match="different project"):
        write_drawings(
            board,
            tmp_path,
            provenance="survey-linked",
            survey=survey.model_copy(update={"project_id": "another-room"}),
        )
    assert not list(tmp_path.iterdir())
    for missing in ({"checks": []}, {"fixture_inventory_source": None}):
        with pytest.raises(ValueError, match="Resolve field checks"):
            write_drawings(
                board,
                tmp_path,
                provenance="survey-linked",
                survey=survey.model_copy(update=missing),
            )
    _, elevation, _ = write_drawings(
        board, tmp_path, provenance="survey-linked", survey=survey
    )
    door["offset_m"] += 0.01
    with pytest.raises(ValueError, match="opening bedroom-door"):
        write_drawings(board, tmp_path, provenance="survey-linked", survey=survey)
    door["offset_m"] -= 0.01
    root = ET.parse(elevation)
    assert root.getroot().attrib["data-survey-project-id"] == board["project"]
    assert root.getroot().attrib["data-survey-date"] == "2026-11-23"
    rect = root.find(".//*[@data-opening='bedroom-door']")
    assert rect is not None
    scale = float(rect.attrib["height"]) / door["height_m"]
    assert float(rect.attrib["x"]) == pytest.approx(
        630 + (room["depth_m"] - door["offset_m"] - door["width_m"]) * scale
    )
    assert "linked to supplied survey" in " ".join(root.getroot().itertext())


def test_xml_safe_labels_and_unknown_provenance(board, tmp_path):
    bedroom(board)["furniture"][0]["name"] = "Desk A & B <oak>"
    plan, _, _ = write_drawings(board, tmp_path, provenance="demonstration")
    assert "Desk A & B <oak>" in " ".join(ET.parse(plan).getroot().itertext())
    with pytest.raises(ValueError, match="provenance"):
        write_drawings(board, tmp_path, provenance="certified")


def test_reject_unsupported_shell_and_furniture(board, tmp_path):
    bedroom(board)["furniture"][0]["rotation_deg"] = 90
    with pytest.raises(ValueError):
        write_drawings(board, tmp_path, provenance="demonstration")
    board["rooms"] = []
    with pytest.raises(ValueError, match="exactly one"):
        write_drawings(board, tmp_path, provenance="demonstration")
    assert list(tmp_path.iterdir()) == []
