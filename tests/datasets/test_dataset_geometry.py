import math

import pytest

from archimind.datasets.geometry import (
    IDENTITY,
    Y_UP_TO_Z_UP,
    Convention,
    GeometryError,
    apply,
    canonical_rotation,
    check_rigid,
    classify,
    normalize_quaternion,
    object_box,
    quaternion_matrix,
)

Y_UP = Convention(
    name="synthetic-y-up",
    basis=Y_UP_TO_Z_UP,
    quaternion_order="xyzw",
    pivot="center",
    size_semantics="full_extent",
)


def yaw_about_source_y(deg: float) -> tuple[float, float, float, float]:
    half = math.radians(deg) / 2
    return (0.0, math.sin(half), 0.0, math.cos(half))


def test_basis_is_a_proper_rotation_and_mirrors_are_rejected():
    check_rigid(Y_UP_TO_Z_UP)
    check_rigid(IDENTITY)
    with pytest.raises(GeometryError):
        check_rigid(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)))  # det -1
    with pytest.raises(GeometryError):
        check_rigid(((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))


def test_basis_maps_source_axes_to_canonical_axes():
    assert apply(Y_UP_TO_Z_UP, (0.0, 1.0, 0.0)) == (0.0, 0.0, 1.0)  # up stays up
    assert apply(Y_UP_TO_Z_UP, (1.0, 0.0, 0.0)) == (1.0, 0.0, 0.0)
    assert apply(Y_UP_TO_Z_UP, (0.0, 0.0, 1.0)) == (0.0, -1.0, 0.0)


def test_translation_lower_left_and_floor_anchor():
    # Source room spans X in [2, 6], Z in [-1, 3]; floor at Y = 0.1. The canonical
    # origin is (minX, floorY, maxZ) so canonical y = maxZ - Z (handoff basis).
    box = object_box(
        Y_UP,
        size=(1.0, 0.5, 2.0),
        position=(3.0, 0.35, 1.0),
        rotation=(0.0, 0.0, 0.0, 1.0),
        origin=(2.0, 0.1, 3.0),
    )
    assert box.quarter_turns == 0
    assert math.isclose(box.width_m, 1.0) and math.isclose(box.depth_m, 2.0)
    assert math.isclose(box.x_m, 0.5)  # centre x 1.0 - 0.5
    assert math.isclose(box.y_m, 1.0)  # centre y (3 - 1) - 1.0
    assert math.isclose(box.bottom_z_m, 0.0, abs_tol=1e-12)
    assert math.isclose(box.height_m, 0.5)


def test_quaternion_sign_and_order_equivalence():
    q = yaw_about_source_y(90)
    neg = tuple(-c for c in q)
    assert normalize_quaternion(q, "xyzw") == pytest.approx(
        normalize_quaternion(neg, "xyzw")
    )
    wxyz = (q[3], q[0], q[1], q[2])
    assert normalize_quaternion(wxyz, "wxyz") == pytest.approx(
        normalize_quaternion(q, "xyzw")
    )
    scaled = tuple(3 * c for c in q)
    assert normalize_quaternion(scaled, "xyzw") == pytest.approx(
        normalize_quaternion(q, "xyzw")
    )


@pytest.mark.parametrize("deg,turns", [(0, 0), (90, 1), (180, 2), (270, 3), (-90, 3)])
def test_quarter_turns_about_up_axis(deg, turns):
    q = normalize_quaternion(yaw_about_source_y(deg), "xyzw")
    orientation = classify(canonical_rotation(Y_UP_TO_Z_UP, quaternion_matrix(q)))
    assert orientation.quarter_turns == turns
    assert orientation.tilt_deg == pytest.approx(0.0, abs=1e-6)


def test_quarter_turn_swaps_footprint_extents():
    box = object_box(
        Y_UP,
        size=(1.0, 0.5, 2.0),
        position=(0.0, 0.25, 0.0),
        rotation=yaw_about_source_y(90),
        origin=(-5.0, 0.0, 5.0),
    )
    assert box.quarter_turns == 1
    assert math.isclose(box.width_m, 2.0) and math.isclose(box.depth_m, 1.0)


def test_non_quarter_yaw_and_tilt_are_rejected_not_snapped():
    with pytest.raises(GeometryError, match="non_quarter_turn_rotation"):
        object_box(
            Y_UP,
            size=(1, 1, 1),
            position=(0, 0.5, 0),
            rotation=yaw_about_source_y(45),
            origin=(-5, 0, 5),
        )
    half = math.radians(10) / 2
    tilted = (math.sin(half), 0.0, 0.0, math.cos(half))  # 10 degrees about X
    with pytest.raises(GeometryError, match="tilted_object"):
        object_box(
            Y_UP,
            size=(1, 1, 1),
            position=(0, 0.5, 0),
            rotation=tilted,
            origin=(-5, 0, 5),
        )


def test_small_noise_within_tolerance_is_a_quarter_turn():
    box = object_box(
        Y_UP,
        size=(1, 1, 1),
        position=(0, 0.5, 0),
        rotation=yaw_about_source_y(90.2),
        origin=(-5, 0, 5),
    )
    assert box.quarter_turns == 1


@pytest.mark.parametrize(
    "q", [(0.0, 0.0, 0.0, 0.0), (float("nan"), 0.0, 0.0, 1.0), (1.0, 0.0, 0.0)]
)
def test_invalid_quaternions_are_rejected(q):
    with pytest.raises(GeometryError):
        normalize_quaternion(q, "xyzw")


def test_half_extent_and_bottom_pivot_conventions_are_explicit():
    half = Convention("half", Y_UP_TO_Z_UP, "xyzw", "bottom_center", "half_extent")
    box = object_box(
        half,
        size=(0.5, 0.25, 1.0),
        position=(1.0, 0.0, -1.0),
        rotation=(0, 0, 0, 1),
        origin=(0.0, 0.0, 0.0),
    )
    assert (box.width_m, box.depth_m, box.height_m) == (1.0, 2.0, 0.5)
    assert box.bottom_z_m == 0.0
    assert half.version_digest != Y_UP.version_digest


def test_invalid_size_is_rejected():
    with pytest.raises(GeometryError):
        object_box(
            Y_UP,
            size=(0.0, 1.0, 1.0),
            position=(0, 0, 0),
            rotation=(0, 0, 0, 1),
            origin=(0, 0, 0),
        )
