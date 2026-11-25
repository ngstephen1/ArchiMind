"""Run the sealed held-out Town evaluation (#68) against a local evaluation database.

The packet, prompts, answer key and full receipts stay in an ignored directory
(default ``storage/eval-68``). Only ``matrix`` writes a public summary, and it
contains run IDs, slot names, outcomes, scores, phases, latency and commits.

    setup   verify the packet hash, initialise the evaluation database and apply
            the zero-call base homes for cases whose controls name a ``base``
    serve   launch Town on the evaluation database and record its commit and model
    run     submit one live case through the local Town API and record a receipt
            (requires --confirm-live; makes the app's bounded OpenAI calls)
    record  record a saved-design answer observed in the ordinary browser
    matrix  write the public results matrix from receipts and the owner's scores
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOTS = {
    "H01": "Hosting and home-office trade-offs on a fresh lot",
    "H02": "Ambiguous or conflicting seating that needs a confirmation",
    "H03": "Width conversion and circulation on a compact lot",
    "H04": "Room lock and targeted change to a saved revision",
    "H05": "Two plausible object referents in a saved-design follow-up",
    "H06": "Conclusion that needs site, supplier or acoustic evidence",
}
AXES = [
    "hard_constraints",
    "source_accuracy",
    "candidate_difference",
    "latency",
    "provider_use",
]


def digest(data):
    raw = data if isinstance(data, bytes) else json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def commit():
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True
    ).strip()
    return {"commit": head, "tracked_changes": bool(dirty)}


def load_packet(path, expected=None):
    raw = Path(path).read_bytes()
    actual = digest(raw)
    if expected and actual != expected:
        raise SystemExit(f"Packet SHA-256 mismatch: {actual}")
    return json.loads(raw), actual


def case(packet, cid):
    for c in packet["cases"]:
        if c["id"] == cid:
            return c
    raise SystemExit(f"Unknown case {cid}")


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)


def effective_model():
    """Resolve the model the way the Town launcher does: shell, then .env, then default.

    The .env file is read with the launcher's own parser, so spacing and repeated
    assignments resolve to the same value Town would use.
    """
    if os.getenv("ARCHIMIND_OPENAI_MODEL"):
        return os.environ["ARCHIMIND_OPENAI_MODEL"]
    scripts = str(Path(__file__).resolve().parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from run_with_agent import settings_from_dotenv

    value = settings_from_dotenv(ROOT / ".env").get("ARCHIMIND_OPENAI_MODEL")
    if value:
        return value
    sys.path.insert(0, str(ROOT / "src"))
    from archimind.agents.requirements_agent import DEFAULT_MODEL

    return DEFAULT_MODEL


def town_start(out, requested_api=None):
    """The commit and model Town was launched with by ``serve``; refuse stale servers."""
    path = Path(out) / "town-start.json"
    if not path.exists():
        raise SystemExit(
            "Start Town with `serve` so its commit and model are recorded."
        )
    start = json.loads(path.read_text(encoding="utf-8"))
    now = commit()
    if (
        start["commit"] != now["commit"]
        or start["tracked_changes"]
        or now["tracked_changes"]
    ):
        raise SystemExit(
            f"Town was started from {start['commit'][:7]} but the checkout is "
            f"{now['commit'][:7]}. Restart it with `serve` before recording a run."
        )
    api = start.get("api", "")
    instance = start.get("instance")
    if not re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}/api", api) or not instance:
        raise SystemExit("Restart Town with this version of the evaluation launcher.")
    if requested_api and requested_api.rstrip("/") != api:
        raise SystemExit(
            "The requested API differs from the Town instance launched by serve."
        )
    try:
        with urllib.request.urlopen(
            api.removesuffix("/api") + "/health", timeout=5
        ) as response:
            observed = response.headers.get("X-Archimind-Evaluation-Instance")
    except OSError:
        raise SystemExit(
            "The evaluation Town instance is unavailable. Restart it with serve."
        ) from None
    if observed != instance:
        raise SystemExit(
            "The responding Town instance does not match the evaluation launch."
        )
    return {"town_commit": start["commit"], "model": start["model"]}, api


def receipt_path(out, cid, rerun):
    """Original receipts are immutable. Each rerun gets its own file."""
    original = Path(out) / "receipts" / f"{cid}.json"
    if not original.exists():
        return original
    if not rerun:
        raise SystemExit(f"{original} exists. Pass --rerun to keep it and add a rerun.")
    # A sortable UTC timestamp plus a random suffix, so two reruns recorded in the
    # same second never share a file.
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(time.time()))
    return original.with_name(f"{cid}-rerun-{stamp}-{uuid.uuid4().hex[:8]}.json")


def serve(args):
    """Launch Town on the evaluation database, recording its commit and model."""
    out = Path(args.out)
    model = effective_model()
    instance = uuid.uuid4().hex
    save(
        out / "town-start.json",
        {
            **commit(),
            "model": model,
            "api": f"http://127.0.0.1:{args.port}/api",
            "instance": instance,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    env = dict(
        os.environ,
        TOWN_DB=str(out / "town-eval.sqlite3"),
        TOWN_PORT=str(args.port),
        TOWN_EDITOR_PORT=str(args.editor_port),
        ARCHIMIND_ENABLE_CODEX_ADVISOR="0",
        ARCHIMIND_OPENAI_MODEL=model,
        PYTHONPATH=str(ROOT / "src"),
    )
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_town.py"),
        "--evaluation-instance",
        instance,
    ]
    if args.extra_team_jobs_on:
        command += ["--extra-team-jobs-on", args.extra_team_jobs_on]
    raise SystemExit(subprocess.call(command, cwd=ROOT, env=env))


def setup(args):
    packet, sha = load_packet(args.packet, args.sha256)
    out = Path(args.out)
    db_path = out / "town-eval.sqlite3"
    if db_path.exists():
        raise SystemExit(f"{db_path} exists. Use a fresh directory for a new run.")
    os.environ.update(TOWN_MODE="local", TOWN_DB=str(db_path))
    os.environ.pop("DATABASE_URL", None)
    sys.path.insert(0, str(ROOT / "src"))
    from archimind.town import service
    from archimind.town.design import Brief, generate

    out.mkdir(parents=True, exist_ok=True)
    service.initialize()
    bases = {}
    for c in packet["cases"]:
        if "base" not in c["controls"]:
            continue
        brief = Brief(
            width=args.base_lot[0],
            depth=args.base_lot[1],
            seed=c["controls"].get("seed", args.base_seed),
            formal_salon=True,
        )
        home = generate(brief)[0]
        p = service.create("local-designer")["project"]
        with service.transaction() as q:
            service.apply(q, "local-designer", p, 0, home)
        bases[c["id"]] = {
            "project": p,
            "revision": 1,
            "brief": brief.model_dump(),
            "candidate_index": 0,
            "home_sha256": digest(home),
            "provider_calls": 0,
        }
    save(
        out / "run-plan.json",
        {
            "issue": 68,
            "packet_sha256": sha,
            "packet_baseline": packet.get("baseline"),
            **commit(),
            "model": effective_model(),
            "database": str(db_path),
            "bases": bases,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    print(
        f"Prepared {db_path} with {len(bases)} zero-call base homes: {', '.join(bases)}"
    )


def call(api, path, data=None):
    req = urllib.request.Request(
        api.rstrip("/") + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"{path}: HTTP {exc.code} {exc.read().decode()[:300]}"
        ) from None


def request_for(c, project, base, base_brief=None):
    k = c["controls"]
    brief = {
        "seed": k.get("seed", 42 + base),
        "compare_tradeoffs": k.get("compare_tradeoffs", True),
    }
    if base_brief:
        # Like the Town form, a revision request carries the saved home's lot.
        brief["width"], brief["depth"] = base_brief["width"], base_brief["depth"]
    if "lot_m" in k:
        brief["width"], brief["depth"] = k["lot_m"]
    if k.get("allow_separate_tables"):
        brief["split_dining"] = True
    return {
        "id": str(uuid.uuid4()),
        "project": project,
        "base": base,
        "message": c["submit"],
        "live": True,
        "agent_team": True,
        "brief": brief,
    }


def run(args):
    if not args.confirm_live:
        raise SystemExit("Add --confirm-live to submit a billed live case.")
    packet, sha = load_packet(args.packet)
    out = Path(args.out)
    plan = json.loads((out / "run-plan.json").read_text(encoding="utf-8"))
    if sha != plan["packet_sha256"]:
        raise SystemExit("Packet differs from the one used for setup.")
    town, api = town_start(out, args.api)
    path = receipt_path(out, args.case, args.rerun)
    c = case(packet, args.case)
    if args.case in plan["bases"]:
        project, base = (
            plan["bases"][args.case]["project"],
            plan["bases"][args.case]["revision"],
        )
    else:
        project, base = call(api, "/projects", {})["project"], 0
    before = call(api, f"/projects/{project}?revision={base}")["home"] if base else None
    req = request_for(c, project, base, plan["bases"].get(args.case, {}).get("brief"))
    started = time.time()
    job = call(api, "/jobs", req)["job"]
    events, status = [], "queued"
    while status not in {"ready", "failed", "cancelled"}:
        if time.time() - started > 240:
            break
        time.sleep(0.75)
        feed = call(
            api, f"/jobs/{job}/events?after={events[-1]['seq'] if events else 0}"
        )
        events += feed["events"]
        status = feed["status"]
    finished = time.time()
    result = call(api, f"/jobs/{job}")["result"]
    phases = {}
    for e in events:
        if e["task"].startswith("OpenAI"):
            phases.setdefault(e["task"], []).append(e["state"])
    after = call(api, f"/projects/{project}?revision={base}")["home"] if base else None
    candidates = result if status == "ready" and isinstance(result, list) else []
    receipt = {
        "case": args.case,
        **commit(),
        **town,
        "packet_sha256": sha,
        "project": project,
        "base_revision": base,
        "request": req,
        "job": job,
        "status": status,
        "submitted_unix": started,
        "elapsed_s": round(finished - started, 2),
        "first_event_s": round(events[0]["time"] - started, 2) if events else None,
        "provider_phases": phases,
        "provider_phases_started": len(phases),
        "provider_count_basis": (
            "Upper bound: OpenAI team phases started. Town can stop a phase at its "
            "deterministic review before the request is sent."
        ),
        "candidate_count": len(candidates),
        "candidate_sha256": [digest(h) for h in candidates],
        "prior_snapshot_unchanged": None
        if base == 0
        else digest(before) == digest(after),
        "result": result,
        "events": events,
    }
    save(path, receipt)
    print(
        f"{args.case}: {status} in {receipt['elapsed_s']} s, "
        f"{len(candidates)} candidate(s), {len(phases)} OpenAI phase(s) -> {path}"
    )


def record(args):
    out = Path(args.out)
    plan = json.loads((out / "run-plan.json").read_text(encoding="utf-8"))
    base = plan["bases"][args.case]
    town, api = town_start(out, args.api)
    path = receipt_path(out, args.case, args.rerun)
    project = call(api, f"/projects/{base['project']}?revision={args.revision}")
    save(
        path,
        {
            "case": args.case,
            **commit(),
            **town,
            "project": base["project"],
            "revision": args.revision,
            "path": "Ask about the saved design (browser, deterministic)",
            "viewport": args.viewport,
            "answer": Path(args.answer_file).read_text(encoding="utf-8"),
            "provider_phases_started": 0,
            # The browser path must leave the saved base revision untouched.
            "prior_snapshot_unchanged": project["head"] == base["revision"]
            and digest(project["home"]) == base["home_sha256"],
            "recorded_unix": time.time(),
        },
    )
    print(f"Recorded {args.case} -> {path}")


PUBLIC_FIELDS = [
    "commit",
    "town_commit",
    "tracked_changes",
    "model",
    "packet_sha256",
    "base_revision",
    "status",
    "elapsed_s",
    "provider_phases_started",
    "candidate_count",
    "candidate_sha256",
    "prior_snapshot_unchanged",
    "path",
    "viewport",
]
SCORE_FIELDS = AXES + ["outcome", "severity", "reviewer"]


def receipts(out):
    """Every run, original first, as (run ID, receipt). The run ID is the file stem."""
    runs = []
    for cid in SLOTS:
        files = sorted((Path(out) / "receipts").glob(f"{cid}*.json"))
        for path in sorted(files, key=lambda p: (p.stem != cid, p.stem)):
            r = json.loads(path.read_text(encoding="utf-8"))
            if r.get("case") != cid:
                raise SystemExit(f"{path.name} records case {r.get('case')}.")
            # Receipts written before the rename counted the same phases.
            r.setdefault("provider_phases_started", r.get("provider_calls_started"))
            runs.append((path.stem, r))
    return runs


def public_receipt(out, scores):
    """Allow-list fields so prompts, answer keys, results and answers stay private.

    Scores are keyed by run ID, so a rerun's score never joins the original's evidence.
    """
    runs = {}
    for run_id, r in receipts(out):
        cid = r["case"]
        row = {"case": cid, "slot": SLOTS[cid], "rerun": run_id != cid}
        row.update({k: r[k] for k in PUBLIC_FIELDS if k in r})
        if "provider_phases" in r:
            row["provider_phases"] = sorted(r["provider_phases"])
        row["scores"] = {
            k: v for k, v in scores.get(run_id, {}).items() if k in SCORE_FIELDS
        }
        runs[run_id] = row
    return {"issue": 68, "scoring_status": scores.get("_status", ""), "runs": runs}


def matrix(args):
    out = Path(args.out)
    scores = json.loads((out / "scores.json").read_text(encoding="utf-8"))
    published = public_receipt(out, scores)
    save(Path(args.output).with_suffix(".json"), published)
    rows = [
        "| Run | Slot | Town commit | Outcome | OpenAI phases | Elapsed (s) | "
        + " | ".join(a.replace("_", " ").capitalize() for a in AXES)
        + " | Severity | Reviewer |",
        "|" + " --- |" * (8 + len(AXES)),
    ]
    for run_id, r in published["runs"].items():
        s = r["scores"]
        label = run_id  # Reruns keep their IDs, which name their receipts and scores.
        town = r.get("town_commit") or r.get("commit", "")
        rows.append(
            f"| {label} | {r['slot']} | `{town[:7]}` | {s.get('outcome', 'not scored')} | "
            f"{r.get('provider_phases_started', '')} | {r.get('elapsed_s', '—')} | "
            + " | ".join(str(s.get(a, "")) for a in AXES)
            + f" | {s.get('severity', '')} | {s.get('reviewer', '')} |"
        )
    Path(args.output).write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(
        f"Wrote {args.output}. Review it for prompt or answer-key text before publishing."
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", default=str(ROOT / "storage" / "eval-68"))
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("setup")
    p.add_argument("--packet", required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--base-seed", type=int, default=178)
    p.add_argument("--base-lot", type=float, nargs=2, default=[15.0, 15.0])
    p.set_defaults(func=setup)
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8890)
    p.add_argument("--editor-port", type=int, default=8891)
    p.add_argument("--extra-team-jobs-on", metavar="YYYY-MM-DD")
    p.set_defaults(func=serve)
    p = sub.add_parser("run")
    p.add_argument("case")
    p.add_argument("--packet", required=True)
    p.add_argument("--api", help="Override only with the API recorded by serve")
    p.add_argument("--confirm-live", action="store_true")
    p.add_argument("--rerun", action="store_true")
    p.set_defaults(func=run)
    p = sub.add_parser("record")
    p.add_argument("case")
    p.add_argument("--revision", type=int, default=1)
    p.add_argument("--viewport", default="1440x1000")
    p.add_argument("--answer-file", required=True)
    p.add_argument("--api", help="Override only with the API recorded by serve")
    p.add_argument("--rerun", action="store_true")
    p.set_defaults(func=record)
    p = sub.add_parser("matrix")
    p.add_argument("--output", required=True)
    p.set_defaults(func=matrix)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
