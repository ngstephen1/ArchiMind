import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app


@pytest.fixture
def saved(tmp_path, monkeypatch):
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.sqlite"))
    service.initialize()
    home = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/data/furnished-residence/home.json"
        ).read_text()
    )
    project = service.create("local-designer", home=home)["project"]
    return (
        TestClient(app, base_url="http://localhost"),
        "/api/projects/" + project,
        home,
    )


def test_scoped_finish_isolation_and_reload(saved):
    client, path, source = saved
    body = {"base": 1, "scope": "room", "room": "salon", "message": "Dark green walls"}
    snapshot = client.post(path + "/finish/preview", json=body).json()["home"]
    assert (
        client.post(
            path + "/finish/apply", json=body | {"preview_id": "wrong"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/finish/apply", json=body | {"preview_id": snapshot["id"]}
        ).json()["revision"]
        == 2
    )
    assert client.get(path + "?revision=1").json()["home"] == source
    for part in client.get(path).json()["home"]["rooms"]:
        if part["design"]["room"]["id"] == "salon":
            assert part["finish_overrides"] == {"wall": "dark green"}
        else:
            assert "finish_overrides" not in part
    assert (
        client.post(
            path + "/finish/preview",
            json=body | {"base": 2, "message": "walnut floors throughout"},
        ).status_code
        == 400
    )


def test_bookmark_is_project_owned_and_keeps_original_pose(saved):
    client, path, home = saved
    room = home["rooms"][0]
    x, y = room["origin"]
    pose = {
        "room": room["design"]["room"]["id"],
        "eye": [x + 1, 1.5, -y - 1],
        "target": [x + 2, 1.5, -y - 1],
        "fov": 61,
        "aspect": 1.777,
    }
    assert (
        client.post(path + "/bookmarks", json={"revision": 1, "pose": pose}).json()
        == pose
    )
    assert (
        client.post(
            path + "/bookmarks",
            json={"revision": 1, "pose": pose | {"eye": [490, 1, -490]}},
        ).status_code
        == 400
    )
    other = service.create("another-user", home=home)["project"]
    assert client.get("/api/projects/" + other + "/bookmarks").status_code in (403, 404)
    assert client.get(path + "/bookmarks").json()["views"] == [pose]


def test_render_rejects_camera_outside_historical_room_before_loading_blender(
    saved, tmp_path
):
    from archimind.town.bookmarks import photograph

    _, _, home = saved
    room = home["rooms"][0]
    pose = {
        "room": room["design"]["room"]["id"],
        "eye": [300, 1.5, -300],
        "target": [301, 1.5, -300],
        "fov": 61,
        "aspect": 1.5,
    }
    with pytest.raises(service.Problem, match="outside the room"):
        photograph({"home": home}, pose, tmp_path / "unused-blender")


def test_client_book_shows_selected_materials_on_their_saved_surfaces(tmp_path):
    import runpy

    swatches = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scripts/publish_studio_board.py")
    )["finish_swatches"]
    board = {
        "finishes": {"proposal-walnut": "#795337"},
        "base_finish_locations": {"floor": [], "tile": []},
        "finish_schedule": [
            {
                "surface": "floor",
                "finish": "walnut",
                "color": "#795337",
                "locations": [
                    {"room": "salon", "label": "Salon"},
                    {"room": "hall", "label": "Hall"},
                ],
            },
            {
                "surface": "object",
                "finish": "sage",
                "color": "#9da98c",
                "locations": [
                    {"label": "Salon · Coffee table", "object": "salon-coffee-table"}
                ],
            },
        ],
    }
    for style in (None, {"surfaces": {"floor": {}, "tile": {}}}):
        html = swatches(board, style, tmp_path)
        assert "Walnut</b> · floor · Salon, Hall" in html
        assert "Sage</b> · object · Salon · Coffee table [salon-coffee-table]" in html
        assert "Proposal-" not in html
