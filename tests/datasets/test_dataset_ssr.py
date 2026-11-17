import math

import pytest

from archimind.datasets.geometry import GeometryError
from archimind.datasets.ssr import (
    SSR_CONVENTION,
    classify_room,
    object_box,
    probe,
    profile_row,
    room_key,
    room_type_split,
)

HOUSE = "62a36664-15ed-4930-839a-0964bdc11d45"
FILE_ID = HOUSE + "-893b170a-f755-4b24-bea3-2fdb13048980"


def rect(w=3.3, d=3.9, h=2.6):
    hx, hz = w / 2, d / 2
    corners = [(-hx, hz), (hx, hz), (hx, -hz), (-hx, -hz)]
    return [[x, 0.0, z] for x, z in corners], [[x, h, z] for x, z in corners]


def yaw(deg):
    half = math.radians(deg) / 2
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def obj(pos, size=(1.0, 0.5, 2.0), deg=0.0, jid="jid-1"):
    return {
        "desc": "IGNORED text",
        "jid": jid,
        "pos": list(pos),
        "size": list(size),
        "rot": yaw(deg),
    }


def row(objects, *, splits=("bedroom_train",), bounds=None, file_id=FILE_ID):
    bottom, top = bounds or rect()
    return {
        "file_id": file_id,
        "room_type": "bedroom",
        "splits": list(splits),
        "scene": {
            "bounds_bottom": bottom,
            "bounds_top": top,
            "objects": objects,
            "room_id": "SecondBedroom-1443",
            "room_type": "bedroom",
        },
    }


def test_conventions_are_the_proven_respace_ones():
    assert SSR_CONVENTION.pivot == "bottom_center"
    assert SSR_CONVENTION.size_semantics == "full_extent"
    assert SSR_CONVENTION.quaternion_order == "xyzw"


def test_rectangular_room_frame_and_origin():
    frame, reason = classify_room(*rect(3.3, 3.9, 2.6))
    assert reason is None
    assert (frame.width_m, frame.depth_m) == pytest.approx((3.3, 3.9))
    assert frame.height_m == pytest.approx(2.6)
    assert frame.origin == pytest.approx((-1.65, 0.0, 1.95))  # (minX, floorY, maxZ)


@pytest.mark.parametrize(
    "bottom,top,reason",
    [
        (
            [[0, 0, 0], [2, 0, 0], [2, 0, 1], [1, 0, 1], [1, 0, 2], [0, 0, 2]],
            [[0, 2, 0], [2, 2, 0], [2, 2, 1], [1, 2, 1], [1, 2, 2], [0, 2, 2]],
            "irregular_room",
        ),
        (
            [[0, 0, 0], [2, 0, 0.1], [2, 0, 1], [0, 0, 1]],
            [[0, 2, 0], [2, 2, 0.1], [2, 2, 1], [0, 2, 1]],
            "irregular_room",
        ),
        (
            [[0, 0, 0], [2, 0.2, 0], [2, 0, 1], [0, 0, 1]],
            [[0, 2, 0], [2, 2, 0], [2, 2, 1], [0, 2, 1]],
            "non_planar_floor_or_ceiling",
        ),
        (
            [[0, 0, 0], [2, 0, 0], [2, 0, 1], [0, 0, 1]],
            [[0, 0, 0], [2, 0, 0], [2, 0, 1], [0, 0, 1]],
            "invalid_dimensions",
        ),
        ([[0, 0, "x"]], [[0, 2, 0]], "malformed_record"),
        ([[0, 0, float("nan")]], [[0, 2, 0]], "malformed_record"),
    ],
)
def test_room_rejections(bottom, top, reason):
    assert classify_room(bottom, top) == (None, reason)


def test_bottom_center_pivot_maps_to_lower_left_on_the_floor():
    frame, _ = classify_room(*rect(4.0, 4.0, 2.6))
    box = object_box(frame, obj((0.0, 0.0, 0.0), size=(1.0, 0.5, 2.0)))
    assert (box.x_m, box.y_m) == pytest.approx((1.5, 1.0))
    assert box.bottom_z_m == pytest.approx(0.0)
    assert (box.width_m, box.depth_m, box.height_m) == pytest.approx((1.0, 2.0, 0.5))


def test_source_plus_z_maps_to_canonical_south():
    frame, _ = classify_room(*rect(4.0, 4.0, 2.6))
    north = object_box(frame, obj((0.0, 0.0, -1.0), size=(0.5, 0.5, 0.5)))
    south = object_box(frame, obj((0.0, 0.0, 1.0), size=(0.5, 0.5, 0.5)))
    assert north.y_m > south.y_m


def test_malformed_object_raises_reason_code():
    frame, _ = classify_room(*rect())
    with pytest.raises(GeometryError, match="malformed_record"):
        object_box(frame, {"pos": [0, 0], "size": [1, 1, 1], "rot": [0, 0, 0, 1]})


@pytest.mark.parametrize(
    "splits,expected",
    [
        (["bedroom_train", "all_val"], "train"),
        (["all_val"], None),
        (["livingroom_val"], None),
        (["bedroom_val", "bedroom_test"], "conflict"),
        (["bedroom_weird"], "unknown"),
        (None, None),
    ],
)
def test_room_type_split_ignores_the_combined_split(splits, expected):
    assert room_type_split(splits) == expected


def test_room_key_matches_midi_identity():
    assert room_key(FILE_ID, "SecondBedroom-1443") == f"{HOUSE}/SecondBedroom-1443"
    with pytest.raises(ValueError):
        room_key("not-a-uuid", "Bedroom-1")
    with pytest.raises(ValueError):
        room_key(FILE_ID, "")


def test_tiers():
    canonical = profile_row(row([obj((0.0, 0.0, 0.0))]))
    assert canonical.tier == "canonical"
    quarter = profile_row(row([obj((0.0, 0.0, 0.0), deg=90)]))
    assert quarter.tier == "reference_only" and quarter.turns == (1,)
    mixed = profile_row(row([obj((0.0, 0.0, 0.0)), obj((0.5, 0.0, 1.0), deg=45)]))
    assert mixed.tier == "reference_only"
    assert mixed.object_reasons == ("non_quarter_turn_rotation",)
    only_bad = profile_row(row([obj((0.0, 0.0, 0.0), deg=30)]))
    assert only_bad.tier == "excluded:no_admitted_object"
    irregular = profile_row(
        row([obj((0, 0, 0))], bounds=([[0, 0, 0]] * 3, [[0, 2, 0]] * 3))
    )
    assert irregular.tier.startswith("excluded:")
    assert profile_row(row([obj((0, 0, 0))], splits=["livingroom_train"])) is None


def test_wall_protrusion_and_overlap_keep_rooms_out_of_canonical():
    through_wall = profile_row(row([obj((1.4, 0.0, 0.0), size=(1.0, 0.5, 1.0))]))
    assert through_wall.outside == 1 and through_wall.tier == "reference_only"
    assert through_wall.max_protrusion_m == pytest.approx(0.25)
    stacked = profile_row(row([obj((0, 0, 0)), obj((0.2, 0.0, 0.2), jid="jid-2")]))
    assert stacked.solid_overlaps == 1 and stacked.tier == "reference_only"
    lamp_above_bed = profile_row(
        row([obj((0, 0, 0)), obj((0.0, 2.0, 0.0), size=(0.4, 0.3, 0.4), jid="lamp")])
    )
    assert lamp_above_bed.footprint_overlaps == 1
    assert lamp_above_bed.solid_overlaps == 0 and lamp_above_bed.floating == 1


def test_descriptions_never_enter_the_profile():
    profile = profile_row(row([obj((0, 0, 0))]))
    assert "IGNORED" not in repr(profile)


def test_probe_is_order_independent_and_counts_duplicates():
    a = profile_row(row([obj((0, 0, 0))]))
    b = profile_row(
        row(
            [obj((0, 0, 0))],
            splits=["bedroom_test"],
            file_id=HOUSE + "-00000000-0000-0000-0000-000000000000",
        )
    )
    c = profile_row(row([obj((0, 0, 0), deg=90)]))
    first, second = probe([a, b, c]), probe([c, b, a])
    assert first == second
    assert first["identity"]["duplicate_geometry"] == 1
    assert first["identity"]["duplicate_geometry_across_splits"] == 1
    assert first["tiers"] == {"canonical": 2, "reference_only": 1}
