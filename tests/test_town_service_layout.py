"""Acceptance checks for saved Town service fixture geometry."""

import copy
from xml.etree.ElementTree import fromstring

import pytest
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app
from archimind.town.brief_review import requirement_controls, review_summary
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


def test_first_fixture_program_requires_unlocking_unfurnished_service_rooms():
    home = generate(Brief(width=15, depth=16))[0]
    with pytest.raises(ValueError, match="Unlock rooms.*bathroom"):
        generate(
            Brief(width=15, depth=16, service_layout=True, locks=["bathroom"]), home
        )


def test_shorter_five_room_program_keeps_four_places_and_fixture_confirmation():
    brief = Brief(width=15, depth=10, service_layout=True, compare_tradeoffs=True)
    brief, questions = requirement_controls(
        brief, "Four seats at one dining table in the kitchen.", None
    )
    assert not questions
    assert brief.dining_seats == 4
    assert (
        "Kitchen and bathroom fixtures with modeled working clearances"
        in review_summary(brief, controls={"service_layout"})["requirements"]
    )
    candidates = generate(brief)
    assert candidates[0]["evidence"]["comparison"]["dining_places"] == {
        "kitchen-dining": 4
    }


def test_room_door_swing_rejects_furniture_outside_the_shallow_entry_zone(service_home):
    home = copy.deepcopy(service_home)
    bath = design_for(home, "bathroom")
    door = bath["room"]["doors"][0]
    assert door["wall"] in {"east", "west"}
    x = 0.7 if door["wall"] == "west" else bath["room"]["width_m"] - 0.9
    bath["furniture"].append(
        {
            "id": "hamper",
            "name": "Hamper",
            "category": "storage",
            "x_m": x,
            "y_m": door["offset_m"] + 0.3,
            "width_m": 0.2,
            "depth_m": 0.2,
            "height_m": 0.5,
        }
    )
    with pytest.raises(ValueError, match="bathroom-door modeled inward door swing"):
        validate_home(home)


def test_service_drawings_reopen_the_exact_saved_revision(
    service_home, monkeypatch, tmp_path
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "services.db"))
    service.initialize()
    owner = "local-designer"
    project = service.create(owner)["project"]
    other_owner_project = service.create("another-owner")["project"]
    with service.transaction() as q:
        service.apply(q, owner, project, 0, service_home)
        service.apply(q, owner, project, 1, generate(Brief())[0])
        service.apply(q, "another-owner", other_owner_project, 0, service_home)

    client = TestClient(app, base_url="http://localhost")
    url = f"/api/projects/{project}/service-study"
    assert client.get(url).status_code == 400
    assert client.get(url, params={"revision": 2}).status_code == 404
    assert (
        client.get(
            f"/api/projects/{other_owner_project}/service-study", params={"revision": 1}
        ).status_code
        == 404
    )
    response = client.get(url, params={"revision": 1})
    assert response.status_code == 200
    assert response.json()["home_id"] == service_home["id"]
    drawings = response.json()["drawings"]
    assert set(drawings) == {
        "kitchen-dining-plan.svg",
        "bathroom-plan.svg",
        "kitchen-elevation.svg",
        "bathroom-services.svg",
    }
    svg = "{http://www.w3.org/2000/svg}"
    for markup in drawings.values():
        root = fromstring(markup)
        assert root.findtext(svg + "metadata") == (
            f"project={project}; revision=1; home={service_home['id']}"
        )
    assert fromstring(drawings["bathroom-plan.svg"]).find(svg + "path") is not None
    assert "0.75 m leaf" in drawings["kitchen-dining-plan.svg"]
    assert "Refrigerator" in drawings["kitchen-elevation.svg"]
    assert "existing branch positions" in drawings["bathroom-services.svg"]
