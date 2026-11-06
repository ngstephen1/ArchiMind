import json
import subprocess
import sys

from archimind.datasets.cli import EXIT_BLOCKED, EXIT_FAIL, EXIT_OK, EXIT_USAGE, main


def run(capsys, *argv):
    code = main(list(argv))
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip() else None


def test_fixture_pack_then_verify(tmp_path, capsys):
    code, built = run(capsys, "fixture-pack", str(tmp_path / "p"))
    assert code == EXIT_OK and built["synthetic"] is True
    code, verified = run(capsys, "verify-pack", str(tmp_path / "p"))
    assert code == EXIT_OK and verified["snapshot_id"] == built["snapshot_id"]
    code, again = run(capsys, "fixture-pack", str(tmp_path / "p"))
    assert code == EXIT_OK and again["status"] == "exists"


def test_verify_reports_invalid_pack(tmp_path, capsys):
    (tmp_path / "p").mkdir()
    code, result = run(capsys, "verify-pack", str(tmp_path / "p"))
    assert code == EXIT_FAIL and result["reason"] == "missing_manifest"


def test_env_receipt_never_contains_secret_values(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_super_secret_value")
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    out = tmp_path / "env.json"
    code, receipt = run(
        capsys,
        "env",
        "--data-root",
        str(tmp_path),
        "--floor-gib",
        "0",
        "--out",
        str(out),
    )
    assert code == EXIT_OK
    assert receipt["secrets_present"]["HF_TOKEN"] is True
    assert receipt["secrets_present"]["KAGGLE_KEY"] is False
    assert "hf_super_secret_value" not in out.read_text()
    assert json.loads(out.read_text())["python"] == receipt["python"]


def test_env_below_floor_is_blocked(tmp_path, capsys):
    code, receipt = run(
        capsys, "env", "--data-root", str(tmp_path), "--floor-gib", "100000"
    )
    assert code == EXIT_BLOCKED and receipt["above_floor"] is False


def test_fetch_without_credential_is_blocked(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    code, result = run(
        capsys,
        "fetch",
        "https://example.invalid/x",
        str(tmp_path / "x"),
        "--max-bytes",
        "10",
        "--auth-env",
        "HF_TOKEN",
    )
    assert code == EXIT_BLOCKED and result["status"] == "blocked"


def test_fetch_rejects_plain_http(tmp_path, capsys):
    code, result = run(
        capsys,
        "fetch",
        "http://example.invalid/x",
        str(tmp_path / "x"),
        "--max-bytes",
        "10",
    )
    assert code == EXIT_FAIL and result["reason"] == "unsafe_content"


def test_sync_command(tmp_path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.txt").write_text("1")
    code, report = run(capsys, "sync", str(tmp_path / "src"), str(tmp_path / "dst"))
    assert code == EXIT_OK and report["copied"] == 1


def test_usage_errors(capsys):
    assert main([]) == EXIT_USAGE
    assert main(["nope"]) == EXIT_USAGE
    capsys.readouterr()


def test_import_has_no_side_effects_or_heavy_dependencies():
    code = (
        "import sys, archimind.datasets, archimind.datasets.cli;"
        "heavy={'streamlit','shapely','openai','plotly','langgraph','numpy'};"
        "print(sorted(m for m in sys.modules if m.split('.')[0] in heavy))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    assert out.strip() == "[]"
