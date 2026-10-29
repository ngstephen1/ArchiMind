"""Explicit one-model acquisition; never imported or called by runtime search."""

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

UPSTREAM = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
REVISION = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"
WEIGHT_SIZE = 66465124
WEIGHT_SHA = "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431"
BUDGET = 250 * 1024 * 1024
# Small-file Git blob identities from the official pinned Hugging Face tree.
FILES = {
    "README.md": (900, "7cb06d09a9326eb4f63654b255d4889895b90db9"),
    "config.json": (706, "0d7726d0cdccb62ee17c03bd1595cff07199b8f8"),
    "ort_config.json": (1272, "ca62fa095648efcf2709136afcd942d98744eb3f"),
    "special_tokens_map.json": (695, "9bbecc17cabbcbd3112c14d6982b51403b264bfa"),
    "tokenizer.json": (711396, "688882a79f44442ddc1f60d70334a7ff5df0fb47"),
    "tokenizer_config.json": (1242, "75305659f7795d4549f0e23688b52fa20a32f925"),
    "vocab.txt": (231508, "fb140275c155a9c7c5a3b3e0e77a9e839594a938"),
    "model_optimized.onnx": (WEIGHT_SIZE, None),
}


class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Non-HTTPS model redirect rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def acquire(destination: Path):
    if WEIGHT_SIZE > BUDGET:
        raise ValueError("Declared model weight exceeds budget")
    destination.mkdir(exist_ok=False)
    opener = urllib.request.build_opener(HTTPSOnly())
    entries = []
    start = time.perf_counter()
    total = 0
    plans = [
        (
            name,
            f"https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/{REVISION}/{name}",
            size,
            oid,
        )
        for name, (size, oid) in sorted(FILES.items())
    ]
    plans.extend(
        (
            name,
            f"https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/{UPSTREAM}/{source}",
            None,
            None,
        )
        for name, source in [
            ("upstream_README.md", "README.md"),
            ("upstream_config.json", "config.json"),
        ]
    )
    for name, url, size, oid in plans:
        cap = size if size is not None else 1024 * 1024
        request = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
        sha = hashlib.sha256()
        body = bytearray()
        actual = 0
        with (
            opener.open(request, timeout=60) as response,
            (destination / (name + ".part")).open("xb") as out,
        ):
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > cap:
                raise ValueError("Model response exceeds planned bound")
            host = urlsplit(response.url).hostname
            while chunk := response.read(1024 * 1024):
                actual += len(chunk)
                if actual > cap or (name.endswith(".onnx") and actual > BUDGET):
                    raise ValueError("Acquisition budget exceeded")
                sha.update(chunk)
                out.write(chunk)
                if oid:
                    body.extend(chunk)
        if size is not None and actual != size:
            raise ValueError("Model artifact size mismatch")
        if oid and hashlib.sha1(f"blob {actual}\0".encode() + body).hexdigest() != oid:
            raise ValueError("Source Git blob mismatch")
        if name.endswith(".onnx") and sha.hexdigest() != WEIGHT_SHA:
            raise ValueError("Model weight SHA-256 mismatch")
        (destination / (name + ".part")).rename(destination / name)
        (destination / name).chmod(0o444)
        entries.append(
            dict(
                filename=name,
                sha256=sha.hexdigest(),
                size_bytes=actual,
                source_url=url,
                redirect_host=host,
                declared_content_length=declared,
            )
        )
        total += actual
    destination.chmod(0o555)
    return dict(
        model_name="BAAI/bge-small-en-v1.5",
        upstream_revision=UPSTREAM,
        artifact_repository="Qdrant/bge-small-en-v1.5-onnx-Q",
        artifact_revision=REVISION,
        license_id="MIT",
        weight_download_budget_bytes=BUDGET,
        actual_weight_bytes=WEIGHT_SIZE,
        actual_all_artifact_bytes=total,
        elapsed_seconds=time.perf_counter() - start,
        artifacts=entries,
        notice="One official FastEmbed quantized ONNX representation. Original upstream float weights were not acquired. No source equivalence or independent license adjudication claim.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise ValueError("Receipt already exists")
    receipt = acquire(args.destination)
    with args.receipt.open("x") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    print(
        "Acquired one pinned encoder:",
        receipt["actual_all_artifact_bytes"],
        "bytes; weights",
        receipt["actual_weight_bytes"],
        "bytes",
    )


if __name__ == "__main__":
    main()
