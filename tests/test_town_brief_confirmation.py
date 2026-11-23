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
