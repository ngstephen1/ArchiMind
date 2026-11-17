"""Record/replay of chat-interpreter answers for the prompt suite (no model calls)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catalog_chat_helpers import TEXT, extraction  # noqa: E402

from archimind.agents.catalog_conversation import reconcile_catalog_extraction
from archimind.agents.catalog_requirements import CatalogChatTurn
from archimind.datasets.prompt_eval import evaluate_recordings, record_case, replay
from archimind.datasets.prompt_suite import PromptCase

CASE = PromptCase(
    case_id="full_metric:fixture",
    style="full_metric",
    prompt=TEXT,
    expected_status="ready",
    expected_reason=None,
    expected_functions={"bed": 1, "desk": 1},
    expected_room=(5.0, 4.0, 2.7),
)


def fake_interpret(turns):
    return reconcile_catalog_extraction(extraction(), turns, mode="api_response")


def test_record_then_replay_reproduces_the_result():
    rec = record_case(CASE, fake_interpret)
    assert rec["case_id"] == CASE.case_id and rec["status"] == "ready"
    json.dumps(rec)  # JSON-ready
    again = replay(CASE, rec)
    assert again.status == "ready" and again.draft.room().width_m == 5.0


def test_replay_of_a_failure_keeps_status_and_code():
    rec = {
        "case_id": CASE.case_id,
        "status": "error",
        "error": "timeout",
        "extraction": None,
    }
    result = replay(CASE, rec)
    assert result.status == "error" and result.error.code == "timeout"


def test_evaluate_recordings_scores_and_flags_missing():
    rec = record_case(CASE, fake_interpret)
    other = PromptCase(**{**CASE.__dict__, "case_id": "feet:none", "style": "feet"})
    report = evaluate_recordings([CASE, other], {rec["case_id"]: rec})
    assert report["summary"]["cases"] == 1 and report["summary"]["passed"] == 1
    assert report["unrecorded"] == ["feet:none"]


def test_turns_are_one_user_turn():
    seen = []
    record_case(CASE, lambda turns: seen.append(turns) or fake_interpret(turns))
    assert seen[0] == (CatalogChatTurn(id=1, role="user", content=TEXT),)


def test_live_disclosure_requires_verified_pack_and_original_prompt(
    tmp_path, monkeypatch
):
    from dataclasses import replace
    from unittest.mock import Mock

    from archimind.datasets import cli
    from archimind.datasets.fixtures import build_synthetic_pack
    from archimind.datasets.pack import load_pack
    from archimind.datasets.prompt_suite import (
        bind_case,
        case_from_json,
        live_cases_allowed,
    )

    root = tmp_path / "pack"
    build_synthetic_pack(root)
    cases = tmp_path / "cases.jsonl"
    assert (
        cli.main(
            [
                "prompt-suite",
                "--pack",
                str(root),
                "--out",
                str(cases),
                "--split",
                "train",
            ]
        )
        == 0
    )
    rows = [case_from_json(json.loads(line)) for line in cases.read_text().splitlines()]
    assert rows and all(row.provider_disclosure == "denied" for row in rows)
    provider = Mock(side_effect=AssertionError("unexpected live request"))
    monkeypatch.setattr(
        "archimind.agents.catalog_conversation.interpret_catalog_conversation", provider
    )
    args = [
        "prompt-eval",
        "--cases",
        str(cases),
        "--recordings",
        str(tmp_path / "recordings"),
        "--out",
        str(tmp_path / "report"),
    ]
    assert cli.main(args) == 0
    assert cli.main(args + ["--live"]) == cli.EXIT_BLOCKED
    assert cli.main(args + ["--live", "--pack", str(root)]) == cli.EXIT_BLOCKED
    provider.assert_not_called()
    pack = load_pack(root, audience="local").pack
    src = next(s for s in pack.sources if s.source == rows[0].source)
    allowed = src.model_copy(
        update={
            "permission": src.permission.model_copy(
                update={"provider_disclosure": "allowed"}
            )
        }
    )
    permitted = replace(pack, sources=(allowed,))
    original = bind_case(rows[0], permitted)
    assert live_cases_allowed([original], permitted)
    for altered in [
        replace(original, prompt="different"),
        replace(original, snapshot_id=None),
        replace(original, source=None),
    ]:
        assert not live_cases_allowed([altered], permitted)
    assert not live_cases_allowed([original], pack)


def test_withdrawn_pack_stops_remaining_live_cases(tmp_path, monkeypatch):
    from archimind.datasets import cli, fixtures

    root = tmp_path / "allowed-pack"
    source_manifest = fixtures.source_manifest

    def permitted_source(source):
        manifest = source_manifest(source)
        return manifest.model_copy(
            update={
                "permission": manifest.permission.model_copy(
                    update={"provider_disclosure": "allowed"}
                )
            }
        )

    monkeypatch.setattr(fixtures, "source_manifest", permitted_source)
    fixtures.build_synthetic_pack(root)
    cases, recordings = tmp_path / "cases", tmp_path / "recordings"
    assert (
        cli.main(
            [
                "prompt-suite",
                "--pack",
                str(root),
                "--out",
                str(cases),
                "--split",
                "train",
            ]
        )
        == 0
    )
    calls = []

    def withdraw(turns, *, allow_live):
        assert allow_live
        calls.append(turns)
        root.rename(tmp_path / "withdrawn")
        return fake_interpret(turns)

    monkeypatch.setattr(
        "archimind.agents.catalog_conversation.interpret_catalog_conversation", withdraw
    )
    assert (
        cli.main(
            [
                "prompt-eval",
                "--cases",
                str(cases),
                "--recordings",
                str(recordings),
                "--out",
                str(tmp_path / "report"),
                "--live",
                "--pack",
                str(root),
            ]
        )
        == cli.EXIT_BLOCKED
    )
    assert len(calls) == len(recordings.read_text().splitlines()) == 1
