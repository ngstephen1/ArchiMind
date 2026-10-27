"""Offline adapter tests: every subprocess is replaced; no live model usage."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from archimind.examples.sample_bedroom import create_sample_bedroom
from archimind.integrations import CodexAdviceResult, request_codex_advice
from archimind.integrations import codex_advisor as adapter


@pytest.fixture
def design():
    return create_sample_bedroom()


@pytest.fixture
def payload(design):
    return {
        "design_analysis": "The desk could be repositioned.",
        "suggestions": [
            {
                "furniture_id": design.furniture[0].id,
                "x_m": 1.0,
                "y_m": 2.0,
                "explanation": "Consider this alternative.",
            }
        ],
        "limitations": ["Not spatially validated; no compliance claim."],
    }


@pytest.fixture
def mocked(monkeypatch, payload):
    state = SimpleNamespace(
        payload=payload,
        raw=None,
        code=0,
        calls=[],
        runs=[],
        cwd=None,
        preflight_code=0,
        auth_code=0,
        help_missing=False,
        timeout=False,
        missing_output=False,
        symlink=False,
        stopped=False,
        env=None,
    )
    monkeypatch.setenv("ARCHIMIND_ENABLE_CODEX_ADVISOR", "1")
    monkeypatch.setattr(adapter.shutil, "which", lambda _: "/usr/local/bin/codex")

    def run(command, **kwargs):
        state.runs.append((command, kwargs))
        assert kwargs["shell"] is False
        if command[-2:] == ["login", "status"]:
            return SimpleNamespace(returncode=state.auth_code)
        content = "--ask-for-approval " + " ".join(adapter._REQUIRED_FLAGS)
        kwargs["stdout"].write(b"" if state.help_missing else content.encode())
        return SimpleNamespace(returncode=state.preflight_code)

    class Process:
        pid = 123456789

        def __init__(self, command, **kwargs):
            state.calls.append((command, kwargs))
            state.cwd = Path(kwargs["cwd"])
            state.env = kwargs["env"]
            state.prompt = kwargs["stdin"].read()
            state.schema = json.loads((state.cwd / "schema.json").read_text())
            assert kwargs["shell"] is False
            assert kwargs["stdout"] == kwargs["stderr"] == subprocess.DEVNULL
            self.returncode = None
            response = state.cwd / "advice.json"
            if state.symlink:
                response.symlink_to(state.cwd / "schema.json")
            elif not state.missing_output:
                response.write_bytes(
                    state.raw
                    if state.raw is not None
                    else json.dumps(state.payload).encode()
                )

        def wait(self, timeout):
            if state.timeout and not state.stopped:
                raise subprocess.TimeoutExpired("sanitized", timeout)
            self.returncode = state.code
            return state.code

        def poll(self):
            return self.returncode

    def killpg(pid, sig):
        assert pid == Process.pid
        state.stopped = True

    monkeypatch.setattr(adapter.subprocess, "run", run)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.os, "killpg", killpg)
    return state


def call(design, goal="Improve desk access."):
    return request_codex_advice(design, goal, allow_live_usage=True)


def test_success_and_no_mutation(design, mocked):
    before = design.model_dump_json()
    result = call(design)
    assert result.status == "success"
    assert result.advice.suggestions[0].x_m == 1
    assert result.requires_spatial_validation is True
    assert design.model_dump_json() == before
    assert CodexAdviceResult.model_validate_json(result.model_dump_json()) == result
    assert mocked.cwd is not None and not mocked.cwd.exists()


def test_fixed_command_and_isolation(design, mocked, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-value")
    monkeypatch.setenv("UNRELATED_SECRET", "secret-test-value")
    goal = "Improve desk; $(touch bad) --sandbox danger-full-access"
    assert call(design, goal).status == "success"
    command, kwargs = mocked.calls[0]
    assert command == [
        "/usr/local/bin/codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--ignore-user-config",
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--skip-git-repo-check",
        "--output-schema",
        "schema.json",
        "--output-last-message",
        "advice.json",
        "--color",
        "never",
        "-",
    ]
    assert goal not in command
    assert goal in mocked.prompt.decode()
    assert mocked.cwd.parent.resolve() == Path("/tmp").resolve()
    assert kwargs["start_new_session"] is True
    assert not any("SECRET" in key or "API_KEY" in key for key in mocked.env)
    assert b"secret-test-value" not in mocked.prompt
    assert mocked.schema["$defs"]["FurniturePlacementSuggestion"]["properties"][
        "furniture_id"
    ]["enum"] == sorted(item.id for item in design.furniture)
    assert all(run[1]["timeout"] <= 5 for run in mocked.runs)


@pytest.mark.parametrize("flag", [None, "0", "true", "yes", ""])
def test_disabled_without_subprocess(design, mocked, monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("ARCHIMIND_ENABLE_CODEX_ADVISOR", raising=False)
    else:
        monkeypatch.setenv("ARCHIMIND_ENABLE_CODEX_ADVISOR", flag)
    assert call(design).error_code == "disabled"
    assert not mocked.runs and not mocked.calls


def test_explicit_authorization_required(design, mocked):
    assert request_codex_advice(design, "Help").error_code == "authorization_required"
    assert not mocked.runs


@pytest.mark.parametrize("goal", ["", "  ", None, 12])
def test_invalid_goal(design, mocked, goal):
    assert call(design, goal).error_code == "invalid_request"
    assert not mocked.runs


def test_oversized_goal(design, mocked):
    assert call(design, "a" * 2001).error_code == "request_too_large"
    assert not mocked.runs


def test_oversized_design(design, mocked):
    design.room.name = "a" * adapter.MAX_REQUEST_BYTES
    assert call(design).error_code == "request_too_large"
    assert not mocked.runs


def test_invalid_nested_model(design, mocked):
    design.furniture[0].width_m = -1
    assert call(design).error_code == "invalid_request"
    assert not mocked.runs


def test_unsupported_rotation(design, mocked):
    design.furniture[0].rotation_deg = 90
    assert call(design).error_code == "unsupported_geometry"
    assert not mocked.runs


def test_failed_layout_can_receive_advice(design, mocked):
    design.furniture[0].x_m = -1
    assert call(design).status == "success"


def test_missing_cli(design, mocked, monkeypatch):
    monkeypatch.setattr(adapter.shutil, "which", lambda _: None)
    assert call(design).error_code == "missing_cli"
    assert not mocked.runs


@pytest.mark.parametrize(
    "attribute,value,code",
    [
        ("auth_code", 1, "authentication_unavailable"),
        ("preflight_code", 2, "unsupported_cli"),
        ("help_missing", True, "unsupported_cli"),
        ("code", 2, "process_error"),
        ("missing_output", True, "io_error"),
        ("symlink", True, "io_error"),
        ("raw", b"x" * (adapter.MAX_RESPONSE_BYTES + 1), "response_too_large"),
    ],
)
def test_execution_failures(design, mocked, attribute, value, code):
    setattr(mocked, attribute, value)
    result = call(design)
    assert result.error_code == code
    assert result.advice is None
    if mocked.cwd:
        assert not mocked.cwd.exists()


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"{} trailing",
        b"\xff",
        b'{"a":1,"a":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"[" * 1500,
    ],
)
def test_malformed_json(design, mocked, raw):
    mocked.raw = raw
    assert call(design).error_code == "malformed_json"


@pytest.mark.parametrize(
    "change", ["extra", "four", "infinite", "string", "blank", "limitations"]
)
def test_schema_errors(design, mocked, change):
    if change == "extra":
        mocked.payload["is_valid"] = True
    elif change == "four":
        mocked.payload["suggestions"] *= 4
    elif change == "infinite":
        mocked.raw = json.dumps(mocked.payload).replace("1.0", "1e309").encode()
    elif change == "string":
        mocked.payload["suggestions"][0]["x_m"] = "1.0"
    elif change == "blank":
        mocked.payload["design_analysis"] = " "
    else:
        mocked.payload["limitations"] = []
    assert call(design).error_code == "invalid_schema"


def test_unknown_furniture(design, mocked):
    mocked.payload["suggestions"][0]["furniture_id"] = "invented-id"
    assert call(design).error_code == "unknown_furniture"


def test_empty_furniture_and_no_doors(design, mocked):
    design.furniture = []
    design.room.doors = []
    mocked.payload["suggestions"] = []
    assert call(design).status == "success"
    assert mocked.schema["properties"]["suggestions"]["maxItems"] == 0


def test_coordinates_are_proposals_not_validation(design, mocked):
    mocked.payload["suggestions"][0]["x_m"] = -50.0
    assert call(design).status == "success"


def test_timeout_reaps_process(design, mocked, monkeypatch):
    mocked.timeout = True
    clock = iter([0, 0, 0, 0, 0, 61])
    monkeypatch.setattr(adapter.time, "monotonic", lambda: next(clock, 61))
    assert call(design).error_code == "timeout"
    assert mocked.stopped
    assert not mocked.cwd.exists()


def test_preflight_timeout(design, mocked, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("secret-test-value", 5)

    monkeypatch.setattr(adapter.subprocess, "run", fail)
    result = call(design)
    assert result.error_code == "timeout"
    assert "secret-test-value" not in result.model_dump_json()


def test_os_error_sanitized(design, mocked, monkeypatch):
    def fail(*args, **kwargs):
        raise PermissionError("secret-test-value")

    monkeypatch.setattr(adapter.subprocess, "Popen", fail)
    result = call(design)
    assert result.error_code == "io_error"
    assert "secret-test-value" not in result.model_dump_json()


def test_result_invariants():
    with pytest.raises(ValidationError):
        CodexAdviceResult(status="success", message="Invalid")


@pytest.mark.parametrize("stage", ["run", "Popen"])
def test_executable_disappears(design, mocked, monkeypatch, stage):
    def fail(*args, **kwargs):
        raise FileNotFoundError("private-path")

    monkeypatch.setattr(adapter.subprocess, stage, fail)
    result = call(design)
    assert result.error_code == "missing_cli"
    assert "private-path" not in result.model_dump_json()


def test_deterministic_results(design, mocked):
    assert call(design).model_dump_json() == call(design).model_dump_json()


def test_failure_does_not_mutate(design, mocked):
    before = design.model_dump_json()
    mocked.raw = b"bad"
    assert call(design).error_code == "malformed_json"
    assert design.model_dump_json() == before


def test_furniture_count_limit(design, mocked):
    item = design.furniture[0]
    design.furniture = [item.model_copy(update={"id": f"item-{i}"}) for i in range(101)]
    assert call(design).error_code == "request_too_large"
    assert not mocked.runs


def test_unsupported_numeric_geometry(design, mocked):
    design.room.width_m = 1e300
    design.room.depth_m = 1e300
    assert call(design).error_code == "unsupported_geometry"
    assert not mocked.runs


def test_response_at_byte_limit(design, mocked):
    raw = json.dumps(mocked.payload).encode()
    mocked.raw = raw + b" " * (adapter.MAX_RESPONSE_BYTES - len(raw))
    assert call(design).status == "success"


def test_non_posix_fails_closed(design, mocked, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(adapter.os, "name", "nt")
        result = call(design)
    assert result.error_code == "unsupported_platform"
    assert not mocked.runs
