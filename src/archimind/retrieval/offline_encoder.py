"""One pinned local CPU encoder; no model discovery or automatic acquisition."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

from archimind.retrieval.embedding_index import (
    EmbeddingError,
    EncoderSpec,
    numpy_module,
)

_PIN = {
    "model_name": "BAAI/bge-small-en-v1.5",
    "upstream_repository": "BAAI/bge-small-en-v1.5",
    "upstream_revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
    "artifact_repository": "Qdrant/bge-small-en-v1.5-onnx-Q",
    "artifact_revision": "aa8f8b060edb00e03bfdd08813a2949946c8ba55",
    "fastembed_version": "0.9.1",
    "onnxruntime_version": "1.24.2",
    "numpy_version": "2.4.6",
    "tokenizers_version": "0.23.3",
    "execution_kind": "real_cpu",
    "artifacts": [
        {
            "filename": "README.md",
            "sha256": "01e220eed6921254f7e086bb3506d1c03f019f5f747bb9ac2f6ec5ce541edc12",
            "size_bytes": 900,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/README.md",
        },
        {
            "filename": "config.json",
            "sha256": "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd",
            "size_bytes": 706,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/config.json",
        },
        {
            "filename": "model_optimized.onnx",
            "sha256": "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431",
            "size_bytes": 66465124,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/model_optimized.onnx",
        },
        {
            "filename": "ort_config.json",
            "sha256": "99881c45e073696289224931dd48694398bc6bcd1fe7cb7018bca1e0cc00e1fc",
            "size_bytes": 1272,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/ort_config.json",
        },
        {
            "filename": "special_tokens_map.json",
            "sha256": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",
            "size_bytes": 695,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/special_tokens_map.json",
        },
        {
            "filename": "tokenizer.json",
            "sha256": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
            "size_bytes": 711396,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/tokenizer.json",
        },
        {
            "filename": "tokenizer_config.json",
            "sha256": "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53",
            "size_bytes": 1242,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/tokenizer_config.json",
        },
        {
            "filename": "vocab.txt",
            "sha256": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
            "size_bytes": 231508,
            "source_url": "https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/aa8f8b060edb00e03bfdd08813a2949946c8ba55/vocab.txt",
        },
        {
            "filename": "upstream_README.md",
            "sha256": "ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837",
            "size_bytes": 94783,
            "source_url": "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/README.md",
        },
        {
            "filename": "upstream_config.json",
            "sha256": "094f8e891b932f2000c92cfc663bac4c62069f5d8af5b5278c4306aef3084750",
            "size_bytes": 743,
            "source_url": "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/config.json",
        },
    ],
}


def pinned_encoder_spec() -> EncoderSpec:
    return EncoderSpec.model_validate_json(
        json.dumps(
            _PIN | {"artifacts": sorted(_PIN["artifacts"], key=lambda a: a["filename"])}
        )
    )


def verify_model_directory(directory: Path, spec: EncoderSpec) -> None:
    try:
        if directory.is_symlink() or {p.name for p in directory.iterdir()} != {
            a.filename for a in spec.artifacts
        }:
            raise ValueError
        for artifact in spec.artifacts:
            path = directory / artifact.filename
            if path.is_symlink() or path.stat().st_size != artifact.size_bytes:
                raise ValueError
            checksum = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    checksum.update(chunk)
            if checksum.hexdigest() != artifact.sha256:
                raise ValueError
    except (ValueError, OSError):
        raise EmbeddingError("Pinned local model cache is missing or invalid") from None


class FastEmbedCPUEncoder:
    def __init__(self, directory: Path):
        self.spec = pinned_encoder_spec()
        verify_model_directory(directory, self.spec)
        expected = {
            "fastembed": self.spec.fastembed_version,
            "onnxruntime": self.spec.onnxruntime_version,
            "numpy": self.spec.numpy_version,
            "tokenizers": self.spec.tokenizers_version,
        }
        try:
            if any(
                importlib.metadata.version(name) != version
                for name, version in expected.items()
            ):
                raise ValueError
        except (ValueError, importlib.metadata.PackageNotFoundError):
            raise EmbeddingError(
                "Pinned optional encoder dependencies are unavailable"
            ) from None
        for key in (
            "HF_HUB_OFFLINE",
            "HF_HUB_DISABLE_TELEMETRY",
            "TRANSFORMERS_OFFLINE",
            "DO_NOT_TRACK",
        ):
            os.environ[key] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        try:
            import onnxruntime
            from fastembed import TextEmbedding

            onnxruntime.disable_telemetry_events()
            self.model = TextEmbedding(
                model_name=self.spec.model_name,
                cache_dir=str(directory.parent / "fastembed-runtime-cache"),
                specific_model_path=str(directory),
                local_files_only=True,
                providers=["CPUExecutionProvider"],
                threads=1,
                lazy_load=False,
            )
            if (
                self.model.embedding_size != 384
                or self.model.model.model.get_providers() != ["CPUExecutionProvider"]
            ):
                raise ValueError
        except (ImportError, ValueError, RuntimeError, OSError):
            raise EmbeddingError(
                "Pinned local CPU encoder could not initialize"
            ) from None

    def _encode(self, texts):
        try:
            return numpy_module().stack(
                list(self.model.embed(list(texts), batch_size=1, parallel=None))
            )
        except AssertionError:
            raise
        except Exception:
            raise EmbeddingError("Local encoder execution failed") from None

    def encode_documents(self, texts):
        return self._encode(texts)

    def encode_queries(self, texts):
        return self._encode(tuple(self.spec.query_instruction + " " + t for t in texts))
