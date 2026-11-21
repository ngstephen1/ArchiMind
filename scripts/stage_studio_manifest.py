"""Stage a pinned public Town export for a Studio render on GitHub Actions."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath


def verify_snapshot(data):
    # Match archimind.town.design.digest without loading the Town service or its SDKs.
    home = json.loads(data)["home"].copy()
    expected = home.pop("id")
    canonical = json.dumps(
        home, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    if hashlib.sha256(canonical).hexdigest() != expected:
        raise ValueError("Saved home contents do not match the Town home ID")


def proof_has_saved_style(proof, receipt, expected_snapshot=None):
    """Inherit a proof's verified lighting workflow, with an optional source pin."""
    filename = "saved-style-receipt.json"
    path = proof / filename
    digest = receipt["files"].get(filename)
    if digest is None:
        if expected_snapshot is not None or path.exists():
            raise ValueError("The approved proof contains no verified saved style")
        return False
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Invalid saved style receipt digest")
    style = json.loads(data)
    keys = ("manifest_sha256", "revision", "home_id")
    if any(style[key] != receipt[key] for key in keys):
        raise ValueError("Saved style receipt identifies another proof")
    if not re.fullmatch(r"[0-9a-f]{64}", style["snapshot_sha256"]):
        raise ValueError("Invalid source snapshot digest")
    if expected_snapshot is not None:
        supplied = hashlib.sha256(expected_snapshot.read_bytes()).hexdigest()
        if style["snapshot_sha256"] != supplied:
            raise ValueError(
                "The approved proof was rendered from another style snapshot"
            )
    return True


def stage(source, output, *, snapshot=False):
    commit, _, path = source.partition(":")
    name = PurePosixPath(path)
    if not (
        re.fullmatch(r"[0-9a-f]{40}", commit)
        and re.fullmatch(r"[A-Za-z0-9._/-]+", path)
        and name.is_relative_to("docs/data")
        and ".." not in name.parts
        and name.suffix == ".json"
    ):
        raise ValueError("Expected a full commit SHA and docs/data/*.json")
    subprocess.run(
        ["git", "fetch", "--no-tags", "--depth=1", "origin", commit], check=True
    )
    spec = f"{commit}:{path}"
    size = int(subprocess.check_output(["git", "cat-file", "-s", spec]))
    if not 0 < size <= 4 * 1024 * 1024:
        raise ValueError("Expected a nonempty manifest at most 4 MiB")
    data = subprocess.check_output(["git", "cat-file", "blob", spec])
    if snapshot:
        verify_snapshot(data)
    output.write_bytes(data)
    print(
        f"Staged {source} ({len(data)} bytes), SHA-256 {hashlib.sha256(data).hexdigest()}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    stage(args.source, args.output, snapshot=args.snapshot)
