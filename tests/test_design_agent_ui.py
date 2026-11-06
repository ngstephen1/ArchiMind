"""Chat panel with the real loop, tools and gate; only the model client is scripted."""

from streamlit.testing.v1 import AppTest
from test_design_agent_loop import (
    FakeModel,
    ReleasingModel,
    happy_script,
    response,
    say,
)

from archimind.examples.requirements_fixture import SAMPLE_REQUEST


def _panel() -> None:
    from archimind.ui.design_agent_chat import render_design_agent

    render_design_agent()


def _open(monkeypatch, model=None, *, enabled=True, key=True) -> AppTest:
    monkeypatch.delenv("ARCHIMIND_OPENAI_MODEL", raising=False)
    for name, value, on in (
        ("ARCHIMIND_ENABLE_OPENAI_AGENT", "1", enabled),
        ("OPENAI_API_KEY", "sk-test", key),
    ):
        if on:
            monkeypatch.setenv(name, value)
        else:
            monkeypatch.delenv(name, raising=False)
    if model is not None:
        monkeypatch.setattr("archimind.design_agent.loop._client", model.factory)
    return AppTest.from_function(_panel, default_timeout=30).run()


def _send(app: AppTest, text: str = SAMPLE_REQUEST) -> AppTest:
    app.checkbox(key="design_agent_consent").check().run()
    return app.chat_input[0].set_value(text).run()


def test_panel_explains_setup_when_the_agent_is_off(monkeypatch) -> None:
    app = _open(monkeypatch, enabled=False)
    assert not app.exception
    assert not app.chat_input
    assert "turned off" in app.info[0].value


def test_panel_explains_setup_when_the_key_is_missing(monkeypatch) -> None:
    app = _open(monkeypatch, key=False)
    assert not app.chat_input
    assert "OPENAI_API_KEY" in app.info[0].value


def test_input_is_disabled_until_consent(monkeypatch) -> None:
    model = FakeModel()
    app = _open(monkeypatch, model)
    assert app.chat_input[0].disabled
    assert not model.requests


def test_released_design_is_shown_with_its_summary(monkeypatch) -> None:
    app = _send(_open(monkeypatch, ReleasingModel(*happy_script())))
    assert not app.exception
    assert any(
        "Here it is." in message.markdown[0].value for message in app.chat_message
    )
    assert "code checks" in app.success[0].value
    assert app.get("plotly_chart")


def test_model_claim_without_release_shows_no_design(monkeypatch) -> None:
    model = FakeModel(*happy_script(), response(say("Your design is approved.")))
    app = _send(_open(monkeypatch, model))
    assert not app.exception
    assert not app.success
    assert not app.get("plotly_chart")


def test_failed_revision_says_the_shown_design_is_older(monkeypatch) -> None:
    model = ReleasingModel(*happy_script())
    app = _send(_open(monkeypatch, model))
    monkeypatch.setattr(
        "archimind.design_agent.loop._client",
        FakeModel(response(say("I need more detail."))).factory,
    )
    app = app.chat_input[0].set_value("Move the desk").run()
    assert not app.exception
    assert app.get("plotly_chart")
    assert any("earlier" in warning.value for warning in app.warning)


def test_usage_and_trace_are_visible(monkeypatch) -> None:
    app = _send(_open(monkeypatch, ReleasingModel(*happy_script())))
    captions = " ".join(caption.value for caption in app.caption)
    assert "tokens" in captions
    assert "Trace" in captions


def test_start_over_clears_the_conversation(monkeypatch) -> None:
    app = _send(_open(monkeypatch, ReleasingModel(*happy_script())))
    app = app.button(key="design_agent_reset").click().run()
    assert not app.chat_message
    assert not app.get("plotly_chart")
