"""Verify the selected layout and resolve style metadata from the fixed catalog."""

import re

from archimind.agents.interior_stylist_catalog import (
    ACCENTS,
    CATALOG,
    MATERIALS,
    PALETTES,
    THEMES,
)
from archimind.agents.interior_stylist_schemas import (
    InteriorStylePlan,
    InteriorStyleProposal,
    InteriorStylistContext,
    InteriorStylistRequest,
    InteriorStylistResult,
    StylePreferenceNote,
)
from archimind.agents.layout_grounding import MAX_REQUEST_BYTES
from archimind.agents.requirements_agent import SUPPORTED_MODELS
from archimind.agents.spatial_critic_grounding import (
    interpret_critic_proposal,
    prepare_critic_context,
)
from archimind.geometry import validate_accessibility
from archimind.geometry.layout_generator import _score


class InvalidCritiqueError(ValueError):
    """Optional feedback is not checked critique of the selected candidate."""


def prepare_stylist_context(request: InteriorStylistRequest) -> InteriorStylistContext:
    request = InteriorStylistRequest.model_validate(request).model_copy(deep=True)
    if len(request.model_dump_json().encode("utf-8")) > MAX_REQUEST_BYTES:
        raise OverflowError("Stylist request size limit")
    candidate = request.candidate
    room = candidate.design.room
    if len(candidate.design.furniture) > 32 or len(room.doors) + len(room.windows) > 16:
        raise ValueError("Stylist supports 32 furniture and 16 openings")
    if any(len(item.id) > 100 for item in candidate.design.furniture):
        raise ValueError("Furniture IDs exceed the stylist reference limit")
    actual = validate_accessibility(
        candidate.design.model_copy(deep=True),
        config=candidate.validation.config,
        area_tolerance_m2=0.0,
    )
    if (
        actual.status != "passed"
        or actual != candidate.validation
        or _score(room, actual) != candidate.score
    ):
        raise ValueError(
            "Selected layout needs a verified passing report and matching original score"
        )
    critique = request.critique
    if critique is not None:
        try:
            if (
                critique.status not in ("evaluated", "abstained")
                or critique.mode == "not_evaluated"
            ):
                raise ValueError("Critique was not evaluated")
            if (critique.mode == "offline_fixture" and critique.model is not None) or (
                critique.mode == "api_response"
                and critique.model not in SUPPORTED_MODELS
            ):
                raise ValueError("Critique provenance is inconsistent")
            context = prepare_critic_context(critique.context.request)
            if (
                context != critique.context
                or interpret_critic_proposal(
                    context, critique.proposal, mode=critique.mode, model=critique.model
                )
                != critique
            ):
                raise ValueError("Critique differs from canonical D1 grounding")
            matches = [
                index
                for index, item in enumerate(
                    context.request.layout.generation.candidates
                )
                if item == candidate
            ]
            if len(matches) != 1 or context.request.reviewed_candidate_index not in (
                None,
                matches[0],
            ):
                raise ValueError("Critique does not concern the selected candidate")
        except (ValueError, TypeError, AttributeError, ArithmeticError) as exc:
            raise InvalidCritiqueError("Invalid selected-candidate critique") from exc
    context = InteriorStylistContext(
        request=request, catalog=CATALOG.model_copy(deep=True)
    )
    if len(context.model_dump_json().encode("utf-8")) > MAX_REQUEST_BYTES:
        raise OverflowError("Stylist context size limit")
    return context


CONFLICTS = {
    "mixed_theme_request": "Several catalog themes were named; one main theme is an interpretation requiring priority confirmation.",
    "palette_preference_conflict": "Some stated appearance preferences conflict with the chosen palette/finish selections; clarify priorities.",
    "unavailable_material": "A requested appearance/material is outside this small catalog; no physical replacement asset was supplied.",
    "missing_style_details": "More detail about the desired appearance is needed before selecting a style.",
    "unsupported_performance_claim": "Material performance, safety, daylight, ergonomics and circulation improvements are not evaluated by style metadata.",
}
LIMITATIONS = [
    "Appearance metadata only; no material, color or finish has been applied to Plotly or Three.js.",
    "No physical material assets, texture files, procurement specifications or performance evidence are provided.",
    "Catalog colors could support a future flat-color mapping; no renderer mapping is implemented here.",
    "Geometry, positions, dimensions, openings, selected candidate, scores and spatial reports remain unchanged.",
    "Aesthetic choices do not improve or recertify verified circulation, daylight, ergonomics or code compliance.",
    "Preference notes are subjective interpretations, not verified satisfaction or general language understanding.",
]
ASSUMPTIONS = [
    "One main theme is used for the selected room.",
    "Named finishes describe an appearance, not a confirmed physical material or construction method.",
    "Accent colors are recommendations without object placement or geometry changes.",
]
UNSUPPORTED = re.compile(
    r"\b(?:fire\w*|flame\w*|thermal|acoustic\w*|soundproof\w*|durab\w*|non-toxic|voc|waterproof\w*|antibacterial|safety|circulation|clearance|daylight|ergonom\w*|code|performance|load-bearing|sustainab\w*|eco-friendly)\b",
    re.I,
)


def _unique(values):
    if len(values) != len(set(values)):
        raise ValueError("Duplicate style references")


def interpret_style_proposal(
    context: InteriorStylistContext,
    proposal: InteriorStyleProposal,
    *,
    mode: str = "api_response",
    model: str | None = None,
) -> InteriorStylistResult:
    context = InteriorStylistContext.model_validate(context).model_copy(deep=True)
    if context != prepare_stylist_context(context.request):
        raise ValueError("Stylist context differs from verified input/catalog")
    proposal = InteriorStyleProposal.model_validate(proposal).model_copy(deep=True)
    if context.request.style_request is None:
        raise ValueError("Styling requires an explicit style request")
    if mode not in ("api_response", "offline_fixture") or (
        mode == "offline_fixture" and model is not None
    ):
        raise ValueError("Stylist provenance must be explicit")
    preferences = [context.request.style_request, *context.request.soft_preferences]
    indices = [item.preference_index for item in proposal.preference_assessments]
    _unique(indices)
    if set(indices) != set(range(len(preferences))):
        raise ValueError("Each stated preference needs exactly one assessment")
    _unique(proposal.conflict_codes)
    _unique(proposal.accent_ids)
    notes = []
    for item in sorted(
        proposal.preference_assessments, key=lambda item: item.preference_index
    ):
        if (
            UNSUPPORTED.search(preferences[item.preference_index])
            and item.judgment != "unverified"
        ):
            raise ValueError(
                "Unsupported performance/spatial claims must remain unverified"
            )
        notes.append(
            StylePreferenceNote(
                preference_index=item.preference_index,
                judgment=item.judgment,
                explanation=f"Preference {item.preference_index}: {item.judgment}; subjective appearance interpretation only, not verified satisfaction.",
            )
        )
    if proposal.decision == "request_clarification":
        if (
            any(
                value is not None
                for value in (
                    proposal.theme_id,
                    proposal.palette_id,
                    proposal.wall_material_id,
                    proposal.floor_material_id,
                )
            )
            or proposal.furniture_finishes
            or proposal.accent_ids
        ):
            raise ValueError("Clarification cannot present a partial style plan")
        if (
            proposal.rationale_code != "clarification_needed"
            or not proposal.conflict_codes
            or any(
                item.judgment != "unverified"
                for item in proposal.preference_assessments
            )
        ):
            raise ValueError(
                "Clarification requires an explicit reason and unverified preferences"
            )
        return InteriorStylistResult(
            status="needs_clarification",
            mode=mode,
            model=model,
            context=context,
            proposal=proposal,
            message="Style priorities need clarification; no plan was fabricated.",
            clarification_reasons=proposal.conflict_codes,
        )
    if (
        None
        in (
            proposal.theme_id,
            proposal.palette_id,
            proposal.wall_material_id,
            proposal.floor_material_id,
        )
        or proposal.rationale_code == "clarification_needed"
    ):
        raise ValueError("Style selection needs complete catalog choices")
    palette = PALETTES[proposal.palette_id]
    if (
        palette.theme_id != proposal.theme_id
        or proposal.palette_id not in THEMES[proposal.theme_id].palette_ids
    ):
        raise ValueError("Palette does not belong to the selected theme")
    if (
        proposal.wall_material_id not in palette.wall_material_ids
        or proposal.floor_material_id not in palette.floor_material_ids
    ):
        raise ValueError("Wall/floor selections are incompatible with the palette")
    ids = [item.furniture_id for item in proposal.furniture_finishes]
    _unique(ids)
    if set(ids) != {item.id for item in context.request.candidate.design.furniture}:
        raise ValueError("Finish selections must cover exactly the selected furniture")
    if any(
        item.material_id not in palette.furniture_material_ids
        for item in proposal.furniture_finishes
    ) or any(accent not in palette.accent_ids for accent in proposal.accent_ids):
        raise ValueError("Furniture/accent choices are incompatible with the palette")
    themes = {
        theme
        for theme in THEMES
        if re.search(rf"\b{theme}\b", " ".join(preferences), re.I)
    }
    if themes and proposal.theme_id not in themes:
        raise ValueError("Selected theme contradicts the named theme request")
    if len(themes) > 1 and (
        "mixed_theme_request" not in proposal.conflict_codes
        or any(
            item.judgment == "favored"
            for item in proposal.preference_assessments
            if sum(
                bool(
                    re.search(rf"\b{theme}\b", preferences[item.preference_index], re.I)
                )
                for theme in themes
            )
            > 1
        )
    ):
        raise ValueError("Mixed themes require a disclosed compromise or clarification")
    for item in proposal.preference_assessments:
        text = preferences[item.preference_index]
        named = {theme for theme in themes if re.search(rf"\b{theme}\b", text, re.I)}
        if named and proposal.theme_id not in named and item.judgment == "favored":
            raise ValueError(
                "An unselected named theme cannot be labeled fully favored"
            )
        conflict = (
            bool(re.search(r"\bwarm white walls?\b", text, re.I))
            and proposal.wall_material_id != "wall_warm_white"
            or bool(re.search(r"\blight oak furniture\b", text, re.I))
            and (
                not proposal.furniture_finishes
                or any(
                    f.material_id != "finish_light_oak"
                    for f in proposal.furniture_finishes
                )
            )
            or bool(re.search(r"\bmuted sage accents?\b", text, re.I))
            and "muted_sage" not in proposal.accent_ids
        )
        if conflict and (
            item.judgment == "favored"
            or "palette_preference_conflict" not in proposal.conflict_codes
        ):
            raise ValueError(
                "Recognized appearance conflict cannot be labeled fully favored or hidden"
            )
    conflicts = [CONFLICTS[code] for code in proposal.conflict_codes]
    if (
        any(UNSUPPORTED.search(text) for text in preferences)
        and CONFLICTS["unsupported_performance_claim"] not in conflicts
    ):
        conflicts.append(CONFLICTS["unsupported_performance_claim"])
    assumptions = list(ASSUMPTIONS)
    if not themes:
        assumptions.append(
            "No catalog theme was explicitly named; the selected theme is a subjective interpretation."
        )
    if context.request.critique is not None:
        assumptions.append(
            "Optional critique remains advisory; styling does not resolve its unverified spatial or functional questions."
        )
    rationale = {
        "coherent_palette": "uses compatible entries from one curated palette",
        "restrained_accents": "limits accents to the selected catalog colors",
        "finish_consistency": "coordinates the catalog finish representations for existing furniture",
    }[proposal.rationale_code]
    plan = InteriorStylePlan(
        theme_id=proposal.theme_id,
        palette_id=proposal.palette_id,
        wall_finish=MATERIALS[proposal.wall_material_id],
        floor_finish=MATERIALS[proposal.floor_material_id],
        furniture_finishes={
            item.furniture_id: MATERIALS[item.material_id]
            for item in sorted(
                proposal.furniture_finishes, key=lambda item: item.furniture_id
            )
        },
        accents=[ACCENTS[identifier] for identifier in proposal.accent_ids],
        explanation=f"{THEMES[proposal.theme_id].label}: {palette.label}; {rationale}. This is an appearance-only style interpretation, not a rendered or physical material specification.",
        preference_notes=notes,
        conflicts=conflicts,
        unmet_preferences=sorted(
            item.preference_index
            for item in proposal.preference_assessments
            if item.judgment == "unmet"
        ),
        assumptions=assumptions,
        limitations=list(LIMITATIONS),
    )
    return InteriorStylistResult(
        status="styled",
        mode=mode,
        model=model,
        context=context,
        proposal=proposal,
        plan=plan,
        message="Catalog style metadata prepared; selected layout is unchanged.",
    )
