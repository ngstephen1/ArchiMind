"""Real generator + AppTest; the only substituted boundary is interpretation."""

import socket
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from catalog_chat_helpers import TEXT, extraction, measure, turns
from streamlit.testing.v1 import AppTest

from archimind.agents.catalog_conversation import reconcile_catalog_extraction
from archimind.agents.catalog_requirements import CatalogConversationResult
from archimind.agents.requirements_schemas import RequirementsError
from archimind.assets.specifications import BELAYA_ID
from archimind.ui import bedroom_chat as chat
from archimind.ui import furniture_assets as controls
from archimind.ui import layout_generation as ui
from archimind.ui import realistic_view as view

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("External operation forbidden")

    for n in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, n, fail)
    for n in ("create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, n, fail)
    monkeypatch.setattr(subprocess, "Popen", fail)
    import openai

    monkeypatch.setattr(openai, "OpenAI", fail)
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def spies(monkeypatch):
    response = reconcile_catalog_extraction(extraction(), turns())
    agent = Mock(return_value=response)
    gen = Mock(wraps=ui.generate_layout_candidates)
    val = Mock(wraps=ui.validate_accessibility)
    monkeypatch.setattr(chat, "interpret_catalog_conversation", agent)
    monkeypatch.setattr(ui, "generate_layout_candidates", gen)
    monkeypatch.setattr(ui, "validate_accessibility", val)
    return agent, gen, val


def app():
    a = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    return a.selectbox(key=controls.MODE_KEY).set_value(controls.CHAT).run()


def submit(a, text=TEXT):
    return a.chat_input(key="chat_bedroom_message").set_value(text).run()


def choose(a):
    a.selectbox(key="chat_choice:1:request-1").set_value("procedural:queen-bed").run()
    return a.selectbox(key="chat_choice:1:request-2").set_value(BELAYA_ID).run()


def test_full_chat_prepare_review_real_generation_and_pending_preservation(spies):
    agent, gen, val = spies
    a = app()
    assert a.button(key="generate_layouts").disabled
    submit(a)
    assert not a.exception
    assert agent.call_count == 1 and agent.call_args.kwargs["allow_live"] is True
    assert (
        a.button(key="prepare_chat").disabled
        and a.button(key="generate_layouts").disabled
    )
    choose(a)
    a.button(key="prepare_chat").click().run()
    assert not a.button(key="generate_layouts").disabled
    assert any("Review next chat" in str(m.value) for m in a.markdown)
    a.run()
    assert not a.button(key="generate_layouts").disabled
    assert gen.call_count == val.call_count == 0
    a.button(key="generate_layouts").click().run()
    assert not a.exception
    result = a.session_state[ui.RESULT_KEY]
    assert len(result.candidates) == 2 and all(
        c.validation.status == "passed" for c in result.candidates
    )
    assert gen.call_count == 1 and val.call_count == 2
    assert a.session_state[view.SNAPSHOT_KEY].source_mode == controls.CHAT
    desk = next(
        f for f in result.candidates[0].design.furniture if f.category == "desk"
    )
    assert (desk.width_m, desk.depth_m, desk.height_m) == (
        1.6,
        0.8018731772899628,
        0.7516312003135682,
    )
    assert result.candidates[0].design.room.windows == []
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    a.run()
    assert a.session_state[ui.RESULT_KEY] is result
    assert (agent.call_count, gen.call_count, val.call_count) == (1, 1, 2)
    a.selectbox(key="chat_choice:1:request-2").set_value("omit").run()
    assert (
        a.button(key="generate_layouts").disabled
        and a.session_state[ui.RESULT_KEY] is result
    )
    a.button(key="chat_bedroom_reset").click().run()
    assert (
        a.session_state[ui.RESULT_KEY] is result
        and a.button(key="generate_layouts").disabled
    )


def test_custom_room_and_exception_policy(spies, monkeypatch):
    agent, gen, val = spies
    e = extraction().model_copy(update={"width": measure(7)})
    agent.return_value = reconcile_catalog_extraction(
        e, turns(TEXT.replace("5 m wide", "7 m wide"))
    )
    a = app()
    submit(a, TEXT.replace("5 m wide", "7 m wide"))
    choose(a)
    a.button(key="prepare_chat").click().run()
    a.button(key="generate_layouts").click().run()
    result = a.session_state[ui.RESULT_KEY]
    assert result.candidates[0].design.room.width_m == 7
    revision = a.session_state[view.REVISION_KEY]
    gen.side_effect = RuntimeError("inert test exception")
    a.button(key="generate_layouts").click().run()
    assert (
        a.session_state[ui.RESULT_KEY] is result
        and a.session_state[view.REVISION_KEY] == revision
    )
    assert agent.call_count == 1


def test_clarification_then_error_no_generation(spies):
    agent, gen, val = spies
    agent.return_value = reconcile_catalog_extraction(
        extraction().model_copy(update={"ceiling_height": None}), turns()
    )
    a = app()
    submit(a)
    assert a.button(key="generate_layouts").disabled
    agent.return_value = CatalogConversationResult(
        status="unavailable",
        error=RequirementsError(
            code="authentication", message="Server credentials unavailable."
        ),
    )
    submit(a, "The ceiling is 2.7 m.")
    assert a.button(key="generate_layouts").disabled and not a.exception
    assert len(a.session_state[chat.TURNS]) == 4
    assert agent.call_count == 2 and gen.call_count == val.call_count == 0


def test_disabled_chat_no_model_and_independent_sessions(spies, monkeypatch):
    agent, gen, val = spies
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "0")
    a = app()
    assert a.chat_input(key="chat_bedroom_message").disabled
    a.run()
    agent.assert_not_called()
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    a = app()
    submit(a)
    b = app()
    assert chat.RESULT not in b.session_state
    assert agent.call_count == 1


def test_no_automatic_first_product_and_seed_keeps_preparation(spies):
    agent, gen, val = spies
    a = app()
    submit(a)
    assert a.selectbox(key="chat_choice:1:request-2").value == "choose"
    choose(a)
    a.button(key="prepare_chat").click().run()
    prepared = a.session_state[chat.PREPARED]
    a.number_input(key="layout_seed").set_value(43).run()
    assert (
        a.session_state[chat.PREPARED] is prepared
        and not a.button(key="generate_layouts").disabled
    )
    assert agent.call_count == 1 and gen.call_count == val.call_count == 0


def test_refresh_catalog_requires_new_choices_without_model_or_generation(spies):
    agent, gen, val = spies
    a = app()
    submit(a)
    choose(a)
    a.button(key="prepare_chat").click().run()
    a.button(key="chat_refresh_catalog").click().run()
    assert not a.exception
    assert a.selectbox(key="chat_choice:2:request-2").value == "choose"
    assert a.button(key="generate_layouts").disabled
    assert agent.call_count == 1 and gen.call_count == val.call_count == 0


def test_missing_planning_evidence_invalidates_prepared_not_results(spies, monkeypatch):
    from archimind.assets import specifications

    agent, gen, val = spies
    a = app()
    submit(a)
    choose(a)
    a.button(key="prepare_chat").click().run()
    a.button(key="generate_layouts").click().run()
    result = a.session_state[ui.RESULT_KEY]
    monkeypatch.setattr(
        specifications,
        "load_planning_envelope",
        Mock(side_effect=ValueError("missing evidence")),
    )
    a.run()
    assert (
        a.button(key="generate_layouts").disabled
        and a.session_state[ui.RESULT_KEY] is result
    )
    assert any(
        "Required planning evidence is unavailable" in w.value for w in a.warning
    )
    assert (agent.call_count, gen.call_count, val.call_count) == (1, 1, 2)


def test_new_message_invalidates_prepared_and_preserves_existing_results(spies):
    agent, gen, val = spies
    a = app()
    submit(a)
    choose(a)
    a.button(key="prepare_chat").click().run()
    a.button(key="generate_layouts").click().run()
    result = a.session_state[ui.RESULT_KEY]
    agent.return_value = reconcile_catalog_extraction(
        extraction().model_copy(update={"width": None}), turns()
    )
    submit(a, "Change the room width; I will measure it.")
    assert (
        a.button(key="generate_layouts").disabled
        and a.session_state[ui.RESULT_KEY] is result
    )
    assert (agent.call_count, gen.call_count, val.call_count) == (2, 1, 2)


def test_reset_keeps_consent_usable_and_starts_fresh_turns(spies):
    agent, gen, val = spies
    a = app()
    submit(a)
    choose(a)
    a.button(key="prepare_chat").click().run()
    a.button(key="generate_layouts").click().run()
    result = a.session_state[ui.RESULT_KEY]
    a.button(key="chat_bedroom_reset").click().run()
    assert not a.chat_input(key="chat_bedroom_message").disabled
    a.chat_input(key="chat_bedroom_message").set_value(TEXT).run()
    assert not a.exception
    assert agent.call_count == 2
    assert len(agent.call_args.args[0]) == 1 and agent.call_args.args[0][0].id == 1
    assert a.selectbox(key="chat_choice:1:request-1").value == "choose"
    assert a.button(key="generate_layouts").disabled
    assert a.session_state[ui.RESULT_KEY] is result
    assert gen.call_count == 1 and val.call_count == 2
