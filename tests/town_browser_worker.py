"""Run the ordinary Town worker with offline OpenAI responses for the seed-42 browser check."""

import runpy
from unittest.mock import patch

from archimind.town.design_review import Direction, VisualReview
from archimind.town.service import Interpretation


def response(schema, content, **kwargs):
    if schema is Interpretation:
        return Interpretation(
            priority="balanced",
            palette="oak",
            lock_rooms=[],
            clarification="",
            unsupported=[],
            lock_furniture=[],
        )
    if schema is Direction:
        return Direction(
            material_direction="Fixture oak.",
            lighting_direction="Fixture daylight.",
            tradeoff="Fixture finish.",
        )
    if schema is VisualReview and any(
        item["type"] == "input_image" for item in content
    ):
        return VisualReview(
            observation="Fixture visual observation.",
            recommendation="Inspect the saved bedroom.",
            uncertainty="Offline browser fixture.",
        )
    raise AssertionError("Unexpected browser fixture request")


if __name__ == "__main__":
    with patch("archimind.studio.provider.request", response):
        runpy.run_module("archimind.town.worker", run_name="__main__")
