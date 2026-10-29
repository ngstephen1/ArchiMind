"""Optional SDK/cache failures tested with inert doubles; no real model imports."""

import hashlib
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from embedding_helpers import spec
from retrieval_helpers import offline  # noqa: F401

from archimind.retrieval import offline_encoder as module
from archimind.retrieval.embedding_index import EmbeddingError


def test_pinned_manifest_matches_acquired_small_receipt():
    import json
    from pathlib import Path

    receipt = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/data/ENCODER_ACQUISITION_08R1.json"
        ).read_text()
    )
    pin = module.pinned_encoder_spec()
    assert pin.execution_kind == "real_cpu" and pin.dimension == 384
    assert (
        sum(a.size_bytes for a in pin.artifacts if a.filename.endswith(".onnx"))
        == receipt["actual_weight_bytes"]
        < 250 * 1024 * 1024
    )
    assert {a.filename: a.sha256 for a in pin.artifacts} == {
        a["filename"]: a["sha256"] for a in receipt["artifacts"]
    }


def test_local_inventory_hash_and_missing_cache(tmp_path):
    path = tmp_path / "model_optimized.onnx"
    path.write_bytes(b"x")
    pin = spec()
    artifact = pin.artifacts[0].model_copy(
        update={"sha256": hashlib.sha256(b"x").hexdigest()}
    )
    pin = pin.model_copy(update={"artifacts": (artifact,)})
    module.verify_model_directory(tmp_path, pin)
    path.write_bytes(b"y")
    with pytest.raises(EmbeddingError, match="missing or invalid"):
        module.verify_model_directory(tmp_path, pin)
    path.unlink()
    path.symlink_to(tmp_path / "absent")
    with pytest.raises(EmbeddingError):
        module.verify_model_directory(tmp_path, pin)
    with pytest.raises(EmbeddingError):
        module.verify_model_directory(tmp_path / "missing", pin)


def setup_sdk(monkeypatch):
    pin = spec()
    monkeypatch.setattr(module, "pinned_encoder_spec", lambda: pin)
    monkeypatch.setattr(module, "verify_model_directory", Mock())
    versions = {
        "fastembed": pin.fastembed_version,
        "onnxruntime": pin.onnxruntime_version,
        "numpy": pin.numpy_version,
        "tokenizers": pin.tokenizers_version,
    }
    monkeypatch.setattr(module.importlib.metadata, "version", versions.__getitem__)
    model = SimpleNamespace(
        embedding_size=384,
        model=SimpleNamespace(
            model=SimpleNamespace(get_providers=lambda: ["CPUExecutionProvider"])
        ),
        embed=Mock(return_value=[np.eye(384, dtype=np.float32)[0]]),
    )
    factory = Mock(return_value=model)
    monkeypatch.setitem(
        sys.modules, "fastembed", SimpleNamespace(TextEmbedding=factory)
    )
    monkeypatch.setitem(
        sys.modules, "onnxruntime", SimpleNamespace(disable_telemetry_events=Mock())
    )
    return factory, model


def test_sdk_is_local_cpu_only_and_instructions_are_asymmetric(monkeypatch, tmp_path):
    factory, model = setup_sdk(monkeypatch)
    encoder = module.FastEmbedCPUEncoder(tmp_path)
    assert factory.call_args.kwargs["local_files_only"] is True
    assert factory.call_args.kwargs["specific_model_path"] == str(tmp_path)
    assert factory.call_args.kwargs["providers"] == ["CPUExecutionProvider"]
    assert factory.call_args.kwargs["threads"] == 1
    encoder.encode_documents(("Exact\nOriginal",))
    assert model.embed.call_args.args[0] == ["Exact\nOriginal"]
    encoder.encode_queries(("a seat",))
    assert model.embed.call_args.args[0] == [encoder.spec.query_instruction + " a seat"]


def test_dependency_errors_and_sdk_errors_are_sanitized(monkeypatch, tmp_path):
    setup_sdk(monkeypatch)
    monkeypatch.setattr(module.importlib.metadata, "version", lambda _: "wrong")
    with pytest.raises(EmbeddingError, match="dependencies are unavailable"):
        module.FastEmbedCPUEncoder(tmp_path)
    factory, _ = setup_sdk(monkeypatch)
    factory.side_effect = RuntimeError("sk-private-secret")
    with pytest.raises(EmbeddingError) as error:
        module.FastEmbedCPUEncoder(tmp_path)
    assert "secret" not in str(error.value)


def test_inference_exception_sanitized(monkeypatch, tmp_path):
    _, model = setup_sdk(monkeypatch)
    encoder = module.FastEmbedCPUEncoder(tmp_path)
    model.embed.side_effect = ValueError("private-path")
    with pytest.raises(EmbeddingError, match="Local encoder execution failed"):
        encoder.encode_queries(("seat",))
