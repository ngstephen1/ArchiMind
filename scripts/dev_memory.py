"""Operator-controlled, local ArchiMind handoffs. No harness hooks or transcript capture."""

import argparse
import contextlib
import fcntl
import hashlib
import http.client
import json
import os
import platform
import re
import secrets
import shutil
import signal
import socket
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

TAG = "v3.5.0"
COMMIT = "bc7faa7d847dd387e634ba8420d115b9dd4ecebe"
LOCK = {
    ("Darwin", "arm64"): (
        "macos-aarch64",
        "64c88c54eb7a953e48131dc26876e684b272f18d99ae6cb7c5553ebf792b883a",
    ),
    ("Linux", "x86_64"): (
        "linux-x86_64",
        "cb3586a98915d84042bd518e519104e6f613cb719c7184b533410d38e741d2df",
    ),
}
REPO = "ngstephen1/ArchiMind"
ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"task", "evidence", "unresolved", "next_action"}
META = {"repository", "base_commit", "branch", "author"}
WORKSPACE = "archimind"
PROJECT = "development"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def install(state):
    target, expected = LOCK[platform.system(), platform.machine()]
    with tempfile.TemporaryDirectory(dir=state) as tmp:
        archive = Path(tmp) / f"ai-memory-{target}.tar.gz"
        subprocess.run(
            [
                "gh",
                "release",
                "download",
                TAG,
                "-R",
                "akitaonrails/ai-memory",
                "-p",
                archive.name,
                "-D",
                tmp,
            ],
            check=True,
            timeout=120,
        )
        if sha(archive) != expected:
            raise ValueError("release checksum mismatch")
        binary = Path(tmp) / "ai-memory"
        with tarfile.open(archive) as tar:
            entries = [m for m in tar if m.name in {"./ai-memory", "ai-memory"}]
            if (
                len(entries) != 1
                or not entries[0].isfile()
                or entries[0].size > 300_000_000
            ):
                raise ValueError("unexpected release archive")
            with binary.open("xb") as dest, tar.extractfile(entries[0]) as source:
                shutil.copyfileobj(source, dest)
        binary.chmod(0o700)
        binary.replace(state / "ai-memory")


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args], text=True).strip()


def validate(note):
    if (
        not isinstance(note, dict)
        or note.keys() != FIELDS | META
        or note.get("repository") != REPO
    ):
        raise ValueError("unexpected repository or note fields")
    if note["author"] not in ("codex", "claude") or not re.fullmatch(
        "[0-9a-f]{40}", note["base_commit"]
    ):
        raise ValueError("invalid author or base commit")
    for value in note.values():
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.encode()) > 1000
            or any(ord(c) < 32 for c in value)
        ):
            raise ValueError("use short single-line reviewed fields")
        if re.search(
            r"sk-(?:proj-)?[A-Za-z0-9_-]{12}|gh[pousr]_[A-Za-z0-9]+|-----BEGIN .*KEY|(?:bearer|api[_-]?key|token|password)\s*[:= ]\s*\S+",
            value,
            re.I,
        ):
            raise ValueError("remove credentials before submitting")
    return note


def rpc(data, port, name, args, project=PROJECT):
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": {**args, "workspace": WORKSPACE, "project": project},
        },
    }
    token = (data / "token").read_text().strip()
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    try:
        conn.request(
            "POST",
            "/mcp",
            json.dumps(body),
            {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        response = conn.getresponse()
        raw = response.read(1_000_001)
        if response.status != 200 or len(raw) > 1_000_000:
            raise ValueError(f"local service returned {response.status}")
        result = json.loads(raw).get("result", {})
        if result.get("isError") or not result.get("content"):
            raise ValueError("local service rejected operation")
        return json.loads(result["content"][0]["text"])
    finally:
        conn.close()


def owns_listener(pid, port):
    result = subprocess.run(
        ["lsof", "-nP", "-a", "-p", str(pid), f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        capture_output=True,
        text=True,
        timeout=4,
    )
    return result.stdout.strip() == str(pid)


def prepare(data, provider):
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        with (data / "token").open("x") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    cfg = data / "archimind.toml"
    cfg.write_text(
        f'embedding_provider = "{provider}"\n[handoff]\nclaim_on_session_start = false\n[auth]\nbearer_token_file = "token"\n'
    )
    return cfg


@contextlib.contextmanager
def server(binary, data, port, project=PROJECT, provider="none"):
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (data / "operator.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with socket.socket() as check:
            check.bind(("127.0.0.1", port))
        cfg = prepare(data, provider)
        args = [
            binary,
            "--data-dir",
            data,
            "--config",
            cfg,
            "serve",
            "--transport",
            "http",
            "--bind",
            f"127.0.0.1:{port}",
            "--no-watcher",
            "--workspace",
            WORKSPACE,
            "--project",
            project,
        ]
        proc = subprocess.Popen(
            args,
            cwd=data,
            env={"PATH": "/usr/bin:/bin", "HOME": str(data)},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(150):
                if proc.poll() is not None:
                    raise RuntimeError(
                        "server exited during startup; check port and model configuration"
                    )
                if not owns_listener(proc.pid, port):
                    time.sleep(0.1)
                    continue
                try:
                    rpc(data, port, "memory_handoff_list", {"limit": 1}, project)
                    break
                except ConnectionRefusedError:
                    time.sleep(0.1)
            else:
                raise TimeoutError("startup timeout")
            yield proc
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "action",
        choices=[
            "install",
            "start",
            "stop",
            "handoff",
            "list",
            "accept",
            "export",
            "import",
        ],
    )
    p.add_argument("--file", type=Path)
    p.add_argument("--id")
    p.add_argument("--author", choices=["codex", "claude"])
    p.add_argument("--accept-stale", action="store_true")
    a = p.parse_args()
    state = Path.home() / ".local/share/archimind-ai-memory"
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = state / "handoffs"
    port = int(os.environ.get("ARCHIMIND_DEV_MEMORY_PORT", "49484"))
    if a.action == "install":
        install(state)
        return
    if a.action == "start":

        def terminate(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, terminate)
        with server(state / "ai-memory", data, port) as proc:
            marker = data / "started"
            marker.write_text(str(proc.pid))
            try:
                print(f"ArchiMind handoffs ready on loopback port {port}", flush=True)
                while marker.exists() and proc.poll() is None:
                    time.sleep(0.2)
            finally:
                marker.unlink(missing_ok=True)
        return
    if a.action == "stop":
        (data / "started").unlink(missing_ok=True)
        return
    checkout = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    remote = git("remote", "get-url", "origin").removesuffix(".git")
    if Path(checkout).resolve() != ROOT or remote.casefold() not in {
        f"https://github.com/{REPO.casefold()}",
        f"git@github.com:{REPO.casefold()}",
        f"ssh://git@github.com/{REPO.casefold()}",
    }:
        p.error("run inside the ArchiMind checkout")
    if not (data / "started").exists() or not owns_listener(
        int((data / "started").read_text()), port
    ):
        p.error("start the developer service first")
    if a.action in {"handoff", "import"}:
        if not a.file or a.file.stat().st_size > 8192:
            p.error("supply a small reviewed JSON note with --file")
        note = json.loads(a.file.read_text())
        if a.action == "handoff":
            if not a.author or not isinstance(note, dict) or note.keys() != FIELDS:
                p.error("supply --author and the four handoff fields")
            note.update(
                repository=REPO,
                branch=git("branch", "--show-current") or "(detached HEAD)",
                base_commit=git("rev-parse", "HEAD"),
                author=a.author,
            )
        summary = json.dumps(validate(note), ensure_ascii=False)
        if len(summary) > 3000:
            p.error("serialized handoff exceeds the 3000-character service limit")
        with (data / "submit.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            pending = rpc(data, port, "memory_handoff_list", {"limit": 100})
            if len(pending["handoffs"]) >= 100:
                p.error("accept an open handoff before creating another (limit 100)")
            result = rpc(data, port, "memory_handoff_begin", {"summary": summary})
        print(json.dumps(result))
        return
    rows = rpc(data, port, "memory_handoff_list", {"limit": 100})["handoffs"]
    notes = {}
    for row in rows:
        try:
            notes[row["id"]] = validate(json.loads(row["summary"]))
        except (ValueError, TypeError):
            continue
    head = git("rev-parse", "HEAD")
    if a.action == "list":
        print(
            json.dumps(
                [
                    {"id": k, "different_base": v["base_commit"] != head, **v}
                    for k, v in notes.items()
                ],
                indent=2,
            )
        )
        return
    if a.id not in notes:
        p.error("select an open handoff ID from this project")
    note = notes[a.id]
    if a.action == "export":
        if not a.file:
            p.error("supply a new output file")
        with a.file.open("x") as dest:
            dest.write(json.dumps(note, indent=2) + "\n")
        return
    if note["base_commit"] != head and not a.accept_stale:
        p.error(
            "handoff base differs from HEAD; inspect the note before --accept-stale"
        )
    got = rpc(data, port, "memory_handoff_accept", {"handoff_id": a.id}).get("handoff")
    if not got or got["id"] != a.id:
        p.error("handoff already claimed or unavailable")
    print(json.dumps(note, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from None
