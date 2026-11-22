import json
import time
from types import SimpleNamespace

import pytest

from archimind.town import render_queue, service
from archimind.town.brief_review import requirement_controls
from archimind.town.design import Brief, RoomGoal, generate, validate_home


def test_six_seats_preserved_and_explanation_routed(monkeypatch):
    def interpret(schema, prompt, **kwargs):
        facts = json.loads(prompt)
        assert "dining_seats" not in facts["controls"]
        assert "compare_tradeoffs" not in facts["controls"]
        assert (
            facts["request"].rstrip(".") == "Place the study far from the living room"
        )
        return schema(
            priority="balanced",
            style="scandinavian",
            formal_salon=True,
            room_goals=[RoomGoal(room="study", relation="far", target="living")],
            unsupported=[],
            clarification="",
        )

    monkeypatch.setattr(service.provider, "configuration", lambda _: ("mock", "mock"))
    monkeypatch.setattr(service.provider, "request", interpret)
    brief = Brief(width=15, depth=16, compare_tradeoffs=True)
    request = SimpleNamespace(
        brief=brief,
        live=True,
        agent_team=True,
        message="Design a home for two people who work from home and host four guests for dinner. Include a formal salon and a separate living room. Place the study far from the living room and explain the placements.",
    )
    with pytest.raises(
        service.BriefClarification, match="All 6 dining places"
    ) as clarification:
        service.interpret(request, None)
    assert (
        "6 dining places at one table" in clarification.value.reviewed["requirements"]
    )

    request.brief = brief.model_copy(update={"dining_seats": 6, "split_dining": True})
    request.message = (
        "Use two four-seat tables in the formal salon and kitchen-dining room "
        "for two residents and four dinner guests. "
        "Place the study far from the living room. Explain the placements."
    )
    confirmed = service.interpret(request, None)
    a, b = generate(confirmed)
    measures = [candidate["evidence"]["comparison"] for candidate in (a, b)]
    assert all(
        m["dining_places"] == {"salon": 4, "kitchen-dining": 4}
        and m["required_dining_seats"] == 6
        and m["split_dining"]
        for m in measures
    )
    distances = [
        {(r["room"], r["target"]): r["distance_m"] for r in m["routes"]}
        for m in measures
    ]
    assert abs(distances[0]["study", "living"] - distances[1]["study", "living"]) >= 0.5
    for candidate in (a, b):
        validate_home(candidate)
        assert any(
            item.get("refined")
            for p in candidate["rooms"]
            for item in p["style"]["dressing"]
        )


def test_saved_constraints_are_inherited_only_when_omitted():
    previous = generate(
        Brief(
            width=15,
            depth=16,
            formal_salon=True,
            compare_tradeoffs=True,
            dining_seats=6,
            split_dining=True,
            passage_m=0.65,
        )
    )[0]
    assert not Brief().compare_tradeoffs
    request = SimpleNamespace(
        brief=Brief(width=15, depth=16), agent_team=True, live=False, message=""
    )
    inherited = service.interpret(request, previous)
    assert (inherited.dining_seats, inherited.split_dining, inherited.passage_m) == (
        6,
        True,
        0.65,
    )
    regenerated = generate(inherited, previous)[0]
    comparison = regenerated["evidence"]["comparison"]
    assert (
        comparison["required_dining_seats"],
        comparison["split_dining"],
        comparison["passage_m"],
    ) == (6, True, 0.65)
    assert regenerated["presentation_detail"] == previous["presentation_detail"]

    request.brief = Brief(
        width=15, depth=16, dining_seats=0, split_dining=False, passage_m=0.6
    )
    changed = service.interpret(request, previous)
    comparison = generate(changed, previous)[0]["evidence"]["comparison"]
    assert (
        comparison["required_dining_seats"],
        comparison["split_dining"],
        comparison["passage_m"],
    ) == (0, False, 0.6)


@pytest.mark.parametrize(
    "phrase",
    [
        ".9 m clear passage",
        "passage at least 90 cm wide",
        "900 mm circulation",
        "90 cm wide passage",
        "passages at least 90 cm wide",
        "Keep the passage at least 90 cm",
        "90 cm clear route",
        "90 cm wide clear route",
    ],
)
def test_passage_with_leading_decimal_or_unit_and_local_seats(phrase):
    brief, questions = requirement_controls(
        Brief(),
        f"Two residents and four dinner guests. Four seats in the salon. {phrase}.",
        None,
    )
    assert not questions
    assert (brief.dining_seats, brief.passage_m) == (6, 0.9)


@pytest.mark.parametrize(
    ("phrase", "seats"),
    [
        ("Six seats in total.", 6),
        ("Six places at one table.", 6),
        ("Four seats in salon and two seats in kitchen.", 0),
        ("Four places per table.", 0),
    ],
)
def test_total_seats_differ_from_per_room_counts(phrase, seats):
    brief, questions = requirement_controls(Brief(), phrase, None)
    assert not questions
    assert brief.dining_seats == seats


def test_route_length_does_not_override_clear_passage_width():
    brief, questions = requirement_controls(
        Brief(),
        "I prefer routes 8 m or shorter, with a 90 cm clear passage. Place the passage at least 1.2 m from the bedroom.",
        None,
    )
    assert brief.passage_m == 0.9
    assert not questions


def test_single_table_and_room_specific_seating_remain_hard_requirements():
    brief, questions = requirement_controls(
        Brief(), "Six dining seats at one table.", None
    )
    assert brief.dining_seats == 6 and not brief.split_dining and not questions
    request = SimpleNamespace(
        brief=Brief(compare_tradeoffs=True, split_dining=True),
        agent_team=True,
        live=True,
        message="Seating for six at a single table, with six seats in the formal salon.",
    )
    with pytest.raises(service.BriefClarification, match="one dining table") as exc:
        service.interpret(request, None)
    assert "requested 6 places there" in str(exc.value)
    assert "6 dining places at one table" in exc.value.reviewed["requirements"]


@pytest.mark.parametrize(
    "brief_text, seats",
    [
        ("Design a home with room for two residents and four dinner guests.", 6),
        ("Leave room for two desks.", 0),
        ("Seat four people at one table and two at the other.", 6),
        ("Four seats at one table and four seats at the other.", 8),
        ("Four seats at one table, and four seats at the other.", 8),
        ("Not only seating for six but also a quiet study.", 6),
        ("Keep the floor plan divided between quiet and social areas.", 0),
        ("Don't move the sofa, provide seating for six.", 6),
        ("Six seats split across two tables, and add lighting in the salon.", 6),
        ("Seating for six split between the salon and the kitchen.", 6),
        (
            "Formal salon with seating for six split between the salon and kitchen-dining room.",
            6,
        ),
        ("Three at each table, not five at one table and one at the other.", 6),
        ("Three at each table. Don't need room for eight diners.", 6),
        ("Make room for six diners.", 6),
        ("Do not seat everyone at one table.", 0),
    ],
)
def test_occupancy_and_split_requests_do_not_conflict(brief_text, seats):
    brief, questions = requirement_controls(Brief(split_dining=True), brief_text, None)
    assert not questions
    assert brief.split_dining and brief.dining_seats == seats


def test_two_table_request_needs_explicit_confirmation():
    brief, questions = requirement_controls(
        Brief(), "Seat two at one table and two at the other.", None
    )
    assert brief.dining_seats == 4 and not brief.split_dining
    assert any("Confirm separate dining tables" in item for item in questions)


def test_local_split_cannot_move_one_rooms_second_table_to_another_room():
    _, questions = requirement_controls(
        Brief(split_dining=True),
        "Request six seats split across two tables in the salon.",
        None,
    )
    assert any("salon has one modeled table" in item for item in questions)


def test_route_length_and_declined_local_width_do_not_block_general_width():
    brief, questions = requirement_controls(
        Brief(),
        "Prefer a route of 8 m between the kitchen and salon. No 90 cm passage is needed between the sofa and wall. Use an 80 cm clear passage.",
        None,
    )
    assert not questions
    assert brief.passage_m == 0.8


def test_negative_clause_does_not_erase_a_following_passage_request():
    brief, questions = requirement_controls(
        Brief(), "Don't move the sofa, keep a 90 cm clear passage.", None
    )
    assert not questions and brief.passage_m == 0.9


def test_comma_before_shared_seating_still_requires_confirming_split():
    brief, questions = requirement_controls(
        Brief(),
        "Seating for four, split between the salon and kitchen-dining room.",
        None,
    )
    assert brief.dining_seats == 4 and not brief.split_dining
    assert any("Confirm separate dining tables" in item for item in questions)


def test_specific_clearance_cannot_be_claimed_by_general_route_check():
    _, questions = requirement_controls(
        Brief(), "Keep the passage at least 90 cm between the sofa and wall.", None
    )
    assert any("90 cm clearance between specific objects" in item for item in questions)


def test_one_room_seating_does_not_become_split_dining():
    request = SimpleNamespace(
        brief=Brief(compare_tradeoffs=True, split_dining=True),
        agent_team=True,
        live=True,
        message="Include a formal salon with room for six diners.",
    )
    with pytest.raises(service.BriefClarification, match="requested 6 places there"):
        service.interpret(request, None)


def test_single_table_capacity_request_is_preserved(monkeypatch):
    def answer(schema, *args, **kwargs):
        return schema(
            priority="balanced",
            style="scandinavian",
            formal_salon=True,
            unsupported=[],
            clarification="",
        )

    monkeypatch.setattr(service.provider, "configuration", lambda _: ("mock", "mock"))
    monkeypatch.setattr(service.provider, "request", answer)
    request = SimpleNamespace(
        brief=Brief(compare_tradeoffs=True),
        agent_team=True,
        live=True,
        message="Include a formal salon. Six seats at one table.",
    )
    with pytest.raises(
        service.BriefClarification,
        match="6 dining places are still required at one table",
    ) as exc:
        service.interpret(request, None)
    assert "Can your party dine at two tables" not in str(exc.value)


def test_conflicting_control_needs_confirmation():
    request = SimpleNamespace(
        brief=Brief(compare_tradeoffs=True, passage_m=0.6),
        agent_team=True,
        live=False,
        message="Passage at least 90 cm wide. Explain the placements.",
    )
    with pytest.raises(
        service.BriefClarification, match="Confirm one modeled passage width"
    ) as exc:
        service.interpret(request, None)
    assert exc.value.reviewed["presentation_requests"] == ["Explain the placements"]


def test_hard_constraints_and_locked_room():
    with pytest.raises(ValueError, match="exhausted"):
        generate(Brief(width=9, depth=9, compare_tradeoffs=True, passage_m=1.4))
    with pytest.raises(ValueError, match="conflicting"):
        generate(
            Brief(
                room_goals=[
                    RoomGoal(room="study", relation="near", target="living"),
                    RoomGoal(room="living", relation="far", target="study"),
                ]
            )
        )
    original = generate(Brief())[0]
    next_home = generate(
        Brief(locks=["bedroom"], seed=123, compare_tradeoffs=True), original
    )[0]

    def room(home):
        return next(p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom")

    assert room(next_home)["origin"] == room(original)["origin"]
    assert room(next_home)["design"] == room(original)["design"]


@pytest.mark.parametrize("distinct", [True, False])
def test_approval_cache_and_tamper_recovery(tmp_path, monkeypatch, distinct):
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.sqlite3"))
    monkeypatch.setattr(render_queue, "_jobs", {})
    blender = tmp_path / "blender"
    blender.touch()
    snapshot = {"project": "example", "revision": 1, "home": {"rooms": []}}

    def run(argv, **kwargs):
        if argv[0] == str(blender):
            if argv[-1] == "--quick-proof":
                output = render_queue.Path(argv[-4])
                output.mkdir()
                for name in render_queue.ASSETS["proof"]:
                    (output / name).write_text(name)
                (output / "manifest.json").write_text(
                    json.dumps(
                        {
                            "rooms": [
                                {
                                    "room": {"id": "bedroom"},
                                    "cameras": [
                                        {
                                            "id": "doorway",
                                            "eye": [1, 2, 3],
                                            "target": [4, 5, 6],
                                            "fov": 45,
                                        },
                                        {
                                            "id": "desk",
                                            "eye": [2 if distinct else 1, 2, 3],
                                            "target": [4, 5, 6],
                                            "fov": 45,
                                        },
                                    ],
                                }
                            ]
                        }
                    )
                )
                (output / "saved-style-receipt.json").write_text("style")
                (output / "receipt.json").write_text(
                    json.dumps(
                        {
                            "files": {
                                name: render_queue._file_hash(output / name)
                                for name in (
                                    "manifest.json",
                                    "home.blend",
                                    "saved-style-receipt.json",
                                )
                            }
                        }
                    )
                )
            else:
                output = render_queue.Path(argv[-1])
                output.mkdir()
                for name in render_queue.ASSETS["hd"]:
                    (output / name).write_text(name)

    monkeypatch.setattr(render_queue.subprocess, "run", run)
    with pytest.raises(service.Problem, match="inspect the proof"):
        render_queue.request(snapshot, blender, "hd")
    assert render_queue.request(snapshot, blender, "proof")["state"] == "queued"

    def wait(stage):
        until = time.monotonic() + 4
        while time.monotonic() < until:
            state = render_queue.describe(snapshot, blender)[stage]["state"]
            if state in {"ready", "failed"}:
                return state
            time.sleep(0.02)
        return "timeout"

    assert wait("proof") == "ready"
    assert render_queue.request(snapshot, blender, "proof")["state"] == "ready"
    asset = render_queue.asset(snapshot, blender, "proof", "home.blend")
    asset.write_bytes(b"corrupt")
    assert render_queue.describe(snapshot, blender)["proof"]["state"] == "idle"
    asset.write_text("home.blend")
    style_receipt = asset.with_name("saved-style-receipt.json")
    style_receipt.unlink()
    assert render_queue.describe(snapshot, blender)["proof"]["state"] == "idle"
    with pytest.raises(service.Problem, match="inspect the proof"):
        render_queue.request(snapshot, blender, "hd")
    style_receipt.write_text("style")
    if distinct:
        render_queue.request(snapshot, blender, "hd")
        assert wait("hd") == "ready"
    else:
        assert render_queue.describe(snapshot, blender)["hd"]["state"] == "blocked"
        with pytest.raises(service.Problem, match="distinct doorway and desk"):
            render_queue.request(snapshot, blender, "hd")
    assert (
        render_queue.describe({**snapshot, "revision": 2}, blender)["proof"]["state"]
        == "idle"
    )
    asset.write_bytes(b"corrupt")
    assert render_queue.describe(snapshot, blender)["proof"]["state"] == "idle"
    with pytest.raises(service.Problem, match="unavailable"):
        render_queue.asset(snapshot, blender, "proof", "home.blend")
