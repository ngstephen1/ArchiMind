"""Public acceptance briefs for Town's interpretation and geometry boundaries."""

import copy
import json
import math
import time
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

import pytest
from pydantic import ValidationError

from archimind.town import service
from archimind.town.design import Brief, digest, generate, validate_home

DATA = Path(__file__).resolve().parents[1] / "docs/data/nov24-baseline/briefs.json"
SUITE = json.loads(DATA.read_text(encoding="utf-8"))


class Observation(NamedTuple):
    outcome: str
    facts: dict


@pytest.fixture(scope="module")
def saved_home():
    return generate(Brief(width=15, depth=16, formal_salon=True))[0]


def room(home, kind):
    return next(p for p in home["rooms"] if p["design"]["room"]["id"] == kind)


def center(home, kind):
    placed = room(home, kind)
    spec = placed["design"]["room"]
    return (
        placed["origin"][0] + spec["width_m"] / 2,
        placed["origin"][1] + spec["depth_m"] / 2,
    )


def supported_observation(homes, prepared, previous, expected):
    assert homes
    details = []
    for home in homes:
        assert home["id"] == digest({k: v for k, v in home.items() if k != "id"})
        assert len(home["rooms"]) == expected["rooms"]
        assert (home["width"], home["depth"]) == (prepared.width, prepared.depth)
        if "lot_wd_m" in expected:
            assert [home["width"], home["depth"]] == expected["lot_wd_m"]
        spaces = validate_home(home, passage_m=prepared.passage_m, measure=True)
        comparison = home["evidence"]["comparison"]
        assert comparison["passage_m"] == prepared.passage_m
        assert comparison["dining_places"] == spaces["dining_places"]
        assert comparison["routes"] == spaces["routes"]
        detail = {
            "candidate_sha256": home["id"],
            "room_count": len(home["rooms"]),
            "lot_wd_m": [home["width"], home["depth"]],
            "passage_m": comparison["passage_m"],
            "dining_places": comparison["dining_places"],
        }
        if "passage_m" in expected:
            assert comparison["passage_m"] == expected["passage_m"]
        if "seats" in expected:
            assert comparison["required_dining_seats"] == expected["seats"]
            assert comparison["split_dining"] is expected["split"]
            assert comparison["dining_places"] == {"salon": 4, "kitchen-dining": 4}
        if "lock" in expected:
            before = room(previous, expected["lock"])
            after = room(home, expected["lock"])
            assert (before["origin"], before["design"]) == (
                after["origin"],
                after["design"],
            )
            detail["locked_placement_sha256"] = digest(
                [after["origin"], after["design"]]
            )
        if "goal" in expected:
            source, relation, target = expected["goal"]
            (claim,) = home["evidence"]["room_preferences"]
            assert {claim["room"], claim["target"]} == {source, target}
            assert claim["relation"] == relation
            assert claim["center_distance_m"] == pytest.approx(
                math.dist(center(home, source), center(home, target)), abs=0.00051
            )
            detail["room_center_distance_m"] = claim["center_distance_m"]
        details.append(detail)
    assert len({d["candidate_sha256"] for d in details}) == len(details)
    if "goal" in expected:
        assert len(details) == 2
        distances = [d["room_center_distance_m"] for d in details]
        assert distances == sorted(distances, reverse=expected["goal"][1] == "far")
        assert distances[0] != distances[1]
    return Observation("supported", {"candidates": details})


class KnownBaselineGap(AssertionError):
    """Fail only for the one remaining documented behavior of the pinned baseline."""


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            id=case["case"],
            marks=pytest.mark.xfail(
                reason=case["known_gap"], raises=KnownBaselineGap, strict=True
            )
            if "known_gap" in case
            else (),
        )
        for case in SUITE["cases"]
    ],
)
def test_nov24_brief(case, saved_home, monkeypatch, record_property):
    previous = (
        copy.deepcopy(saved_home) if case["case"] in SUITE["saved_home_cases"] else None
    )
    before = copy.deepcopy(previous)
    previous_digest = digest(before)
    controls = SUITE["default_controls"] | case["controls"]
    request = service.Request(
        project=uuid4(),
        id=uuid4(),
        base=int(previous is not None),
        brief=Brief.model_validate(controls),
        message=case["brief"],
        live=True,
    )
    calls = []

    def fixture_provider(schema, payload, **kwargs):
        calls.append(json.loads(payload))
        response = dict(
            priority="balanced", style="scandinavian", clarification="", unsupported=[]
        )
        if previous:
            response.update(lock_rooms=[], lock_furniture=[])
        return schema.model_validate(response | case["provider_fixture"])

    monkeypatch.setattr(
        service.provider, "configuration", lambda _: ("fixture", "fixture")
    )
    monkeypatch.setattr(service.provider, "request", fixture_provider)
    prepared = None
    expected = case["expected"]
    start = time.perf_counter()
    if case["outcome"] == "supported":
        prepared = service.interpret(request, previous)
        homes = generate(prepared, previous)
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        observed = supported_observation(homes, prepared, before, expected)
    else:
        error = None
        try:
            prepared = service.interpret(request, previous)
            homes = generate(prepared, previous)
        except ValidationError:
            raise
        except (service.Problem, ValueError) as exc:
            error = exc
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        if error is None:
            assert case["case"] == "single-table"
            assert homes and len(calls) == 1 and prepared.dining_seats == 0
            for home in homes:
                validate_home(home)
                assert home["evidence"]["comparison"]["required_dining_seats"] == 0
            record_property(
                "observation",
                json.dumps(
                    {
                        "case": case["case"],
                        "outcome": "unexpected_generation",
                        "candidate_sha256": [home["id"] for home in homes],
                        "expected_dining_seats": 6,
                        "applied_dining_seats": prepared.dining_seats,
                        "interpreter_fixture_calls": len(calls),
                        "elapsed_ms": elapsed_ms,
                    }
                ),
            )
            raise KnownBaselineGap(case["known_gap"])
        assert expected["message"].lower() in str(error).lower()
        reviewed = (
            error.reviewed if isinstance(error, service.BriefClarification) else None
        )
        if "requirement" in expected:
            assert expected["requirement"] in reviewed["requirements"]
        if "passage_m" in expected:
            assert prepared.passage_m == expected["passage_m"]
        outcome = (
            "abstention"
            if isinstance(error, ValueError) or reviewed and reviewed["unsupported"]
            else "clarification"
        )
        observed = Observation(
            outcome, {"candidates": [], "message": str(error), "reviewed": reviewed}
        )
    assert observed.outcome == case["outcome"]
    allowed_calls = case["expected_calls"]
    if isinstance(allowed_calls, int):
        allowed_calls = [allowed_calls]
    assert len(calls) in allowed_calls
    after_sha = digest(previous)
    assert after_sha == previous_digest
    record_property(
        "observation",
        json.dumps(
            {
                "case": case["case"],
                "outcome": observed.outcome,
                **observed.facts,
                "interpreter_fixture_calls": len(calls),
                "elapsed_ms": elapsed_ms,
                "input_sha256_before": previous_digest if before else None,
                "input_sha256_after": after_sha if previous else None,
                "changed_locked_fields": [],
            }
        ),
    )
