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


def test_salon_plan_keeps_both_wall_faces_and_openings_above_them():
    import runpy
    import xml.etree.ElementTree as ET

    drawing = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scripts/publish_studio_board.py")
    )["drawing"]
    opening = {"wall": "north", "offset_m": 1, "width_m": 0.9}
    fixture = {
        "width": 4,
        "depth": 6,
        "finishes": {"proposal-dark green": "#294735"},
        "rooms": [
            {
                "origin": [0, y],
                "room": {
                    "name": name,
                    "width_m": 4,
                    "depth_m": 3,
                    "doors": [opening | {"wall": wall}],
                    "windows": [],
                },
                "finish_overrides": {"wall": "dark green"} if y == 0 else {},
                "furniture": [],
            }
            for name, y, wall in (("Salon", 0, "north"), ("Living", 3, "south"))
        ],
    }
    for rooms in (fixture["rooms"], list(reversed(fixture["rooms"]))):
        root = ET.fromstring(drawing(fixture | {"rooms": rooms}))
        rects = list(root.iter("{http://www.w3.org/2000/svg}rect"))
        faces = [r for r in rects if r.get("fill") == "none"]
        salon = next(r for r in faces if r.get("stroke") == "#294735")
        living = next(r for r in faces if r.get("stroke") == "#686558")
        assert float(salon.get("y")) > 3
        assert float(living.get("y")) + float(living.get("height")) < 3
        assert min(i for i, r in enumerate(rects) if r.get("fill") == "#cb8e3c") > max(
            rects.index(f) for f in faces
        )


def test_unmodified_hall_floor_keeps_its_own_material_in_the_book(tmp_path):
    import runpy

    swatches = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scripts/publish_studio_board.py")
    )["finish_swatches"]
    board = {
        "finishes": {},
        "base_finish_locations": {"hall_floor": ["Hall"], "hall_wall": ["Hall ends"]},
    }
    actual = swatches(board, {"surfaces": {}}, tmp_path)
    assert "<b>Base timber floor</b> · Hall" in actual
    assert "Base plaster" in swatches(board, None, tmp_path)
