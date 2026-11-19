"""Run the original-chair authoring recipe using Blender Lab's pinned integration harness."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def isolate_windows_profile():
    """Keep the add-on install out of the operator's real Blender profile.

    The upstream harness isolates Blender by pointing HOME at a temporary folder,
    which Blender honours on Linux and macOS. On Windows Blender reads its user
    resources from %APPDATA%, so point BLENDER_USER_RESOURCES at a fresh folder.
    """
    if os.name == "nt" and "BLENDER_USER_RESOURCES" not in os.environ:
        os.environ["BLENDER_USER_RESOURCES"] = tempfile.mkdtemp(
            prefix="archimind-blender-profile-"
        )


def patch_windows_stdio_client():
    """Replace the upstream client's select() wait, which Windows pipes reject.

    A daemon thread reads the server's stdout lines into a queue; requests wait on
    the queue with the same timeout and the same id matching as upstream.
    """
    if os.name != "nt":
        return
    import queue
    import threading
    import time

    from tests import mcp_client

    def lines(client):
        if not hasattr(client, "_lines"):
            client._lines = queue.Queue()

            def reader():
                for line in iter(client._proc.stdout.readline, b""):
                    client._lines.put(line)
                client._lines.put(b"")

            threading.Thread(target=reader, daemon=True).start()
        return client._lines

    def send_request(self, method, params=None):
        request_id = self._next_id
        self._next_id += 1
        msg = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            msg["params"] = params
        inbox = lines(self)
        self._proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        self._proc.stdin.flush()
        deadline = time.monotonic() + mcp_client._REQUEST_TIMEOUT
        while True:
            remaining = deadline - time.monotonic()
            try:
                if remaining <= 0:
                    raise queue.Empty
                line = inbox.get(timeout=remaining)
            except queue.Empty:
                raise RuntimeError(f"Timeout waiting for response to {method}") from None
            if not line:
                raise RuntimeError("MCP server closed stdout unexpectedly")
            try:
                response = json.loads(line.strip() or b"null")
            except json.JSONDecodeError:
                continue
            if not isinstance(response, dict) or response.get("id") != request_id:
                continue
            if "error" in response:
                raise RuntimeError(f"JSON-RPC error: {response['error']!r}")
            return response.get("result", {})

    mcp_client.MCPClient._send_request = send_request


def run(upstream, output):
    isolate_windows_profile()
    sys.path.insert(0, str(upstream.resolve()))
    patch_windows_stdio_client()
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


CLEAR_SESSION = """import bpy
keep = bpy.context.window.scene
for s in list(bpy.data.scenes):
    if s != keep:
        bpy.data.scenes.remove(s)
for block in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images,
              bpy.data.cameras, bpy.data.lights, bpy.data.collections, bpy.data.worlds,
              bpy.data.node_groups):
    for item in list(block):
        block.remove(item)
result = {"status": "ok"}
"""


def run_pieces(upstream, output, concepts):
    """Author designer pieces through the MCP harness and write their operator receipt.

    Each concept is built by ``scripts/author_designer_piece.py`` inside the live
    Blender session, inspected with ``get_objects_summary`` and reopened from its
    ``piece.blend`` in a second Blender process. ``operator.json`` is keyed
    ``<concept>@<version>``, which ``release_designer_piece.py`` checks.
    """
    isolate_windows_profile()
    sys.path.insert(0, str(upstream.resolve()))
    patch_windows_stdio_client()
    from tests.test_blender_mcp_with_blender import TestBackgroundServer

    script = Path(__file__).with_name("author_designer_piece.py").resolve()
    output.mkdir(exist_ok=False)
    session = TestBackgroundServer()
    receipt = {}
    try:
        TestBackgroundServer.setUpClass()
        for concept in concepts:
            folder = (output / concept).resolve()
            # Start every piece from empty data so part names (and the exported
            # bytes) never depend on which pieces were built before it.
            session._test_tool("execute_blender_code", {"code": CLEAR_SESSION})
            metadata = session._test_tool(
                "execute_blender_code",
                {
                    "code": (
                        "import runpy\n"
                        f"result = runpy.run_path({str(script)!r})['author_piece']"
                        f"({str(folder)!r}, {concept!r})"
                    )
                },
            )
            if metadata.get("concept_id") != concept:
                raise RuntimeError(f"Blender authoring failed for {concept}: {metadata}")
            objects = session._test_tool("get_objects_summary")
            if objects.get("status") != "ok":
                raise RuntimeError(f"Scene inspection failed: {objects}")
            for name, digest in metadata["sha256"].items():
                if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
                    raise ValueError(f"Artifact digest mismatch for {concept}/{name}")
            inspection = (
                "import bpy; "
                f"s=next(s for s in bpy.data.scenes if s.get('archimind_concept')=={concept!r}); "
                f"assert all(any(o.name==n and o.type=='MESH' for o in s.objects) "
                f"for n in {metadata['inputs']['parts']!r}); "
                "assert sum(o.type=='CAMERA' for o in s.objects)==2"
            )
            subprocess.run(
                [
                    os.environ["BLENDER_BIN"],
                    "--background",
                    str(folder / "piece.blend"),
                    "--python-exit-code",
                    "1",
                    "--python-expr",
                    inspection,
                ],
                check=True,
                capture_output=True,
            )
            receipt[f"{concept}@{metadata['version']}"] = {
                "parts": len(metadata["inputs"]["parts"]),
                "sha256": metadata["sha256"],
            }
            print(f"authored {concept}@{metadata['version']}", flush=True)
        (output / "operator.json").write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        TestBackgroundServer.doClassCleanups()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--pieces",
        help="Comma-separated designer piece concepts, or 'all', instead of the chair",
    )
    args = parser.parse_args()
    if args.pieces:
        sys.path.insert(0, str(Path(__file__).parent))
        from author_designer_piece import PIECES

        chosen = sorted(PIECES) if args.pieces == "all" else args.pieces.split(",")
        unknown = set(chosen) - set(PIECES)
        if unknown:
            parser.error(f"unknown concepts: {sorted(unknown)}")
        run_pieces(args.upstream, args.output, chosen)
    else:
        run(args.upstream, args.output)
