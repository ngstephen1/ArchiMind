"""P2a SSR adapter on synthetic rows (real-data results: docs/data/DATASET_SSR_P2A.md)."""

import json
import math

import pytest

from archimind.datasets.canonical import file_sha256
from archimind.datasets.cli import main
from archimind.datasets.pack import verify_pack
from archimind.datasets.ssr_adapter import (
    base_jid,
    build_report,
    convert_row,
    deduplicate,
    lookup_category,
)

HOUSE = "62a36664-15ed-4930-839a-0964bdc11d45"
OTHER_HOUSE = "0f1e2d3c-4b5a-4968-8776-655443322110"
BED = "83db09d8-0c4c-4b13-8909-404bdf4ea3ec"
LAMP = "19e1a64d-a87f-4d82-8834-5c34b889a059"
UNKNOWN = "2a6d5ab2-bb75-462f-ab8f-471b7cc6a9fc"
REVISION = "b606183e56d972f85850125f9191932cbea654c3"
SHA = "a" * 64
CATEGORIES = {BED: "Bed", LAMP: "Lighting"}


def rect(w=3.3, d=3.9, h=2.6):
    hx, hz = w / 2, d / 2
    corners = [(-hx, hz), (hx, hz), (hx, -hz), (-hx, -hz)]
    return [[x, 0.0, z] for x, z in corners], [[x, h, z] for x, z in corners]


def yaw(deg):
    half = math.radians(deg) / 2
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def obj(pos=(0.0, 0.0, 0.0), size=(1.0, 0.5, 2.0), deg=0.0, jid=BED):
    return {
        "desc": "IGNORED",
        "jid": jid,
        "pos": list(pos),
        "size": list(size),
        "rot": yaw(deg),
    }


def row(objects, *, house=HOUSE, room="Bedroom-1443", split="train", bounds=None):
    bottom, top = bounds or rect()
    return {
        "file_id": house + "-893b170a-f755-4b24-bea3-2fdb13048980",
        "room_type": "bedroom",
        "splits": [f"bedroom_{split}", "all_val"],
        "scene": {
            "bounds_bottom": bottom,
            "bounds_top": top,
            "objects": objects,
            "room_id": room,
            "room_type": "bedroom",
        },
    }


def convert(r, midi_splits=None):
    return convert_row(
        r,
        revision=REVISION,
        source_sha256=SHA,
        jid_categories=CATEGORIES,
        midi_splits=midi_splits or {},
    )


def check(scene, name):
    return next(c for c in scene.checks if c.name == name)


def test_base_jid_strips_scale_variant_suffix():
    assert base_jid(BED) == BED
    assert base_jid(f"{BED}-(0.74)-(1.0)-(0.68)") == BED
    assert base_jid(f"{BED}-(-1.0)-(1)-(1)") == BED  # mirrored (negative x scale)
    assert base_jid(f"{BED}-(--1.0)") is None
    assert base_jid("not-a-jid") is None
    assert base_jid(None) is None


def test_category_lookup_exact_then_base():
    assert lookup_category(f"{BED}-(0.5)", CATEGORIES) == "Bed"
    assert lookup_category(f"{BED}-(0.5)", {f"{BED}-(0.5)": "Sofa"}) == "Sofa"
    assert lookup_category(UNKNOWN, CATEGORIES) is None


def test_all_zero_yaw_room_is_canonical_with_namespaced_identity():
    result = convert(row([obj((0.0, 0.0, 0.0))]))
    scene = result.scene
    assert scene.tier == "canonical"
    assert scene.reference_id == f"ssr:{HOUSE}:Bedroom-1443"
    assert scene.openings == "unknown"
    assert check(scene, "door_clearance").status == "NOT_VERIFIABLE"
    assert check(scene, "split_agreement").status == "NOT_VERIFIABLE"
    o = scene.objects[0]
    assert (o.category, o.raw_category, o.jid) == ("bed", "Bed", BED)
    assert o.footprint.x_m == pytest.approx(1.15)


def test_descriptions_are_never_stored():
    scene = convert(row([obj()])).scene
    assert "IGNORED" not in scene.model_dump_json()


def test_quarter_turn_is_reference_only():
    scene = convert(row([obj(deg=90.0)])).scene
    assert scene.tier == "reference_only"
    assert scene.objects[0].footprint.yaw_quarter_turns == 1


def test_unmapped_object_is_kept_without_footprint():
    scene = convert(row([obj(), obj((1.0, 0.0, 1.0), jid=UNKNOWN)])).scene
    assert scene.tier == "reference_only"
    unmapped = scene.objects[1]
    assert unmapped.exclusion == "unmapped_category"
    assert unmapped.footprint is None and unmapped.jid == UNKNOWN


def test_no_admitted_object_is_an_exclusion():
    result = convert(row([obj(jid=UNKNOWN)]))
    assert result.scene is None
    assert result.exclusion.reason == "unmapped_category"


def test_irregular_room_is_an_exclusion():
    bottom = [[0, 0, 0], [2, 0, 0], [2, 0, 1], [1, 0, 1], [1, 0, 2], [0, 0, 2]]
    top = [[x, 2.5, z] for x, _, z in bottom]
    result = convert(row([obj()], bounds=(bottom, top)))
    assert result.exclusion.reason == "irregular_room"


def test_wall_protrusion_and_solid_overlap_fail_checks_and_tier():
    scene = convert(row([obj((1.5, 0.0, 0.0)), obj((1.4, 0.0, 0.0))])).scene
    assert scene.tier == "reference_only"
    assert check(scene, "wall_containment").status == "FAIL"
    assert check(scene, "solid_overlap").status == "FAIL"


def test_hanging_light_does_not_fail_floor_contact():
    lamp = obj((1.0, 2.2, 1.0), size=(0.4, 0.3, 0.4), jid=LAMP)
    scene = convert(row([obj(), lamp])).scene
    assert check(scene, "floor_contact").status == "PASS"
    floating_bed = obj((-1.0, 0.5, -1.0), size=(0.5, 0.5, 0.5))
    scene = convert(row([obj(), floating_bed])).scene
    assert check(scene, "floor_contact").status == "FAIL"


def test_floor_lamp_must_stand_on_the_floor():
    floating_lamp = obj((1.0, 0.5, 1.0), size=(0.4, 1.5, 0.4), jid=LAMP)
    fine = {LAMP: "Floor Lamp"}
    scene = convert_row(
        row([obj(), floating_lamp]),
        revision=REVISION,
        source_sha256=SHA,
        jid_categories=CATEGORIES,
        midi_splits={},
        jid_fine_categories=fine,
    ).scene
    assert check(scene, "floor_contact").status == "FAIL"
    hanging = obj((1.0, 2.2, 1.0), size=(0.4, 0.3, 0.4), jid=LAMP)
    scene = convert_row(
        row([obj(), hanging]),
        revision=REVISION,
        source_sha256=SHA,
        jid_categories=CATEGORIES,
        midi_splits={},
        jid_fine_categories={LAMP: "Pendant Lamp"},
    ).scene
    assert check(scene, "floor_contact").status == "PASS"


def test_fine_category_is_raw_category_and_mirrored_jid_is_admitted():
    mirrored = obj((1.0, 0.0, 1.0), size=(0.5, 0.5, 0.5), jid=f"{BED}-(-1.0)-(1)-(1)")
    scene = convert_row(
        row([obj(), mirrored]),
        revision=REVISION,
        source_sha256=SHA,
        jid_categories=CATEGORIES,
        midi_splits={},
        jid_fine_categories={BED: "King-size Bed"},
    ).scene
    assert [(o.jid, o.raw_category, o.category) for o in scene.objects] == [
        (BED, "King-size Bed", "bed"),
        (BED, "King-size Bed", "bed"),
    ]
    assert scene.category_map_version == "1.1.0"
    report = build_report([scene], [])
    assert report["admitted_raw_categories"] == {"King-size Bed": 2}


def test_bad_quaternion_becomes_malformed_object():
    broken = obj((1.0, 0.0, 1.0))
    broken["rot"] = [0.0, 0.0, 0.0, 0.0]
    scene = convert(row([obj(), broken])).scene
    assert scene.objects[1].exclusion == "malformed_record"


def test_split_agreement_uses_midi_split():
    key = f"{HOUSE}/Bedroom-1443"
    assert (
        check(convert(row([obj()]), {key: "test"}).scene, "split_agreement").status
        == "FAIL"
    )
    assert (
        check(convert(row([obj()]), {key: "train"}).scene, "split_agreement").status
        == "PASS"
    )


def test_non_bedroom_rows_are_skipped():
    r = row([obj()])
    r["splits"] = ["livingroom_train"]
    assert convert(r) is None


def test_duplicate_geometry_keeps_smallest_id_and_records_alias():
    a = convert(row([obj()], house=HOUSE, split="train"))
    b = convert(row([obj()], house=OTHER_HOUSE, split="test"))
    scenes, exclusions = deduplicate([a, b])
    assert [s.reference_id for s in scenes] == [b.reference_id]  # "0f..." < "62..."
    (alias,) = exclusions
    assert alias.reason == "duplicate_identity" and alias.source_id == a.reference_id
    assert "splits train and test" in alias.detail
    report = build_report(scenes, exclusions)
    assert report["exclusion_reasons"] == {"duplicate_identity": 1}


def _write_parquet(path, rows):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    pq.write_table(pa.Table.from_pylist(rows), path)


def test_ssr_build_cli_writes_stage_and_verified_local_pack(tmp_path, capsys):
    shard = tmp_path / "train.parquet"
    _write_parquet(
        shard,
        [
            row([obj()]),
            row([obj(deg=90.0)], house=OTHER_HOUSE, room="MasterBedroom-7"),
        ],
    )
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "repo": "gradient-spaces/SSR-3DFRONT",
                "revision": REVISION,
                "files": [
                    {
                        "path": "data/train-00000-of-00001.parquet",
                        "size_bytes": shard.stat().st_size,
                        "sha256": file_sha256(shard),
                    }
                ],
            }
        )
    )
    midi = tmp_path / "midi"
    midi.mkdir()
    rooms = [f"{HOUSE}/Bedroom-1443"] + [
        f"{OTHER_HOUSE}/Bedroom-{i}" for i in range(1000)
    ]
    furniture = [[f"Bed_{BED}_0"]] + [[] for _ in range(1000)]
    (midi / "midi_room_ids.json").write_text(json.dumps(rooms))
    (midi / "midi_furniture_ids.json").write_text(json.dumps(furniture))
    (midi / "midi_test_room_ids.json").write_text(json.dumps(rooms[-1000:]))
    permission = tmp_path / "permission.json"
    permission.write_text(
        json.dumps(
            {
                "local_research": "allowed",
                "derived_metadata": "unknown",
                "public_geometry": "unknown",
                "public_images": "unknown",
                "provider_disclosure": "unknown",
                "evidence": "synthetic test",
                "decided_by": "test",
                "decided_utc": "2026-01-01T00:00:00Z",
            }
        )
    )
    code = main(
        [
            "ssr-build",
            str(shard),
            "--inventory",
            str(inventory),
            "--midi-dir",
            str(midi),
            "--out",
            str(tmp_path / "stage"),
            "--pack-dir",
            str(tmp_path / "pack"),
            "--permission",
            str(permission),
            "--retrieved-utc",
            "2026-11-06T18:00:00Z",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0, payload
    assert payload["tiers"] == {"canonical": 1, "reference_only": 1}
    pack = verify_pack(tmp_path / "pack")
    assert pack.manifest.audience == "local"
    assert len(pack.scenes) == 2
    assert pack.sources[0].files[0].path == "data/train-00000-of-00001.parquet"

    # A public pack is refused while derived-metadata permission is unknown.
    code = main(
        [
            "ssr-build",
            str(shard),
            "--inventory",
            str(inventory),
            "--midi-dir",
            str(midi),
            "--out",
            str(tmp_path / "stage2"),
            "--pack-dir",
            str(tmp_path / "pack2"),
            "--audience",
            "public",
            "--permission",
            str(permission),
            "--retrieved-utc",
            "2026-11-06T18:00:00Z",
        ]
    )
    assert code == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "source_not_public"
    assert not (tmp_path / "pack2").exists()


def test_ssr_build_rejects_unpinned_shard(tmp_path, capsys):
    shard = tmp_path / "train.parquet"
    _write_parquet(shard, [row([obj()])])
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"repo": "x/y", "revision": REVISION, "files": []}))
    midi = tmp_path / "midi"
    midi.mkdir()
    rooms = [f"{OTHER_HOUSE}/Bedroom-{i}" for i in range(1000)]
    (midi / "midi_room_ids.json").write_text(json.dumps(rooms))
    (midi / "midi_furniture_ids.json").write_text(json.dumps([[] for _ in rooms]))
    (midi / "midi_test_room_ids.json").write_text(json.dumps(rooms))
    code = main(
        [
            "ssr-build",
            str(shard),
            "--inventory",
            str(inventory),
            "--midi-dir",
            str(midi),
            "--out",
            str(tmp_path / "stage"),
        ]
    )
    assert code == 1
    assert (
        "not in the pinned inventory" in json.loads(capsys.readouterr().out)["reason"]
    )


def _future_build_inputs(tmp_path, model_info):
    """Shard, inventories, MIDI lists, permission and a model_info.json on disk."""
    shard = tmp_path / "train.parquet"
    lamp = obj((1.0, 0.0, 1.0), size=(0.4, 1.5, 0.4), jid=f"{UNKNOWN}-(-1.0)-(1)-(1)")
    _write_parquet(shard, [row([obj(), lamp])])
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "repo": "gradient-spaces/SSR-3DFRONT",
                "revision": REVISION,
                "files": [
                    {
                        "path": "data/train-00000-of-00001.parquet",
                        "size_bytes": shard.stat().st_size,
                        "sha256": file_sha256(shard),
                    }
                ],
            }
        )
    )
    midi = tmp_path / "midi"
    midi.mkdir()
    rooms = [f"{OTHER_HOUSE}/Bedroom-{i}" for i in range(1000)]
    furniture = [[f"Bed_{BED}_0"]] + [[] for _ in range(999)]
    (midi / "midi_room_ids.json").write_text(json.dumps(rooms))
    (midi / "midi_furniture_ids.json").write_text(json.dumps(furniture))
    (midi / "midi_test_room_ids.json").write_text(json.dumps(rooms))
    info = tmp_path / "model_info.json"
    info.write_text(json.dumps(model_info))
    future_inventory = tmp_path / "future_inventory.json"
    future_inventory.write_text(
        json.dumps(
            {
                "ref": "owner/3d-future",
                "version": 1,
                "model_info": [
                    {
                        "path": "3D-FUTURE-model/model_info.json",
                        "size_bytes": info.stat().st_size,
                        "url": "https://www.kaggle.com/x",
                    }
                ],
            }
        )
    )
    permission = tmp_path / "permission.json"
    permission.write_text(
        json.dumps(
            {
                "local_research": "allowed",
                "derived_metadata": "unknown",
                "public_geometry": "unknown",
                "public_images": "unknown",
                "provider_disclosure": "unknown",
                "evidence": "synthetic test",
                "decided_by": "test",
                "decided_utc": "2026-01-01T00:00:00Z",
            }
        )
    )
    base = [
        "ssr-build",
        str(shard),
        "--inventory",
        str(inventory),
        "--midi-dir",
        str(midi),
        "--future-model-info",
        str(info),
        "--future-sha256",
        file_sha256(info),
        "--future-inventory",
        str(future_inventory),
    ]
    return base, permission


def test_ssr_build_with_future_categories_and_pack(tmp_path, capsys):
    model_info = [
        {"model_id": BED, "super-category": "Bed", "category": "Double Bed"},
        {"model_id": UNKNOWN, "super-category": "Lighting", "category": "Floor Lamp"},
    ]
    base, permission = _future_build_inputs(tmp_path, model_info)
    pack_args = [
        "--pack-dir",
        str(tmp_path / "pack"),
        "--permission",
        str(permission),
        "--retrieved-utc",
        "2026-11-06T18:00:00Z",
    ]
    # The pack needs a 3D-FUTURE permission record of its own.
    code = main([*base, "--out", str(tmp_path / "s0"), *pack_args])
    assert code == 1
    assert "--future-permission" in json.loads(capsys.readouterr().out)["reason"]

    code = main(
        [
            *base,
            "--out",
            str(tmp_path / "stage"),
            *pack_args,
            "--future-permission",
            str(permission),
            "--future-retrieved-utc",
            "2026-11-16T03:12:56Z",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0, payload
    assert payload["category_sources"]["future_3d"]["midi_agrees_with_future"] == 1
    assert payload["admitted_raw_categories"] == {"Double Bed": 1, "Floor Lamp": 1}
    assert payload["object_exclusions"] == {}
    pack = verify_pack(tmp_path / "pack")
    assert sorted(s.source for s in pack.sources) == ["future_3d", "ssr_3dfront"]
    future = next(s for s in pack.sources if s.source == "future_3d")
    assert future.revision == "kaggle-v1"
    assert future.files[0].path == "3D-FUTURE-model/model_info.json"


def test_ssr_build_rejects_unpinned_or_contradicting_future(tmp_path, capsys):
    model_info = [{"model_id": BED, "super-category": "Sofa", "category": None}]
    base, _ = _future_build_inputs(tmp_path, model_info)
    wrong_sha = [*base]
    wrong_sha[wrong_sha.index("--future-sha256") + 1] = "0" * 64
    assert main([*wrong_sha, "--out", str(tmp_path / "a")]) == 1
    assert "does not match" in json.loads(capsys.readouterr().out)["reason"]
    # MIDI says Bed, 3D-FUTURE says Sofa: the build stops.
    assert main([*base, "--out", str(tmp_path / "b")]) == 1
    assert "MIDI says Bed" in json.loads(capsys.readouterr().out)["reason"]
    # The three --future-* inputs go together.
    partial = base[: base.index("--future-sha256")]
    assert main([*partial, "--out", str(tmp_path / "c")]) == 1
    assert "go together" in json.loads(capsys.readouterr().out)["reason"]
