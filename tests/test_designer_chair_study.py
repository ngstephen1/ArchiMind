"""Operating-study acceptance against saved Town geometry and field records."""

import json
from pathlib import Path

import pytest

from archimind.designer_handoff.chair_study import (
    ChairFieldRecord,
    bedroom_board,
    chair_study,
    draw_study,
)


@pytest.fixture
def board():
    file = (
        Path(__file__).resolve().parents[1]
        / "docs/data/nov24-fresh-live/snapshot-r2.json"
    )
    return bedroom_board(json.loads(file.read_bytes()))


def test_three_states_are_saved_geometry_studies_while_physical_fit_is_unknown(board):
    report = chair_study(board)
    tucked, occupied, pulled = report["states"]
    assert [tucked["state"], occupied["state"], pulled["state"]] == [
        "tucked-in",
        "occupied",
        "pulled-back",
    ]
    assert abs(occupied["chair"]["y_m"] - pulled["chair"]["y_m"]) == pytest.approx(0.3)
    assert tucked["physical_tuck"] == "awaiting verification"
    assert tucked["modeled_room_circulation"] == "passed"
    assert report["field_record"] is None
    assert report["home_id"] == board["home_id"]
    assert "underside height" in draw_study(board, report)
    assert "REVISION 2" in draw_study(board, report)


def synthetic_measurements(board, **changes):
    record = dict(
        project=board["project"],
        revision=board["revision"],
        home_id=board["home_id"],
        chair_id="desk-chair",
        desk_id="belaya",
        recorded_on="2026-11-23",
        source="Synthetic measurement fixture for regression testing",
        clear_width_m=1.20,
        clear_height_m=0.65,
        clear_depth_m=0.40,
        opening_offset_from_desk_west_m=0.20,
        chair_width_m=0.45,
        chair_depth_m=0.48,
        chair_arm_height_m=0.55,
    )
    return ChairFieldRecord.model_validate(record | changes)


def test_source_bound_fit_obstruction_and_identity(board):
    report = chair_study(board, record=synthetic_measurements(board))
    assert report["states"][0]["physical_tuck"] == "measured fit at modeled position"
    failed = chair_study(
        board, record=synthetic_measurements(board, chair_arm_height_m=0.68)
    )
    assert failed["states"][0]["physical_tuck"] == "measured interference"
    assert "chair arms" in failed["physical_findings"][0]
    with pytest.raises(ValueError, match="do not belong"):
        chair_study(
            board, record=synthetic_measurements(board, project="other-project")
        )


def test_floor_object_can_obstruct_the_pulled_back_passage(board):
    baseline = chair_study(board)
    moved = baseline["states"][2]["chair"]
    original = baseline["states"][1]["chair"]
    north = moved["y_m"] > original["y_m"]
    bedroom = next(r for r in board["rooms"] if r["room"]["id"] == "bedroom")
    y = (moved["y_m"] + moved["depth_m"] + 0.10) if north else moved["y_m"] - 0.20
    bedroom["dressing"].append(
        {
            "id": "test-object",
            "kind": "plant",
            "x_m": moved["x_m"],
            "y_m": y,
            "width_m": 0.20,
            "depth_m": 0.10,
            "height_m": 0.30,
        }
    )
    pulled = chair_study(board)["states"][2]
    assert pulled["rear_gap_m"] == pytest.approx(0.10)
    assert pulled["modeled_rear_gap"] == "obstructed"


def test_sheet_shows_the_same_floor_obstacles_and_travel_as_the_report(board):
    report = chair_study(board)
    sheet = draw_study(board, report)
    assert report["floor_obstacles"]
    for item in report["floor_obstacles"]:
        assert sheet.count(f'data-object="{item["id"]}"') == 3
    assert "0.150 m under the desk" in sheet
    assert "0.300 m back from saved position" in sheet


def test_cli_writes_utf8_drawings(tmp_path, monkeypatch):
    from xml.etree.ElementTree import parse

    from archimind.designer_handoff.chair_study import main

    manifest = (
        Path(__file__).resolve().parents[1]
        / "docs/data/nov24-fresh-live/snapshot-r2.json"
    )
    destination = tmp_path / "study"
    monkeypatch.setattr(
        "sys.argv", ["chair_study", str(manifest), "--output", str(destination)]
    )
    main()
    sheet = destination / "chair-operation.svg"
    assert bytes([194, 183]) in sheet.read_bytes()
    assert parse(sheet).getroot().tag.endswith("svg")
