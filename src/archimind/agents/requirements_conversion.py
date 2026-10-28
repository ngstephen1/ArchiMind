"""Deterministic evidence checks, catalog defaults and canonical conversion."""

import re
from decimal import Decimal

from pydantic import ValidationError

from archimind.agents.requirements_schemas import (
    LengthEvidence,
    RequirementsResult,
    RequirementsSchema,
)
from archimind.examples.sample_bedroom import create_sample_bedroom
from archimind.models import Door, Furniture, Room, RoomDesign, Window

_ALIASES = {
    "queen_bed": r"queen(?:[- ]size)?(?:\s+beds?)?",
    "desk": r"desks?",
    "wardrobe": r"wardrobes?",
}


def meters(length: LengthEvidence) -> float:
    """Exact decimal 1 ft = 0.3048 m, converted by Python, never by the model."""
    length = LengthEvidence.model_validate(length)
    return float(
        Decimal(str(length.value))
        * (Decimal("0.3048") if length.unit == "ft" else Decimal(1))
    )


def _source(quote: str, description: str) -> bool:
    return bool(quote.strip()) and quote.casefold() in description.casefold()


def _length_supported(length: LengthEvidence, description: str) -> bool:
    if not _source(length.source_text, description):
        return False
    numbers = re.findall(r"(?<![\w.])[+-]?\d+(?:\.\d+)?(?![\d.])", length.source_text)
    unit = (
        r"(?<![A-Za-z])(?:m|meters?|metres?)\b"
        if length.unit == "m"
        else r"(?<![A-Za-z])(?:ft|feet|foot)\b|′|'"
    )
    return any(
        Decimal(number) == Decimal(str(length.value)) for number in numbers
    ) and bool(re.search(unit, length.source_text, re.I))


def prepare_requirements(
    extraction: RequirementsSchema,
    description: str,
    *,
    mode: str = "offline_fixture",
    model: str | None = None,
) -> RequirementsResult:
    """Revalidate evidence, then use existing canonical schemas; no geometry claims.

    Defaults are exclusively the existing bedroom catalog dimensions, disclosed
    as assumptions. Missing room/opening fields are never filled. Additional hard
    constraints stop the workflow because the current generator cannot enforce them.
    """
    data = RequirementsSchema.model_validate(extraction).model_copy(deep=True)
    questions = list(data.missing_or_ambiguous)
    assumptions = list(data.assumptions)
    limits = [
        "Catalog dimensions are demonstration values, not product specifications.",
        "Style and soft preferences are retained metadata; the generator does not enforce them.",
        "Extraction can misinterpret intent; schema/evidence checks do not prove semantic accuracy.",
    ]

    def outcome(
        status: str, specification: RoomDesign | None = None
    ) -> RequirementsResult:
        return RequirementsResult(
            status=status,
            mode=mode,
            model=model,
            extraction=data,
            specification=specification,
            clarifications=list(dict.fromkeys(questions)),
            assumptions=list(dict.fromkeys(assumptions)),
            limitations=limits,
        )

    if (
        data.room_type == "unsupported"
        or data.shape == "unsupported"
        or data.unsupported_features
    ):
        limits.extend(
            data.unsupported_features
            or ["Only rectangular bedrooms and studios are supported."]
        )
        return outcome("unsupported")
    if data.hard_constraints:
        limits.append(
            "Additional hard constraints cannot be enforced; explicitly revise them before generation."
        )
        return outcome("unsupported")
    if data.room_type == "unknown" or data.room_type_source is None:
        questions.append("Specify a bedroom or simple studio.")
    elif not _source(data.room_type_source, description) or not re.search(
        rf"\b{data.room_type}\b", data.room_type_source, re.I
    ):
        questions.append(
            "Confirm the room type; its evidence was not found in the request."
        )
    if data.shape != "rectangular":
        questions.append("Confirm a single rectangular room.")
    else:
        assumptions.append(
            "One rectangular room is modeled; no other room shape is inferred."
        )

    def length(
        value: LengthEvidence | None, label: str, *, positive: bool = True
    ) -> float | None:
        if value is None:
            questions.append(f"Provide {label}, including units.")
            return None
        if not _length_supported(value, description):
            questions.append(
                f"Confirm {label}; its number/unit evidence is missing or inconsistent."
            )
            return None
        converted = meters(value)
        if positive and converted <= 0:
            questions.append(f"Provide a positive {label}.")
            return None
        return converted

    dimensions = {
        name: length(getattr(data, name), f"room {name.replace('_', ' ')}")
        for name in ("width", "depth", "ceiling_height")
    }
    if not data.doors:
        questions.append(
            "Provide at least one door with wall, offset, width and height; an entrance cannot be invented."
        )
    if not data.furniture:
        questions.append(
            "Specify furniture from the supported catalog, or clarify the intended empty-room request."
        )
    if (
        not data.windows
        and re.search(r"\bwindows?\b", description, re.I)
        and not re.search(r"\b(?:no|without)\s+windows?\b", description, re.I)
    ):
        questions.append(
            "Confirm window specifications mentioned in the request but omitted from extraction."
        )
    elif data.windows is None:
        assumptions.append("Windows were not specified; no window geometry is modeled.")

    doors, windows = [], []
    for kind, openings in (("door", data.doors or []), ("window", data.windows or [])):
        for index, opening in enumerate(openings, 1):
            label = f"{kind} {index}"
            if (
                opening.wall is None
                or not _source(opening.source_text, description)
                or not re.search(rf"\b{opening.wall}\b", opening.source_text, re.I)
            ):
                questions.append(
                    f"Confirm {label} wall; no wall location will be assumed."
                )
            values = {
                field: length(
                    getattr(opening, field),
                    f"{label} {field}",
                    positive=field != "offset",
                )
                for field in ("offset", "width", "height")
            }
            if kind == "window":
                values["sill_height"] = length(
                    opening.sill_height, f"{label} sill height", positive=False
                )
            if opening.wall is not None and all(
                value is not None for value in values.values()
            ):
                params = {f"{field}_m": value for field, value in values.items()}
                try:
                    item = (Door if kind == "door" else Window)(
                        id=f"{kind}-{index}", wall=opening.wall, **params
                    )
                except ValidationError:
                    questions.append(f"Correct {label} dimensions.")
                else:
                    (doors if kind == "door" else windows).append(item)

    sample = create_sample_bedroom()
    catalog = dict(
        zip(("queen_bed", "desk", "wardrobe"), sample.furniture, strict=True)
    )
    furniture = []
    counts: dict[str, int] = {}
    for item in data.furniture:
        if item.catalog_key == "unknown_bed":
            questions.append(
                "Confirm bed size; only the queen-bed catalog entry is currently available."
            )
            continue
        if item.catalog_key == "unsupported":
            limits.append(
                "Requested furniture is outside the queen-bed, desk and wardrobe catalog."
            )
            return outcome("unsupported")
        if not _source(item.source_text, description) or not re.search(
            rf"\b{_ALIASES[item.catalog_key]}\b", item.source_text, re.I
        ):
            questions.append(f"Confirm the {item.catalog_key} catalog mapping.")
        quantity = item.quantity
        if quantity is None:
            questions.append(f"Specify the quantity of {item.catalog_key}.")
            continue
        if quantity > 1:
            word = (
                "zero",
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
            )[quantity]
            if not re.search(rf"\b(?:{quantity}|{word})\b", item.source_text, re.I):
                questions.append(
                    f"Confirm the quantity of {item.catalog_key}; multiple items need explicit evidence."
                )
        source = catalog[item.catalog_key]
        size = {}
        defaults = []
        for field in ("width", "depth", "height"):
            explicit = getattr(item, field)
            if explicit is None:
                size[f"{field}_m"] = getattr(source, f"{field}_m")
                defaults.append(f"{field}={size[f'{field}_m']:g} m")
            else:
                value = length(explicit, f"{item.catalog_key} {field}")
                size[f"{field}_m"] = (
                    value if value is not None else getattr(source, f"{field}_m")
                )
        if defaults:
            assumptions.append(
                f"{item.catalog_key}: catalog defaults used for {', '.join(defaults)}."
            )
        for _ in range(quantity):
            counts[item.catalog_key] = counts.get(item.catalog_key, 0) + 1
            number = counts[item.catalog_key]
            furniture.append(
                Furniture(
                    id=f"{source.id}-{number}",
                    name=source.name,
                    category=source.category,
                    x_m=0.0,
                    y_m=0.0,
                    **size,
                )
            )
    for preference in [
        *data.soft_preferences,
        *data.hard_constraints,
        *([data.style] if data.style else []),
    ]:
        if not _source(preference.source_text, description):
            questions.append(
                "Confirm a preference whose source was not present in the request."
            )
    if len(furniture) > 32:
        limits.append("The existing generator supports at most 32 furniture objects.")
        return outcome("unsupported")
    if questions:
        return outcome("needs_clarification")
    try:
        room = Room(
            id="requirements-room",
            name=data.room_type.capitalize(),
            width_m=dimensions["width"],
            depth_m=dimensions["depth"],
            ceiling_height_m=dimensions["ceiling_height"],
            doors=doors,
            windows=windows,
        )
        specification = RoomDesign(
            room=room, furniture=furniture, name="Interpreted requirements"
        )
    except ValidationError:
        questions.append(
            "Correct room/opening dimensions: openings must fit wall endpoints and ceiling height."
        )
        return outcome("needs_clarification")
    assumptions.append(
        "Furniture X/Y starts at (0, 0) as an unplaced request; the deterministic generator replaces it."
    )
    return outcome("ready", specification)
