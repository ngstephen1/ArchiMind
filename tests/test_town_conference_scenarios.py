"""Structured provider fixtures through Town's real interpreter and generation path."""

import json
import math
from uuid import uuid4

import pytest

from archimind.town import agents, service
from archimind.town.design import Brief, digest, generate, validate_home


@pytest.fixture(scope="module")
def existing_home():
    return generate(Brief(width=15, depth=16, formal_salon=True))[0]


CASES = [
    (
        "hosting",
        "We host dinners. Include a formal salon close to the kitchen.",
        {
            "formal_salon": True,
            "room_goals": [
                {"room": "kitchen-dining", "relation": "near", "target": "salon"}
            ],
        },
    ),
    (
        "remote",
        "I work from home. Put the study away from the living room.",
        {"room_goals": [{"room": "study", "relation": "far", "target": "living"}]},
    ),
    ("lock", "Keep the bedroom where it is.", {"lock_rooms": ["bedroom"]}),
    ("style", "Make it Japandi.", {"style": "japandi"}),
    ("ambiguous", "Keep the desk in place.", {"lock_furniture": ["desk"]}),
    (
        "unsupported",
        "This home must have a second storey.",
        {"unsupported": ["second storey"]},
    ),
]


@pytest.mark.parametrize("case,message,fields", CASES, ids=[case[0] for case in CASES])
def test_conference_design_scenario(
    case, message, fields, existing_home, monkeypatch, record_property
):
    previous = None if case in {"hosting", "remote"} else existing_home
    before = digest(previous)
    request = service.Request(
        project=uuid4(),
        id=uuid4(),
        base=int(previous is not None),
        message=message,
        live=True,
        brief=Brief(width=15, depth=16, formal_salon=previous is not None),
    )
    calls = []

    def fixture_provider(schema, payload, **kwargs):
        calls.append(json.loads(payload)["request"])
        response = {
            "priority": "balanced",
            "style": "scandinavian",
            "clarification": "",
            "unsupported": [],
        }
        if previous:
            response.update(lock_rooms=[], lock_furniture=[])
        return schema(**(response | fields))

    monkeypatch.setattr(service.provider, "configuration", lambda _: None)
    monkeypatch.setattr(service.provider, "request", fixture_provider)
    monkeypatch.delenv("ARCHIMIND_ENABLE_DATASET_REFERENCES", raising=False)
    monkeypatch.delenv("ARCHIMIND_ENABLE_CODEX_ADVISOR", raising=False)

    def candidates():
        return agents.coordinate(request, previous, service.interpret, lambda *_: None)

    expected_error = {
        "ambiguous": "Clarify which room",
        "unsupported": "Unsupported requirements",
    }
    if case in expected_error:
        with pytest.raises(service.Problem, match=expected_error[case]) as error:
            candidates()
        actual = {"message": str(error.value), "candidates": 0}
    else:
        homes = candidates()
        assert homes
        for home in homes:
            validate_home(home)
        actual = {"candidate_ids": [h["id"] for h in homes]}
        if case in {"hosting", "remote"}:
            distances = []
            for home in homes:
                (measured,) = home["evidence"]["room_preferences"]
                room, target, relation = (
                    measured[key] for key in ("room", "target", "relation")
                )
                expected = fields["room_goals"][0]
                assert {room, target} == {expected["room"], expected["target"]}
                assert relation == expected["relation"]
                centers = {
                    p["design"]["room"]["id"]: (
                        p["origin"][0] + p["design"]["room"]["width_m"] / 2,
                        p["origin"][1] + p["design"]["room"]["depth_m"] / 2,
                    )
                    for p in home["rooms"]
                }
                assert measured["center_distance_m"] == pytest.approx(
                    math.dist(centers[room], centers[target]), abs=0.00051
                )
                distances.append(measured["center_distance_m"])
            assert len(distances) == 2
            assert distances == sorted(distances, reverse=case == "remote")
            actual["room_center_distances_m"] = distances
        elif case == "lock":

            def bedroom(home):
                return next(
                    p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom"
                )

            for home in homes:
                assert bedroom(home)["design"] == bedroom(previous)["design"]
                assert bedroom(home)["origin"] == bedroom(previous)["origin"]
            actual["locked_bedroom_geometry_sha256"] = digest(
                bedroom(previous)["design"]
            )
        elif case == "style":
            (home,) = homes

            def geometry(h):
                return [(p["origin"], p["design"]) for p in h["rooms"]]

            assert geometry(home) == geometry(previous)
            assert all(
                p["style"]["style_pack"]["id"] == "japandi" for p in home["rooms"]
            )
            assert home["id"] != previous["id"]
            actual["restyled_rooms"] = len(home["rooms"])
    assert calls == [message]
    assert digest(previous) == before
    record_property("observation", json.dumps(actual))
