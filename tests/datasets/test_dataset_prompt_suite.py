"""Prompt-variation suite built from reference rooms, and its scorer."""

from types import SimpleNamespace

import pytest

from archimind.datasets.prompt_suite import (
    STYLES,
    PromptCase,
    build_prompt_suite,
    score_case,
    summarize,
)

from test_dataset_habits import BED, CHAIR, DESK, STAND, WARDROBE, obj, scene


def rooms():
    out = []
    for i in range(6):
        objects = [
            obj("b", *BED, 0.0, 1.0, 2.0, 1.8),
            obj("n1", *STAND, 0.0, 0.5, 0.4, 0.4),
            obj("w", *WARDROBE, 3.0, 0.0, 1.0, 0.6),
        ]
        if i % 2:
            objects.append(obj("n2", *STAND, 0.0, 2.9, 0.4, 0.4))
        if i % 3 == 0:
            objects += [obj("d", *DESK, 2.0, 3.4, 1.0, 0.6), obj("c", *CHAIR, 2.2, 2.8, 0.5, 0.5)]
        out.append(scene(f"h{i}", objects, dims=(4.0 + i * 0.1, 3.6), split="val"))
    return out


def by_style(cases):
    out = {}
    for c in cases:
        out.setdefault(c.style, []).append(c)
    return out


def test_suite_is_deterministic_and_covers_styles():
    a = build_prompt_suite(rooms(), per_style=2, seed=3)
    b = build_prompt_suite(list(reversed(rooms())), per_style=2, seed=3)
    assert a == b
    assert set(by_style(a)) == set(STYLES)
    assert len({c.case_id for c in a}) == len(a)
    assert all(isinstance(c, PromptCase) for c in a)


def test_full_prompt_has_everything_and_expected_answer():
    case = by_style(build_prompt_suite(rooms(), per_style=1, seed=0))["full_metric"][0]
    text = case.prompt
    assert "rectangular bedroom" in text and "ceiling" in text
    assert "South door" in text and "No windows" in text
    assert "king bed" in text
    assert case.expected_status == "ready"
    assert case.expected_functions["bed"] == 1 and case.expected_functions["wardrobe"] == 1
    assert case.expected_room[0] == pytest.approx(float(text.split(" m wide")[0].split()[-1]))


def test_variations_change_only_their_aspect():
    s = by_style(build_prompt_suite(rooms(), per_style=1, seed=0))
    assert " ft " in s["feet"][0].prompt and " m wide" not in s["feet"][0].prompt
    assert "wadrobe" in s["typos"][0].prompt and s["typos"][0].expected_status == "ready"
    multi = s["multiples"][0]
    assert "two nightstands" in multi.prompt
    assert multi.expected_status == "needs_clarification" and multi.expected_reason == "quantity"
    assert "door" not in s["missing_door"][0].prompt.lower()
    assert "window" not in s["missing_windows"][0].prompt.lower()
    assert "ceiling" not in s["missing_ceiling"][0].prompt.lower()
    assert "a bed" in s["no_bed_size"][0].prompt and "king" not in s["no_bed_size"][0].prompt
    assert "L-shaped" in s["l_shaped"][0].prompt and s["l_shaped"][0].expected_status == "unsupported"
    assert s["casual"][0].expected_status == "ready"


def _result(status, functions=(), room=None, clarifications=()):
    extraction = SimpleNamespace(
        furniture=[SimpleNamespace(function=f, quantity=q) for f, q in functions]
    )
    draft = None
    if room is not None:
        draft = SimpleNamespace(
            room=lambda: SimpleNamespace(width_m=room[0], depth_m=room[1], ceiling_height_m=room[2])
        )
    return SimpleNamespace(
        status=status, extraction=extraction, draft=draft, clarifications=clarifications, error=None
    )


def test_score_case_checks_status_functions_and_room():
    case = by_style(build_prompt_suite(rooms(), per_style=1, seed=0))["full_metric"][0]
    funcs = tuple(case.expected_functions.items())
    good = score_case(case, _result("ready", funcs, case.expected_room))
    assert good["status_ok"] and good["functions_ok"] and good["room_ok"] and good["passed"]
    wrong_room = (case.expected_room[0] + 0.5, *case.expected_room[1:])
    assert not score_case(case, _result("ready", funcs, wrong_room))["passed"]
    assert not score_case(case, _result("ready", funcs[:-1], case.expected_room))["passed"]
    bad = score_case(case, _result("unsupported", funcs))
    assert not bad["status_ok"] and bad["got_status"] == "unsupported"


def test_summarize_by_style():
    cases = build_prompt_suite(rooms(), per_style=1, seed=0)
    rows = [score_case(c, _result(c.expected_status, tuple(c.expected_functions.items()), c.expected_room)) for c in cases]
    rows[0]["passed"] = False
    report = summarize(rows)
    assert report["cases"] == len(cases)
    assert report["passed"] == len(cases) - 1
    assert set(report["by_style"]) == set(STYLES)


def test_cases_round_trip_through_json():
    import json

    from archimind.datasets.prompt_suite import case_from_json, case_to_json

    for case in build_prompt_suite(rooms(), per_style=1, seed=0):
        assert case_from_json(json.loads(json.dumps(case_to_json(case)))) == case


def test_entrance_question_counts_as_naming_the_door():
    case = by_style(build_prompt_suite(rooms(), per_style=1, seed=0))["missing_door"][0]
    row = score_case(case, _result("needs_clarification", tuple(case.expected_functions.items()),
                                   clarifications=("Provide at least one entrance: wall, offset, width and height.",)))
    assert row["reason_ok"] is True
