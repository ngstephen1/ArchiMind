"""Open the published bedroom in an editable, disposable local Town project."""

import json
import os
import runpy
import tempfile
from pathlib import Path

from archimind.town import service
from archimind.town.design import digest, validate_home
from archimind.town.designer_chair import chair_change

ROOT = Path(__file__).resolve().parents[1]


def replay_showcase(directory: Path):
    database = directory / "bedroom-showcase.sqlite3"
    if database.exists():
        raise ValueError("The showcase requires a fresh database.")
    os.environ.pop("DATABASE_URL", None)
    os.environ["TOWN_MODE"] = "local"
    os.environ["TOWN_DB"] = str(database)
    history = json.loads((ROOT / "design/bedroom-showcase/history.json").read_text())
    project = history["project"]
    owner = "local-designer"
    home = history["initial_home"]
    validate_home(home)
    if digest({k: v for k, v in home.items() if k != "id"}) != home["id"]:
        raise ValueError("The starting home differs from its saved digest.")
    service.initialize()
    with service.transaction() as q:
        q("INSERT INTO projects VALUES(?,?,0)", (project, owner))
        saved = service.apply(q, owner, project, 0, home)
        for change in history["changes"]:
            request = {"binding": change["binding"], "base": saved["revision"]}
            preview = chair_change(
                q, owner, project, request, apply=False, collection=change["collection"]
            )
            if (
                preview["home"]["id"] != change["id"]
                or change["revision"] != saved["revision"] + 1
            ):
                raise ValueError(
                    "Furniture replay differs from the published revision."
                )
            saved = chair_change(
                q,
                owner,
                project,
                request | {"preview_id": change["id"]},
                apply=True,
                collection=change["collection"],
            )
    return saved


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="archimind-bedroom-") as temp:
        saved = replay_showcase(Path(temp))
        print(
            "Open the published bedroom after Town starts:\n"
            f"http://127.0.0.1:8790/?project={saved['project']}&revision={saved['revision']}\n"
            "This session uses temporary storage. Edits last until the launcher stops.",
            flush=True,
        )
        runpy.run_path(str(ROOT / "scripts/run_town.py"), run_name="__main__")
