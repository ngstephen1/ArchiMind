import json
import time
from types import SimpleNamespace

import pytest

from archimind.town import render_queue, service
from archimind.town.design import Brief, RoomGoal, generate, validate_home


def test_six_seats_preserved_and_explanation_routed(monkeypatch):
    def interpret(schema, prompt, **kwargs):
        facts = json.loads(prompt)
        assert "dining_seats" not in facts["controls"]
        assert "compare_tradeoffs" not in facts["controls"]
        assert facts["request"] == "Place the study far from the living room"
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

    request.brief = brief.model_copy(update={"split_dining": True})
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


def test_approval_cache_and_tamper_recovery(tmp_path, monkeypatch):
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
    render_queue.request(snapshot, blender, "hd")
    assert wait("hd") == "ready"
    assert (
        render_queue.describe({**snapshot, "revision": 2}, blender)["proof"]["state"]
        == "idle"
    )
    asset.write_bytes(b"corrupt")
    assert render_queue.describe(snapshot, blender)["proof"]["state"] == "idle"
    with pytest.raises(service.Problem, match="unavailable"):
        render_queue.asset(snapshot, blender, "proof", "home.blend")
