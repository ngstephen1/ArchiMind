"""Publish only the stored revisions whose exported boards match the supplied examples."""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path

from archimind.town.design import digest, validate_home
from archimind.town.service import SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def export(source, output, examples):
    if output.exists():
        raise FileExistsError(output)
    records = []
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        temp = Path(scratch)
        with (
            closing(
                sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
            ) as src,
            closing(sqlite3.connect(temp / "replay.sqlite3")) as dst,
            dst,
        ):
            for statement in SCHEMA:
                dst.execute(statement)
            for example in examples:
                project = json.loads((example / "before.json").read_bytes())["project"]
                dst.execute(
                    "INSERT INTO projects VALUES(?,?,2)", (project, "local-designer")
                )
                for rev, member in ((1, "before.json"), (2, "manifest.json")):
                    row = src.execute(
                        "SELECT home FROM revisions WHERE project=? AND revision=?",
                        (project, rev),
                    ).fetchone()
                    if row is None:
                        raise ValueError(f"Missing saved revision {project}/{rev}")
                    home = json.loads(row[0])
                    validate_home(home)
                    if home["id"] != digest(
                        {k: v for k, v in home.items() if k != "id"}
                    ):
                        raise ValueError("Saved home digest mismatch")
                    snapshot, board = temp / "snapshot.json", temp / "board.json"
                    snapshot.write_text(
                        json.dumps({"project": project, "revision": rev, "home": home})
                    )
                    subprocess.run(
                        [
                            "node",
                            str(
                                ROOT / "frontend/realistic_viewer/town/export-home.mjs"
                            ),
                            str(snapshot),
                            str(board),
                        ],
                        check=True,
                    )
                    raw = board.read_bytes()
                    if raw != (example / member).read_bytes():
                        raise ValueError(
                            f"Browser export does not match {project}/{rev}"
                        )
                    dst.execute(
                        "INSERT INTO revisions VALUES(?,?,?)", (project, rev, row[0])
                    )
                    records.append(
                        {
                            "project": project,
                            "revision": rev,
                            "home_id": home["id"],
                            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                        }
                    )
            if dst.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("SQLite integrity check failed")
        # Link only a complete, closed database; an existing edition is kept intact.
        os.link(temp / "replay.sqlite3", output)
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "examples",
        type=Path,
        nargs="+",
        help="Directories with original browser exports",
    )
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output, args.examples), indent=2))
