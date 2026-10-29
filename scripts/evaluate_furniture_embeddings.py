"""Separately invoked local CPU experiment; calibration precedes sealed evaluation."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

from archimind.retrieval.eligibility import build_index, current_options, digest
from archimind.retrieval.embedding_experiment import (
    SPLIT_HASHES,
    FixtureSemanticProvider,
    add_error_rates,
    benchmark_inputs,
    choose_policy,
    timing_summary,
)
from archimind.retrieval.embedding_index import (
    build_embedding_index,
    read_embedding_index,
    write_embedding_index,
)
from archimind.retrieval.evaluation import SyntheticRetrievalProvider, evaluate_provider
from archimind.retrieval.lexical import LexicalRetrievalProvider, fts5_available
from archimind.retrieval.offline_encoder import FastEmbedCPUEncoder
from archimind.retrieval.semantic import AbstentionPolicy, SemanticRetrievalProvider


def offline_bootstrap():
    for key in (
        "HF_HUB_OFFLINE",
        "HF_HUB_DISABLE_TELEMETRY",
        "TRANSFORMERS_OFFLINE",
        "DO_NOT_TRACK",
    ):
        os.environ[key] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    start = time.perf_counter()
    # Dependency bootstrap is separately timed; the local-only model constructor
    # and every inference below run after the process-level Python tripwire.
    import fastembed  # noqa: F401
    import onnxruntime

    onnxruntime.disable_telemetry_events()
    bootstrap_seconds = time.perf_counter() - start
    attempts = []

    def guard(event, args):
        if event.startswith("socket.") or event in (
            "subprocess.Popen",
            "os.system",
            "os.posix_spawn",
            "os.fork",
            "os.exec",
        ):
            attempts.append(event)
            raise RuntimeError("Offline benchmark operation denied")

    sys.addaudithook(guard)
    return dict(
        dependency_bootstrap_seconds=bootstrap_seconds,
        denied_operations=attempts,
        scope="model_constructor_index_build_and_all_inference_after_dependency_bootstrap",
        limitation="Python audited operations; not an arbitrary native-code OS sandbox",
    )


def publish(path, body):
    with path.open("x") as stream:
        json.dump(body, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("calibrate", "evaluate"))
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--index-directory", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or (
        args.phase == "calibrate"
        and (args.index_directory.exists() or args.policy.exists())
    ):
        parser.error("Outputs must be new; existing artifacts are never overwritten")
    if args.phase == "evaluate" and not args.policy_sha256:
        parser.error("Evaluation requires the externally sealed policy SHA-256")
    root = Path(__file__).resolve().parents[1] / "data" / "benchmarks"
    synthetic, splits = benchmark_inputs(root)
    corpora = {"real": build_index(), "synthetic_fixture": synthetic.index()}
    guard = offline_bootstrap()
    start = time.perf_counter()
    encoder = FastEmbedCPUEncoder(args.model_directory)
    initial_seconds = time.perf_counter() - start
    start = time.perf_counter()
    second = FastEmbedCPUEncoder(args.model_directory)
    warm_seconds = time.perf_counter() - start
    del second
    indexes, builds = {}, {}
    if args.phase == "calibrate":
        args.index_directory.mkdir(exist_ok=False)
        for scope, corpus in corpora.items():
            start = time.perf_counter()
            indexes[scope] = build_embedding_index(corpus, encoder)
            builds[scope] = time.perf_counter() - start
            write_embedding_index(indexes[scope], args.index_directory / scope)
    else:
        for scope, corpus in corpora.items():
            indexes[scope] = read_embedding_index(
                args.index_directory / scope, encoder=encoder.spec, corpus=corpus
            )

    def semantic(scope, policy):
        return (
            SemanticRetrievalProvider(
                index=indexes[scope], encoder=encoder, policy=policy
            )
            if scope == "real"
            else FixtureSemanticProvider(synthetic, indexes[scope], encoder, policy)
        )

    raw_policy = AbstentionPolicy(
        mode="threshold", minimum_cosine=-1.0, method="raw_reference"
    )
    if args.phase == "calibrate":
        policies, grids = {}, {}
        for scope in corpora:
            cases = tuple(c for c in splits["development"] if c.scope == scope)
            raw = semantic(scope, raw_policy)
            outputs = [raw.search(c.request) for c in cases]
            policy, grid = choose_policy(cases, outputs, SPLIT_HASHES["development"])
            policies[scope], grids[scope] = policy.model_dump(mode="json"), grid
        sealed = dict(
            schema_version=1,
            method="zero_dev_fp_max_recall_highest_threshold_v1",
            development_sha256=SPLIT_HASHES["development"],
            held_out_sha256=SPLIT_HASHES["held_out"],
            encoder_digest=digest(encoder.spec),
            index_manifest_digests={
                s: i.manifest.manifest_digest for s, i in indexes.items()
            },
            policies=policies,
            grids=grids,
            authorship="implementation_agent_no_independent_human_review",
            evaluation_has_not_run=True,
        )
        publish(args.policy, sealed)
        args.policy.chmod(0o444)
        policy_checksum = hashlib.sha256(args.policy.read_bytes()).hexdigest()
        partitions = ("development",)
    else:
        body = args.policy.read_bytes()
        if (
            len(body) > 1024 * 1024
            or hashlib.sha256(body).hexdigest() != args.policy_sha256
        ):
            raise ValueError("Sealed policy hash mismatch")
        sealed = json.loads(body)
        if (
            sealed["encoder_digest"] != digest(encoder.spec)
            or sealed["index_manifest_digests"]
            != {s: i.manifest.manifest_digest for s, i in indexes.items()}
            or sealed["development_sha256"] != SPLIT_HASHES["development"]
            or sealed["held_out_sha256"] != SPLIT_HASHES["held_out"]
        ):
            raise ValueError("Sealed policy context mismatch")
        policy_checksum = args.policy_sha256
        partitions = ("original", "held_out")
    reports = {}
    for partition in partitions:
        for scope, corpus in corpora.items():
            cases = tuple(c for c in splits[partition] if c.scope == scope)
            policy = AbstentionPolicy.model_validate_json(
                json.dumps(sealed["policies"][scope])
            )
            lexical = (
                LexicalRetrievalProvider(index=corpus)
                if scope == "real"
                else SyntheticRetrievalProvider(synthetic)
            )
            providers = {
                "python_bm25_v1": lexical,
                "cosine_raw_reference": semantic(scope, raw_policy),
                "cosine_frozen": semantic(scope, policy),
            }
            if fts5_available():
                providers["sqlite_fts5_bm25_v1"] = (
                    LexicalRetrievalProvider(
                        index=corpus, algorithm="sqlite_fts5_bm25_v1"
                    )
                    if scope == "real"
                    else SyntheticRetrievalProvider(
                        synthetic, algorithm="sqlite_fts5_bm25_v1"
                    )
                )
            refs = {d.reference.asset_id: d.reference for d in corpus.documents}
            cats = (
                {o.record.asset_id: o.record.category for o in current_options()}
                if scope == "real"
                else {p.asset_id: p.category for p in synthetic.products}
            )
            for method, provider in providers.items():
                report = evaluate_provider(
                    provider,
                    cases,
                    identity=corpus.identity,
                    references=refs,
                    categories=cats,
                    repeats=3,
                )
                add_error_rates(report, cases)
                if hasattr(provider, "timings"):
                    report["stages_ms"] = timing_summary(provider.timings)
                reports[f"{partition}/{scope}/{method}"] = report
    if guard["denied_operations"]:
        raise RuntimeError("Offline operation attempted; evidence not accepted")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary = dict(
        schema_version=1,
        phase=args.phase,
        policy_sha256=policy_checksum,
        policy=sealed,
        encoder=encoder.spec.model_dump(mode="json"),
        manifests={s: i.manifest.model_dump(mode="json") for s, i in indexes.items()},
        environment=dict(
            python=platform.python_version(),
            platform=" ".join(
                (platform.system(), platform.release(), platform.machine())
            ),
            machine=platform.machine(),
            dependencies={
                d.metadata["Name"]: d.version
                for d in importlib.metadata.distributions()
            },
            provider=["CPUExecutionProvider"],
            threads=1,
        ),
        resources=dict(
            dependency_bootstrap_seconds=guard["dependency_bootstrap_seconds"],
            first_encoder_initialization_seconds=initial_seconds,
            warm_encoder_initialization_seconds=warm_seconds,
            initialization_definition="Fresh process first instance versus second instance; no OS cache eviction; both include hash verification",
            index_build_seconds=builds,
            process_peak_rss_bytes=peak if sys.platform == "darwin" else peak * 1024,
            model_cache_bytes=sum(
                p.stat().st_size for p in args.model_directory.iterdir()
            ),
            vector_bytes={s: len(i.vector_bytes) for s, i in indexes.items()},
            index_disk_bytes={
                s: sum(p.stat().st_size for p in (args.index_directory / s).iterdir())
                for s in indexes
            },
        ),
        guard=guard,
        reports=reports,
    )
    summary["semantic_signature"] = digest(
        {
            key: [
                {k: v for k, v in q.items() if k != "latency_ms"}
                for q in report["queries"]
            ]
            for key, report in reports.items()
        }
    )
    publish(args.output, summary)
    print(
        json.dumps(
            dict(
                output=str(args.output),
                policy_sha256=policy_checksum,
                semantic_signature=summary["semantic_signature"],
                denied_operations=guard["denied_operations"],
            )
        )
    )


if __name__ == "__main__":
    main()
