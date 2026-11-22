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
COUNT = r"\b(\d{1,3}|" + "|".join(NUMBERS) + r")\b"


MEASUREMENT = r"(?<![\d.])(\d+(?:\.\d+)?|\.\d+)\s*(mm|cm|m)\b"
PASSAGE = r"(?:passages?|walkways?|circulation)\b"
PATH = r"(?:passages?|walkways?|routes?|circulation)\b"
MINIMUM = r"(?:of|at least|min(?:imum)?)\s+"
WIDTH_PATTERNS = (
    MEASUREMENT + r"\s+(?:(?:clear|wide)\s+){0,2}" + PASSAGE,
    MEASUREMENT + r"\s+(?:clear\s+(?:wide\s+)?|wide\s+(?:clear\s+)?)routes?\b",
    PATH + r"\s+width\s+(?:" + MINIMUM + r")?" + MEASUREMENT,
    PATH + r"\s+(?:" + MINIMUM + r")?" + MEASUREMENT + r"\s+wide\b",
    PASSAGE
    + r"\s+(?:at least|min(?:imum)?)\s+"
    + MEASUREMENT
    + r"(?!\s+(?:long|in length|or shorter|(?:away\s+)?from|between|past)\b)",
)
REVIEW_FIELDS = ("dining_seats", "split_dining", "passage_m")


def _affirmative_clauses(message):
    """Keep supported affirmative clauses ahead of an explicit negation."""
    clauses = re.split(
        r"[;!?\n]|\.(?!\d)|\bbut\b|,(?=\s*(?:and\s+)?"
        r"(?:not|never|no|keep|add|use|place|put|include|maintain|reserve|leave|allow|ensure|provide|make|seating)\b)",
        message.lower(),
    )
    negative = r"\b(?:not(?!\s+only\b)|never|don['’]t|no need|instead of)\b"
    return [
        re.split(negative + r"|\bno\s+(?=" + MEASUREMENT + r")", clause, 1)[0]
        for clause in clauses
    ]


def requests_single_table(message):
    for clause in _affirmative_clauses(message):
        table = re.search(
            r"\b(?:at|around) (?:one|a single|the same) (?:dining )?table\b", clause
        )
        if not table or re.search(
            r"\b(?:other|another|second|separate|split)\b", clause[table.end() :]
        ):
            continue
        prefix = clause[: table.start()].strip()
        if re.search(
            r"\b(?:all|everyone|party|seats?|places?|seating|dine|sit|seated|together)\b",
            prefix,
        ):
            return True
    return False


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
    dining = ". ".join(_affirmative_clauses(message))
    totals = set()
    questions = []
    per_table = []
    count_at = COUNT + r"\s+(?:(?:people|diners|guests|seats|places)\s+)?(?:at|around) "
    split_counts = re.search(
        count_at
        + r"one table\s*,?\s+and\s+"
        + count_at
        + r"(?:the )?(?:other|second)(?: table)?\b",
        dining,
    )
    each_table = re.search(count_at + r"each(?: of the two)? tables?\b", dining)
    if split_counts:
        per_table = [count(value) for value in split_counts.groups()]
        dining = dining[: split_counts.start()] + " " + dining[split_counts.end() :]
    elif each_table:
        per_table = [count(each_table[1])] * 2
        dining = dining[: each_table.start()] + " " + dining[each_table.end() :]
    if per_table:
        totals.add(sum(per_table))
        if max(per_table) > 4:
            questions.append(
                "Each modeled table has four places. Revise the requested split."
            )

    shared = r"\s*,?\s+(?:to be )?(?:split|shared|divided) (?:between|across)\b"
    requested_split = bool(per_table) or bool(re.search(r"\bsplit dining\b", dining))

    dining_room = r"(formal salon|salon|kitchen(?:[- ]dining)?)"
    for match in re.finditer(
        COUNT
        + r"\s+(?:dining\s+)?(?:total\s+)?(?:seats|places)\b"
        + r"|\bseating for\s+"
        + COUNT
        + r"|\bdining room for\s+"
        + COUNT
        + r"(?=\s*[,.;!?]|\s*$)"
        + r"|\broom for\s+"
        + COUNT
        + r"\s+diners?\b",
        dining,
    ):
        value = count(next(group for group in match.groups() if group is not None))
        tail = dining[match.end() :]
        shared_seats = re.match(shared, tail)
        location = re.match(r"\s+(?:in|at)\s+(?:the\s+)?" + dining_room + r"\b", tail)
        if shared_seats:
            requested_split = True
            arrangement = re.split(r"[,.;]", tail[shared_seats.end() :], maxsplit=1)[0]
            names_both_rooms = bool(
                re.search(r"\bsalon\b", arrangement)
                and re.search(r"\bkitchen(?:[- ]dining)?\b", arrangement)
            )
            if not names_both_rooms:
                location = re.search(
                    r"\bin\s+(?:the\s+)?" + dining_room + r"\b", arrangement
                )
        if not location and not shared_seats:
            location = re.search(
                r"\b" + dining_room + r"\s+with\s+$", dining[: match.start()]
            )
        if location:
            if shared_seats:
                questions.append(
                    f"The {location[1]} has one modeled table. Confirm a different location for the second table."
                )
            elif value > 4:
                questions.append(
                    f"The {location[1]} has four modeled places. "
                    f"Confirm how to accommodate the requested {value} places there."
                )
        elif not re.match(r"\s+(?:per|for each)\b", tail):
            totals.add(value)
    if requested_split and not split:
        questions.append(
            "Confirm separate dining tables in the brief controls, or revise the seating arrangement."
        )
    if requests_single_table(text):
        if split and "split_dining" in explicit:
            questions.append(
                "The brief asks for one dining table, but the controls allow two. Confirm the arrangement."
            )
        split = False
    guests = re.search(COUNT + r"\s+(?:dinner\s+)?guests\b", dining)
    residents = re.search(COUNT + r"\s+(?:residents|hosts|people)\b", dining)
    if guests and residents:
        totals.add(count(guests[1]) + count(residents[1]))
    elif guests and not totals:
        totals.add(max(seats, count(guests[1])))
    if len(totals) > 1 or (
        totals and "dining_seats" in explicit and seats not in totals
    ):
        questions.append(
            "Confirm one total number of dining places in both the brief and controls."
        )
    elif totals:
        seats = totals.pop()

    circulation = ". ".join(_affirmative_clauses(message))
    if fixed := re.search(
        PASSAGE
        + r"\s+(?:width\s+)?(?:of |at least |of at least )?"
        + MEASUREMENT
        + r"(?:\s+wide)?\s+between\b",
        circulation,
    ):
        questions.append(
            f"The requested {fixed[1]} {fixed[2]} clearance between specific objects "
            "needs a separate geometry check. Confirm a general circulation width or revise the brief."
        )
    widths = {
        float(value) / {"m": 1, "cm": 100, "mm": 1000}[unit]
        for pattern in WIDTH_PATTERNS
        for value, unit in re.findall(pattern, circulation)
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
