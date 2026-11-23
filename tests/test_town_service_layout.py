"""Acceptance checks for saved Town service fixture geometry."""

import copy

import pytest

from archimind.town.design import Brief, generate, validate_home


@pytest.fixture(scope="module")
def service_home():
    return generate(Brief(width=15, depth=16, formal_salon=True, service_layout=True))[
        0
    ]


def design_for(home, name):
    return next(
        part["design"] for part in home["rooms"] if part["design"]["room"]["id"] == name
    )


def test_operating_states_and_service_evidence_are_bound_to_candidate(service_home):
    comparison = validate_home(service_home, measure=True)
    assert (
        comparison["service_rooms"]
        == service_home["evidence"]["comparison"]["service_rooms"]
    )
    kitchen = comparison["service_rooms"]["kitchen-dining"]
    assert {f["fixture_id"] for f in kitchen["operating_zones"]} == {
        "refrigerator",
        "prep-counter",
        "kitchen-sink",
        "cooking-range",
    }
    assert kitchen["operating_zones"][0]["leaf_projection_m"] == 0.75
    assert kitchen["service_connections"] == "field verification pending"
    assert comparison["dining_places"]["kitchen-dining"] == 4


def test_missing_toilet_blocks_saved_plan(service_home):
    home = copy.deepcopy(service_home)
    bath = design_for(home, "bathroom")
    bath["furniture"] = [f for f in bath["furniture"] if f["id"] != "toilet"]
    with pytest.raises(ValueError, match="Missing required.*toilet"):
        validate_home(home)


def test_fridge_body_fits_but_opening_is_obstructed(service_home):
    home = copy.deepcopy(service_home)
    kitchen = design_for(home, "kitchen-dining")
    fridge = next(f for f in kitchen["furniture"] if f["id"] == "refrigerator")
    kitchen["furniture"].append(
        {
            **fridge,
            "id": "blocker",
            "width_m": 0.3,
            "depth_m": 0.3,
            "y_m": fridge["y_m"] + fridge["depth_m"] + 0.2,
        }
    )
    with pytest.raises(
        ValueError, match="refrigerator working or appliance-opening zone"
    ):
        validate_home(home)


def test_locked_service_room_is_preserved(service_home):
    home = generate(
        Brief(width=15, depth=16, formal_salon=True, locks=["bathroom"]), service_home
    )[0]
    assert design_for(home, "bathroom") == design_for(service_home, "bathroom")
    assert home["service_layout"] is True
