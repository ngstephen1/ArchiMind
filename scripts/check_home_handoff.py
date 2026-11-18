"""Check a pair of saved Town boards against the edited Blender render receipt."""

import argparse
import hashlib
import json
from pathlib import Path


def chair(board):
    rooms = [r for r in board["rooms"] if r["room"]["id"] == "bedroom"]
    if len(rooms) != 1:
        raise ValueError("expected one bedroom")
    chairs = [f for f in rooms[0]["furniture"] if f["id"] == "desk-chair"]
    if len(chairs) != 1:
        raise ValueError("expected one bedroom desk-chair")
    return [chairs[0]["x_m"], chairs[0]["y_m"]]


def check(before, after, receipt):
    digest = hashlib.sha256(after).hexdigest()
    first, last = json.loads(before), json.loads(after)
    if any(b.get("kind") != "whole-home-presentation" for b in (first, last)):
        raise ValueError("expected whole-home manifests")
    if first["project"] != last["project"] or last["revision"] != first["revision"] + 1:
        raise ValueError("expected consecutive revisions of one project")
    if first["home_id"] == last["home_id"] or chair(first) == chair(last):
        raise ValueError("expected a saved chair move")
    if (last["home_id"], last["revision"], digest, digest) != (
        receipt["home_id"],
        receipt["revision"],
        receipt["manifest_sha256"],
        receipt["files"]["manifest.json"],
    ):
        raise ValueError("render receipt does not match edited manifest")
    return {
        "project": last["project"],
        "revision": last["revision"],
        "sha256": digest,
        "chair_before_m": chair(first),
        "chair_after_m": chair(last),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("before", "after", "receipt"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                check(
                    args.before.read_bytes(),
                    args.after.read_bytes(),
                    json.loads(args.receipt.read_bytes()),
                ),
                indent=2,
            )
        )
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(1, f"Cannot verify handoff: {exc}\n")
