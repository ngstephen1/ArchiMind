"""Replay a furnished six-room local project or export its saved revision."""

import argparse
import json
import os
import runpy
import tempfile
from pathlib import Path

from archimind.town import service
from archimind.town.design import Brief, generate
from archimind.town.designer_chair import chair_change

ROOT = Path(__file__).resolve().parents[1]


def create(directory):
    os.environ.pop("DATABASE_URL", None)
    os.environ.update(TOWN_DB=str(directory / "studio.sqlite3"), TOWN_MODE="local")
    service.initialize()
    owner, project = "local-designer", "f08f4541-8845-4c8a-b430-dc3535c60542"
    home = generate(Brief(formal_salon=True, width=15, depth=16, palette="sage"))[0]
    changes = json.loads((ROOT / "design/bedroom-showcase/history.json").read_text())[
        "changes"
    ]
    with service.transaction() as q:
        q("INSERT INTO projects VALUES(?,?,0)", (project, owner))
        saved = service.apply(q, owner, project, 0, home)
        for change in changes:
            req = {"binding": change["binding"], "base": saved["revision"]}
            preview = chair_change(
                q, owner, project, req, apply=False, collection=change["collection"]
            )
            saved = chair_change(
                q,
                owner,
                project,
                req | {"preview_id": preview["home"]["id"]},
                apply=True,
                collection=change["collection"],
            )
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="archimind-studio-") as directory:
        saved = create(Path(directory))
        if args.export:
            args.export.write_text(json.dumps(saved, indent=2))
        else:
            print(
                f"Studio home: http://127.0.0.1:{os.getenv('TOWN_PORT', '8790')}/?project={saved['project']}&revision={saved['revision']}",
                flush=True,
            )
            runpy.run_path(str(ROOT / "scripts/run_town.py"), run_name="__main__")
