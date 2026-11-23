import json
import time
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from openai import APITimeoutError
from starlette.testclient import TestClient

from archimind.town import decisions, service
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
                "selected_threshold": 0.85,
                "heldout_gate_passed": True,
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
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "7")
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
    promotion.write_text(json.dumps(data | {"requests": 36}))
    assert decisions.settings() == ("shadow", None)
