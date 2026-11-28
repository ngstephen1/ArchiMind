import json
from pathlib import Path

import pytest
from shapely.geometry import box

from archimind.town.design import digest
from archimind.town.study_edit import edit

PROMPT = (
    "Move the study table and chair together to clear a 90 cm passage "
    "from the door to the window-side table."
)
FIXTURE = (
    Path(__file__).resolve().parents[1] / "docs/data/furnished-residence/home.json"
)


def test_rearrangement_clears_measured_route():
    original = json.loads(FIXTURE.read_text())
    updated, _ = edit(original, PROMPT)
    assert original == json.loads(FIXTURE.read_text())
    route = updated["evidence"]["study_passage"]
    assert set(route["before_blockers"]) == {"library-chair", "library-table"}
    assert route["width_m"] == 0.90
    assert route["length_m"] == pytest.approx(6.148)
    x1, y1, x2, y2 = route["room_local_bounds_m"]
    assert y2 - y1 == pytest.approx(0.90)
    corridor = box(x1, y1, x2, y2)
    for before, after in zip(original["rooms"], updated["rooms"], strict=True):
        if before["design"]["room"]["id"] != "study":
            assert before == after
            continue
        for a, b in zip(
            before["design"]["furniture"], after["design"]["furniture"], strict=True
        ):
            x, y = b["x_m"], b["y_m"]
            assert (
                box(x, y, x + b["width_m"], y + b["depth_m"])
                .intersection(corridor)
                .area
                < 1e-8
            )
            if b["id"] in route["moved"]:
                assert y - a["y_m"] == pytest.approx(
                    route["translation_y_m"], abs=0.0001
                )
            else:
                assert a == b
    assert updated["id"] == digest({k: v for k, v in updated.items() if k != "id"})
    with pytest.raises(ValueError, match="already clear"):
        edit(updated, PROMPT)


def test_preserves_unsupported_requirements():
    original = json.loads(FIXTURE.read_text())
    with pytest.raises(ValueError):
        edit(original, PROMPT + " Also move the sofa.")
    study = next(p for p in original["rooms"] if p["design"]["room"]["id"] == "study")
    study["design"]["room"]["doors"][0]["width_m"] = 0.85
    with pytest.raises(ValueError, match="align"):
        edit(original, PROMPT)
