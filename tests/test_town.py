"""Town's furnished reachability, native admission and private revision workflow."""

import copy
import json
import uuid
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app
from archimind.town.design import Brief, generate, validate_home

SHOWCASE = (
    Path(__file__).resolve().parents[1] / "frontend/realistic_viewer/town/showcase.json"
)


@pytest.mark.parametrize("i", range(30))
def test_measured_briefs(i):
    brief = Brief(
        width=11 + i % 5,
        depth=11 + i % 6,
        seed=i,
        priority=["balanced", "quiet bedroom", "bright study"][i % 3],
    )
    homes = generate(brief)
    assert 1 <= len(homes) <= 2
    assert len({h["id"] for h in homes}) == len(homes)
    for h in homes:
        validate_home(h)
        assert h["width"] == brief.width and h["depth"] == brief.depth
        assert h["evidence"]["reachable_rooms"] == 5
        if brief.priority == "quiet bedroom":
            assert h["evidence"]["bedroom_center_from_front_m"] > brief.depth / 2
        if brief.priority == "bright study":
            assert h["evidence"]["study_window_width_m"] == 2.5


def test_fixture_locks_and_rejections():
    home = generate(Brief())[0]
    assert home == json.loads(SHOWCASE.read_text())
    bedroom = next(p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom")
    assert next(b for b in bedroom["asset_bindings"] if b["furniture_id"] == "belaya")[
        "envelope_sha256"
    ]
    assert (
        bedroom
        in generate(Brief(seed=499, palette="sage", locks=["bedroom"]), home)[0][
            "rooms"
        ]
    )
    with pytest.raises(ValueError, match="shell dimensions"):
        generate(Brief(width=12, locks=["bedroom"]), home)
    damaged = copy.deepcopy(home)
    damaged["rooms"][0]["design"]["room"]["doors"] = []
    with pytest.raises(ValueError, match="entrance"):
        validate_home(damaged)


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "test.db"))
    service.initialize()
    return TestClient(app, base_url="http://localhost")


def job(project, base=0, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "project": project,
        "base": base,
        "brief": {},
        **kwargs,
    }


def test_two_clients_apply_undo_and_cancel(local):
    post = local.post
    p = post("/api/projects", json={}).json()["project"]
    assert (
        post(
            "/api/projects", json={}, headers={"Origin": "https://outside.invalid"}
        ).status_code
        == 403
    )
    req = job(p)
    j = post("/api/jobs", json=req).json()["job"]
    assert post("/api/jobs", json=req).json()["job"] == j
    assert post("/api/jobs", json=job(p)).status_code == 409
    assert post("/api/jobs", json={**req, "message": "different"}).status_code == 409
    assert service.work_once()
    h = local.get("/api/jobs/" + j).json()["result"][0]
    assert local.get("/api/projects/" + p).json()["home"] is None
    for invalid_index in (True, False, 1.0, "0", -1, 2, None):
        assert (
            post("/api/jobs/" + j + "/apply", json={"index": invalid_index}).status_code
            == 400
        )
    assert local.get("/api/projects/" + p).json()["revision"] == 0
    assert post("/api/jobs/" + j + "/apply", json={"index": 0}).json()["home"] == h
    assert post("/api/jobs/" + j + "/apply", json={"index": 0}).status_code == 409
    j2 = post("/api/jobs", json=job(p, 1)).json()["job"]
    assert service.work_once()
    assert post("/api/jobs/" + j2 + "/apply", json={"index": 1}).json()["revision"] == 2
    restored = post("/api/projects/" + p + "/undo", json={"base": 2}).json()
    assert restored["revision"] == 3 and restored["home"] == h
    j3 = post("/api/jobs", json=job(p, 3)).json()["job"]
    assert post("/api/jobs/" + j3 + "/cancel", json={}).status_code == 200
    assert not service.work_once()
    assert post("/api/jobs", json=job(p, 3)).status_code == 429
    assert local.get("/api/projects/" + p + "?revision=1").json()["home"] == h


def test_owner_and_budget(local, monkeypatch):
    p = service.create("other")["project"]
    assert local.get("/api/projects/" + p).status_code == 404
    assert local.post("/api/jobs", json=job(p)).status_code == 404
    p = service.create("local-designer")["project"]
    req = job(p, message="A bright study", live=True)
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "0")
    assert local.post("/api/jobs", json=req).status_code == 400
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "1")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "0")
    monkeypatch.setenv("TOWN_CALL_RESERVE_MICROUSD", "10")
    assert local.post("/api/jobs", json=req).status_code == 429
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "10")
    j = local.post("/api/jobs", json=req).json()["job"]
    monkeypatch.setattr(
        service.provider, "configuration", lambda consent: ("mock", "mock")
    )
    seen = []

    def clarify(schema, prompt, **kwargs):
        seen.append(prompt)
        return schema(
            priority="balanced",
            palette="oak",
            lock_rooms=[],
            clarification="Which room needs daylight?",
            unsupported=[],
            lock_furniture=[],
        )

    monkeypatch.setattr(service.provider, "request", clarify)
    assert service.work_once()
    assert len(seen) == 1
    assert local.get("/api/jobs/" + j).json() == {
        "status": "failed",
        "result": "Which room needs daylight?",
    }
    assert (
        local.post("/api/jobs", json=job(p, message="retry", live=True)).status_code
        == 429
    )
    assert local.get("/api/projects/" + p).json()["revision"] == 0


def test_compound_offline_brief_preserves_unsupported_constraints():
    from archimind.town.design import interpret_offline

    brief = interpret_offline(
        Brief(), "Bright study and sage finishes; keep the bedroom."
    )
    assert (brief.priority, brief.palette, brief.locks) == (
        "bright study",
        "sage",
        ["bedroom"],
    )
    with pytest.raises(ValueError, match="Offline briefs"):
        interpret_offline(Brief(), "Quiet bedroom and add another storey")
    combined = interpret_offline(
        Brief(), "Design a five-room home with a quiet bedroom and a bright study."
    )
    assert combined.priority == "quiet bedroom and bright study"
    home = generate(combined)[0]
    assert home["evidence"]["study_window_width_m"] == 2.5
    assert home["evidence"]["bedroom_center_from_front_m"] > combined.depth / 2
    with pytest.raises(ValueError, match="one finish"):
        interpret_offline(Brief(), "oak and terracotta")


def test_specialists_execute_concurrently_and_emit_owned_history(local, monkeypatch):
    from threading import Barrier

    from archimind.town import agents

    barrier = Barrier(5, timeout=8)
    original = agents.coordinate

    def observed(req, previous, interpret, emit):
        arrived = set()

        def record(agent, state, task, artifact):
            emit(agent, state, task, artifact)
            if state == "running" and agent not in arrived:
                arrived.add(agent)
                barrier.wait()

        return original(req, previous, interpret, record)

    monkeypatch.setattr(service, "coordinate", observed)
    p = service.create("local-designer")["project"]
    j = local.post(
        "/api/jobs",
        json=job(
            p, message="Design a quiet bedroom with a writing desk and warm finishes"
        ),
    ).json()["job"]
    assert service.work_once()
    feed = local.get(f"/api/jobs/{j}/events").json()
    assert feed["status"] == "ready"
    events = feed["events"]
    assert {e["agent"] for e in events[:5]} == set("ABCDE")
    assert all(e["state"] == "running" for e in events[:5])
    assert all(e["seq"] == i for i, e in enumerate(events, 1))
    hit = next(e for e in events if e["agent"] == "B" and e["state"] == "completed")
    assert hit["artifact"]["catalog_matches"]
    homes = local.get("/api/jobs/" + j).json()["result"]
    checked = {
        e["artifact"]["candidate"]
        for e in events
        if e["agent"] == "D" and "candidate" in e["artifact"]
    }
    assert checked == {h["id"] for h in homes}
    assert local.get(f"/api/jobs/{j}/events?after=5").json()["events"] == events[5:]
    assert local.get("/api/projects/" + p).json()["latest_job"] == j
    other = service.create("other")["project"]
    private_job = service.enqueue("other", service.Request.model_validate(job(other)))[
        "job"
    ]
    assert local.get(f"/api/jobs/{private_job}/events").status_code == 404


def test_study_desk_edit_preserves_other_rooms_and_improves_measured_distance():
    from archimind.town.design import interpret_offline

    home = json.loads(SHOWCASE.read_text())
    edit = interpret_offline(
        Brief(), "Keep the bedroom and move the study desk closer to its window."
    )
    (revised,) = generate(edit, home)
    validate_home(revised)
    distances = revised["evidence"]["study_desk_window_center_distance_m"]
    assert distances["after"] < distances["before"]
    assert revised["id"] != home["id"]
    for old, new in zip(home["rooms"], revised["rooms"], strict=True):
        if old["design"]["room"]["id"] != "study":
            assert old == new
    with pytest.raises(ValueError, match="unlock"):
        generate(edit.model_copy(update={"locks": ["study"]}), home)
