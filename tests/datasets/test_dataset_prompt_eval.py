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
    rec = {"case_id": CASE.case_id, "status": "error", "error": "timeout", "extraction": None}
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
