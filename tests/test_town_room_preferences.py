import math

import pytest

from archimind.town.design import Brief, generate, interpret_offline, validate_home


def test_composed_preferences_rank_validated_homes_and_report_measurements():
    brief = interpret_offline(
        Brief(width=15, depth=16),
        "formal salon and quiet study and kitchen-dining near salon",
    )
    events = []
    homes = generate(brief, on_progress=lambda kind, data: events.append((kind, data)))
    assert len(homes) == 2
    scores = []
    for home in homes:
        validate_home(home)
        centers = {}
        for part in home["rooms"]:
            room = part["design"]["room"]
            centers[room["id"]] = (
                part["origin"][0] + room["width_m"] / 2,
                part["origin"][1] + room["depth_m"] / 2,
            )
        measures = home["evidence"]["room_preferences"]
        assert len(measures) == 2
        for row in measures:
            assert row["center_distance_m"] == pytest.approx(
                math.dist(centers[row["room"]], centers[row["target"]]), abs=0.00051
            )
        scores.append(
            sum(
                r["center_distance_m"] * (1 if r["relation"] == "near" else -1)
                for r in measures
            )
        )
    assert scores == sorted(scores)
    assert (
        next(data for name, data in events if name == "Compared room placements")[
            "validated_alternatives"
        ]
        > 2
    )


@pytest.mark.parametrize(
    "prompt",
    [
        "study near study",
        "study near bedroom and bedroom away from study",
        "living near salon",
    ],
)
def test_invalid_relations(prompt):
    with pytest.raises(ValueError):
        generate(interpret_offline(Brief(), prompt))


def test_live_interpreter_hands_multiple_goals_to_geometry(monkeypatch):
    from uuid import uuid4

    from archimind.town import service

    req = service.Request(
        project=uuid4(),
        id=uuid4(),
        base=0,
        live=True,
        message="I take calls at home and want a short trip from the bedroom to the bathroom.",
        brief=interpret_offline(Brief(), "bathroom near study"),
    )

    def interpret(schema, prompt, **kwargs):
        assert req.message in prompt
        return schema(
            priority="balanced",
            palette="oak",
            clarification="",
            unsupported=[],
            room_goals=[
                dict(room="study", relation="far", target="living"),
                dict(room="bedroom", relation="near", target="bathroom"),
            ],
        )

    monkeypatch.setattr(service.provider, "configuration", lambda _: None)
    monkeypatch.setattr(service.provider, "request", interpret)
    result = service.interpret(req, None)
    assert len(generate(result)[0]["evidence"]["room_preferences"]) == 3
