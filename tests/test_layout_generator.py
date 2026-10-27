"""Bounded, deterministic placement using real Task 04A/04B validators."""

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from archimind.examples import create_sample_bedroom
from archimind.geometry import (
    MAX_GENERATION_ATTEMPTS,
    MAX_GENERATION_FURNITURE,
    AccessibilityConfig,
    LayoutCandidate,
    LayoutGenerationResult,
    generate_layout_candidates,
    validate_accessibility,
    validate_layout,
)
from archimind.models import Door, Furniture, Room, RoomDesign
from archimind.render import render_floorplan


def _room(**changes: object) -> Room:
    return Room.model_validate(
        {
            "id": "room",
            "name": "Test room",
            "width_m": 5.0,
            "depth_m": 4.0,
            "ceiling_height_m": 2.7,
            "doors": [
                Door(id="entry", wall="south", offset_m=1.0, width_m=1.0, height_m=2.1)
            ],
            **changes,
        }
    )


def _item(identifier: str = "item", **changes: object) -> Furniture:
    return Furniture.model_validate(
        {
            "id": identifier,
            "name": identifier,
            "category": "test",
            "x_m": -10.0,
            "y_m": -10.0,
            "width_m": 1.0,
            "depth_m": 1.0,
            "height_m": 0.8,
            **changes,
        }
    )


@pytest.fixture
def bedroom_result() -> LayoutGenerationResult:
    original = create_sample_bedroom()
    return generate_layout_candidates(original.room, original.furniture)


def _positions(candidate: LayoutCandidate) -> tuple:
    return tuple((item.id, item.x_m, item.y_m) for item in candidate.design.furniture)


def test_feasible_bedroom_produces_two_distinct_ranked_candidates(
    bedroom_result: LayoutGenerationResult,
) -> None:
    result = bedroom_result
    assert result.status == "complete"
    assert len(result.candidates) == result.requested_candidates == 2
    assert 0 < result.attempts_used <= 500
    assert len({_positions(candidate) for candidate in result.candidates}) == 2
    assert result.candidates == sorted(
        result.candidates,
        key=lambda candidate: (-candidate.score.total, _positions(candidate)),
    )


def test_every_candidate_preserves_requested_identities_dimensions_and_room(
    bedroom_result: LayoutGenerationResult,
) -> None:
    original = create_sample_bedroom()
    expected = {
        item.id: item.model_dump(exclude={"x_m", "y_m"}) for item in original.furniture
    }
    for candidate in bedroom_result.candidates:
        assert candidate.design.room == original.room
        assert {
            item.id: item.model_dump(exclude={"x_m", "y_m"})
            for item in candidate.design.furniture
        } == expected
        assert candidate.design.room.windows == original.room.windows


def test_accepted_layouts_are_contained_and_have_no_positive_area_overlaps(
    bedroom_result: LayoutGenerationResult,
) -> None:
    for candidate in bedroom_result.candidates:
        assert (
            validate_layout(candidate.design, area_tolerance_m2=0.0).status == "passed"
        )
        for item in candidate.design.furniture:
            assert item.x_m >= 0 and item.y_m >= 0
            assert item.x_m + item.width_m <= candidate.design.room.width_m + 1e-12
            assert item.y_m + item.depth_m <= candidate.design.room.depth_m + 1e-12
            assert item.rotation_deg == 0


def test_accepted_layouts_pass_complete_door_and_circulation_checks(
    bedroom_result: LayoutGenerationResult,
) -> None:
    for candidate in bedroom_result.candidates:
        actual = validate_accessibility(
            candidate.design, config=bedroom_result.config, area_tolerance_m2=0.0
        )
        assert candidate.validation == actual
        assert actual.status == "passed"
        assert all(check.status == "passed" for check in actual.checks.values())
        assert all(issue.severity == "warning" for issue in actual.violations)


def test_scores_match_documented_measurable_components(
    bedroom_result: LayoutGenerationResult,
) -> None:
    for candidate in bedroom_result.candidates:
        clearance = bedroom_result.config.walking_clearance_m
        room = candidate.design.room
        empty_area = (room.width_m - clearance) * (room.depth_m - clearance)
        usable = candidate.validation.checks["circulation"].measurements[
            "usable_center_area_m2"
        ]
        warned_doors = {
            door_id
            for issue in candidate.validation.violations
            if issue.violation_type == "door_clearance_warning"
            for door_id in issue.door_ids
        }
        assert candidate.score.usable_space_ratio == pytest.approx(usable / empty_area)
        assert candidate.score.advisory_clearance_ratio == pytest.approx(
            1.0 - len(warned_doors) / len(room.doors)
        )
        assert candidate.score.total == round(
            80 * candidate.score.usable_space_ratio
            + 20 * candidate.score.advisory_clearance_ratio,
            6,
        )


def test_identical_seed_produces_identical_json(
    bedroom_result: LayoutGenerationResult,
) -> None:
    original = create_sample_bedroom()
    repeated = generate_layout_candidates(original.room, original.furniture, seed=42)
    assert repeated.model_dump_json() == bedroom_result.model_dump_json()


def test_different_seeds_explore_different_arrangements(
    bedroom_result: LayoutGenerationResult,
) -> None:
    original = create_sample_bedroom()
    other = generate_layout_candidates(original.room, original.furniture, seed=43)
    assert other.status == "complete"
    assert {_positions(candidate) for candidate in other.candidates} != {
        _positions(candidate) for candidate in bedroom_result.candidates
    }


def test_furniture_input_order_does_not_change_search(
    bedroom_result: LayoutGenerationResult,
) -> None:
    original = create_sample_bedroom()
    reordered = generate_layout_candidates(
        original.room, list(reversed(original.furniture))
    )
    assert reordered.model_dump_json() == bedroom_result.model_dump_json()


def test_generator_does_not_use_global_random_state() -> None:
    before = random.getstate()
    generate_layout_candidates(_room(), [_item()])
    assert random.getstate() == before


def test_duplicate_sample_is_skipped_before_returning_two_alternatives() -> None:
    original = create_sample_bedroom()
    result = generate_layout_candidates(
        original.room, [original.furniture[1]], seed=51, max_attempts=3
    )
    assert result.status == "complete"
    assert result.attempts_used == 3
    assert result.rejections["duplicate"] == 1
    assert len({_positions(candidate) for candidate in result.candidates}) == 2


def test_input_objects_are_unchanged_and_output_does_not_alias_them() -> None:
    original = create_sample_bedroom()
    before = original.model_dump_json()
    config = AccessibilityConfig()
    config_before = config.model_dump_json()
    result = generate_layout_candidates(
        original.room, original.furniture, config=config
    )
    assert original.model_dump_json() == before
    assert config.model_dump_json() == config_before
    result.candidates[0].design.room.doors[0].offset_m = 2.0
    result.candidates[0].design.furniture[0].name = "Edited output"
    assert original.model_dump_json() == before


def test_original_positions_are_not_fixed_or_used_for_geometry_preflight() -> None:
    requested = [_item(x_m=1e308, y_m=-1e308)]
    before = requested[0].model_dump_json()
    result = generate_layout_candidates(_room(), requested)
    assert result.status == "complete"
    assert requested[0].model_dump_json() == before


def test_excess_total_area_returns_a_proven_necessary_condition() -> None:
    items = [_item(str(index), width_m=3.0, depth_m=2.0) for index in range(4)]
    result = generate_layout_candidates(_room(), items)
    assert result.status == "infeasible"
    assert result.attempts_used == 0
    assert result.candidates == []
    assert "area" in result.message


@pytest.mark.parametrize("size", [{"width_m": 5.1}, {"depth_m": 4.1}])
def test_oversized_furniture_is_infeasible_at_zero_rotation(size: dict) -> None:
    result = generate_layout_candidates(_room(), [_item(**size)])
    assert result.status == "infeasible"
    assert result.attempts_used == 0


def test_full_room_item_is_rejected_by_hard_checks_without_an_infeasibility_claim() -> (
    None
):
    result = generate_layout_candidates(
        _room(), [_item(width_m=5.0, depth_m=4.0)], max_attempts=3
    )
    assert result.status == "search_exhausted"
    assert result.attempts_used == 3
    assert result.candidates == []
    assert result.rejections["complete_access"] == 3
    assert "not proof" in result.message


def test_packing_failure_below_room_area_is_reported_as_search_exhaustion() -> None:
    result = generate_layout_candidates(
        _room(),
        [_item("a", width_m=3.0, depth_m=2.5), _item("b", width_m=3.0, depth_m=2.5)],
        max_attempts=20,
    )
    assert result.status == "search_exhausted"
    assert result.attempts_used == result.rejections["partial_spatial"] == 20
    assert result.candidates == []


def test_advisory_warnings_reduce_score_without_disqualifying_candidates() -> None:
    # The expanded advisory zone covers the whole room, while the required
    # entrance zone remains small. Every accepted item therefore has a warning.
    config = AccessibilityConfig(advisory_door_depth_m=4.0, advisory_side_margin_m=5.0)
    result = generate_layout_candidates(_room(), [_item()], config=config)
    assert result.status == "complete"
    for candidate in result.candidates:
        assert candidate.validation.status == "passed"
        assert candidate.validation.violations
        assert all(
            issue.severity == "warning" for issue in candidate.validation.violations
        )
        assert candidate.score.advisory_clearance_ratio == 0.0
        assert candidate.score.total == round(
            80 * candidate.score.usable_space_ratio, 6
        )


def test_zero_budget_returns_structured_search_exhaustion() -> None:
    result = generate_layout_candidates(_room(), [_item()], max_attempts=0)
    assert result.status == "search_exhausted"
    assert result.attempts_used == 0
    assert result.candidates == []


def test_insufficient_candidates_preserve_the_valid_partial_result() -> None:
    original = create_sample_bedroom()
    result = generate_layout_candidates(
        original.room, original.furniture, max_attempts=8
    )
    assert result.status == "search_exhausted"
    assert result.attempts_used == 8
    assert len(result.candidates) == 1
    assert result.candidates[0].validation.status == "passed"


def test_pruned_search_stays_within_its_validation_work_bound(monkeypatch) -> None:
    import archimind.geometry.layout_generator as generator

    original_validate = generator.validate_layout
    calls = []

    def record(design, **kwargs):
        calls.append(len(design.furniture))
        return original_validate(design, **kwargs)

    monkeypatch.setattr(generator, "validate_layout", record)
    original = create_sample_bedroom()
    result = generator.generate_layout_candidates(
        original.room, original.furniture, max_attempts=4
    )
    assert result.attempts_used <= 4
    assert len(calls) <= 4 * len(original.furniture)
    assert result.rejections["partial_spatial"] > 0


def test_one_requested_candidate_returns_exactly_one() -> None:
    result = generate_layout_candidates(_room(), [_item()], max_candidates=1)
    assert result.status == "complete"
    assert len(result.candidates) == 1


@pytest.mark.parametrize("target", [1, 2])
def test_empty_furniture_has_only_one_distinct_arrangement(target: int) -> None:
    result = generate_layout_candidates(_room(), [], max_candidates=target)
    assert result.status == ("complete" if target == 1 else "search_exhausted")
    assert result.attempts_used == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].design.furniture == []
    assert result.candidates[0].score.total == 100.0


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_unsupported_rotations_are_not_silently_reset(rotation: int) -> None:
    item = _item(rotation_deg=rotation)
    result = generate_layout_candidates(_room(), [item])
    assert result.status == "unsupported"
    assert result.attempts_used == 0
    assert result.candidates == []
    assert item.rotation_deg == rotation


def test_no_door_cannot_produce_a_claimed_valid_candidate() -> None:
    result = generate_layout_candidates(_room(doors=[]), [_item()])
    assert result.status == "unsupported"
    assert result.candidates == []
    assert "door" in result.message


def test_empty_room_with_too_narrow_an_entrance_is_infeasible_for_chosen_clearance() -> (
    None
):
    room = _room(
        doors=[Door(id="narrow", wall="south", offset_m=1.0, width_m=0.4, height_m=2.1)]
    )
    result = generate_layout_candidates(room, [_item()])
    assert result.status == "infeasible"
    assert result.attempts_used == 0
    # The configurable requirement, rather than the input schema, rejects this.
    smaller = generate_layout_candidates(
        room, [_item()], config=AccessibilityConfig(walking_clearance_m=0.3)
    )
    assert smaller.status == "complete"


def test_custom_clearance_is_used_for_every_accepted_candidate() -> None:
    original = create_sample_bedroom()
    config = AccessibilityConfig(walking_clearance_m=0.8, required_door_depth_m=0.5)
    result = generate_layout_candidates(
        original.room, original.furniture, config=config
    )
    assert result.status == "complete"
    assert result.config == config
    for candidate in result.candidates:
        assert candidate.validation.config == config
        assert (
            validate_accessibility(
                candidate.design, config=config, area_tolerance_m2=0
            ).status
            == "passed"
        )


@pytest.mark.parametrize("wall", ["north", "south", "east", "west"])
def test_generator_uses_door_constraints_on_all_walls(wall: str) -> None:
    room = _room(
        doors=[Door(id="entry", wall=wall, offset_m=0.0, width_m=1.0, height_m=2.1)]
    )
    result = generate_layout_candidates(room, [_item()])
    assert result.status == "complete"
    assert all(
        candidate.validation.checks["door_clearance"].status == "passed"
        for candidate in result.candidates
    )


def test_numeric_geometry_limit_returns_unsupported() -> None:
    result = generate_layout_candidates(_room(width_m=1e200, depth_m=1e200), [])
    assert result.status == "unsupported"
    assert result.candidates == []


def test_generator_object_limit_returns_unsupported() -> None:
    requested = [
        _item(str(index), width_m=0.01, depth_m=0.01)
        for index in range(MAX_GENERATION_FURNITURE + 1)
    ]
    result = generate_layout_candidates(_room(), requested)
    assert result.status == "unsupported"
    assert result.attempts_used == 0


@pytest.mark.parametrize(
    "options",
    [
        {"seed": True},
        {"seed": 1.5},
        {"seed": None},
        {"max_attempts": -1},
        {"max_attempts": 2.5},
        {"max_attempts": True},
        {"max_attempts": MAX_GENERATION_ATTEMPTS + 1},
        {"max_candidates": 0},
        {"max_candidates": 3},
        {"max_candidates": True},
    ],
)
def test_invalid_search_options_are_rejected(options: dict) -> None:
    with pytest.raises(ValueError):
        generate_layout_candidates(_room(), [_item()], **options)


def test_duplicate_ids_and_mutated_invalid_specifications_are_revalidated() -> None:
    with pytest.raises(ValidationError):
        generate_layout_candidates(_room(), [_item("same"), _item("same")])
    item = _item()
    item.width_m = -1.0
    with pytest.raises(ValidationError):
        generate_layout_candidates(_room(), [item])


def test_full_result_round_trip_is_lossless(
    bedroom_result: LayoutGenerationResult,
) -> None:
    payload = bedroom_result.model_dump_json()
    assert LayoutGenerationResult.model_validate_json(payload) == bedroom_result
    assert json.loads(
        json.dumps(bedroom_result.model_dump(), allow_nan=False)
    ) == json.loads(payload)


def test_failure_results_are_json_serializable() -> None:
    outcomes = [
        generate_layout_candidates(_room(), [_item()], max_attempts=0),
        generate_layout_candidates(_room(), [_item(width_m=6.0)]),
        generate_layout_candidates(_room(), [_item(rotation_deg=90)]),
    ]
    for result in outcomes:
        assert (
            LayoutGenerationResult.model_validate_json(result.model_dump_json())
            == result
        )


def test_existing_renderer_accepts_each_candidate_without_special_cases(
    bedroom_result: LayoutGenerationResult,
) -> None:
    for candidate in bedroom_result.candidates:
        before = candidate.design.model_dump_json()
        figure = render_floorplan(candidate.design)
        assert json.loads(figure.to_json())["layout"]["meta"]["units"] == "m"
        assert candidate.design.model_dump_json() == before


def test_candidate_model_rejects_a_failed_report() -> None:
    invalid = RoomDesign(room=_room(), furniture=[_item()])
    with pytest.raises(ValidationError):
        LayoutCandidate(
            design=invalid,
            validation=validate_accessibility(invalid, area_tolerance_m2=0),
            score={
                "usable_space_ratio": 1.0,
                "advisory_clearance_ratio": 1.0,
                "total": 100.0,
            },
        )


def test_example_cli_preserves_original_request_and_exports_alternatives(
    tmp_path: Path,
) -> None:
    output = tmp_path / "bedroom.json"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "archimind.examples.generate_bedroom",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    document = json.loads(output.read_text())
    assert (
        RoomDesign.model_validate(document["original_request"])
        == create_sample_bedroom()
    )
    result = LayoutGenerationResult.model_validate(document["generation"])
    assert result.status == "complete"
    assert len(result.candidates) == 2
    assert "complete: 2 alternatives" in process.stderr
    assert not process.stdout
