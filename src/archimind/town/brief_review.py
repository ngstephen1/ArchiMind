"""Preserve explicit seating and metric circulation needs independently of the model."""

import re

NUMBERS = {
    word: number
    for number, word in enumerate(
        (
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
        )
    )
}
COUNT = r"\b(\d{1,3}|" + "|".join(NUMBERS) + r")"


def requirement_controls(brief, message, previous):
    evidence = (previous or {}).get("evidence", {}).get("comparison", {})
    seats = brief.dining_seats or evidence.get("required_dining_seats", 0)
    split = brief.split_dining or evidence.get("split_dining", False)
    passage = max(brief.passage_m, evidence.get("passage_m", 0.6))

    def count(value):
        return int(value) if value.isdecimal() else NUMBERS[value]

    text = message.lower()
    explicit = re.search(
        COUNT + r"\s+(?:dining\s+)?(?:total\s+)?(?:seats|places)\b", text
    )
    guests = re.search(COUNT + r"\s+(?:dinner\s+)?guests\b", text)
    residents = re.search(COUNT + r"\s+(?:residents|hosts|people)\b", text)
    if explicit:
        seats = count(explicit[1])
    elif guests and residents:
        seats = count(guests[1]) + count(residents[1])
    elif guests:
        seats = max(seats, count(guests[1]))
    widths = re.findall(
        r"(\d+(?:\.\d+)?)\s*(m|cm|mm)\b\s*(?:clear\s+)?(?:passage|walkway|route|circulation)\b",
        text,
    )
    for value, unit in widths:
        passage = max(passage, float(value) / {"m": 1, "cm": 100, "mm": 1000}[unit])
    return brief.model_copy(
        update={
            "dining_seats": seats,
            "split_dining": split,
            "passage_m": passage,
            "formal_salon": brief.formal_salon
            or bool(
                re.search(r"\b(?:include|add|use) (?:a |the )?formal salon\b", text)
            ),
        }
    )


def review_summary(brief, *, questions=(), unsupported=()):
    requirements = [
        f"Lot {brief.width:g} × {brief.depth:g} m",
        f"{brief.passage_m:g} m modeled passage",
    ]
    if brief.formal_salon:
        requirements.append("Formal salon")
    if brief.dining_seats:
        arrangement = "across two tables" if brief.split_dining else "at one table"
        requirements.append(f"{brief.dining_seats} dining places {arrangement}")
    if brief.locks:
        requirements.append("Keep " + ", ".join(brief.locks))
    preferences = [
        f"{goal.room} {goal.relation} {goal.target}" for goal in brief.room_goals
    ]
    if brief.priority != "balanced":
        preferences.append(brief.priority)
    preferences.append(brief.style.replace("_", " "))
    return {
        "requirements": requirements,
        "preferences": preferences,
        "questions": [q for q in questions if q],
        "unsupported": list(unsupported),
    }


def provider_brief(message):
    """Route known seating and explanation clauses to the app before interpretation."""
    hosting = (
        r"(?:design a home for )?"
        + COUNT
        + r" (?:people who work from home|residents|hosts) (?:and host|and) "
        + COUNT
        + r" (?:dinner )?guests(?: for dinner)?[.!?]?"
    )
    confirmed = (
        r"use two four-seat tables in the formal salon and kitchen-dining room for "
        + COUNT
        + r" (?:residents|hosts) and "
        + COUNT
        + r" dinner guests[.!?]?"
    )
    program = r"include a formal salon (?:and a separate living room|as well as the living room)[.!?]?"
    explanation = r"(?:and )?explain (?:the placements|which placement decisions you can support from the floor plan)[.!?]?"
    remaining = re.sub(
        r"(?:^|(?<=[.!?])\s+)(?:"
        + "|".join((hosting, confirmed, program))
        + r")(?=\s|$)",
        " ",
        message,
        flags=re.IGNORECASE,
    )
    return re.sub(explanation + r"(?=\s*$)", "", remaining, flags=re.IGNORECASE).strip()
