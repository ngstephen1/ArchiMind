"""Explicit actions, separate sessions and exact selected-object handoff."""

from streamlit.testing.v1 import AppTest

from archimind.ui import studio

APP = "from archimind.ui.studio import render_studio\nrender_studio()"


def test_offline_review_build_and_ab_never_make_provider_calls(monkeypatch):
    monkeypatch.delenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", raising=False)
    monkeypatch.setattr(
        "archimind.studio.provider.configuration",
        lambda *a: (_ for _ in ()).throw(AssertionError("unexpected provider")),
    )
    calls = []
    real_build = studio.build_room
    monkeypatch.setattr(
        studio,
        "build_room",
        lambda *a, **kw: (calls.append(1), real_build(*a, **kw))[1],
    )
    handoff = []
    real_floor = studio.render_floorplan
    monkeypatch.setattr(
        studio, "render_floorplan", lambda d: (handoff.append(d), real_floor(d))[1]
    )
    # Components are opaque to AppTest; geometry is verified in JS/browser tests.
    scenes = []
    monkeypatch.setattr(
        studio, "_component", lambda: lambda **kw: scenes.append(kw["data"])
    )
    app = AppTest.from_string(APP, default_timeout=30).run()
    assert not app.exception
    assert app.button(key="studio_propose").disabled
    app.button(key="studio_example").click().run()
    assert studio.DRAFT in app.session_state and studio.BUILD not in app.session_state
    app.button(key="studio_build_button").click().run()
    assert not app.exception and len(calls) == 1
    built = app.session_state[studio.BUILD]
    assert len(built.result().candidates) == 2
    app.radio(key="studio_selection_1").set_value("Layout B").run()
    assert len(calls) == 1 and handoff[-1] == built.result().candidates[1].design
    assert scenes[-1]["design"] == handoff[-1].model_dump(mode="json")
    app.radio(key="studio_view").set_value("Plotly schematic").run()
    assert len(calls) == 1
    app.number_input(key="studio_width").set_value(6.0).run()
    assert studio.DRAFT not in app.session_state
    assert app.session_state[studio.BUILD] == built and len(calls) == 1
    other = AppTest.from_string(APP, default_timeout=30).run()
    assert studio.BUILD not in other.session_state


def test_failed_build_keeps_last_snapshot(monkeypatch):
    monkeypatch.setattr(studio, "_component", lambda: lambda **kw: None)
    app = AppTest.from_string(APP, default_timeout=30).run()
    app.button(key="studio_example").click().run()
    app.button(key="studio_build_button").click().run()
    previous = app.session_state[studio.BUILD]

    def fail(*a, **k):
        raise RuntimeError("private exception detail")

    monkeypatch.setattr(studio, "build_room", fail)
    app.button(key="studio_build_button").click().run()
    assert app.session_state[studio.BUILD] == previous
    assert "private exception detail" not in str(app.error)


def test_unexpected_proposal_failure_is_sanitized_and_keeps_results(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setattr(studio, "_component", lambda: lambda **kw: None)
    app = AppTest.from_string(APP, default_timeout=30).run()
    app.button(key="studio_example").click().run()
    app.button(key="studio_build_button").click().run()
    previous = app.session_state[studio.BUILD]

    def fail(*a, **k):
        raise RuntimeError("private request detail")

    monkeypatch.setattr(studio, "propose_room", fail)
    app.checkbox(key="studio_consent").check().run()
    app.button(key="studio_propose").click().run()
    assert not app.exception
    assert studio.DRAFT not in app.session_state
    assert app.session_state[studio.BUILD] == previous
    assert "private request detail" not in str(app.error)


def test_failed_offline_example_clears_pending_ai_plan(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_STUDIO", "1")
    monkeypatch.setattr(studio, "_component", lambda: lambda **kw: None)
    app = AppTest.from_string(APP, default_timeout=30).run()
    app.button(key="studio_example").click().run()
    example = app.session_state[studio.DRAFT]
    app.button(key="studio_build_button").click().run()
    displayed = app.session_state[studio.BUILD]
    calls = []

    def propose(*args, offline=False, **kwargs):
        calls.append(offline)
        if offline:
            raise ValueError("Example does not fit")
        return example.model_copy(
            update={"source": "ai_concept", "model": "test-model"}
        )

    monkeypatch.setattr(studio, "propose_room", propose)
    app.checkbox(key="studio_consent").check().run()
    app.button(key="studio_propose").click().run()
    assert app.session_state[studio.DRAFT].source == "ai_concept"
    app.button(key="studio_example").click().run()
    assert not app.exception and app.error
    assert studio.DRAFT not in app.session_state
    assert all(button.key != "studio_build_button" for button in app.button)
    assert app.session_state[studio.BUILD] == displayed
    assert calls == [False, True]
