"""Town's furnished reachability, native admission and private revision workflow."""

import copy
import json
import uuid
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app
from archimind.town.design import Brief, generate, interpret_offline, validate_home

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
    original = copy.deepcopy(home)
    changed = generate(Brief(seed=499, palette="sage", locks=["bedroom"]), home)[0]
    locked = next(
        part for part in changed["rooms"] if part["design"]["room"]["id"] == "bedroom"
    )
    assert {key: value for key, value in locked.items() if key != "style"} == {
        key: value for key, value in bedroom.items() if key != "style"
    }
    assert locked["style"]["style_pack"]["id"] == "japandi"
    assert home == original
    locked["design"]["room"]["windows"][0]["offset_m"] += 0.01
    assert home == original
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


def test_legacy_job_retry_accepts_disabled_service_layout(local):
    project = local.post("/api/projects").json()["project"]
    req = job(project)
    assert local.post("/api/jobs", json=req).json()["job"] == req["id"]
    with service.transaction() as q:
        (raw,) = q("SELECT request FROM jobs WHERE id=?", (req["id"],)).fetchone()
    assert '"service_layout"' not in raw
    pre_upgrade = json.loads(raw)
    pre_upgrade["brief"]["service_layout"] = False
    with service.transaction() as q:
        q("UPDATE jobs SET request=? WHERE id=?", (json.dumps(pre_upgrade), req["id"]))
    same = {**req, "brief": {"service_layout": False}}
    assert local.post("/api/jobs", json=same).json()["job"] == req["id"]
    changed = {**req, "brief": {"service_layout": True}}
    assert local.post("/api/jobs", json=changed).status_code == 409


def test_legacy_job_retry_accepts_disabled_zoning_comparison(local):
    project = local.post("/api/projects").json()["project"]
    req = job(project)
    assert local.post("/api/jobs", json=req).json()["job"] == req["id"]
    with service.transaction() as q:
        (raw,) = q("SELECT request FROM jobs WHERE id=?", (req["id"],)).fetchone()
    assert '"compare_zoning"' not in raw
    pre_upgrade = json.loads(raw)
    pre_upgrade["brief"]["compare_zoning"] = False
    pre_upgrade["brief"]["service_layout"] = False
    with service.transaction() as q:
        q("UPDATE jobs SET request=? WHERE id=?", (json.dumps(pre_upgrade), req["id"]))
    same = {**req, "brief": {"compare_zoning": False}}
    assert local.post("/api/jobs", json=same).json()["job"] == req["id"]
    changed = {**req, "brief": {"compare_zoning": True}}
    assert local.post("/api/jobs", json=changed).status_code == 409


def test_infeasible_zoning_requests_clarification_without_saving(local):
    project = local.post("/api/projects").json()["project"]
    req = job(
        project,
        brief={"width": 9, "depth": 9, "formal_salon": True, "compare_zoning": True},
    )
    identifier = local.post("/api/jobs", json=req).json()["job"]
    assert service.work_once()
    feed = local.get(f"/api/jobs/{identifier}/events").json()
    reviews = [
        event["artifact"]
        for event in feed["events"]
        if event["task"] == "Reviewable brief"
    ]
    assert feed["status"] == "failed"
    assert reviews[-1]["status"] == "needs confirmation"
    assert (
        "both a validated gallery and service-core plan" in reviews[-1]["questions"][0]
    )
    assert local.get(f"/api/projects/{project}").json()["revision"] == 0


def test_zoning_only_preserves_confirmed_program_and_room_scoped_dining():
    from archimind.town.brief_review import requirement_controls

    brief = Brief(formal_salon=True, compare_zoning=True)
    _, questions = requirement_controls(brief, "No formal salon.", None)
    assert any(
        "clearing the formal salon control" in question for question in questions
    )
    reviewed, questions = requirement_controls(
        brief, "Four seats in the kitchen-dining room.", None
    )
    assert not questions
    assert reviewed.dining_seats == 4


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
            style="scandinavian",
            clarification="Which room needs daylight?",
            unsupported=[],
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
    assert (brief.priority, brief.style, brief.locks) == (
        "bright study",
        "japandi",
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
    with pytest.raises(ValueError, match="Choose one style"):
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


def test_designer_chair_preview_apply_fallback_and_undo(local, monkeypatch):
    from types import SimpleNamespace

    from archimind.town import designer_chair
    from archimind.town.design import digest

    binding = {"concept_id": "fixture-chair", "version": "1.0.0", "sha256": "1" * 64}
    chair = SimpleNamespace(
        **binding,
        width_m=0.47,
        depth_m=0.50,
        height_m=0.83,
        name="Fixture chair",
        variant_label="Gentle back",
    )
    monkeypatch.setattr(designer_chair, "approved_chairs", lambda: ())
    assert local.get("/api/designer-chairs").json() == {"chairs": []}
    p = service.create("local-designer")["project"]
    url = f"/api/projects/{p}/designer-chair"
    old = json.loads(SHOWCASE.read_text())
    with service.transaction() as q:
        service.apply(q, "local-designer", p, 0, old)
    request = {"base": 1, "binding": binding}

    def resolve(**fields):
        if fields != binding:
            raise ValueError("Unavailable")
        return chair

    monkeypatch.setattr(designer_chair, "approved_chairs", lambda: (chair,))
    monkeypatch.setattr(designer_chair, "resolve_chair", resolve)
    assert (
        local.get("/api/designer-chairs").json()["chairs"][0]["name"] == "Fixture chair"
    )
    preview = local.post(url + "/preview", json=request).json()
    assert preview["base"] == 1
    home = preview["home"]
    room = next(r for r in home["rooms"] if r["design"]["room"]["id"] == "bedroom")
    assert room["designer_chair"] == {
        "binding": binding,
        "name": "Fixture chair",
        "dimensions_wdh_m": [0.47, 0.5, 0.83],
        "variant_label": "Gentle back",
    }
    assert home["id"] == digest({k: v for k, v in home.items() if k != "id"})
    original = copy.deepcopy(home)
    chosen = next(r for r in original["rooms"] if "designer_chair" in r)
    chosen.pop("designer_chair")
    # The chosen chair's reservation keeps it: no pack model is bound there.
    assert {
        "furniture_id": "desk-chair",
        "asset_id": None,
        "reason": "designer",
    } in chosen["style"]["bindings"]
    old_bedroom = next(
        r for r in old["rooms"] if r["design"]["room"]["id"] == "bedroom"
    )
    chosen["style"]["bindings"] = old_bedroom["style"]["bindings"]
    assert original | {"id": old["id"]} == old
    assert local.get(f"/api/projects/{p}").json()["home"] == old
    for key, value in (
        ("base", True),
        ("binding", binding | {"url": "external"}),
        ("binding", binding | {"sha256": "2" * 64}),
    ):
        assert local.post(
            url + "/preview", json=request | {key: value}
        ).status_code in (400, 409)
    other = service.create("another-designer")["project"]
    assert (
        local.post(
            f"/api/projects/{other}/designer-chair/preview", json=request
        ).status_code
        == 404
    )
    apply = request | {"preview_id": home["id"]}
    assert (
        local.post(url + "/apply", json=apply | {"preview_id": "old"}).status_code
        == 409
    )
    chair.depth_m = 0.53
    assert local.post(url + "/apply", json=apply).status_code == 400
    chair.depth_m = 0.50
    assert local.post(url + "/apply", json=apply).json() == {
        "project": p,
        "revision": 2,
        "home": home,
    }
    assert local.get(f"/api/projects/{p}").json()["home"] == home
    assert local.get(f"/api/projects/{p}?revision=1").json()["home"] == old
    assert local.post(url + "/apply", json=apply).status_code == 409
    assert local.post(url + "/preview", json=request | {"base": 2}).status_code == 409
    assert local.post(f"/api/projects/{p}/undo", json={"base": 2}).json()["home"] == old


def test_bedroom_collection_is_revision_bound_and_preserves_reservations(local):
    original = json.loads(SHOWCASE.read_bytes())
    p = service.create("local-designer")["project"]
    with service.transaction() as q:
        service.apply(q, "local-designer", p, 0, original)
    endpoint = f"/api/projects/{p}"
    records = local.get("/api/bedroom-collection").json()["concepts"]
    assert len(records) == 2
    for base, record in enumerate(records, 1):
        binding = {k: record[k] for k in ("concept_id", "version", "sha256")}
        req = {"base": base, "binding": binding}
        path = endpoint + "/bedroom-collection"
        assert (
            local.post(
                path + "/preview",
                json=req | {"binding": binding | {"sha256": "0" * 64}},
            ).status_code
            == 409
        )
        prior = local.get(endpoint).json()["home"]
        candidate = local.post(path + "/preview", json=req).json()["home"]
        bedroom = next(
            r for r in candidate["rooms"] if r["design"]["room"]["id"] == "bedroom"
        )
        assert len(bedroom["designer_collection"]) == base
        assert local.get(endpoint).json()["home"] == prior
        assert (
            local.post(
                path + "/apply", json=req | {"preview_id": candidate["id"]}
            ).json()["home"]
            == candidate
        )
        assert (
            local.post(
                path + "/apply", json=req | {"preview_id": candidate["id"]}
            ).status_code
            == 409
        )
        assert [r["design"] for r in candidate["rooms"]] == [
            r["design"] for r in original["rooms"]
        ]
        assert local.get(endpoint + "?revision=1").json()["home"] == original
    assert local.post(endpoint + "/undo", json={"base": 3}).json()["home"] == prior


@pytest.mark.parametrize(
    ("vision_fails", "salon"), [(False, False), (True, False), (False, True)]
)
def test_design_team_reviews_real_candidates_and_reserves_three_calls(
    local, monkeypatch, vision_fails, salon
):
    import base64

    from archimind.town import design_review

    for key, value in {
        "ARCHIMIND_ENABLE_OPENAI_STUDIO": "1",
        "TOWN_DAILY_MODEL_CALLS": "3",
        "TOWN_CALL_RESERVE_MICROUSD": "10",
        "TOWN_DAILY_MICROUSD": "30",
        "ARCHIMIND_ENABLE_CODEX_ADVISOR": "1",
    }.items():
        monkeypatch.setenv(key, value)
    project = service.create("local-designer")["project"]
    req = job(
        project,
        message="Plan a quiet bedroom and bright study. Keep the measured lot and five standard rooms.",
        live=True,
        agent_team=True,
    )
    if salon:
        req["brief"] = {"width": 15, "depth": 16, "formal_salon": True}
        req["message"] = "Entertain guests in a formal salon."
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert local.post("/api/jobs", json=req).status_code == 400
    monkeypatch.setenv("OPENAI_API_KEY", "fixture")
    calls = []
    images = {}
    codex = []

    def provider(schema, content, **kwargs):
        calls.append(schema)
        if schema is service.NewHomeInterpretation:
            assert {"lock_rooms", "lock_furniture"}.isdisjoint(schema.model_fields)
            return schema(
                priority="quiet bedroom",
                style="japandi",
                clarification="",
                unsupported=[],
            )
        if schema is design_review.Direction:
            return schema(
                material_direction="Linen.",
                lighting_direction="Window light.",
                tradeoff="Glare.",
            )
        assert schema is design_review.VisualReview
        for label, image in zip(content[1::2], content[2::2], strict=True):
            images[label["text"].removeprefix("Candidate ")] = base64.b64decode(
                image["image_url"].split(",", 1)[1], validate=True
            )
        if vision_fails:
            raise service.provider.StudioError("Visual review unavailable.")
        return schema(
            observation="One bedroom.",
            recommendation="Review daylight.",
            uncertainty="No luminance data.",
        )

    def advisor(req, home):
        codex.append(home["id"])
        return {"status": "failure", "message": "Codex login unavailable."}

    monkeypatch.setattr(service.provider, "request", provider)
    monkeypatch.setattr(design_review, "codex_review", advisor)
    j = local.post("/api/jobs", json=req).json()["job"]
    assert local.post("/api/jobs", json=req).json()["job"] == j
    assert service.work_once()
    result = local.get("/api/jobs/" + j).json()
    assert len(calls) == 3 and len(set(calls)) == 3 and len(codex) == 1
    assert local.get("/api/projects/" + project).json()["revision"] == 0
    assert (
        local.post(
            "/api/jobs", json=job(project, message="Again", live=True)
        ).status_code
        == 429
    )
    assert result["status"] == "ready"
    homes = result["result"]
    assert all(h["evidence"]["reachable_rooms"] == (6 if salon else 5) for h in homes)
    assert codex == [homes[0]["id"]]
    assert images == {home["id"]: design_review.plan_png(home) for home in homes}
    events = local.get(f"/api/jobs/{j}/events").json()["events"]
    visual = [e for e in events if e["task"] == "OpenAI · Review plan images"][-1]
    if vision_fails:
        assert visual["state"] == "failed"
        assert (
            local.post(f"/api/jobs/{j}/apply", json={"index": 0}).json()["home"]
            == homes[0]
        )
    else:
        assert visual["state"] == "completed"
        assert visual["artifact"]["candidate_ids"] == list(images)
    assert any(
        e["state"] == "failed" and e["task"].startswith("Codex CLI") for e in events
    )


def test_concept_image_uses_validated_saved_plan(monkeypatch):
    import base64
    from types import SimpleNamespace

    from archimind.town.design_review import plan_png

    monkeypatch.syspath_prepend(str(SHOWCASE.parents[3] / "scripts"))
    from render_ai_concept import render

    home = json.loads(SHOWCASE.read_text())
    expected = plan_png(home)
    calls = []

    def edit(**args):
        calls.append(args)
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(expected))]
        )

    assert render(home, "Sage and oak", SimpleNamespace(edit=edit)) == expected
    assert len(calls) == 1
    assert calls[0]["image"] == ("measured-plan.png", expected, "image/png")
    assert calls[0]["n"] == 1
    assert home == json.loads(SHOWCASE.read_text())


def test_entertaining_home_has_distinct_salon_and_clearance_reservations():
    brief = interpret_offline(Brief(width=15, depth=16), "entertaining guests")
    home = generate(brief)[0]
    validate_home(home)
    assert home["evidence"]["reachable_rooms"] == 6
    assert {"salon", "living", "kitchen-dining"} <= {
        p["design"]["room"]["id"] for p in home["rooms"]
    }
    salon = next(p for p in home["rooms"] if p["design"]["room"]["id"] == "salon")
    dining = next(f for f in salon["design"]["furniture"] if f["id"] == "salon-dining")
    assert dining["depth_m"] / 2 - 0.72 - 0.46 / 2 >= 0.5
    assert (
        interpret_offline(Brief(), "quiet work").priority
        == "quiet bedroom and bright study"
    )
    compact = interpret_offline(Brief(), "compact everyday living")
    assert (compact.width, compact.depth) == (10.5, 11.5)


def test_rotated_salon_uses_checked_group_footprint():
    home = generate(Brief(formal_salon=True, width=15, depth=16, seed=43))[0]
    salon = next(p for p in home["rooms"] if p["design"]["room"]["id"] == "salon")
    suite = next(f for f in salon["design"]["furniture"] if f["id"] == "salon-suite")
    assert salon["suite_yaw_deg"] == 90
    assert (suite["width_m"], suite["depth_m"]) == (2.35, 2.8)
    validate_home(home)
    suite["depth_m"] = 2
    with pytest.raises(ValueError, match="group footprint"):
        validate_home(home)


def test_chair_edit_keeps_the_original_and_revalidates():
    brief = Brief(width=15, depth=16, formal_salon=True, palette="sage")
    before = generate(brief)[0]
    frozen = copy.deepcopy(before)
    edit = interpret_offline(
        brief, "move the bedroom desk chair and terracotta finishes"
    )
    after = generate(edit, previous=before)[0]
    assert before == frozen
    assert after["id"] != before["id"]
    assert after["palette"] == "terracotta"
    move = after["evidence"]["chair_move_m"]
    assert abs(move["from_x"] - move["to_x"]) >= 0.10
    validate_home(after)
    with pytest.raises(ValueError, match="unlock"):
        generate(edit.model_copy(update={"locks": ["bedroom"]}), previous=before)


def test_controls_only_team_uses_controls_when_styling_unavailable(local, monkeypatch):
    from archimind.town import agents, design_review

    req = service.Request.model_validate(
        job(
            service.create("local-designer")["project"],
            live=True,
            agent_team=True,
            message="  ",
            brief={"priority": "bright study", "palette": "sage"},
        )
    )
    schemas = []
    monkeypatch.setattr(
        service.provider, "configuration", lambda consent: ("fixture", "fixture")
    )
    monkeypatch.setenv("ARCHIMIND_ENABLE_CODEX_ADVISOR", "0")

    def respond(schema, content, **_):
        schemas.append(schema)
        if schema is design_review.Direction:
            raise service.provider.StudioError("Stylist unavailable.")
        assert schema is design_review.VisualReview
        assert '"priority": "bright study"' in content[0]["text"]
        assert '"style": "japandi"' in content[0]["text"]
        assert '"style": null' in content[0]["text"]
        return schema(
            observation="Window visible.",
            recommendation="Check at desk height.",
            uncertainty="No lux reading.",
        )

    monkeypatch.setattr(service.provider, "request", respond)
    events = []
    homes = agents.coordinate(
        req, None, service.interpret, lambda *event: events.append(event)
    )
    assert homes and all(home["palette"] == "sage" for home in homes)
    assert schemas == [design_review.Direction, design_review.VisualReview]
    assert any(agent == "E" and state == "failed" for agent, state, *_ in events)


def test_pullout_is_a_validated_preview_of_the_saved_revision(local):
    p = service.create("local-designer")["project"]
    home = json.loads(SHOWCASE.read_text())
    with service.transaction() as q:
        service.apply(q, "local-designer", p, 0, home)
    url = f"/api/projects/{p}/chair-pullout"
    preview = local.post(url + "/preview", json={"base": 1})
    assert preview.status_code == 200, preview.text
    moved = preview.json()["home"]
    validate_home(moved)
    assert local.get(f"/api/projects/{p}").json()["home"] == home
    for old, new in zip(home["rooms"], moved["rooms"], strict=True):
        if old["design"]["room"]["id"] != "bedroom":
            assert old == new
            continue
        for a, b in zip(
            old["design"]["furniture"], new["design"]["furniture"], strict=True
        ):
            if a["id"] == "desk-chair":
                assert abs(b["y_m"] - a["y_m"]) == pytest.approx(0.30)
                assert a | {"y_m": b["y_m"]} == b
            else:
                assert a == b
    assert local.post(url + "/preview", json={"base": True}).status_code == 400
    assert local.post(url + "/preview", json={"base": 1, "y_m": 500}).status_code == 400
    other = service.create("other-owner")["project"]
    assert (
        local.post(
            f"/api/projects/{other}/chair-pullout/preview", json={"base": 1}
        ).status_code
        == 404
    )
    assert (
        local.post(url + "/apply", json={"base": 1, "preview_id": "stale"}).status_code
        == 409
    )
    data = {"base": 1, "preview_id": moved["id"]}
    assert local.post(url + "/apply", json=data).json()["home"] == moved
    assert local.post(url + "/apply", json=data).status_code == 409
    assert (
        local.post(f"/api/projects/{p}/undo", json={"base": 2}).json()["home"] == home
    )


def test_stale_chair_preview_cannot_replace_another_saved_edit(local, record_property):
    project = service.create("local-designer")["project"]
    original = json.loads(SHOWCASE.read_text())
    with service.transaction() as q:
        service.apply(q, "local-designer", project, 0, original)

    url = f"/api/projects/{project}"
    pullout = local.post(f"{url}/chair-pullout/preview", json={"base": 1})
    assert pullout.status_code == 200, pullout.text
    stale = {"base": 1, "preview_id": pullout.json()["home"]["id"]}
    catalog = local.get("/api/designer-chairs").json()["chairs"]
    binding = {key: catalog[0][key] for key in ("concept_id", "version", "sha256")}
    selection = {"base": 1, "binding": binding}
    preview = local.post(f"{url}/designer-chair/preview", json=selection)
    assert preview.status_code == 200, preview.text
    next_home = preview.json()["home"]
    assert next_home["id"] != stale["preview_id"]
    saved = local.post(
        f"{url}/designer-chair/apply",
        json=selection | {"preview_id": next_home["id"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 2
    validate_home(next_home)

    response = local.post(f"{url}/chair-pullout/apply", json=stale)
    assert response.status_code == 409 and "newer revision" in response.json()["error"]
    assert (
        local.post(f"{url}/chair-pullout/preview", json={"base": 1}).status_code == 409
    )
    head = local.get(url).json()
    assert (head["revision"], head["head"], head["home"]) == (2, 2, next_home)
    assert local.get(url, params={"revision": 1}).json()["home"] == original
    record_property(
        "stale_edit_observation",
        json.dumps(
            {
                "base_revision": stale["base"],
                "base_home_id": original["id"],
                "stale_preview_id": stale["preview_id"],
                "saved_head_revision": head["revision"],
                "saved_head_home_id": head["home"]["id"],
                "stale_apply_http_status": response.status_code,
                "stale_apply_error": response.json()["error"],
                "original_revision_unchanged": True,
            }
        ),
    )


@pytest.mark.parametrize("obstacle_kind", ["furniture", "plant"])
def test_pullout_rejects_obstructed_move(local, obstacle_kind):
    p = service.create("local-designer")["project"]
    home = json.loads(SHOWCASE.read_text())
    part = next(r for r in home["rooms"] if r["design"]["room"]["id"] == "bedroom")
    chair = next(f for f in part["design"]["furniture"] if f["id"] == "desk-chair")
    desk = next(f for f in part["design"]["furniture"] if f["id"] == "belaya")
    direction = 1 if chair["y_m"] > desk["y_m"] else -1
    obstacle = dict(chair, id="side-table", category="table", depth_m=0.05)
    obstacle["y_m"] += chair["depth_m"] + 0.1 if direction == 1 else -0.15
    if obstacle_kind == "furniture":
        part["design"]["furniture"].append(obstacle)
    else:
        part.setdefault("style", {}).setdefault("dressing", []).append(
            {**obstacle, "id": "saved-potted-plant", "kind": "plant"}
        )
    with service.transaction() as q:
        service.apply(q, "local-designer", p, 0, home)
    assert (
        local.post(
            f"/api/projects/{p}/chair-pullout/preview", json={"base": 1}
        ).status_code
        == 400
    )
    assert local.get(f"/api/projects/{p}").json()["revision"] == 1


def test_local_extra_jobs_are_date_limited_and_bounded(local, monkeypatch):
    from datetime import UTC, datetime

    p = service.create("local-designer")["project"]
    monkeypatch.setenv("OPENAI_API_KEY", "mock")
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "9")
    monkeypatch.setenv("TOWN_CALL_RESERVE_MICROUSD", "10")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "90")

    def team():
        return job(p, message="A study", live=True, agent_team=True)

    for _ in range(3):
        j = local.post("/api/jobs", json=team()).json()["job"]
        assert local.post("/api/jobs/" + j + "/cancel", json={}).status_code == 200
    for date in ("", "2001-01-01"):
        monkeypatch.setenv("TOWN_EXTRA_TEAM_JOBS_DATE", date)
        assert local.post("/api/jobs", json=team()).status_code == 429
    monkeypatch.setenv(
        "TOWN_EXTRA_TEAM_JOBS_DATE", datetime.now(UTC).date().isoformat()
    )
    assert local.post("/api/jobs", json=job(p)).status_code == 429
    for calls, micro in [("5", "90"), ("9", "50"), ("0", "90"), ("9", "0")]:
        monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", calls)
        monkeypatch.setenv("TOWN_DAILY_MICROUSD", micro)
        rejected = local.post("/api/jobs", json=team())
        assert rejected.status_code == 429
        assert "allowance" in rejected.json()["error"]
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "9")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "90")
    for _ in range(2):
        req = team()
        j = local.post("/api/jobs", json=req).json()["job"]
        assert local.post("/api/jobs", json=req).json()["job"] == j
        assert local.post("/api/jobs/" + j + "/cancel", json={}).status_code == 200
    assert local.post("/api/jobs", json=team()).status_code == 429
    req = service.Request.model_validate(team())
    monkeypatch.setenv("DATABASE_URL", "unused")
    assert service.local_extra_team_jobs(req, datetime.now(UTC).timestamp()) == 0


@pytest.mark.parametrize("explicit", [True, False])
def test_launcher_requires_date_flag(tmp_path, monkeypatch, explicit):
    import errno
    import os
    import runpy
    import socket
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts/run_town.py"
    for key in ("TOWN_MODE", "TOWN_STATIC", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TOWN_PORT", "8790")
    monkeypatch.setenv("TOWN_EDITOR_PORT", "8791")
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "unused.sqlite3"))
    monkeypatch.setenv("TOWN_EXTRA_TEAM_JOBS_DATE", "2026-11-20")
    monkeypatch.setattr(
        sys,
        "argv",
        [str(script)] + (["--extra-team-jobs-on", "2026-11-21"] if explicit else []),
    )

    def occupied(_socket, _address):
        raise OSError(errno.EADDRINUSE, "Test stops before launching the server")

    monkeypatch.setattr(socket.socket, "bind", occupied)
    with pytest.raises(SystemExit, match="already in use"):
        runpy.run_path(str(script), run_name="__main__")
    assert os.getenv("TOWN_EXTRA_TEAM_JOBS_DATE") == (
        "2026-11-21" if explicit else None
    )


def test_compound_conference_failure_offers_actionable_review(local, monkeypatch):
    p = service.create("local-designer")["project"]
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "mock")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "3")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "30")
    monkeypatch.setenv("TOWN_CALL_RESERVE_MICROUSD", "10")
    monkeypatch.setattr(
        service.provider, "configuration", lambda consent: ("mock", "mock")
    )
    calls = []

    def unresolved(schema, prompt, **kwargs):
        calls.append(prompt)
        return schema(
            priority="balanced",
            style="scandinavian",
            formal_salon=True,
            clarification="Can four total seats work?",
            unsupported=["six dining seats"],
        )

    def styling(_request):
        calls.append("initial style direction")
        return {"status": "success"}

    from archimind.town import design_review

    monkeypatch.setattr(design_review, "direction", styling)
    monkeypatch.setattr(service.provider, "request", unresolved)
    request = job(
        p,
        message="A formal salon for two hosts and four dinner guests, a quiet study. Explain the placements.",
        live=True,
        agent_team=True,
    )
    j = local.post("/api/jobs", json=request).json()["job"]
    assert service.work_once()
    result = local.get("/api/jobs/" + j).json()
    assert result["status"] == "failed"
    for expected in (
        "Can four total seats work?",
        "six dining seats",
        "four dining seats in total",
        "Compare alternatives shows the recorded room-center distances",
        "Ask about the saved design",
        "edit the brief",
    ):
        assert expected in result["result"]
    assert local.get("/api/projects/" + p).json()["revision"] == 0
    assert len(calls) == 2 and calls.count("initial style direction") == 1
    assert not service.work_once()
