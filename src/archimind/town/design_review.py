"""Generate measured plan images and collect advisory feedback for a Town job."""

import base64
import io
import json
import time
from typing import Annotated

from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field

from archimind.integrations.codex_advisor import request_codex_advice
from archimind.models import RoomDesign
from archimind.studio import provider

Note = Annotated[str, Field(min_length=1, max_length=400)]


class Direction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    material_direction: Note
    lighting_direction: Note
    tradeoff: Note


class VisualReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation: Note
    recommendation: Note
    uncertainty: Note


def direction(req):
    return provider.request(
        Direction,
        "Propose a material and daylight direction for this brief and its controls. "
        "These are presentation suggestions. "
        + json.dumps({"brief": req.message, "controls": req.brief.model_dump()}),
        config=provider.configuration(True),
        deadline=time.monotonic() + 30,
    )


def plan_png(home):
    """Render shared-scale north-up footprints and real wall openings."""
    scale = 36
    margin = 16
    w, d = home["width"], home["depth"]
    im = Image.new(
        "RGB", (round(w * scale) + 2 * margin, round(d * scale) + 2 * margin), "#d8cbbb"
    )
    draw = ImageDraw.Draw(im)

    def point(x, y):
        return (round(margin + x * scale), round(margin + (d - y) * scale))

    for part in home["rooms"]:
        x, y = part["origin"]
        design = part["design"]
        room = design["room"]
        rw, rd = room["width_m"], room["depth_m"]
        draw.rectangle(
            [point(x, y + rd), point(x + rw, y)],
            fill="#faf7ee",
            outline="#293e38",
            width=2,
        )
        for item in design["furniture"]:
            fx, fy = x + item["x_m"], y + item["y_m"]
            draw.rectangle(
                [point(fx, fy + item["depth_m"]), point(fx + item["width_m"], fy)],
                fill="#92ae9f",
                outline="#42584e",
            )
        for group, color in [("doors", "#bb6932"), ("windows", "#3175a4")]:
            for opening in room[group]:
                wall, offset, length = (
                    opening["wall"],
                    opening["offset_m"],
                    opening["width_m"],
                )
                if wall in ("west", "east"):
                    xx = x + (rw if wall == "east" else 0)
                    ends = [point(xx, y + offset), point(xx, y + offset + length)]
                else:
                    yy = y + (rd if wall == "north" else 0)
                    ends = [point(x + offset, yy), point(x + offset + length, yy)]
                draw.line(ends, fill=color, width=4)
        px, py = point(x, y + rd)
        draw.text(
            (px + 4, py + 3),
            room["id"],
            fill="#161f19",
            stroke_width=1,
            stroke_fill="#faf7ee",
        )
    data = io.BytesIO()
    im.save(data, format="PNG")
    return data.getvalue()


def review_candidates(req, homes, style):
    content = [
        {
            "type": "input_text",
            "text": "Review the pictured candidate plans in order against the brief and the stylist's proposal. Green blocks are furniture, blue lines windows and orange lines doors. Cite visible room relationships. Distinguish suggestions from verified measurements. "
            + json.dumps({"brief": req.message, "style": style.model_dump()}),
        }
    ]
    for home in homes:
        png = base64.b64encode(plan_png(home)).decode("ascii")
        content.append({"type": "input_text", "text": "Candidate " + home["id"]})
        content.append(
            {"type": "input_image", "image_url": "data:image/png;base64," + png}
        )
    result = provider.request(
        VisualReview,
        content,
        config=provider.configuration(True),
        deadline=time.monotonic() + 30,
    )
    return {"candidate_ids": [h["id"] for h in homes], **result.model_dump()}


def codex_review(req, home):
    room = next(
        p["design"] for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom"
    )
    result = request_codex_advice(
        RoomDesign.model_validate(room),
        req.message or "Review bedroom furniture placement.",
        allow_live_usage=True,
    )
    return {
        "candidate": home["id"],
        "room": "bedroom",
        **result.model_dump(mode="json"),
    }
