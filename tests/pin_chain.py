"""Expected SHA-256 of every hash-pinned file after all authorized migrations.

The 08F1 receipt pins 142 files. Each later receipt may authorize a change to a
pinned file by binding its previous hash (``before_sha256``) and its new bytes
(``after_sha256``). Receipts apply in the order they were written; the style
pack receipt (11A) applies last.
"""

from __future__ import annotations

import json
from pathlib import Path

STYLE_PACKS_RECEIPT = "docs/data/STYLE_PACKS_11A.json"


def _load(root: Path, path: str) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _migration_steps(root: Path, include_style_packs: bool) -> list[dict]:
    belaya = _load(root, "docs/data/ASSET_QUALIFICATION_BELAYA_08F3A.json")
    chat = _load(root, "docs/data/CHAT_BEDROOM_09A.json")
    studio = _load(root, "docs/data/3D_STUDIO_10A.json")
    steps = [
        _load(root, "docs/data/FURNITURE_CATALOG_ADMISSION_08F2.json")[
            "authorized_migrations"
        ],
        belaya["r1"]["authorized_migrations"],
        belaya.get("r2", {}).get("authorized_migrations", {}),
        belaya["delivery_20261101"]["authorized_migrations"],
        belaya["ci_compatibility_20261101"]["authorized_migrations"],
        belaya["r3c"]["final2"]["authorized_migrations"],
        belaya["r3c"]["delivery_followup"]["authorized_migrations"],
        chat["authorized_migrations"],
        chat.get("resume3", {}).get("authorized_migrations", {}),
        _load(root, "docs/data/DESIGN_AGENT_SINGLE.json")["authorized_migrations"],
        studio["authorized_migrations"],
        studio["merge_review"]["authorized_migrations"],
        studio["bedroom_view"]["authorized_migrations"],
        studio["three_0_187"]["authorized_migrations"],
        studio["designer_chair"]["authorized_migrations"],
        studio["bedroom_collection"]["authorized_migrations"],
    ]
    # Dependency manifest updates only ever touch pyproject.toml.
    for update in _load(root, "docs/data/DEPENDENCY_MANIFEST_MIGRATIONS.json"):
        assert set(update) == {"pyproject.toml"}
        steps.append(update)
    if include_style_packs and (root / STYLE_PACKS_RECEIPT).exists():
        steps.append(_load(root, STYLE_PACKS_RECEIPT)["authorized_migrations"])
    return steps


def expected_pins(root: Path, *, include_style_packs: bool = True) -> dict[str, str]:
    """Map every pinned path to its expected SHA-256 after all migrations.

    Raises ``AssertionError`` when a migration's ``before_sha256`` does not
    match the chain value it claims to replace.
    """
    receipt = _load(root, "docs/data/FURNITURE_EXPANSION_08F1.json")
    pins = dict(receipt["preservation"]["baseline_files"])
    steps = _migration_steps(root, include_style_packs)
    # 08F2 (the first step) may only touch pinned files. Later receipts also
    # record unpinned paths (e.g. MANIFEST.in); those are not part of the chain.
    assert set(steps[0]) <= pins.keys(), sorted(set(steps[0]) - pins.keys())
    for step in steps:
        for path, entry in step.items():
            if path not in pins:
                continue
            assert entry["before_sha256"] == pins[path], path
            pins[path] = entry["after_sha256"]
    return pins
