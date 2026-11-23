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
PARTY = r"\s+(?:people|persons|guests|diners)\b"
# Two or more groups that sit together, e.g. "two guests and two hosts".
GROUP = (
    COUNT + r"\s+(?:dinner\s+)?(?:people|persons?|guests?|diners?|residents?|hosts?)\b"
)
GROUPS = GROUP + r"(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+)" + GROUP + r")+"
REVIEW_FIELDS = ("dining_seats", "split_dining", "passage_m")
ROOMS = (
    r"(bedroom|study|living(?: room)?|kitchen(?:[- ]dining)?(?: room)?|bathroom|salon)"
)
# A verb acting on a specific door or window, e.g. "keep the bedroom window" or
# "add a second door". Spatial words end the object, so "keep the bedroom near
# the door" and "move the desk closer to its window" are not opening requests.
OPENING_REQUEST = (
    r"\b(keep|preserve|move|relocate|shift|add|remove|block|widen|enlarge)\s+"
    r"((?:(?!(?:near|away|from|to|by|next|close|closer|beside|facing|towards?|with"
    r"|and|or|in|on|at)\b)[\w-]+\s+){0,3}?)(doors?|doorways?|windows?|openings?)\b"
)


def _affirmative_clauses(message):
    """Keep supported affirmative clauses ahead of an explicit negation."""
    message = re.sub(
        r"\b(?:don['’]t|do not|never)\b[^.;!?\n]*,\s*or\b[^.;!?\n]*",
        "",
        message.lower(),
    )
    clauses = re.split(
        r"[;!?\n]|\.(?!\d)|\bbut\b|,(?=\s*(?:and\s+)?"
        r"(?:not|never|no|keep|add|use|place|put|include|maintain|reserve|leave|allow|ensure|provide|make|seating)\b)",
        message,
    )
    negative = r"\b(?:not(?!\s+only\b)|never|don['’]t|no need|instead of)\b"
    return [
        re.split(negative + r"|\bno\s+(?=" + MEASUREMENT + r")", clause, maxsplit=1)[0]
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
            r"\b(?:all|everyone|party|seats?|places?|seating|dine|sit|seated|together"
            r"|people|persons|guests|diners)\b",
            prefix,
        ):
            return True
    return False


def _widths(text):
    return {
        float(value) / {"m": 1, "cm": 100, "mm": 1000}[unit]
        for pattern in WIDTH_PATTERNS
        for value, unit in re.findall(pattern, text)
    }


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

    parties = [
        (party.span(), sum(count(group[1]) for group in re.finditer(GROUP, party[0])))
        for party in re.finditer(GROUPS, dining)
    ]
    counted = set()
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
        + r"\s+diners?\b"
        + r"|\bseat(?:ing)?\s+"
        + COUNT
        + PARTY
        + r"|"
        + COUNT
        + PARTY
        + r"\s+(?=(?:at|around) (?:one|a single|the same) (?:dining )?table\b)",
        dining,
    ):
        index = next(i for i, group in enumerate(match.groups(), 1) if group)
        value, end = count(match[index]), match.end()
        for (start, stop), total in parties:
            if start <= match.start(index) < stop:
                value, end = total, max(end, stop)
                counted.add((start, stop))
        tail = dining[end:]
        shared_seats = re.match(shared, tail)
        location = re.match(r"\s+(?:in|at)\s+(?:the\s+)?" + dining_room + r"\b", tail)
        if shared_seats:
            requested_split = True
            arrangement = tail[shared_seats.end() :].split(".", 1)[0]
            named_places = list(
                re.finditer(r"\bin\s+(?:the\s+)?" + dining_room + r"\b", arrangement)
            )
            named_pair = re.match(
                r"\s*(?:the\s+)?"
                + dining_room
                + r"\s*,?\s+and\s+(?:the\s+)?"
                + dining_room
                + r"\b",
                arrangement,
            )
            room_names = [place[1] for place in named_places]
            if named_pair:
                room_names.extend(named_pair.groups())
            names_both_rooms = any("salon" in name for name in room_names) and any(
                "kitchen" in name for name in room_names
            )
            if named_places and not names_both_rooms:
                location = named_places[0]
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
    totals.update(total for span, total in parties if span not in counted)
    guests = not parties and re.search(COUNT + r"\s+(?:dinner\s+)?guests\b", dining)
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
    widths = _widths(circulation)
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


def _room_id(name):
    word = name.split()[0]
    return "kitchen-dining" if word.startswith("kitchen") else word


def _opening_room(clause, match, fronted):
    """Name the room of one opening request, e.g. "the bedroom window"."""
    words = match[2]
    after = r"\s+(?:in|of|for|on)\s+(?:the\s+)?" + ROOMS + r"\b"
    before = re.findall(r"\b" + ROOMS + r"\b", clause[: match.start()])
    if own := re.search(r"\b" + ROOMS + r"\b", words) or re.match(
        after, clause[match.end() :]
    ):
        return _room_id(own[1])
    if before:
        return _room_id(before[-1])
    return fronted


def opening_questions(message, locks):
    """Ask before generation when the brief needs one specific door or window.

    Town generates door and window positions. A lock keeps a saved room's
    openings, so keeping the openings of a locked room is already satisfied.
    """
    questions = []
    fronted = None
    for clause in _affirmative_clauses(message):
        for match in re.finditer(OPENING_REQUEST, clause):
            verb, words, noun = match.groups()
            room_id = _opening_room(clause, match, fronted)
            if verb in {"keep", "preserve"} and room_id in locks:
                continue
            requested = f"{verb} {words}{noun}".strip()
            questions.append(
                f"Town places doors and windows itself and cannot guarantee a request to "
                f"{requested} for a specific door or window. Lock the room on a saved "
                "revision to keep its openings, or revise the brief."
            )
        # "In the bedroom, keep the window" names the room in its own clause.
        qualifier = re.fullmatch(
            r"\s*(?:in|for)\s+(?:the\s+)?" + ROOMS + r"\s*", clause
        )
        fronted = _room_id(qualifier[1]) if qualifier else None
    return questions


def _statement(message, pattern, accepts):
    """Return the user's sentence that states a requirement, if one does."""
    for sentence in re.split(r"(?<=[.!?;])\s+|\n+", message.strip()):
        if (
            sentence
            and re.search(pattern, sentence, re.IGNORECASE)
            and accepts(sentence)
        ):
            return sentence.strip()
    return None


def _source(
    requirement, message, pattern, field, controls, carried, inherited, accepts
):
    if pattern and (statement := _statement(message, pattern, accepts)):
        return dict(requirement=requirement, origin="brief", statement=statement)
    if field in controls:
        origin = "controls"
    elif inherited:
        origin = "saved revision"
    elif carried:
        origin = "interpreted"
    else:
        origin = "default"
    return dict(requirement=requirement, origin=origin, statement=None)


def review_summary(
    brief,
    *,
    message="",
    questions=(),
    unsupported=(),
    previous=None,
    controls=frozenset(),
):
    """Summarize the brief for confirmation before any layout is generated.

    Each requirement records where it came from: the user's own sentence, the
    brief controls, the saved revision, the interpreter, or a Town default.
    """
    comparison = (previous or {}).get("evidence", {}).get("comparison", {})
    saved_rooms = {r["design"]["room"]["id"] for r in (previous or {}).get("rooms", ())}
    requirements, sources = [], []

    def require(
        text,
        pattern,
        field,
        *,
        inherited=False,
        interpreted=False,
        accepts=lambda _: True,
    ):
        requirements.append(text)
        sources.append(
            _source(
                text, message, pattern, field, controls, interpreted, inherited, accepts
            )
        )

    require(
        f"Lot {brief.width:g} × {brief.depth:g} m",
        r"\d+(?:\.\d+)?\s*(?:m|metres?|meters?)?\s*(?:by|x|×)\s*\d",
        "width",
        inherited=bool(previous),
    )
    passage_inherited = "passage_m" in comparison and brief.passage_m == comparison.get(
        "passage_m"
    )
    require(
        f"{brief.passage_m:g} m modeled passage",
        "|".join(WIDTH_PATTERNS),
        "passage_m",
        inherited=passage_inherited,
        accepts=lambda sentence: (
            brief.passage_m in _widths(". ".join(_affirmative_clauses(sentence)))
        ),
    )
    if brief.formal_salon:
        require(
            "Formal salon",
            r"\bsalon\b",
            "formal_salon",
            inherited="salon" in saved_rooms,
            interpreted=True,
        )
    if brief.dining_seats:
        arrangement = "across two tables" if brief.split_dining else "at one table"
        require(
            f"{brief.dining_seats} dining places {arrangement}",
            r"\b(?:seats?|seating|places|tables?|guests|diners|dinner)\b",
            "dining_seats",
            inherited=brief.dining_seats == comparison.get("required_dining_seats"),
        )
    if brief.locks:
        require(
            "Keep " + ", ".join(brief.locks),
            r"\b(?:keep|lock|preserve)\b",
            "locks",
            interpreted=True,
        )
    assumptions = []
    if sources[1]["origin"] == "default":
        assumptions.append(
            "0.6 m modeled passage is Town's default because no width was stated."
        )
    assumptions.append(
        "Doors and windows are modeled by Town. Confirm existing openings, "
        "clearances and dimensions with a site survey."
    )
    if brief.locks:
        assumptions.append(
            "Locked rooms keep their saved placement, openings and furniture."
        )
    preferences = [
        f"{goal.room} {goal.relation} {goal.target}" for goal in brief.room_goals
    ]
    if brief.priority != "balanced":
        preferences.append(brief.priority)
    preferences.append(brief.style.replace("_", " "))
    questions = [q for q in questions if q]
    return {
        "status": "unsupported"
        if unsupported
        else "needs confirmation"
        if questions
        else "confirmed",
        "requirements": requirements,
        "sources": sources,
        "assumptions": assumptions,
        "preferences": preferences,
        "presentation_requests": [
            match.group(0).strip()
            for match in re.finditer(
                r"\b(?:why|explain)\b[^.!?]*", message, re.IGNORECASE
            )
        ],
        "questions": questions,
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
