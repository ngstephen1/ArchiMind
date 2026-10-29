"""Test-only external-operation and geometry tripwires for retrieval units."""

import socket
import subprocess

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Retrieval must not execute external/geometry work")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    for name in ("create_connection", "getaddrinfo", "gethostbyname"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    import openai

    import archimind.geometry as geometry
    from archimind.assets import render_assets

    for name in ("OpenAI", "AsyncOpenAI", "Client", "AsyncClient"):
        monkeypatch.setattr(openai, name, forbidden)
    for name in (
        "generate_layout_candidates",
        "validate_accessibility",
        "validate_layout",
    ):
        monkeypatch.setattr(geometry, name, forbidden)
    monkeypatch.setattr(render_assets, "verify_product_asset", forbidden)
