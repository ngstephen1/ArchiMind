"""Editable metric survey plan contract and rejection cases."""

import json
from math import sqrt
from pathlib import Path

import pytest
from pydantic import ValidationError

from archimind.designer_handoff.survey import Survey, write_survey_dxf


@pytest.fixture
def intake():
    return {
        "source_kind": "demonstration",
        "height_m": 2.8,
        "geometry_source": "sketch",
        "sources": [{"id": "sketch", "description": "Synthetic test sketch"}],
        "vertices_m": [(0, 0), (4, 0), (4, 3), (3, 4), (0, 4)],
        "openings": [
            dict(
                id="entry",
                kind="door",
                wall=0,
                offset_m=0.5,
                width_m=0.9,
                height_m=2.1,
                sill_m=0,
                source="sketch",
                hinge="end",
                swing="inward",
            ),
            dict(
                id="light",
                kind="window",
                wall=2,
                offset_m=0.2,
                width_m=1,
                height_m=1.2,
                sill_m=0.7,
                source="sketch",
            ),
        ],
        "fixtures": [
            dict(
                id="built-in",
                x_m=2,
                y_m=2,
                width_m=0.8,
                depth_m=0.4,
                rotation_deg=90,
                source="sketch",
            )
        ],
    }


def test_dxf_measured_geometry_and_editable_layers(intake, tmp_path):
    survey = Survey.model_validate(intake)
    target = tmp_path / "plan.dxf"
    write_survey_dxf(survey, target)
    raw = target.read_text().splitlines()
    pairs = list(zip(raw[::2], raw[1::2], strict=True))
    assert pairs[pairs.index(("9", "$INSUNITS")) + 1] == ("70", "6")
    entities = []
    for code, value in pairs[pairs.index(("2", "ENTITIES")) + 1 :]:
        if code == "0":
            entities.append({})
        entities[-1][code] = value

    def tagged(layer):
        return [e for e in entities if e.get("8") == layer]

    assert len(tagged("WALLS")) == 7
    assert len(tagged("FIXTURES")) == 4
    assert len(tagged("DOORS")) == 1
    leaf, arc = tagged("DOOR_LEAVES")
    assert tuple(float(leaf[k]) for k in ("10", "20", "11", "21")) == pytest.approx(
        (1.4, 0, 1.4, 0.9)
    )
    assert arc["0"] == "ARC"
    assert tuple(float(arc[k]) for k in ("40", "50", "51")) == pytest.approx(
        (0.9, 90, 180)
    )
    (window,) = tagged("WINDOWS")
    assert tuple(float(window[k]) for k in ("10", "20", "11", "21")) == pytest.approx(
        (4 - 0.2 / sqrt(2), 3 + 0.2 / sqrt(2), 4 - 1.2 / sqrt(2), 3 + 1.2 / sqrt(2))
    )
    fixture = tagged("FIXTURES")[0]
    assert tuple(float(fixture[k]) for k in ("11", "21")) == pytest.approx((2, 2.8))


@pytest.mark.parametrize(
    "changes",
    [
        {"geometry_source": "missing"},
        {"vertices_m": [(0, 0), (0, 4), (4, 4), (4, 0)]},
        {"vertices_m": [(0, 0), (4, 4), (4, 0), (0, 4)]},
        {"height_m": None},
        {
            "fixtures": [
                dict(id="entry", x_m=0, y_m=0, width_m=1, depth_m=1, source="sketch")
            ]
        },
        {
            "fixtures": [
                dict(
                    id="bad",
                    x_m=3.1,
                    y_m=3.1,
                    width_m=0.8,
                    depth_m=0.8,
                    source="sketch",
                )
            ]
        },
    ],
)
def test_invalid_survey_rejected(intake, changes):
    with pytest.raises(ValidationError):
        Survey.model_validate(intake | changes)


@pytest.mark.parametrize(
    "changes", [{"wall": 5}, {"offset_m": 3.5}, {"height_m": 3}, {"hinge": None}]
)
def test_invalid_opening(intake, changes):
    intake["openings"][0].update(changes)
    with pytest.raises(ValidationError):
        Survey.model_validate(intake)


def test_overlapping_openings(intake):
    intake["openings"].append(intake["openings"][0] | {"id": "conflict"})
    with pytest.raises(ValidationError, match="Overlapping"):
        Survey.model_validate(intake)


def test_archival_survey_keeps_unknowns_and_conflicts_visible(intake):
    intake.update(
        source_kind="archival",
        height_m=None,
        field_checks=["Locate radiator."],
        checks=[dict(start=0, end=2, length_m=5.5, tolerance_m=0.01, source="sketch")],
    )
    intake["openings"][0].update(hinge=None, swing=None)
    items = Survey.model_validate(intake).verification_items()
    assert "Locate radiator." in items
    assert any("floor-to-ceiling" in i for i in items)
    assert any("5.0000 m" in i and "5.5 m" in i for i in items)
    assert any("entry" in i for i in items)


def test_zane_street_packet_cannot_supply_a_survey_polygon():
    packet = (
        Path(__file__).resolve().parents[1] / "docs/handovers/zane-street/evidence.json"
    )
    evidence = json.loads(packet.read_bytes())
    assert evidence["profile"] == "angled north bay"
    assert evidence["current_building_status"] == "unverified"
    assert evidence["surveyed_polygon_m"] is None
    assert evidence["height_m"] is None
    source = {"id": "habs", "description": evidence["plan_reference"]}
    with pytest.raises(ValidationError) as error:
        Survey.model_validate(
            {
                "source_kind": "archival",
                "sources": [source],
                "geometry_source": source["id"],
                "height_m": evidence["height_m"],
            }
        )
    assert [item["loc"] for item in error.value.errors()] == [("vertices_m",)]


@pytest.mark.parametrize(
    "metadata", [{}, {"project_id": "synthetic-bedroom", "surveyed_on": "2026-11-23"}]
)
def test_survey_cli_keeps_submitted_evidence_and_rejects_overwrites(
    intake, tmp_path, metadata
):
    import hashlib
    import json
    import subprocess
    import sys

    source, out = tmp_path / "input.json", tmp_path / "edition"
    source.write_text(json.dumps(intake | metadata))
    cmd = [
        sys.executable,
        "-m",
        "archimind.designer_handoff.survey",
        str(source),
        "--output",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    assert (out / "survey.json").read_bytes() == source.read_bytes()
    report = json.loads((out / "field-verification.json").read_text())
    assert report["intake_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["plan_area_m2"] == pytest.approx(15.5)
    assert report["review_status"] == "pending professional review"
    assert {
        key: report[key] for key in ("project_id", "surveyed_on") if key in report
    } == metadata
    assert report["field_verification_items"]
    retry = subprocess.run(cmd, capture_output=True, text=True)
    assert retry.returncode == 1 and "already exists" in retry.stderr


def test_export_preserves_window_reveal_and_outlet_without_inventing_a_depth(
    intake, tmp_path
):
    from archimind.designer_handoff.survey import export_intake

    intake["openings"][1]["reveal_depth_m"] = 0.17
    outlet = {
        "id": "O1",
        "wall": 4,
        "offset_m": 3,
        "height_m": 0.31,
        "source": "sketch",
    }
    intake["outlets"] = [outlet]
    source, output = tmp_path / "site.json", tmp_path / "edition"
    source.write_text(json.dumps(intake))
    export_intake(source, output)
    report = json.loads((output / "field-verification.json").read_text())
    assert report["window_details"] == [
        {
            "id": "light",
            "source": "sketch",
            "reveal_depth_m": 0.17,
            "trim_projection_m": None,
        }
    ]
    assert report["outlets"] == [outlet]
    dxf = (output / "existing-conditions.dxf").read_text()
    assert dxf.count("8\nOUTLETS\n") == 2


@pytest.mark.parametrize(
    "mutation", [{"offset_m": 5}, {"height_m": 3}, {"source": "other"}]
)
def test_unbound_outlet_values_are_rejected(intake, mutation):
    intake["outlets"] = [
        {"id": "O1", "wall": 4, "offset_m": 3, "height_m": 0.31, "source": "sketch"}
        | mutation
    ]
    with pytest.raises(ValidationError):
        Survey.model_validate(intake)
