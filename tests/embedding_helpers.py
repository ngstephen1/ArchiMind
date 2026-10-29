"""Explicit fixed-vector encoder; never a real-model or source-qualification claim."""

import numpy as np

from archimind.retrieval.embedding_index import EncoderSpec, ModelArtifact


def spec():
    return EncoderSpec(
        model_name="BAAI/bge-small-en-v1.5",
        upstream_repository="BAAI/bge-small-en-v1.5",
        upstream_revision="0" * 40,
        artifact_repository="Qdrant/bge-small-en-v1.5-onnx-Q",
        artifact_revision="0" * 40,
        fastembed_version="0.9.1",
        onnxruntime_version="1.24.2",
        numpy_version=np.__version__,
        tokenizers_version="test",
        execution_kind="test_double",
        artifacts=(
            ModelArtifact(
                filename="model_optimized.onnx", sha256="0" * 64, size_bytes=1
            ),
        ),
    )


class FixedEncoder:
    def __init__(self, documents=None, query=None):
        self.spec = spec()
        self.documents = documents
        self.query = query
        self.document_inputs = []
        self.query_inputs = []

    def encode_documents(self, texts):
        self.document_inputs.append(texts)
        return (
            self.documents
            if self.documents is not None
            else np.eye(384, dtype=np.float32)[: len(texts)]
        )

    def encode_queries(self, texts):
        self.query_inputs.append(texts)
        return np.asarray(
            [self.query if self.query is not None else np.eye(384, dtype=np.float32)[0]]
        )
