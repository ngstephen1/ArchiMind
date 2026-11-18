"""Exercise the installed binary, offline rebuilds, removal and concurrent public lookup."""

import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from archimind import design_evidence as evidence


def main():
    state = evidence.state_dir()
    spec_file = Path("data/design_evidence/sources.json")
    spec = json.loads((evidence.ROOT / spec_file).read_text())
    # Check citation targets independently against the immutable Git objects.
    for path in {row["path"] for row in spec["passages"]}:
        raw = subprocess.check_output(
            ["git", "show", f"{spec['revision']}:{path}"], cwd=evidence.ROOT
        )
        assert (evidence.ROOT / path).read_bytes() == raw, path
    pages = evidence.corpus(evidence.ROOT)
    with tempfile.TemporaryDirectory(dir=state) as tmp:
        sandbox = Path(tmp)
        executable = evidence.binary(state)
        (sandbox / executable.name).symlink_to(executable)
        first = evidence.build(sandbox, pages)
        receipt = json.loads((sandbox / "active.json").read_text())
        first_hits = evidence.search_design_evidence("Belaya", state=sandbox)
        second = evidence.build(sandbox, pages)
        assert first["imported"] == second["imported"] == len(pages)
        assert (
            receipt["manifest"]
            == json.loads((sandbox / "active.json").read_text())["manifest"]
        )

        def lookup():
            return evidence.search_design_evidence(
                "synthetic-private-marker Belaya", state=sandbox
            )

        with ThreadPoolExecutor(2) as pool:
            one, two = [f.result() for f in [pool.submit(lookup), pool.submit(lookup)]]
        assert first_hits == one == two and one["status"] == "found", (
            one["status"],
            two["status"],
        )
        assert all(
            evidence.digest(h["excerpt"].encode()) == h["sha256"] for h in one["hits"]
        )
        reduced = dict(pages)
        del reduced["belaya-size"]
        evidence.build(sandbox, reduced)
        assert lookup()["status"] == "stale"
        active = json.loads((sandbox / "active.json").read_text())
        directory = sandbox / active["directory"]
        assert "belaya-size" not in evidence.query(executable, directory, ["belaya"])
        for path in sandbox.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            with path.open("rb") as stream:
                previous = b""
                for chunk in iter(lambda: stream.read(65536), b""):
                    assert b"synthetic-private-marker" not in previous + chunk
                    previous = chunk[-32:]
        print(
            f"{len(pages)} source-verified pages; two matching imports; concurrent search and removal passed"
        )


if __name__ == "__main__":
    main()
