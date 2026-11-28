import base64
import io
from types import SimpleNamespace
from unittest.mock import MagicMock

from PIL import Image
from starlette.testclient import TestClient

from archimind.town import photo_concept
from archimind.town.api import app


def sample(size):
    data = io.BytesIO()
    Image.new("RGB", size, "white").save(data, format="JPEG")
    return base64.b64encode(data.getvalue()).decode()


def test_photo_edit_is_local_explicit_bounded_and_returns_matching_frame(monkeypatch):
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    client = MagicMock()
    images = client.return_value.__enter__.return_value.images
    monkeypatch.setattr(photo_concept, "_client", client)
    http = TestClient(app, base_url="http://localhost")
    path = "/api/photo-concept"
    body = {
        "photo": sample((1024, 1024)),
        "direction": "Oak and linen",
        "consent": True,
    }
    for change in [
        {"consent": False},
        {"photo": "invalid"},
        {"photo": sample((200, 200))},
        {"direction": " "},
    ]:
        assert http.post(path, json=body | change).status_code == 400
    assert (
        http.post(
            path, json=body, headers={"Origin": "https://other.invalid"}
        ).status_code
        == 403
    )
    assert (
        http.post(
            path,
            content=b" " * (4 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    client.assert_not_called()
    images.edit.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json=body["photo"])]
    )
    r = http.post(path, json=body)
    assert r.status_code == 200
    assert (
        r.headers["cache-control"] == "no-store" and r.json()["jpeg"] == body["photo"]
    )
    assert images.edit.call_args.kwargs["size"] == "1024x1024"
    images.edit.return_value.data[0].b64_json = sample((100, 100))
    assert http.post(path, json=body).status_code == 502
    monkeypatch.setenv("TOWN_MODE", "hosted")
    assert http.post(path, json=body).status_code == 404
    assert images.edit.call_count == 2


def test_photo_layout_links_visible_furniture_to_source_and_checks_room_size(
    monkeypatch,
):
    from archimind.town import photo_layout

    http = TestClient(app, base_url="http://localhost")
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setattr(
        photo_layout.provider, "configuration", lambda _: ("test", "test")
    )
    piece = photo_layout.VisiblePiece(
        kind="chair",
        label="Oak chair",
        photo=1,
        center_x_fraction=0.4,
        center_depth_fraction=0.7,
        quarter_turns=1,
    )
    vision = MagicMock(
        return_value=photo_layout.LayoutGuess(
            furniture=[piece], uncertainty="Chair width unknown."
        )
    )
    monkeypatch.setattr(photo_layout.provider, "request", vision)
    path = "/api/photo-layout"
    photo = sample((620, 420))
    body = {"width": 4, "depth": 3.5, "photos": [photo], "consent": True}
    for invalid in [
        {"consent": False},
        {"width": 0},
        {"depth": 16},
        {"photos": []},
        {"photos": [photo, photo]},
    ]:
        assert http.post(path, json=body | invalid).status_code == 400
    vision.assert_not_called()
    response = http.post(path, json=body)
    assert (
        response.status_code == 200 and response.headers["cache-control"] == "no-store"
    )
    digest, _ = photo_layout.prepare_photo(base64.b64decode(photo))
    assert response.json()["photo_sha256"] == [digest]
    assert response.json()["furniture"] == [piece.model_dump()]
    piece.photo = 2
    assert http.post(path, json=body).status_code == 502
    piece.photo = 1
    piece.center_depth_fraction = 1.1
    assert http.post(path, json=body).status_code == 502
    monkeypatch.setenv("TOWN_MODE", "hosted")
    assert http.post(path, json=body).status_code == 404
