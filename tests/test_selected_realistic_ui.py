"""Selected 3D view and generation-sidecar contracts in independent sessions."""

import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.assets import furniture_from_planning_envelope
from archimind.assets.render_qualification import CHARLES_ID
from archimind.examples import create_sample_bedroom
from archimind.geometry import LayoutGenerationResult
from archimind.render import product_scene
from archimind.ui import interior_styling
from archimind.ui import layout_generation as ui
from archimind.ui import realistic_view as view

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External operation forbidden")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    for name in ("create_connection", "getaddrinfo", "gethostbyname"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


@pytest.fixture
def spies(monkeypatch):
    result = SimpleNamespace(
        generator=Mock(wraps=ui.generate_layout_candidates),
        validator=Mock(wraps=ui.validate_accessibility),
        plot=Mock(wraps=ui.render_design_3d),
        plan=Mock(wraps=ui.render_floorplan),
        three=Mock(wraps=view.render_selected_realistic_scene),
        component=Mock(),
    )
    for name, value in [
        ("generate_layout_candidates", result.generator),
        ("validate_accessibility", result.validator),
        ("render_design_3d", result.plot),
        ("render_floorplan", result.plan),
    ]:
        monkeypatch.setattr(ui, name, value)
    monkeypatch.setattr(view, "render_selected_realistic_scene", result.three)
    monkeypatch.setattr(product_scene, "_component", lambda: result.component)
    return result


def app():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def generate(a):
    return a.button(key="generate_layouts").click().run()


def three(a):
    return a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()


def test_default_inactivity_and_plotly_default(spies):
    a = app()
    assert not spies.component.called and not a.exception
    generate(a)
    assert a.radio(key=view.VIEW_KEY).value == view.PLOTLY_VIEW
    assert spies.plot.called and not spies.component.called


def test_switching_active_renderer_and_ab_uses_exact_stored_objects(spies):
    a = generate(app())
    result = a.session_state[ui.RESULT_KEY]
    before = result.model_dump_json()
    counts = spies.generator.call_count, spies.validator.call_count
    plot_calls = spies.plot.call_count
    three(a)
    assert not a.exception and spies.plot.call_count == plot_calls
    assert spies.three.call_args.args[0] is result.candidates[0].design
    assert spies.plan.call_args.args[0] is result.candidates[0].design
    first_key = spies.component.call_args.kwargs["key"]
    for index, label in [(1, "Layout B"), (0, "Layout A")]:
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
        assert not a.exception
        assert (
            spies.three.call_args.args[0]
            is spies.plan.call_args.args[0]
            is result.candidates[index].design
        )
        assert spies.component.call_args.kwargs["data"]["design"] == result.candidates[
            index
        ].design.model_dump(mode="json")
        assert spies.component.call_args.kwargs["key"] == first_key
        assert all(
            b["asset_id"] is None
            for b in spies.component.call_args.kwargs["data"]["asset_bindings"]
        )
    a.radio(key=view.VIEW_KEY).set_value(view.PLOTLY_VIEW).run()
    assert spies.plot.call_args.args[0] is result.candidates[0].design
    assert (spies.generator.call_count, spies.validator.call_count) == counts
    assert before == result.model_dump_json()
    assert a.session_state[ui.RESULT_KEY] is result


def test_pending_seed_and_rerun_preserve_revision_snapshot_and_payload(spies):
    a = three(generate(app()))
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    payload = spies.component.call_args.kwargs
    calls = spies.generator.call_count, spies.validator.call_count
    a.number_input(key="layout_seed").set_value(1234).run()
    a.run()
    assert not a.exception
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert spies.component.call_args.kwargs == payload
    assert (spies.generator.call_count, spies.validator.call_count) == calls


def test_identical_seed_regeneration_invalidates_render_context(spies):
    a = three(generate(app()))
    original = a.session_state[ui.RESULT_KEY].model_dump_json()
    old_key = spies.component.call_args.kwargs["key"]
    old_revision = a.session_state[view.REVISION_KEY]
    generate(a)
    assert a.session_state[ui.RESULT_KEY].model_dump_json() == original
    assert a.session_state[view.REVISION_KEY] == old_revision + 1
    assert spies.component.call_args.kwargs["key"] != old_key
    assert a.radio(key=view.VIEW_KEY).value == view.THREE_VIEW


def test_failed_generation_keeps_selection_snapshot_and_camera_context(spies):
    a = three(generate(app()))
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    result = a.session_state[ui.RESULT_KEY]
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    key = spies.component.call_args.kwargs["key"]
    spies.generator.side_effect = RuntimeError("secret-token-do-not-show")
    generate(a)
    assert not a.exception
    assert a.session_state[ui.RESULT_KEY] is result
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert a.radio(key=ui.SELECTION_KEY).value == "Layout B"
    assert spies.component.call_args.kwargs["key"] == key
    assert "secret-token" not in str([e.value for e in a.error])


def test_two_sessions_do_not_share_selection_or_view(spies):
    a, b = generate(app()), generate(app())
    three(a)
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    assert b.radio(key=ui.SELECTION_KEY).value == "Layout A"
    assert b.radio(key=view.VIEW_KEY).value == view.PLOTLY_VIEW
    assert a.session_state[ui.RESULT_KEY] is not b.session_state[ui.RESULT_KEY]
    assert a.session_state[view.SNAPSHOT_KEY] is not b.session_state[view.SNAPSHOT_KEY]


def test_renderer_failure_sanitized_and_recoverable(spies):
    a = generate(app())
    original = a.session_state[ui.RESULT_KEY].model_dump_json()
    spies.three.side_effect = RuntimeError("sk-secret-provider-error")
    three(a)
    assert not a.exception
    assert "sk-secret" not in str([e.value for e in a.error])
    assert a.session_state[ui.RESULT_KEY].model_dump_json() == original
    a.radio(key=view.VIEW_KEY).set_value(view.PLOTLY_VIEW).run()
    assert not a.exception and spies.plot.called


def test_styling_survives_view_change_but_clears_on_ab_change(spies):
    a = generate(app())
    a.button(key="show_fixture_styling").click().run()
    stored = a.session_state[interior_styling.RESULT_KEY]
    three(a)
    assert not a.exception
    assert a.session_state[interior_styling.RESULT_KEY] is stored
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    assert not a.exception
    assert interior_styling.RESULT_KEY not in a.session_state


def test_snapshot_freezes_submitted_proof_and_rejects_stale_context():
    spec = create_sample_bedroom()
    p = furniture_from_planning_envelope(
        CHARLES_ID, furniture_id="c", name="Charles", x_m=1.0, y_m=1.0
    )
    spec.furniture = [p.furniture]
    result = ui._generate(spec, 42)
    proofs = {"c": p.binding}
    snap = view.snapshot_generation(spec, result, 1, proofs)
    proofs.clear()
    assert snap.bindings == (p.binding,)
    assert snap.generation_digest == view.digest(result)
    assert snap.specification_digest == view.digest(spec)
    assert result.candidates


def test_stored_proofs_used_instead_of_pending_inputs(spies):
    # The explicit backend caller is a test fixture, not an 08E UI control.
    script = """
from archimind.examples import create_sample_bedroom
from archimind.assets import furniture_from_planning_envelope
from archimind.assets.render_qualification import CHARLES_ID
from archimind.ui.layout_generation import render_layout_generator
import streamlit as st
spec = create_sample_bedroom()
p = furniture_from_planning_envelope(CHARLES_ID, furniture_id='c', name='Charles', x_m=1.0, y_m=1.0)
spec.furniture = [p.furniture]
render_layout_generator(spec, planning_bindings={} if st.session_state.get('pending_changed') else {'c':p.binding})
"""
    a = AppTest.from_string(script, default_timeout=30).run()
    generate(a)
    three(a)
    assert not a.exception
    assert (
        spies.component.call_args.kwargs["data"]["asset_bindings"][0]["asset_id"]
        == CHARLES_ID
    )
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    a.session_state["pending_changed"] = True
    a.run()
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert (
        spies.component.call_args.kwargs["data"]["asset_bindings"][0]["asset_id"]
        == CHARLES_ID
    )
    generate(a)
    assert a.session_state[view.SNAPSHOT_KEY].bindings == ()
    assert (
        spies.component.call_args.kwargs["data"]["asset_bindings"][0]["asset_id"]
        is None
    )


def test_empty_generation_unmounts_without_discarding_view_preference(spies):
    a = three(generate(app()))
    old_revision = a.session_state[view.REVISION_KEY]
    spies.generator.return_value = LayoutGenerationResult(
        status="infeasible",
        message="No candidates",
        seed=42,
        requested_candidates=2,
        max_attempts=500,
        attempts_used=0,
        config=a.session_state[ui.RESULT_KEY].config,
        candidates=[],
    )
    spies.generator.side_effect = None
    count = spies.component.call_count
    generate(a)
    assert not a.exception and spies.component.call_count == count
    assert a.session_state[view.REVISION_KEY] == old_revision + 1
    assert a.session_state[ui.RESULT_KEY].candidates == []
    assert a.session_state[view.VIEW_KEY] == view.THREE_VIEW


def test_unsupported_rotation_is_explicit_and_not_coerced(spies):
    a = three(generate(app()))
    result = a.session_state[ui.RESULT_KEY]
    result.candidates[0].design.furniture[0].rotation_deg = 90
    before = result.model_dump_json()
    calls = (
        spies.generator.call_count,
        spies.validator.call_count,
        spies.three.call_count,
    )
    a.run()
    assert not a.exception
    assert any("unsupported rotation" in e.value for e in a.error)
    assert (
        spies.generator.call_count,
        spies.validator.call_count,
        spies.three.call_count,
    ) == calls
    assert result.model_dump_json() == before


def test_altered_generation_invalidates_stored_binding_context(spies):
    a = three(generate(app()))
    result = a.session_state[ui.RESULT_KEY]
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    result.candidates[0].score.total -= 0.001
    before = result.model_dump_json()
    a.run()
    assert not a.exception
    assert any("stale or incompatible" in e.value for e in a.warning)
    assert not spies.three.call_args.kwargs["planning_bindings"]
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert result.model_dump_json() == before


def test_invalid_submitted_sidecar_is_not_snapshotted():
    spec = create_sample_bedroom()
    p = furniture_from_planning_envelope(
        CHARLES_ID, furniture_id="c", name="Charles", x_m=1.0, y_m=1.0
    )
    spec.furniture = [p.furniture]
    result = ui._generate(spec, 42)
    snap = view.snapshot_generation(
        spec,
        result,
        1,
        {"c": p.binding.model_copy(update={"metadata_sha256": "0" * 64})},
    )
    assert snap.invalid_evidence and not snap.bindings
