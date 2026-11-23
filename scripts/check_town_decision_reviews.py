"""Exercise optional Town Decisions checks in Chrome with local response fixtures."""

import argparse
import json
import os
import socket
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import uvicorn
from evaluate_town_decision_reviews import CORPUS, CURRENT, PRIOR, ROOT
from playwright.sync_api import expect, sync_playwright

from archimind.town import decision_review, service

COMPARE = "What changed when we pulled the chair out?"
TIMEOUT = "It might need a different chair."
GENERAL_COMPARE = "Compare the two saved revisions."
MIXED = "Why is the chair there? Move it closer."


def browser_check(url, output, stale_started, release_stale, route_receipt):
    errors = []
    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.locator("#design").click()
        route = page.locator("#requestReviewStatus")
        page.locator("#message").fill(COMPARE)
        page.locator("#checkRequest").click()
        expect(route).to_contain_text("Calibration check recorded")
        expect(page.locator("#openSavedAnswer")).to_be_hidden()
        page.locator("#requestReview").screenshot(path=output / "request-shadow.png")

        page.locator("#message").fill(MIXED)
        page.locator("#checkRequest").click()
        expect(route).to_contain_text("Calibration check recorded")
        expect(page.locator("#openSavedAnswer")).to_be_hidden()
        page.locator("#message").fill(TIMEOUT)
        page.locator("#checkRequest").click()
        expect(route).to_contain_text("Review unavailable")
        page.locator("#message").fill(
            "Why will the chair fit? I mean the one at Belaya."
        )
        page.locator("#checkRequest").click()
        expect(route).to_contain_text("question about a saved design")
        page.locator("#openSavedAnswer").click()
        expect(page.locator("#whyAnswer")).to_contain_text("Under-desk knee clearance")
        page.locator("#whyQuery").fill(COMPARE)
        page.locator("#askWhy").click()
        expect(page.locator("#whyAnswer")).to_contain_text("0.300 m")
        page.locator("#checkEvidence").click()
        expect(page.locator("#evidenceReviewItems")).to_contain_text(
            "Supported by the supplied facts"
        )
        expect(page.locator("#whyAnswer")).to_contain_text("0.300 m")
        page.locator("#evidenceReview").screenshot(path=output / "evidence-review.png")

        page.locator("#whyQuery").fill("Why will the chair fit?")
        page.locator("#askWhy").click()
        expect(page.locator("#whyAnswer")).to_contain_text("Under-desk knee clearance")
        with page.expect_response(
            lambda res: (
                res.request.method == "POST" and res.url.endswith("/decision-review")
            )
        ):
            page.locator("#checkEvidence").click()
            assert stale_started.wait(3)
            page.locator("#whyQuery").fill("Edited while the check was running")
            release_stale.set()
        expect(page.locator("#evidenceReview")).to_be_hidden()
        expect(page.locator("#evidenceReviewItems")).to_be_empty()
        page.get_by_label("Close presentation").click()

        # Simulate a qualifying route receipt to exercise the advisory delivery.
        os.environ["ARCHIMIND_TOWN_DECISIONS_ROUTE_RECEIPT"] = str(route_receipt)
        page.reload()
        page.locator("#design").click()
        page.locator("#message").fill(COMPARE)
        page.locator("#checkRequest").click()
        expect(route).to_contain_text("compare the saved revisions")
        page.locator("#openSavedAnswer").click()
        expect(page.locator("#whyAnswer")).to_contain_text("0.300 m")
        page.get_by_label("Close presentation").click()

        page.locator("#design").click()
        page.locator("#message").fill(GENERAL_COMPARE)
        page.locator("#checkRequest").click()
        page.locator("#openSavedAnswer").click()
        expect(page.locator("#whyAnswer")).to_contain_text(
            "currently cover the bedroom desk chair"
        )
        page.get_by_label("Close presentation").click()
        page.locator("#tour").click()
        expect(page.locator("#revision")).to_contain_text("Revision 2")
        browser.close()
    return errors


def check(output):
    output.mkdir(parents=True, exist_ok=True)
    calls = []
    stale_started, release_stale = threading.Event(), threading.Event()

    def evaluate(kind, message, *, facts, claims):
        calls.append((kind, message))
        if kind == "route":
            if message == TIMEOUT:
                return {
                    "status": "unavailable",
                    "reason": "connection_or_timeout",
                    "answers": {},
                }
            return {
                "status": "checked",
                "answers": {
                    "intent": {
                        "label": "clarify" if message == MIXED else "compare",
                        "confidence": 0.9,
                    }
                },
            }
        assert facts["chair_displacement_m"] == 0.3
        if message != COMPARE:
            stale_started.set()
            if not release_stale.wait(3):
                return {
                    "status": "unavailable",
                    "reason": "connection_or_timeout",
                    "answers": {},
                }
        return {
            "status": "checked",
            "answers": {
                f"claim_{i}": {"label": "supported", "confidence": 0.9}
                for i in range(len(claims))
            },
        }

    with tempfile.TemporaryDirectory() as temporary, socket.socket() as listener:
        route_receipt = Path(temporary) / "simulated-route-receipt.json"
        promoted = json.loads((CORPUS / "route-receipt.json").read_bytes())
        promoted["heldout_passed"] = True
        promoted["holdout_metrics"].update(coverage=1.0, accepted=16, correct=16)
        route_receipt.write_text(json.dumps(promoted))
        env = {
            "TOWN_DB": str(Path(temporary) / "town.sqlite"),
            "TOWN_MODE": "local",
            "TOWN_STATIC": str(ROOT / "dist/town"),
            "OPENAI_API_KEY": "browser-fixture",
            "ARCHIMIND_ENABLE_OPENAI_STUDIO": "1",
            "TOWN_DAILY_MODEL_CALLS": "17",
            "TOWN_DAILY_MICROUSD": "17",
            "TOWN_CALL_RESERVE_MICROUSD": "1",
            "ARCHIMIND_TOWN_DECISIONS_ROUTE_MODE": "advisory",
            "ARCHIMIND_TOWN_DECISIONS_ROUTE_RECEIPT": str(
                CORPUS / "route-receipt.json"
            ),
            "ARCHIMIND_TOWN_DECISIONS_EVIDENCE_MODE": "advisory",
            "ARCHIMIND_TOWN_DECISIONS_EVIDENCE_RECEIPT": str(
                CORPUS / "evidence-receipt.json"
            ),
        }
        with (
            patch.dict(os.environ, env),
            patch.object(decision_review, "evaluate", evaluate),
        ):
            os.environ.pop("DATABASE_URL", None)
            service.initialize()
            first = json.loads(PRIOR.read_bytes())
            second = json.loads(CURRENT.read_bytes())
            owner = "local-designer"
            project = service.create(owner)["project"]
            with service.transaction() as q:
                service.apply(q, owner, project, 0, first["home"])
                service.apply(q, owner, project, 1, second["home"])
            listener.bind(("127.0.0.1", 0))
            host, port = listener.getsockname()
            server = uvicorn.Server(
                uvicorn.Config("archimind.town.api:app", access_log=False)
            )
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]})
            thread.start()
            try:
                errors = browser_check(
                    f"http://{host}:{port}/?project={project}&revision=2",
                    output,
                    stale_started,
                    release_stale,
                    route_receipt,
                )
            finally:
                release_stale.set()
                server.should_exit = True
                thread.join(10)
            with service.transaction() as q:
                assert q("SELECT count(*) FROM jobs").fetchone()[0] == 0
                assert service.project(q, owner, project) == 2
    assert (
        calls
        == [
            ("route", COMPARE),
            ("route", MIXED),
            ("route", TIMEOUT),
            ("evidence", COMPARE),
            ("evidence", "Why will the chair fit?"),
            ("route", COMPARE),
            ("route", GENERAL_COMPARE),
        ]
        and not errors
    )
    (output / "browser-receipt.json").write_text(
        json.dumps(
            {
                "mode": "local Town with recorded Decisions responses",
                "viewport": [1440, 1000],
                "fixture_calls": len(calls),
                "external_calls": 0,
                "writes": 0,
                "page_errors": errors,
                "checks": [
                    "independent promotion",
                    "timeout",
                    "direct answer without model",
                    "mixed request uses configured review",
                    "simulated advisory comparison and explicit unsupported comparison",
                    "evidence on revision 2",
                    "discard delayed result on input edit",
                    "walkthrough without Decisions call",
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
