"""The launcher reads only its two named settings from .env."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "run_with_agent", ROOT / "scripts" / "run_with_agent.py"
)
launcher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launcher)


def test_only_allowed_names_are_read(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        'OPENAI_API_KEY="abc"\nOTHER_SECRET=nope\n# OPENAI_API_KEY=commented\n'
        "ARCHIMIND_ENABLE_OPENAI_STYLIST=1\n",
        encoding="utf-8",
    )
    assert launcher.settings_from_dotenv(env) == {"OPENAI_API_KEY": "abc"}


def test_missing_file_gives_no_settings(tmp_path: Path) -> None:
    assert launcher.settings_from_dotenv(tmp_path / ".env") == {}
