import json
from pathlib import Path

import pytest

from archimind.town.dining_edit import edit

PROMPT = "Seat six at one table in the salon and keep the lounge seating unchanged."


def test_dining_edit_changes_one_group_and_rejects_unsupported_requests():
    snapshot = (
        Path(__file__).resolve().parents[1]
        / "docs/data/nov24-fresh-live/snapshot-r2.json"
    )
    home = json.loads(snapshot.read_text())["home"]
    updated, summary = edit(home, PROMPT)
    assert updated["evidence"]["comparison"]["dining_places"] == {
        "salon": 6,
        "kitchen-dining": 4,
    }
    assert home["evidence"]["comparison"]["dining_places"]["salon"] == 4
    assert "2.04 m" in summary
    for old, new in zip(home["rooms"], updated["rooms"], strict=True):
        if old["design"]["room"]["id"] != "salon":
            assert new == old
        else:
            assert new["dining_variant"] == "six-place"
            for before, after in zip(
                old["design"]["furniture"], new["design"]["furniture"], strict=True
            ):
                assert before | {"name": after["name"]} == after
    with pytest.raises(ValueError, match="already"):
        edit(updated, PROMPT)
    with pytest.raises(ValueError, match="Try:"):
        edit(home, PROMPT + " Remove the lounge too.")
    salon = next(r for r in home["rooms"] if r["design"]["room"]["id"] == "salon")
    next(f for f in salon["design"]["furniture"] if f["id"] == "salon-dining")[
        "width_m"
    ] = 1.5
    with pytest.raises(ValueError, match="exceeds"):
        edit(home, PROMPT)
