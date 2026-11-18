"""Record authorized 11A migrations for every hash-pinned file that changed.

Run after ``git add`` and before ``git commit``. For each pinned path whose
staged bytes differ from the pre-11A chain value, write
``{"before_sha256", "after_sha256"}`` into
``docs/data/STYLE_PACKS_11A.json["authorized_migrations"]``; paths whose staged
bytes equal the pre-11A value are removed. Hashes use the staged blob (LF
line endings), matching CI checkouts.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/data/STYLE_PACKS_11A.json"
sys.path.insert(0, str(ROOT / "tests"))

from pin_chain import expected_pins  # noqa: E402


def staged_sha256(path: str) -> str:
    data = subprocess.run(
        ["git", "show", f":{path}"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    before = expected_pins(ROOT, include_style_packs=False)
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    migrations = {}
    for path in sorted(before):
        after = staged_sha256(path)
        if after != before[path]:
            migrations[path] = {"before_sha256": before[path], "after_sha256": after}
    receipt["authorized_migrations"] = migrations
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for path in migrations:
        print(f"migration: {path}")
    print(f"{len(migrations)} authorized migration(s) recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
