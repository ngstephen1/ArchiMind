"""Real isolated handoff acceptance. Run after dev_memory.py install."""

import concurrent.futures
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from dev_memory import ROOT


def main():
    tool = [sys.executable, str(ROOT / "scripts/dev_memory.py")]
    binary = Path.home() / ".local/share/archimind-ai-memory/ai-memory"
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        state = home / ".local/share/archimind-ai-memory"
        state.mkdir(parents=True)
        (state / "ai-memory").symlink_to(binary)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {
            **os.environ,
            "HOME": str(home),
            "ARCHIMIND_DEV_MEMORY_PORT": str(port),
            "OPENAI_API_KEY": "synthetic-private-marker-uncaptured",
        }
        data = state / "handoffs"

        def call(*args, success=True):
            result = subprocess.run(
                [*tool, *args],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
            )
            assert (result.returncode == 0) == success, result.stderr
            return json.loads(result.stdout) if result.stdout else None

        def start():
            proc = subprocess.Popen(
                [*tool, "start"], cwd=ROOT, env=env, stdout=subprocess.PIPE, text=True
            )
            for _ in range(200):
                if (data / "started").exists():
                    return proc
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            proc.kill()
            proc.wait()
            raise AssertionError("handoff service failed to start")

        note = home / "note.json"
        note.write_text(
            json.dumps(
                dict(
                    task="Compare measured geometry",
                    evidence="Twelve public passages",
                    unresolved="Evaluate retrieval",
                    next_action="Inspect the report",
                )
            )
        )
        proc = start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
            conn.request(
                "POST",
                "/mcp",
                "{}",
                {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            assert conn.getresponse().status in {401, 403}
            conn.close()
            for author in ["claude", "codex"]:
                key = call("handoff", "--file", note, "--author", author)["handoff_id"]
                call("stop")
                proc.wait(10)
                proc = start()
                assert call("list")[0]["id"] == key
                export = home / f"{author}.json"
                call("export", "--id", key, "--file", export)
                assert json.loads(export.read_text())["author"] == author
                with concurrent.futures.ThreadPoolExecutor(2) as pool:
                    claims = list(
                        pool.map(
                            lambda _: subprocess.run(
                                [*tool, "accept", "--id", key],
                                cwd=ROOT,
                                env=env,
                                capture_output=True,
                                timeout=20,
                            ),
                            range(2),
                        )
                    )
                assert sorted(r.returncode == 0 for r in claims) == [False, True]
                assert call("list") == []
            exported = json.loads(export.read_text())
            exported["repository"] = "other/repo"
            export.write_text(json.dumps(exported))
            call("import", "--file", export, success=False)
            exported.update(repository="ngstephen1/ArchiMind", base_commit="1" * 40)
            export.write_text(json.dumps(exported))
            key = call("import", "--file", export)["handoff_id"]
            assert call("list")[0]["different_base"]
            call("accept", "--id", key, success=False)
            assert (
                call("accept", "--id", key, "--accept-stale")["base_commit"] == "1" * 40
            )
            exported["task"] = "Bearer synthetic-credential"
            export.write_text(json.dumps(exported))
            call("import", "--file", export, success=False)
            for f in data.rglob("*"):
                if f.is_file():
                    assert b"synthetic-private-marker-uncaptured" not in f.read_bytes()
            print(
                "Both handoff directions, restart, auth, claim race, transfer, stale base and credential rejection passed."
            )
        finally:
            if proc.poll() is None:
                (data / "started").unlink(missing_ok=True)
                proc.wait(10)


if __name__ == "__main__":
    main()
