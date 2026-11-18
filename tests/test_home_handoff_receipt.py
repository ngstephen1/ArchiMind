"""Mutation cases for the offline receipt check, using synthetic data."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

check = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/check_home_handoff.py")
)["check"]


@pytest.mark.parametrize("change", ["valid", "stale", "swapped", "stationary"])
def test_handoff(change):
    def board(n, x):
        return json.dumps(
            dict(
                kind="whole-home-presentation",
                project="p",
                home_id=str(n),
                revision=n,
                rooms=[
                    dict(
                        room={"id": "bedroom"},
                        furniture=[dict(id="desk-chair", x_m=x, y_m=1)],
                    )
                ],
            )
        ).encode()

    before, after = board(1, 2), board(2, 2 if change == "stationary" else 3)
    digest = hashlib.sha256(before if change == "stale" else after).hexdigest()
    receipt = dict(
        home_id="2", revision=2, manifest_sha256=digest, files={"manifest.json": digest}
    )
    if change == "valid":
        assert check(before, after, receipt)["revision"] == 2
    else:
        with pytest.raises(ValueError):
            check(after, before, receipt) if change == "swapped" else check(
                before, after, receipt
            )
