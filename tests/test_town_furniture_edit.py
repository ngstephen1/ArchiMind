import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app

HOME = Path(__file__).resolve().parents[1] / "docs/data/furnished-residence/home.json"


def test_editable_coffee_table_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.sqlite"))
    service.initialize()
    project = service.create("local-designer", home=json.loads(HOME.read_text()))[
        "project"
    ]
    client = TestClient(app, base_url="http://127.0.0.1")
    path = f"/api/projects/{project}"
    base = 1

    def edit(action, ident="salon-coffee-table", fail=False, **args):
        nonlocal base
        body = dict(base=base, room="salon", object=ident, action=action, **args)
        preview = client.post(path + "/furniture-edit/preview", json=body)
        if fail:
            assert preview.status_code == 400, preview.text
            assert client.get(path).json()["revision"] == base
            return
        assert preview.status_code == 200, preview.text
        assert client.get(path).json()["revision"] == base
        result = preview.json()
        body["preview_id"] = result["home"]["id"]
        saved = client.post(path + "/furniture-edit/apply", json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()["home"] == client.get(path).json()["home"]
        assert client.post(path + "/furniture-edit/apply", json=body).status_code == 409
        base += 1
        return result

    edit("replace", replacement="round", sofa_route=True, fail=True)
    edit("move", x_m=-1, y_m=0, fail=True)
    edit("move", ident="salon-dining", x_m=1, y_m=1, fail=True)
    edit("move", x_m=2.2, y_m=1.45)
    replaced = edit("replace", replacement="round", sofa_route=True)
    assert "90 cm" in replaced["summary"]
    edit("rotate")
    copy = edit("duplicate", x_m=4, y_m=0.5)
    salon = next(
        p for p in copy["home"]["rooms"] if p["design"]["room"]["id"] == "salon"
    )
    assert [f["id"] for f in salon["coffee_tables"]] == [
        "salon-coffee-table",
        "salon-coffee-table-copy-2",
    ]
    edit("remove", ident="salon-coffee-table-copy-2")
    assert (
        client.post(path + "/undo", json={"base": base}).json()["home"] == copy["home"]
    )


@pytest.mark.parametrize("object_id", ["side-table", "console-table"])
def test_standalone_furniture_edits_preserve_old_snapshot(object_id):
    from archimind.town.furniture_edit import Change, edit

    h = json.loads(HOME.read_text())
    room = "salon" if object_id == "side-table" else "living"
    original = next(p for p in h["rooms"] if p["design"]["room"]["id"] == room)
    if object_id == "console-table":
        with pytest.raises(ValueError, match="spatial checks"):
            edit(h, Change(base=1, room=room, object=object_id, action="rotate"))
        return
    updated, _ = edit(h, Change(base=1, room=room, object=object_id, action="rotate"))
    new = next(p for p in updated["rooms"] if p["design"]["room"]["id"] == room)
    assert "piece_edits" not in original
    assert new["piece_edits"][object_id]["yaw"] == 90
