"""Daylight metering stays fixed when only furniture placements change."""

import runpy
from pathlib import Path

import pytest

exposure = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/studio_photography.py")
)["daylight_exposure"]


def test_glazing_controls_camera_exposure_across_room_edits():
    room = {
        "width_m": 4,
        "depth_m": 5,
        "windows": [{"width_m": 1.2, "height_m": 1.0}],
    }
    assert exposure(room) == pytest.approx(0.5)
    assert exposure({**room, "furniture": ["changed chair"]}) == exposure(room)
    assert exposure({**room, "windows": []}) == pytest.approx(1.1)
    assert exposure({**room, "windows": [{"width_m": 8, "height_m": 4}]}) == -0.9
