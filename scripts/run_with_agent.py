"""Start the app with the design agent on, using OPENAI_API_KEY from the local .env.

The app itself never loads .env files. This explicit launcher reads only the two
names below, passes them to the Streamlit process and never prints them.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ("OPENAI_API_KEY", "ARCHIMIND_OPENAI_MODEL")


def settings_from_dotenv(path: Path) -> dict[str, str]:
    """Return only the allowed names; every other line in the file is ignored."""
    if not path.is_file():
        return {}
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*([A-Z_]+)\s*=\s*(.*)$", line)
        if match and match.group(1) in ALLOWED:
            value = match.group(2).strip().strip("'\"")
            if value:
                found[match.group(1)] = value
    return found


def main() -> int:
    environment = {
        **settings_from_dotenv(ROOT / ".env"),
        **os.environ,
        "ARCHIMIND_ENABLE_OPENAI_AGENT": "1",
    }
    if not environment.get("OPENAI_API_KEY", "").strip():
        print("OPENAI_API_KEY was not found in the environment or .env.")
        return 1
    return subprocess.call(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"), *sys.argv[1:]],
        cwd=ROOT,
        env=environment,
    )


if __name__ == "__main__":
    raise SystemExit(main())
