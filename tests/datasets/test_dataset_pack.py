import random

import pytest

from archimind.datasets.fixtures import (
    FIXTURE_VERSION,
    SYNTHETIC_TIME,
    build_synthetic_pack,
    source_manifest,
    synthetic_asset,
    synthetic_exclusions,
    synthetic_glb_bytes,
    synthetic_scenes,
)
from archimind.datasets.pack import PackError, build_pack, load_pack, verify_pack


def _build(
    root,
    *,
    scenes=None,
    sources=None,
    audience="local",
    glb_dir=None,
    assets=True,
    created=SYNTHETIC_TIME,
):
    glb = synthetic_glb_bytes()
    glb_dir = glb_dir or root.parent / f"{root.name}-glb"
    glb_dir.mkdir(parents=True, exist_ok=True)
    (glb_dir / "a.glb").write_bytes(glb)
    return build_pack(
        root,
        pack_id="test-pack",
        audience=audience,
        sources=sources
        or [source_manifest("ssr_3dfront"), source_manifest("future_3d")],
        scenes=synthetic_scenes() if scenes is None else scenes,
        exclusions=synthetic_exclusions(),
        assets=[synthetic_asset(glb)] if assets else [],
        glb_files={"assets/synthetic-jid-1.glb": glb_dir / "a.glb"} if assets else {},
        transform_version=FIXTURE_VERSION,
        category_map_version=FIXTURE_VERSION,
        builder="test",
        created_utc=created,
    )


def test_snapshot_is_independent_of_input_order_and_build_time(tmp_path):
    scenes = synthetic_scenes()
    shuffled = scenes[:]
    random.Random(7).shuffle(shuffled)
    shuffled.reverse()
    a = _build(tmp_path / "a", scenes=scenes)
    b = _build(tmp_path / "b", scenes=shuffled, created="2027-05-05T05:05:05Z")
    assert a.snapshot_id == b.snapshot_id
    assert (tmp_path / "a/scenes.jsonl").read_bytes() == (
        tmp_path / "b/scenes.jsonl"
    ).read_bytes()


def test_verified_pack_round_trips(tmp_path):
    manifest = build_synthetic_pack(tmp_path / "p")
    pack = verify_pack(tmp_path / "p")
    assert pack.manifest == manifest
    assert [s.reference_id for s in pack.scenes] == sorted(
        s.reference_id for s in synthetic_scenes()
    )
    assert len(pack.assets) == 1 and len(pack.exclusions) == 1


def test_identical_duplicates_collapse_and_conflicts_fail(tmp_path):
    scenes = synthetic_scenes()
    manifest = _build(tmp_path / "dup", scenes=[*scenes, scenes[0]])
    assert next(f for f in manifest.files if f.path == "scenes.jsonl").records == 2
    conflicting = scenes[0].model_copy(update={"split": "test"})
    with pytest.raises(PackError, match="Conflicting"):
        _build(tmp_path / "conflict", scenes=[*scenes, conflicting])
    assert not (tmp_path / "conflict").exists()


@pytest.mark.parametrize("tamper", ["byte", "extra", "missing", "manifest"])
def test_tampering_is_detected(tmp_path, tamper):
    root = tmp_path / "p"
    build_synthetic_pack(root)
    if tamper == "byte":
        data = bytearray((root / "scenes.jsonl").read_bytes())
        data[10] ^= 1
        (root / "scenes.jsonl").write_bytes(bytes(data))
    elif tamper == "extra":
        (root / "notes.txt").write_text("x")
    elif tamper == "missing":
        (root / "exclusions.jsonl").unlink()
    else:
        (root / "manifest.json").write_text('{"pack_id":"x","pack_id":"y"}')
    with pytest.raises(PackError):
        verify_pack(root)
    assert load_pack(root, audience="local").status == "unavailable"


def test_public_pack_requires_public_permission(tmp_path):
    restricted = [
        source_manifest("ssr_3dfront", "unknown"),
        source_manifest("future_3d"),
    ]
    with pytest.raises(PackError, match="source_not_public"):
        _build(tmp_path / "p", sources=restricted, audience="public")
    local_only = [source_manifest("ssr_3dfront", "unknown")]
    with pytest.raises(PackError, match="source_not_permitted"):
        _build(tmp_path / "q", sources=local_only, assets=False)


def test_assets_require_a_future_source_and_exact_glb_set(tmp_path):
    with pytest.raises(PackError):
        _build(tmp_path / "p", sources=[source_manifest("ssr_3dfront")])


def test_load_pack_reports_unavailable_without_raising(tmp_path):
    assert load_pack(None).reason == "not_configured"
    assert load_pack("").reason == "not_configured"
    assert load_pack(tmp_path / "missing").reason == "pack_not_found"
    build_synthetic_pack(tmp_path / "local")
    assert load_pack(tmp_path / "local").reason == "pack_not_public"
    ready = load_pack(tmp_path / "local", audience="local")
    assert ready.status == "ready" and ready.pack is not None
    build_synthetic_pack(tmp_path / "public", audience="public")
    assert load_pack(tmp_path / "public").status == "ready"


def test_reasons_never_contain_paths(tmp_path):
    root = tmp_path / "secret-location"
    build_synthetic_pack(root)
    (root / "extra.txt").write_text("x")
    status = load_pack(root, audience="local")
    assert status.status == "unavailable"
    assert "secret-location" not in status.reason and "/" not in status.reason


def test_pack_directory_must_be_empty(tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p/keep.txt").write_text("x")
    with pytest.raises(PackError):
        _build(tmp_path / "p")
    assert (tmp_path / "p/keep.txt").exists()
