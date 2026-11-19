import hashlib
import json
from pathlib import Path

from pin_chain import expected_pins

ROOT = Path(__file__).resolve().parents[1]


def _shas(path: str) -> set[str]:
    # Windows checkouts may convert text files to CRLF; binaries stay raw.
    data = (ROOT / path).read_bytes()
    return {
        hashlib.sha256(data).hexdigest(),
        hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest(),
    }


def test_chain_matches_preservation_test():
    pins = expected_pins(ROOT)
    assert len(pins) == 142
    for path, sha in pins.items():
        assert sha in _shas(path), path


def test_receipt_records_owner_authorization():
    r = json.loads((ROOT / "docs/data/STYLE_PACKS_11A.json").read_text())
    assert r["authorization"] == {
        "by": "owner",
        "date": "2026-11-17",
        "scope": "docs/superpowers/specs/2026-11-17-photoreal-style-packs-design.md",
    }
    assert set(r["authorized_migrations"]) <= set(expected_pins(ROOT))


def test_chain_without_style_packs_is_the_pre_11a_state():
    before = expected_pins(ROOT, include_style_packs=False)
    after = expected_pins(ROOT)
    migrations = json.loads((ROOT / "docs/data/STYLE_PACKS_11A.json").read_text())[
        "authorized_migrations"
    ]
    review = json.loads((ROOT / "docs/data/STYLE_PACKS_11A.json").read_text())[
        "merge_review_migrations"
    ]
    assert review.keys() <= before.keys()
    for path in migrations.keys() | review.keys():
        expected = before[path]
        if path in migrations:
            assert expected == migrations[path]["before_sha256"]
            expected = migrations[path]["after_sha256"]
        if path in review:
            assert expected == review[path]["before_sha256"]
            expected = review[path]["after_sha256"]
        assert expected == after[path]
    assert {
        p for p in before if before[p] != after[p]
    } == migrations.keys() | review.keys()
