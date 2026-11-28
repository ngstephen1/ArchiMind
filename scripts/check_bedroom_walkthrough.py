"""Exercise the real local Town UI and save its composed bedroom views."""

import argparse
import base64
import json
import statistics
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


def check_room_study_reopen(page):
    """A charged study and a furniture correction survive reopening the same room."""
    page.locator("#houseLabels").get_by_role("button", name="Bedroom").click()
    page.locator("#restyleRoom").click()
    page.locator("#layoutSetup summary").click()
    page.locator("#layoutWidth").fill("1.7")
    page.locator("#layoutDepth").fill("2.1")
    # The bed fits only after a quarter turn from the provider's estimated pose.
    result = {
        "width": 1.7,
        "depth": 2.1,
        "photo_sha256": ["a" * 64],
        "uncertainty": "Recorded browser fixture.",
        "furniture": [
            {
                "kind": "bed",
                "label": "Bed",
                "photo": 1,
                "quarter_turns": 1,
                "center_x_fraction": 0.5,
                "center_depth_fraction": 0.5,
            }
        ],
    }
    route = "**/api/photo-layout"
    page.route(route, lambda request: request.fulfill(json=result))
    try:
        page.locator("#buildLayout").click()
        page.locator("#layoutStudio canvas").wait_for()
        assert page.locator("#layoutPiece option").count() == 1
        assert "Turned 1" in page.locator("#layoutNotice").inner_text()
        assert page.locator("#rotatePiece").inner_text() == "Turn 180°"
        page.locator("#rotatePiece").click()
        page.locator("#layoutX").fill("0.80")
        page.locator("#layoutX").press("Tab")
        page.locator("#layoutStudio button[aria-label]").click()
        page.locator("#conceptStudio button[aria-label]").first.click()
        page.locator("#restyleRoom").click()
        assert page.locator("#buildLayout").inner_text() == "Reopen layout study"
        page.locator("#buildLayout").click()
        page.locator("#layoutStudio canvas").wait_for()
        assert page.locator("#layoutX").input_value() == "0.80"
        with page.expect_download() as download:
            page.locator("#saveStudy").click()
        glb = Path(download.value.path()).read_bytes()
        scene = json.loads(glb[20 : 20 + int.from_bytes(glb[12:16], "little")])
        bed = next(
            node
            for node in scene["nodes"]
            if node.get("extras", {}).get("kind") == "bed"
        )
        # The input orientation was 90°. Auto-fitting and flipping yield 360°.
        assert abs(bed["matrix"][0] - 1) < 1e-6
        assert abs(bed["matrix"][12] - 0.80) < 1e-6
        page.locator("#layoutStudio button[aria-label]").click()
        page.locator("#conceptStudio button[aria-label]").first.click()
    finally:
        page.unroute(route)


def check_house_editor(page, url, output):
    """Select the reservation on the actual plan canvas and save a scoped move."""
    page.goto(url)
    page.locator("#selectChair").click()
    page.locator("#copyHouse").click()
    page.wait_for_function(
        "new URL(location.href).searchParams.get('revision') === '1'"
    )
    project = parse_qs(urlparse(page.url).query)["project"][0]
    endpoint = f"{url.rstrip('/')}/api/projects/{project}"
    home = page.request.get(endpoint).json()["home"]
    bedroom = next(p for p in home["rooms"] if p["design"]["room"]["id"] == "bedroom")
    chair = next(f for f in bedroom["design"]["furniture"] if f["id"] == "desk-chair")
    page.locator("#closeChairChat").click()
    page.get_by_role("button", name="Plan", exact=True).click()
    canvas = page.locator("#world").bounding_box()
    scale = min(canvas["width"] / home["width"], canvas["height"] / home["depth"]) / 1.2
    x = bedroom["origin"][0] + chair["x_m"] + chair["width_m"] / 2
    y = bedroom["origin"][1] + chair["y_m"] + chair["depth_m"] / 2
    page.mouse.click(
        canvas["x"] + canvas["width"] / 2 + (x - home["width"] / 2) * scale,
        canvas["y"] + canvas["height"] / 2 - (y - home["depth"] / 2) * scale,
    )
    message = page.locator("#chairMessage")
    message.fill("Move it")
    page.locator("#previewChat").click()
    page.get_by_text("Which direction and distance?", exact=False).wait_for()
    assert page.locator("#applyChat").is_hidden()
    message.fill("Pull this chair 30 cm away from the desk.")
    page.locator("#previewChat").click()
    page.locator("#applyChat").wait_for()
    assert page.request.get(endpoint).json()["revision"] == 1
    page.locator("#applyChat").click()
    page.wait_for_function(
        "new URL(location.href).searchParams.get('revision') === '2'"
    )
    page.reload()
    page.locator("#compareHouse").click()
    page.locator("#compareFrames").wait_for()
    assert page.locator("#compareLeft").get_attribute("src") != page.locator(
        "#compareRight"
    ).get_attribute("src")
    page.screenshot(path=output / "house-editor-comparison.png")
    page.locator("#houseCompare button").click()
    page.locator("#openPhotoStudio").click()
    page.wait_for_function("document.querySelector('#conceptAfter').naturalWidth > 0")
    page.locator("#conceptWipe").fill("35")
    page.locator("#exampleLayout").click()
    page.locator("#layoutStudio canvas").wait_for()
    assert page.locator("#layoutPiece option").count() == 2
    page.locator("#layoutX").fill("2.30")
    page.locator("#layoutX").press("Tab")
    with page.expect_download() as download:
        page.locator("#saveStudy").click()
    model = Path(download.value.path()).read_bytes()
    assert model[:4] == b"glTF"
    gltf = json.loads(model[20 : 20 + int.from_bytes(model[12:16], "little")])
    chair_node = next(
        node for node in gltf["nodes"] if node.get("extras", {}).get("kind") == "chair"
    )
    assert abs(chair_node["matrix"][12] - 2.30) < 0.001
    page.locator("#layoutStudio button[aria-label]").click()
    page.locator("#conceptStudio button[aria-label]").first.click()
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="3D house", exact=True).click()
    check_room_study_reopen(page)
    page.get_by_role("button", name="Walk", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#world').dataset.location === 'interior'"
    )


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
        revision_reads = []
        page.on(
            "request",
            lambda req: (
                revision_reads.append(req.url)
                if "/api/projects/" in req.url and "?revision=" in req.url
                else None
            ),
        )
        page.locator("#whyQuery").fill("Can I move the chair under the desk?")
        page.locator("#askWhy").click()
        assert "clear width between supports" in page.locator("#whyAnswer").inner_text()
        assert revision_reads == []
        page.locator("#whyQuery").fill("What changed when I moved the chair?")
        with page.expect_response(lambda r: r.url.endswith("?revision=3")) as response:
            page.locator("#askWhy").click()
        assert response.value.ok
        page.wait_for_function(
            "document.querySelector('#whyAnswer').textContent.includes('Displacement:')"
        )
        assert len(revision_reads) == 1
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
        editor_page = browser.new_page(viewport={"width": 1440, "height": 1000})
        editor_page.set_default_timeout(60000)
        check_house_editor(editor_page, url, output)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8790")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.url, args.output)
