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
    town_port = int(os.getenv("TOWN_PORT", "8790"))
    editor_port = int(os.getenv("TOWN_EDITOR_PORT", "8791"))
    if town_port == editor_port:
        raise SystemExit("Choose distinct town and editor ports.")
    for port in (town_port, editor_port):
        with socket.socket() as check:
            check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                check.bind(("127.0.0.1", port))
            except OSError as exc:
                if exc.errno != errno.EADDRINUSE:
                    raise
                raise SystemExit(
                    f"Port {port} is already in use. If Town is running, open "
                    f"http://127.0.0.1:{town_port} (town) or http://127.0.0.1:{editor_port} (editor). "
                    f"To identify the listener, run: lsof -nP -iTCP:{port} -sTCP:LISTEN"
                ) from None
    os.environ["TOWN_EDITOR_URL"] = f"http://127.0.0.1:{editor_port}"
    os.environ["TOWN_API_URL"] = f"http://127.0.0.1:{town_port}/api"
    os.environ["TOWN_SITE_URL"] = f"http://127.0.0.1:{town_port}"
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
            f"--server.port={editor_port}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
    )
    try:
        uvicorn.run("archimind.town.api:app", host="127.0.0.1", port=town_port)
    finally:
        editor.terminate()
        worker.terminate()
        editor.wait()
        worker.wait()
