"""Verify deterministic evidence and render bounded qualitative critiques.

No layout generation, scoring, spatial-rule changes, selection or graph routing.
Planar metrics are descriptive proxies; they do not certify preference satisfaction.
"""

import re

from shapely import LineString

from archimind.agents.layout_grounding import (
    MAX_REQUEST_BYTES,
    interpret_layout_proposal,
    prepare_layout_context,
)
from archimind.agents.requirements_agent import SUPPORTED_MODELS
from archimind.agents.spatial_critic_schemas import (
    CriticEvidence,
    GroundedObservation,
    GroundedPreference,
    SpatialCriticContext,
    SpatialCriticProposal,
    SpatialCriticRequest,
    SpatialCriticResult,
)
from archimind.geometry import furniture_footprint, room_footprint
from archimind.geometry.layout_generator import _score


class InvalidRecommendationError(ValueError):
    """An optional C1 recommendation is inconsistent with the canonical packet."""


def prepare_critic_context(request: SpatialCriticRequest) -> SpatialCriticContext:
    request = SpatialCriticRequest.model_validate(request).model_copy(deep=True)
    if len(request.model_dump_json().encode("utf-8")) > MAX_REQUEST_BYTES:
        raise OverflowError("Critic request size limit")
    # Reuse C1's independent validation, specification handoff and opening metrics.
    layout = prepare_layout_context(request.layout)
    for candidate in request.layout.generation.candidates:
        # Reuse the existing score calculation; never replace the supplied score.
        if (
            _score(request.layout.specification.room, candidate.validation)
            != candidate.score
        ):
            raise ValueError("Heuristic score does not match its verified report")
    advice = request.layout_recommendation
    if advice is not None:
        try:
            if (
                advice.status not in ("recommended", "abstained")
                or advice.context != layout
                or advice.mode == "not_evaluated"
                or (advice.mode == "offline_fixture" and advice.model is not None)
                or (
                    advice.mode == "api_response"
                    and advice.model not in SUPPORTED_MODELS
                )
            ):
                raise ValueError("Recommendation context or provenance mismatch")
            if (
                interpret_layout_proposal(
                    layout, advice.proposal, mode=advice.mode, model=advice.model
                )
                != advice
            ):
                raise ValueError("Recommendation differs from grounded C1 output")
        except (ValueError, TypeError, AttributeError) as exc:
            raise InvalidRecommendationError("Invalid recommendation") from exc
    features = [CriticEvidence(**fact.model_dump()) for fact in layout.features]
    room = request.layout.specification.room
    left, bottom, right, top = room_footprint(room).bounds
    walls = {
        "north": LineString([(left, top), (right, top)]),
        "south": LineString([(left, bottom), (right, bottom)]),
        "east": LineString([(right, bottom), (right, top)]),
        "west": LineString([(left, bottom), (left, top)]),
    }
    for index, candidate in enumerate(request.layout.generation.candidates):
        for check_name, check in sorted(candidate.validation.checks.items()):
            features.append(
                CriticEvidence(
                    ref=f"candidate-{index}.check.{check_name}",
                    candidate_index=index,
                    kind="spatial_check",
                    check_name=check_name,
                    check_status=check.status,
                )
            )
        for furniture_index, item in enumerate(
            sorted(candidate.design.furniture, key=lambda item: item.id)
        ):
            footprint = furniture_footprint(item)
            for wall, segment in walls.items():
                features.append(
                    CriticEvidence(
                        ref=f"candidate-{index}.wall-gap.furniture-{furniture_index}.{wall}",
                        candidate_index=index,
                        kind="wall_planar_gap",
                        furniture_id=item.id,
                        wall=wall,
                        value=footprint.distance(segment),
                        unit="m",
                    )
                )
    context = SpatialCriticContext(request=request, features=features)
    if len(context.model_dump_json().encode("utf-8")) > MAX_REQUEST_BYTES:
        raise OverflowError("Critic context size limit")
    return context


KINDS = {
    "window_proximity": {"window_planar_gap"},
    "wall_proximity": {"wall_planar_gap"},
    "entrance_separation": {"door_planar_gap"},
    "usable_center_space": {"usable_center_space_ratio", "usable_center_area"},
    "heuristic_score": {"heuristic_score"},
    "spatial_validation": {"spatial_check"},
}
MISSING = {
    "daylight": "Actual daylight needs orientation, glazing, obstructions and lighting evidence; planar window gaps cannot establish it.",
    "ergonomics": "Ergonomics needs occupant, task and functional-access evidence; it is not evaluated by the current spatial checks.",
    "code_compliance": "Architectural code compliance and safety certification are not evaluated.",
    "furniture_usability": "Furniture usability needs task-specific access and usage requirements; no usability conclusion is supported.",
    "preference_details": "Clarify the preference and its measurable criterion before judging satisfaction.",
    "additional_constraints": "Additional hard constraints are retained but not evaluated by this advisory critic.",
    "alternative_layouts": "More validated alternatives are needed for a broader comparison; no new placement is generated.",
}
LIMITATIONS = [
    "Advisory critique only; deterministic spatial reports remain authoritative and unchanged.",
    "Planar footprint gaps are not actual daylight, ergonomics, reachability, door-swing or minimum-clearance measurements.",
    "Existing circulation uses a square-occupant approximation; passing scoped checks is not architectural code or safety certification.",
    "Preference judgments concern measured proxies only; intent and satisfaction are not certified.",
    "Only supplied alternatives are compared; no geometry, heuristic score or candidate selection is changed.",
]


def _unique(values):
    if len(values) != len(set(values)):
        raise ValueError("Duplicate references")


def _preference_categories(text: str) -> set[str]:
    """Conservative vocabulary, not general natural-language understanding.

    Mixed unsupported claims remain unverified, even when a proxy also occurs.
    Other user intent must be clarified rather than certified through a metric.
    """
    if re.search(
        r"\b(?:daylight|sunlight|illuminance|lux|ergonom\w*|code|certif\w*|safety|usable desk|desk usability)\b",
        text,
        re.I,
    ):
        return set()
    return {
        category
        for category, pattern in {
            "window_proximity": r"\bwindow\w*\b",
            "wall_proximity": r"\bwall\w*\b",
            "entrance_separation": r"\b(?:entrance|door\w*)\b",
            "usable_center_space": r"\b(?:spacious\w*|space|circulation)\b",
            "heuristic_score": r"\bscore\w*\b",
        }.items()
        if re.search(pattern, text, re.I)
    }


def _describe(fact: CriticEvidence) -> str:
    label = f"candidate-{fact.candidate_index}"
    if fact.kind == "spatial_check":
        return f"{label}: existing {fact.check_name} check {fact.check_status} (scoped approximation; advisory warnings may remain)"
    subject = {
        "window_planar_gap": f"{fact.furniture_id!r} to window {fact.opening_id!r} planar footprint gap",
        "door_planar_gap": f"{fact.furniture_id!r} to door {fact.opening_id!r} planar footprint gap",
        "wall_planar_gap": f"{fact.furniture_id!r} to {fact.wall} wall planar footprint gap",
        "heuristic_score": "original heuristic score",
        "usable_center_space_ratio": "existing usable occupant-center-space ratio",
        "usable_center_area": "existing usable occupant-center area",
    }[fact.kind]
    return f"{label}: {subject} = {fact.value:.6f} {fact.unit}"


def interpret_critic_proposal(
    context: SpatialCriticContext,
    proposal: SpatialCriticProposal,
    *,
    mode: str = "api_response",
    model: str | None = None,
) -> SpatialCriticResult:
    """Recompute context; accept no model measurements or arbitrary factual prose."""
    context = SpatialCriticContext.model_validate(context).model_copy(deep=True)
    if context != prepare_critic_context(context.request):
        raise ValueError("Context evidence differs from canonical geometry")
    proposal = SpatialCriticProposal.model_validate(proposal).model_copy(deep=True)
    facts = {fact.ref: fact for fact in context.features}
    observations, favored = [], []
    missing_topics = []
    for observation in proposal.observations:
        for values in (
            observation.candidate_indices,
            observation.furniture_ids,
            observation.evidence_refs,
        ):
            _unique(values)
        if observation.category == "missing_evidence":
            if (
                observation.relation != "unknown"
                or observation.missing_topic == "none"
                or observation.evidence_refs
                or observation.candidate_indices
                or observation.furniture_ids
            ):
                raise ValueError(
                    "Missing evidence cannot assert objects or measurements"
                )
            text, cited, preferred = MISSING[observation.missing_topic], [], None
            missing_topics.append(observation.missing_topic)
        else:
            if observation.missing_topic != "none" or not observation.evidence_refs:
                raise ValueError("Measured observation requires facts")
            if any(ref not in facts for ref in observation.evidence_refs):
                raise ValueError("Unknown evidence reference")
            cited = [facts[ref] for ref in observation.evidence_refs]
            if any(fact.kind not in KINDS[observation.category] for fact in cited):
                raise ValueError("Evidence kind does not support category")
            if observation.candidate_indices != list(
                dict.fromkeys(fact.candidate_index for fact in cited)
            ):
                raise ValueError("Observation candidate IDs must match evidence")
            if observation.furniture_ids != sorted(
                {fact.furniture_id for fact in cited if fact.furniture_id is not None}
            ):
                raise ValueError("Observation furniture IDs must match evidence")
            preferred = None
            if observation.relation == "reported":
                if len(cited) != 1 and observation.category != "spatial_validation":
                    raise ValueError(
                        "Report one metric or compare two corresponding metrics"
                    )
            else:
                if len(cited) != 2 or observation.category == "spatial_validation":
                    raise ValueError("Comparison requires two measured alternatives")
                first, second = cited

                def key(f):
                    return f.kind, f.furniture_id, f.opening_id, f.wall

                if first.candidate_index == second.candidate_index or key(first) != key(
                    second
                ):
                    raise ValueError("Comparison must concern the same metric/object")
                expected = (
                    "less"
                    if first.value < second.value
                    else "greater"
                    if first.value > second.value
                    else "equal"
                )
                if observation.relation != expected:
                    raise ValueError("Comparison contradicts actual measurements")
                if expected != "equal":
                    minimum = observation.category in (
                        "window_proximity",
                        "wall_proximity",
                    )
                    preferred = (
                        first if (first.value < second.value) == minimum else second
                    ).candidate_index
            text = "; ".join(_describe(fact) for fact in cited) + "."
            if observation.relation not in ("reported", "unknown"):
                comparison = (
                    "equal to"
                    if observation.relation == "equal"
                    else f"{observation.relation} than"
                )
                text += f" The first value is {comparison} the second. This is a measured proxy, not a guarantee of suitability."
        favored.append(preferred)
        observations.append(
            GroundedObservation(
                category=observation.category,
                candidate_ids=[
                    f"candidate-{index}" for index in observation.candidate_indices
                ],
                furniture_ids=list(observation.furniture_ids),
                explanation=text,
                evidence=cited,
            )
        )

    assessments = proposal.preference_assessments
    indices = [item.preference_index for item in assessments]
    _unique(indices)
    if set(indices) != set(range(len(context.request.layout.soft_preferences))):
        raise ValueError("Every preference needs one assessment")
    feedback = []
    for item in sorted(assessments, key=lambda item: item.preference_index):
        _unique(item.observation_indices)
        if any(index >= len(observations) for index in item.observation_indices):
            raise ValueError("Unknown preference observation")
        categories = _preference_categories(
            context.request.layout.soft_preferences[item.preference_index]
        )
        if item.judgment != "unverified":
            if (
                not categories
                or not item.observation_indices
                or any(
                    observations[index].category not in categories
                    for index in item.observation_indices
                )
            ):
                raise ValueError("Preference judgment lacks matching measured proxies")
            if item.judgment == "tradeoff" and (
                len(
                    {observations[index].category for index in item.observation_indices}
                )
                < 2
                or len({favored[index] for index in item.observation_indices} - {None})
                < 2
            ):
                raise ValueError(
                    "Tradeoff requires distinct measured advantages for different candidates"
                )
        elif any(
            observations[index].category != "missing_evidence"
            for index in item.observation_indices
        ):
            raise ValueError(
                "Unverified preference cannot assert a measurement conclusion"
            )
        feedback.append(
            GroundedPreference(
                preference_index=item.preference_index,
                judgment=item.judgment,
                observation_indices=list(item.observation_indices),
                explanation=f"Preference {item.preference_index}: {item.judgment} (subjective interpretation of measured proxies only; satisfaction is not certified).",
            )
        )
    _unique(proposal.stance_observation_indices)
    if any(index >= len(observations) for index in proposal.stance_observation_indices):
        raise ValueError("Unknown stance observation")
    advice = context.request.layout_recommendation
    selected = advice.proposal.candidate_index if advice is not None else None
    stance = proposal.recommendation_stance
    if advice is None:
        if stance != "not_provided":
            raise ValueError("No recommendation was supplied")
    elif selected is None and stance != "cannot_evaluate":
        raise ValueError("Cannot support/challenge an abstained recommendation")
    elif selected is not None and stance == "not_provided":
        raise ValueError("Recommendation stance must acknowledge supplied advice")
    if stance in ("supports", "challenges"):
        if not proposal.stance_observation_indices or any(
            favored[index] is None
            or (favored[index] == selected) != (stance == "supports")
            for index in proposal.stance_observation_indices
        ):
            raise ValueError("Stance contradicts comparative evidence")
    elif proposal.stance_observation_indices:
        raise ValueError("Unevaluated stance cannot claim supporting evidence")
    if proposal.decision == "abstain":
        if (
            observations
            or any(item.judgment != "unverified" for item in assessments)
            or stance in ("supports", "challenges")
        ):
            raise ValueError("Abstention cannot assert design conclusions")
    elif proposal.decision == "request_information":
        if not missing_topics or stance in ("supports", "challenges"):
            raise ValueError(
                "Information request needs missing evidence and no stance claim"
            )
    elif not any(observation.evidence for observation in observations) or not any(
        _preference_categories(text) for text in context.request.layout.soft_preferences
    ):
        raise ValueError(
            "Unsupported judgments require abstention or additional information"
        )
    if mode not in ("api_response", "offline_fixture") or (
        mode == "offline_fixture" and model is not None
    ):
        raise ValueError("Critique provenance must be explicit")
    assessment = {
        "critique": "The supplied layouts have measured design tradeoffs. Qualitative weighting is advisory; deterministic reports remain authoritative.",
        "request_information": "Additional evidence is needed for the requested design judgment.",
        "abstain": "The critic abstained: supplied evidence cannot support the requested design judgment.",
    }[proposal.decision]
    unsupported = list(
        dict.fromkeys(
            MISSING[topic]
            for topic in [
                "daylight",
                "ergonomics",
                "code_compliance",
                "furniture_usability",
                *missing_topics,
            ]
        )
    )
    if context.request.explicit_constraints:
        unsupported.append(MISSING["additional_constraints"])
    if any(item.judgment == "unverified" for item in assessments):
        unsupported.append(
            "Unverified preferences need additional information; no satisfaction claim is made."
        )
    return SpatialCriticResult(
        status="abstained" if proposal.decision == "abstain" else "evaluated",
        mode=mode,
        model=model,
        context=context,
        proposal=proposal,
        assessment=assessment,
        observations=observations,
        preference_feedback=feedback,
        recommendation_stance=stance,
        recommendation_explanation=(
            f"The critic {stance} candidate-{selected}'s recommendation only under the cited measured proxies "
            f"(observations {proposal.stance_observation_indices}); this advisory weighting is not a hard spatial violation or approval."
            if stance in ("supports", "challenges")
            else "No designer recommendation was supplied."
            if stance == "not_provided"
            else "The supplied evidence does not justify supporting or challenging the recommendation."
        ),
        unverified_constraints=list(range(len(context.request.explicit_constraints))),
        limitations=list(LIMITATIONS),
        unsupported_claims=unsupported,
    )
