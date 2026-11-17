"""Start local 3D Studio with explicit server-side live creation enabled."""

import argparse
import os
import sys
from pathlib import Path


def load_settings(path, environ):
    for line in path.read_text().splitlines():
        key, separator, value = line.strip().partition("=")
        if not separator or key not in {"OPENAI_API_KEY", "ARCHIMIND_OPENAI_MODEL"}:
            continue
        value = value.strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Invalid runtime setting")
            value = value[1:-1]
        if value:
            environ.setdefault(key, value)


def main():
    parser = argparse.ArgumentParser(description="Local procedural 3D Studio")
    parser.add_argument("--port", type=int, default=8502)
    parser.add_argument(
        "--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env"
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port from 1024 to 65535")
    try:
        if args.env_file.is_file():
            load_settings(args.env_file, os.environ)
    except (OSError, ValueError):
        parser.error("Could not load the selected runtime settings")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error(
            "Server API credentials are missing. Use normal Streamlit startup for offline examples."
        )
    os.environ["ARCHIMIND_ENABLE_OPENAI_STUDIO"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    from streamlit.web import cli

    print(f"3D Studio: http://127.0.0.1:{args.port}/?workspace=studio")
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
