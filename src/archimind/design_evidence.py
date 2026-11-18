"""Local, operator-installed GBrain evidence pilot. Run python -m archimind.design_evidence."""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TAG = "v0.60.737.0"
COMMIT = "291b7996a4e2881acc921b1085d818bb9640f5d0"
UPSTREAM = "garrytan/gbrain"
BINARIES = {
    ("Darwin", "arm64"): (
        "gbrain-darwin-arm64",
        "9b62ab175935b393f7d0a125c3a3fe7d2e1099a242423b8f44837ae67b6aff62",
    ),
    ("Linux", "x86_64"): (
        "gbrain-linux-x64",
        "cf985ecd435195630862273383ed2bd4edcac0576f46d4230e0e6f66002b73d0",
    ),
}
ROOT = Path(__file__).resolve().parents[2]
# Only reviewed design vocabulary may reach upstream query bookkeeping.
VOCABULARY = frozenset(
    """
belaya desk oak charles armchair sod chair deep gentle backrest bend seat height
width depth dimensions planning reserve reservation published mixed native render
mesh placements placeholders studio house revision salon daylight window gpu cpu
palette finish finishes book client sage terracotta project manifest resolution
footprint rooms lot dining groups closed parts chair bedroom moved b074l4976t
b075x2x4xs clearance lighting glare rug window curtains revision 5 6
""".split()
)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def state_dir():
    path = Path(
        os.environ.get(
            "ARCHIMIND_EVIDENCE_HOME", Path.home() / ".local/share/archimind-gbrain"
        )
    ).resolve()
    if path.is_relative_to(ROOT) or path == Path.home():
        raise ValueError("choose a dedicated state directory outside the checkout")
    return path


def binary(state):
    name, expected = BINARIES[platform.system(), platform.machine()]
    path = state / name
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("GBrain binary differs from release lock")
    return path


def install(state):
    name, expected = BINARIES[platform.system(), platform.machine()]
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=state) as tmp:
        dest = Path(tmp) / name
        subprocess.run(
            ["gh", "release", "download", TAG, "-R", UPSTREAM, "-p", name, "-D", tmp],
            check=True,
        )
        with dest.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("release checksum mismatch")
        verified = subprocess.check_output(
            [
                "gh",
                "attestation",
                "verify",
                str(dest),
                "-R",
                UPSTREAM,
                "--source-digest",
                COMMIT,
                "--signer-workflow",
                UPSTREAM + "/.github/workflows/release.yml",
                "--format",
                "json",
            ]
        )
        if not json.loads(verified):
            raise ValueError("missing verified attestation")
        dest.chmod(0o700)
        dest.replace(state / name)


def corpus(root):
    spec = json.loads((root / "data/design_evidence/sources.json").read_bytes())
    if not re.fullmatch(r"[0-9a-f]{40}", spec["revision"]):
        raise ValueError("expected an immutable source revision")
    pages = {}
    for row in spec["passages"]:
        path = root / row["path"]
        if not path.resolve().is_relative_to(root.resolve()) or path.suffix not in {
            ".md",
            ".json",
        }:
            raise ValueError("invalid source path")
        if (
            not re.fullmatch("[a-z0-9]+(?:-[a-z0-9]+)*", row["id"])
            or row["id"] in pages
        ):
            raise ValueError("invalid or duplicate passage ID")
        raw = path.read_bytes()
        if digest(raw) != row["source_sha256"]:
            raise ValueError("source differs from reviewed version")
        text = raw.decode().splitlines()
        if not 1 <= row["first"] <= row["last"] <= len(text):
            raise ValueError("invalid citation line range")
        body = "\n".join(text[row["first"] - 1 : row["last"]])
        pages[row["id"]] = {
            "id": row["id"],
            "title": row["title"],
            "excerpt": body,
            "sha256": digest(body.encode()),
            "source_sha256": row["source_sha256"],
            "citation": f"https://github.com/ngstephen1/ArchiMind/blob/{spec['revision']}/{row['path']}#L{row['first']}-L{row['last']}",
        }
    return pages


def stamp(pages):
    return digest(json.dumps([COMMIT, pages], sort_keys=True).encode())


def invoke(executable, directory, args, timeout):
    # Bun reads cwd .env files. The directory and synthetic HOME are operator-owned.
    result = subprocess.run(
        [executable, *args],
        cwd=directory,
        stdin=subprocess.DEVNULL,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(directory),
            "GBRAIN_HOME": str(directory),
        },
        capture_output=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout


def terms(question):
    return list(
        dict.fromkeys(
            word
            for word in re.findall(r"[a-z0-9]+", question[:2000].lower())
            if word in VOCABULARY
        )
    )[:12]


def query(executable, index, words):
    payload = {
        "query": " ".join(words),
        "match": "keyword",
        "limit": 3,
        "source_id": "default",
    }
    rows = json.loads(
        invoke(
            executable,
            index,
            ["call", "--source", "default", "search", json.dumps(payload)],
            8,
        )
    )
    if not isinstance(rows, list):
        raise ValueError("invalid result envelope")
    if any(
        not isinstance(row, dict)
        or row.get("source_id") != "default"
        or row.get("stale") is not False
        or not isinstance(row.get("slug"), str)
        for row in rows
    ):
        raise ValueError("unverified search rows")
    return [row["slug"] for row in rows]


def build(state, pages):
    executable = binary(state)
    directory = Path(tempfile.mkdtemp(prefix="index-", dir=state))
    try:
        content = directory / "pages"
        content.mkdir()
        for slug, page in pages.items():
            (content / f"{slug}.md").write_text(
                f"# {page['title']}\n\n{page['excerpt']}\n"
            )
        invoke(executable, directory, ["init", "--pglite", "--no-embedding"], 90)
        invoke(executable, directory, ["transcripts", "archive", "off"], 30)
        invoke(
            executable, directory, ["config", "set", "maintenance.auto", "false"], 30
        )
        receipt = json.loads(
            invoke(
                executable,
                directory,
                ["import", str(content), "--source", "default", "--no-embed", "--json"],
                120,
            )
        )
        if receipt["errors"] or receipt["imported"] != len(pages):
            raise ValueError("incomplete import")
        first = next(iter(pages))
        page = json.loads(
            invoke(
                executable,
                directory,
                [
                    "call",
                    "--source",
                    "default",
                    "get_page",
                    json.dumps({"slug": first}),
                ],
                15,
            )
        )
        if page.get("slug") != first:
            raise ValueError("index failed readback")
        pointer = directory / "ready.json"
        pointer.write_text(
            json.dumps({"directory": directory.name, "manifest": stamp(pages)})
        )
        pointer.replace(state / "active.json")
    except BaseException:
        shutil.rmtree(directory)
        raise
    return receipt


def search_design_evidence(question, *, root=ROOT, state=None):
    """Return bounded public citations. Never use index-provided snippets or URLs."""
    state = state_dir() if state is None else state
    try:
        pages = corpus(root)
        active = json.loads((state / "active.json").read_bytes())
        if stamp(pages) != active["manifest"]:
            return {"status": "stale", "hits": []}
        if not re.fullmatch(r"index-[a-zA-Z0-9_-]+", active["directory"]):
            raise ValueError("invalid pointer")
        words = terms(question)
        ids = query(binary(state), state / active["directory"], words) if words else []
        if any(slug not in pages for slug in ids):
            raise ValueError("unknown passage")
        hits = [pages[key] for key in dict.fromkeys(ids)][:3]
        return {"status": "found" if hits else "empty", "hits": hits}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {"status": "unavailable", "hits": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "build", "search"])
    parser.add_argument("question", nargs="?")
    args = parser.parse_args()
    if (
        args.action == "build"
        and not (ROOT / "data/design_evidence/sources.json").is_file()
    ):
        parser.error("build requires an editable ArchiMind source checkout")
    state = state_dir()
    if args.action == "install":
        install(state)
    elif args.action == "build":
        print(json.dumps(build(state, corpus(ROOT))))
    else:
        if not args.question:
            parser.error("supply a design question")
        result = search_design_evidence(args.question)
        print(json.dumps({"purpose": "related passages only", **result}, indent=2))
        if result["status"] in {"stale", "unavailable"}:
            sys.exit(1)


if __name__ == "__main__":
    main()
