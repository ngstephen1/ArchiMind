"""Create a separate AI concept illustration from an applied local Town revision."""

import argparse
import base64
import io
import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from openai import APIError, OpenAI
from PIL import Image
from run_with_agent import settings_from_dotenv

from archimind.town import service
from archimind.town.design import validate_home
from archimind.town.design_review import plan_png

ROOT = Path(__file__).resolve().parents[1]


def render(home, brief, images):
    validate_home(home)
    response = images.edit(
        model="gpt-image-2",
        image=("measured-plan.png", plan_png(home), "image/png"),
        prompt=(
            "Use the supplied north-up furniture plan as a spatial reference for one interior concept illustration. "
            "Blue marks windows, orange doors. Work with the saved "
            + home["palette"]
            + " palette. "
            "Use plausible daylight, dimensional furnishings and tactile materials. "
            "Do not include annotations or make compliance claims. Design direction: "
            + brief
        ),
        n=1,
        size="1536x1024",
        quality="medium",
        output_format="png",
    )
    if not response.data or not response.data[0].b64_json:
        raise ValueError("Image generation returned no image.")
    data = base64.b64decode(response.data[0].b64_json, validate=True)
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG":
                raise ValueError("Expected a PNG concept image.")
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except (SyntaxError, OSError) as exc:
        raise ValueError("The concept PNG could not be decoded.") from exc
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=UUID)
    parser.add_argument("revision", type=int)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.getenv("TOWN_DB", ROOT / "storage/town-designer.sqlite3")),
    )
    parser.add_argument("--direction", required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/concepts")
    args = parser.parse_args()
    if not 0 < len(args.direction.strip()) <= 1800 or args.revision < 1:
        parser.error(
            "Supply a saved revision and a design direction of 1–1800 characters."
        )
    try:
        with sqlite3.connect(
            args.database.resolve().as_uri() + "?mode=ro", uri=True
        ) as conn:
            service.project(conn.execute, "local-designer", str(args.project))
            home = service.revision(conn.execute, str(args.project), args.revision)
        key = os.environ.get("OPENAI_API_KEY") or settings_from_dotenv(
            ROOT / ".env"
        ).get("OPENAI_API_KEY")
        if not key:
            parser.error("Configure OPENAI_API_KEY in the environment or local .env.")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        destination = (
            args.output_dir
            / f"{args.project}-r{args.revision}-concept-{uuid4().hex}.png"
        )
        with TemporaryDirectory(dir=args.output_dir) as staging:
            temporary = Path(staging) / "concept.tmp"
            with (
                temporary.open("xb") as output,
                OpenAI(api_key=key, max_retries=0, timeout=180) as client,
            ):
                output.write(render(home, args.direction, client.images))
            temporary.replace(destination)
    except APIError:
        parser.exit(1, "The OpenAI image request failed. No retry was made.\n")
    except (ValueError, OSError, sqlite3.Error, service.Problem) as exc:
        parser.exit(1, f"Concept unavailable: {exc}\n")

    print(destination)


if __name__ == "__main__":
    main()
