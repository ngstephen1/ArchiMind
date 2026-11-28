import io

import pytest
from PIL import Image

from archimind.town import room_photos


def test_upload_resized_and_metadata_removed():
    photo = Image.new("RGB", (1400, 700), "white")
    meta = Image.Exif()
    meta[315] = "Private author"
    buffer = io.BytesIO()
    photo.save(buffer, format="JPEG", exif=meta)
    first = room_photos.prepare_photo(buffer.getvalue())
    assert first == room_photos.prepare_photo(buffer.getvalue())
    with Image.open(io.BytesIO(first[1])) as preview:
        assert preview.size == (1280, 640)
        assert not preview.getexif()
    with pytest.raises(ValueError):
        room_photos.prepare_photo(b"invalid")
    with pytest.raises(ValueError):
        room_photos.prepare_photo(bytes(8 * 1024 * 1024 + 1))


def test_visual_review_requires_consent_and_valid_references(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    with pytest.raises(room_photos.provider.StudioError, match="consent"):
        room_photos.review_photos([b"test"], False)

    def response(schema, prompt, **kwargs):
        assert prompt[2]["type"] == "input_image"
        return schema(
            observations=[
                {
                    "photo": 2,
                    "feature": "opening",
                    "observation": "Window",
                    "field_question": "Which wall?",
                }
            ]
        )

    monkeypatch.setattr(room_photos.provider, "request", response)
    with pytest.raises(ValueError, match="reference"):
        room_photos.review_photos([b"test"], True)
