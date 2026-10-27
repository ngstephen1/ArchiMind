"""Deterministic Task 04B checks using real geometry, without network services."""

import json

import pytest
from pydantic import ValidationError

from archimind.examples import create_sample_bedroom
from archimind.geometry import (
    MAX_ACCESSIBILITY_OBJECTS,
    AccessibilityConfig,
    AccessibilityIssue,
    AccessibilityValidationReport,
    SpatialValidationReport,
    validate_accessibility,
    validate_layout,
)
from archimind.models import Door, Furniture, Room, RoomDesign


def _door(identifier: str = "entry", **changes: object) -> Door:
    return Door.model_validate(
        {
            "id": identifier,
            "wall": "south",
            "offset_m": 1.0,
            "width_m": 1.0,
            "height_m": 2.1,
            **changes,
        }
    )


def _item(identifier: str = "item", **changes: object) -> Furniture:
    return Furniture.model_validate(
        {
            "id": identifier,
            "name": identifier,
            "category": "test",
            "x_m": 3.0,
            "y_m": 2.0,
            "width_m": 0.5,
            "depth_m": 0.5,
            "height_m": 1.0,
            **changes,
        }
    )


def _design(
    *items: Furniture, doors: list[Door] | None = None, **room_changes: object
) -> RoomDesign:
    return RoomDesign(
        room=Room.model_validate(
            {
                "id": "room",
                "name": "Test room",
                "width_m": 5.0,
                "depth_m": 4.0,
                "ceiling_height_m": 2.7,
                "doors": [_door()] if doors is None else doors,
                **room_changes,
            }
        ),
        furniture=list(items),
    )


def _issues(report: AccessibilityValidationReport, kind: str) -> list:
    return [issue for issue in report.violations if issue.violation_type == kind]


def test_empty_room_has_unobstructed_door_and_connected_usable_space() -> None:
    report = validate_accessibility(_design())
    assert isinstance(report, SpatialValidationReport)
    assert report.scope == "task_04b_accessibility"
    assert report.status == "passed"
    assert report.violations == []
    assert all(check.status == "passed" for check in report.checks.values())
    result = report.checks["circulation"].measurements
    assert result["usable_region_count"] == 1
    assert result["usable_center_area_m2"] == pytest.approx(4.4 * 3.4)


def test_blocked_entrance_identifies_every_blocking_object() -> None:
    design = _design(
        _item("b", x_m=1.5, y_m=0.0, depth_m=0.2),
        _item("a", x_m=1.0, y_m=0.0, depth_m=0.2),
    )
    report = validate_accessibility(design)
    assert report.status == "failed"
    blocked = _issues(report, "blocked_door")
    assert [issue.furniture_ids for issue in blocked] == [["a"], ["b"]]
    assert all(issue.door_ids == ["entry"] for issue in blocked)
    assert all(issue.severity == "error" for issue in blocked)
    assert report.checks["circulation"].status == "failed"
    # The old API deliberately retains its original containment/overlap scope.
    assert validate_layout(design).status == "passed"


@pytest.mark.parametrize("y", [0.9, 0.900001, 1.2])
def test_furniture_outside_or_touching_advisory_zone_is_not_reported(y: float) -> None:
    report = validate_accessibility(_design(_item(x_m=1.0, y_m=y)))
    assert not _issues(report, "blocked_door")
    assert not _issues(report, "door_clearance_warning")
    assert report.status == "passed"


def test_advisory_only_intrusion_does_not_fail_an_otherwise_clear_design() -> None:
    report = validate_accessibility(_design(_item(x_m=1.0, y_m=0.7)))
    assert report.status == "passed"
    assert not _issues(report, "blocked_door")
    warning = _issues(report, "door_clearance_warning")[0]
    assert warning.severity == "warning"
    assert warning.furniture_ids == ["item"]
    assert warning.door_ids == ["entry"]
    assert warning.measurements["intersection_area_m2"] == pytest.approx(0.1)


def test_contact_with_required_zone_is_advisory_not_strict() -> None:
    report = validate_accessibility(_design(_item(x_m=1.0, y_m=0.3)))
    assert not _issues(report, "blocked_door")
    assert len(_issues(report, "door_clearance_warning")) == 1


def test_any_positive_required_intrusion_is_not_hidden_by_overlap_tolerance() -> None:
    report = validate_accessibility(
        _design(_item(x_m=1.0, y_m=0.3 - 1e-10)), area_tolerance_m2=1.0
    )
    assert _issues(report, "blocked_door")


@pytest.mark.parametrize(
    ("wall", "x", "y", "width", "depth"),
    [
        ("south", 1.0, 0.0, 1.0, 0.2),
        ("north", 1.0, 3.8, 1.0, 0.2),
        ("west", 0.0, 1.0, 0.2, 1.0),
        ("east", 4.8, 1.0, 0.2, 1.0),
    ],
)
def test_wall_offsets_and_inward_direction(
    wall: str, x: float, y: float, width: float, depth: float
) -> None:
    door = _door(wall=wall)
    assert validate_accessibility(_design(doors=[door])).status == "passed"
    report = validate_accessibility(
        _design(_item(x_m=x, y_m=y, width_m=width, depth_m=depth), doors=[door])
    )
    blocked = _issues(report, "blocked_door")
    assert len(blocked) == 1
    assert blocked[0].measurements["intersection_area_m2"] == pytest.approx(0.2)
    assert report.checks["circulation"].status == "failed"


@pytest.mark.parametrize("wall", ["south", "north", "east", "west"])
@pytest.mark.parametrize("at_end", [False, True])
def test_corner_entrances_clip_advisory_zone_without_false_failure(
    wall: str, at_end: bool
) -> None:
    wall_length = 5.0 if wall in ("south", "north") else 4.0
    offset = wall_length - 0.8 if at_end else 0.0
    report = validate_accessibility(
        _design(doors=[_door(wall=wall, offset_m=offset, width_m=0.8)])
    )
    assert report.status == "passed"
    assert report.checks["circulation"].measurements["inaccessible_door_count"] == 0


def test_clipped_corner_zone_still_detects_furniture() -> None:
    report = validate_accessibility(
        _design(_item(x_m=0.0, y_m=0.0), doors=[_door(offset_m=0.0)])
    )
    assert len(_issues(report, "blocked_door")) == 1


def test_wall_to_wall_barrier_disconnects_usable_regions() -> None:
    report = validate_accessibility(
        _design(_item(x_m=0.0, y_m=1.8, width_m=5.0, depth_m=0.4))
    )
    assert not _issues(report, "blocked_door")
    assert report.checks["door_clearance"].status == "passed"
    assert report.checks["circulation"].status == "failed"
    issue = _issues(report, "circulation_disconnected")[0]
    assert issue.measurements["usable_region_count"] == 2


@pytest.mark.parametrize(
    ("gap", "expected"), [(0.5, "failed"), (0.6, "failed"), (0.7, "passed")]
)
def test_narrow_passage_and_conservative_exact_width_pinches(
    gap: float, expected: str
) -> None:
    report = validate_accessibility(
        _design(_item(x_m=0.0, y_m=1.8, width_m=5.0 - gap, depth_m=0.4))
    )
    assert report.checks["circulation"].status == expected


def test_clearance_configuration_changes_narrow_passage_result() -> None:
    design = _design(_item(x_m=0.0, y_m=1.8, width_m=4.5, depth_m=0.4))
    assert validate_accessibility(design).checks["circulation"].status == "failed"
    assert (
        validate_accessibility(
            design, config=AccessibilityConfig(walking_clearance_m=0.4)
        )
        .checks["circulation"]
        .status
        == "passed"
    )


def test_alternative_route_around_central_furniture_is_reachable() -> None:
    report = validate_accessibility(
        _design(_item(x_m=0.8, y_m=1.8, width_m=3.4, depth_m=0.4))
    )
    assert report.status == "passed"
    assert report.checks["circulation"].measurements["usable_region_count"] == 1


def test_multiple_doors_can_reach_one_connected_region() -> None:
    report = validate_accessibility(
        _design(doors=[_door("south"), _door("north", wall="north")])
    )
    assert report.status == "passed"


def test_one_good_door_does_not_hide_another_blocked_door() -> None:
    report = validate_accessibility(
        _design(
            _item(x_m=1.0, y_m=3.8, width_m=1.0, depth_m=0.2),
            doors=[_door("south"), _door("north", wall="north")],
        )
    )
    assert _issues(report, "blocked_door")[0].door_ids == ["north"]
    assert _issues(report, "circulation_disconnected")[0].door_ids == ["north"]


def test_separate_doors_do_not_excuse_disconnected_room_regions() -> None:
    report = validate_accessibility(
        _design(
            _item(x_m=0.0, y_m=1.8, width_m=5.0, depth_m=0.4),
            doors=[_door("south"), _door("north", wall="north")],
        )
    )
    assert report.status == "failed"
    issue = _issues(report, "circulation_disconnected")[0]
    assert issue.door_ids == ["north", "south"]
    assert issue.measurements["inaccessible_door_count"] == 0
    assert issue.measurements["usable_region_count"] == 2


def test_no_door_is_explicitly_not_evaluated_and_cannot_pass() -> None:
    report = validate_accessibility(_design(doors=[]))
    assert report.status == "unverified"
    assert report.checks["containment"].status == "passed"
    assert report.checks["furniture_overlap"].status == "passed"
    for name in ("door_clearance", "circulation"):
        assert report.checks[name].status == "not_evaluated"
        assert "no door" in report.checks[name].message


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_unsupported_rotation_never_becomes_an_ignored_obstacle(rotation: int) -> None:
    report = validate_accessibility(
        _design(
            _item("rotated", rotation_deg=rotation), _item("blocker", x_m=1.0, y_m=0.0)
        )
    )
    assert report.status == "unverified"
    assert report.checks["circulation"].status == "unsupported"
    assert report.checks["door_clearance"].status == "unsupported"
    assert _issues(report, "unsupported_geometry")[0].furniture_ids == ["rotated"]
    assert _issues(report, "blocked_door")[0].furniture_ids == ["blocker"]


@pytest.mark.parametrize("door_width", [0.4, 0.6, 0.8])
def test_door_width_is_part_of_circulation_clearance(door_width: float) -> None:
    report = validate_accessibility(_design(doors=[_door(width_m=door_width)]))
    assert report.checks["door_clearance"].status == "passed"
    assert report.checks["circulation"].status == (
        "failed" if door_width < 0.6 else "passed"
    )


def test_room_too_small_for_clearance_has_no_usable_center_region() -> None:
    report = validate_accessibility(
        _design(width_m=0.5, doors=[_door(offset_m=0.0, width_m=0.4)])
    )
    assert report.status == "failed"
    assert report.checks["circulation"].measurements["usable_region_count"] == 0


def test_furniture_filling_room_has_no_usable_region() -> None:
    report = validate_accessibility(
        _design(_item(x_m=0.0, y_m=0.0, width_m=5.0, depth_m=4.0))
    )
    assert report.status == "failed"
    assert report.checks["circulation"].measurements["usable_region_count"] == 0


def test_required_depth_is_configurable() -> None:
    design = _design(_item(x_m=1.0, y_m=0.4))
    assert not _issues(validate_accessibility(design), "blocked_door")
    report = validate_accessibility(
        design, config=AccessibilityConfig(required_door_depth_m=0.5)
    )
    assert _issues(report, "blocked_door")


def test_advisory_side_margin_is_configurable() -> None:
    design = _design(_item(x_m=2.05, y_m=0.1, width_m=0.1, depth_m=0.1))
    assert _issues(validate_accessibility(design), "door_clearance_warning")
    report = validate_accessibility(
        design, config=AccessibilityConfig(advisory_side_margin_m=0.0)
    )
    assert not _issues(report, "door_clearance_warning")


def test_overlap_and_containment_violations_are_preserved() -> None:
    design = _design(_item("b", x_m=4.8), _item("a", x_m=4.8))
    base = validate_layout(design)
    report = validate_accessibility(design)
    expected = [issue.model_dump() for issue in base.violations]
    actual = [
        issue.model_dump(exclude={"door_ids", "severity"})
        for issue in report.violations
        if issue.violation_type in ("out_of_bounds", "furniture_overlap")
    ]
    assert actual == expected
    assert report.checks["containment"].status == "failed"
    assert report.checks["furniture_overlap"].status == "failed"


@pytest.mark.parametrize(
    "case", ["valid", "blocked", "warning", "no_door", "unsupported"]
)
def test_report_round_trip_preserves_every_field(case: str) -> None:
    designs = {
        "valid": _design(),
        "blocked": _design(_item(x_m=1.0, y_m=0.0)),
        "warning": _design(_item(x_m=1.0, y_m=0.7)),
        "no_door": _design(doors=[]),
        "unsupported": _design(_item(rotation_deg=90)),
    }
    report = validate_accessibility(designs[case])
    payload = report.model_dump_json()
    assert AccessibilityValidationReport.model_validate_json(payload) == report
    assert json.loads(json.dumps(report.model_dump(), allow_nan=False)) == json.loads(
        payload
    )


def test_report_is_deterministic_and_input_is_unchanged() -> None:
    design = _design(
        _item("z", x_m=1.0, y_m=0.0),
        _item("a", x_m=1.0, y_m=3.5),
        doors=[_door("south"), _door("north", wall="north")],
    )
    before = design.model_dump_json()
    expected = validate_accessibility(design).model_dump_json()
    assert validate_accessibility(design).model_dump_json() == expected
    assert design.model_dump_json() == before
    reordered = design.model_copy(deep=True)
    reordered.furniture.reverse()
    reordered.room.doors.reverse()
    assert validate_accessibility(reordered).model_dump_json() == expected


def test_old_report_api_and_json_remain_unchanged() -> None:
    report = validate_layout(_design())
    assert report.scope == "task_04a_containment_and_overlap"
    assert set(report.model_dump()) == {
        "room_id",
        "scope",
        "status",
        "violations",
        "area_tolerance_m2",
    }
    assert (
        SpatialValidationReport.model_validate_json(report.model_dump_json()) == report
    )


@pytest.mark.parametrize(
    "config",
    [
        {"walking_clearance_m": 0},
        {"walking_clearance_m": -1},
        {"walking_clearance_m": float("inf")},
        {"walking_clearance_m": float("nan")},
        {"walking_clearance_m": True},
        {"required_door_depth_m": 0},
        {"required_door_depth_m": 1.0, "advisory_door_depth_m": 0.5},
        {"advisory_side_margin_m": -0.1},
    ],
)
def test_invalid_configuration_is_rejected(config: dict) -> None:
    with pytest.raises(ValidationError):
        AccessibilityConfig.model_validate(config)


def test_report_cannot_claim_passed_with_an_unevaluated_check() -> None:
    data = validate_accessibility(_design(doors=[])).model_dump()
    data["status"] = "passed"
    with pytest.raises(ValidationError):
        AccessibilityValidationReport.model_validate(data)


def test_report_cannot_omit_a_required_check() -> None:
    data = validate_accessibility(_design()).model_dump()
    del data["checks"]["circulation"]
    with pytest.raises(ValidationError):
        AccessibilityValidationReport.model_validate(data)


def test_strict_door_blockage_cannot_be_downgraded_to_warning() -> None:
    with pytest.raises(ValidationError):
        AccessibilityIssue(
            violation_type="blocked_door",
            furniture_ids=["item"],
            door_ids=["entry"],
            severity="warning",
            message="Blocked",
        )


def test_access_work_limit_returns_unsupported_instead_of_passing() -> None:
    doors = [
        _door(f"door-{index:03d}") for index in range(MAX_ACCESSIBILITY_OBJECTS + 1)
    ]
    report = validate_accessibility(_design(doors=doors))
    assert report.status == "unverified"
    assert report.checks["circulation"].status == "unsupported"
    assert _issues(report, "unsupported_check")


def test_unrepresentable_geometry_cannot_pass_access_checks() -> None:
    report = validate_accessibility(_design(_item(x_m=1e308)))
    assert report.status == "unverified"
    assert report.checks["circulation"].status == "unsupported"


def test_invalid_mutated_models_are_revalidated() -> None:
    design = _design()
    design.room.doors[0].offset_m = 10.0
    with pytest.raises(ValidationError):
        validate_accessibility(design)


def test_sample_bedroom_reports_its_actual_access_conditions() -> None:
    report = validate_accessibility(create_sample_bedroom())
    assert report.checks["containment"].status == "passed"
    assert report.checks["furniture_overlap"].status == "passed"
    assert report.checks["door_clearance"].status == "passed"
    assert report.checks["circulation"].status == "passed"
    assert report.status == "passed"


@pytest.mark.parametrize("width", [5e-324, 1e-200])
def test_clearance_below_numeric_resolution_cannot_silently_pass(width: float) -> None:
    report = validate_accessibility(
        _design(), config=AccessibilityConfig(walking_clearance_m=width)
    )
    assert report.status == "unverified"
    assert report.checks["circulation"].status == "unsupported"


def test_unrepresentable_door_segment_is_an_unsupported_check() -> None:
    report = validate_accessibility(
        _design(
            width_m=1e100,
            doors=[_door(offset_m=1e99)],
        )
    )
    assert report.status == "unverified"
    assert report.checks["door_clearance"].status == "unsupported"
    assert report.checks["circulation"].status == "unsupported"


def test_report_rejects_passed_with_known_error_issues() -> None:
    data = validate_accessibility(_design(_item(x_m=1.0, y_m=0.0))).model_dump()
    data["status"] = "passed"
    with pytest.raises(ValidationError):
        AccessibilityValidationReport.model_validate(data)


def test_configuration_is_not_mutated_and_mutated_config_is_revalidated() -> None:
    config = AccessibilityConfig()
    before = config.model_dump_json()
    validate_accessibility(_design(), config=config)
    assert config.model_dump_json() == before
    config.walking_clearance_m = -1.0
    with pytest.raises(ValidationError):
        validate_accessibility(_design(), config=config)
