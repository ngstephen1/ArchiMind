"""Stage a pinned public Town export for a Studio render on GitHub Actions."""

import argparse
import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath


def stage(source, output):
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
    output.write_bytes(data)
    print(
        f"Staged {source} ({len(data)} bytes), SHA-256 {hashlib.sha256(data).hexdigest()}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    stage(args.source, args.output)
