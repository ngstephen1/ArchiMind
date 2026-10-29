"""Acquisition boundary tests with in-memory responses; no downloads or real model."""

import importlib.util
import io
from pathlib import Path
from unittest.mock import Mock

import pytest
from retrieval_helpers import offline  # noqa: F401


def script():
    spec = importlib.util.spec_from_file_location(
        "acquire_encoder",
        Path(__file__).resolve().parents[1] / "scripts/acquire_furniture_encoder.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declared_weight_budget_stops_before_acquisition(tmp_path, monkeypatch):
    module = script()
    monkeypatch.setattr(module, "WEIGHT_SIZE", module.BUDGET + 1)
    with pytest.raises(ValueError, match="exceeds budget"):
        module.acquire(tmp_path / "new")
    assert not (tmp_path / "new").exists()


def test_existing_cache_is_never_overwritten(tmp_path):
    with pytest.raises(FileExistsError):
        script().acquire(tmp_path)


def test_https_redirect_cannot_downgrade():
    with pytest.raises(ValueError, match="Non-HTTPS"):
        script().HTTPSOnly().redirect_request(
            None, None, 302, "", {}, "http://example.invalid/model"
        )


@pytest.mark.parametrize(
    "body,declared,error",
    [
        (b"x", "2", "planned bound"),
        (b"xx", None, "budget exceeded"),
        (b"x", "1", "SHA-256 mismatch"),
    ],
)
def test_bad_download_responses_cannot_publish_model(
    tmp_path, monkeypatch, body, declared, error
):
    module = script()
    monkeypatch.setattr(module, "FILES", {"model_optimized.onnx": (1, None)})
    response = io.BytesIO(body)
    response.headers = {"Content-Length": declared} if declared else {}
    response.url = "https://huggingface.co/fixed"
    monkeypatch.setattr(
        module.urllib.request,
        "build_opener",
        Mock(return_value=Mock(open=Mock(return_value=response))),
    )
    destination = tmp_path / "new"
    with pytest.raises(ValueError, match=error):
        module.acquire(destination)
    assert not (destination / "model_optimized.onnx").exists()
