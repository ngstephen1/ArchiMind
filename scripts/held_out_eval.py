"""Run the sealed held-out Town evaluation (#68) against a local evaluation database.

The packet, prompts, answer key and full receipts stay in an ignored directory
(default ``storage/eval-68``). Only ``matrix`` writes a public summary, and it
contains case IDs, slot names, outcomes, scores, calls, latency and the commit.

    setup   verify the packet hash, initialise the evaluation database and apply
            the zero-call base homes for cases whose controls name a ``base``
    run     submit one live case through the local Town API and record a receipt
            (requires --confirm-live; makes the app's bounded OpenAI calls)
    record  record a saved-design answer observed in the ordinary browser
    matrix  write the public results matrix from receipts and the owner's scores
"""

import argparse
import hashlib
import json
import os
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


def model_name():
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        if line.startswith("ARCHIMIND_OPENAI_MODEL="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return os.getenv("ARCHIMIND_OPENAI_MODEL", "")


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
            "model": model_name(),
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
    receipt_path = out / "receipts" / f"{args.case}.json"
    if receipt_path.exists() and not args.rerun:
        raise SystemExit(
            f"{receipt_path} exists. Pass --rerun to keep it and add a rerun."
        )
    c = case(packet, args.case)
    if args.case in plan["bases"]:
        project, base = (
            plan["bases"][args.case]["project"],
            plan["bases"][args.case]["revision"],
        )
    else:
        project, base = call(args.api, "/projects", {})["project"], 0
    before = (
        call(args.api, f"/projects/{project}?revision={base}")["home"] if base else None
    )
    req = request_for(c, project, base, plan["bases"].get(args.case, {}).get("brief"))
    started = time.time()
    job = call(args.api, "/jobs", req)["job"]
    events, status = [], "queued"
    while status not in {"ready", "failed", "cancelled"}:
        if time.time() - started > 240:
            break
        time.sleep(0.75)
        feed = call(
            args.api, f"/jobs/{job}/events?after={events[-1]['seq'] if events else 0}"
        )
        events += feed["events"]
        status = feed["status"]
    finished = time.time()
    result = call(args.api, f"/jobs/{job}")["result"]
    phases = {}
    for e in events:
        if e["task"].startswith("OpenAI"):
            phases.setdefault(e["task"], []).append(e["state"])
    after = (
        call(args.api, f"/projects/{project}?revision={base}")["home"] if base else None
    )
    candidates = result if status == "ready" and isinstance(result, list) else []
    receipt = {
        "case": args.case,
        **commit(),
        "model": model_name(),
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
        "provider_calls_started": len(phases),
        "provider_count_basis": "one bounded call per recorded OpenAI phase in the worker",
        "candidate_count": len(candidates),
        "candidate_sha256": [digest(h) for h in candidates],
        "prior_snapshot_unchanged": None
        if base == 0
        else digest(before) == digest(after),
        "result": result,
        "events": events,
    }
    if receipt_path.exists():
        receipt_path = receipt_path.with_name(f"{args.case}-rerun-{int(started)}.json")
    save(receipt_path, receipt)
    print(
        f"{args.case}: {status} in {receipt['elapsed_s']} s, "
        f"{len(candidates)} candidate(s), {len(phases)} OpenAI phase(s) -> {receipt_path}"
    )


def record(args):
    out = Path(args.out)
    plan = json.loads((out / "run-plan.json").read_text(encoding="utf-8"))
    base = plan["bases"][args.case]
    save(
        out / "receipts" / f"{args.case}.json",
        {
            "case": args.case,
            **commit(),
            "project": base["project"],
            "revision": args.revision,
            "path": "Ask about the saved design (browser, deterministic)",
            "viewport": args.viewport,
            "answer": Path(args.answer_file).read_text(encoding="utf-8"),
            "provider_calls_started": 0,
            "recorded_unix": time.time(),
        },
    )
    print(f"Recorded {args.case}.")


PUBLIC_FIELDS = [
    "commit",
    "tracked_changes",
    "model",
    "packet_sha256",
    "base_revision",
    "status",
    "elapsed_s",
    "provider_calls_started",
    "candidate_count",
    "candidate_sha256",
    "prior_snapshot_unchanged",
    "path",
    "viewport",
]


def public_receipt(out, scores):
    """Allow-list fields so prompts, answer keys, results and answers stay private."""
    cases = {}
    for cid, slot in SLOTS.items():
        path = out / "receipts" / f"{cid}.json"
        r = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        row = {"slot": slot, **{k: r[k] for k in PUBLIC_FIELDS if k in r}}
        if "provider_phases" in r:
            row["provider_phases"] = sorted(r["provider_phases"])
        row["scores"] = {
            k: v
            for k, v in scores.get(cid, {}).items()
            if k in AXES + ["outcome", "severity", "reviewer"]
        }
        cases[cid] = row
    return {"issue": 68, "scoring_status": scores.get("_status", ""), "cases": cases}


def matrix(args):
    out = Path(args.out)
    scores = json.loads((out / "scores.json").read_text(encoding="utf-8"))
    save(Path(args.output).with_suffix(".json"), public_receipt(out, scores))
    rows = [
        "| Case | Slot | Commit | Outcome | Calls | Elapsed (s) | "
        + " | ".join(a.replace("_", " ").capitalize() for a in AXES)
        + " | Severity | Reviewer |",
        "|" + " --- |" * (8 + len(AXES)),
    ]
    for cid, slot in SLOTS.items():
        path = out / "receipts" / f"{cid}.json"
        r = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        s = scores.get(cid, {})
        rows.append(
            f"| {cid} | {slot} | `{r.get('commit', '')[:7]}` | {s.get('outcome', 'not run')} | "
            f"{r.get('provider_calls_started', '')} | {r.get('elapsed_s', '—')} | "
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
    p = sub.add_parser("run")
    p.add_argument("case")
    p.add_argument("--packet", required=True)
    p.add_argument("--api", default="http://127.0.0.1:8890/api")
    p.add_argument("--confirm-live", action="store_true")
    p.add_argument("--rerun", action="store_true")
    p.set_defaults(func=run)
    p = sub.add_parser("record")
    p.add_argument("case")
    p.add_argument("--revision", type=int, default=1)
    p.add_argument("--viewport", default="1440x1000")
    p.add_argument("--answer-file", required=True)
    p.set_defaults(func=record)
    p = sub.add_parser("matrix")
    p.add_argument("--output", required=True)
    p.set_defaults(func=matrix)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
