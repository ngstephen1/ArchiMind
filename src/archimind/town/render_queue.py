"""Bounded, local Cycles jobs using an immutable Town revision."""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from . import service
from .design import digest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
FRONTEND = ROOT / "frontend/realistic_viewer/town"
log = logging.getLogger(__name__)
_lock = Lock()
_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="town-render")
_jobs = {}
ASSETS = {
    "proof": (
        "home.blend",
        "bedroom-doorway.png",
        "bedroom-desk.png",
        "manifest.json",
        "receipt.json",
    ),
    "hd": (
        "bedroom-doorway.png",
        "bedroom-desk.png",
        "salon-overview.png",
        "Client-Book.pdf",
        "eye-view-receipt.json",
    ),
}


def configuration():
    if os.getenv("TOWN_MODE") != "local":
        return None
    blender = os.getenv("TOWN_BLENDER_BIN")
    if not blender or not shutil.which(blender):
        return None
    return Path(shutil.which(blender)).resolve()


def _paths(snapshot, blender):
    output = Path(os.environ["TOWN_DB"]).resolve().parent / "town-renders"
    sources = [
        Path(__file__),
        *SCRIPTS.glob("render_*.py"),
        SCRIPTS / "studio_photography.py",
        SCRIPTS / "publish_studio_board.py",
        SCRIPTS / "print_revision_book.py",
        *FRONTEND.glob("*.js"),
        *FRONTEND.glob("*.mjs"),
        *FRONTEND.parent.joinpath("src").glob("*.js"),
        *ROOT.joinpath("src/archimind/_viewer_assets/packs").glob("*.json"),
    ]
    config = hashlib.sha256()
    for path in sorted(sources):
        config.update(path.relative_to(ROOT).as_posix().encode())
        config.update(hashlib.sha256(path.read_bytes()).digest())
    config.update(str((blender, blender.stat().st_mtime_ns)).encode())
    return output / digest([snapshot, config.hexdigest()])


def _file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _required(stage):
    return set(ASSETS[stage]) - ({"salon-overview.png"} if stage == "hd" else set())


def _completed(directory, stage):
    try:
        result = json.loads((directory / "town-render.json").read_bytes())
        if not _required(stage) <= result["files"].keys() or not all(
            name in ASSETS[stage] and _file_hash(directory / name) == digest
            for name, digest in result["files"].items()
        ):
            return None
        if stage == "proof":
            receipt = json.loads((directory / "receipt.json").read_bytes())
            if not {"home.blend", "manifest.json"} <= receipt[
                "files"
            ].keys() or not all(
                name == Path(name).name and _file_hash(directory / name) == digest
                for name, digest in receipt["files"].items()
            ):
                return None
        return {
            "state": "ready",
            "phase": "Completed",
            "files": result["files"],
            "seconds": result["seconds"],
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def _hd_block(proof):
    try:
        manifest = json.loads((proof / "manifest.json").read_bytes())
        bedroom = next(
            room for room in manifest["rooms"] if room["room"]["id"] == "bedroom"
        )
        cameras = {camera["id"]: camera for camera in bedroom["cameras"]}
        if any(
            cameras["doorway"][key] != cameras["desk"][key]
            for key in ("eye", "target", "fov")
        ):
            return None
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        pass
    return (
        "HD needs distinct doorway and desk camera views. The proof remains available."
    )


def _status(key, stage, directory):
    with _lock:
        job = _jobs.get((key, stage))
    if job and job["state"] in {"queued", "running"}:
        return job
    completed = _completed(directory / stage, stage)
    return completed or (job if job and job["state"] == "failed" else {"state": "idle"})


def describe(snapshot, blender):
    directory = _paths(snapshot, blender)
    stages = {stage: _status(directory.name, stage, directory) for stage in ASSETS}
    if stages["proof"]["state"] == "ready" and stages["hd"]["state"] in {
        "idle",
        "failed",
    }:
        reason = _hd_block(directory / "proof")
        if reason:
            stages["hd"] = {"state": "blocked", "phase": reason}
    return stages


def request(snapshot, blender, stage):
    if stage not in ASSETS:
        raise service.Problem("Choose proof or HD.")
    directory = _paths(snapshot, blender)
    if stage == "hd":
        if not _completed(directory / "proof", "proof"):
            raise service.Problem(
                "Finish and inspect the proof before requesting HD.", 409
            )
        reason = _hd_block(directory / "proof")
        if reason:
            raise service.Problem(reason, 409)
    existing = _completed(directory / stage, stage)
    if existing:
        return existing
    key = (directory.name, stage)
    with _lock:
        if _jobs.get(key, {}).get("state") in {"queued", "running"}:
            return _jobs[key]
        if sum(j["state"] in {"queued", "running"} for j in _jobs.values()) >= 3:
            raise service.Problem("The local render queue is full.", 429)
        for previous in list(_jobs):
            if previous != key and _jobs[previous]["state"] in {"ready", "failed"}:
                del _jobs[previous]
        _jobs[key] = {"state": "queued", "phase": "Waiting for the local renderer"}
        _worker.submit(_run, key, snapshot, blender, stage, directory)
        return _jobs[key]


def asset(snapshot, blender, stage, name):
    if stage not in ASSETS or name not in ASSETS[stage]:
        raise service.Problem("Render output unavailable.", 404)
    directory = _paths(snapshot, blender) / stage
    finished = _completed(directory, stage)
    if not finished or name not in finished["files"]:
        raise service.Problem("Render output unavailable.", 404)
    return directory / name


def _run(key, snapshot, blender, stage, directory):
    start = time.monotonic()

    def update(state, phase):
        with _lock:
            _jobs[key] = {"state": state, "phase": phase}

    def command(label, argv, output, timeout):
        update("running", label)
        with output.open("ab") as stream:
            subprocess.run(
                [str(arg) for arg in argv],
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=timeout,
            )

    def cycles(script):
        return [
            blender,
            "-b",
            "--factory-startup",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
            "-P",
            SCRIPTS / script,
            "--",
        ]

    try:
        if _paths(snapshot, blender) != directory:
            raise ValueError("Renderer settings changed while the job waited.")
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            work = Path(tmp)
            out, trace = work / "result", directory / f"{stage}.log"
            if stage == "proof":
                source, manifest, styled = (
                    work / name
                    for name in ("snapshot.json", "manifest.json", "style.json")
                )
                source.write_text(json.dumps(snapshot, separators=(",", ":")) + "\n")
                command(
                    "Exporting the saved design",
                    ["node", FRONTEND / "export-home.mjs", source, manifest],
                    trace,
                    40,
                )
                command(
                    "Resolving released furniture and materials",
                    [
                        "node",
                        FRONTEND / "export-saved-style.mjs",
                        source,
                        manifest,
                        styled,
                    ],
                    trace,
                    120,
                )
                command(
                    "Rendering the Cycles proof",
                    [
                        *cycles("render_studio_home.py"),
                        manifest,
                        out,
                        "--saved-style",
                        styled,
                        "--quick-proof",
                    ],
                    trace,
                    1800,
                )
            else:
                proof = directory / "proof"
                manifest = proof / "manifest.json"
                command(
                    "Rendering the approved revision in HD",
                    [
                        *cycles("render_studio_eye_views.py"),
                        proof,
                        manifest,
                        manifest,
                        out,
                        *(
                            ["--salon-cover"]
                            if any(
                                r["design"]["room"]["id"] == "salon"
                                for r in snapshot["home"]["rooms"]
                            )
                            else []
                        ),
                    ],
                    trace,
                    3600,
                )
                # The book writer emits derivatives outside the approved proof directory.
                board = work / "portfolio"
                shutil.copytree(proof, board, copy_function=os.link)
                command(
                    "Assembling the client presentation",
                    [
                        sys.executable,
                        SCRIPTS / "publish_studio_board.py",
                        board,
                        "--eye-views",
                        out,
                    ],
                    trace,
                    90,
                )

                # Use the same bounded Chromium print command without mutating sys.path.
                chrome = (
                    shutil.which("google-chrome")
                    or shutil.which("chromium")
                    or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                )
                command(
                    "Printing the client book",
                    [
                        chrome,
                        "--headless",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--no-pdf-header-footer",
                        f"--user-data-dir={work / 'chrome'}",
                        f"--print-to-pdf={out / 'Client-Book.pdf'}",
                        (board / "index.html").as_uri(),
                    ],
                    trace,
                    180,
                )
            files = {
                name: _file_hash(out / name)
                for name in ASSETS[stage]
                if (out / name).is_file()
            }
            if _required(stage) - files.keys():
                raise ValueError("Required render outputs missing.")
            if _paths(snapshot, blender) != directory:
                raise ValueError("Renderer settings changed during the job.")
            result = {"seconds": round(time.monotonic() - start, 1), "files": files}
            (out / "town-render.json").write_text(json.dumps(result))
            if not _completed(out, stage):
                raise ValueError("Render evidence did not verify.")
            target = directory / stage
            if target.exists():
                shutil.rmtree(target)
            out.replace(target)
        update("ready", "Completed")
    except Exception:
        log.exception("Local Town render failed")
        update("failed", "Render failed. Check the local renderer log and retry.")
