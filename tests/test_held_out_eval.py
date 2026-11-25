import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "held_out_eval.py"
spec = importlib.util.spec_from_file_location("held_out_eval", SCRIPT)
held_out_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(held_out_eval)

SECRET = "Synthetic private prompt that must never be published"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_request_uses_packet_controls_and_saved_lot():
    case = {"id": "H09", "controls": {"base": "saved", "seed": 7}, "submit": SECRET}
    req = held_out_eval.request_for(case, "p", 1, {"width": 15.0, "depth": 14.0})
    assert req["brief"] == {
        "seed": 7,
        "compare_tradeoffs": True,
        "width": 15.0,
        "depth": 14.0,
    }
    assert req["base"] == 1 and req["live"] and req["agent_team"]

    fresh = {
        "id": "H08",
        "controls": {"lot_m": [12.5, 13.5], "allow_separate_tables": True},
        "submit": SECRET,
    }
    brief = held_out_eval.request_for(fresh, "p", 0)["brief"]
    assert (brief["width"], brief["depth"], brief["split_dining"], brief["seed"]) == (
        12.5,
        13.5,
        True,
        42,
    )


def matrix(tmp_path):
    class Args:
        out = str(tmp_path)
        output = str(tmp_path / "public" / "matrix.md")

    (tmp_path / "public").mkdir(exist_ok=True)
    held_out_eval.matrix(Args)
    md = (tmp_path / "public" / "matrix.md").read_text(encoding="utf-8")
    js = (tmp_path / "public" / "matrix.json").read_text(encoding="utf-8")
    return md, json.loads(js), md + js


def test_public_outputs_exclude_prompts_results_and_answers(tmp_path):
    write(
        tmp_path / "receipts" / "H01.json",
        {
            "case": "H01",
            "commit": "abc",
            "status": "failed",
            "elapsed_s": 1.0,
            "provider_calls_started": 2,
            "provider_phases": {"OpenAI · Interpret brief": ["running", "failed"]},
            "request": {"message": SECRET},
            "result": SECRET,
            "events": [{"task": SECRET}],
        },
    )
    write(
        tmp_path / "receipts" / "H05.json",
        {"case": "H05", "commit": "abc", "answer": SECRET},
    )
    write(tmp_path / "scores.json", {"H01": {"outcome": "fail", "notes": SECRET}})
    _, receipt, published = matrix(tmp_path)
    assert SECRET not in published
    run = receipt["runs"]["H01"]
    assert run["provider_phases"] == ["OpenAI · Interpret brief"]
    assert run["provider_phases_started"] == 2
    assert run["scores"] == {"outcome": "fail"}


def test_rerun_is_a_separate_row_with_its_own_score_and_commit(tmp_path):
    write(
        tmp_path / "receipts" / "H01.json",
        {"case": "H01", "commit": "aaaaaaa1", "candidate_count": 0},
    )
    write(
        tmp_path / "receipts" / "H01-rerun-2.json",
        {"case": "H01", "commit": "bbbbbbb2", "town_commit": "bbbbbbb2"},
    )
    write(
        tmp_path / "scores.json",
        {"H01": {"outcome": "fail"}, "H01-rerun-2": {"outcome": "pass"}},
    )
    md, receipt, _ = matrix(tmp_path)
    assert receipt["runs"]["H01"]["scores"]["outcome"] == "fail"
    assert receipt["runs"]["H01"]["candidate_count"] == 0
    assert receipt["runs"]["H01-rerun-2"]["scores"]["outcome"] == "pass"
    assert receipt["runs"]["H01-rerun-2"]["rerun"] is True
    assert "| H01 | " in md and "`aaaaaaa` | fail" in md
    assert "| H01-rerun-2 | " in md and "`bbbbbbb` | pass" in md


def test_receipt_from_another_case_is_rejected(tmp_path):
    write(tmp_path / "receipts" / "H01-rerun-3.json", {"case": "H02"})
    write(tmp_path / "scores.json", {})
    with pytest.raises(SystemExit, match="records case H02"):
        matrix(tmp_path)


def test_original_receipts_are_never_replaced(tmp_path):
    write(tmp_path / "receipts" / "H06.json", {"case": "H06"})
    with pytest.raises(SystemExit, match="--rerun"):
        held_out_eval.receipt_path(tmp_path, "H06", rerun=False)
    path = held_out_eval.receipt_path(tmp_path, "H06", rerun=True)
    assert path.name.startswith("H06-rerun-") and not path.exists()
    assert held_out_eval.receipt_path(tmp_path, "H05", rerun=False).name == "H05.json"


def test_a_stale_town_server_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(
        held_out_eval, "commit", lambda: {"commit": "new", "tracked_changes": False}
    )
    with pytest.raises(SystemExit, match="serve"):
        held_out_eval.town_start(tmp_path)
    write(
        tmp_path / "town-start.json",
        {"commit": "old", "tracked_changes": False, "model": "m"},
    )
    with pytest.raises(SystemExit, match="Restart"):
        held_out_eval.town_start(tmp_path)
    write(
        tmp_path / "town-start.json",
        {"commit": "new", "tracked_changes": False, "model": "m"},
    )
    assert held_out_eval.town_start(tmp_path) == {"town_commit": "new", "model": "m"}


def test_effective_model_prefers_the_shell_like_the_launcher(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_OPENAI_MODEL", "shell-model")
    assert held_out_eval.effective_model() == "shell-model"


def test_same_second_reruns_get_distinct_receipts(tmp_path, monkeypatch):
    write(tmp_path / "receipts" / "H05.json", {"case": "H05"})
    monkeypatch.setattr(held_out_eval.time, "time", lambda: 123.5)
    first = held_out_eval.receipt_path(tmp_path, "H05", rerun=True)
    write(first, {"case": "H05"})
    second = held_out_eval.receipt_path(tmp_path, "H05", rerun=True)
    assert first != second and not second.exists()
    assert sorted([first.name, second.name])[0].startswith("H05-rerun-")


def test_matrix_labels_each_rerun_with_its_run_id(tmp_path):
    write(tmp_path / "receipts" / "H05.json", {"case": "H05"})
    write(tmp_path / "receipts" / "H05-rerun-1-a.json", {"case": "H05"})
    write(tmp_path / "receipts" / "H05-rerun-1-b.json", {"case": "H05"})
    write(tmp_path / "scores.json", {})
    md, _, _ = matrix(tmp_path)
    assert "| H05-rerun-1-a | " in md and "| H05-rerun-1-b | " in md


@pytest.mark.parametrize(
    ("dotenv", "expected"),
    [
        ("ARCHIMIND_OPENAI_MODEL = spaced-model\n", "spaced-model"),
        ("ARCHIMIND_OPENAI_MODEL=first\nARCHIMIND_OPENAI_MODEL=last\n", "last"),
        ("ARCHIMIND_OPENAI_MODEL=kept\nARCHIMIND_OPENAI_MODEL=\n", "kept"),
    ],
)
def test_effective_model_reads_dotenv_like_the_launcher(
    tmp_path, monkeypatch, dotenv, expected
):
    monkeypatch.delenv("ARCHIMIND_OPENAI_MODEL", raising=False)
    (tmp_path / ".env").write_text(dotenv, encoding="utf-8")
    monkeypatch.setattr(held_out_eval, "ROOT", tmp_path)
    assert held_out_eval.effective_model() == expected
