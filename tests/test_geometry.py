"""Real-geometry tests for Task 04A; no UI, placement, or network services."""

import json

import pytest
from pydantic import ValidationError
from shapely import Polygon

from archimind.examples import create_sample_bedroom
from archimind.geometry import (
    DEFAULT_AREA_TOLERANCE_M2,
    SpatialValidationReport,
    SpatialViolation,
    UnsupportedGeometryError,
    furniture_footprint,
    room_footprint,
    validate_layout,
)
from archimind.models import Furniture, Room, RoomDesign


def _item(identifier: str = "a", **changes: object) -> Furniture:
    data = {
        "id": identifier,
        "name": f"Item {identifier}",
        "category": "test",
        "x_m": 1.0,
        "y_m": 1.0,
        "width_m": 1.0,
        "depth_m": 1.0,
        "height_m": 0.8,
    }
    return Furniture.model_validate({**data, **changes})


def _layout(*items: Furniture) -> RoomDesign:
    return RoomDesign(
        room=Room(id="room", name="Test", width_m=5, depth_m=4, ceiling_height_m=2.7),
        furniture=list(items),
    )


def test_footprints_preserve_lower_left_coordinates_and_dimensions() -> None:
    footprint = furniture_footprint(_item(x_m=1.2, y_m=0.8, width_m=1.6, depth_m=2))
    assert isinstance(footprint, Polygon)
    assert footprint.bounds == pytest.approx((1.2, 0.8, 2.8, 2.8))
    assert footprint.area == pytest.approx(3.2)
    room = room_footprint(_layout().room)
    assert room.bounds == (0, 0, 5, 4)
    assert room.area == 20


def test_sample_bedroom_passes_implemented_checks_only() -> None:
    report = validate_layout(create_sample_bedroom())
    assert report.status == "passed"
    assert report.violations == []
    assert report.scope == "task_04a_containment_and_overlap"
    assert report.area_tolerance_m2 == DEFAULT_AREA_TOLERANCE_M2


@pytest.mark.parametrize(("x", "y"), [(0, 1), (4, 1), (1, 0), (1, 3), (0, 0), (4, 3)])
def test_wall_and_corner_contact_is_allowed(x: float, y: float) -> None:
    assert validate_layout(_layout(_item(x_m=x, y_m=y))).status == "passed"


def test_furniture_can_fill_entire_room() -> None:
    report = validate_layout(_layout(_item(x_m=0, y_m=0, width_m=5, depth_m=4)))
    assert report.status == "passed"


@pytest.mark.parametrize(
    ("x", "y", "outside_area"),
    [
        (4.5, 1, 0.5),
        (-0.5, 1, 0.5),
        (1, 3.5, 0.5),
        (1, -0.5, 0.5),
        (4.5, 3.5, 0.75),
        (6, 1, 1.0),
        (-2, -2, 1.0),
    ],
    ids=[
        "east",
        "west",
        "north",
        "south",
        "northeast",
        "fully-outside",
        "negative-outside",
    ],
)
def test_room_boundary_violations(x: float, y: float, outside_area: float) -> None:
    report = validate_layout(_layout(_item(x_m=x, y_m=y)))
    assert report.status == "failed"
    assert len(report.violations) == 1
    issue = report.violations[0]
    assert issue.violation_type == "out_of_bounds"
    assert issue.furniture_ids == ["a"]
    assert "'a'" in issue.message and "'room'" in issue.message
    assert issue.measurements["outside_area_m2"] == pytest.approx(outside_area)


def test_tiny_outside_area_is_not_hidden_by_collision_tolerance() -> None:
    report = validate_layout(_layout(_item(x_m=-5e-10)))
    assert report.status == "failed"
    assert report.violations[0].violation_type == "out_of_bounds"


@pytest.mark.parametrize(
    ("first", "second", "expected_area"),
    [
        (_item("a", width_m=2, depth_m=2), _item("b", x_m=2, y_m=2), 1.0),
        (_item("a"), _item("b"), 1.0),
        (
            _item("a", width_m=2, depth_m=2),
            _item("b", x_m=1.5, y_m=1.5, width_m=0.5, depth_m=0.5),
            0.25,
        ),
    ],
    ids=["partial", "identical", "one-inside-another"],
)
def test_positive_area_overlap(
    first: Furniture, second: Furniture, expected_area: float
) -> None:
    report = validate_layout(_layout(first, second))
    assert report.status == "failed"
    issue = report.violations[0]
    assert issue.violation_type == "furniture_overlap"
    assert issue.furniture_ids == ["a", "b"]
    assert "'a'" in issue.message and "'b'" in issue.message
    assert issue.measurements["overlap_area_m2"] == pytest.approx(expected_area)


def test_every_colliding_pair_is_reported() -> None:
    report = validate_layout(_layout(_item("c"), _item("a"), _item("b")))
    assert report.status == "failed"
    assert [issue.furniture_ids for issue in report.violations] == [
        ["a", "b"],
        ["a", "c"],
        ["b", "c"],
    ]


def test_containment_and_collision_are_both_reported() -> None:
    report = validate_layout(_layout(_item("b", x_m=4.75), _item("a", x_m=4.5)))
    assert [
        (issue.violation_type, issue.furniture_ids) for issue in report.violations
    ] == [
        ("out_of_bounds", ["a"]),
        ("out_of_bounds", ["b"]),
        ("furniture_overlap", ["a", "b"]),
    ]


@pytest.mark.parametrize(("x", "y"), [(2, 1), (1, 2), (2, 2), (2.001, 1)])
def test_edge_corner_contact_and_separation_are_not_collisions(
    x: float, y: float
) -> None:
    report = validate_layout(_layout(_item("a"), _item("b", x_m=x, y_m=y)))
    assert report.status == "passed"
    assert report.violations == []


@pytest.mark.parametrize(("area", "expected"), [(5e-10, "passed"), (2e-9, "failed")])
def test_documented_overlap_area_tolerance(area: float, expected: str) -> None:
    report = validate_layout(_layout(_item("a"), _item("b", x_m=2 - area)))
    assert report.status == expected


def test_custom_tolerance_boundary_and_zero_tolerance() -> None:
    design = _layout(_item("a"), _item("b", x_m=1.75))
    assert validate_layout(design, area_tolerance_m2=0.25).status == "passed"
    assert validate_layout(design, area_tolerance_m2=0.249).status == "failed"
    tiny = _layout(_item("a"), _item("b", x_m=2 - 5e-10))
    assert validate_layout(tiny, area_tolerance_m2=0).status == "failed"


def test_decimal_endpoints_do_not_create_false_boundary_violations() -> None:
    design = RoomDesign(
        room=Room(
            id="room", name="Decimal", width_m=5.1, depth_m=4.1, ceiling_height_m=2.7
        ),
        furniture=[_item(x_m=4.2, y_m=3.2, width_m=0.9, depth_m=0.9)],
    )
    assert validate_layout(design).status == "passed"
    touching = _layout(
        _item("a", x_m=0.1, width_m=0.2), _item("b", x_m=0.3, width_m=0.2)
    )
    assert validate_layout(touching, area_tolerance_m2=0).status == "passed"
    assert furniture_footprint(touching.furniture[0]).bounds[2] == 0.3


def test_empty_furniture_list() -> None:
    assert validate_layout(_layout()).status == "passed"


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_unsupported_rotations_never_pass(rotation: int) -> None:
    item = _item(rotation_deg=rotation)
    before = item.model_dump_json()
    with pytest.raises(UnsupportedGeometryError, match="only 0-degree"):
        furniture_footprint(item)
    report = validate_layout(_layout(item))
    assert report.status == "unverified"
    assert report.violations[0].violation_type == "unsupported_geometry"
    assert report.violations[0].furniture_ids == ["a"]
    assert report.violations[0].measurements["rotation_deg"] == rotation
    assert item.model_dump_json() == before


def test_supported_items_are_checked_when_another_item_is_unsupported() -> None:
    report = validate_layout(
        _layout(_item("z", rotation_deg=90), _item("a"), _item("b"), _item("c", x_m=6))
    )
    assert report.status == "unverified"
    assert [
        (issue.violation_type, issue.furniture_ids) for issue in report.violations
    ] == [
        ("unsupported_geometry", ["z"]),
        ("out_of_bounds", ["c"]),
        ("furniture_overlap", ["a", "b"]),
    ]


@pytest.mark.parametrize(
    "changes",
    [
        {"x_m": 1e308},
        {"x_m": 1e308, "width_m": 1e308},
        {"width_m": 1e-200, "depth_m": 1e-200, "x_m": 0, "y_m": 0},
        {"width_m": 1e200, "depth_m": 1e200, "x_m": 0, "y_m": 0},
    ],
    ids=["lost-precision", "coordinate-overflow", "area-underflow", "area-overflow"],
)
def test_unrepresentable_furniture_geometry_is_reported(changes: dict) -> None:
    report = validate_layout(_layout(_item(**changes)))
    assert report.status == "unverified"
    assert report.violations[0].violation_type == "unsupported_geometry"
    json.dumps(report.model_dump(), allow_nan=False)


def test_unsupported_room_geometry_still_allows_supported_pair_checks() -> None:
    design = RoomDesign(
        room=Room(
            id="huge", name="Huge", width_m=1e200, depth_m=1e200, ceiling_height_m=3
        ),
        furniture=[_item("a"), _item("b")],
    )
    report = validate_layout(design)
    assert report.status == "unverified"
    assert report.room_id == "huge"
    assert report.violations[0].furniture_ids == []
    assert "Room 'huge'" in report.violations[0].message
    assert report.violations[1].violation_type == "furniture_overlap"


@pytest.mark.parametrize("case", ["valid", "invalid", "unsupported"])
def test_report_json_round_trip(case: str) -> None:
    design = {
        "valid": create_sample_bedroom(),
        "invalid": _layout(_item("a"), _item("b"), _item("c", x_m=-2)),
        "unsupported": _layout(_item(rotation_deg=90)),
    }[case]
    report = validate_layout(design)
    payload = report.model_dump_json()
    assert SpatialValidationReport.model_validate_json(payload) == report
    assert json.loads(payload) == report.model_dump(mode="json")
    json.dumps(report.model_dump(), allow_nan=False)


def test_results_are_deterministic_and_input_is_unchanged() -> None:
    design = _layout(
        _item("c", x_m=6), _item("b"), _item("a"), _item("z", rotation_deg=90)
    )
    before = design.model_dump_json()
    first = validate_layout(design).model_dump_json()
    assert validate_layout(design).model_dump_json() == first
    assert design.model_dump_json() == before
    data = design.model_dump()
    data["furniture"].reverse()
    assert validate_layout(RoomDesign.model_validate(data)).model_dump_json() == first


@pytest.mark.parametrize(
    "tolerance", [-1, float("nan"), float("inf"), -float("inf"), True, "0.1"]
)
def test_invalid_tolerance_is_rejected(tolerance: object) -> None:
    with pytest.raises(ValueError, match="area_tolerance_m2"):
        validate_layout(_layout(), area_tolerance_m2=tolerance)


def test_invalid_mutated_canonical_schema_raises_validation_error() -> None:
    design = _layout(_item())
    design.furniture[0].width_m = -1
    with pytest.raises(ValidationError, match="width_m"):
        validate_layout(design)


def test_report_cannot_claim_passed_with_violations() -> None:
    issue = SpatialViolation(
        violation_type="out_of_bounds", furniture_ids=["a"], message="Outside room"
    )
    with pytest.raises(ValidationError, match="Status must agree"):
        SpatialValidationReport(room_id="room", status="passed", violations=[issue])
    with pytest.raises(ValidationError, match="Status must agree"):
        SpatialValidationReport(room_id="room", status="unverified")


def test_violation_pair_ids_and_measurements_are_validated() -> None:
    with pytest.raises(ValidationError, match="number of furniture IDs"):
        SpatialViolation(
            violation_type="furniture_overlap", furniture_ids=["a"], message="Bad"
        )
    with pytest.raises(ValidationError):
        SpatialViolation(
            violation_type="out_of_bounds",
            furniture_ids=["a"],
            message="Bad",
            measurements={"outside_area_m2": float("inf")},
        )


def test_door_clearance_is_not_part_of_passed_scope() -> None:
    sample = create_sample_bedroom()
    design = RoomDesign(
        room=sample.room,
        furniture=[
            _item(x_m=sample.room.doors[0].offset_m, y_m=0, width_m=0.8, depth_m=0.8)
        ],
    )
    report = validate_layout(design)
    assert report.status == "passed"
    assert report.scope == "task_04a_containment_and_overlap"
