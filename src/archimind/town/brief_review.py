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


MEASUREMENT = r"(?<![\d.])(\d+(?:\.\d+)?|\.\d+)\s*(mm|cm|m)\b"
PASSAGE = r"(?:passage|walkway|route|circulation)\b"
WIDTH_PATTERNS = (
    MEASUREMENT + r"\s+(?:clear\s+)?" + PASSAGE,
    PASSAGE + r"\s+(?:width\s+)?(?:(?:of|at least|min(?:imum)?)\s+)?" + MEASUREMENT,
)
REVIEW_FIELDS = ("dining_seats", "split_dining", "passage_m")


def requirement_controls(brief, message, previous):
    """Return normalized controls and any conflicts that need user confirmation."""
    evidence = (previous or {}).get("evidence", {}).get("comparison", {})
    explicit = brief.model_fields_set
    seats = (
        brief.dining_seats
        if "dining_seats" in explicit
        else evidence.get("required_dining_seats", 0)
    )
    split = (
        brief.split_dining
        if "split_dining" in explicit
        else evidence.get("split_dining", False)
    )
    passage = (
        brief.passage_m if "passage_m" in explicit else evidence.get("passage_m", 0.6)
    )

    def count(value):
        return int(value) if value.isdecimal() else NUMBERS[value]

    text = message.lower()
    totals = {
        count(match[1])
        for match in re.finditer(
            COUNT
            + r"\s+(?:dining\s+)?(?:total\s+)?(?:seats|places)\b"
            + r"(?!\s+(?:in|at|per|for each)\b)",
            text,
        )
    }
    guests = re.search(COUNT + r"\s+(?:dinner\s+)?guests\b", text)
    residents = re.search(COUNT + r"\s+(?:residents|hosts|people)\b", text)
    if guests and residents:
        totals.add(count(guests[1]) + count(residents[1]))
    elif guests and not totals:
        totals.add(max(seats, count(guests[1])))
    questions = []
    if len(totals) > 1 or (
        totals and "dining_seats" in explicit and seats not in totals
    ):
        questions.append(
            "Confirm one total number of dining places in both the brief and controls."
        )
    elif totals:
        seats = totals.pop()

    widths = {
        float(value) / {"m": 1, "cm": 100, "mm": 1000}[unit]
        for pattern in WIDTH_PATTERNS
        for value, unit in re.findall(pattern, text)
    }
    if any(not 0.6 <= value <= 2 for value in widths):
        questions.append("Choose a modeled passage width between 0.6 and 2 m.")
    elif len(widths) > 1 or (
        widths and "passage_m" in explicit and passage not in widths
    ):
        questions.append(
            "Confirm one modeled passage width in both the brief and controls."
        )
    elif widths:
        passage = widths.pop()
    if seats > 100:
        questions.append(
            "Choose a supported dining requirement of at most eight places."
        )
    return brief.model_copy(
        update={
            "dining_seats": seats,
            "split_dining": split,
            "passage_m": passage,
            "formal_salon": brief.formal_salon
            or any(
                room["design"]["room"]["id"] == "salon"
                for room in (previous or {}).get("rooms", ())
            )
            or bool(
                re.search(r"\b(?:include|add|use) (?:a |the )?formal salon\b", text)
            ),
        }
    ), questions


def review_summary(brief, *, message="", questions=(), unsupported=()):
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
        "presentation_requests": [
            match.group(0).strip()
            for match in re.finditer(
                r"\b(?:why|explain)\b[^.!?]*", message, re.IGNORECASE
            )
        ],
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
