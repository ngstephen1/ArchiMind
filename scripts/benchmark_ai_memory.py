"""Reproduce public-fixture recall; never opens the developer handoff store."""

import argparse
import csv
import http.client
import json
import re
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from benchmark_design_evidence import lexical
from dev_memory import COMMIT, WORKSPACE, rpc, server, sha

from archimind import design_evidence as ev

MODEL = "all-MiniLM-L6-v2"
FILES = {
    "model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
    "config.json": "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
}
PROJECT = "public-evidence"


def models(cache):
    cache.mkdir(parents=True, exist_ok=True)
    for name, pin in FILES.items():
        path = cache / name
        if not path.exists():
            with tempfile.NamedTemporaryFile(dir=cache) as f:
                subprocess.run(
                    [
                        "curl",
                        "-fsSL",
                        "--max-time",
                        "180",
                        f"https://huggingface.co/sentence-transformers/{MODEL}/resolve/main/{name}",
                        "-o",
                        f.name,
                    ],
                    check=True,
                )
                if sha(Path(f.name)) != pin:
                    raise ValueError("model checksum mismatch")
                shutil.copyfile(f.name, path)
        if sha(path) != pin:
            raise ValueError("model checksum mismatch")


def backfill(data, port):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    try:
        conn.request(
            "POST",
            "/admin/embed",
            json.dumps(
                dict(
                    workspace=WORKSPACE,
                    project=PROJECT,
                    reembed=True,
                    dry_run=False,
                    all_projects=False,
                )
            ),
            {
                "Authorization": "Bearer " + (data / "token").read_text().strip(),
                "Content-Type": "application/json",
            },
        )
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError(f"embedding backfill failed ({response.status})")
        return json.loads(response.read())
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    state = Path.home() / ".local/share/archimind-ai-memory"
    cache = state / "models" / MODEL
    models(cache)
    pages = ev.corpus(ev.ROOT)
    brain = ev.state_dir()
    active = json.loads((brain / "active.json").read_text())
    if ev.stamp(pages) != active["manifest"]:
        raise ValueError("rebuild GBrain index")
    executable = ev.binary(brain)
    rows = []
    for split, filename in [
        ("original", "design_evidence"),
        ("holdout", "design_memory_holdout"),
    ]:
        with (ev.ROOT / f"data/benchmarks/{filename}.tsv").open() as src:
            for case in csv.DictReader(src, delimiter="\t"):
                for mode in ["filtered", "property"]:
                    words = (
                        ev.terms(case["question"])
                        if mode == "filtered"
                        else re.findall(r"[a-z0-9]+", case["question"].lower())
                    )
                    rows.append({**case, "split": split, "mode": mode, "terms": words})
    timings = {"lexical": [], "gbrain": []}
    for row in rows:
        start = time.monotonic()
        words = row["terms"]
        row["lexical"] = lexical(words, pages)
        timings["lexical"].append(time.monotonic() - start)
        start = time.monotonic()
        row["gbrain"] = (
            ev.query(executable, brain / active["directory"], words) if words else []
        )
        timings["gbrain"].append(time.monotonic() - start)
    details = {
        name: {"median_seconds": round(statistics.median(t), 6)}
        for name, t in timings.items()
    }
    for provider in ["none", "local"]:
        with tempfile.TemporaryDirectory(dir=state) as tmp:
            data = Path(tmp)
            if provider == "local":
                shutil.copytree(cache, data / "models" / MODEL)
            port = 49485
            with server(state / "ai-memory", data, port, PROJECT, provider):
                for key, page in pages.items():
                    rpc(
                        data,
                        port,
                        "memory_write_page",
                        dict(
                            path=f"concepts/{key}.md",
                            body=page["excerpt"],
                            title=page["title"],
                            create_only=True,
                        ),
                        PROJECT,
                    )
                if provider == "local":
                    summary = backfill(data, port)
                    if (
                        summary.get("embedded") != len(pages)
                        or summary.get("failed") != 0
                    ):
                        raise ValueError(f"incomplete backfill: {summary}")
                times = []
                streams = set()
                for row in rows:
                    start = time.monotonic()
                    if row["terms"]:
                        resp = rpc(
                            data,
                            port,
                            "memory_query",
                            dict(query=" ".join(row["terms"]), limit=3, explain=True),
                            PROJECT,
                        )
                        streams.update(resp["streams_active"])
                        if any(
                            hit["path"] not in {f"concepts/{k}.md" for k in pages}
                            for hit in resp["hits"]
                        ):
                            raise ValueError("unknown evidence path")
                        ids = [
                            hit["path"].removeprefix("concepts/").removesuffix(".md")
                            for hit in resp["hits"]
                        ]
                    else:
                        ids = []
                    row[provider] = ids
                    times.append(time.monotonic() - start)
                if provider == "local" and "vector" not in streams:
                    raise ValueError(f"vector stream absent: {streams}")
                details[provider] = {
                    "streams": sorted(streams),
                    "median_seconds": round(statistics.median(times), 4),
                    "bytes": sum(
                        f.stat().st_size for f in data.rglob("*") if f.is_file()
                    ),
                }
    scores = {}
    for split in ["original", "holdout"]:
        for mode in ["filtered", "property"]:
            cases = [r for r in rows if r["split"] == split and r["mode"] == mode]
            scores[split + "_" + mode] = {}
            for engine in ["lexical", "gbrain", "none", "local"]:
                if any(k not in pages for r in cases for k in r[engine]):
                    raise ValueError("unresolved citation")
                scores[split + "_" + mode][engine] = [
                    sum(r["expected_passage"] in r[engine] for r in cases),
                    sum(not r[engine] and r["expected_passage"] == "-" for r in cases),
                ]
    args.output.write_text(
        json.dumps(
            dict(
                commit=COMMIT,
                manifest=ev.stamp(pages),
                scores=scores,
                measurements=details,
                rows=rows,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(scores))


if __name__ == "__main__":
    main()
