"""Runtime settings use literal allowlisted values, never shell execution."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "chat_launcher", Path(__file__).resolve().parents[1] / "scripts/run_chat.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def test_allowlisted_literal_settings_and_existing_environment(tmp_path):
    config = tmp_path / "runtime.env"
    config.write_text(
        'OPENAI_API_KEY="dummy-test-value"\n'
        "ARCHIMIND_OPENAI_MODEL='test-model'\n"
        "UNRELATED=$(touch do-not-run)\n"
        "ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS=0\n"
    )
    env = {"OPENAI_API_KEY": "existing-dummy"}
    launcher.load_runtime_env(config, env)
    assert env == {
        "OPENAI_API_KEY": "existing-dummy",
        "ARCHIMIND_OPENAI_MODEL": "test-model",
    }
    assert not (tmp_path / "do-not-run").exists()


def test_bad_quotes_fail_without_echoing_value(tmp_path):
    config = tmp_path / "runtime.env"
    config.write_text('OPENAI_API_KEY="dummy-unclosed\n')
    with pytest.raises(ValueError, match="^Invalid quoted runtime setting$"):
        launcher.load_runtime_env(config, {})
