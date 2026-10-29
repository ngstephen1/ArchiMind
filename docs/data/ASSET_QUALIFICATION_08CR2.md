# Charles product requalification — 08C-R2

**Final result: Charles is render-qualified at native scale 1.0, in the isolated experimental V3 scene only.** The original technical checkpoint below is preserved. Its pending state was resolved by the separately sealed visual review and render release described in the completion record.

Technical checkpoint, 2026-10-29 UTC (October 28 in New York): automated pass, visual approval pending at that checkpoint. No model was committed before the review.

The paired [machine receipt](ASSET_QUALIFICATION_08CR2.json) records the current HTTPS retrieval, received-byte SHA-256, complete recomputed offline inspection and revalidated Policy B envelope. Acquisition used the official individual object only, capped at 15 MiB with system CA verification and redirects rejected; no preview, external texture, bookcase or dataset archive was acquired. Quarantine remains outside Git.

## Identity, rights and dimensions

Charles, Sod, ASIN/model B075X2X4XS, remains bound to `abo-b075x2x4xs-amazon-com`, catalog/record 1.0.0 and the existing 08A product evidence. The [official object](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/original/S/B075X2X4XS.glb) is **4,252,440 bytes**, SHA-256 **62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645**. ETag is retained separately and is not treated as SHA-256.

The freshly read [ABO model README](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) and [CC BY 4.0 license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt) support public browser redistribution subject to attribution, license linking, retained notices and modification disclosure. Include dataset/contributor credit and no endorsement claim. This does not independently clear trademarks, individual mesh authorship or certify physical product fidelity. Historical source qualification remains in [08A](FURNITURE_SOURCE_REGISTER.md).

| W × D × H (m) | Values | Meaning |
| --- | --- | --- |
| Published | 0.9906 × 0.9906 × 0.9652 | Published item claims, unchanged; not measured by ArchiMind |
| Current native mesh | 0.996104896068573 × 1.0019413232803345 × 0.976093053817749 | Current decoded positions and static transforms |
| Planning envelope | 0.996104896068573 × 1.0019413232803345 × 0.9760930538177491 | Exact approved outward envelope, not corrected product dimensions |

Native +Y up/+Z front convention, identity orientation and scale **1.0**, normalized translation `(0, 0, 0.00010657310485839844)`. Floor/center anchoring and all eight AABB corners are revalidated by the exact-rational R1 contract with no inward epsilon. Placement for canonical furniture `(x,y)` is Three `(x+W/2, 0, -(y+D/2))` after normalization. Renderer integration must never use illustrative fitting.

## Recomputed technical gates

One mesh/primitive/material, **42,706 triangles**, three embedded **2048 × 2048** images and **67,108,860 bytes** estimated unique decoded RGBA including mipmaps. No extensions, animation, deformation or external resources. Per-asset resource gates pass. Two instances require 85,412 furniture triangles, 4,252,440 unique encoded bytes and 67,108,860 unique texture bytes, below unchanged scene budgets.

The original offline inspection still rejects containment in the published physical box. That historical gate is retained; Policy B independently proves containment in its approved planning box. The new helper compares the complete freshly recomputed receipt digest with reviewed evidence, not just caller-supplied bounds. Missing/currently corrupt files and mismatched receipts fail with sanitized errors.

## Pending gates and verification

Image pixel decoding, recognizable front/back, source materials, floor contact, browser compatibility, interaction, fallback and cleanup require the private native-scale inspection harness. No render approval follows from this technical checkpoint. No device-performance or manufacturer-metrology claim is made.

Focused tests cover current-inspection handoff, altered hashes/counters/unchecked integrity, unsupported IDs and missing files, alongside the existing inspection and exact-envelope tests. Full CI is required before the next checkpoint. Original catalog, planning JSON, canonical models, geometry, A/B and legacy renderer are unchanged.

## Completion record — qualified native-scale release

Charles is now approved by `src/archimind/assets/product_render_release.json`, render version **1.0.0**, bound to the original catalog record, exact B envelope and separately sealed `charles_visual_review.json`. This does not change historical catalog/planning flags or the old physical-box rejection. The [product guide](../developer/CHARLES_PRODUCT_RENDERING.md) explains the complete authority chain and local testing commands.

The isolated **Charles product (08C-R2)** choice uses V3 ID/version/envelope bindings, two native-scale Charles meshes and one desk placeholder. It never changes A/B generation, selection, reports, scores or Plotly inputs. The original V1/V2 Sheen routes remain supported. The approved model is packaged once, unchanged, with official provenance, required credit, full CC BY 4.0 text and source notices. The upstream README copy has whitespace normalized only; source and packaged hashes are recorded. No extra model, texture, image or archive was acquired.

### Browser results and limitations

Actual desktop Chromium **1440 × 1000** and resized narrow Chromium **390 × 844** were inspected first through an external private inspection build, then through the actual Streamlit local component route. Both Charles instances show the source brown leather-like upholstery, rolled arms, cushions and turned legs. Front seating faces canonical south; rear upholstery was observed through orbit. Source metadata, exact same-ASIN model bytes and appearance agree; no independent product photo, physical measurement or calibrated color/material certification was performed.

Native scale is 1 for both instances. Ground contact is Y=0; actual world bounds enclose the expected envelope with only sub-ULP floating-point placement differences. Room/door/window geometry, framing, orbit/zoom/reset and cutaway controls work. At narrow width the actual component is 347 px wide with no page overflow; detail benefits from zoom and labels require scrolling. This is not physical-phone testing or a performance guarantee.

Two instances share one source geometry and load. Source asset/setup observations were 2.66 s on the initial private load, approximately 0.24–0.40 s on later cached/remounted scenes, and 0.345 s on the final Streamlit product mount. These include initialization and are not isolated network/decode timings or sustained frame-rate measurements. Actual image decoding and materials passed. Missing and hash-corrupt fixtures show two labeled chair placeholders plus the intentional desk placeholder; normal remount recovers. A deliberate eight-chair resource fixture reports 341,648 product triangles, eight budget placeholders and zero GLB loads.

Cleanup/remount, pending cancellation and shared ownership are covered by browser observations and focused unit tests. An early repeated-cleanup WebGL context warning was corrected with an idempotent cleanup guard; the fresh private review had zero errors/warnings. The final Streamlit review had zero console errors and one existing Plotly canvas-readback advisory. An early rapid cold rerun hit a pandas partial-import error; it did not recur after clean restart and completed sequential reruns. No unrelated import workaround was introduced. Sustained memory/leak, physical-device and cross-browser testing remain unverified.

Screenshots are outside Git under `/Users/macbook/Hack/`: `08cr2-qualified-desktop.png`, `08cr2-qualified-narrow.png`, `08cr2-private-front-detail.png`, `08cr2-private-orbit.png`, `08cr2-private-fallback.png`, `08cr2-final-streamlit-desktop.png`, `08cr2-final-streamlit-narrow.png`. The sealed review and paired JSON record filenames/hashes. Earlier private images retain inspection-pending text; final Streamlit images show the released route.

### Verification and delivery

- Final full Python suite: **1,507 passed in 86.21s**, zero failures/skips; all 1,477 baseline cases retained. Integration checkpoint also passed **1,507 in 88.78s**. The earlier development run reported one expected obsolete one-GLB inventory assertion; the test now requires exactly the two authorized assets and keeps all old provenance/hash checks.
- Frontend: **68 passed, 0 failed, 0 skipped**, including all 27 old cases. Syntax and production build pass. Rebuild equals the committed checkpoint-2 bundle; derived registry passes `--check`.
- Ruff lint and formatting pass; **129 files already formatted**. `pip check`: **No broken requirements found**. Streamlit health: **HTTP 200 ok**.
- Offline source/wheel build, exact member comparison, one Charles copy, preserved Sheen resources, `--no-deps --no-index` target installation and outside-repository asset integrity/V3 loading pass. Separate focused packaging run: **1 passed in 5.60s**; the expanded packaging check is also in the final full suite. Catalog imports remain SDK-free. The pre-existing render package imports styling SDK types; the installed-render test blocks provider construction, network and external processes.
- Fixed source/model hash reverified. No live AI, Codex subprocess, new dependency or further acquisition was used. Canonical models, validators, generator, AI, UI layout-selection modules, Plotly, catalog and planning snapshots remain byte-identical; 39 selected protected source files were explicitly hash-checked. `.agents/` and `.claude/` remain untracked and untouched.

Checkpoint 1: [`01dcd77`](https://github.com/ngstephen1/ArchiMind/commit/01dcd77c0338e75ad876384568d7701480d2d053), [CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40794073487), 1,484 Python / 27 frontend tests. Checkpoint 2: [`93b2b9f`](https://github.com/ngstephen1/ArchiMind/commit/93b2b9f51159ebc57b11a9452b2c15da74718f3a), [integration CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40795254059). The final response records final checkpoint/CI identity after it exists; a document cannot contain its own future commit hash without changing that hash.

### Remaining scope

08D can now be separately scoped around this single approved asset, with explicit compatible B-sized specifications and procedural fallbacks. Existing A/B furniture must never be silently resized or rebound. Bed, desk and wardrobe have no approved models; the bookcase remains deferred due to 4096 px textures. No selected-layout integration, retrieval, embeddings, new AI, dataset pipeline or later-task implementation is included.

### Exact changed-file inventory

- `MANIFEST.in`
- `README.md`
- `app.py`
- `docs/data/ASSET_QUALIFICATION_08CR2.json`
- `docs/data/ASSET_QUALIFICATION_08CR2.md`
- `docs/developer/CHARLES_PRODUCT_RENDERING.md`
- `docs/developer/PLANNING_ENVELOPES.md`
- `docs/developer/REALISTIC_ROOM.md`
- `docs/developer/STATUS.md`
- `frontend/realistic_viewer/package.json`
- `frontend/realistic_viewer/src/asset_pool.js`
- `frontend/realistic_viewer/src/main.js`
- `frontend/realistic_viewer/src/product_assets.js`
- `frontend/realistic_viewer/src/product_registry.js`
- `frontend/realistic_viewer/src/room_geometry.js`
- `frontend/realistic_viewer/src/room_viewer.js`
- `frontend/realistic_viewer/tests/product.test.js`
- `scripts/build_product_registry.py`
- `src/archimind/_viewer_assets/furniture/ABO_ATTRIBUTION.txt`
- `src/archimind/_viewer_assets/furniture/ABO_LICENSE_CC_BY_4.0.txt`
- `src/archimind/_viewer_assets/furniture/ABO_SOURCE_README.md`
- `src/archimind/_viewer_assets/furniture/CHARLES_PROVENANCE.json`
- `src/archimind/_viewer_assets/furniture/CharlesArmchair.glb`
- `src/archimind/_viewer_assets/viewer.js`
- `src/archimind/assets/charles_visual_review.json`
- `src/archimind/assets/product_render_release.json`
- `src/archimind/assets/render_assets.py`
- `src/archimind/assets/render_qualification.py`
- `src/archimind/examples/sample_product_room.py`
- `src/archimind/render/product_scene.py`
- `tests/test_asset_catalog_packaging.py`
- `tests/test_product_qualification.py`
- `tests/test_product_rendering.py`
- `tests/test_realistic_viewer.py`
