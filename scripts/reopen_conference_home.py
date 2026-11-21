"""Create an offline Town replay database from the shipped, validated revisions."""

import argparse
import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from archimind.town.design import digest, validate_home
from archimind.town.service import SCHEMA

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/data/conference-sprint"


def reopen(target: Path) -> None:
    """Recreate the two recorded revisions in a new, independently writable file."""
    if target.exists():
        raise FileExistsError(target)
    with TemporaryDirectory(dir=target.parent) as temp:
        work = Path(temp)
        draft = work / "replay.sqlite3"
        with closing(sqlite3.connect(draft)) as db, db:
            for statement in SCHEMA:
                db.execute(statement)
            project = None
            for revision, board_file in [(1, "before.json"), (2, "manifest.json")]:
                source = EVIDENCE / f"snapshot-r{revision}.json"
                record = json.loads(source.read_bytes())
                home = record["home"]
                validate_home(home)
                if (
                    record["revision"] != revision
                    or digest({k: v for k, v in home.items() if k != "id"})
                    != home["id"]
                ):
                    raise ValueError(f"Invalid saved revision {revision}")
                if project is None:
                    project = record["project"]
                    db.execute(
                        "INSERT INTO projects VALUES(?,?,?)",
                        (project, "local-designer", 2),
                    )
                if record["project"] != project:
                    raise ValueError("The revisions belong to different projects.")
                board = work / board_file
                subprocess.run(
                    [
                        "node",
                        str(ROOT / "frontend/realistic_viewer/town/export-home.mjs"),
                        str(source),
                        str(board),
                    ],
                    check=True,
                )
                if board.read_bytes() != (EVIDENCE / board_file).read_bytes():
                    raise ValueError(f"Manifest mismatch for revision {revision}")
                db.execute(
                    "INSERT INTO revisions VALUES(?,?,?)",
                    (project, revision, json.dumps(home, separators=(",", ":"))),
                )
        target.hardlink_to(draft)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    reopen(parser.parse_args().database)
