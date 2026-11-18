"""Start the local API, durable design worker and static town on loopback."""

import errno
import os
import socket
import subprocess
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
os.environ["TOWN_MODE"] = "local"
os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("TOWN_DB", str(ROOT / "storage" / "town-designer.sqlite3"))
Path(os.environ["TOWN_DB"]).parent.mkdir(parents=True, exist_ok=True)
os.environ["TOWN_STATIC"] = str(ROOT / "dist/town")

if __name__ == "__main__":
    from archimind.town.service import initialize

    # Check both endpoints before starting children or building the site.
    for port in (8790, 8791):
        with socket.socket() as check:
            check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                check.bind(("127.0.0.1", port))
            except OSError as exc:
                if exc.errno != errno.EADDRINUSE:
                    raise
                raise SystemExit(
                    f"Port {port} is already in use. If Town is running, open "
                    "http://127.0.0.1:8790 (town) or http://127.0.0.1:8791 (editor). "
                    f"To identify the listener, run: lsof -nP -iTCP:{port} -sTCP:LISTEN"
                ) from None
    os.environ["TOWN_EDITOR_URL"] = "http://127.0.0.1:8791"
    os.environ["TOWN_API_URL"] = "http://127.0.0.1:8790/api"
    os.environ["TOWN_SITE_URL"] = "http://127.0.0.1:8790"
    for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
        os.environ.pop(key, None)
    subprocess.run(
        ["node", "frontend/realistic_viewer/town/build.mjs"], cwd=ROOT, check=True
    )
    initialize()
    worker = subprocess.Popen([sys.executable, "-m", "archimind.town.worker"], cwd=ROOT)
    editor = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "pages/Town_Editor.py",
            "--server.address=127.0.0.1",
            "--server.port=8791",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
    )
    try:
        uvicorn.run("archimind.town.api:app", host="127.0.0.1", port=8790)
    finally:
        editor.terminate()
        worker.terminate()
        editor.wait()
        worker.wait()
