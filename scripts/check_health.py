"""Start a temporary headless Streamlit server, verify health, then stop it."""

import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def main() -> None:
    """Fail if the real server cannot start or return a healthy HTTP response."""
    project_root = Path(__file__).resolve().parents[1]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(project_root / "app.py"),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
    ]
    url = f"http://127.0.0.1:{port}/_stcore/health"
    with tempfile.TemporaryFile(mode="w+") as log:
        server = subprocess.Popen(
            command, cwd=project_root, stdout=log, stderr=subprocess.STDOUT
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError(
                        f"Streamlit exited before becoming healthy: {server.returncode}"
                    )
                try:
                    with urlopen(url, timeout=2) as response:
                        body = response.read().decode().strip()
                        if response.status == 200 and body == "ok":
                            print(f"Streamlit health check passed: {url} -> 200 ok")
                            return
                except URLError:
                    pass
                time.sleep(0.25)
            raise TimeoutError("Streamlit did not become healthy within 30 seconds")
        except Exception:
            log.seek(0)
            print(log.read(), file=sys.stderr)
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


if __name__ == "__main__":
    main()
