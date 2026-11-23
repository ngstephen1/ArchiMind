import json
import time
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError
from starlette.testclient import TestClient

from archimind.town import decisions, render_queue, service
from archimind.town.api import app
from archimind.town.design import validate_home
from archimind.town.design_review import Direction, VisualReview


def envelope(first=0.94, *, refusal=False):
    answers = [
        SimpleNamespace(
            name=name, probability=first if index == 0 else 0, type="predicate"
        )
        for index, name in enumerate(decisions.CRITERIA)
    ]
    if refusal:
        answers[-1].type = "refusal"
    return SimpleNamespace(
        model=decisions.MODEL, answers=answers, usage=SimpleNamespace(input_tokens=288)
    )


def adapter(reply):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if isinstance(reply, Exception):
            raise reply
        return reply

    client = SimpleNamespace(decisions=SimpleNamespace(create=create))
    result = decisions.audit(
        {"original_brief": "A private test statement"},
        key="fixture",
        deadline=time.monotonic() + 20,
        client_factory=lambda _: nullcontext(client),
    )
    return result, calls


def test_audit_batches_named_conditions_and_keeps_refusals_unknown():
    review, (call,) = adapter(envelope(refusal=True))
    assert call["model"] == "gpt-6-luna" and 0 < call["timeout"] <= 5
    assert [part["name"] for part in call["questions"]] == list(decisions.CRITERIA)
    assert review["status"] == "partial" and review["input_tokens"] == 288
    assert decisions.flagged(review, 0.85) == ["dining_requirement_missing"]
    assert review["probabilities"]["unsupported_requirement_unaddressed"] is None
    assert "private test statement" not in json.dumps(review)


@pytest.mark.parametrize("value", [True, -0.1, 1.01, float("nan")])
def test_malformed_batch_is_unavailable(value):
    result, (call,) = adapter(envelope(first=value))
    assert call["questions"] == decisions.QUESTIONS
    assert result["reason"] == "invalid_response"
    assert not decisions.flagged(result, 0.85)


def test_provider_timeout_does_not_retry():
    result, calls = adapter(
        APITimeoutError(
            request=httpx.Request("POST", "https://api.openai.com/v1/decisions")
        )
    )
    assert len(calls) == 1
    assert result["status"] == "unavailable"
    assert result["reason"] == "connection_or_timeout"


@pytest.fixture
def town(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.sqlite"))
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "12")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "12")
    monkeypatch.setenv("TOWN_CALL_RESERVE_MICROUSD", "1")
    monkeypatch.setenv("ARCHIMIND_ENABLE_CODEX_ADVISOR", "0")
    monkeypatch.delenv("ARCHIMIND_TOWN_DECISIONS_MODE", raising=False)
    monkeypatch.delenv("ARCHIMIND_TOWN_DECISIONS_PROMOTION_RECEIPT", raising=False)
    monkeypatch.delenv("TOWN_EXTRA_TEAM_JOBS_DATE", raising=False)
    promotion = tmp_path / "promotion.json"
    promotion.write_text(
        json.dumps(
            {
                "model": decisions.MODEL,
                "rubric": decisions.RUBRIC,
                "payload_profile": decisions.APP_PAYLOAD_PROFILE,
                "selected_threshold": 0.85,
                "heldout_gate_passed": True,
                "public_calibration_sha256": "a" * 64,
                "responses_complete": True,
                "requests": 6,
                "p95_ms": 500,
            }
        )
    )
    service.initialize()

    def response(schema, *_args, **_kwargs):
        if schema is Direction:
            return Direction(
                material_direction="Oak",
                lighting_direction="Daylight",
                tradeoff="Fixture",
            )
        if schema is VisualReview:
            return VisualReview(
                observation="Fixture",
                recommendation="Review the route",
                uncertainty="Fixture",
            )
        return schema(
            priority="balanced", style="scandinavian", clarification="", unsupported=[]
        )

    monkeypatch.setattr(service.provider, "request", response)
    client = TestClient(app, base_url="http://localhost")
    project = client.post("/api/projects", json={}).json()["project"]
    return client, project, promotion


def submit(town, message="Include a study.", **updates):
    client, project, _ = town
    payload = {
        "id": str(uuid4()),
        "project": project,
        "base": 0,
        "message": message,
        "live": True,
        "agent_team": True,
        "brief": {
            "compare_tradeoffs": True,
            "width": 15,
            "depth": 16,
            "formal_salon": True,
        },
    } | updates
    return client.post("/api/jobs", json=payload), payload


def review_fixture(town, monkeypatch, *, mode, flag=True, unavailable=False):
    client, _, promotion = town
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_MODE", mode)
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_PROMOTION_RECEIPT", str(promotion))
    calls = []

    def check(payload, **_kwargs):
        calls.append(payload)
        return {
            "status": "unavailable" if unavailable else "checked",
            "reason": "connection_or_timeout" if unavailable else None,
            "probabilities": {"dining_requirement_missing": 0.95 if flag else 0.1}
            if not unavailable
            else {},
        }

    monkeypatch.setattr(decisions, "audit", check)
    response, payload = submit(town)
    assert response.status_code == 200
    job = response.json()["job"]
    assert client.post("/api/jobs", json=payload).json() == {"job": job}
    assert service.work_once()
    assert not service.work_once()
    return (
        calls,
        client.get(f"/api/jobs/{job}").json(),
        client.get(f"/api/jobs/{job}/events").json()["events"],
    )


@pytest.mark.parametrize(
    ("mode", "unavailable", "completion"),
    [
        ("off", False, "ready"),
        ("shadow", False, "ready"),
        ("clarify", True, "ready"),
        ("clarify", False, "failed"),
    ],
)
def test_review_modes(town, monkeypatch, mode, unavailable, completion):
    calls, result, events = review_fixture(
        town, monkeypatch, mode=mode, unavailable=unavailable
    )
    assert len(calls) == (0 if mode == "off" else 1)
    assert result["status"] == completion
    checks = [e for e in events if e["task"] == decisions.TASK]
    assert len(checks) == (0 if mode == "off" else 2)
    if completion == "ready":
        for candidate in result["result"]:
            validate_home(candidate)
    else:
        assert "number of diners" in result["result"]
        assert not any(event["task"] == "Furnished candidate" for event in events)


def test_optional_reservation_counts_against_cap(town, monkeypatch):
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_MODE", "shadow")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "10")
    client, _, _ = town
    first, payload = submit(town)
    assert first.status_code == 200
    assert client.post("/api/jobs", json=payload).json() == first.json()
    assert client.post(f"/api/jobs/{payload['id']}/cancel", json={}).status_code == 200
    second, _ = submit(town)
    assert second.status_code == 200
    with service.transaction() as query:
        rows = query("SELECT job FROM job_brief_decisions").fetchall()
    assert rows == [(first.json()["job"],)]
    monkeypatch.setattr(
        decisions, "audit", lambda *_a, **_kw: pytest.fail("Unreserved call")
    )
    assert service.work_once()
    assert client.get(f"/api/jobs/{second.json()['job']}").json()["status"] == "ready"
    third, _ = submit(town)
    assert third.status_code == 200
    assert service.work_once()
    assert client.get(f"/api/jobs/{third.json()['job']}").json()["status"] == "ready"


def test_single_table_regression_without_decisions(town, monkeypatch):
    monkeypatch.setattr(
        decisions, "audit", lambda *_a, **_kw: pytest.fail("Unexpected call")
    )
    response, _ = submit(town, "Seat six people at a single table in the formal salon.")
    assert response.status_code == 200
    assert service.work_once()
    client, _, _ = town
    job = response.json()["job"]
    result = client.get(f"/api/jobs/{job}").json()
    assert result["status"] == "failed" and "6 dining places" in result["result"]
    trace = client.get(f"/api/jobs/{job}/events").json()["events"]
    (review,) = [e["artifact"] for e in trace if e["task"] == "Reviewable brief"]
    assert "6 dining places at one table" in review["requirements"]


def test_clarification_requires_six_case_promotion_receipt(town, monkeypatch):
    _, _, promotion = town
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_MODE", "clarify")
    assert decisions.settings() == ("shadow", None)
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_PROMOTION_RECEIPT", str(promotion))
    assert decisions.settings() == ("clarify", 0.85)
    data = json.loads(promotion.read_text())
    promotion.write_text(json.dumps(data | {"payload_profile": None}))
    assert decisions.settings() == ("shadow", None)
    promotion.write_text(json.dumps(data | {"requests": 36}))
    assert decisions.settings() == ("shadow", None)


def test_saved_edit_and_proof_retry_use_no_decisions_calls(town, monkeypatch):
    calls, result, events = review_fixture(town, monkeypatch, mode="shadow", flag=False)
    assert result["status"] == "ready"
    client, project, _ = town
    job = events[0]["run"]
    assert client.post(f"/api/jobs/{job}/apply", json={"index": 0}).status_code == 200
    url = f"/api/projects/{project}"
    assert (
        client.post(f"{url}/chair-pullout/preview", json={"base": 1}).status_code == 200
    )
    assert client.get(f"{url}?revision=1").json()["home"] == result["result"][0]

    monkeypatch.setattr(render_queue, "configuration", lambda: object())
    seen = []

    def start(snapshot, _blender, stage):
        assert snapshot["revision"] == 1 and stage == "proof"
        seen.append(stage)
        return {"state": "failed" if len(seen) == 1 else "queued"}

    monkeypatch.setattr(render_queue, "request", start)
    assert (
        client.post(f"{url}/render?revision=1", json={"stage": "proof"}).json()["state"]
        == "failed"
    )
    assert (
        client.post(f"{url}/render?revision=1", json={"stage": "proof"}).json()["state"]
        == "queued"
    )
    assert seen == ["proof", "proof"] and len(calls) == 1


@pytest.mark.parametrize(
    ("message", "formal_salon", "dining_seats", "split_dining", "expected_seats"),
    [
        (
            "Seat four guests at one table in the salon and two residents at a separate table in the kitchen.",
            True,
            6,
            True,
            6,
        ),
        ("Seat four people at a single table in the formal salon.", True, 0, False, 4),
        (
            "We cannot seat six people at a single table. Use four dining places instead.",
            True,
            4,
            False,
            4,
        ),
        (
            "Seat four people at a single table in the kitchen-dining room.",
            False,
            0,
            False,
            None,
        ),
    ],
)
def test_supported_table_phrasing_keeps_existing_path(
    town, message, formal_salon, dining_seats, split_dining, expected_seats
):
    response, _ = submit(
        town,
        message,
        brief={
            "compare_tradeoffs": True,
            "width": 15,
            "depth": 16,
            "formal_salon": formal_salon,
            "dining_seats": dining_seats,
            "split_dining": split_dining,
        },
    )
    assert response.status_code == 200
    assert service.work_once()
    client, _, _ = town
    result = client.get(f"/api/jobs/{response.json()['job']}").json()
    if not formal_salon:
        assert result["status"] == "failed", result
        assert "five-room program" in result["result"]
        return
    assert result["status"] == "ready", result
    for candidate in result["result"]:
        plan = candidate["evidence"]["comparison"]
        assert plan["required_dining_seats"] == expected_seats
        assert plan["split_dining"] is split_dining
        assert plan["dining_places"] == {"kitchen-dining": 4, "salon": 4}


def test_calibration_holdout_accepts_pairs_without_public_reuse(monkeypatch):
    import runpy
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    api = runpy.run_path(str(scripts / "evaluate_town_decisions.py"))

    def example(brief, seats):
        return {"input": {"original_brief": brief, "proposed_brief": {"seats": seats}}}

    pair = [example("Seat six diners", 6), example("Seat six diners", 4)]
    assert api["distinct_holdout"](pair, [example("Seat four diners", 4)])
    assert not api["distinct_holdout"](pair + pair[:1], [])
    assert not api["distinct_holdout"](pair, [example("SEAT  SIX diners", 3)])


def test_historical_reduced_cases_cannot_qualify_runtime_payloads(monkeypatch):
    import runpy
    from pathlib import Path

    from archimind.town.brief_review import review_summary
    from archimind.town.design import Brief

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    api = runpy.run_path(str(scripts / "evaluate_town_decisions.py"))
    old = json.loads(
        (scripts.parent / "docs/data/town-decisions/public-cases.json").read_bytes()
    )["cases"]
    assert len(old) == 36
    assert api["reviewed_payload_profile"](old) is None
    current = [
        {
            "input": {
                "confirmed_controls": {},
                "proposed_brief": review_summary(Brief(compare_tradeoffs=True)),
            }
        }
    ]
    assert api["reviewed_payload_profile"](current) == decisions.APP_PAYLOAD_PROFILE
    current[0]["input"]["proposed_brief"] = review_summary(
        Brief(width=15, depth=16, compare_tradeoffs=True),
        controls={"width"},
        previous={"evidence": {"comparison": {"passage_m": 0.6}}},
    )
    assert {
        source["origin"] for source in current[0]["input"]["proposed_brief"]["sources"]
    } >= {"controls", "saved revision"}
    assert api["reviewed_payload_profile"](current) == decisions.APP_PAYLOAD_PROFILE
    for field in ("sources", "assumptions"):
        reduced = current[0]["input"]["proposed_brief"] | {field: []}
        altered = [{"input": current[0]["input"] | {"proposed_brief": reduced}}]
        assert api["reviewed_payload_profile"](altered) is None


def test_evaluator_validates_input_before_a_dry_run_or_provider_request(
    monkeypatch, tmp_path
):
    import runpy
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    api = runpy.run_path(str(scripts / "evaluate_town_decisions.py"))
    broken = tmp_path / "invalid.json"
    broken.write_text(
        json.dumps({"cases": [{"case": "case", "expected_flags": [], "input": None}]})
    )
    monkeypatch.setattr(sys, "argv", ["evaluate", "--cases", str(broken)])
    monkeypatch.setattr(
        decisions, "audit", lambda *_a, **_kw: pytest.fail("Unexpected call")
    )
    with pytest.raises(SystemExit) as error:
        api["main"]()
    assert error.value.code == 2


def test_evaluator_never_overwrites_an_input_or_existing_receipt(monkeypatch, tmp_path):
    import runpy
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    api = runpy.run_path(str(scripts / "evaluate_town_decisions.py"))
    source = tmp_path / "cases.json"
    raw = json.dumps(
        {
            "cases": [
                {
                    "case": "test",
                    "expected_flags": [],
                    "input": {
                        "original_brief": "A bedroom",
                        "confirmed_controls": {},
                        "proposed_brief": {},
                    },
                }
            ]
        }
    ).encode()
    source.write_bytes(raw)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate", "--live", "--cases", str(source), "--output", str(source)],
    )
    monkeypatch.setenv("OPENAI_API_KEY", "fixture")
    monkeypatch.setattr(
        decisions, "audit", lambda *_a, **_kw: pytest.fail("Unexpected call")
    )
    with pytest.raises(SystemExit) as error:
        api["main"]()
    assert error.value.code == 2
    assert source.read_bytes() == raw
