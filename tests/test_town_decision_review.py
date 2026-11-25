import json
import time
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from archimind.town import decision_review, decisions, service
from archimind.town.api import app

DATA = Path(__file__).resolve().parents[1] / "docs/data"
PROJECT = DATA / "live-quality-proof/live-snapshot-r2.json"
RECEIPTS = DATA / "town-decision-reviews"


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.sqlite"))
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "12")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "12")
    monkeypatch.setenv("TOWN_CALL_RESERVE_MICROUSD", "1")
    for kind in decision_review.RUBRICS:
        monkeypatch.delenv(
            f"ARCHIMIND_TOWN_DECISIONS_{kind.upper()}_MODE", raising=False
        )
    service.initialize()
    owner = "local-designer"
    project = service.create(owner)["project"]
    home = json.loads(PROJECT.read_bytes())["home"]
    with service.transaction() as q:
        service.apply(q, owner, project, 0, home)
        service.apply(q, owner, project, 1, home)
    endpoint = f"/api/projects/{project}/decision-review"
    request = {
        "id": str(uuid4()),
        "revision": 2,
        "home_id": home["id"],
        "kind": "route",
        "message": "Please check my private question.",
        "allow_live": True,
    }
    return TestClient(app, base_url="http://localhost"), endpoint, request, project


def test_off_consent_and_scope(state, monkeypatch):
    client, endpoint, request, _ = state
    calls = []
    monkeypatch.setattr(
        decision_review, "evaluate", lambda *args, **kwargs: calls.append(args)
    )
    assert client.get(endpoint).json() == {"route": "off", "evidence": "off"}
    assert client.post(endpoint, json=request).json()["reason"] == "off"
    for consent in (False, "true", 1):
        assert (
            client.post(endpoint, json=request | {"allow_live": consent}).status_code
            == 400
        )
    assert (
        client.post(endpoint, json=request | {"home_id": "c" * 64}).status_code == 409
    )
    assert client.post(endpoint, json=request | {"revision": 3}).status_code == 404
    assert (
        client.post(
            f"/api/projects/{uuid4()}/decision-review", json=request
        ).status_code
        == 404
    )
    assert (
        client.post(
            endpoint, json=request, headers={"Origin": "https://other.example"}
        ).status_code
        == 403
    )
    assert calls == []


def test_evidence_is_scoped_and_shadow_is_private(state, monkeypatch):
    client, endpoint, request, project = state
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_EVIDENCE_MODE", "shadow")
    calls = []

    def evaluate(kind, message, *, facts, claims):
        calls.append((kind, message, facts, claims))
        return {
            "status": "checked",
            "answers": {"claim_0": {"label": "supported", "confidence": 0.99}},
        }

    monkeypatch.setattr(decision_review, "evaluate", evaluate)
    request |= {"kind": "evidence", "claims": ["Private claim."]}
    result = client.post(endpoint, json=request).json()
    assert result["mode"] == "shadow"
    assert "outcomes" not in result and "suggestions" not in result
    assert client.post(endpoint, json=request).json() == result
    assert (
        client.post(
            endpoint, json=request | {"claims": ["Different claim."]}
        ).status_code
        == 409
    )
    ((kind, _, facts, claims),) = calls
    assert kind == "evidence" and claims == ["Private claim."]
    assert facts["revision"] == 2 and facts["prior_revision"] == 1
    assert facts["bedroom_footprints"]["footprint_gap_m"] == 0.36
    assert facts["chair_displacement_m"] == 0
    assert facts["plan"]["validated_passage_check_m"] == 0.6
    assert "passage_m" not in facts["plan"]
    assert facts["bedroom_desk_to_window_centers_m"]["bedroom-window"] == 4.46
    with service.transaction() as q:
        persisted = q("SELECT result FROM town_decision_checks").fetchone()[0]
        assert "Private claim" not in persisted and "private question" not in persisted
        assert service.project(q, "local-designer", project) == 2
        assert q("SELECT count(*) FROM jobs").fetchone()[0] == 0


def test_independent_promotion_and_budget_headroom(state, monkeypatch):
    client, endpoint, request, _ = state
    for kind in decision_review.RUBRICS:
        monkeypatch.setenv(f"ARCHIMIND_TOWN_DECISIONS_{kind.upper()}_MODE", "advisory")
        monkeypatch.setenv(
            f"ARCHIMIND_TOWN_DECISIONS_{kind.upper()}_RECEIPT",
            str(RECEIPTS / f"{kind}-receipt.json"),
        )
    assert client.get(endpoint).json() == {"route": "shadow", "evidence": "advisory"}
    calls = []

    def evaluate(*_args, **_kwargs):
        calls.append(True)
        return {
            "status": "checked",
            "answers": {
                "claim_0": {"label": "missing_evidence", "confidence": 0.99},
                "claim_1": {"label": "supported", "confidence": 0.01},
            },
        }

    monkeypatch.setattr(decision_review, "evaluate", evaluate)
    request |= {"kind": "evidence", "claims": ["Need a measurement.", "Need two."]}
    for _ in range(3):
        request["id"] = str(uuid4())
        assert client.post(endpoint, json=request).json()["suggestions"] == {
            "claim_0": "missing_evidence"
        }
    assert (
        client.post(endpoint, json=request | {"id": str(uuid4())}).json()["reason"]
        == "budget"
    )
    assert len(calls) == 3
    with service.transaction() as q:
        assert service.model_calls_used(q, 0) == 3


def test_old_evidence_packet_cannot_enable_advice(tmp_path, monkeypatch):
    receipt = json.loads((RECEIPTS / "evidence-receipt.json").read_bytes())
    receipt.pop("evidence_schema")
    old = tmp_path / "old-receipt.json"
    old.write_text(json.dumps(receipt))
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_EVIDENCE_MODE", "advisory")
    monkeypatch.setenv("ARCHIMIND_TOWN_DECISIONS_EVIDENCE_RECEIPT", str(old))
    assert decision_review.settings("evidence") == ("shadow", None)


@pytest.mark.parametrize("type_", ["choice", "score"])
def test_typed_adapter(type_):
    question = {"name": "criterion", "type": type_}
    if type_ == "choice":
        question["choices"] = [{"value": "a"}, {"value": "b"}]
        labels = ("a", "b")
    else:
        question["levels"] = [{"label": "poor"}, {"label": "clear"}]
        labels = (0, 1)
    answer = SimpleNamespace(
        type=type_,
        name="criterion",
        confidence=0.75,
        choice="b",
        score=0.75,
        probabilities=[
            SimpleNamespace(value=k, probability=v)
            for k, v in zip(labels, (0.25, 0.75), strict=True)
        ],
    )
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            model=decisions.MODEL,
            answers=[answer],
            usage=SimpleNamespace(input_tokens=1),
        )

    client = SimpleNamespace(decisions=SimpleNamespace(create=create))

    def query():
        return decisions.query(
            "sample",
            [question],
            key="fixture",
            deadline=time.monotonic() + 20,
            client_factory=lambda _: nullcontext(client),
        )

    result = query()
    assert result["status"] == "checked"
    assert result["answers"]["criterion"]["confidence"] == 0.75
    answer.probabilities[0].probability = True
    assert query()["reason"] == "invalid_response"
    assert len(calls) == 2
