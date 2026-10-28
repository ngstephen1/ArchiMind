"""Read-only eligibility checks and descriptive metrics, not placement algorithms."""

import re

from shapely import LineString

from archimind.agents.layout_schemas import (
    LayoutAdviceContext,
    LayoutAdviceRequest,
    LayoutAdviceResult,
    LayoutProposal,
    MeasuredFeature,
)
from archimind.geometry import furniture_footprint, validate_accessibility

MAX_REQUEST_BYTES = 65_536


def prepare_layout_context(request: LayoutAdviceRequest) -> LayoutAdviceContext:
    """Copy supplied generator data and screen every candidate, preserving indices.

    Screening reuses the existing validator and does not grant final approval.
    No generation/scoring API is called and no input object is mutated.
    """
    request = LayoutAdviceRequest.model_validate(request).model_copy(deep=True)
    if len(request.model_dump_json().encode("utf-8")) > MAX_REQUEST_BYTES:
        raise OverflowError("Request size limit")
    specification = request.specification
    room = specification.room
    if len(room.doors) + len(room.windows) > 16 or len(specification.furniture) > 32:
        raise ValueError("Layout advice supports 32 furniture and 16 openings")

    def fixed(design):
        return {
            item.id: item.model_dump(exclude={"x_m", "y_m"})
            for item in design.furniture
        }

    def opening_segment(opening):
        start, end = opening.offset_m, opening.offset_m + opening.width_m
        if opening.wall == "south":
            points = [(start, 0), (end, 0)]
        elif opening.wall == "north":
            points = [(start, room.depth_m), (end, room.depth_m)]
        elif opening.wall == "west":
            points = [(0, start), (0, end)]
        else:
            points = [(room.width_m, start), (room.width_m, end)]
        return LineString(points)

    features = []
    for index, candidate in enumerate(request.generation.candidates):
        if candidate.design.room != room or fixed(candidate.design) != fixed(
            specification
        ):
            raise ValueError("Candidate must preserve the specification")
        actual = validate_accessibility(
            candidate.design.model_copy(deep=True),
            config=request.generation.config,
            area_tolerance_m2=0.0,
        )
        if actual.status != "passed" or actual != candidate.validation:
            raise ValueError(
                "Every candidate must have a matching complete passing report"
            )

        def add(kind, value, unit, suffix, furniture_id=None, opening_id=None):
            features.append(
                MeasuredFeature(
                    ref=f"candidate-{index}.{suffix}",
                    candidate_index=index,
                    kind=kind,
                    value=value,
                    unit=unit,
                    furniture_id=furniture_id,
                    opening_id=opening_id,
                )
            )

        add("heuristic_score", candidate.score.total, "score", "heuristic-score")
        add(
            "usable_center_space_ratio",
            candidate.score.usable_space_ratio,
            "ratio",
            "usable-center-ratio",
        )
        add(
            "usable_center_area",
            actual.checks["circulation"].measurements["usable_center_area_m2"],
            "m2",
            "usable-center-area",
        )
        for furniture_index, item in enumerate(
            sorted(candidate.design.furniture, key=lambda item: item.id)
        ):
            footprint = furniture_footprint(item)
            for kind, openings in (("window", room.windows), ("door", room.doors)):
                for opening_index, opening in enumerate(
                    sorted(openings, key=lambda item: item.id)
                ):
                    add(
                        f"{kind}_planar_gap",
                        footprint.distance(opening_segment(opening)),
                        "m",
                        f"{kind}-gap.furniture-{furniture_index}.opening-{opening_index}",
                        item.id,
                        opening.id,
                    )
    context = LayoutAdviceContext(request=request, features=features)
    if len(context.model_dump_json().encode("utf-8")) > MAX_REQUEST_BYTES:
        raise OverflowError("Context size limit")
    return context


def interpret_layout_proposal(
    context: LayoutAdviceContext,
    proposal: LayoutProposal,
    *,
    mode: str = "api_response",
    model: str | None = None,
) -> LayoutAdviceResult:
    """Validate references and render factual prose exclusively from Python data."""
    context = LayoutAdviceContext.model_validate(context).model_copy(deep=True)
    proposal = LayoutProposal.model_validate(proposal).model_copy(deep=True)
    selected = proposal.candidate_index
    assessments = proposal.preference_assessments
    expected = set(range(len(context.request.soft_preferences)))
    indices = [item.preference_index for item in assessments]
    if len(set(indices)) != len(indices) or set(indices) != expected:
        raise ValueError(
            "Every supplied preference needs exactly one subjective assessment"
        )
    for assessment in assessments:
        preference = context.request.soft_preferences[assessment.preference_index]
        if (
            re.search(
                r"\b(?:daylight|sunlight|illuminance|lux|ergonom\w*|code compliance|accessibility certification)\b",
                preference,
                re.I,
            )
            and assessment.judgment != "uncertain"
        ):
            raise ValueError(
                "Unsupported daylight/ergonomic evaluations must remain uncertain"
            )
    if len(set(proposal.evidence_refs)) != len(proposal.evidence_refs):
        raise ValueError("Duplicate evidence references")
    facts = {fact.ref: fact for fact in context.features}
    if any(ref not in facts for ref in proposal.evidence_refs):
        raise ValueError("Unknown evidence reference")
    reasons = {
        "window_proximity": "the smallest cited planar window gap among supplied candidates",
        "entrance_separation": "the largest cited planar door gap among supplied candidates",
        "usable_center_space": "the largest supplied usable-center-space ratio",
        "preference_balance": "a subjective balance of the supplied preferences",
    }
    limits = [
        "Recommendation only; the independent Spatial Critic must give final approval.",
        "Planar footprint-to-opening gaps are not daylight, reachability, door-swing or minimum-clearance measurements.",
        "No daylight, ergonomic or building-code evaluation is performed.",
        "Preference assessments are subjective; satisfaction is not certified.",
        "Only the supplied candidates were compared; their original scores are unchanged.",
    ]
    if proposal.decision == "abstain":
        if (
            selected is not None
            or proposal.rationale_code
            not in ("insufficient_evidence", "no_clear_preference")
            or proposal.evidence_refs
            or any(item.judgment != "uncertain" for item in assessments)
        ):
            raise ValueError(
                "Abstention must have no selection/claims and uncertain preferences"
            )
        rationale = "The advisor abstained: supplied evidence does not establish a clear preference choice."
        evidence = []
    else:
        if (
            selected is None
            or selected >= len(context.request.generation.candidates)
            or proposal.rationale_code not in reasons
        ):
            raise ValueError("Invalid candidate selection or rationale")
        cited = [facts[ref] for ref in proposal.evidence_refs]
        if any(fact.candidate_index != selected for fact in cited):
            raise ValueError("Cited evidence must belong to the proposed candidate")
        required_kind = {
            "window_proximity": "window_planar_gap",
            "entrance_separation": "door_planar_gap",
            "usable_center_space": "usable_center_space_ratio",
        }.get(proposal.rationale_code)
        if required_kind and not any(fact.kind == required_kind for fact in cited):
            raise ValueError(
                "Measurable rationale requires corresponding deterministic evidence"
            )

        # Include matching facts for all candidates; the model cannot invent comparisons.
        def key(fact):
            return fact.kind, fact.furniture_id, fact.opening_id

        for fact in cited:
            if fact.kind == required_kind:
                peers = [
                    other.value for other in context.features if key(other) == key(fact)
                ]
                optimum = (
                    min(peers) if required_kind == "window_planar_gap" else max(peers)
                )
                if fact.value != optimum:
                    raise ValueError(
                        "Measured rationale contradicts the supplied comparison"
                    )
        keys = {key(fact) for fact in cited}
        evidence = [fact for fact in context.features if key(fact) in keys]
        rationale = f"Candidate {selected} is proposed with {reasons[proposal.rationale_code]}. This is an advisory preference judgment."
        score = context.request.generation.candidates[selected].score.total
        best_score = max(
            candidate.score.total for candidate in context.request.generation.candidates
        )
        if score < best_score:
            rationale += f" Its original heuristic score is {score:.6f}, below the highest supplied score {best_score:.6f}; the preference choice does not change either score."
    tradeoffs = []
    for item in sorted(assessments, key=lambda item: item.preference_index):
        preference = context.request.soft_preferences[item.preference_index]
        tradeoffs.append(
            f"Subjective assessment of user preference {item.preference_index} ({preference!r}): {item.judgment}; not a measured guarantee."
        )
    return LayoutAdviceResult(
        status="recommended" if proposal.decision == "recommend" else "abstained",
        mode=mode,
        model=model,
        context=context,
        proposal=proposal,
        rationale=rationale,
        evidence=evidence,
        tradeoffs=tradeoffs,
        unmet_preferences=[
            item.preference_index for item in assessments if item.judgment == "unmet"
        ],
        limitations=limits,
    )
