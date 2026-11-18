"""Run the original-chair authoring recipe using Blender Lab's pinned integration harness."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def run(upstream, output):
    sys.path.insert(0, str(upstream.resolve()))
    from tests.test_blender_mcp_with_blender import TestBackgroundServer

    script = Path(__file__).with_name("author_designer_chair.py").resolve()
    output.mkdir(exist_ok=False)
    session = TestBackgroundServer()
    snapshots = {}
    try:
        TestBackgroundServer.setUpClass()
        for variant in ("gentle", "deep"):
            folder = (output / variant).resolve()
            metadata = session._test_tool(
                "execute_blender_code",
                {
                    "code": (
                        "import runpy\n"
                        f"result = runpy.run_path({str(script)!r})['author_chair']"
                        f"({str(folder)!r}, {variant!r})"
                    )
                },
            )
            if metadata.get("variant") != variant:
                raise RuntimeError(f"Blender authoring failed: {metadata}")
            objects = session._test_tool("get_objects_summary")
            if objects.get("status") != "ok":
                raise RuntimeError(f"Scene inspection failed: {objects}")
            for name, digest in metadata["sha256"].items():
                if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
                    raise ValueError(f"Artifact digest mismatch for {variant}/{name}")
            # Open the project in a second Blender process. The exported library must
            # contain the entire editable chair, its studio, and both named cameras.
            inspection = (
                "import bpy; "
                f"s=next(s for s in bpy.data.scenes if s.get('archimind_variant')=={variant!r}); "
                f"assert all(any(o.name.split('.')[0]==n and o.type=='MESH' for o in s.objects) "
                f"for n in {metadata['inputs']['parts']!r}); "
                "assert sum(o.type=='CAMERA' for o in s.objects)==2"
            )
            subprocess.run(
                [
                    os.environ["BLENDER_BIN"],
                    "--background",
                    str(folder / "chair.blend"),
                    "--python-exit-code",
                    "1",
                    "--python-expr",
                    inspection,
                ],
                check=True,
            )
            snapshots[variant] = {"scene": objects, "sha256": metadata["sha256"]}
        if (
            snapshots["gentle"]["sha256"]["chair.glb"]
            == snapshots["deep"]["sha256"]["chair.glb"]
        ):
            raise ValueError("The back-curve variation produced identical mesh bytes")
        (output / "operator.json").write_text(json.dumps(snapshots, indent=2) + "\n")
    finally:
        TestBackgroundServer.doClassCleanups()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.upstream, args.output)
