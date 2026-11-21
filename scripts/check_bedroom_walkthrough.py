"""Exercise the real local Town UI and save its composed bedroom views."""

import argparse
import base64
import json
import statistics
from pathlib import Path

from playwright.sync_api import sync_playwright


def check(url: str, output: Path):
    output.mkdir(exist_ok=True, parents=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            args=["--enable-unsafe-swiftshader", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(60000)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        first_load = page.evaluate(
            "performance.getEntriesByType('navigation')[0].loadEventEnd"
        )
        page.locator("#design").click()
        page.locator("#generate").click()
        page.locator("#apply").click()
        page.get_by_text("Applied revision 1.", exact=True).wait_for(state="attached")

        page.locator("#design").click()
        page.locator("#chairStudio summary").click()
        page.locator("#chairPullout").click()
        page.wait_for_function(
            "document.querySelector('#world').dataset.chair === 'procedural' && "
            "!document.querySelector('#panel').open"
        )
        page.locator("#design").click()
        page.locator("#chairDiscard").click()
        assert "Revision 1" in page.locator("#revision").text_content()
        page.locator("#chairChoice").select_option("1")
        page.locator("#chairPreview").click()
        page.wait_for_function(
            "document.querySelector('#world').dataset.chair === 'verified' && "
            "!document.querySelector('#panel').open"
        )
        page.wait_for_function(
            "document.querySelector('#world').dataset.desk === 'verified'"
        )
        frames = page.evaluate(
            """async () => {
                const frames=[];
                let last=await new Promise(requestAnimationFrame);
                for(let i=0;i<20;i++){
                    const now=await new Promise(requestAnimationFrame);
                    frames.push(now-last);last=now;
                }
                return frames;
            }"""
        )
        page.screenshot(path=output / "walkthrough.png")
        canvas = page.locator("#world")
        # This fixed canvas needs no scroll or element-stability wait.
        clip = canvas.bounding_box()
        assert clip and clip["width"] > 0 and clip["height"] > 0
        initial = page.screenshot(clip=clip)
        for view in ("doorway", "desk", "bedside"):
            page.locator("#photoView").select_option(view)
            assert canvas.get_attribute("data-camera") == view
            assert page.locator("#photoReason").text_content() == ""
        page.locator("#photoView").select_option("")
        assert canvas.evaluate("element => element === document.activeElement")
        assert initial == page.screenshot(clip=clip), "Walking view was not restored"

        # A rejected replacement leaves both the selected camera and accepted preview usable.
        page.locator("#photoView").select_option("desk")
        page.locator("#design").click()
        rejected_route = "**/chair-pullout/preview"
        page.route(
            rejected_route,
            lambda route: route.fulfill(
                status=400, json={"error": "The chair move is obstructed."}
            ),
        )
        page.locator("#chairPullout").click()
        page.get_by_text("The chair move is obstructed.", exact=True).wait_for()
        assert canvas.get_attribute("data-camera") == "desk"
        assert page.locator("#chairApply").is_visible()
        page.unroute(rejected_route)
        page.locator("#chairApply").click()
        page.get_by_text(
            "Designer furniture saved in revision 2.", exact=True
        ).wait_for()
        for option, new_revision in [("2", 3), ("3", 4)]:
            page.locator("#chairStudio summary").click()
            page.locator("#chairChoice").select_option(option)
            page.locator("#chairPreview").click()
            page.wait_for_function(
                "document.querySelector('#world').dataset.collection === 'verified' && !document.querySelector('#panel').open"
            )
            page.locator("#design").click()
            page.locator("#chairApply").click()
            page.get_by_text(
                f"Designer furniture saved in revision {new_revision}.", exact=True
            ).wait_for()
        page.locator('#panel [aria-label="Close studio"]').click()
        page.locator("#present").click()
        page.wait_for_function("document.querySelectorAll('#photos img').length === 3")
        assert "revision 4" in page.locator("#boardSource").inner_text()
        for image, name, label in zip(
            page.locator("#photos img").all(),
            ("doorway", "desk", "bedside"),
            ("Doorway", "Desk and chair", "Bedside"),
            strict=True,
        ):
            assert image.get_attribute("alt") == label
            data = image.get_attribute("src").split(",", 1)[1]
            (output / f"{name}.jpg").write_bytes(base64.b64decode(data))
        page.keyboard.press("Escape")
        page.set_viewport_size({"width": 390, "height": 844})
        page.reload()
        page.wait_for_function(
            "document.querySelector('#world').dataset.chair === 'verified'"
        )
        page.locator("#tour").click()
        page.locator("#door").click()
        page.locator("#photoView").select_option("desk")
        assert page.locator("#photoReason").text_content() == ""
        page.screenshot(path=output / "narrow.png")
        page.route(
            "**/assets/designer-*.glb",
            lambda route: route.fulfill(
                status=200, body=b"corrupt", content_type="model/gltf-binary"
            ),
        )
        page.reload()
        page.locator("#present").click()
        page.wait_for_function("document.querySelectorAll('#photos img').length === 3")
        page.get_by_text(
            "Designer chair unavailable in these views.", exact=False
        ).wait_for()
        page.get_by_text(
            "Bedroom collection mesh unavailable.", exact=False
        ).last.wait_for()
        assert not errors, errors
        (output / "check.json").write_text(
            json.dumps(
                {
                    "applied_revision": 4,
                    "seed": 42,
                    "raf_ms_median": statistics.median(frames),
                    "initial_navigation_load_ms": first_load,
                    "page_errors": errors,
                },
                indent=2,
            )
        )
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8790")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.url, args.output)
