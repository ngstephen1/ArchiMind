import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "held_out_eval.py"
spec = importlib.util.spec_from_file_location("held_out_eval", SCRIPT)
held_out_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(held_out_eval)

SECRET = "Synthetic private prompt that must never be published"


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


def test_public_outputs_exclude_prompts_results_and_answers(tmp_path):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    (receipts / "H01.json").write_text(
        json.dumps(
            {
                "commit": "abc",
                "status": "failed",
                "elapsed_s": 1.0,
                "provider_calls_started": 2,
                "provider_phases": {"OpenAI · Interpret brief": ["running", "failed"]},
                "request": {"message": SECRET},
                "result": SECRET,
                "events": [{"task": SECRET}],
            }
        )
    )
    (receipts / "H05.json").write_text(
        json.dumps({"commit": "abc", "answer": SECRET, "provider_calls_started": 0})
    )
    (tmp_path / "scores.json").write_text(
        json.dumps({"H01": {"outcome": "fail", "notes": SECRET}})
    )

    class Args:
        out = str(tmp_path)
        output = str(tmp_path / "public" / "matrix.md")

    (tmp_path / "public").mkdir()
    held_out_eval.matrix(Args)
    published = (tmp_path / "public" / "matrix.md").read_text() + (
        tmp_path / "public" / "matrix.json"
    ).read_text()
    assert SECRET not in published
    receipt = json.loads((tmp_path / "public" / "matrix.json").read_text())
    assert receipt["cases"]["H01"]["provider_phases"] == ["OpenAI · Interpret brief"]
    assert receipt["cases"]["H01"]["scores"] == {"outcome": "fail"}
