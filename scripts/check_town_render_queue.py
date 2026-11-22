"""Accept Town proof jobs through the ordinary UI and an unmodified Blender binary."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from archimind.town import service
from archimind.town.design import digest, validate_home

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/data/live-quality-proof"
OWNER = "local-designer"
BLENDER_PHASE = "Rendering the Cycles proof"


def seed():
    snapshots = [
        json.loads((FIXTURES / f"live-snapshot-r{revision}.json").read_bytes())
        for revision in (1, 2)
    ]
    project = snapshots[0]["project"]
    service.initialize()
    with service.transaction() as q:
        q("INSERT INTO projects VALUES(?,?,0)", (project, OWNER))
        for expected, snapshot in enumerate(snapshots, 1):
            home = snapshot["home"]
            assert snapshot["project"] == project and snapshot["revision"] == expected
            assert digest({k: v for k, v in home.items() if k != "id"}) == home["id"]
            validate_home(home)
            service.apply(q, OWNER, project, expected - 1, home)
    return project, snapshots


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def check(url, output):
    output.mkdir(parents=True, exist_ok=True)
    project, snapshots = seed()
    cache = Path(os.environ["TOWN_DB"]).parent / "town-renders"
    endpoint = f"{url}/api/projects/{project}/render"
    errors = []
    observations = []
    proofs = {}
    started = time.monotonic()

    def observe(state, **fields):
        observations.append(
            dict(seconds=round(time.monotonic() - started, 3), state=state, **fields)
        )
        write_json(output / "events.json", observations)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome", args=["--enable-unsafe-swiftshader"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))

        def state(revision):
            response = page.request.get(f"{endpoint}?revision={revision}")
            assert response.ok, response.status
            return response.json()

        def open_board(revision):
            page.goto(f"{url}/?project={project}&revision={revision}")
            expect(page.locator("#revision")).to_have_text(
                re.compile(f"Revision {revision}$"), timeout=30000
            )
            page.locator("#present").click()
            expect(page.locator("#boardSource")).to_contain_text(
                f"Saved revision {revision}"
            )

        def queue(revision):
            proof = page.locator("#renderProof")
            expect(proof).to_be_enabled()
            with page.expect_response(
                lambda r: (
                    r.request.method == "POST"
                    and r.url == f"{endpoint}?revision={revision}"
                )
            ) as result:
                proof.click()
            response = result.value
            assert response.ok
            admitted = response.json()
            assert admitted["state"] == "queued", admitted
            observe(admitted["state"], revision=revision, phase=admitted["phase"])

        def wait_capture(revision, expected, *, phase=None, timeout=1800):
            deadline = time.monotonic() + timeout
            previous = None
            while time.monotonic() < deadline:
                proof = state(revision)["proof"]
                current = (proof["state"], proof.get("phase"))
                if current != previous:
                    observe(current[0], revision=revision, phase=current[1])
                    previous = current
                if current[0] == expected and (phase is None or current[1] == phase):
                    return proof
                if expected == "running":
                    assert current[0] != "ready", "Blender completed before overlap"
                assert current[0] != "failed", proof
                time.sleep(2)
            raise TimeoutError(f"Revision {revision} did not reach {expected}")

        # A real filesystem obstruction makes the actual worker fail before export.
        # Only the isolated runner cache is touched.
        cache.touch(exist_ok=False)
        open_board(1)
        queue(1)
        expect(page.locator("#renderStatus")).to_contain_text("Render failed")
        expect(page.locator("#renderProof")).to_be_enabled()
        assert state(1)["proof"]["state"] == "failed"
        page.locator("#renderPanel").screenshot(path=output / "retry-visible.png")
        observe("failed", revision=1, obstacle="isolated cache path was a file")
        cache.unlink()
        queue(1)
        wait_capture(1, "running", phase=BLENDER_PHASE, timeout=150)
        page.get_by_role("button", name="Close presentation").click()
        page.locator("#tour").click()
        page.locator("#door").click()
        page.locator("#roomJump").select_option("bedroom")
        expect(page.locator("#roomJump")).to_have_value("bedroom")
        assert state(1)["proof"] == {"state": "running", "phase": BLENDER_PHASE}
        page.screenshot(path=output / "walk-during-proof.png")
        assert state(1)["proof"] == {"state": "running", "phase": BLENDER_PHASE}
        observe("walkthrough-during-render", revision=1, phase=BLENDER_PHASE)
        page.locator("#present").click()
        expect(page.locator("#boardSource")).to_contain_text("Saved revision 1")

        for revision in (1, 2):
            if revision == 2:
                open_board(2)
                assert state(2)["proof"]["state"] == "idle"
                assert state(1)["proof"] == proofs["1"]
                assert (
                    page.request.get(
                        f"{endpoint}/proof/manifest.json?revision=2"
                    ).status
                    == 404
                )
                observe("revision-isolated-before-render", revision=2, stage="proof")
                queue(2)
            proof = wait_capture(revision, "ready")
            proofs[str(revision)] = proof
            expect(page.locator("#renderDownloads")).to_contain_text(
                "Proof · bedroom-doorway.png", timeout=25000
            )
            observe("ready-links-without-reload", revision=revision)
            expect(page.locator("#renderProof")).to_be_disabled()
            page.locator("#renderPanel").screenshot(
                path=output / f"proof-ready-r{revision}.png"
            )
            for name, expected_sha in proof["files"].items():
                response = page.request.get(
                    f"{endpoint}/proof/{name}?revision={revision}"
                )
                assert response.ok, (revision, name, response.status)
                assert hashlib.sha256(response.body()).hexdigest() == expected_sha
                if name in {"manifest.json", "receipt.json"}:
                    (output / f"r{revision}-{name}").write_bytes(response.body())
            manifest = json.loads((output / f"r{revision}-manifest.json").read_bytes())
            receipt = json.loads((output / f"r{revision}-receipt.json").read_bytes())
            assert manifest["revision"] == revision and manifest["project"] == project
            assert manifest["home_id"] == snapshots[revision - 1]["home"]["id"]
            assert receipt["manifest_sha256"] == proof["files"]["manifest.json"]
            assert receipt["files"]["home.blend"] == proof["files"]["home.blend"]
            if revision == 2:
                assert (output / "r2-manifest.json").read_bytes() == (
                    FIXTURES / "live-manifest-r2.json"
                ).read_bytes()
            cache_logs = {p: p.read_bytes() for p in cache.glob("*/proof.log")}
            reused = page.request.post(
                f"{endpoint}?revision={revision}", data={"stage": "proof"}
            )
            assert reused.ok and reused.json() == proof
            assert cache_logs == {p: p.read_bytes() for p in cache.glob("*/proof.log")}
            assert len(cache_logs) == revision
            assert all(b"Blender 5.1.2" in log for log in cache_logs.values())
            observe("cache-reused", revision=revision, files=proof["files"])
        assert (
            proofs["1"]["files"]["manifest.json"]
            != proofs["2"]["files"]["manifest.json"]
        )
        assert state(1)["proof"] == proofs["1"]
        assert not errors, errors
        browser.close()

    write_json(
        output / "verification.json",
        dict(
            tested_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            project=project,
            proofs=proofs,
            browser_errors=errors,
            provider_calls=0,
            renderer=str(Path(shutil.which(os.environ["TOWN_BLENDER_BIN"])).name),
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8790")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.url, args.output)
