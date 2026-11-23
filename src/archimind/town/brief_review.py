"""Preserve explicit seating and metric circulation needs independently of the model."""

import re

from .design import Brief

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
FIXED_PASSAGE = (
    r"(?:"
    + "|".join(WIDTH_PATTERNS[:2])
    + r"|"
    + PASSAGE
    + r"\s+(?:width\s+)?(?:of |at least |of at least )?"
    + MEASUREMENT
    + r")(?:\s+wide)?\s+between\b"
    + r"|"
    + MEASUREMENT
    + r"\s+routes?\s+between\b[^.;!?\n]*"
    + r"\b(?:measured|(?:the\s+)?(?:clear\s+)?width(?:\s+(?:is|taken|measured|specified)){0,3})"
    r"\s+across\s+(?:the\s+)?(?:open\s+)?gap\b"
)
PARTY = r"\s+(?:people|persons?|guests?|diners?|hosts?|residents?)\b"
# Two or more groups that sit together, e.g. "two guests and two hosts".
GROUP = (
    COUNT + r"\s+(?:dinner\s+)?(?:people|persons?|guests?|diners?|residents?|hosts?)\b"
)
GROUPS = GROUP + r"(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+)" + GROUP + r")+"
REVIEW_FIELDS = ("dining_seats", "split_dining", "passage_m")
ROOM_NAMES = (
    r"bedroom|study|living(?: room)?|kitchen(?:[- ]dining)?(?: room)?|bathroom|salon"
)
ROOMS = f"({ROOM_NAMES})"
DINING_CONTEXT = (
    r"\b(?:seats?|seating|places|dining|dine|diners?|dinner|tables?|"
    r"eat\s+together|(?:share|have)\s+(?:a\s+)?(?:meal|lunch|breakfast))\b"
)
OFFSITE_MEAL = (
    r"\b(?:breakfast|lunch|dinner|meal|(?:eat|dine)(?:\s+together)?)"
    r"\s+(?:off[- ]site|away from home|at (?:a |the )?restaurant|at work)\b"
)
SALON_ACTION = (
    r"\b(?:include|add|use|with) (?:a |the )?(?:(?:separate|dedicated|additional) )?"
    r"formal salon\b"
)
SALON_EXCLUSION = (
    r"\s*(?:please\s+)?(?:avoid|exclude|omit|skip|do not (?:include|add)|"
    r"don['’]t (?:include|add))\s+(?:(?:a|the)\s+)?"
    r"(?:plan\s+with\s+(?:(?:a|the)\s+)?)?"
    r"(?:(?:separate|dedicated|additional)\s+)?formal salon\b"
)
SALON_ONLY = r"(?:a\s+)?formal salon(?:,?\s+please)?[.!;]?"
FIVE_STANDARD_ROOMS = r"\b(?:keep|use) (?:the )?five standard rooms\b"
SALON_DECLINE = (
    r"\s*(?:(?:actually|no),\s*){0,2}"
    r"(?:no|not (?:needed|required|wanted)|" + FIVE_STANDARD_ROOMS + r"|"
    r"leave (?:it|(?:the )?(?:formal )?salon) out|"
    r"(?:omit|skip|exclude) (?:it|(?:the )?(?:formal )?salon)|"
    r"(?:no|without) (?:a |the )?(?:formal )?salon)"
    r"(?:,?\s+(?:please|instead|for now|after all|this time|today)){0,3}"
    r"(?:,\s*(?:keep|use) (?:the )?five standard rooms)?"
    r"\s*[.!;]?\s*$"
)
STATEMENT_BREAK = r"(?<=[.!?])\s+|(?<=;)\s*|\n+"
CONDITIONAL_CONTINUATION = (
    r"\s*(?:but\s+)?"
    r"(?!(?:if|when)\s+(?:possible|practical|convenient|appropriate)\s*,)"
    r"(?:(?:only\s+)?(?:if|when)|unless|provided(?:\s+that)?)\b"
)
SALON_SEGMENT_BREAK = STATEMENT_BREAK + r"|,?\s+but\s+"


# A verb acting on a specific door or window, e.g. "keep the bedroom window" or
# "add a second door". Spatial words end the object, so "keep the bedroom near
# the door" and "move the desk closer to its window" are not opening requests.
OPENING_OBJECT = (
    r"((?:(?!(?:near|away|from|to|by|next|close|closer|beside|facing|towards?|with"
    r"|and|or|in|on|at)\b)[\w-]+\s+){0,3}?)(doors?|doorways?|windows?|openings?)\b"
)


OPENING_VERB = r"keep|preserve|move|relocate|shift|add|remove|block|widen|enlarge"
OPENING_REQUEST = r"\b(" + OPENING_VERB + ")" + r"\s+" + OPENING_OBJECT
COORDINATED_OPENING = re.compile(
    r"(?:\s*,\s*(?:(?:and|or)\s+)?|\s+(?:and|or)\s+)"
    + r"(?=(?:the|a|an|that|those|its|existing|original|current|historic|front|back|"
    r"rear|side|main|north|south|east|west|all|both|another|"
    + ROOM_NAMES
    + r"|doors?|doorways?|windows?|openings?)\b)"
    + OPENING_OBJECT
)


def _affirmative_clauses(message, *, retain_dining_context=False):
    """Keep supported affirmative clauses ahead of an explicit negation."""
    message = re.sub(
        r"\b(?:don['’]t|do not|never)\b[^.;!?\n]*,\s*or\b[^.;!?\n]*",
        "",
        message.lower(),
    )
    message = re.sub(
        r"\b(?:cannot|can not|can['’]t) (?:do without|compromise on)\b",
        "need",
        message,
    )

    def replace_rationale(match):
        reason = match[0]
        if (
            retain_dining_context
            and reason.startswith("because")
            and re.search(r"\b(?:dine|eat) together\b", reason)
            and not re.search(OFFSITE_MEAL, reason)
            and not re.search(
                r"\b(?:not|never|don['’]t|won['’]t|can['’]t|cannot)\b", reason
            )
        ):
            return " dine together "
        return " "

    message = re.sub(
        r"\b(?:because|otherwise)\b(?:(?!\bbut\b|[;!?,\n]|\.(?!\d)).)*",
        replace_rationale,
        message,
    )
    clauses = re.split(
        r"[;!?\n]|\.(?!\d)|\bbut\b|,(?=\s*(?:(?:and|so)\s+)?"
        r"(?:not|never|no|keep|add|use|place|put|include|maintain|reserve|leave|allow|ensure|provide|make|seating)\b)",
        message,
    )
    negative = r"\b(?:not(?!\s+only\b)|never|don['’]t|cannot|can['’]t|won['’]t|mustn['’]t|no need|instead of)\b"
    return [
        re.split(negative + r"|\bno\s+(?=" + MEASUREMENT + r")", clause, maxsplit=1)[0]
        for clause in clauses
        if not re.search(
            r"\b(?:won['’]t|will not|cannot|can['’]t) (?:work|fit)\b"
            r"|\b(?:is|are) not (?:acceptable|feasible)\b",
            clause,
        )
    ]


def salon_choice(message):
    """Return the last explicit program decision and its source, when recognized."""
    sentences = re.split(SALON_SEGMENT_BREAK, message)
    following_sentences = sentences[1:] + [""]
    continuations = [*sentences, "", ""][2:]
    decision = None
    statement = None
    conditional_correction = False
    previous = ""
    for sentence, following, continuation in zip(
        sentences, following_sentences, continuations, strict=True
    ):
        wrapped_condition = not following.rstrip().endswith(
            (".", "?", "!", ";")
        ) and re.match(CONDITIONAL_CONTINUATION, continuation.lower())
        exclusion = re.match(SALON_EXCLUSION, sentence.lower())
        if (
            exclusion
            and not conditional_correction
            and not re.match(
                CONDITIONAL_CONTINUATION, sentence[exclusion.end() :].lower()
            )
        ):
            decision = False
            statement = sentence.strip()
        elif (
            not conditional_correction
            and re.match(SALON_DECLINE, sentence.lower())
            and (
                re.search(r"\bsalon\b|" + FIVE_STANDARD_ROOMS, sentence, re.IGNORECASE)
                or (decision is True and previous == statement)
            )
        ):
            decision = False
            statement = sentence.strip()
        elif not exclusion and (
            re.fullmatch(SALON_ONLY, sentence.strip().lower())
            or any(
                re.search(SALON_ACTION, clause)
                for clause in _affirmative_clauses(sentence)
            )
        ):
            decision = True
            statement = sentence.strip()
        conditional_correction = bool(wrapped_condition)
        previous = sentence.strip()
    return decision, statement


def _dining_clauses(clauses):
    for clause in clauses:
        if offsite := re.search(OFFSITE_MEAL, clause):
            home_request = re.search(
                r"\b(?:so|and)\s+(?:(?:we|i)\s+)?(?:need|want|require|add|provide)\b",
                clause[offsite.end() :],
            )
            if not home_request:
                continue
            clause = clause[offsite.end() + home_request.end() :]
            if not re.search(
                r"\b(?:at home|(?:in|at) (?:the )?(?:formal salon|"
                + ROOM_NAMES
                + r"))\b",
                clause,
            ):
                continue
        if re.search(DINING_CONTEXT, clause):
            yield clause


def requests_single_table(message):
    named_rooms = set()
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
            room = re.match(
                r"\s+in (?:the )?(?:formal )?(salon|kitchen(?:[- ]dining)?)\b",
                clause[table.end() :],
            )
            if not room:
                return True
            named_rooms.add(_room_id(room[1]))
    return len(named_rooms) == 1


def _widths(text):
    text = re.sub(FIXED_PASSAGE, "", text)
    return {
        float(value) / {"m": 1, "cm": 100, "mm": 1000}[unit]
        for pattern in WIDTH_PATTERNS
        for value, unit in re.findall(pattern, text)
    }


def requirement_controls(brief, message, previous, *, evaluate_passage=True):
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

    clauses = _affirmative_clauses(message)
    text = ". ".join(clauses)
    dining = ". ".join(
        _dining_clauses(_affirmative_clauses(message, retain_dining_context=True))
    )
    program, _ = salon_choice(message)
    salon_seating = program is not False and any(
        not re.match(
            r"\s*(?:if|unless|provided)\b|\s*when\b[^,.;!?]*\bsalon\b",
            sentence.lower(),
        )
        and re.search(r"\bformal salon\b", clause)
        for sentence in re.split(STATEMENT_BREAK, message)
        for clause in _dining_clauses(
            _affirmative_clauses(sentence, retain_dining_context=True)
        )
    )
    saved_salon = any(
        part["design"]["room"]["id"] == "salon"
        for part in (previous or {}).get("rooms", ())
    )
    salon = brief.formal_salon or saved_salon or program is True
    totals = set()
    questions = []
    if brief.compare_tradeoffs and program is False:
        if saved_salon:
            questions.append(
                "This saved project includes the formal salon. Start a new project by "
                "opening Town without the project and revision query parameters, "
                "then choose Design a home. You can also keep the salon in this revision."
            )
        elif brief.formal_salon:
            questions.append(
                "Confirm the five-room program by clearing the formal salon control."
            )
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
    kitchen_table = re.search(
        COUNT
        + PARTY
        + r"\s+(?:at|around) (?:one|a single|the same) (?:dining )?table"
        + r"\s+in (?:the )?kitchen(?:[- ]dining)?\b",
        dining,
    )
    single_table = requests_single_table(text)
    counted = set()
    room_minima = {}
    dining_room = r"(formal salon|salon|kitchen(?:[- ]dining)?)"
    for match in re.finditer(
        COUNT
        + r"\s+(?:(?:dining\s+)?(?:total\s+)?|total\s+dining\s+)(?:seats|places)\b"
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
        table_location = (
            r""
            if single_table
            else r"(?:(?:at|around) (?:one|a single|the same) (?:dining )?table\s+)?"
        )
        location = re.match(
            r"\s*" + table_location + r"(?:in|at)\s+(?:the\s+)?" + dining_room + r"\b",
            tail,
        )
        if not location and value <= 4:
            location = re.match(
                r"\s+(?:at|around) (?:one|a single|the same|a separate) (?:dining )?table"
                r"\s+in (?:the )?" + dining_room + r"\b",
                tail,
            )
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
            elif brief.compare_tradeoffs:
                room_minima.setdefault(
                    _room_id(location[1].removeprefix("formal ")), set()
                ).add(value)
        elif not re.match(r"\s+(?:per|for each)\b", tail):
            totals.add(value)
    if requested_split and not split:
        questions.append(
            "Confirm separate dining tables in the brief controls, or revise the seating arrangement."
        )
    if single_table:
        if split and "split_dining" in explicit:
            questions.append(
                "The brief asks for one dining table, but the controls allow two. Confirm the arrangement."
            )
        split = False
    for (start, end), total in parties:
        if (start, end) in counted:
            continue
        location = re.match(r"\s+in (?:the )?" + dining_room + r"\b", dining[end:])
        if location and total > 4:
            questions.append(
                f"The {location[1]} has four modeled places. "
                f"Confirm how to accommodate the requested {total} places there."
            )
        elif location:
            if brief.compare_tradeoffs:
                room_minima.setdefault(
                    _room_id(location[1].removeprefix("formal ")), set()
                ).add(total)
        else:
            totals.add(total)
    guests = not parties and re.search(COUNT + r"\s+(?:dinner\s+)?guests\b", dining)
    residents = re.search(COUNT + r"\s+(?:residents|hosts|people)\b", dining)
    if guests and residents:
        totals.add(count(guests[1]) + count(residents[1]))
    elif guests and not totals:
        totals.add(max(seats, count(guests[1])))
    if "salon" in room_minima and salon_seating:
        salon = True
    if kitchen_table and brief.compare_tradeoffs:
        amount = next(
            (
                total
                for (start, stop), total in parties
                if start <= kitchen_table.start() < stop
            ),
            count(kitchen_table[1]),
        )
        if amount > 4:
            questions.append(
                f"The kitchen-dining room has four modeled places. "
                f"Confirm how to accommodate the requested {amount} places there."
            )
        elif not salon:
            questions.append(
                f"The brief requests {amount} dining places in the kitchen-dining room. "
                "The five-room program has no modeled dining table there. "
                "Confirm the six-room program or revise the seating requirement."
            )
    if room_minima:
        for room, counts in room_minima.items():
            if len(counts) > 1:
                questions.append(
                    f"Confirm one minimum number of dining places for the {room}."
                )
            if not salon:
                questions.append(
                    f"The five-room program has no modeled table in the {room}. "
                    "Confirm the six-room program or revise the seating requirement."
                )
        if len(room_minima) > 1 and not split:
            questions.append(
                "Confirm separate tables for the requested room-specific seating."
            )
        minimum = sum(max(counts) for counts in room_minima.values())
        if split and (requested_split or totals or seats):
            minimum += 2 - len(room_minima)
        if (
            totals
            and min(totals) < minimum
            or "dining_seats" in explicit
            and 0 < seats < minimum
        ):
            questions.append(
                "Confirm a total that covers the requested room-specific seating."
            )
        elif not totals and (not seats or seats < minimum):
            totals.add(minimum)
    if len(totals) > 1 or (
        totals and "dining_seats" in explicit and seats > 0 and seats not in totals
    ):
        questions.append(
            "Confirm one total number of dining places in both the brief and controls."
        )
    elif totals:
        seats = totals.pop()

    circulation = text if evaluate_passage else ""
    if fixed := re.search(FIXED_PASSAGE, circulation):
        measurement = re.search(MEASUREMENT, fixed[0])
        assert measurement is not None
        questions.append(
            f"The requested {measurement[1]} {measurement[2]} clearance between specific objects "
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
            "formal_salon": salon,
        }
    ), questions


def _room_id(name):
    word = name.split()[0]
    return "kitchen-dining" if word.startswith("kitchen") else word


def _opening_room(clause, match, words, fronted, *, connecting_door):
    """Name the room of one opening request, e.g. "the bedroom window"."""
    qualifiers = "in|of|for|on|to" if connecting_door else "in|of|for|on"
    after = (
        r"(?:\s+and\s+(?:the\s+)?(?:doors?|doorways?|windows?|openings?))?"
        rf"\s+(?:{qualifiers})\s+(?:the\s+)?" + ROOMS + r"\b"
    )
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
            objects = [(match, words, noun)]
            end = match.end()
            while True:
                qualifier = re.match(
                    r"\s+(?:in|of|for|on|to)\s+(?:the\s+)?" + ROOMS + r"\b",
                    clause[end:],
                )
                if qualifier:
                    end += qualifier.end()
                continuation = COORDINATED_OPENING.match(clause, end)
                if not continuation:
                    break
                words, noun = continuation.groups()
                objects.append((continuation, words, noun))
                end = continuation.end()
            room_id = fronted
            for item, words, noun in objects:
                room_id = _opening_room(
                    clause,
                    item,
                    words,
                    room_id,
                    connecting_door=verb in {"keep", "preserve"}
                    and noun.startswith("door"),
                )
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
    for sentence in re.split(STATEMENT_BREAK, message.strip()):
        if (
            sentence
            and re.search(pattern, sentence, re.IGNORECASE)
            and accepts(sentence)
        ):
            return sentence.strip()
    return None


def _source(
    requirement, message, pattern, field, controls, carried, inherited, accepts, quote
):
    if quote or (pattern and (quote := _statement(message, pattern, accepts))):
        return dict(requirement=requirement, origin="brief", statement=quote)
    if field in controls:
        origin = "controls"
    elif inherited:
        origin = "saved revision"
    elif carried:
        origin = "interpreted"
    else:
        origin = "default"
    return dict(requirement=requirement, origin=origin, statement=None)


def _dining_statement_matches(brief, sentence):
    stated, questions = requirement_controls(
        Brief(
            formal_salon=brief.formal_salon,
            split_dining=brief.split_dining,
            compare_tradeoffs=brief.compare_tradeoffs,
        ),
        sentence,
        None,
        evaluate_passage=False,
    )
    return not questions and (stated.dining_seats, stated.split_dining) == (
        brief.dining_seats,
        brief.split_dining,
    )


def _dining_quote(brief, message):
    single = _statement(
        message,
        DINING_CONTEXT,
        lambda sentence: _dining_statement_matches(brief, sentence),
    )
    if single:
        return single
    # Preserve separators between adjacent relevant excerpts and skip unrelated prose.
    excerpts = []
    end = cursor = 0
    for sentence in re.split(STATEMENT_BREAK, message):
        start = message.index(sentence, cursor)
        cursor = start + len(sentence)
        if any(
            _dining_clauses(_affirmative_clauses(sentence, retain_dining_context=True))
        ):
            gap = message[end:start]
            if excerpts:
                excerpts.append(gap if not gap.strip() else "\n")
            excerpts.append(sentence)
            end = start + len(sentence)
    combined = "".join(excerpts).strip()
    if combined and _dining_statement_matches(brief, combined):
        return combined
    return None


LOT_SIZE = (
    r"\b(\d+(?:\.\d+)?)\s*(?:m|metres?|meters?)?\s*(?:by|x|×)\s*"
    r"(\d+(?:\.\d+)?)\b"
)


def _lot_statement_matches(brief, sentence):
    return any(
        re.search(r"\blot\b", clause)
        and any(
            (float(width), float(depth)) == (brief.width, brief.depth)
            for width, depth in re.findall(LOT_SIZE, clause)
        )
        for clause in _affirmative_clauses(sentence)
    )


def _lock_statement_matches(room_id, sentence):
    pattern = (
        r"\b(?:keep|lock|preserve)\s+(?:the\s+)?"
        + ROOMS
        + r"\b(?=\s*(?:$|[.!?,;]|(?:(?:exactly )?(?:where|as) it is|"
        r"unchanged|in place|and)\b))"
    )
    return any(
        _room_id(name) == room_id
        for clause in _affirmative_clauses(sentence)
        for name in re.findall(pattern, clause)
    )


def review_summary(
    brief,
    *,
    message="",
    questions=(),
    unsupported=(),
    previous=None,
    controls=frozenset(),
    control_locks=None,
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
        quote=None,
        active_controls=controls,
    ):
        requirements.append(text)
        sources.append(
            _source(
                text,
                message,
                pattern,
                field,
                active_controls,
                interpreted,
                inherited,
                accepts,
                quote,
            )
        )

    require(
        f"Lot {brief.width:g} × {brief.depth:g} m",
        LOT_SIZE,
        "width",
        inherited=bool(previous),
        accepts=lambda sentence: _lot_statement_matches(brief, sentence),
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
        salon_requested, salon_statement = salon_choice(message)
        require(
            "Formal salon",
            None,
            "formal_salon",
            inherited="salon" in saved_rooms,
            interpreted=True,
            quote=salon_statement if salon_requested else None,
        )
    if brief.dining_seats:
        arrangement = "across two tables" if brief.split_dining else "at one table"
        require(
            f"{brief.dining_seats} dining places {arrangement}",
            None,
            "dining_seats",
            inherited=brief.dining_seats == comparison.get("required_dining_seats"),
            quote=_dining_quote(brief, message),
        )
    for room_id in brief.locks:
        require(
            "Keep " + room_id,
            r"\b(?:keep|lock|preserve)\b",
            "locks",
            interpreted=True,
            accepts=lambda sentence: _lock_statement_matches(room_id, sentence),
            active_controls=(
                controls - {"locks"}
                if control_locks is not None and room_id not in control_locks
                else controls
            ),
        )
    assumptions = []
    if sources[1]["origin"] == "default":
        assumptions.append(
            "0.6 m modeled passage is Town's default when there is no accepted width."
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
