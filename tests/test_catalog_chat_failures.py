"""Provider failures stay explicit and sanitized without automatic retries."""

from unittest.mock import Mock

import httpx2
import pytest
from catalog_chat_helpers import extraction, turns
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from archimind.agents.catalog_conversation import interpret_catalog_conversation


@pytest.mark.parametrize(
    "kind,code",
    [
        ("timeout", "timeout"),
        ("connection", "connection"),
        ("authentication", "authentication"),
        ("rate_limit", "rate_limit"),
        ("server", "api_error"),
    ],
)
def test_provider_failure_is_one_attempt_and_never_leaks(monkeypatch, kind, code):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "inert-test-value")
    monkeypatch.delenv("ARCHIMIND_OPENAI_MODEL", raising=False)
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    if kind in ("timeout", "connection"):
        error = (APITimeoutError if kind == "timeout" else APIConnectionError)(
            request=request
        )
    else:
        cls, status = {
            "authentication": (AuthenticationError, 401),
            "rate_limit": (RateLimitError, 429),
            "server": (InternalServerError, 500),
        }[kind]
        error = cls(
            "private-provider-detail",
            response=httpx2.Response(status, request=request),
            body={"sensitive": "private-provider-detail"},
        )
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.side_effect = error
    result = interpret_catalog_conversation(
        turns(), allow_live=True, client_factory=lambda _: client
    )
    assert result.error.code == code and result.draft is None
    assert "private-provider-detail" not in result.model_dump_json()
    assert client.responses.parse.call_count == 1


def test_invalid_large_clarification_is_sanitized_before_UI(monkeypatch):
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "inert-test-value")
    monkeypatch.delenv("ARCHIMIND_OPENAI_MODEL", raising=False)
    data = extraction().model_copy(update={"missing_or_ambiguous": ("x" * 5000,)})
    response = Mock(status="completed", output=[], output_parsed=data)
    response.model_dump_json.return_value = "{}"
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.responses.parse.return_value = response
    result = interpret_catalog_conversation(
        turns(), allow_live=True, client_factory=lambda _: client
    )
    assert result.error.code == "invalid_response"
    assert "x" * 5000 not in result.model_dump_json()
