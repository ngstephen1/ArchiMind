"""Immutable 384-D snapshots and pinned source/model bindings, using fixed vectors."""

import json
from pathlib import Path

import numpy as np
import pytest
from embedding_helpers import FixedEncoder
from retrieval_helpers import offline  # noqa: F401

from archimind.retrieval.eligibility import build_index
from archimind.retrieval.embedding_index import (
    EmbeddingError,
    EmbeddingIndex,
    EmbeddingManifest,
    build_embedding_index,
    document_texts,
    normalized_vectors,
    read_embedding_index,
    write_embedding_index,
)


@pytest.mark.parametrize(
    "values",
    [
        np.zeros((2, 384)),
        np.ones((2, 383)),
        np.ones((3, 384)),
        np.full((2, 384), np.nan),
        np.full((2, 384), np.inf),
        np.ones((2, 384), dtype=int),
        np.full((2, 384), 1e300),
    ],
)
def test_invalid_embedding_vectors(values):
    with pytest.raises(EmbeddingError):
        normalized_vectors(values, rows=2)


def test_normalization_exact_documents_and_immutable_rows(tmp_path):
    corpus = build_index()
    encoder = FixedEncoder(np.ones((2, 384), dtype=np.float32) * 3)
    index = build_embedding_index(corpus, encoder)
    assert encoder.document_inputs == [document_texts(corpus)]
    assert "\n" in encoder.document_inputs[0][0]
    assert index.manifest.row_asset_ids == tuple(
        d.reference.asset_id for d in corpus.documents
    )
    assert index.vectors().dtype == np.dtype("<f4")
    assert np.allclose(np.linalg.norm(index.vectors(), axis=1), 1, rtol=0, atol=1e-6)
    with pytest.raises(ValueError):
        index.vectors().setflags(write=True)
    with pytest.raises(ValueError):
        index.vectors()[0, 0] = 10
    path = tmp_path / "index"
    write_embedding_index(index, path)
    assert read_embedding_index(path, encoder=encoder.spec, corpus=corpus) == index
    with pytest.raises(FileExistsError):
        write_embedding_index(index, path)


@pytest.mark.parametrize(
    "change",
    [
        "truncated",
        "corrupt",
        "extra_file",
        "symlink",
        "manifest",
        "model",
        "deleted_row",
        "text_digest",
    ],
)
def test_bad_or_stale_snapshots_are_rejected(tmp_path, change):
    corpus = build_index()
    encoder = FixedEncoder()
    index = build_embedding_index(corpus, encoder)
    path = tmp_path / "index"
    write_embedding_index(index, path)
    expected_spec = encoder.spec
    expected_corpus = corpus
    if change == "truncated":
        (path / "vectors.f32").write_bytes(index.vector_bytes[:-4])
    elif change == "corrupt":
        (path / "vectors.f32").write_bytes(bytes(len(index.vector_bytes)))
    elif change == "extra_file":
        (path / "unlisted").write_text("unexpected")
    elif change == "symlink":
        (path / "vectors.f32").unlink()
        (path / "vectors.f32").symlink_to(tmp_path / "elsewhere")
    elif change == "manifest":
        (path / "manifest.json").write_text("{broken")
    elif change == "model":
        expected_spec = encoder.spec.model_copy(update={"fastembed_version": "0.0.0"})
    elif change == "deleted_row":
        expected_corpus = corpus.model_copy(update={"documents": corpus.documents[:1]})
    else:
        expected_corpus = corpus.model_copy(
            update={
                "documents": (
                    corpus.documents[0].model_copy(update={"text": "changed"}),
                    corpus.documents[1],
                )
            }
        )
    with pytest.raises(EmbeddingError):
        read_embedding_index(path, encoder=expected_spec, corpus=expected_corpus)


def test_manifest_ids_digests_and_json_are_strict():
    index = build_embedding_index(build_index(), FixedEncoder())
    raw = index.manifest.model_dump(mode="json")
    for key, value in [
        ("row_asset_ids", [raw["row_asset_ids"][0]] * 2),
        ("dimension", 383),
        ("vectors_sha256", "a" * 64),
        ("manifest_digest", "0" * 64),
    ]:
        with pytest.raises(ValueError):
            EmbeddingManifest.model_validate_json(json.dumps(raw | {key: value}))
    with pytest.raises(EmbeddingError):
        EmbeddingIndex(index.manifest, index.vector_bytes + b"bad")


def test_new_judgments_are_frozen_and_original_cases_unchanged():
    import hashlib

    root = Path(__file__).resolve().parents[1] / "data" / "benchmarks"
    expected = {
        "development": "1800c1932ba13373de8e62a189a53393e71c97699a19fef288047180528fac29",
        "held_out": "e219d29f10de791627acfc573bb2108d8074f937d105b72b2a9e534f85ecd088",
    }
    from archimind.retrieval.evaluation import BenchmarkCase

    for partition, sha in expected.items():
        raw = (root / f"furniture_embedding_{partition}_08r1.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sha
        data = json.loads(raw)
        assert data["partition"] == partition
        for c in data["cases"]:
            BenchmarkCase.model_validate_json(json.dumps(c))
        assert data["authorship"] == "implementation_agent_no_independent_human_review"
