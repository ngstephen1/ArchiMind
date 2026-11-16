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
    if args.kaggle_auth:
        from archimind.datasets.remote import kaggle_headers

        try:
            headers = kaggle_headers()
        except PermissionError as error:
            _emit({"status": "blocked", "reason": str(error)})
            return EXIT_BLOCKED
    elif args.auth_env:
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
            "cached": receipt.cached,
        }
    )
    return EXIT_OK


def _write_out(args, payload: dict) -> None:
    if getattr(args, "out", None):
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        atomic_write_bytes(Path(args.out), text.encode("utf-8"))


def _files(files) -> list[dict]:
    return [
        {"path": f.path, "size_bytes": f.size_bytes, "sha256": f.sha256} for f in files
    ]


def _cmd_probe_hf(args) -> int:
    from archimind.datasets.remote import hf_dataset_revision, hf_tree

    info = hf_dataset_revision(args.repo)
    revision = args.revision or info["revision"]
    files = hf_tree(args.repo, revision)
    payload = info | {
        "revision": revision,
        "current_revision": info["revision"],
        "file_count": len(files),
        "total_bytes": sum(f.size_bytes for f in files),
        "files": _files(files),
    }
    _write_out(args, payload)
    _emit(payload)
    return EXIT_OK


def _cmd_probe_kaggle(args) -> int:
    from archimind.datasets.remote import (
        kaggle_dataset_view,
        kaggle_download_url,
        kaggle_files,
    )

    try:
        payload = kaggle_dataset_view(args.ref)
        files = kaggle_files(args.ref)
    except PermissionError as error:
        payload = {"ref": args.ref, "files": None, "blocked": str(error)}
        _write_out(args, payload)
        _emit(payload)
        return EXIT_BLOCKED
    payload |= {"file_count": len(files), "files": _files(files)}
    wanted = [f for f in files if f.path.rsplit("/", 1)[-1] == "model_info.json"]
    payload["model_info"] = [
        {
            "path": f.path,
            "size_bytes": f.size_bytes,
            "url": kaggle_download_url(args.ref, f.path),
        }
        for f in wanted
    ]
    _write_out(args, payload)
    _emit({k: v for k, v in payload.items() if k != "files"})
    return EXIT_OK


def _cmd_probe_tar_prefix(args) -> int:
    from archimind.datasets.remote import gzip_tar_prefix

    headers = {}
    if args.auth_env and os.environ.get(args.auth_env):
        headers["Authorization"] = f"Bearer {os.environ[args.auth_env]}"
    listing = gzip_tar_prefix(args.url, max_bytes=args.max_bytes, headers=headers)
    files = [m for m in listing.members if m[2] == "file"]
    top = sorted({m[0].split("/")[0] for m in listing.members})
    payload = {
        "url": listing.url,
        "bytes_read": listing.bytes_read,
        "complete": listing.complete,
        "members": len(listing.members),
        "files": len(files),
        "file_bytes": sum(m[1] for m in files),
        "top_level": top[:50],
        "suffixes": dict(
            sorted(
                {
                    s: sum(1 for m in files if m[0].endswith(s))
                    for s in {
                        "." + m[0].rsplit(".", 1)[-1] for m in files if "." in m[0]
                    }
                }.items()
            )
        ),
        "first_members": [list(m) for m in listing.members[:40]],
    }
    _write_out(args, payload | {"all_members": [list(m) for m in listing.members]})
    _emit(payload)
    return EXIT_OK


def _cmd_probe_ssr(args) -> int:
    from archimind.datasets.canonical import file_sha256
    from archimind.datasets.ssr import iter_parquet_rows, probe, profile_row

    profiles, inputs = [], []
    for path in sorted(Path(p) for p in args.parquet):
        inputs.append({"file": path.name, "sha256": file_sha256(path)})
        for row in iter_parquet_rows(path):
            profile = profile_row(row, args.room_type)
            if profile is not None:
                profiles.append(profile)
    payload = {"room_type": args.room_type, "inputs": inputs} | probe(profiles)
    _write_out(args, payload)
    _emit(payload)
    return EXIT_OK


def _cmd_probe_join(args) -> int:
    from archimind.datasets.canonical import strict_loads
    from archimind.datasets.midi import build_index, join_report
    from archimind.datasets.ssr import iter_parquet_rows, profile_row, room_key

    midi = Path(args.midi_dir)

    def load(name):
        return strict_loads((midi / name).read_bytes())

    index = build_index(
        load("midi_room_ids.json"),
        load("midi_furniture_ids.json"),
        test_room_ids=load("midi_test_room_ids.json"),
    )

    def ssr_rooms():
        for path in sorted(Path(p) for p in args.parquet):
            for row in iter_parquet_rows(path):
                profile = profile_row(row, "bedroom")
                if profile is None:
                    continue
                key = room_key(profile.file_id, profile.room_id)
                yield key, profile.split, profile.tier, profile.jids

    payload = {
        "midi_rooms": len(index.rooms),
        "midi_jids": len(index.jid_categories),
    } | join_report(ssr_rooms(), index)
    _write_out(args, payload)
    _emit(payload)
    return EXIT_OK


def _cmd_ssr_build(args) -> int:
    """P2a: real SSR parquet -> scenes/exclusions/report (and optionally a pack)."""
    from archimind.datasets.canonical import file_sha256, strict_loads, write_jsonl
    from archimind.datasets.contracts import (
        PermissionRecord,
        SourceFile,
        SourceManifest,
    )
    from archimind.datasets.midi import build_index
    from archimind.datasets.pack import PackError, build_pack, verify_pack
    from archimind.datasets.ssr import iter_parquet_rows
    from archimind.datasets.ssr_adapter import (
        CATEGORY_MAP_VERSION,
        TRANSFORM_VERSION,
        build_report,
        convert_row,
        deduplicate,
    )

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        _emit({"status": "failed", "reason": "output directory is not empty"})
        return EXIT_FAIL
    inventory = strict_loads(Path(args.inventory).read_bytes())
    revision = inventory["revision"]
    pinned = {f["sha256"]: f for f in inventory["files"] if f.get("sha256")}
    midi = Path(args.midi_dir)

    def load(name):
        return strict_loads((midi / name).read_bytes())

    index = build_index(
        load("midi_room_ids.json"),
        load("midi_furniture_ids.json"),
        test_room_ids=load("midi_test_room_ids.json"),
    )
    jid_categories, jid_fine, future_report = index.jid_categories, {}, None
    future_given = [
        args.future_model_info,
        args.future_sha256,
        args.future_inventory,
    ]
    if any(future_given) and not all(future_given):
        _emit(
            {
                "status": "failed",
                "reason": "--future-model-info, --future-sha256 and "
                "--future-inventory go together",
            }
        )
        return EXIT_FAIL
    if args.future_model_info:
        from archimind.datasets.future import (
            FutureInfoError,
            merge_categories,
            parse_model_info,
        )

        info_path = Path(args.future_model_info)
        info_sha = file_sha256(info_path)
        future_inventory = strict_loads(Path(args.future_inventory).read_bytes())
        listed = [
            m
            for m in future_inventory.get("model_info") or []
            if m.get("size_bytes") == info_path.stat().st_size
        ]
        if info_sha != args.future_sha256 or len(listed) != 1:
            _emit(
                {
                    "status": "failed",
                    "reason": "model_info.json does not match --future-sha256 "
                    "and the Kaggle inventory",
                }
            )
            return EXIT_FAIL
        try:
            future = parse_model_info(strict_loads(info_path.read_bytes()))
            jid_categories, future_report = merge_categories(
                future.super_categories, index.jid_categories
            )
        except FutureInfoError as error:
            _emit({"status": "failed", "reason": str(error)})
            return EXIT_FAIL
        jid_fine = future.fine_categories
        future_report |= {
            "ref": future_inventory["ref"],
            "version": future_inventory["version"],
            "path": listed[0]["path"],
            "size_bytes": listed[0]["size_bytes"],
            "sha256": info_sha,
        }
    results, source_files = [], []
    for path in sorted(Path(p) for p in args.parquet):
        sha = file_sha256(path)
        entry = pinned.get(sha)
        if entry is None or entry["size_bytes"] != path.stat().st_size:
            _emit(
                {
                    "status": "failed",
                    "reason": f"{path.name} is not in the pinned inventory",
                }
            )
            return EXIT_FAIL
        source_files.append(
            SourceFile(path=entry["path"], size_bytes=entry["size_bytes"], sha256=sha)
        )
        for row in iter_parquet_rows(path):
            result = convert_row(
                row,
                revision=revision,
                source_sha256=sha,
                jid_categories=jid_categories,
                midi_splits=index.splits,
                jid_fine_categories=jid_fine,
            )
            if result is not None:
                results.append(result)
    scenes, exclusions = deduplicate(results)
    report = {
        "source": "ssr_3dfront",
        "revision": revision,
        "inputs": [f.model_dump() for f in sorted(source_files, key=lambda f: f.path)],
        "bedroom_rows": len(results),
        "category_sources": {"midi": "furniture ids", "future_3d": future_report},
    } | build_report(scenes, exclusions)
    out.mkdir(parents=True, exist_ok=True)
    report["outputs"] = {}
    for name, records in (("scenes.jsonl", scenes), ("exclusions.jsonl", exclusions)):
        sha, count = write_jsonl(out / name, records)
        report["outputs"][name] = {"sha256": sha, "records": count}
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    atomic_write_bytes(out / "report.json", text.encode("utf-8"))

    if args.pack_dir:
        if not (args.permission and args.retrieved_utc):
            _emit(
                {
                    "status": "failed",
                    "reason": "--pack-dir needs --permission and --retrieved-utc",
                }
            )
            return EXIT_FAIL
        permission = PermissionRecord.model_validate_json(
            Path(args.permission).read_bytes()
        )
        manifests = [
            SourceManifest(
                source="ssr_3dfront",
                origin_url=f"https://huggingface.co/datasets/{inventory['repo']}",
                revision=revision,
                retrieved_utc=args.retrieved_utc,
                files=tuple(sorted(source_files, key=lambda f: f.path)),
                permission=permission,
            )
        ]
        if future_report:
            if not (args.future_permission and args.future_retrieved_utc):
                _emit(
                    {
                        "status": "failed",
                        "reason": "a pack with 3D-FUTURE categories needs "
                        "--future-permission and --future-retrieved-utc",
                    }
                )
                return EXIT_FAIL
            manifests.append(
                SourceManifest(
                    source="future_3d",
                    origin_url=f"https://www.kaggle.com/datasets/{future_report['ref']}",
                    revision=f"kaggle-v{future_report['version']}",
                    retrieved_utc=args.future_retrieved_utc,
                    files=(
                        SourceFile(
                            path=future_report["path"],
                            size_bytes=future_report["size_bytes"],
                            sha256=future_report["sha256"],
                        ),
                    ),
                    permission=PermissionRecord.model_validate_json(
                        Path(args.future_permission).read_bytes()
                    ),
                )
            )
        try:
            pack = build_pack(
                Path(args.pack_dir),
                pack_id=args.pack_id,
                audience=args.audience,
                sources=manifests,
                scenes=scenes,
                exclusions=exclusions,
                assets=[],
                glb_files={},
                transform_version=TRANSFORM_VERSION,
                category_map_version=CATEGORY_MAP_VERSION,
                builder=f"archimind.datasets ssr-build {report['adapter_version']}",
                created_utc=args.retrieved_utc,
            )
            verify_pack(Path(args.pack_dir))
        except PackError as error:
            _emit({"status": "failed", "reason": str(error)} | {"report": report})
            return EXIT_FAIL
        report["pack"] = {"pack_id": pack.pack_id, "snapshot_id": pack.snapshot_id}
    _emit({"status": "built"} | report)
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
    p.add_argument(
        "--kaggle-auth",
        action="store_true",
        help="Use KAGGLE_USERNAME/KAGGLE_KEY (Basic auth)",
    )
    p.add_argument("--floor-gib", type=int, default=4)
    p.add_argument("--timeout", type=float, default=60.0)
    p.set_defaults(func=_cmd_fetch)

    p = sub.add_parser("probe-hf", help="Pin a Hugging Face dataset and list files")
    p.add_argument("repo")
    p.add_argument("--revision", help="Exact 40-character revision (default: current)")
    p.add_argument("--out")
    p.set_defaults(func=_cmd_probe_hf)

    p = sub.add_parser("probe-kaggle", help="Kaggle dataset version and file list")
    p.add_argument("ref")
    p.add_argument("--out")
    p.set_defaults(func=_cmd_probe_kaggle)

    p = sub.add_parser("probe-tar-prefix", help="List a capped .tar.gz prefix")
    p.add_argument("url")
    p.add_argument("--max-bytes", type=int, required=True)
    p.add_argument("--auth-env")
    p.add_argument("--out")
    p.set_defaults(func=_cmd_probe_tar_prefix)

    p = sub.add_parser("probe-ssr", help="Yield/identity profile of SSR parquet files")
    p.add_argument("parquet", nargs="+")
    p.add_argument("--room-type", default="bedroom")
    p.add_argument("--out")
    p.set_defaults(func=_cmd_probe_ssr)

    p = sub.add_parser("probe-join", help="SSR bedrooms joined to MIDI identities")
    p.add_argument("parquet", nargs="+")
    p.add_argument("--midi-dir", required=True)
    p.add_argument("--out")
    p.set_defaults(func=_cmd_probe_join)

    p = sub.add_parser("ssr-build", help="P2a: SSR bedrooms -> scene references")
    p.add_argument("parquet", nargs="+")
    p.add_argument(
        "--inventory", required=True, help="probe-hf output that pins the shards"
    )
    p.add_argument("--midi-dir", required=True)
    p.add_argument("--out", required=True, help="new or empty stage directory")
    p.add_argument("--pack-dir", help="also build and verify a pack here")
    p.add_argument("--pack-id", default="ssr-bedrooms")
    p.add_argument("--audience", choices=("local", "public"), default="local")
    p.add_argument("--permission", help="PermissionRecord JSON decided by the owner")
    p.add_argument("--retrieved-utc", help="when the pinned shards were fetched")
    p.add_argument(
        "--future-model-info",
        help="P2b: 3D-FUTURE model_info.json (primary categories)",
    )
    p.add_argument("--future-sha256", help="expected SHA-256 of model_info.json")
    p.add_argument("--future-inventory", help="probe-kaggle output listing it")
    p.add_argument("--future-permission", help="PermissionRecord JSON for 3D-FUTURE")
    p.add_argument("--future-retrieved-utc", help="when model_info.json was fetched")
    p.set_defaults(func=_cmd_ssr_build)
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
