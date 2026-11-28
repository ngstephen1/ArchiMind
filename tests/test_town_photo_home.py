"""Local source provenance, joined geometry, storage and correction in one project."""

import base64
import io

import pytest
from PIL import Image
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app
from archimind.town.photo_home import assemble


def payload():
    rooms = []
    passage = {"width": 1.0, "offset": 1.5}
    for n, color in enumerate(("darkgreen", "linen")):
        out = io.BytesIO()
        Image.new("RGB", (40, 30), color).save(out, "PNG")
        rooms.append(
            dict(
                name=["Studio", "Library"][n],
                photo=base64.b64encode(out.getvalue()).decode(),
                width=3.5 + n,
                depth=4.0,
                ceiling_height=2.6,
                west=passage.copy() if n else None,
                east=None if n else passage.copy(),
                windows=[
                    dict(wall="north", offset=0.5, width=1.1, sill=0.8, height=1.0)
                ],
                uncertainty="Depth checked on site.",
            )
        )
    return dict(confirmed=True, entry=dict(width=0.95, offset=0.75), rooms=rooms)


def test_reopen_paired_room_sources_and_scale(tmp_path, monkeypatch):
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.sqlite3"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    service.initialize()
    client = TestClient(app, base_url="http://127.0.0.1")
    saved = client.post("/api/photo-home", json=payload())
    assert saved.status_code == 200, saved.text
    data = saved.json()
    path = "/api/projects/" + data["project"]
    home = client.get(path + "?revision=1").json()["home"]
    assert home == data["home"]
    assert [part["origin"] for part in home["rooms"]] == [[0, 0], [3.5, 0]]
    assert home["width"] == 8 and home["depth"] == 4
    doors = [
        next(d for d in p["design"]["room"]["doors"] if d["id"] == "join-1")
        for p in home["rooms"]
    ]
    assert [d["wall"] for d in doors] == ["east", "west"]
    assert doors[0]["width_m"] == doors[1]["width_m"] == 1.0
    for source in home["photo_home"]["sources"]:
        response = client.get(path + "/room-photo/" + source["photo_sha256"])
        assert response.headers["content-type"] == "image/jpeg"
        import hashlib

        assert hashlib.sha256(response.content).hexdigest() == source["photo_sha256"]
    assert client.get(path + "/room-photo/wrong").status_code == 404


@pytest.mark.parametrize(
    "bad", ["scale", "depth", "offset", "width", "source", "window", "overlap"]
)
def test_insufficient_or_conflicting_room_intake(bad):
    d = payload()
    if bad == "scale":
        d["confirmed"] = False
    if bad == "depth":
        d["rooms"][1]["depth"] = 5.0
    if bad == "offset":
        d["rooms"][1]["west"]["offset"] = 1.0
    if bad == "width":
        d["rooms"][0]["east"]["width"] = 0.85
    if bad == "source":
        d["rooms"][1]["photo"] = d["rooms"][0]["photo"]
    if bad == "window":
        d["rooms"][1]["windows"][0]["wall"] = "west"
    if bad == "overlap":
        d["rooms"][0]["windows"][0]["wall"] = "south"
    with pytest.raises(service.Problem):
        assemble(d)


def test_shared_glazing_requires_both_observations_and_matches_by_location():
    intake = payload()
    east = dict(wall="east", offset=0.15, width=0.65, sill=0.85, height=1.1)
    west = {**east, "wall": "west"}
    intake["rooms"][0]["windows"].append(east)
    intake["rooms"][1]["windows"].insert(0, west)
    home, _ = assemble(intake)
    shared = [
        next(w for w in p["design"]["room"]["windows"] if w["wall"] == side)
        for p, side in zip(home["rooms"], ["east", "west"])
    ]
    assert shared[0]["id"] == shared[1]["id"] == "join-window-1-1"
    for field in ("offset", "width", "sill", "height"):
        west[field] += 0.01
        with pytest.raises(service.Problem, match="Reconcile shared windows"):
            assemble(intake)
        west[field] = east[field]
