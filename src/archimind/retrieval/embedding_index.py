"""Bounded, immutable derived vectors. Optional NumPy is loaded only explicitly."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import Field, StrictInt, model_validator

from archimind.retrieval.contracts import Digest, Frozen
from archimind.retrieval.eligibility import (
    RetrievalIndex,
    build_index,
    current_options,
    digest,
)

DIMENSION = 384
MAX_VECTOR_BYTES = 64 * DIMENSION * 4
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages:"


class EmbeddingError(ValueError):
    """Sanitized local-cache/index/capability failure."""


def numpy_module():
    try:
        import numpy

        return numpy
    except ImportError:
        raise EmbeddingError("Optional NumPy dependency is unavailable") from None


class ModelArtifact(Frozen):
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    sha256: Digest
    size_bytes: StrictInt = Field(gt=0, le=250 * 1024 * 1024)
    source_url: str | None = None


class EncoderSpec(Frozen):
    model_name: Literal["BAAI/bge-small-en-v1.5"]
    upstream_repository: Literal["BAAI/bge-small-en-v1.5"]
    upstream_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    artifact_repository: Literal["Qdrant/bge-small-en-v1.5-onnx-Q"]
    artifact_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    fastembed_version: str
    onnxruntime_version: str
    numpy_version: str
    tokenizers_version: str
    license_id: Literal["MIT"] = "MIT"
    execution_kind: Literal["real_cpu", "test_double"]
    artifacts: tuple[ModelArtifact, ...] = Field(min_length=1, max_length=12)
    dimension: StrictInt = Field(default=384, ge=384, le=384)
    providers: tuple[Literal["CPUExecutionProvider"], ...] = ("CPUExecutionProvider",)
    threads: StrictInt = Field(default=1, ge=1, le=1)
    batch_size: StrictInt = Field(default=1, ge=1, le=1)
    pooling: Literal["cls"] = "cls"
    document_instruction: Literal[""] = ""
    query_instruction: Literal[
        "Represent this sentence for searching relevant passages:"
    ] = QUERY_INSTRUCTION
    max_tokens: StrictInt = Field(default=512, ge=512, le=512)
    normalization: Literal["l2_float64_then_float32_v1"] = "l2_float64_then_float32_v1"

    @model_validator(mode="after")
    def bounded_model(self):
        names = [a.filename for a in self.artifacts]
        if names != sorted(set(names)) or self.providers != ("CPUExecutionProvider",):
            raise ValueError("Invalid model artifact/provider inventory")
        weights = sum(
            a.size_bytes for a in self.artifacts if a.filename.endswith(".onnx")
        )
        if (
            weights > 250 * 1024 * 1024
            or sum(a.size_bytes for a in self.artifacts) > 252 * 1024 * 1024
        ):
            raise ValueError("Model acquisition budget exceeded")
        if self.execution_kind == "real_cpu":
            required = {
                "model_optimized.onnx",
                "config.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
                "README.md",
            }
            if not required <= set(names):
                raise ValueError("Incomplete real model inventory")
            roots = (
                f"https://huggingface.co/{self.upstream_repository}/resolve/{self.upstream_revision}/",
                f"https://huggingface.co/{self.artifact_repository}/resolve/{self.artifact_revision}/",
            )
            if any(
                a.source_url is None or not a.source_url.startswith(roots)
                for a in self.artifacts
            ):
                raise ValueError("Unqualified model source")
        return self


class TextEncoder(Protocol):
    spec: EncoderSpec

    def encode_documents(self, texts: tuple[str, ...]): ...
    def encode_queries(self, texts: tuple[str, ...]): ...


def normalized_vectors(values, *, rows: int):
    np = numpy_module()
    matrix = np.asarray(values)
    if (
        matrix.shape != (rows, DIMENSION)
        or matrix.dtype.kind != "f"
        or not np.isfinite(matrix).all()
        or (np.abs(matrix) > np.finfo(np.float32).max).any()
    ):
        raise EmbeddingError("Invalid embedding shape or finite floating-point values")
    matrix = matrix.astype(np.float32).astype(np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms <= 0).any():
        raise EmbeddingError("Embedding has zero or invalid norm")
    return (matrix / norms).astype("<f4")


def document_texts(corpus: RetrievalIndex, *, historical=False) -> tuple[str, ...]:
    """Use exact existing reviewed text, preserving real-document line breaks."""
    if corpus.identity.scope == "real":
        from archimind.retrieval.historical import historical_index, historical_options

        index = historical_index() if historical else build_index()
        if index != corpus:
            raise EmbeddingError("Corpus is stale")
        options = {
            o.record.asset_id: o
            for o in (historical_options() if historical else current_options())
        }
        texts = tuple(
            options[d.reference.asset_id].record.search_document()
            for d in corpus.documents
        )
    else:
        texts = tuple(d.text for d in corpus.documents)
    if any(
        hashlib.sha256(t.encode()).hexdigest() != d.reference.search_document_digest
        for t, d in zip(texts, corpus.documents, strict=True)
    ):
        raise EmbeddingError("Search document digest mismatch")
    return texts


class EmbeddingManifest(Frozen):
    schema_version: StrictInt = Field(default=1, ge=1, le=1)
    encoder: EncoderSpec
    corpus: RetrievalIndex
    row_asset_ids: tuple[str, ...] = Field(min_length=1, max_length=64)
    dtype: Literal["float32_le"] = "float32_le"
    dimension: StrictInt = Field(default=384, ge=384, le=384)
    encoder_digest: Digest
    input_texts_digest: Digest
    vectors_sha256: Digest
    vector_bytes: StrictInt = Field(gt=0, le=MAX_VECTOR_BYTES)
    manifest_digest: Digest

    @model_validator(mode="after")
    def complete_binding(self):
        if (
            self.row_asset_ids
            != tuple(d.reference.asset_id for d in self.corpus.documents)
            or self.vector_bytes != len(self.row_asset_ids) * DIMENSION * 4
            or self.encoder_digest != digest(self.encoder)
        ):
            raise ValueError("Incomplete vector row/model binding")
        if self.manifest_digest != digest(
            self.model_dump(mode="json", exclude={"manifest_digest"})
        ):
            raise ValueError("Manifest checksum mismatch")
        return self


@dataclass(frozen=True)
class EmbeddingIndex:
    manifest: EmbeddingManifest
    vector_bytes: bytes

    def __post_init__(self):
        try:
            manifest = EmbeddingManifest.model_validate(self.manifest)
            if (
                type(self.vector_bytes) is not bytes
                or len(self.vector_bytes) != manifest.vector_bytes
                or hashlib.sha256(self.vector_bytes).hexdigest()
                != manifest.vectors_sha256
            ):
                raise ValueError
            np = numpy_module()
            matrix = self.vectors()
            norms = np.linalg.norm(matrix.astype(np.float64), axis=1)
            if not np.isfinite(matrix).all() or not np.allclose(
                norms, 1.0, rtol=0, atol=1e-6
            ):
                raise ValueError
        except (ValueError, TypeError):
            raise EmbeddingError("Corrupt or invalid embedding index") from None

    def vectors(self):
        # Immutable bytes back this view; callers cannot enable writable storage.
        return (
            numpy_module()
            .frombuffer(self.vector_bytes, dtype="<f4")
            .reshape((-1, DIMENSION))
        )


def build_embedding_index(
    corpus: RetrievalIndex, encoder: TextEncoder, *, historical=False
) -> EmbeddingIndex:
    corpus = RetrievalIndex.model_validate(corpus)
    spec = EncoderSpec.model_validate(encoder.spec)
    texts = document_texts(corpus, historical=historical)
    values = normalized_vectors(encoder.encode_documents(texts), rows=len(texts))
    raw = values.tobytes(order="C")
    fields = dict(
        schema_version=1,
        encoder=spec.model_dump(mode="json"),
        corpus=corpus.model_dump(mode="json"),
        row_asset_ids=[d.reference.asset_id for d in corpus.documents],
        dtype="float32_le",
        dimension=384,
        encoder_digest=digest(spec),
        input_texts_digest=digest(texts),
        vectors_sha256=hashlib.sha256(raw).hexdigest(),
        vector_bytes=len(raw),
    )
    manifest = EmbeddingManifest.model_validate_json(
        json.dumps(fields | {"manifest_digest": digest(fields)})
    )
    return EmbeddingIndex(manifest, raw)


def write_embedding_index(index: EmbeddingIndex, directory: Path) -> None:
    """Explicit immutable publication; existing directories are never overwritten."""
    EmbeddingIndex(index.manifest, index.vector_bytes)
    directory.mkdir(exist_ok=False)
    (directory / "vectors.f32").write_bytes(index.vector_bytes)
    (directory / "manifest.json").write_text(
        index.manifest.model_dump_json(indent=2) + "\n"
    )


def read_embedding_index(
    directory: Path, *, encoder: EncoderSpec, corpus: RetrievalIndex, historical=False
) -> EmbeddingIndex:
    try:
        if (
            directory.is_symlink()
            or {p.name for p in directory.iterdir()} != {"manifest.json", "vectors.f32"}
            or any(p.is_symlink() for p in directory.iterdir())
        ):
            raise ValueError
        with (directory / "manifest.json").open("rb") as f:
            body = f.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError
        manifest = EmbeddingManifest.model_validate_json(body)
        if (
            manifest.encoder != encoder
            or manifest.corpus != corpus
            or manifest.input_texts_digest
            != digest(document_texts(corpus, historical=historical))
        ):
            raise ValueError
        with (directory / "vectors.f32").open("rb") as f:
            raw = f.read(MAX_VECTOR_BYTES + 1)
        return EmbeddingIndex(manifest, raw)
    except (ValueError, TypeError, OSError):
        raise EmbeddingError(
            "Embedding snapshot is unavailable, corrupt or stale"
        ) from None
