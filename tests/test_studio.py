"""Offline recipe, provider, snapshot and whole-room integration checks."""

import json
import socket
import subprocess
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError
from pydantic import ValidationError

from archimind.examples import create_sample_bedroom
from archimind.studio import provider, workflow
from archimind.studio.contracts import Part, Recipe, StudioError
from archimind.studio.fixtures import example_plan, example_recipe
from archimind.studio.workflow import build_room, propose_room, scene_payload


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError("External operation forbidden")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    for name in ("getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for name in (
        "ARCHIMIND_ENABLE_OPENAI_STUDIO",
        "OPENAI_API_KEY",
        "ARCHIMIND_OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def room():
    return create_sample_bedroom().room


@pytest.mark.parametrize("kind", ["Bedroom", "Living room", "Home office"])
def test_whole_room_offline_is_repeatable_and_preserves_openings(kind):
    r = room()
    original = r.model_dump_json()
    draft = propose_room(r, kind, "A warm contemporary room", offline=True)
    a, b = build_room(draft, 42), build_room(draft, 42)
    assert a.snapshot_id == b.snapshot_id and a.model_calls == 0
    assert a.result().candidates and a.result().status == "complete"
    assert r.model_dump_json() == original
    for candidate in a.result().candidates:
        assert candidate.design.room == r and candidate.validation.status == "passed"
        data = scene_payload(a, candidate)
        assert data["schema_version"] == 4
        assert all(b["asset_id"] is None for b in data["asset_bindings"])
        assert len(data["concept_bindings"]) == len(candidate.design.furniture)
        assert data["design"] == candidate.design.model_dump(mode="json")


@pytest.mark.parametrize(
    "update",
    [
        {"kind": "javascript"},
        {"uri": "https://bad.invalid/a"},
        {"size": [2.0, 1.0, 1.0]},
        {"center": [0.0, 0.5, 0.5]},
        {"size": [float("nan"), 0.2, 0.2]},
        {"color": "url(x)"},
    ],
)
def test_parts_reject_code_urls_outside_and_nonfinite(update):
    data = {
        "kind": "box",
        "size": [1.0, 1.0, 1.0],
        "center": [0.5, 0.5, 0.5],
        "color": "#112233",
        "roughness": 0.75,
    }
    with pytest.raises(ValidationError):
        Part.model_validate_json(json.dumps(data | update))


def test_recipe_rejects_floating_unbounded_and_material_bombs():
    good = example_recipe("table").parts[0]
    with pytest.raises(ValidationError):
        Recipe(parts=(good,))
    with pytest.raises(ValidationError):
        Recipe(parts=(good,) * 65)
    grounded = example_recipe("table").parts[-1]
    with pytest.raises(ValidationError):
        Recipe(
            parts=tuple(
                grounded.model_copy(update={"roughness": i / 10}) for i in range(9)
            )
        )


def test_scene_rejects_candidate_from_a_different_snapshot():
    draft = propose_room(room(), "Bedroom", "calm", offline=True)
    built = build_room(draft)
    candidate = built.result().candidates[0].model_copy(deep=True)
    candidate.design.furniture[0].x_m += 0.1
    with pytest.raises(StudioError):
        scene_payload(built, candidate)


def fake_factory(log, *, bad=False, nullable_reasoning=False):
    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        @property
        def responses(self):
            return self

        def parse(self, **kwargs):
            log.append(kwargs)
            schema = kwargs["text_format"]
            value = (
                example_plan("Bedroom")
                if schema.__name__ == "FurnishingPlan"
                else example_recipe("desk")
            )
            if bad:
                raise RuntimeError("private provider details must not leak")
            return SimpleNamespace(
                status="completed",
                output=[SimpleNamespace(type="reasoning", content=None)]
                if nullable_reasoning
                else [],
                output_parsed=value,
                model_dump_json=lambda: "{}",
            )

    return lambda key: Client()


def test_valid_recipe_can_follow_a_reasoning_item_without_content():
    calls = []
    recipe = provider.request(
        Recipe,
        "Test concept",
        config=("test-only-key", "mock-model"),
        deadline=time.monotonic() + 10,
        client_factory=fake_factory(calls, nullable_reasoning=True),
    )
    assert recipe == example_recipe("desk") and len(calls) == 1


def test_explicit_calls_only_and_no_browser_credentials(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.delenv("ARCHIMIND_OPENAI_MODEL", raising=False)
    log = []
    factory = fake_factory(log)
    with pytest.raises(StudioError):
        propose_room(room(), "Bedroom", "calm", client_factory=factory)
    assert log == []
    draft = propose_room(
        room(), "Bedroom", "calm", allow_live=True, client_factory=factory
    )
    assert len(log) == 1
    with pytest.raises(StudioError):
        build_room(draft, client_factory=factory)
    assert len(log) == 1
    build = build_room(draft, allow_live=True, client_factory=factory)
    assert len(log) == 1 + len(draft.plan.items)
    for call in log:
        assert call["tools"] == [] and call["tool_choice"] == "none"
        assert call["store"] is False and call["timeout"] <= 30
    payload = scene_payload(build, build.result().candidates[0])
    assert "test-only-key" not in json.dumps(payload)
    assert "test-only-key" not in build.model_dump_json()
    assert len(log) == 4


@pytest.mark.parametrize("flag,key", [("0", "x"), ("1", "")])
def test_missing_access_never_constructs_a_client(monkeypatch, flag, key):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", flag)
    monkeypatch.setenv("OPENAI_API_KEY", key)

    def forbidden(_):
        pytest.fail("unauthorized client")

    with pytest.raises(StudioError):
        propose_room(
            room(), "Bedroom", "calm", allow_live=True, client_factory=forbidden
        )


def test_plan_cannot_invent_room_dimensions_or_exceed_limits():
    r = room().model_copy(update={"width_m": 1.0})
    with pytest.raises(StudioError):
        propose_room(r, "Bedroom", "calm", offline=True)


@pytest.mark.parametrize(
    "case", ["refusal", "incomplete", "malformed", "oversize", "timeout"]
)
def test_provider_failures_are_sanitized_without_repair_or_retry(case):
    calls = []

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        @property
        def responses(self):
            return self

        def parse(self, **kwargs):
            calls.append(kwargs)
            if case == "timeout":
                raise APITimeoutError(
                    request=httpx.Request("POST", "https://api.openai.com/v1/responses")
                )
            return SimpleNamespace(
                status="incomplete" if case == "incomplete" else "completed",
                output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])]
                if case == "refusal"
                else [],
                output_parsed={"secret": "private-output"}
                if case == "malformed"
                else example_recipe("desk"),
                model_dump_json=lambda: "x" * 262145 if case == "oversize" else "{}",
            )

    with pytest.raises(StudioError) as err:
        provider.request(
            Recipe,
            "Concept request",
            config=("private-key", "mock-model"),
            deadline=time.monotonic() + 10,
            client_factory=lambda _: Client(),
        )
    assert len(calls) == 1
    assert "private-output" not in str(err.value) and "private-key" not in str(
        err.value
    )


def test_expired_deadline_prevents_a_request():
    def forbidden(_):
        pytest.fail("A spent budget must never start a client")

    with pytest.raises(StudioError, match="deadline"):
        provider.request(
            Recipe,
            "x",
            config=("test", "mock"),
            deadline=time.monotonic() - 1,
            client_factory=forbidden,
        )


def test_provider_vector_schema_is_homogeneous_and_still_exactly_three():
    # Positional tuple prefixItems are outside the documented provider subset.
    from openai.lib._pydantic import to_strict_json_schema

    schema = to_strict_json_schema(Recipe)
    assert "prefixItems" not in json.dumps(schema)
    for name in ("center", "size"):
        vector = schema["$defs"]["Part"]["properties"][name]
        assert vector["minItems"] == vector["maxItems"] == 3 and "items" in vector
    raw = example_recipe("desk").parts[0].model_dump(mode="json")
    for vector in ([0.5, 0.5], [0.5] * 4):
        with pytest.raises(ValidationError):
            Part.model_validate_json(json.dumps(raw | {"center": vector}))


def test_no_candidates_skips_recipe_requests_and_preserves_honest_outcome(monkeypatch):
    draft = propose_room(room(), "Bedroom", "calm", offline=True)
    original = build_room(draft).result()
    empty = original.model_copy(
        update={
            "status": "search_exhausted",
            "candidates": [],
            "message": "Bounded search found no alternatives",
        }
    )
    monkeypatch.setattr(workflow, "generate_layout_candidates", lambda *a, **k: empty)
    monkeypatch.setattr(provider, "configuration", lambda *a: ("test", "mock"))
    draft = draft.model_copy(update={"source": "ai_concept", "model": "mock"})
    built = build_room(
        draft,
        allow_live=True,
        client_factory=lambda _: pytest.fail("No recipe spending after exhaustion"),
    )
    assert built.result().status == "search_exhausted" and not built.result().candidates
    assert built.recipes == () and built.model_calls == 0


def test_recipe_generation_never_exceeds_two_concurrent_requests(monkeypatch):
    draft = propose_room(room(), "Bedroom", "calm", offline=True).model_copy(
        update={"source": "ai_concept", "model": "mock"}
    )
    monkeypatch.setattr(provider, "configuration", lambda *a: ("test", "mock"))
    lock, counts = threading.Lock(), {"active": 0, "maximum": 0, "calls": 0}
    barrier = threading.Barrier(2)

    def request(*a, **k):
        with lock:
            counts["active"] += 1
            counts["calls"] += 1
            counts["maximum"] = max(counts["maximum"], counts["active"])
            first_pair = counts["calls"] <= 2
        if first_pair:
            barrier.wait(timeout=5)
        with lock:
            counts["active"] -= 1
        return example_recipe("desk")

    monkeypatch.setattr(provider, "request", request)
    build_room(draft, allow_live=True)
    assert counts == {"active": 0, "maximum": 2, "calls": 3}
