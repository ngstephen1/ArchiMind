"""Asset release records, file verification, pack budgets and the CC0 fetch helpers."""

import hashlib
import io
import json
import runpy
from pathlib import Path

import pytest
from PIL import Image

from archimind.assets import designer_concepts as concepts
from archimind.style_packs import all_packs, load_releases, pack_status
from archimind.style_packs.models import AssetRelease
from archimind.style_packs.release import (
    ALL_PACKS_CAP_BYTES,
    PACK_CAP_BYTES,
    notices_path,
    pack_budget,
    verify_release,
)

ROOT = Path(__file__).resolve().parents[1]
FETCH = runpy.run_path(str(ROOT / "scripts" / "fetch_cc0_asset.py"))


def _webp(size, color="white"):
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, "WEBP", quality=80)
    return out.getvalue()


def _store(tmp_path, data, ext):
    digest = hashlib.sha256(data).hexdigest()
    (tmp_path / f"{digest}.{ext}").write_bytes(data)
    return digest


def _material(tmp_path, data, *, px=(1024, 1024), **overrides):
    digest = _store(tmp_path, data, "webp")
    row = {
        "asset_id": "polyhaven:fixture_floor",
        "kind": "material",
        "license": "CC0-1.0",
        "source_url": "https://polyhaven.com/a/fixture_floor",
        "upstream_checksum": None,
        "files": [
            {"role": "diffuse", "tier": "low", "sha256": digest, "ext": "webp",
             "bytes": len(data), "width_px": px[0], "height_px": px[1]}
        ],
    }
    row.update(overrides)
    return AssetRelease.model_validate(row)


def test_release_requires_license_source_and_hash(tmp_path):
    release = _material(tmp_path, _webp((1024, 1024)))
    verify_release(release, tmp_path)
    raw = release.model_dump(mode="json")
    for bad in (
        {"license": "CC-BY-4.0"},
        {"source_url": "http://polyhaven.com/a/x"},
        {"files": [raw["files"][0] | {"sha256": "abc"}]},
    ):
        with pytest.raises(ValueError):
            AssetRelease.model_validate(raw | bad)
    with pytest.raises(ValueError, match="source"):
        verify_release(AssetRelease.model_validate(raw | {"source_url": "https://example.com/x"}), tmp_path)
    with pytest.raises(ValueError, match="diffuse"):
        verify_release(
            AssetRelease.model_validate(raw | {"files": [raw["files"][0] | {"role": "normal"}]}), tmp_path
        )


def test_texture_over_2048px_rejected(tmp_path):
    release = _material(tmp_path, _webp((2049, 16)), px=(1024, 1024))
    with pytest.raises(ValueError, match="2048"):
        verify_release(release, tmp_path)
    release = _material(tmp_path, _webp((512, 512)), px=(1024, 1024))
    with pytest.raises(ValueError, match="pixel size"):
        verify_release(release, tmp_path)


def test_file_hash_must_match_bytes_on_disk(tmp_path):
    release = _material(tmp_path, _webp((1024, 1024)))
    path = tmp_path / f"{release.files[0].sha256}.webp"
    data = path.read_bytes()
    path.write_bytes(data[:-1] + bytes([data[-1] ^ 0xFF]))
    with pytest.raises(ValueError, match="hash"):
        verify_release(release, tmp_path)
    path.unlink()
    with pytest.raises(ValueError, match="missing"):
        verify_release(release, tmp_path)


def test_model_release_passes_glb_inspection_budgets(tmp_path):
    chair = concepts.approved_chairs()[0]
    data = concepts._asset(chair.sha256, "glb")
    digest = _store(tmp_path, data, "glb")
    release = AssetRelease.model_validate({
        "asset_id": "polyhaven:fixture_chair", "kind": "model", "license": "CC0-1.0",
        "source_url": "https://polyhaven.com/a/fixture_chair", "upstream_checksum": None,
        "files": [{"role": "model", "tier": "both", "sha256": digest, "ext": "glb", "bytes": len(data)}],
    })
    facts = verify_release(release, tmp_path)
    assert facts["polyhaven:fixture_chair"]["triangles"] == 3712
    junk = b"glTF" + b"\0" * 40
    bad = _store(tmp_path, junk, "glb")
    broken = release.model_copy(update={"files": (release.files[0].model_copy(update={"sha256": bad, "bytes": len(junk)}),)})
    with pytest.raises(ValueError):
        verify_release(broken, tmp_path)


def test_hdr_environment_header_and_size_are_checked(tmp_path):
    hdr = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 512 +X 1024\n" + b"\0" * 64
    digest = _store(tmp_path, hdr, "hdr")
    release = AssetRelease.model_validate({
        "asset_id": "polyhaven:fixture_room", "kind": "environment", "license": "CC0-1.0",
        "source_url": "https://polyhaven.com/a/fixture_room", "upstream_checksum": None,
        "files": [{"role": "hdr", "tier": "both", "sha256": digest, "ext": "hdr", "bytes": len(hdr),
                   "width_px": 1024, "height_px": 512}],
    })
    verify_release(release, tmp_path)
    big = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 2048 +X 4096\n" + b"\0" * 64
    bad = _store(tmp_path, big, "hdr")
    with pytest.raises(ValueError, match="1k"):
        verify_release(release.model_copy(update={"files": (release.files[0].model_copy(update={"sha256": bad, "bytes": len(big)}),)}), tmp_path)


def test_every_packaged_release_verifies():
    for release in load_releases().values():
        verify_release(release)


def test_every_released_pack_is_within_25mb_and_total_within_120mb():
    total = 0
    for pack in all_packs():
        high = pack_budget(pack, "high")
        assert high <= PACK_CAP_BYTES, pack.id
        assert pack_budget(pack, "low") <= high
        if pack_status(pack).released:
            total += high
    assert total <= ALL_PACKS_CAP_BYTES


def test_every_cc0_release_has_a_notice_line():
    notices = notices_path().read_text(encoding="utf-8")
    for release in load_releases().values():
        if release.license == "CC0-1.0":
            assert f"{release.asset_id} " in notices and release.source_url in notices
    bundle = (ROOT / "src/archimind/_viewer_assets/THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert notices.strip() in bundle


# --- fetch_cc0_asset.py helpers (no network) ---

POLYHAVEN_FILES = {
    "Diffuse": {"1k": {"jpg": {"url": "https://dl.polyhaven.org/a/d_1k.jpg", "md5": "a" * 32, "size": 10}},
                "2k": {"jpg": {"url": "https://dl.polyhaven.org/a/d_2k.jpg", "md5": "b" * 32, "size": 20}}},
    "nor_gl": {"1k": {"jpg": {"url": "https://dl.polyhaven.org/a/n_1k.jpg", "md5": "c" * 32, "size": 10}}},
    "Rough": {"1k": {"jpg": {"url": "https://dl.polyhaven.org/a/r_1k.jpg", "md5": "d" * 32, "size": 10}}},
    "AO": {"1k": {"jpg": {"url": "https://dl.polyhaven.org/a/ao_1k.jpg", "md5": "e" * 32, "size": 10}}},
}


def test_polyhaven_material_plan_picks_roles_and_tiers():
    plan = FETCH["polyhaven_material_plan"](POLYHAVEN_FILES, roles=["diffuse", "normal", "roughness"], high_roles=["diffuse"])
    assert [(p["role"], p["tier"], p["px"]) for p in plan] == [
        ("diffuse", "low", 1024), ("diffuse", "high", 2048), ("normal", "both", 1024), ("roughness", "both", 1024),
    ]
    assert plan[1]["url"].endswith("d_2k.jpg") and plan[1]["md5"] == "b" * 32
    with pytest.raises(ValueError, match="ao_missing"):
        FETCH["polyhaven_material_plan"]({"Diffuse": POLYHAVEN_FILES["Diffuse"]}, roles=["diffuse", "ao_missing"], high_roles=[])


def test_texture_conversion_resizes_to_requested_px_as_webp():
    src = io.BytesIO()
    Image.new("RGB", (2048, 2048), "red").save(src, "JPEG")
    out = FETCH["to_webp"](src.getvalue(), 1024)
    with Image.open(io.BytesIO(out)) as image:
        assert image.format == "WEBP" and image.size == (1024, 1024)


def test_gltf_with_external_buffers_packs_into_a_single_glb():
    chair = concepts.approved_chairs()[0]
    glb = concepts._asset(chair.sha256, "glb")
    import struct

    json_len = struct.unpack_from("<I", glb, 12)[0]
    doc = json.loads(glb[20 : 20 + json_len])
    bin_start = 20 + json_len + 8
    binary = glb[bin_start : bin_start + doc["buffers"][0]["byteLength"]]
    doc["buffers"][0]["uri"] = "chair.bin"
    packed = FETCH["pack_glb"](doc, {"chair.bin": binary})
    assert packed[:4] == b"glTF"
    facts = concepts.inspect_piece(packed, (0.48, 0.52, 0.83))
    assert facts["triangles"] == 3712


def test_notice_line_format():
    line = FETCH["notice_line"]("polyhaven:oak_floor", "Oak Floor", ["Rico Cilliers"], "https://polyhaven.com/a/oak_floor")
    assert line == "polyhaven:oak_floor — Oak Floor by Rico Cilliers, CC0 1.0 (public domain dedication), https://polyhaven.com/a/oak_floor"
