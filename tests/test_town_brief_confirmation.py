"""Hard requirements are confirmed in the reviewed brief before any layout search."""

import copy
import json
import uuid
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from archimind.town import service
from archimind.town.api import app
from archimind.town.brief_review import (
    opening_questions,
    requirement_controls,
    review_summary,
)
from archimind.town.design import Brief, check_brief, generate


@pytest.fixture(scope="module")
def saved_home():
    return generate(Brief(width=15, depth=16, formal_salon=True))[0]


@pytest.mark.parametrize(
    "phrase",
    [
        "Seat six people at a single table in the formal salon.",
        "Six people at one table, please.",
        "Seat 6 guests at the same table.",
        "Seating six diners around one table.",
    ],
)
def test_single_table_party_size_is_retained(phrase):
    brief, questions = requirement_controls(Brief(formal_salon=True), phrase, None)
    assert (brief.dining_seats, brief.split_dining) == (6, False)
    assert questions == []


def test_people_count_without_a_table_is_not_a_seating_requirement():
    brief, _ = requirement_controls(Brief(), "Two people work from home.", None)
    assert brief.dining_seats == 0


def live_answer(**fields):
    def answer(schema, *args, **kwargs):
        response = dict(
            priority="balanced", style="scandinavian", clarification="", unsupported=[]
        )
        if "lock_rooms" in schema.model_fields:
            response.update(lock_rooms=[], lock_furniture=[])
        return schema.model_validate(response | fields)

    return answer


def review_request(message="", live=False, **brief):
    return SimpleNamespace(
        brief=Brief(compare_tradeoffs=True, **brief),
        agent_team=False,
        live=live,
        message=message,
    )


@pytest.mark.parametrize("split_dining", [True, False])
@pytest.mark.parametrize(
    "phrase",
    [
        "Five attendees must all sit together at one table in the formal salon.",
        "Seat five diners around a single table in the formal salon.",
        "Seat five at one table in the formal salon.",
    ],
)
def test_single_table_clarification_preserves_count_location_and_capacity(
    split_dining, phrase, monkeypatch
):
    monkeypatch.setattr(
        service.provider, "configuration", lambda _: pytest.fail("called provider")
    )
    request = review_request(
        phrase, live=True, formal_salon=True, split_dining=split_dining
    )
    brief, _ = requirement_controls(request.brief, phrase, None)
    assert brief.dining_seats == 5
    assert brief.split_dining is False
    with pytest.raises(
        service.BriefClarification, match="four modeled places"
    ) as error:
        service.interpret(request, None)
    assert {
        "requirement": "Requested 5 dining places at one table in the formal salon",
        "origin": "brief",
        "statement": phrase,
    } in error.value.reviewed["sources"]
    assert {
        "requirement": "5 dining places at one table",
        "origin": "brief",
        "statement": phrase,
    } in error.value.reviewed["sources"]


@pytest.mark.parametrize("split_dining", [True, False])
@pytest.mark.parametrize(
    ("phrase", "count"),
    [
        ("Two children and four adults must sit at one table in the salon.", 6),
        ("Four diners must sit at one table and two at the other end of it.", 6),
        (
            "Four diners must sit at one table and two at the other table if possible.",
            4,
        ),
    ],
)
def test_modal_seating_includes_required_allocations_only(split_dining, phrase, count):
    brief, _ = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=split_dining),
        phrase,
        None,
    )
    assert brief.dining_seats == count
    assert brief.split_dining is (split_dining and count == 4)


@pytest.mark.parametrize("modal", ["can", "must"])
def test_modal_seating_does_not_extract_speculative_counts(modal):
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=False),
        f"Could we check whether five attendees {modal} sit at one table in the salon? "
        "Four dining seats are required.",
        None,
    )
    assert brief.dining_seats == 4
    assert not questions


def test_exploratory_modal_seating_does_not_override_split_control():
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=True),
        "Could we check whether five attendees must sit at one table in the salon? "
        "Four dining seats are required.",
        None,
    )
    assert (brief.dining_seats, brief.split_dining) == (4, True)
    assert not questions


@pytest.mark.parametrize(
    ("phrase", "count"),
    [
        ("Thirty-one attendees and two adults must sit at one table in the salon.", 33),
        ("Seat thirty-one attendees at one table in the salon.", 31),
        ("Twenty‑one attendees must sit at one table in the salon.", 21),
        ("Twenty one attendees must sit at one table in the salon.", 21),
    ],
)
def test_compound_party_counts_are_kept_whole(phrase, count):
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=False),
        phrase,
        None,
    )
    assert brief.dining_seats == count
    assert any("four modeled places" in question for question in questions)


def test_modal_guest_count_keeps_conflicting_total_visible():
    request = review_request(
        "Four guests must sit at one table in the salon with two hosts.",
        formal_salon=True,
    )
    with pytest.raises(service.BriefClarification, match="Confirm one total"):
        service.interpret(request, None)


def test_locked_room_contradiction_is_reviewed_before_generation(
    saved_home, monkeypatch
):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(
        service.provider,
        "request",
        live_answer(lock_rooms=["bedroom"], shift_bedroom_chair=True),
    )
    before = copy.deepcopy(saved_home)
    request = review_request(
        "Keep the bedroom exactly as it is and move the bedroom desk chair.",
        live=True,
        width=15,
        depth=16,
    )
    with pytest.raises(service.BriefClarification, match="unlock its bedroom") as exc:
        service.interpret(request, saved_home)
    reviewed = exc.value.reviewed
    assert reviewed["status"] == "needs confirmation"
    assert "Keep bedroom" in reviewed["requirements"]
    assert saved_home == before


@pytest.mark.parametrize(
    ("brief", "message"),
    [
        (dict(dining_seats=6, formal_salon=True), ""),
        (dict(dining_seats=4), ""),
        (dict(locks=["bedroom"]), ""),
    ],
)
def test_offline_conflicts_stop_at_the_reviewed_brief(brief, message):
    with pytest.raises(service.BriefClarification) as exc:
        service.interpret(review_request(message, **brief), None)
    assert exc.value.reviewed["status"] == "needs confirmation"
    assert exc.value.reviewed["questions"]


def test_check_brief_matches_generation_boundaries(saved_home):
    with pytest.raises(ValueError, match="Unlock rooms"):
        check_brief(
            Brief(
                locks=["bedroom"],
                room_goals=[dict(room="study", relation="far", target="living")],
            ),
            saved_home,
        )
    assert check_brief(Brief(formal_salon=True, dining_seats=4)) is None


@pytest.mark.parametrize(
    "message",
    [
        "Keep the existing bedroom window where it is.",
        "Add a second door to the study.",
        "Move the front door to the east wall.",
    ],
)
def test_specific_opening_requests_need_confirmation(message):
    (question,) = opening_questions(message, locks=())
    assert "door or window" in question


@pytest.mark.parametrize(
    "message",
    [
        "Move the study desk closer to its window.",
        "Keep the bedroom near the door.",
        "Don't move the bedroom window.",
        "Bright study and sage finishes.",
    ],
)
def test_opening_words_without_an_opening_request_pass(message):
    assert opening_questions(message, locks=()) == []


def test_locked_room_keeps_its_saved_openings():
    message = "Keep the bedroom window where it is."
    assert opening_questions(message, locks=("bedroom",)) == []
    assert opening_questions(message, locks=("study",))


def test_review_cites_statements_and_labels_assumptions(saved_home):
    message = "Use oak finishes. Keep the passage at least 90 cm wide."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    reviewed = review_summary(brief, message=message, questions=questions)
    sources = {s["requirement"]: s for s in reviewed["sources"]}
    assert sources["0.9 m modeled passage"] == {
        "requirement": "0.9 m modeled passage",
        "origin": "brief",
        "statement": "Keep the passage at least 90 cm wide.",
    }
    assert sources["Lot 13 × 13 m"]["origin"] == "default"
    assert reviewed["status"] == "confirmed"
    assert any("site survey" in a for a in reviewed["assumptions"])

    default = review_summary(Brief(compare_tradeoffs=True))
    passage = {s["requirement"]: s for s in default["sources"]}["0.6 m modeled passage"]
    assert passage["origin"] == "default"
    assert any("0.6 m" in a for a in default["assumptions"])

    carried = Brief(width=15, depth=16, passage_m=0.6, formal_salon=True)
    inherited = review_summary(carried, previous=saved_home, controls={"width"})
    origins = {s["requirement"]: s["origin"] for s in inherited["sources"]}
    assert origins["Formal salon"] == "saved revision"
    assert origins["Lot 15 × 16 m"] == "controls"


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "town.db"))
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setenv("TOWN_DAILY_MODEL_CALLS", "9")
    monkeypatch.setenv("TOWN_DAILY_MICROUSD", "90")
    monkeypatch.setenv("TOWN_CALL_RESERVE_MICROUSD", "10")
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    service.initialize()
    return TestClient(app, base_url="http://localhost")


def submit(client, project, base, message, **brief):
    body = {
        "id": str(uuid.uuid4()),
        "project": project,
        "base": base,
        "brief": {"width": 15, "depth": 16, "compare_tradeoffs": True, **brief},
        "message": message,
        "live": bool(message),
    }
    job = client.post("/api/jobs", json=body).json()["job"]
    assert service.work_once()
    events = client.get(f"/api/jobs/{job}/events?after=0").json()["events"]
    return job, client.get("/api/jobs/" + job).json(), events


def test_rejected_contradiction_then_corrected_brief_keeps_saved_revision(
    local, monkeypatch
):
    project = local.post("/api/projects", json={}).json()["project"]
    first, result, _ = submit(local, project, 0, "")
    assert result["status"] == "ready"
    saved = local.post(f"/api/jobs/{first}/apply", json={"index": 0}).json()
    assert saved["revision"] == 1

    message = "Keep the bedroom exactly as it is and move the bedroom desk chair."
    monkeypatch.setattr(
        service.provider,
        "request",
        live_answer(lock_rooms=["bedroom"], shift_bedroom_chair=True),
    )
    _, rejected, events = submit(local, project, 1, message)
    assert rejected["status"] == "failed"
    assert "unlock its bedroom" in rejected["result"]
    (review,) = [e["artifact"] for e in events if e["task"] == "Reviewable brief"]
    assert review["status"] == "needs confirmation"
    assert not [e for e in events if e["task"] == "Furnished candidate"]
    reopened = local.get(f"/api/projects/{project}").json()
    assert (reopened["revision"], reopened["home"]) == (1, saved["home"])

    monkeypatch.setattr(
        service.provider, "request", live_answer(shift_bedroom_chair=True)
    )
    corrected, accepted, events = submit(
        local, project, 1, "Move the bedroom desk chair."
    )
    assert accepted["status"] == "ready", accepted["result"]
    (review,) = [e["artifact"] for e in events if e["task"] == "Reviewable brief"]
    assert review["status"] == "confirmed"
    applied = local.post(f"/api/jobs/{corrected}/apply", json={"index": 0}).json()
    assert applied["revision"] == 2
    original = local.get(f"/api/projects/{project}?revision=1").json()["home"]
    assert json.dumps(original, sort_keys=True) == json.dumps(
        saved["home"], sort_keys=True
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "Seat two guests and two hosts at one table.",
        "Two hosts and two guests at one table.",
        "Seat two guests, one host and one resident around one table.",
    ],
)
def test_grouped_diners_form_one_party(phrase):
    brief, questions = requirement_controls(
        Brief(formal_salon=True, dining_seats=4), phrase, None
    )
    assert (brief.dining_seats, brief.split_dining) == (4, False)
    assert questions == []


def test_grouped_diners_keep_independent_total_conflicts():
    _, questions = requirement_controls(
        Brief(formal_salon=True),
        "Seat two guests and two hosts at one table. Seating for six.",
        None,
    )
    assert any("one total number" in q for q in questions)


def test_fronted_room_keeps_locked_openings():
    message = "In the bedroom, keep the window where it is."
    assert opening_questions(message, locks=("bedroom",)) == []
    assert opening_questions(message, locks=("study",))


def test_each_opening_uses_its_own_room():
    message = "Move the study door and keep the bedroom window."
    (question,) = opening_questions(message, locks=("bedroom",))
    assert "move the study door" in question
    assert len(opening_questions(message, locks=("study",))) == 2


def test_rejected_width_is_not_cited_for_the_default_passage():
    message = "Keep a 5 m passage."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    reviewed = review_summary(brief, message=message, questions=questions)
    passage = {s["requirement"]: s for s in reviewed["sources"]}[
        "0.6 m modeled passage"
    ]
    assert passage == {
        "requirement": "0.6 m modeled passage",
        "origin": "default",
        "statement": None,
    }


def test_interpreted_lock_is_not_credited_to_empty_lock_controls(saved_home):
    request = review_request(locks=[])
    brief = request.brief.model_copy(update={"locks": ["bedroom"]})
    reviewed = service.reviewed_brief(request, brief, saved_home)
    origins = {s["requirement"]: s["origin"] for s in reviewed["sources"]}
    assert origins["Keep bedroom"] == "interpreted"


def test_ambiguous_furniture_lock_publishes_a_reviewed_brief(saved_home, monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(
        service.provider, "request", live_answer(lock_furniture=["missing-item"])
    )
    request = review_request(
        "Keep the missing item where it is.", live=True, width=15, depth=16
    )
    with pytest.raises(service.BriefClarification, match="furniture to lock") as exc:
        service.interpret(request, saved_home)
    assert exc.value.reviewed["status"] == "needs confirmation"


def test_kitchen_seating_without_a_modeled_table_requires_review():
    request = service.Request(
        project=uuid.uuid4(),
        id=uuid.uuid4(),
        base=0,
        brief=Brief(width=15, depth=16, compare_tradeoffs=True),
        message="Seat four people at a single table in the kitchen-dining room.",
        live=True,
    )
    with pytest.raises(
        service.BriefClarification, match="4 dining places in the kitchen-dining"
    ) as error:
        service.interpret(request, None)
    assert error.value.reviewed["status"] == "needs confirmation"
    assert "five-room program" in error.value.reviewed["questions"][0]


def test_conflicting_count_is_not_cited_for_retained_seating():
    reviewed = review_summary(
        Brief(formal_salon=True, dining_seats=6),
        message="Seat four people at a single table in the kitchen-dining room.",
        controls={"dining_seats"},
    )
    source = next(
        item
        for item in reviewed["sources"]
        if item["requirement"].startswith("6 dining")
    )
    assert source == {
        "requirement": "6 dining places at one table",
        "origin": "controls",
        "statement": None,
    }


def test_remote_work_headcount_does_not_define_dining():
    review, questions = requirement_controls(
        Brief(dining_seats=0),
        "Two residents and one guest work remotely. Move the study desk toward the window.",
        None,
    )
    assert not questions
    assert review.dining_seats == 0


def test_grouped_party_stays_in_its_named_room():
    review, questions = requirement_controls(
        Brief(formal_salon=True, split_dining=True),
        "Seat four hosts and two residents in the salon.",
        None,
    )
    assert any("requested 6 places there" in question for question in questions)
    assert review.dining_seats == 0


def test_coordinated_openings_retain_locked_room_scope():
    assert (
        opening_questions(
            "Preserve the doors and windows in the bedroom.", locks=("bedroom",)
        )
        == []
    )


def test_salon_in_brief_can_enable_the_kitchen_table_program():
    review, questions = requirement_controls(
        Brief(compare_tradeoffs=True),
        "Include a formal salon. Seat four people at a single table in the kitchen-dining room.",
        None,
    )
    assert review.formal_salon and not questions


def test_supported_split_quote_survives_separate_passage_problem():
    sentence = "Seat six dining places split across the salon and kitchen-dining with a 5 m clear passage."
    reviewed = review_summary(
        Brief(formal_salon=True, dining_seats=6, split_dining=True), message=sentence
    )
    assert any(
        item["statement"] == sentence and item["origin"] == "brief"
        for item in reviewed["sources"]
    )


def test_lot_and_locks_are_not_credited_to_unrelated_requirements():
    reviewed = review_summary(
        Brief(locks=["bedroom"]),
        message="Make the lot 12 by 14 m. Keep the passage at least 65 cm wide.",
        controls={"width", "locks"},
    )
    evidence = {item["requirement"]: item for item in reviewed["sources"]}
    assert evidence["Lot 13 × 13 m"]["origin"] == "controls"
    assert evidence["Keep bedroom"]["origin"] == "controls"
    assert evidence["Keep bedroom"]["statement"] is None


@pytest.mark.parametrize(
    "message",
    [
        "Seat four people in the kitchen-dining room.",
        "Seat four people in the formal salon.",
        "Seat two hosts and two guests in the kitchen-dining room.",
    ],
)
def test_supported_room_specific_dining_retains_the_count(message):
    review, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True), message, None
    )
    assert review.dining_seats == 4
    assert questions == []


def test_coordinated_openings_require_each_room_to_be_locked():
    message = "Keep the bedroom window and the study window where they are."
    assert opening_questions(message, locks=("bedroom", "study")) == []
    (question,) = opening_questions(message, locks=("bedroom",))
    assert "keep the study window" in question
    (question,) = opening_questions(message, locks=("study",))
    assert "keep the bedroom window" in question


def test_room_minimum_does_not_override_a_larger_total():
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=True),
        "Six total dining places. Four seats in the salon.",
        None,
    )
    assert not questions
    assert brief.dining_seats == 6


def test_distinct_room_minima_need_two_tables():
    message = "Four seats in the formal salon and two seats in the kitchen."
    base = Brief(formal_salon=True, compare_tradeoffs=True)
    brief, questions = requirement_controls(base, message, None)
    assert brief.dining_seats == 6
    assert any("Confirm separate tables" in item for item in questions)
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=True),
        message,
        None,
    )
    assert not questions
    assert brief.dining_seats == 6


def test_independent_action_does_not_inherit_opening_verb():
    message = "Keep the bedroom window and use the study door for access."
    assert opening_questions(message, locks=("bedroom",)) == []


def test_meal_language_counts_the_party_and_cites_the_source():
    message = "Two hosts and four guests will eat together."
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True), message, None
    )
    assert brief.dining_seats == 6 and not questions
    source = next(
        item
        for item in review_summary(brief, message=message)["sources"]
        if item["requirement"].startswith("6 dining")
    )
    assert source["statement"] == message
    assert source["origin"] == "brief"


def test_room_minimum_cites_the_source_in_review():
    message = "Four seats in the salon."
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True), message, None
    )
    assert not questions
    assert {
        "requirement": "4 dining places at one table",
        "origin": "brief",
        "statement": message,
    } in review_summary(brief, message=message)["sources"]


def test_repeated_four_person_room_minima_add_up_to_eight():
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, split_dining=True),
        "Four seats in the salon and four seats in the kitchen.",
        None,
    )
    assert review_summary(brief)["status"] == "confirmed"
    assert not questions and brief.dining_seats == 8


def test_negative_salon_statement_is_not_cited(saved_home):
    review = review_summary(
        Brief(formal_salon=True, compare_tradeoffs=True),
        message="Do not add a salon.",
        previous=saved_home,
    )
    assert {
        "requirement": "Formal salon",
        "origin": "saved revision",
        "statement": None,
    } in review["sources"]


def test_opening_modifiers_can_continue_a_preservation_request():
    message = "Keep the bedroom window and original study door."
    (question,) = opening_questions(message, locks=("bedroom",))
    assert "keep original study door" in question


def test_offsite_meal_does_not_override_home_seating():
    message = (
        "Two hosts and four guests will have breakfast off-site. Four dining places."
    )
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True, dining_seats=4), message, None
    )
    assert not questions and brief.dining_seats == 4


def test_review_quotes_a_standalone_salon_request():
    message = "Formal salon"
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert brief.formal_salon and not questions
    assert {
        "requirement": "Formal salon",
        "origin": "brief",
        "statement": message,
    } in review_summary(brief, message=message)["sources"]


def test_day_at_work_does_not_discard_an_at_home_meal():
    phrase = "We dine together at home with two residents and two dinner guests after a day at work."
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True), phrase, None
    )
    assert not questions and brief.dining_seats == 4


def test_declined_standalone_salon_is_not_a_requirement_or_source():
    phrase = "Formal salon, not needed"
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and not brief.formal_salon
    assert {
        "requirement": "Formal salon",
        "origin": "controls",
        "statement": None,
    } in review_summary(
        Brief(formal_salon=True), message=phrase, controls={"formal_salon"}
    )["sources"]


def test_salon_question_followed_by_no_does_not_add_a_room():
    phrase = "Formal salon? No, keep the five standard rooms."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and not brief.formal_salon
    assert {
        "requirement": "Formal salon",
        "origin": "controls",
        "statement": None,
    } in review_summary(
        Brief(formal_salon=True), message=phrase, controls={"formal_salon"}
    )["sources"]


def test_salon_shorthand_before_seating_is_quoted():
    phrase = "Formal salon; four seats in the salon."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and brief.formal_salon and brief.dining_seats == 4
    assert {
        "requirement": "Formal salon",
        "origin": "brief",
        "statement": "Formal salon;",
    } in review_summary(brief, message=phrase)["sources"]


def test_an_unrelated_prohibition_does_not_cancel_salon_seating():
    phrase = "Formal salon. No changes to the bedroom. Four seats in the salon."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and brief.formal_salon and brief.dining_seats == 4


@pytest.mark.parametrize("decline", ["leave it out", "omit it", "not needed"])
def test_salon_omission_and_replacement_are_read_in_context(decline):
    phrase = f"Formal salon; {decline}."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and not brief.formal_salon

    phrase += " Actually, include a formal salon."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and brief.formal_salon
    assert {
        "requirement": "Formal salon",
        "origin": "brief",
        "statement": "Actually, include a formal salon.",
    } in review_summary(brief, message=phrase)["sources"]


def test_excluding_a_salon_feature_does_not_exclude_the_room():
    phrase = (
        "Include a formal salon. No salon fireplace, please. Four seats in the salon."
    )
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), phrase, None)
    assert not questions and brief.formal_salon and brief.dining_seats == 4


def test_each_room_lock_quotes_its_own_statement():
    message = "Move the bedroom door. Keep the bedroom;keep the study."
    brief = Brief(locks=["bedroom", "study"])
    entries = {
        item["requirement"]: item
        for item in review_summary(brief, message=message)["sources"]
    }
    assert entries["Keep bedroom"]["statement"] == "Keep the bedroom;"
    assert entries["Keep study"]["statement"] == "keep the study."
    entries = review_summary(
        Brief(locks=["bedroom"]), message="Keep the bedroom window."
    )["sources"]
    assert (
        next(item for item in entries if item["requirement"] == "Keep bedroom")[
            "origin"
        ]
        == "interpreted"
    )


@pytest.mark.parametrize("timing", ["for now", "after all", "this time"])
def test_salon_room_cancellation_can_have_a_timing_qualifier(timing):
    message = f"Include a formal salon. Skip the salon {timing}."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert not questions and not brief.formal_salon


def test_exact_where_wording_cites_an_explicit_lock(saved_home, monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(
        service.provider, "request", live_answer(lock_rooms=["bedroom"])
    )
    message = "Keep the bedroom exactly where it is."
    request = review_request(message, live=True, width=15, depth=16)
    brief = service.interpret(request, saved_home)
    assert brief.locks == ["bedroom"]
    assert {
        "requirement": "Keep bedroom",
        "origin": "brief",
        "statement": message,
    } in service.reviewed_brief(request, brief, saved_home)["sources"]


def test_conditional_salon_omission_does_not_cancel_an_unconditional_request():
    message = (
        "Include a formal salon. Skip the salon this time only if it won't fit. "
        "Four seats in the salon."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert not questions and brief.formal_salon and brief.dining_seats == 4


@pytest.mark.parametrize(
    "correction",
    [
        "No salon, keep the five standard rooms.",
        "Omit the salon for now, please.",
        "Skip the salon this time, please, keep the five standard rooms.",
    ],
)
def test_explicit_program_correction_after_a_salon_request(correction):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), "Include a formal salon. " + correction, None
    )
    assert not questions and not brief.formal_salon


def test_new_instruction_must_not_truncate_a_conditional_program_correction():
    message = (
        "Include a formal salon. No salon, but only if it won't fit. "
        "Four seats in the salon."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert not questions and brief.formal_salon and brief.dining_seats == 4


@pytest.mark.parametrize("linebreak", [" ", "\n", "\r\n", "\n\n"])
@pytest.mark.parametrize("condition", ["only if it won't fit", "unless there is space"])
def test_wrapped_condition_does_not_turn_a_salon_fallback_into_a_cancellation(
    linebreak, condition
):
    message = (
        "Include a formal salon. No salon, keep the five standard rooms"
        f"{linebreak}{condition}. Four seats in the salon."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert not questions and brief.formal_salon and brief.dining_seats == 4


def test_unqualified_five_room_correction_on_separate_line():
    message = (
        "Include a formal salon.\nNo salon, keep the five standard rooms.\nUse oak."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert not questions and not brief.formal_salon


def test_salon_correction_in_the_same_sentence():
    brief = Brief(compare_tradeoffs=True)
    text = "Include a formal salon, but skip the salon for now."
    result, questions = requirement_controls(brief, text, None)
    assert not questions and not result.formal_salon
    result, questions = requirement_controls(
        brief, "Include a formal salon, but skip the salon only if it won't fit.", None
    )
    assert not questions and result.formal_salon


def test_independent_conditional_finish_does_not_reverse_the_room_correction():
    message = (
        "Include a formal salon.\nNo salon, keep the five standard rooms\n\n"
        "If possible, use oak."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True), message, None
    )
    assert not questions and not brief.formal_salon


def test_restaurant_table_does_not_supply_a_home_dining_count():
    message = (
        "Two hosts and four guests will have dinner at a restaurant table. "
        "Four dining places."
    )
    brief, questions = requirement_controls(
        Brief(formal_salon=True, compare_tradeoffs=True), message, None
    )
    assert not questions and brief.dining_seats == 4


def test_split_total_must_cover_both_tables():
    settings = Brief(formal_salon=True, compare_tradeoffs=True, split_dining=True)
    text = "Four dining places split between the salon and kitchen. Four seats in the salon."
    _, questions = requirement_controls(settings, text, None)
    assert any("room-specific seating" in item for item in questions)
    brief, questions = requirement_controls(
        settings, text.replace("Four dining places", "Five dining places"), None
    )
    assert not questions and brief.dining_seats == 5


def test_preserved_connecting_door_respects_an_existing_study_lock():
    text = "Keep the door to the study where it is."
    assert not opening_questions(text, ["study"])
    assert opening_questions(text, ["bedroom"])


def test_cannot_lock_a_room_that_does_not_exist(monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(service.provider, "request", live_answer())
    previous = generate(Brief(width=15, depth=16))[0]
    request = review_request(
        "Keep the salon window.", live=True, width=15, depth=16, locks=["salon"]
    )
    with pytest.raises(service.BriefClarification, match="absent from the saved home"):
        service.interpret(request, previous)


@pytest.mark.parametrize(
    "text",
    [
        "Keep the passage width at least 0.6 m between the sofa and the wall.",
        "Keep a 0.6 m clear passage between the sofa and the wall.",
    ],
)
def test_object_clearance_is_not_cited_as_the_default_plan_passage(text):
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert questions
    sources = review_summary(brief, message=text, questions=questions)["sources"]
    assert next(
        item for item in sources if "modeled passage" in item["requirement"]
    ) == {
        "requirement": "0.6 m modeled passage",
        "origin": "default",
        "statement": None,
    }


def test_two_room_allocations_are_quoted_as_the_combined_dining_total():
    text = "Four seats in the salon. Two seats in the kitchen."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert not questions and brief.dining_seats == 6
    assert {
        "requirement": "6 dining places across two tables",
        "origin": "brief",
        "statement": text,
    } in review_summary(brief, message=text)["sources"]


def test_checked_locks_are_attributed_only_to_the_checked_rooms(saved_home):
    request = review_request(
        "Keep the study desk exactly where it is.", locks=["bedroom"]
    )
    brief = request.brief.model_copy(update={"locks": ["bedroom", "study"]})
    origins = {
        source["requirement"]: source["origin"]
        for source in service.reviewed_brief(request, brief, saved_home)["sources"]
    }
    assert origins["Keep bedroom"] == "controls"
    assert origins["Keep study"] == "interpreted"


def test_salon_correction_after_an_unrelated_but_clause():
    text = (
        "Include a formal salon, but keep the living room separate. "
        "Skip the salon for now."
    )
    result, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert not questions and not result.formal_salon


def test_offsite_meal_does_not_hide_separate_home_seating():
    text = "We have dinner at a restaurant, so we need five seats in the salon for breakfast."
    _, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True), text, None
    )
    assert any("requested 5 places" in question for question in questions)


def test_qualified_door_does_not_hide_separate_window_request():
    text = "Keep the door to the bedroom and the window in the study."
    assert len(opening_questions(text, ["bedroom"])) == 1
    assert not opening_questions(text, ["bedroom", "study"])


def test_newline_after_negation_preserves_dining_evidence():
    text = "Four seats in the salon, not beside the door\nTwo seats in the kitchen."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert not questions and brief.dining_seats == 6
    assert {
        "requirement": "6 dining places across two tables",
        "origin": "brief",
        "statement": text,
    } in review_summary(brief, message=text)["sources"]


def test_route_length_between_rooms_does_not_block_a_valid_width():
    text = (
        "Prefer an 8 m route between the kitchen and salon that runs across the open gap. "
        "Use an 80 cm clear passage."
    )
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert not questions and brief.passage_m == 0.8


def test_offsite_seats_are_not_another_home_seating_total():
    text = "We have dinner at a restaurant and need six seats there. Four dining places at home."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert not questions and brief.dining_seats == 4


def test_bare_decline_of_another_feature_does_not_cancel_the_salon():
    text = (
        "Include a formal salon. A kitchen island? Not needed. Four seats in the salon."
    )
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert not questions and brief.formal_salon and brief.dining_seats == 4


def test_combined_seating_citation_omits_unrelated_study_preference():
    text = "Four seats in the salon. Prefer daylight in the study. Two seats in the kitchen."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert not questions and brief.dining_seats == 6
    assert {
        "requirement": "6 dining places across two tables",
        "origin": "brief",
        "statement": "Four seats in the salon.\nTwo seats in the kitchen.",
    } in review_summary(brief, message=text)["sources"]


def test_five_room_correction_overrides_a_model_salon_even_after_another_preference(
    monkeypatch,
):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(service.provider, "request", live_answer(formal_salon=True))
    text = "Include a formal salon. Use oak floors. Actually, no, keep the five standard rooms."
    request = review_request(text, live=True, width=15, depth=16)
    assert not service.interpret(request, None).formal_salon
    checked = review_request(text, live=True, width=15, depth=16, formal_salon=True)
    with pytest.raises(service.BriefClarification, match="Confirm the five-room"):
        service.interpret(checked, None)


@pytest.mark.parametrize(
    "cue", ["measured", "with the width taken", "with the width measured"]
)
def test_width_cue_after_fixture_endpoints_needs_clarification(cue):
    text = f"Keep a 90 cm route between the kitchen island and the counters, {cue} across the open gap."
    _, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert any("90 cm clearance between specific objects" in item for item in questions)


def test_combined_seating_quote_preserves_a_semicolon_without_spaces():
    text = "Four seats in the salon;Two seats in the kitchen."
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert not questions and brief.dining_seats == 6
    assert {
        "requirement": "6 dining places across two tables",
        "origin": "brief",
        "statement": text,
    } in review_summary(brief, message=text)["sources"]


def test_a_later_explicit_salon_request_overrides_the_five_room_default(monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(service.provider, "request", live_answer(formal_salon=True))
    text = "Keep the five standard rooms. Actually, add a separate formal salon."
    request = review_request(text, live=True, width=15, depth=16)
    assert service.interpret(request, None).formal_salon


def test_saved_salon_removal_identifies_the_new_project_path(saved_home):
    request = review_request("Keep the five standard rooms.", width=15, depth=16)
    with pytest.raises(service.BriefClarification, match="Start a new project"):
        service.interpret(request, saved_home)


@pytest.mark.parametrize("prefix", ["", "Keep the five standard rooms. "])
def test_explicit_salon_exclusion_cannot_add_a_salon(prefix, monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    monkeypatch.setattr(service.provider, "request", live_answer(formal_salon=True))
    request = review_request(
        prefix + "Avoid a plan with a separate formal salon.",
        live=True,
        width=15,
        depth=16,
    )
    assert not service.interpret(request, None).formal_salon


@pytest.mark.parametrize(
    "passage", ["Keep a 65 cm wide passage.", "Keep the passage width at least 65 cm."]
)
def test_live_interpreter_receives_verified_controls_without_reinterpreting_them(
    monkeypatch,
    passage,
):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    seating = "Seat six people total across two tables in the formal salon and kitchen-dining room."
    preference = "Prefer the study away from the living room."

    def answer(schema, payload, **_kwargs):
        facts = json.loads(payload)
        assert facts["confirmed_layout_controls"] == {
            "dining_seats": 6,
            "split_dining": True,
            "modeled_passage_m": 0.65,
        }
        assert preference in facts["request"]
        unsupported = [
            phrase for phrase in (seating, passage) if phrase in facts["request"]
        ]
        return live_answer(formal_salon=True, unsupported=unsupported)(schema)

    monkeypatch.setattr(service.provider, "request", answer)
    request = review_request(
        " ".join((seating, passage, preference)),
        live=True,
        width=15,
        depth=16,
        formal_salon=True,
        dining_seats=6,
        split_dining=True,
        passage_m=0.65,
    )
    brief = service.interpret(request, None)
    assert brief.dining_seats == 6 and brief.split_dining and brief.passage_m == 0.65


def test_live_interpreter_still_receives_mixed_unenforceable_requirements(monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    statement = "Keep a 65 cm wide passage and certify it meets local building code."

    def answer(schema, payload, **_kwargs):
        assert statement in json.loads(payload)["request"]
        return live_answer(unsupported=["Building code certification"])(schema)

    monkeypatch.setattr(service.provider, "request", answer)
    request = review_request(statement, live=True, width=15, depth=16, passage_m=0.65)
    with pytest.raises(service.BriefClarification, match="Building code certification"):
        service.interpret(request, None)


def test_wrapped_specific_clearance_remains_a_single_requirement():
    text = "Keep a 65 cm wide passage\nbetween the kitchen island and the counters."
    _, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert any("65 cm clearance between specific objects" in item for item in questions)


def test_standalone_control_line_does_not_consume_the_next_request(monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    preference = "Prefer the study away from the living room."

    def answer(schema, payload, **_kwargs):
        facts = json.loads(payload)
        assert facts["request"] == preference
        assert facts["confirmed_layout_controls"]["modeled_passage_m"] == 0.65
        return live_answer()(schema)

    monkeypatch.setattr(service.provider, "request", answer)
    assert (
        service.interpret(
            review_request(
                "Keep the passage width at least 65 cm\n" + preference, live=True
            ),
            None,
        ).passage_m
        == 0.65
    )


def test_a_coordinated_line_has_an_independent_requirement():
    text = "Don't add a formal salon,\nand please keep a 65 cm wide passage."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert not questions and brief.passage_m == 0.65 and not brief.formal_salon

    text = "Don't add a formal salon,\nand please keep the existing study window."
    assert opening_questions(text, [])


@pytest.mark.parametrize("separator", [" ", "\n"])
def test_study_separation_does_not_change_the_one_table_request(separator):
    text = (
        "Seat six guests at one table"
        + separator
        + "and keep the study separate from the living room."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        text,
        None,
    )
    assert brief.dining_seats == 6 and not brief.split_dining
    assert any("one dining table" in question for question in questions)


def test_fronted_room_preference_is_not_a_wrapped_passage_qualifier():
    text = "Keep a 65 cm wide passage\nBetween the study and living room, prefer more separation."
    brief, questions = requirement_controls(Brief(compare_tradeoffs=True), text, None)
    assert not questions and brief.passage_m == 0.65


@pytest.mark.parametrize("linebreak", [" ", "\n"])
def test_coordinated_table_allocations_keep_the_total_and_room_qualifier(linebreak):
    text = (
        "Seat three guests at one table"
        + linebreak
        + "and three guests at the other in the kitchen-dining room."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert not questions and brief.dining_seats == 6 and brief.split_dining


@pytest.mark.parametrize("separator", [" ", "\n"])
def test_opposite_ends_of_one_table_do_not_confirm_split_dining(separator):
    text = (
        "Seat four guests at one table" + separator + "and two at the other end of it."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert brief.dining_seats == 6 and not brief.split_dining
    assert any("one dining table" in question for question in questions)


def test_same_table_seats_are_not_an_additional_headcount():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "Seat two hosts at one table and two at the other end of it for dinner with two guests.",
        None,
    )
    assert not questions and brief.dining_seats == 4 and not brief.split_dining


@pytest.mark.parametrize(
    "qualifier", ["the other for dinner", "the other end for dinner"]
)
@pytest.mark.parametrize("separator", [" and ", "\nand seat "])
def test_counted_seating_keeps_both_allocations_with_a_meal_qualifier(
    qualifier, separator
):
    single = "end" in qualifier
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Seat four guests at one table" + separator + "two at " + qualifier + ".",
        None,
    )
    assert brief.dining_seats == 6 and brief.split_dining is not single
    assert bool(questions) is single


@pytest.mark.parametrize("location", ["the other table", "the other end"])
@pytest.mark.parametrize("separator", [" and ", "\nand seat "])
@pytest.mark.parametrize("first", ["four", "four guests"])
def test_optional_second_group_does_not_raise_required_seating(
    location, separator, first
):
    text = (
        f"Seat {first} at one table"
        + separator
        + "two at "
        + location
        + " if possible."
    )
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=False),
        text,
        None,
    )
    assert not questions and brief.dining_seats == 4 and not brief.split_dining
    check_brief(brief)


@pytest.mark.parametrize(
    "text",
    [
        "Six dining seats. Seat everyone at one table at home for breakfast and have dinner at a restaurant.",
        "Six dining seats. We have dinner at a restaurant and seat everyone at one table at home for breakfast.",
    ],
)
def test_home_single_table_requirement_survives_offsite_meal(text):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        text,
        None,
    )
    assert brief.dining_seats == 6 and not brief.split_dining
    assert any("one dining table" in question for question in questions)


def test_offsite_single_table_does_not_restrict_home_split():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Six dining seats at home. Seat four guests at one table for dinner at a restaurant.",
        None,
    )
    assert not questions and brief.dining_seats == 6 and brief.split_dining


@pytest.mark.parametrize(
    "text",
    [
        "We need six dining seats at home and for our Friday outing seat everyone at one table while we have dinner at a restaurant.",
        "We have breakfast at work and seat six guests at one table for dinner at a restaurant and need six dining seats at home.",
        "For dinner at home seat six across two tables and have breakfast off-site and need eight seats there.",
    ],
)
def test_offsite_table_in_a_compound_sentence_does_not_restrict_home_split(text):
    brief, questions = requirement_controls(
        Brief(
            compare_tradeoffs=True, formal_salon=True, split_dining=True, dining_seats=6
        ),
        text,
        None,
    )
    assert not questions and brief.dining_seats == 6 and brief.split_dining


@pytest.mark.parametrize("lead", ["want", "we want", "we would want"])
def test_same_table_followup_inherits_home_seating_location(lead):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        f"We have lunch at work and need six dining seats at home and {lead} everyone at one table.",
        None,
    )
    assert brief.dining_seats == 6 and not brief.split_dining
    assert any("one dining table" in question for question in questions)


@pytest.mark.parametrize(
    "text",
    [
        "We have dinner at a restaurant on Fridays and seat four guests at one table and seat two guests at the other table at home.",
        "We need six dining seats at home while our neighbors have dinner at a restaurant.",
        "We have dinner at a restaurant while our housemates need six dining seats at home.",
    ],
)
def test_offsite_meal_preserves_full_home_requirement(text):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        text,
        None,
    )
    assert not questions and brief.dining_seats == 6 and brief.split_dining


@pytest.mark.parametrize(
    "text",
    [
        "We have lunch at work and need six dining seats while at home.",
        "We have lunch at work and need six dining seats while in the house at home.",
    ],
)
def test_while_location_qualifier_stays_with_home_seating(text):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert not questions and brief.dining_seats == 6 and brief.split_dining


@pytest.mark.parametrize(
    "text",
    [
        "For dinner at home, seat four guests at one table and seat two guests at the other table for lunch at work.",
        "For lunch at work, seat two guests at one table and seat four guests at the other table for dinner at home.",
        "For lunch at work, seat two at one table and seat four at the other table for dinner at home.",
    ],
)
def test_allocations_with_different_meals_keep_the_home_count(text):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True), text, None
    )
    assert not questions and brief.dining_seats == 4 and not brief.split_dining


def test_later_home_activity_does_not_rescope_restaurant_seating():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "For dinner at a restaurant, seat four guests at one table and seat two guests at the other table before we meet back at home. We need four dining seats.",
        None,
    )
    assert not questions and brief.dining_seats == 4 and not brief.split_dining


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "We need four dining seats at home before we have dinner at a restaurant with seating for six.",
            4,
        ),
        (
            "We have lunch at work and need seating for four after we get together for dinner at home.",
            4,
        ),
        (
            "We need seating for four at home. If possible, seat two at the second table.",
            4,
        ),
        (
            "We need seating for four at home. Seat two at the second table if possible.",
            4,
        ),
    ],
)
def test_temporal_and_optional_statements_do_not_lose_required_seats(text, expected):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True), text, None
    )
    assert not questions and brief.dining_seats == expected and not brief.split_dining


@pytest.mark.parametrize(
    ("text", "total", "message"),
    [
        (
            "Seat four at one table in the kitchen and seat two at the other table in the salon.",
            6,
            "",
        ),
        (
            "Seat five at one table in the kitchen and seat two at the other table in the salon.",
            7,
            "four places",
        ),
        (
            "Seat four at one table in the kitchen and seat two at the other table in the kitchen-dining room.",
            6,
            "different location",
        ),
    ],
)
def test_room_qualified_table_allocations_keep_both_counts(text, total, message):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True), text, None
    )
    assert brief.dining_seats == total and brief.split_dining
    assert (
        any(message in question for question in questions) if message else not questions
    )


@pytest.mark.parametrize("room", ["kitchen", "kitchen-dining"])
@pytest.mark.parametrize("split", [False, True])
def test_optional_second_room_keeps_only_the_required_home_allocation(room, split):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=split),
        f"Seat four at one table in the salon and two at the other table in the {room} if possible.",
        None,
    )
    assert not questions and brief.dining_seats == 4 and brief.split_dining is split


@pytest.mark.parametrize(
    "first, second",
    [("in the salon", "in the kitchen"), ("", "")],
)
def test_optional_table_does_not_waive_required_table_capacity(first, second):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        f"Seat six guests at one table {first} and two at the other table {second} if possible.",
        None,
    )
    assert brief.dining_seats == 6
    assert any("smaller group at the required table" in q for q in questions)


@pytest.mark.parametrize("location", ["At the restaurant", "At work", "Away from home"])
def test_fronted_offsite_location_cannot_supply_home_table_requirements(location):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        f"{location}, put six at one table and two at the other table if possible. "
        "At home, seat four at one table and one at the other table.",
        None,
    )
    assert not questions and brief.dining_seats == 5


@pytest.mark.parametrize(
    "other",
    ["we eat lunch", "we seat two at one table"],
)
def test_split_out_home_seating_after_a_fronted_offsite_heading(other):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        f"At work, {other}, and at home we need six dining seats.",
        None,
    )
    assert not questions and brief.dining_seats == 6


@pytest.mark.parametrize("sequence", ["after", "before"])
def test_keep_home_seats_with_offsite_timing_qualifier(sequence):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        f"We need six dining seats, and at home we have dinner together {sequence} we eat at work.",
        None,
    )
    assert not questions and brief.dining_seats == 6
    with pytest.raises(ValueError, match="four places at one table"):
        check_brief(brief)


def test_table_allocation_can_refer_back_to_an_offsite_timing_venue():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "At home, we need four dining seats before we have dinner at a restaurant "
        "and seat six guests there.",
        None,
    )
    assert not questions and brief.dining_seats == 4
    check_brief(brief)


@pytest.mark.parametrize("location", ["", "At home, "])
def test_offsite_timing_reference_cannot_erase_the_home_count(location):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        f"{location}we need six dining seats for breakfast before we have lunch "
        "at a restaurant and have dessert there.",
        None,
    )
    assert not questions and brief.dining_seats == 6
    with pytest.raises(ValueError, match="four places at one table"):
        check_brief(brief)


def test_optional_same_table_end_cannot_waive_required_one_table_arrangement():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Seat four at one table in the salon and two at the other end if possible.",
        None,
    )
    assert brief.dining_seats == 4 and not brief.split_dining
    assert any("one dining table" in question for question in questions)


def test_existential_there_does_not_inherit_the_offsite_location():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "We have lunch at work and need there to be seating for six before we have dinner at home.",
        None,
    )
    assert not questions and brief.dining_seats == 6


def test_explicit_offsite_reference_comes_before_later_home_meal():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        "We have lunch at work and need seating for six there after we have breakfast at home. We need four dining seats at home.",
        None,
    )
    assert not questions and brief.dining_seats == 4


def test_live_interpreter_receives_room_qualified_pair_with_confirmed_total(
    monkeypatch,
):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    text = "Seat four at one table in the kitchen and seat two at the other table in the salon."

    def answer(schema, payload, **_kwargs):
        facts = json.loads(payload)
        assert facts["request"] == text
        assert facts["confirmed_layout_controls"]["dining_seats"] == 6
        assert facts["confirmed_layout_controls"]["split_dining"] is True
        return live_answer()(schema)

    monkeypatch.setattr(service.provider, "request", answer)
    assert (
        service.interpret(
            review_request(text, live=True, formal_salon=True, split_dining=True), None
        ).dining_seats
        == 6
    )


def test_live_interpreter_receives_optional_seating_as_prose(monkeypatch):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    text = "Seat four at one table and two at the other table if possible."

    def answer(schema, payload, **kwargs):
        facts = json.loads(payload)
        assert facts["request"] == text
        assert facts["confirmed_layout_controls"]["dining_seats"] == 4
        assert facts["confirmed_layout_controls"]["split_dining"] is False
        assert (
            "described as optional in the request as a preference"
            in kwargs["task_instructions"]
        )
        return live_answer()(schema)

    monkeypatch.setattr(service.provider, "request", answer)
    result = service.interpret(review_request(text, live=True, formal_salon=True), None)
    assert result.dining_seats == 4 and not result.split_dining


def test_grouped_seating_can_wrap_after_preposition():
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True, split_dining=True),
        "Four guests at\none table and two at\nthe other table.",
        None,
    )
    assert not questions and brief.dining_seats == 6 and brief.split_dining


@pytest.mark.parametrize(("first", "total"), [("one host", 4), ("three hosts", 6)])
def test_same_table_retains_every_group_at_each_end(first, total):
    brief, questions = requirement_controls(
        Brief(compare_tradeoffs=True, formal_salon=True),
        f"For dinner, {first} and two guests at a single table and one at the other end of it.",
        None,
    )
    assert not questions and brief.dining_seats == total and not brief.split_dining
    if total > 4:
        with pytest.raises(ValueError, match="four places at one table"):
            check_brief(brief)
    else:
        check_brief(brief)


def test_a_wrapped_opening_list_still_checks_the_second_room():
    text = "Keep the bedroom door\nand the study window."
    assert len(opening_questions(text, ["bedroom"])) == 1
    assert not opening_questions(text, ["bedroom", "study"])


def test_live_payload_preserves_a_coordinated_opening_request(monkeypatch, saved_home):
    monkeypatch.setattr(service.provider, "configuration", lambda _: ("f", "f"))
    action = "and please preserve the existing study window."

    def answer(schema, payload, **_kwargs):
        facts = json.loads(payload)
        assert facts["request"] == action
        assert facts["confirmed_layout_controls"]["modeled_passage_m"] == 0.65
        return live_answer()(schema)

    monkeypatch.setattr(service.provider, "request", answer)
    req = review_request(
        "Keep a 65 cm wide passage\n" + action,
        width=15,
        depth=16,
        locks=["study"],
        live=True,
    )
    assert service.interpret(req, saved_home).passage_m == 0.65
