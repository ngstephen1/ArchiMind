"""A single, explicitly requested material study of a supplied room view."""

import base64
import io
from threading import BoundedSemaphore

from openai import APIError
from PIL import Image

from archimind.agents.requirements_agent import _client
from archimind.studio.provider import configuration

from .room_photos import prepare_photo
from .service import Problem

_slot = BoundedSemaphore(1)
SIZES = {(1536, 1024), (1024, 1536), (1024, 1024)}


def restyle(data):
    if set(data) != {"direction", "photo", "consent"} or data["consent"] is not True:
        raise Problem("Confirm that this room image and brief may be sent to OpenAI.")
    direction = data["direction"]
    if not isinstance(direction, str) or not 1 <= len(direction.strip()) <= 800:
        raise Problem("Describe the design in 1–800 characters.")
    if not isinstance(data["photo"], str):
        raise Problem("Select a room image first.")
    if not _slot.acquire(blocking=False):
        raise Problem(
            "Another image is being developed. Try again after it finishes.", 429
        )
    try:
        config_key, _ = configuration(True)
        source = base64.b64decode(data["photo"], validate=True)
        try:
            with Image.open(io.BytesIO(source), formats=("JPEG",)) as image:
                size = image.size
        except (OSError, Image.DecompressionBombError) as exc:
            raise Problem("Select a readable room image.") from exc
        if size not in SIZES:
            raise Problem("Use a room photo framed by the Town studio.")
        _, jpeg = prepare_photo(source)
        with _client(config_key) as client:
            result = client.images.edit(
                model="gpt-image-2",
                image=("room.jpg", jpeg, "image/jpeg"),
                prompt=(
                    "Make a photographic interior design proposal by editing the supplied room image. "
                    "Keep the camera position, lens, framing, walls, floor outline, doors and windows. "
                    "Preserve furniture locations unless the brief asks to move them. "
                    "Use coherent material scale, contact shadows and light from the actual openings. "
                    "Show one full-bleed frame without typography or a collage. Design brief: "
                    + direction.strip()
                ),
                size=f"{size[0]}x{size[1]}",
                quality="medium",
                output_format="jpeg",
                n=1,
                timeout=180,
            )
        encoded = result.data[0].b64_json if result.data else None
        if not encoded:
            raise Problem("The image service returned no concept.", 502)
        try:
            with Image.open(
                io.BytesIO(base64.b64decode(encoded, validate=True)), formats=("JPEG",)
            ) as image:
                if image.size != size:
                    raise ValueError("frame mismatch")
                image.load()
        except (ValueError, OSError, Image.DecompressionBombError) as exc:
            raise Problem(
                "The returned image did not match the requested frame.", 502
            ) from exc
        return {"jpeg": encoded}
    except APIError as exc:
        raise Problem(
            "The image service could not finish this concept. No retry was made.", 502
        ) from exc
    finally:
        _slot.release()
