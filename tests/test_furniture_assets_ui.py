"""Pending controls stay separate from generation and selected-layout state."""

from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.assets.specifications import BOOKCASE_ID, CHARLES_ID
from archimind.ui import furniture_assets as panel


@pytest.fixture(autouse=True)
def no_backend_work(monkeypatch):
    import socket
    import subprocess

    import archimind.geometry as geometry

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Pending controls must not perform external or spatial work"
        )

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for name in ("generate_layout_candidates", "validate_accessibility"):
        monkeypatch.setattr(geometry, name, forbidden)


def app():
    return AppTest.from_string("""
import streamlit as st
from archimind.examples import create_sample_bedroom
from archimind.ui.furniture_assets import render_furniture_assets
st.session_state['pending'] = render_furniture_assets(create_sample_bedroom())
""").run()


def catalog(a):
    return a.selectbox(key=panel.MODE_KEY).set_value(panel.CATALOG).run()


def test_default_and_explicit_preparation():
    a = app()
    assert not a.session_state["pending"].catalog_mode
    catalog(a)
    assert all(
        a.checkbox(key=f"keep_manual:{fid}").value
        for fid in ("queen-bed", "desk", "wardrobe")
    )
    assert not a.checkbox(key=f"catalog_product:{CHARLES_ID}").value
    assert a.session_state["pending"].prepared is None
    a.button(key="prepare_catalog").click().run()
    assert len(a.session_state["pending"].prepared.design().furniture) == 3
    assert not a.exception


def test_selection_invalidates_review_and_preparation_is_not_generation():
    a = catalog(app())
    a.checkbox(key=f"catalog_product:{CHARLES_ID}").check().run()
    a.button(key="prepare_catalog").click().run()
    p = a.session_state["pending"].prepared
    assert len(p.design().furniture) == 4
    a.checkbox(key=f"catalog_product:{BOOKCASE_ID}").check().run()
    assert a.session_state["pending"].prepared is None
    assert a.session_state[panel.PREPARED_KEY] is p
    a.button(key="prepare_catalog").click().run()
    assert len(a.session_state["pending"].prepared.design().furniture) == 5


def test_empty_review_and_sessions_are_independent():
    a, b = catalog(app()), catalog(app())
    for fid in ("queen-bed", "desk", "wardrobe"):
        a.checkbox(key=f"keep_manual:{fid}").uncheck().run()
    a.button(key="prepare_catalog").click().run()
    assert not a.session_state["pending"].prepared.design().furniture
    assert any("one distinct empty" in i.value for i in a.info)
    assert b.session_state["pending"].prepared is None
    assert all(
        b.checkbox(key=f"keep_manual:{fid}").value
        for fid in ("queen-bed", "desk", "wardrobe")
    )


def test_unavailable_catalog_is_sanitized(monkeypatch):
    monkeypatch.setattr(
        panel, "catalog_product_options", Mock(side_effect=ValueError("secret-token"))
    )
    a = catalog(app())
    assert not a.exception and a.session_state["pending"].prepared is None
    assert "secret-token" not in str([i.value for i in a.error])
