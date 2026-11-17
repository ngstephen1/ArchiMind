"""P2c MIDI adapter on synthetic rooms (real-data results: docs/data/DATASET_MIDI_P2C.md)."""

import json
import math

import pytest

from archimind.datasets.midi_adapter import (
    MidiAlignmentError,
    alignment_report,
    associate,
    camera_report,
    classify_room_files,
    fit_similarity,
    gltf_to_camera_world,
    is_quarter_turn,
    match_objects,
    predicted_normalization,
    project,
    projected_box,
    ssr_world_box,
    topdown_svg,
    view_inventory,
)

BED = "83db09d8-0c4c-4b13-8909-404bdf4ea3ec"
LAMP = "19e1a64d-a87f-4d82-8834-5c34b889a059"
STAND = "2a6d5ab2-bb75-462f-ab8f-471b7cc6a9fc"
ZERO = [0.0, 0.0, 0.0, 1.0]
QUARTER = [0.0, math.sin(math.pi / 4), 0.0, math.cos(math.pi / 4)]

# --------------------------------------------------------------- files


def test_classify_room_files_sorts_room_object_and_structure_members():
    files = classify_room_files(
        "Bedroom-1",
        [
            "Bedroom-1.glb",
            "Bedroom-1_full.glb",
            f"Bedroom-1/Bed_{BED}_1.glb",
            "Bedroom-1/ceil.glb",
            "Bedroom-1/others.glb",
            "Bedroom-1/mystery.glb",
            "Bedroom-2.glb",
        ],
    )
    assert files.room_glb == "Bedroom-1.glb" and files.full_glb == "Bedroom-1_full.glb"
    assert files.objects == {f"Bed_{BED}_1": f"Bedroom-1/Bed_{BED}_1.glb"}
    assert files.structure == ("Bedroom-1/ceil.glb", "Bedroom-1/others.glb")
    assert files.unrecognized == ("Bedroom-1/mystery.glb", "Bedroom-2.glb")


def test_association_reports_missing_orphan_and_duplicate_objects():
    a, b, c = f"Bed_{BED}_1", f"Lighting_{LAMP}_2", f"Cabinet_Shelf_Desk_{STAND}_3"
    result = associate([a, b, b], [a, c])
    assert result.matched == (a,)
    assert result.missing == (b,)
    assert result.orphans == (c,)
    assert result.duplicates == (b,)


def test_view_inventory_counts_missing_extra_and_unexpected():
    names = ["meta.json", "render_0000.webp", "render_0002.webp", "semantic_0000.png"]
    names += ["depth_0000.exr", "depth_0001.webp", "notes.txt"]
    inv = view_inventory(names, 2)
    assert inv["kinds"]["render"] == {"present": 1, "missing": [1], "extra": [2]}
    assert inv["kinds"]["depth"]["present"] == 1
    assert inv["unexpected"] == ["depth_0001.webp", "notes.txt"]


# --------------------------------------------------------------- geometry


def test_ssr_world_box_uses_bottom_pivot_and_swaps_extent_at_quarter_turn():
    centre, extent = ssr_world_box([2.0, 1.0, 0.5], [1.0, 0.0, -1.0], ZERO)
    assert centre == (1.0, 0.5, -1.0) and extent == (2.0, 1.0, 0.5)
    _, turned = ssr_world_box([2.0, 1.0, 0.5], [0.0, 0.0, 0.0], QUARTER)
    assert [round(v, 9) for v in turned] == [0.5, 1.0, 2.0]
    assert ssr_world_box([1, 1, 1], [0, 0, 0], [0.1, 0.0, 0.0, 0.995]) is None
    assert is_quarter_turn(QUARTER) and not is_quarter_turn([0, 0.5, 0, 0.866])


def ssr_object(oid, jid, size, pos, rot=ZERO):
    return {
        "source_object_id": oid,
        "jid": jid,
        "size_raw": size,
        "position_raw": pos,
        "rotation_raw_xyzw": rot,
    }


def to_midi(objects, scale, translation, *, skip=()):
    """Synthesize MIDI (centre, extent) boxes: MIDI = scale * (SSR - translation)."""
    midi = {}
    for n, o in enumerate(objects):
        if o["source_object_id"] in skip:
            continue
        centre, extent = ssr_world_box(
            o["size_raw"], o["position_raw"], o["rotation_raw_xyzw"]
        )
        category = {BED: "Bed", LAMP: "Lighting"}.get(o["jid"], "Cabinet_Shelf_Desk")
        midi[f"{category}_{o['jid']}_{n + 1}"] = (
            tuple(scale * (c - t) for c, t in zip(centre, translation, strict=True)),
            tuple(scale * e for e in extent),
        )
    return midi


ROOM = [
    ssr_object("o00", BED, [1.6, 0.9, 2.0], [0.2, 0.0, -0.4]),
    ssr_object("o01", STAND, [0.45, 0.5, 0.4], [-1.1, 0.0, -1.3], QUARTER),
    ssr_object("o02", STAND, [0.45, 0.5, 0.4], [1.4, 0.0, -1.3], QUARTER),
    ssr_object("o03", LAMP, [0.6, 0.2, 0.6], [0.0, 2.3, 0.0]),
]


def test_fit_recovers_scale_translation_and_assigns_repeated_jids_by_position():
    midi = to_midi(ROOM, 0.6, (0.3, 1.25, -0.2))
    report = alignment_report(midi, ROOM)
    assert report["status"] == "PASS"
    assert report["scale_midi_per_m"] == pytest.approx(0.6)
    assert report["translation_m"] == pytest.approx([0.3, 1.25, -0.2])
    pairs = {p["furniture_id"]: p["ssr_object_id"] for p in report["pairs"]}
    assert pairs[f"Cabinet_Shelf_Desk_{STAND}_2"] == "o01"
    assert pairs[f"Cabinet_Shelf_Desk_{STAND}_3"] == "o02"
    assert all(p["centre_error_m"] == 0 for p in report["pairs"])


def test_displaced_object_fails_and_extra_objects_stay_unmatched():
    midi = to_midi(ROOM, 0.6, (0.0, 1.3, 0.0), skip={"o03"})
    key = f"Bed_{BED}_1"
    centre, extent = midi[key]
    midi[key] = ((centre[0] + 0.6 * 0.10, centre[1], centre[2]), extent)  # 10 cm off
    midi[f"Sofa_{LAMP.replace('1', '2')}_9"] = ((0.0, 0.0, 0.0), (0.1, 0.1, 0.1))
    report = alignment_report(midi, ROOM)
    assert report["status"] == "FAIL"
    assert (
        next(p for p in report["pairs"] if p["furniture_id"] == key)["status"] == "FAIL"
    )
    assert report["unmatched_ssr"] == ["o03"]
    assert len(report["unmatched_midi"]) == 1


def test_extent_is_not_compared_off_a_quarter_turn():
    tilted_yaw = [0.0, math.sin(1.0), 0.0, math.cos(1.0)]
    room = [
        *ROOM[:1],
        ssr_object("o09", LAMP, [0.6, 0.2, 0.3], [1.0, 0.0, 1.0], tilted_yaw),
    ]
    midi = to_midi(room, 0.5, (0.0, 1.0, 0.0))
    key = f"Lighting_{LAMP}_2"
    centre, extent = midi[key]
    midi[key] = (
        centre,
        (extent[0] * 0.8, extent[1], extent[2] * 0.8),
    )  # mesh box smaller
    report = alignment_report(midi, room)
    row = next(p for p in report["pairs"] if p["furniture_id"] == key)
    assert row["extent_error_m"] is None and row["status"] == "PASS"


def test_no_shared_jid_is_not_verifiable_and_repeated_only_jids_are_not_guessed():
    report = alignment_report({f"Bed_{LAMP}_1": ((0, 0, 0), (1, 1, 1))}, ROOM[:1])
    assert report["status"] == "NOT_VERIFIABLE"
    midi = to_midi(ROOM[1:3], 0.5, (0.0, 0.0, 0.0))
    ssr = {
        o["source_object_id"]: (
            o["jid"],
            ssr_world_box(o["size_raw"], o["position_raw"], o["rotation_raw_xyzw"]),
        )
        for o in ROOM[1:3]
    }
    pairs, unmatched_midi, _ = match_objects(midi, ssr)
    assert pairs == [] and len(unmatched_midi) == 2
    with pytest.raises(MidiAlignmentError):
        fit_similarity([])


def test_predicted_normalization_matches_the_union_box_rule():
    boxes = [((0.0, 1.0, 0.0), (4.0, 2.0, 1.0)), ((3.0, 0.5, 0.0), (2.0, 1.0, 1.0))]
    scale, centre = predicted_normalization(boxes)
    assert scale == pytest.approx(1.9 / 6.0)
    assert centre == pytest.approx((1.0, 1.0, 0.0))


# --------------------------------------------------------------- cameras

# Camera at (0, -3, 0) in the Z-up world, looking at the origin along +Y.
C2W = [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, -3.0], [0.0, 1.0, 0.0, 0.0], [0, 0, 0, 1]]


def test_projection_centre_right_up_and_behind():
    angle = math.radians(60)
    assert project(C2W, angle, 100, 80, (0.0, 0.0, 0.0)) == pytest.approx((50.0, 40.0))
    u, v = project(C2W, angle, 100, 80, (0.5, 0.0, 0.5))  # right and up of centre
    assert u > 50 and v < 40
    assert project(C2W, angle, 100, 80, (0.0, -4.0, 0.0)) is None  # behind
    with pytest.raises(MidiAlignmentError):
        project(C2W, 0.0, 100, 80, (0.0, 0.0, 0.0))


def test_gltf_points_map_into_the_z_up_camera_world():
    assert gltf_to_camera_world((1.0, 2.0, 3.0)) == (1.0, -3.0, 2.0)
    # glTF +y (up) projects above the image centre.
    _, v = project(C2W, 1.0, 100, 100, gltf_to_camera_world((0.0, 0.5, 0.0)))
    assert v < 50


def look_at(eye):
    """Camera-to-world matrix (Z-up world, camera -Z towards the origin, +Y up)."""
    norm = math.sqrt(sum(v * v for v in eye))
    back = tuple(v / norm for v in eye)
    right = (-back[1], back[0], 0.0)  # cross(world up, back) for a level camera
    scale = math.hypot(*right)
    right = tuple(v / scale for v in right)
    up = (
        back[1] * right[2] - back[2] * right[1],
        back[2] * right[0] - back[0] * right[2],
        back[0] * right[1] - back[1] * right[0],
    )
    return [[right[i], up[i], back[i], eye[i]] for i in range(3)] + [[0, 0, 0, 1]]


def test_look_at_matches_the_real_frontal_camera():
    for got, want in zip(look_at((0.0, -3.0, 0.0)), C2W, strict=True):
        assert got == pytest.approx(want)


def synthetic_views(objects, *, to_world):
    """meta.json with three cameras and semantic boxes rendered under ``to_world``.

    Frame names are deliberately stale (as in the real files) and must be ignored.
    """
    locations = [
        {
            "index": f"{k:04d}",
            "transform_matrix": look_at(eye),
            "frames": [{"name": f"render_{(2 - k) * 5:04d}.webp"}],
        }
        for k, eye in enumerate(((0.0, -3.0, 0.0), (-2.1, -2.1, 0.6), (2.1, -2.1, 0.6)))
    ]
    meta = {"camera_angle_x": 0.7, "locations": locations}
    labels = []
    for location in locations:
        found = {}
        for n, (lo, hi) in enumerate(objects.values(), start=1):
            box = projected_box(
                location["transform_matrix"], 0.7, 200, 200, lo, hi, to_world
            )
            if box:
                found[n] = box
        labels.append(found)
    return meta, labels


OBJECTS = {
    "bed": ((-0.6, -0.9, -0.2), (0.4, -0.3, 0.9)),
    "lamp": ((0.3, 0.6, -0.5), (0.6, 0.8, -0.2)),
    "stand": ((0.5, -0.9, 0.5), (0.8, -0.5, 0.8)),
}


def test_camera_report_passes_only_when_the_documented_convention_fits_best():
    meta, labels = synthetic_views(OBJECTS, to_world=gltf_to_camera_world)
    report = camera_report(meta, OBJECTS, labels, width=200, height=200)
    assert report["status"] == "PASS"
    assert report["hypotheses"]["documented"]["median_iou"] == pytest.approx(1.0)
    meta, labels = synthetic_views(OBJECTS, to_world=lambda p: p)
    assert (
        camera_report(meta, OBJECTS, labels, width=200, height=200)["status"] == "FAIL"
    )
    with pytest.raises(MidiAlignmentError):
        camera_report(meta, OBJECTS, labels[:1], width=200, height=200)


def test_topdown_svg_draws_room_ssr_and_midi_boxes():
    svg = topdown_svg(
        {"width_m": 3.0, "depth_m": 4.0, "height_m": 2.6},
        {"o00": ((0.0, 0.5, 0.0), (1.0, 1.0, 2.0))},
        {"bed": ((0.0, 0.5, 0.0), (1.0, 1.0, 2.0))},
    )
    assert svg.startswith("<svg") and svg.count("<rect") == 4
    assert "stroke-dasharray" in svg
    json.dumps(svg)  # plain text, safe to embed in a JSON report


# --------------------------------------------------------------- CLI end to end


def _glb(path, lo, hi):
    """Minimal one-box GLB with an identity node."""
    import struct

    doc = {
        "asset": {"version": "2.0"},
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "accessors": [{"count": 8, "min": list(lo), "max": list(hi)}, {"count": 36}],
    }
    body = json.dumps(doc).encode()
    body += b" " * (-len(body) % 4)
    chunk = struct.pack("<II", len(body), 0x4E4F534A) + body
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(chunk)) + chunk)


def test_midi_audit_cli_on_a_synthetic_room(tmp_path, capsys):
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw

    from archimind.datasets.cli import main
    from archimind.datasets.contracts import (
        PermissionRecord,
        SourceFile,
        SourceManifest,
    )
    from archimind.datasets.pack import build_pack
    from archimind.datasets.ssr_adapter import convert_row

    house, room = "fd9984b0-5f43-40b7-861b-f2cbee90326a", "Bedroom-9575"
    hx, hz = 1.6, 1.5
    corners = [(-hx, hz), (hx, hz), (hx, -hz), (-hx, -hz)]
    ssr_objects = [
        {"jid": BED, "size": [2.36, 1.28, 2.72], "pos": [0.38, 0.0, -0.1], "rot": ZERO},
        {
            "jid": LAMP,
            "size": [0.58, 0.13, 0.58],
            "pos": [0.09, 2.47, -0.13],
            "rot": ZERO,
        },
    ]
    row = {
        "file_id": house + "-893b170a-f755-4b24-bea3-2fdb13048980",
        "splits": ["bedroom_train"],
        "scene": {
            "room_id": room,
            "bounds_bottom": [[x, 0.0, z] for x, z in corners],
            "bounds_top": [[x, 2.6, z] for x, z in corners],
            "objects": ssr_objects,
        },
    }
    scene = convert_row(
        row,
        revision="b606183e56d972f85850125f9191932cbea654c3",
        source_sha256="a" * 64,
        jid_categories={BED: "Bed", LAMP: "Lighting"},
        midi_splits={},
    ).scene
    permission = PermissionRecord(
        local_research="allowed",
        derived_metadata="unknown",
        public_geometry="unknown",
        public_images="unknown",
        provider_disclosure="unknown",
        evidence="synthetic test",
        decided_by="test",
        decided_utc="2026-01-01T00:00:00Z",
    )
    build_pack(
        tmp_path / "pack",
        pack_id="ssr-test",
        audience="local",
        sources=[
            SourceManifest(
                source="ssr_3dfront",
                origin_url="https://huggingface.co/datasets/x/y",
                revision="b606183e56d972f85850125f9191932cbea654c3",
                retrieved_utc="2026-01-01T00:00:00Z",
                files=(
                    SourceFile(
                        path="data/train.parquet", size_bytes=1, sha256="a" * 64
                    ),
                ),
                permission=permission,
            )
        ],
        scenes=[scene],
        exclusions=[],
        assets=[],
        glb_files={},
        transform_version=scene.transform_version,
        category_map_version=scene.category_map_version,
        builder="test",
        created_utc="2026-01-01T00:00:00Z",
    )

    scale, t = 0.7, (0.38, 1.3, -0.1)
    boxes = {}
    for n, o in enumerate(ssr_objects, start=1):
        centre, extent = ssr_world_box(o["size"], o["pos"], o["rot"])
        lo = tuple(
            scale * (c - e / 2 - tt) for c, e, tt in zip(centre, extent, t, strict=True)
        )
        hi = tuple(
            scale * (c + e / 2 - tt) for c, e, tt in zip(centre, extent, t, strict=True)
        )
        name = f"{'Bed' if o['jid'] == BED else 'Lighting'}_{o['jid']}_{n}"
        boxes[name] = (lo, hi)
        _glb(tmp_path / "scene" / house / room / f"{name}.glb", lo, hi)
    _glb(
        tmp_path / "scene" / house / room / "others.glb",
        (-1.2, -0.9, -1.1),
        (1.2, 0.9, 1.1),
    )
    _glb(
        tmp_path / "scene" / house / f"{room}.glb",
        (-0.8, -0.9, -0.95),
        (0.8, 0.9, 0.95),
    )
    _glb(
        tmp_path / "scene" / house / f"{room}_full.glb",
        (-1.2, -0.9, -1.1),
        (1.2, 0.9, 1.1),
    )

    views = tmp_path / "render" / house / room
    views.mkdir(parents=True)
    eyes = ((0.0, -3.0, 0.0), (-2.1, -2.1, 0.6))
    meta = {
        "camera_angle_x": 0.7,
        "locations": [
            {
                "index": f"{k:04d}",
                "transform_matrix": look_at(e),
                "frames": [{"name": f"render_{17 - k:04d}.webp"}],
            }
            for k, e in enumerate(eyes)
        ],
    }
    (views / "meta.json").write_text(json.dumps(meta))
    for k, location in enumerate(meta["locations"]):
        image = Image.new("L", (128, 128), 0)
        draw = ImageDraw.Draw(image)
        for label, (lo, hi) in enumerate(boxes.values(), start=1):
            box = projected_box(location["transform_matrix"], 0.7, 128, 128, lo, hi)
            if box:
                draw.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], fill=label)
        image.save(views / f"semantic_{k:04d}.png")

    midi = tmp_path / "midi"
    midi.mkdir()
    rooms = [f"{house}/{room}"] + [f"{house}/Bedroom-{i}" for i in range(999)]
    furniture = [list(boxes)] + [[] for _ in range(999)]
    (midi / "midi_room_ids.json").write_text(json.dumps(rooms))
    (midi / "midi_furniture_ids.json").write_text(json.dumps(furniture))
    (midi / "midi_test_room_ids.json").write_text(json.dumps(rooms))

    code = main(
        [
            "midi-audit",
            "--scene-root",
            str(tmp_path / "scene"),
            "--render-root",
            str(tmp_path / "render"),
            "--midi-dir",
            str(midi),
            "--ssr-pack",
            str(tmp_path / "pack"),
            "--out",
            str(tmp_path / "audit"),
        ]
    )
    summary = json.loads(capsys.readouterr().out)
    assert code == 0, summary
    assert summary["alignment"] == {"PASS": 1} and summary["camera"] == {"PASS": 1}
    assert summary["association_clean"] == 1
    report = json.loads((tmp_path / "audit" / "report.json").read_text())
    (room_report,) = report["rooms"]
    assert (
        room_report["midi_split"] == "test" and room_report["ssr"]["split"] == "train"
    )
    assert room_report["alignment"]["scale_midi_per_m"] == pytest.approx(scale)
    assert room_report["modalities"]["depth"] == "absent"
    assert room_report["views"]["kinds"]["render"]["missing"] == [0, 1]
    assert (tmp_path / "audit" / "overlays" / f"{house}_{room}.svg").is_file()

    # A non-empty output directory is refused.
    assert (
        main(
            [
                "midi-audit",
                "--scene-root",
                str(tmp_path / "scene"),
                "--render-root",
                str(tmp_path / "render"),
                "--midi-dir",
                str(midi),
                "--ssr-pack",
                str(tmp_path / "pack"),
                "--out",
                str(tmp_path / "audit"),
            ]
        )
        == 1
    )


def test_camera_report_requires_distinguishing_observations():
    meta, labels = synthetic_views(OBJECTS, to_world=gltf_to_camera_world)
    for objects, observed in [({}, labels), (OBJECTS, [{} for _ in labels])]:
        report = camera_report(meta, objects, observed, width=200, height=200)
        assert report["status"] == "NOT_VERIFIABLE"
        assert report["best"] is None
    # A single frame cannot distinguish the two index rules, even with perfect overlap.
    report = camera_report(
        {**meta, "locations": meta["locations"][:1]},
        OBJECTS,
        labels[:1],
        width=200,
        height=200,
    )
    assert report["status"] == "NOT_VERIFIABLE"
