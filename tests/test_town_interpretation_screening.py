"""Model interpretations are screened against Town's controls and the request text."""

from types import SimpleNamespace

import pytest

from archimind.town import service
from archimind.town.brief_review import requirement_controls, review_summary
from archimind.town.design import Brief, RoomGoal, generate


def live_answer(**fields):
    def answer(schema, *args, **kwargs):
        response = dict(
            priority="balanced", style="scandinavian", clarification="", unsupported=[]
        )
        if "lock_rooms" in schema.model_fields:
            response.update(lock_rooms=[], lock_furniture=[])
        return schema.model_validate(response | fields)

    return answer


def review_request(message, **brief):
    return SimpleNamespace(
        brief=Brief(compare_tradeoffs=True, **brief),
        agent_team=False,
        live=True,
        message=message,
    )


@pytest.fixture(scope="module")
def saved_home():
    return generate(Brief(width=15, depth=16, formal_salon=True))[0]


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))

    def use(**fields):
        monkeypatch.setattr(service.provider, "request", live_answer(**fields))

    return use


def test_comparing_supported_priorities_is_a_presentation_request(provider):
    message = (
        "Keep the bathroom near the bedroom and the study far from the living room. "
        "Compare how each option handles those two goals."
    )
    provider(unsupported=["Compare how each option handles those two goals"])
    brief = service.interpret(review_request(message, width=15, depth=16), None)
    assert brief.compare_tradeoffs
    review = review_summary(brief, message=message)
    assert review["presentation_requests"] == [
        "Compare how each option handles those two goals"
    ]


def test_comparison_of_unmodeled_performance_stays_unsupported(provider):
    message = "Compare which option keeps sound out of the study."
    provider(unsupported=["Compare acoustic isolation of the study"])
    with pytest.raises(service.BriefClarification, match="Unsupported") as exc:
        service.interpret(review_request(message, width=15, depth=16), None)
    assert exc.value.reviewed["status"] == "unsupported"


def test_kitchen_dining_room_name_is_not_a_seating_request():
    parsed = SimpleNamespace(formal_salon=True)
    plain = SimpleNamespace(
        message="Put the kitchen-dining room next to the salon.",
        brief=Brief(formal_salon=True),
    )
    assert "dining seats" not in service.clarification_guidance(plain, parsed)
    hosting = SimpleNamespace(
        message="Seat our dinner guests in the salon.", brief=Brief(formal_salon=True)
    )
    assert "four dining seats" in service.clarification_guidance(hosting, parsed)


def test_desk_move_ignores_inferred_lock_and_unrequested_room_goals(
    provider, saved_home
):
    message = (
        "Without touching the bathroom, slide the study desk nearer to its window."
    )
    provider(
        closer_study_desk=True,
        lock_rooms=["bathroom", "study"],
        lock_furniture=["writing-suite"],
        room_goals=[
            dict(room="study", relation="near", target="study"),
            dict(room="living", relation="far", target="salon"),
        ],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    brief = service.interpret(request, saved_home)
    assert brief.closer_study_desk
    assert brief.locks == ["bathroom"]
    assert brief.room_goals == []


def test_requested_room_goals_still_block_a_furniture_move(provider, saved_home):
    message = "Move the study desk closer to its window and keep the living room far from the salon."
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="living", relation="far", target="salon")],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    with pytest.raises(service.BriefClarification, match="separately"):
        service.interpret(request, saved_home)


def test_self_referencing_goal_is_dropped_for_a_new_home(provider):
    provider(
        room_goals=[
            dict(room="study", relation="far", target="study"),
            dict(room="study", relation="far", target="living"),
        ]
    )
    brief = service.interpret(
        review_request("A calm study for remote work.", width=15, depth=16), None
    )
    assert brief.room_goals == [RoomGoal(room="study", relation="far", target="living")]


@pytest.mark.parametrize(
    ("text", "seats"),
    [
        ("Seven relatives must eat together at one shared table.", 7),
        ("Four adults sit around the same table.", 4),
        ("Three friends need to dine at one table.", 3),
        ("We have friends over on weekends.", 0),
    ],
)
def test_party_wording_keeps_the_seat_count(text, seats):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True), text, None
    )
    assert (brief.dining_seats, questions) == (seats, [])


def test_single_table_conflict_keeps_seats_and_explains_the_table_limit():
    text = "Seven relatives must eat together around the same table."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert (brief.dining_seats, brief.split_dining) == (7, False)
    (question,) = questions
    assert "7 places at one dining table" in question
    assert "four places" in question
    review = review_summary(brief, message=text, questions=questions)
    assert "7 dining places at one table" in review["requirements"]


# Review findings on #111.


def test_listed_room_lock_survives_a_move_in_that_room(provider, saved_home):
    message = "Keep the bathroom and study unchanged. Move the study desk closer to its window."
    provider(closer_study_desk=True, lock_rooms=["bathroom", "study"])
    request = review_request(message, width=15, depth=16, formal_salon=True)
    with pytest.raises(service.BriefClarification, match="unlock its study"):
        service.interpret(request, saved_home)


def test_keep_one_room_and_move_another_is_not_a_lock_on_the_moved_room():
    message = "Keep the bathroom and move the study desk closer to its window."
    assert service._asks_to_keep(message, "bathroom")
    assert not service._asks_to_keep(message, "study")


@pytest.mark.parametrize(
    "objection",
    [
        "Comparison of one-storey and two-storey layouts",
        "Compare a garage option",
        "Compare the two plans",
    ],
)
def test_comparisons_town_cannot_produce_stay_unsupported(provider, objection):
    provider(unsupported=[objection])
    with pytest.raises(service.BriefClarification, match="Unsupported"):
        service.interpret(
            review_request("Compare the plans.", width=15, depth=16), None
        )


def test_shared_table_without_a_verb_conflicts_with_split_control():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Six adults at one shared table.",
        None,
    )
    assert (brief.dining_seats, brief.split_dining) == (6, False)
    assert questions and "6 places at one dining table" in questions[0]


def test_two_seated_groups_at_separate_tables_keep_both_counts():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "Four adults sit at one table and four adults sit at the other table.",
        None,
    )
    assert brief.dining_seats == 8
    assert any("separate dining tables" in q for q in questions)


def test_room_synonym_keeps_a_requested_goal_during_a_move(provider, saved_home):
    message = "Move the study desk closer to its window and keep the lounge far from the salon."
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="living", relation="far", target="salon")],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    with pytest.raises(service.BriefClarification, match="separately"):
        service.interpret(request, saved_home)


@pytest.mark.parametrize(
    "text",
    [
        "Two adults and two friends live here; put the kitchen-dining room by the garden.",
        "Six friends will eat together at one shared table at a restaurant.",
    ],
)
def test_household_and_offsite_wording_adds_no_home_seats(text):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True), text, None
    )
    assert (brief.dining_seats, questions) == (0, [])


@pytest.mark.parametrize(
    ("text", "quoted"),
    [
        (
            "Seven of us eat together at one table.",
            "The brief asks for one dining table",
        ),
        ("Seven relatives eat together at one table.", "The brief asks for 7 places"),
    ],
)
def test_conflict_question_quotes_only_the_brief_count(text, quoted):
    _, questions = requirement_controls(
        Brief(
            compare_tradeoffs=True, formal_salon=True, split_dining=True, dining_seats=8
        ),
        text,
        None,
    )
    assert questions[0].startswith(quoted)
    assert "8 places" not in questions[0]


# Second review pass on #111.


@pytest.mark.parametrize(
    ("objection", "cleared"),
    [
        ("Compare the floor plans by bedroom-to-bathroom distance", True),
        ("Compare one-floor and two-floor distance", False),
        ("Comparison of one-storey and two-storey layouts", False),
    ],
)
def test_floor_plan_wording_is_not_a_storey_request(provider, objection, cleared):
    provider(unsupported=[objection])
    request = review_request("Compare the plans.", width=15, depth=16)
    if cleared:
        assert service.interpret(request, None).compare_tradeoffs
    else:
        with pytest.raises(service.BriefClarification, match="Unsupported"):
            service.interpret(request, None)


def test_household_groups_at_one_table_count_every_diner():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "Two adults and two friends eat together at one table.",
        None,
    )
    assert (brief.dining_seats, questions) == (4, [])


def test_contrasting_restaurant_clause_keeps_home_seating():
    brief, _ = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "At home we need four dining seats, even though we usually eat at one "
        "shared table at a restaurant.",
        None,
    )
    assert brief.dining_seats == 4


def test_work_table_is_not_a_single_dining_table():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Three adults work at one table in the study.",
        None,
    )
    assert (brief.dining_seats, brief.split_dining, questions) == (0, True, [])


def test_polite_move_after_a_keep_request_is_its_own_clause():
    message = "Keep the bathroom unchanged and please move the study desk."
    assert service._asks_to_keep(message, "bathroom")
    assert not service._asks_to_keep(message, "study")


def test_unchanged_layout_drops_inferred_goals_during_a_move(provider, saved_home):
    message = (
        "Leave the layout as it is; we host in the kitchen and salon. "
        "Just move the study desk closer to its window."
    )
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="kitchen-dining", relation="near", target="salon")],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    brief = service.interpret(request, saved_home)
    assert brief.closer_study_desk and brief.room_goals == []


def test_goal_naming_only_one_other_room_is_dropped_during_a_move(provider, saved_home):
    message = "We often host in the kitchen. Move the study desk closer to its window."
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="kitchen-dining", relation="near", target="salon")],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    assert service.interpret(request, saved_home).room_goals == []


# Third review pass on #111.


def test_after_work_timing_keeps_the_single_table_requirement():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Six dining seats. Our family should sit together at one table after work.",
        None,
    )
    assert (brief.dining_seats, brief.split_dining) == (6, False)
    assert questions and "6 places at one dining table" in questions[0]


def test_same_size_layout_does_not_cancel_a_requested_room_move(provider, saved_home):
    message = (
        "Keep the layout the same size, but put the kitchen closer to the salon. "
        "Move the study desk closer to its window."
    )
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="kitchen-dining", relation="near", target="salon")],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    with pytest.raises(service.BriefClarification, match="separately"):
        service.interpret(request, saved_home)


def test_room_alias_keeps_an_explicit_placement_goal_during_a_move(
    provider, saved_home
):
    message = (
        "Move the study desk closer to its window and bring the bathroom closer "
        "to the primary suite."
    )
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="bathroom", relation="near", target="bedroom")],
    )
    request = review_request(message, width=15, depth=16, formal_salon=True)
    with pytest.raises(service.BriefClarification, match="separately"):
        service.interpret(request, saved_home)


@pytest.mark.parametrize(
    "objection",
    [
        "Compare bedroom-to-bathroom distance when they are on different levels",
        "Compare the distance from an upstairs bedroom to the bathroom",
        "Compare a split-level route between the study and living room",
    ],
)
def test_cross_level_comparisons_stay_unsupported(provider, objection):
    provider(unsupported=[objection])
    with pytest.raises(service.BriefClarification, match="Unsupported"):
        service.interpret(
            review_request("Compare the plans.", width=15, depth=16), None
        )


@pytest.mark.parametrize(
    ("text", "split", "seats", "question"),
    [
        (
            "Two adults and two children live here and we host six dinner guests",
            False,
            6,
            "",
        ),
        (
            "Our study group of six adults must eat together at one table.",
            True,
            6,
            "6 places at one dining table",
        ),
        ("During study sessions, the kids sit together at one table.", True, 0, ""),
        ("Provide a dining table for five guests and two children.", False, 7, ""),
        (
            "Seating for 2 - 4 attendees at one table in the salon.",
            False,
            0,
            "Choose one required",
        ),
        ("We need four seats. Compare seating for 2 - 4 visitors.", False, 4, ""),
        ("Seating for 4—2 adults and 2 children.", False, 4, ""),
        (
            "Dining for five guests and two children split between the salon and kitchen.",
            False,
            7,
            "Confirm separate dining tables",
        ),
    ],
)
def test_dining_evidence_preserves_confirmed_counts_and_arrangements(
    text, split, seats, question
):
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=split),
        text,
        None,
    )
    assert brief.dining_seats == seats
    assert len(questions) == bool(question)
    if question:
        assert question in questions[0]
    if "must eat" in text:
        assert not brief.split_dining


def test_turning_radius_comparison_remains_unsupported(provider):
    question = "Compare the alternatives against a 1.5 m wheelchair turning-radius goal"
    provider(unsupported=[question])
    with pytest.raises(service.BriefClarification, match="turning-radius"):
        service.interpret(review_request(question), None)


@pytest.mark.parametrize(
    "text",
    [
        "Could we check whether five attendees can sit at one table in the salon? Four dining seats are required.",
        "Four dining seats are required. Compare seating for 2 - 4 attendees at one table in the salon.",
    ],
)
def test_exploratory_seating_preserves_confirmed_split(text):
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=True), text, None
    )
    assert (brief.dining_seats, brief.split_dining, questions) == (4, True, [])


def test_comparison_of_both_floor_plans_is_supported(provider):
    provider(
        unsupported=["Compare study-to-living room distances in both floor plans."]
    )
    assert service.interpret(
        review_request("Compare both floor plans."), None
    ).compare_tradeoffs


@pytest.mark.parametrize(
    "prelude",
    [
        "We host friends near the kitchen island.",
        "Keep the layout the same size and arrangement. We host in the kitchen and salon.",
    ],
)
def test_incidental_room_mentions_do_not_add_goals_to_desk_edit(
    provider, saved_home, prelude
):
    provider(
        closer_study_desk=True,
        room_goals=[dict(room="kitchen-dining", relation="near", target="salon")],
    )
    request = review_request(
        prelude + " Move the study desk closer to its window.",
        width=15,
        depth=16,
        formal_salon=True,
    )
    assert service.interpret(request, saved_home).room_goals == []
