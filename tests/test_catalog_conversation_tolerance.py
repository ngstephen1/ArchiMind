"""Prompt-suite fixes: typo-tolerant evidence words, restated requests, named reasons."""

from types import SimpleNamespace

from catalog_chat_helpers import TEXT, extraction, intent, quote, turns

from archimind.agents.catalog_conversation import (
    near_term,
    reconcile_catalog_extraction,
)
from archimind.agents.catalog_requirements import ChatTextFact


def run(text, **changes):
    data = extraction().model_copy(update=changes)
    return reconcile_catalog_extraction(data, turns(text))


TYPO_TEXT = TEXT.replace("A rectangular bedroom", "A rectangular bedrom").replace(
    "A queen bed and a writing desk.", "A queen bed, one nighstand and one wadrobe."
)


def test_near_term_accepts_one_slip_and_rejects_other_words():
    assert near_term("bedroom", "A rectangular bedrom 5 m wide")
    assert near_term("nightstand", "one nighstand")
    assert near_term("wardrobe", "one wadrobe")
    assert near_term("chair", "a chiar")  # transposition
    assert not near_term("bedroom", "A rectangular bathroom")
    assert not near_term("nightstand", "a nightmare")
    assert not near_term("desk", "a dog")  # short words need an exact match
    assert not near_term("bed", "a bad")


def test_typos_in_room_and_function_words_still_ready():
    result = run(
        TYPO_TEXT,
        room_source=quote("bedrom"),
        furniture=(
            intent("bed", "queen bed"),
            intent("nightstand", "one nighstand"),
            intent("wardrobe", "one wadrobe"),
        ),
    )
    assert result.status == "ready", result.clarifications


def test_wrong_function_word_still_asks():
    text = TEXT.replace("a writing desk", "a nightmare")
    result = run(
        text,
        furniture=(intent("bed", "queen bed"), intent("nightstand", "a nightmare")),
    )
    assert result.status == "needs_clarification"
    assert any("function of furniture request 2" in q for q in result.clarifications)


def fact(value, source):
    return ChatTextFact(value=value, source=quote(source))


def test_constraint_that_only_restates_a_request_is_ignored():
    result = run(
        TEXT,
        hard_constraints=(
            fact("A queen bed", "A queen bed"),
            fact("a writing desk", "a writing desk"),
        ),
    )
    assert result.status == "ready", result.clarifications


def test_real_constraint_is_still_unsupported():
    text = TEXT.replace("A queen bed", "A queen bed against the north wall")
    result = run(
        text,
        hard_constraints=(
            fact("bed against the north wall", "A queen bed against the north wall"),
        ),
    )
    assert result.status == "unsupported"


def test_restated_constraint_for_an_unrequested_function_is_still_unsupported():
    result = run(TEXT, hard_constraints=(fact("one wardrobe", "A queen bed"),))
    assert result.status == "unsupported"


def test_two_twin_beds_asks_about_quantity_instead_of_unsupported():
    text = TEXT.replace(
        "A queen bed and a writing desk.", "Two twin beds and a writing desk."
    )
    beds = intent("bed", "Two twin beds").model_copy(update={"quantity": 2})
    result = run(
        text,
        furniture=(beds, intent("desk", "a writing desk")),
        hard_constraints=(fact("Two twin beds", "Two twin beds"),),
    )
    assert result.status == "needs_clarification"
    assert any("one instance" in q for q in result.clarifications)


def test_unsupported_message_names_the_reason():
    from archimind.ui.bedroom_chat import _assistant_text

    data = extraction().model_copy(
        update={
            "shape": "unsupported",
            "unsupported_features": ("L-shaped bedroom",),
            "hard_constraints": (fact("bed against the north wall", "bed"),),
        }
    )
    result = SimpleNamespace(status="unsupported", error=None, extraction=data)
    text = _assistant_text(result)
    assert "L-shaped bedroom" in text and "bed against the north wall" in text
    assert "no layout has changed" in text
    bare = _assistant_text(
        SimpleNamespace(status="unsupported", error=None, extraction=None)
    )
    assert "no layout has changed" in bare


def test_correction_conflicts_with_retained_request():
    for phrase in ("two writing desks", "a king bed"):
        result = run(
            TEXT + " I require " + phrase + ".",
            hard_constraints=(fact(phrase, phrase),),
        )
        assert result.status == "needs_clarification"
        assert result.draft is None


def test_shortened_constraint_cannot_drop_qualifiers_from_quoted_evidence():
    result = run(
        TEXT + " I require two writing desks.",
        hard_constraints=(fact("desk", "two writing desks"),),
    )
    assert result.status == "needs_clarification"


def test_quoted_list_only_restates_distinct_agreeing_items():
    assert (
        run(
            TEXT,
            hard_constraints=(fact("queen bed", "A queen bed and a writing desk."),),
        ).status
        == "needs_clarification"
    )
    assert (
        run(
            TEXT,
            hard_constraints=(fact("A queen bed", "A queen bed and a writing desk."),),
        ).status
        == "ready"
    )
    phrase = "A queen bed and two writing desks"
    assert (
        run(TEXT + " " + phrase, hard_constraints=(fact("A queen bed", phrase),)).status
        == "needs_clarification"
    )


def test_later_user_turn_requires_two_desks():
    from archimind.agents.catalog_requirements import CatalogChatTurn

    correction = "I require two writing desks."
    constraint = ChatTextFact(value="two writing desks", source=quote(correction, 2))
    result = reconcile_catalog_extraction(
        extraction().model_copy(update={"hard_constraints": (constraint,)}),
        (*turns(), CatalogChatTurn(id=2, role="user", content=correction)),
    )
    assert result.status == "needs_clarification" and result.draft is None
