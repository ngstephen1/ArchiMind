import json

import pytest
from pydantic import ValidationError

from archimind.datasets.contracts import (
    CheckResult,
    ReferenceAsset,
    SceneReference,
    SourceFile,
    check_relative_path,
    namespaced,
)
from archimind.datasets.fixtures import (
    permission,
    source_manifest,
    synthetic_asset,
    synthetic_glb_bytes,
    synthetic_scenes,
)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/abs",
        "../up",
        "a/../b",
        "a\\b",
        "C:/x",
        "a//b",
        "./a",
        "CON",
        "nul.txt",
        "Lpt1.obj",
        "dir./x",
        "trailing ",
        "a:stream",
        "q?.txt",
        "x" * 241,
    ],
)
def test_unportable_or_escaping_paths_are_rejected(path):
    with pytest.raises(ValueError):
        check_relative_path(path)


@pytest.mark.parametrize("path", ["a.json", "models/abc-123/raw_model.obj", "con_x"])
def test_portable_paths_are_accepted(path):
    assert check_relative_path(path) == path


def test_namespacing_keeps_sources_apart():
    assert namespaced("ssr_3dfront", "h", "r") == "ssr:h:r"
    assert namespaced("midi_3dfront", "h", "r") == "midi:h:r"
    assert namespaced("future_3d", "j") == "future:j"


def test_reference_id_must_match_namespaced_identity():
    data = synthetic_scenes()[0].model_dump_json()
    with pytest.raises(ValidationError):
        SceneReference.model_validate_json(
            data.replace('"ssr:synthetic-house-1', '"midi:synthetic-house-1')
        )


def test_canonical_tier_rejects_rotated_objects():
    rotated = synthetic_scenes()[1]
    assert rotated.tier == "reference_only"
    with pytest.raises(ValidationError):
        SceneReference.model_validate_json(
            rotated.model_dump_json().replace('"reference_only"', '"canonical"')
        )


def test_unknown_openings_cannot_claim_door_checks():
    scene = synthetic_scenes()[0]
    passing = scene.model_dump_json().replace(
        '"door_clearance","status":"NOT_VERIFIABLE"',
        '"door_clearance","status":"PASS"',
    )
    with pytest.raises(ValidationError):
        SceneReference.model_validate_json(passing)


def test_duplicate_objects_and_checks_are_rejected():
    scene = synthetic_scenes()[0]
    with pytest.raises(ValidationError):
        SceneReference.model_validate_json(
            scene.model_dump_json().replace('"nightstand-1"', '"bed-1"')
        )
    data = scene.model_dump(mode="json")
    data["checks"].append(CheckResult(name="collision", status="FAIL").model_dump())
    with pytest.raises(ValidationError):
        SceneReference.model_validate_json(json.dumps(data))


def test_records_are_frozen_and_strict():
    scene = synthetic_scenes()[0]
    with pytest.raises(ValidationError):
        scene.split = "test"
    with pytest.raises(ValidationError):
        SourceFile(path="a", size_bytes="3", sha256="0" * 64)


def test_reference_asset_identity_and_budgets():
    asset = synthetic_asset(synthetic_glb_bytes())
    data = asset.model_dump_json()
    with pytest.raises(ValidationError):
        ReferenceAsset.model_validate_json(
            data.replace('"triangles":12', '"triangles":100001')
        )
    with pytest.raises(ValidationError):
        ReferenceAsset.model_validate_json(
            data.replace('"max_texture_px":0', '"max_texture_px":4096')
        )
    with pytest.raises(ValidationError):
        ReferenceAsset.model_validate_json(
            data.replace('"asset_id":"future:synthetic-jid-1"', '"asset_id":"abo:x"')
        )
    with pytest.raises(ValidationError):
        ReferenceAsset.model_validate_json(
            data.replace("assets/synthetic-jid-1.glb", "other/synthetic-jid-1.glb")
        )


def test_permission_unknown_is_not_allowed():
    assert permission("allowed").allows("local_research", "derived_metadata")
    assert not permission("unknown").allows("local_research")
    assert not permission("allowed").allows("provider_disclosure")


def test_source_files_must_be_unique_case_insensitively():
    manifest = source_manifest("ssr_3dfront")
    entry = manifest.files[0].model_dump()
    upper = dict(entry, path="SYNTHETIC.json")
    with pytest.raises(ValidationError):
        type(manifest).model_validate_json(
            manifest.model_copy()
            .model_dump_json()
            .replace(
                '"files":[', '"files":[' + SourceFile(**upper).model_dump_json() + ","
            )
        )
