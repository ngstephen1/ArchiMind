"""The release gate is code only: real geometry, real generator, no model."""

from archimind.design_agent.gate import (
    PlacementGoal,
    expected_items,
    goal_met,
    release_gate,
    window_blockers,
)
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates


def _candidates(seed: int = 1, count: int = 2):
    spec = create_sample_bedroom()
    result = generate_layout_candidates(
        spec.room, spec.furniture, seed=seed, max_candidates=count, max_attempts=500
    )
    assert result.candidates
    return spec, result.candidates, result.config


def _unblocked(seed_limit: int = 40):
    for seed in range(seed_limit):
        spec, candidates, config = _candidates(seed)
        for candidate in candidates:
            if not window_blockers(candidate.design):
                return spec, candidate, config
    raise AssertionError("no unblocked candidate in seed range")


def _blocked(seed_limit: int = 200):
    for seed in range(seed_limit):
        spec, candidates, config = _candidates(seed)
        for candidate in candidates:
            if window_blockers(candidate.design):
                return spec, candidate, config
    raise AssertionError("no blocked candidate in seed range")


REQUEST = ["A bedroom with a queen bed, a desk and a wardrobe."]


def test_expected_items_counts_mentions_and_ignores_the_word_bedroom() -> None:
    assert expected_items(["A bedroom with two desks and a wardrobe"]) == {
        "desk": 2,
        "storage": 1,
    }


def test_expected_items_latest_removal_wins() -> None:
    messages = ["A queen bed and a desk.", "Actually remove the desk."]
    assert expected_items(messages) == {"bed": 1, "desk": 0}


def test_expected_items_negation_means_zero() -> None:
    assert expected_items(["A bed but no wardrobe"]) == {"bed": 1, "storage": 0}


def test_gate_passes_a_valid_complete_layout() -> None:
    spec, candidate, config = _unblocked()
    gate = release_gate(spec, candidate, REQUEST, [], config)
    assert gate.passed, gate.reasons


def test_gate_fails_when_a_requested_item_was_dropped() -> None:
    spec, candidate, config = _unblocked()
    gate = release_gate(
        spec, candidate, ["A queen bed, a desk, a wardrobe and two desks."], [], config
    )
    assert not gate.passed
    assert any("desk" in reason for reason in gate.reasons)


def test_gate_fails_when_a_removed_item_is_still_present() -> None:
    spec, candidate, config = _unblocked()
    gate = release_gate(spec, candidate, ["No wardrobe please."], [], config)
    assert not gate.passed
    assert any("wardrobe" in reason for reason in gate.reasons)


def test_gate_fails_when_tall_furniture_blocks_the_window() -> None:
    spec, candidate, config = _blocked()
    gate = release_gate(spec, candidate, REQUEST, [], config)
    assert not gate.passed
    assert any("window" in reason for reason in gate.reasons)


def test_gate_recomputes_geometry_instead_of_trusting_the_claimed_report() -> None:
    spec, candidate, config = _unblocked()
    moved = candidate.design.model_copy(deep=True)
    moved.furniture[1].x_m = moved.furniture[0].x_m
    moved.furniture[1].y_m = moved.furniture[0].y_m
    forged = candidate.model_copy(update={"design": moved})
    gate = release_gate(spec, forged, REQUEST, [], config)
    assert not gate.passed
    assert any("spatial" in reason.lower() for reason in gate.reasons)


def test_gate_fails_when_furniture_size_differs_from_the_specification() -> None:
    spec, candidate, config = _unblocked()
    resized = spec.model_copy(deep=True)
    resized.furniture[0].width_m = 1.0
    gate = release_gate(resized, candidate, REQUEST, [], config)
    assert not gate.passed
    assert any("specification" in reason for reason in gate.reasons)


def test_required_goal_is_enforced_and_optional_goal_is_not() -> None:
    spec, candidate, config = _unblocked()
    far = PlacementGoal(item="desk", relation="near_door", required=True)
    near = PlacementGoal(item="desk", relation="away_from_door", required=True)
    unmet = far if not goal_met(candidate.design, far) else near
    assert not goal_met(candidate.design, unmet)

    required = release_gate(spec, candidate, REQUEST, [unmet], config)
    optional = release_gate(
        spec,
        candidate,
        REQUEST,
        [unmet.model_copy(update={"required": False})],
        config,
    )
    assert not required.passed
    assert optional.passed


def test_window_blockers_ignores_furniture_lower_than_the_sill() -> None:
    design = create_sample_bedroom()
    bed = design.furniture[0]
    bed.x_m, bed.y_m = 2.7, design.room.depth_m - bed.depth_m
    assert bed.height_m < design.room.windows[0].sill_height_m
    assert bed.id not in window_blockers(design)


def test_window_blockers_flags_a_tall_item_against_the_window() -> None:
    design = create_sample_bedroom()
    wardrobe = design.furniture[2]
    wardrobe.x_m, wardrobe.y_m = 2.7, design.room.depth_m - wardrobe.depth_m
    assert wardrobe.id in window_blockers(design)
