"""``python -m archimind.datasets <command>``: the only entry point notebooks call.

Exit codes: 0 success, 1 failure, 2 usage error, 3 blocked (capacity floor or a
missing credential). Output is one JSON document on stdout. Tokens are read from
environment variables by name, never from arguments, and are never printed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from archimind.datasets.canonical import atomic_write_bytes
from archimind.datasets.safe_io import (
    GIB,
    CapacityError,
    UnsafeContentError,
    bounded_download,
)

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_BLOCKED = 0, 1, 2, 3


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _cmd_env(args) -> int:
    from archimind.datasets.envinfo import environment_receipt

    receipt = environment_receipt(
        Path(args.data_root), floor_bytes=args.floor_gib * GIB
    )
    if args.out:
        text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        atomic_write_bytes(Path(args.out), text.encode("utf-8"))
    _emit(receipt)
    return EXIT_OK if receipt["above_floor"] else EXIT_BLOCKED


def _cmd_sync(args) -> int:
    from archimind.datasets.stages import sync_tree

    report = sync_tree(Path(args.src), Path(args.dst))
    _emit(
        {
            "copied": report.copied,
            "unchanged": report.unchanged,
            "bytes_copied": report.bytes_copied,
        }
    )
    return EXIT_OK


def _verified_summary(pack) -> dict:
    return {
        "status": "verified",
        "pack_id": pack.manifest.pack_id,
        "audience": pack.manifest.audience,
        "snapshot_id": pack.manifest.snapshot_id,
        "scenes": len(pack.scenes),
        "exclusions": len(pack.exclusions),
        "assets": len(pack.assets),
        "sources": sorted(s.source for s in pack.sources),
    }


def _cmd_verify(args) -> int:
    from archimind.datasets.pack import PackError, verify_pack

    try:
        pack = verify_pack(Path(args.root))
    except PackError as error:
        _emit({"status": "invalid", "reason": str(error)})
        return EXIT_FAIL
    _emit(_verified_summary(pack))
    return EXIT_OK


def _cmd_fixture_pack(args) -> int:
    from archimind.datasets.fixtures import build_synthetic_pack
    from archimind.datasets.pack import PackError, verify_pack

    root = Path(args.root)
    if root.exists() and any(root.iterdir()):
        try:
            pack = verify_pack(root)
        except PackError as error:
            _emit({"status": "invalid_existing", "reason": str(error)})
            return EXIT_FAIL
        _emit({"status": "exists", "snapshot_id": pack.manifest.snapshot_id})
        return EXIT_OK
    manifest = build_synthetic_pack(root, audience=args.audience)
    _emit({"status": "built", "snapshot_id": manifest.snapshot_id, "synthetic": True})
    return EXIT_OK


def _cmd_fetch(args) -> int:
    headers = {}
    if args.auth_env:
        token = os.environ.get(args.auth_env)
        if not token:
            _emit({"status": "blocked", "reason": f"{args.auth_env} is not set"})
            return EXIT_BLOCKED
        headers["Authorization"] = f"Bearer {token}"
    receipt = bounded_download(
        args.url,
        Path(args.dest),
        max_bytes=args.max_bytes,
        expected_sha256=args.sha256,
        headers=headers,
        floor_bytes=args.floor_gib * GIB,
        timeout_s=args.timeout,
    )
    _emit(
        {
            "status": "fetched",
            "url": receipt.url,
            "size_bytes": receipt.size_bytes,
            "sha256": receipt.sha256,
            "resumed": receipt.resumed,
        }
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m archimind.datasets")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("env", help="Environment receipt and free-space check")
    p.add_argument("--data-root", required=True)
    p.add_argument("--floor-gib", type=int, default=4)
    p.add_argument("--out")
    p.set_defaults(func=_cmd_env)

    p = sub.add_parser("sync", help="Atomic, hash-checked copy (Drive checkpoint)")
    p.add_argument("src")
    p.add_argument("dst")
    p.set_defaults(func=_cmd_sync)

    p = sub.add_parser("verify-pack", help="Re-hash and re-validate a reference pack")
    p.add_argument("root")
    p.set_defaults(func=_cmd_verify)

    p = sub.add_parser("fixture-pack", help="Build a synthetic self-check pack")
    p.add_argument("root")
    p.add_argument("--audience", choices=("local", "public"), default="local")
    p.set_defaults(func=_cmd_fixture_pack)

    p = sub.add_parser("fetch", help="Bounded, resumable, hash-verified download")
    p.add_argument("url")
    p.add_argument("dest")
    p.add_argument("--max-bytes", type=int, required=True)
    p.add_argument("--sha256")
    p.add_argument("--auth-env", help="Name of the env var holding a bearer token")
    p.add_argument("--floor-gib", type=int, default=4)
    p.add_argument("--timeout", type=float, default=60.0)
    p.set_defaults(func=_cmd_fetch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return EXIT_OK if exit_.code == 0 else EXIT_USAGE
    try:
        return args.func(args)
    except CapacityError as error:
        _emit({"status": "blocked", "reason": "capacity_floor", "detail": str(error)})
        return EXIT_BLOCKED
    except UnsafeContentError as error:
        _emit({"status": "failed", "reason": "unsafe_content", "detail": str(error)})
        return EXIT_FAIL
