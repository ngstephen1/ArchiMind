"""Score three pinned Blender shots and their deliberately degraded controls."""

import argparse
import base64
import io
import json
import os
import time
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from run_with_agent import settings_from_dotenv

from archimind.town import decisions

RUBRIC = "town-render-visual-v1"
CAMERAS = {
    ("bedroom", "doorway"): ("window_detail", "grounding", "materials"),
    ("bedroom", "desk"): ("grounding", "materials"),
    ("salon", "overview"): ("window_detail", "grounding", "materials"),
}
CRITERIA = {
    "window_detail": "Visible window frames and nearby surfaces retain detail without clipping.",
    "grounding": "Furniture reads as physically grounded where it meets the floor, with clear edges and contact shadows.",
    "materials": "Major surfaces have distinct, readable grain, fabric texture, or finish.",
}


def question(name):
    return {
        "type": "score",
        "name": name,
        "instructions": CRITERIA[name] + " Assess the visible evidence in this image.",
        "levels": [
            {
                "label": "poor",
                "description": "Little readable evidence of this quality.",
            },
            {
                "label": "mixed",
                "description": "Some visible evidence, with important losses.",
            },
            {
                "label": "clear",
                "description": "Clearly readable across relevant areas.",
            },
        ],
    }


def jpeg(image):
    resized = image.copy()
    resized.thumbnail((1440, 960))
    raw = io.BytesIO()
    resized.save(raw, format="JPEG", quality=90)
    return raw.getvalue()


def compare(root, key):
    raw = (root / "eye-view-receipt.json").read_bytes()
    receipt = json.loads(raw)
    cameras = {(shot["room"], shot["view"]): shot for shot in receipt["shots"]}
    if (
        receipt["engine"] != "CYCLES"
        or cameras.keys() != CAMERAS.keys()
        or len(receipt["shots"]) != 3
    ):
        raise ValueError("Expected exactly three pinned Cycles shots.")
    rows = []
    for identity, criteria in CAMERAS.items():
        shot = cameras[identity]
        name = shot["file"]
        if (
            Path(name).name != name
            or shot["camera_manifest_sha256"] != receipt["camera_manifest_sha256"]
        ):
            raise ValueError("Shot binding does not match the camera manifest.")
        png = (root / name).read_bytes()
        if sha256(png).hexdigest() != shot["sha256"]:
            raise ValueError("Shot bytes do not match the render receipt.")
        with Image.open(io.BytesIO(png)) as image:
            source = image.convert("RGB")
        control = ImageEnhance.Contrast(
            source.filter(ImageFilter.GaussianBlur(6))
        ).enhance(0.50)
        control = ImageEnhance.Brightness(control).enhance(1.45)
        cases = []
        for variant, image in (("source", source), ("synthetic_control", control)):
            sent = jpeg(image)
            result = decisions.query(
                [
                    {
                        "role": "user",
                        "type": "message",
                        "content": [
                            {
                                "type": "input_image",
                                "detail": "high",
                                "image_url": "data:image/jpeg;base64,"
                                + base64.b64encode(sent).decode("ascii"),
                            }
                        ],
                    }
                ],
                [question(name) for name in criteria],
                key=key,
                deadline=time.monotonic() + 20,
                rubric=RUBRIC,
            )
            cases.append(
                {
                    "variant": variant,
                    "submitted_sha256": sha256(sent).hexdigest(),
                    "review": result,
                }
            )
        a, b = (case["review"]["answers"] for case in cases)
        deltas = {
            name: round(a[name]["score"] - b[name]["score"], 3)
            for name in criteria
            if a.get(name) and b.get(name)
        }
        rows.append(
            {
                "shot": name,
                "room": identity[0],
                "view": identity[1],
                "source_sha256": shot["sha256"],
                "camera": shot["camera"],
                "scores": cases,
                "source_minus_control": deltas,
            }
        )
    return {
        "rubric": RUBRIC,
        "model": decisions.MODEL,
        "revision": receipt["revision"],
        "home_id": receipt["home_id"],
        "source_receipt_sha256": sha256(raw).hexdigest(),
        "mode": "offline_artifact_qa",
        "runtime_authority": False,
        "shots": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--live", action="store_true", required=True)
    args = parser.parse_args()
    key = os.getenv("OPENAI_API_KEY") or settings_from_dotenv(args.env_file).get(
        "OPENAI_API_KEY"
    )
    if not key:
        parser.error("OpenAI credentials are unavailable.")
    receipt = compare(args.artifacts, key)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    for shot in receipt["shots"]:
        print(shot["shot"], shot["source_minus_control"])


if __name__ == "__main__":
    main()
