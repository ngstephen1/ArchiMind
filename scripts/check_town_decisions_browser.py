"""Replay Town's Decisions review in Chrome using recorded model results."""

import argparse
import json
import os
import socket
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import uvicorn
from playwright.sync_api import expect, sync_playwright

from archimind.town import decisions, service
from archimind.town.design_review import Direction, VisualReview

ROOT = Path(__file__).resolve().parents[1]
FLAGGED = "The salon must have measured acoustic isolation from the study."
CORRECTED = "Use the formal salon as a social room."
TIMEOUT = "Keep the formal salon and use warm finishes."


def response(schema, *_args, **_kwargs):
    if schema is Direction:
        return Direction(
            material_direction="Oak", lighting_direction="Daylight", tradeoff="Replay"
        )
    if schema is VisualReview:
        return VisualReview(
            observation="Replay",
            recommendation="Inspect the plan",
            uncertainty="Replay",
        )
    values = {
        "priority": "balanced",
        "style": "scandinavian",
        "clarification": "",
        "unsupported": [],
    }
    if "lock_rooms" in schema.model_fields:
        values.update(lock_rooms=[], lock_furniture=[])
    return schema.model_validate(values)


def browser_check(url, output):
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.locator("#design").click()
        page.locator("#width").fill("15")
        page.locator("#depth").fill("16")
        page.locator("#formalSalon").check()

        def generate(message):
            page.locator("#message").fill(message)
            page.locator("#generate").click()

        generate(FLAGGED)
        expect(page.locator("#reviewBrief")).to_contain_text(
            "Please confirm which requirement", timeout=30_000
        )
        expect(page.locator("#alternatives")).to_be_hidden()
        page.locator("#reviewBrief").screenshot(path=output / "clarification.png")

        generate(CORRECTED)
        expect(page.locator("#choices button")).to_have_count(2, timeout=30_000)
        page.locator("#choices").screenshot(path=output / "alternatives.png")
        page.locator("#apply").click()
        expect(page.locator("#revision")).to_contain_text("Revision 1", timeout=30_000)
        if not page.locator("#panel").evaluate("(el) => el.open"):
            page.locator("#design").click()
        generate(TIMEOUT)
        expect(page.locator("#choices button")).to_have_count(2, timeout=30_000)
        expect(page.locator("#notice")).to_contain_text(
            "Checks complete", timeout=30_000
        )
        page.locator('#agentCards [data-agent="A"] summary').click()
        message = page.get_by_text(
            "Unavailable. Existing checks continue.", exact=False
        )
        expect(message).to_be_visible()
        message.screenshot(path=output / "timeout.png")
        expect(page.locator("#revision")).to_contain_text("Revision 1")
        page.locator("#choices button").nth(1).click()
        page.locator("#visit").click()
        expect(page.locator("#panel")).to_be_hidden()
        browser.close()
    return errors


def check(output):
    output.mkdir(parents=True, exist_ok=True)
    calls = []

    def audit(payload, **_kwargs):
        message = payload["original_brief"]
        calls.append(message)
        return {
            "rubric": decisions.RUBRIC,
            "model": decisions.MODEL,
            "status": "unavailable" if message == TIMEOUT else "checked",
            "reason": "connection_or_timeout" if message == TIMEOUT else None,
            "probabilities": {
                "unsupported_requirement_unaddressed": 0.99
                if message == FLAGGED
                else 0.01
            }
            if message != TIMEOUT
            else {},
        }

    with tempfile.TemporaryDirectory() as temporary, socket.socket() as listener:
        directory = Path(temporary)
        promotion = directory / "recorded-promotion.json"
        promotion.write_text(
            json.dumps(
                {
                    "model": decisions.MODEL,
                    "rubric": decisions.RUBRIC,
                    "selected_threshold": 0.85,
                    "heldout_gate_passed": True,
                    "responses_complete": True,
                    "requests": 6,
                    "p95_ms": 500,
                }
            )
        )
        env = {
            "TOWN_DB": str(directory / "town.sqlite"),
            "TOWN_MODE": "local",
            "TOWN_STATIC": str(ROOT / "dist/town"),
            "OPENAI_API_KEY": "browser-fixture",
            "ARCHIMIND_ENABLE_OPENAI_STUDIO": "1",
            "ARCHIMIND_ENABLE_CODEX_ADVISOR": "0",
            "TOWN_DAILY_MODEL_CALLS": "12",
            "TOWN_DAILY_MICROUSD": "12",
            "TOWN_CALL_RESERVE_MICROUSD": "1",
            "ARCHIMIND_TOWN_DECISIONS_MODE": "clarify",
            "ARCHIMIND_TOWN_DECISIONS_PROMOTION_RECEIPT": str(promotion),
        }
        with (
            patch.dict(os.environ, env),
            patch.object(service.provider, "request", response),
            patch.object(decisions, "audit", audit),
        ):
            os.environ.pop("DATABASE_URL", None)
            service.initialize()
            listener.bind(("127.0.0.1", 0))
            host, port = listener.getsockname()
            server = uvicorn.Server(
                uvicorn.Config("archimind.town.api:app", access_log=False)
            )
            serving = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}
            )
            stop = threading.Event()

            def work():
                while not stop.wait(0.15):
                    service.work_once()

            worker = threading.Thread(target=work)
            serving.start()
            worker.start()
            try:
                errors = browser_check(f"http://{host}:{port}/", output)
            finally:
                stop.set()
                worker.join()
                server.should_exit = True
                serving.join()
    assert calls == [FLAGGED, CORRECTED, TIMEOUT] and not errors
    (output / "receipt.json").write_text(
        json.dumps(
            {
                "mode": "recorded model responses",
                "viewport": [1440, 1000],
                "decisions_fixture_calls": len(calls),
                "external_model_calls": 0,
                "page_errors": errors,
                "checks": [
                    "clarification",
                    "corrected A/B",
                    "timeout A/B with revision 1 preserved",
                    "switch to B and open the walkthrough with no extra Decisions call",
                ],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    check(parser.parse_args().output)
