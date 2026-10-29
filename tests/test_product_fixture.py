"""The explicit Charles fixture uses the same adapter and real spatial checks."""

import socket
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.examples.sample_product_room import (
    create_sample_product_fixture,
    create_sample_product_room,
)
from archimind.geometry import validate_accessibility
from archimind.render import product_scene
from archimind.ui import product_fixture as ui

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External operation forbidden")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def test_fixture_keeps_legacy_geometry_and_explicit_factory_bindings():
    fixture = create_sample_product_fixture()
    assert fixture.design == create_sample_product_room()
    assert fixture.design is not create_sample_product_room()
    assert len(fixture.planning_bindings) == 2
    for proof in fixture.planning_bindings:
        proof.validate_furniture(
            next(f for f in fixture.design.furniture if f.id == proof.furniture_id)
        )
    report = validate_accessibility(fixture.design, area_tolerance_m2=0.0)
    assert report.status == "passed" and not report.violations


def load():
    a = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    a.button(key="generate_layouts").click().run()
    a.checkbox(key="experimental_chair_enabled").check().run()
    a.radio(key="experimental_scene_mode").set_value("Charles product (08C-R2)").run()
    return a


def test_explicit_load_validates_once_and_ab_reruns_reuse_report(monkeypatch):
    spy = Mock(wraps=ui.validate_accessibility)
    seen = Mock()
    monkeypatch.setattr(ui, "validate_accessibility", spy)
    monkeypatch.setattr(product_scene, "_component", lambda: seen)
    a = load()
    assert not a.exception and spy.call_count == 1
    cached = a.session_state[ui.VALIDATION_KEY]
    assert isinstance(cached, tuple) and isinstance(cached[1], str)
    assert seen.call_args.kwargs["data"]["schema_version"] == 3
    assert (
        sum(
            b["asset_id"] is not None
            for b in seen.call_args.kwargs["data"]["asset_bindings"]
        )
        == 2
    )
    a.radio(key="selected_layout").set_value("Layout B").run()
    a.number_input(key="layout_seed").set_value(123).run()
    a.run()
    assert not a.exception and spy.call_count == 1
    assert a.session_state[ui.VALIDATION_KEY] is cached


def test_fixture_reports_are_session_local(monkeypatch):
    spy = Mock(wraps=ui.validate_accessibility)
    monkeypatch.setattr(ui, "validate_accessibility", spy)
    monkeypatch.setattr(product_scene, "_component", lambda: Mock())
    a, b = load(), load()
    assert not a.exception and not b.exception and spy.call_count == 2
    assert a.session_state[ui.VALIDATION_KEY] == b.session_state[ui.VALIDATION_KEY]
    a.session_state[ui.VALIDATION_KEY] = ("invalid", "{}")
    assert b.session_state[ui.VALIDATION_KEY][0] != "invalid"


def test_changed_fixture_geometry_invalidates_report(monkeypatch):
    spy = Mock(wraps=ui.validate_accessibility)
    monkeypatch.setattr(ui, "validate_accessibility", spy)
    monkeypatch.setattr(product_scene, "_component", lambda: Mock())
    a = load()
    original = a.session_state[ui.VALIDATION_KEY][0]
    factory = ui.create_sample_product_fixture

    def changed():
        fixture = factory()
        fixture.design.furniture[-1].x_m -= 0.1
        return fixture

    monkeypatch.setattr(ui, "create_sample_product_fixture", changed)
    a.run()
    assert not a.exception and spy.call_count == 2
    assert a.session_state[ui.VALIDATION_KEY][0] != original


def test_failed_spatial_fixture_never_mounts_and_failure_is_cached(monkeypatch):
    factory = ui.create_sample_product_fixture

    def blocked():
        fixture = factory()
        fixture.design.furniture[0].x_m = 0.5
        fixture.design.furniture[0].y_m = 0.0
        return fixture

    monkeypatch.setattr(ui, "create_sample_product_fixture", blocked)
    spy = Mock(wraps=ui.validate_accessibility)
    mount = Mock()
    monkeypatch.setattr(ui, "validate_accessibility", spy)
    monkeypatch.setattr(ui, "render_selected_realistic_scene", mount)
    a = load()
    assert not a.exception and not mount.called
    assert any("did not pass" in e.value for e in a.error)
    a.run()
    assert spy.call_count == 1 and not mount.called


def test_unexpected_fixture_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(
        ui,
        "render_selected_realistic_scene",
        Mock(side_effect=RuntimeError("secret-private-path")),
    )
    a = load()
    assert not a.exception
    assert "secret-private-path" not in str([e.value for e in a.error])
