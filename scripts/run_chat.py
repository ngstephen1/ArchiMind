"""Explicit local chat launcher. Reads only permitted runtime settings, never evals .env."""

import argparse
import os
from pathlib import Path


def load_runtime_env(path: Path, environ) -> None:
    """Existing environment wins; read only the API key/model, without printing values."""
    for line in path.read_text().splitlines():
        key, separator, value = line.strip().partition("=")
        if not separator or key not in {"OPENAI_API_KEY", "ARCHIMIND_OPENAI_MODEL"}:
            continue
        value = value.strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Invalid quoted runtime setting")
            value = value[1:-1]
        if value and key not in environ:
            environ[key] = value


def main():
    parser = argparse.ArgumentParser(
        description="Start local ArchiMind with opt-in chat enabled"
    )
    parser.add_argument(
        "--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env"
    )
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port between 1024 and 65535")
    try:
        if args.env_file.is_file():
            load_runtime_env(args.env_file, os.environ)
    except (OSError, ValueError):
        parser.error("Could not read the selected runtime settings file")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("Server API key is unavailable; configure OPENAI_API_KEY locally")
    os.environ["ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import sys

    from streamlit.web import cli

    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).resolve().parents[1] / "app.py"),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(args.port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    raise SystemExit(cli.main())


if __name__ == "__main__":
    main()
