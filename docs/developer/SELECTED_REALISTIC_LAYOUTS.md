# Selected A/B layouts in Three.js — Task 08D

The selected candidate now drives the 2D floor plan and the chosen 3D backend. Under **Selected 3D Furnished Room**, choose **Plotly schematic** (default) or **Realistic Three.js**. The 2D plan stays visible. The current generated bedroom uses three labeled procedural placeholders: no bed, desk or wardrobe product is qualified, and matching a category or size never identifies a product.

Charles/Sod remains the only approved real-product mesh. Its separate, explicitly loaded demonstration uses fresh Policy B factory specifications, retained planning sidecars and a real passing deterministic spatial report. It does not replace the generated alternatives or imply architectural certification. The original Sheen architectural room and single-chair demonstration remain available.

## Adapter and authority

`assets/selection.py` exports `build_render_bindings(design, *, planning_bindings=None, overrides=None) -> RenderBindingResolution`. The result contains immutable, furniture-ID-sorted V3 `ProductBinding` records and `BindingDiagnostic` records. Diagnostics distinguish `approved_product` from `placeholder` and carry a fixed reason code. Approved diagnostics retain the immutable original planning evidence, including catalog/product/model/envelope identities, versions and hashes.

`render/selected_realistic.py` exports `build_selected_realistic_scene(...)` and `render_selected_realistic_scene(...)`, using the same optional evidence/override arguments. The former returns `PreparedRealisticScene(scene, resolution)`; the latter mounts through the existing product component and reports backend asset-integrity failures in its diagnostics. The render function also accepts a component key. The common `mount_product_payload()` validates the existing V3 contract and performs the existing local integrity check. Legacy wrappers reuse it without changing their public return behavior.

No product is inferred from a chair category, approximate dimensions or even an exact dimension match. Charles requires an explicit `PlanningFurnitureBinding`, revalidated against the actual furniture ID/name/category, exact B dimensions, zero yaw, current catalog/record and envelope, source-model hash and digest-bound render release. Overrides are backend-only: `None` explicitly requests a placeholder; a product override requires its matching sidecar. An invalid override for a known furniture item produces a placeholder, never a substitute. Unknown furniture references reject the request.

Missing/stale/malformed planning evidence, unavailable render approval and resource-budget failure produce fixed diagnostic reasons. Placeholder-only and empty scenes require no Charles metadata lookup or model file. Unsupported rotation and renderer size/count limits are explicit errors, never geometry coercion or truncated scenes. Actual binary corruption/missing files trigger the existing unavailable-asset fallback; browser failures show their own truthful loading status.

The adapter receives the actual stored `candidate.design`. Canonical IDs, values and furniture ordering remain unchanged; only binding records are sorted. Pydantic makes temporary model copies during schema validation. These are serialization envelopes, never a second canonical layout or session-state design. There is no generation, spatial validation, score calculation, AI invocation, asset acquisition or user-supplied URL/path in scene conversion.

## UI and session contracts

`render_layout_generator(specification, *, planning_bindings=None)` accepts optional explicit backend evidence. No product-selection or catalog-sized generation controls were added. The default application supplies no product sidecars, so normal alternatives honestly remain placeholders.

On successful generation, `ui/realistic_view.py` captures only immutable planning bindings, the submitted specification digest, a digest of the stored generation and a session-local revision. Every successful replacement advances the revision, including identical-seed regeneration; failed generation preserves the previous result, selection, revision and evidence. Pending input/evidence changes cannot rebind the displayed generation. Rendering checks the stored revision/digest and revalidates each sidecar against the selected candidate. Invalid evidence fails closed; rendering never repairs the candidate, report or score.

The view selector is independent of the A/B selector. Its preference survives ordinary reruns, A/B switches, successful generation and empty results. Only the active 3D backend is invoked. Empty results remove the viewer. Unexpected render failures show a fixed sanitized error and retain the selected layout, allowing a switch to Plotly. Nonzero rotation is rejected explicitly before drawing an inaccurate view.

Styling results, consent and stale-result safeguards retain their original semantics. View changes do not invalidate a matching style result; A/B changes do. Stored flat-color previews apply to Plotly. Three.js retains source asset materials and procedural placeholder appearances; it does not apply the stylist plan.

The standalone fixture caches only validation-report JSON and its fingerprint in that browser session. The fingerprint includes canonical fixture geometry, planning-binding digests, accessibility configuration and current render release. First explicit load runs real accessibility validation at zero overlap tolerance. Ordinary reruns and selected-layout changes reuse the report. Changed evidence/geometry invalidates it. Failed reports remain failures and suppress approved fixture rendering. No mutable fixture design is cached or shared between sessions.

## Lifecycle and camera

The component entrypoint uses `scene_lifecycle.js` to manage one mount per host. Identical scene signatures reuse the scene and cleanup handle. Changed input captures the view, disposes the old scene, then mounts the replacement. Old cleanup callbacks cannot dispose newer entries. Final unmount cleans up once; late asynchronous asset work cannot attach to a replaced scene.

Within one generation, A/B uses the same component key. If the room payload is unchanged, camera position, orbit target and cutaway/footprint controls carry across. **Reset camera** fits the current scene. A changed room, successful new generation or reopening Three.js starts with deterministic framing. Camera state stays client-side and never changes canonical coordinates.

The existing shared asset pool, cancellation and ownership rules remain authoritative. No second renderer or decoder was introduced. Same-product A/B replacements can reuse the pool during its existing grace period. Ordinary reruns retain the mounted scene and avoid duplicate loads. Failed client loads do not auto-retry on unrelated reruns: switch away and reopen the view after restoring the asset.

V1/V2/V3 wire contracts remain unchanged. V3 wording is now binding-aware instead of claiming every scene is the standalone Charles demo. Product meshes still use exactly unit scale, the original anchor/axis mapping and all resource limits documented in [the Charles guide](CHARLES_PRODUCT_RENDERING.md). Only the illustrative Sheen path fits a mesh.

## Verification

Integration checkpoint: **1,547 Python tests passed in 99.46s** and **75 frontend tests passed**. Final release verification, browser evidence, exact changed files and CI identities are recorded below when complete. The baseline was 1,507 Python / 68 frontend tests. The only historical assertion changed is the application's displayed development-phase value; other existing tests remain intact.

### Local commands

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
python scripts/check_health.py
python scripts/build_product_registry.py --check
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run build
git diff --exit-code -- src/archimind/_viewer_assets
python -m pytest -q tests/test_asset_catalog_packaging.py
python -m streamlit run app.py
```

Unit tests block external networking/providers/process work using local fixtures and mocks. Controlled local browser requests and offline packaging subprocesses are separate verification activities. The installed-wheel regression resolves the adapter and asset from the installed package outside the repository, preserves the legacy/catalog checks and verifies explicit-product versus unbound-placeholder conversion.

## Remaining boundaries

Normal generated layouts contain no compatible explicit Charles specification. Bed, desk and wardrobe remain placeholders; the bookcase remains deferred for its 4096 px textures. Model fidelity, physical-device performance and architectural usefulness are separate from this synchronization result. There is no material editing, furniture dragging, rotation support, new asset, dependency, AI behavior, embeddings or dataset ingestion.

08E can be scoped next around explicit catalog-sized specifications and compatible user choices. It must associate evidence before generation, show dimension changes for review, and never resize active candidates. Future retrieval must resolve only to qualified, versioned catalog records; retrieval cannot grant rights, correct dimensions or approve a render binding.

## Final verification and browser evidence

Local release suite: **1,556 passed in 94.81s**, zero failures/skips, preserving all
1,507 baseline tests. Frontend: **75 passed**, zero failures/skips. Ruff lint and
format passed (**137 files already formatted**); dependencies and Streamlit health
passed (HTTP 200). Product registry and committed-bundle checks passed after a
production rebuild. Offline source/wheel builds, exact packaged bytes, installed
asset integrity and selected-adapter checks passed from an isolated target outside
the repository; the separate packaging run passed in **5.00s**. Unit test suites
made no model acquisition, live AI/Codex calls or external network requests.

Actual browser inspection used Chromium desktop **1440×1000** and resized narrow
**390×844**. Layout A and B furniture IDs, X/Y extents and heights agreed between
selected Plotly 2D/3D traces and the Three.js canonical metrics. Normal layouts
had zero product loads and three labeled placeholders. Seed 42 retained its nine
search attempts and original scores (A **67.721925**, B **67.614973**) through view
switching. Pending seed 43 changed neither the mounted DOM node nor camera.
A/B replacement preserved camera and cutaway, leaving one canvas. Explicit same-seed regeneration disconnected the old scene with cleanup complete, reset selection to A, retained the Three.js preference and restored initial framing. A separate real
browser context started empty, then independently defaulted to A/Plotly while
the original remained B/Three.js.

Normal selected-scene setup observations ranged **0.105–0.185 s**. The validated
Charles fixture loaded two source-textured meshes at scale **1.0**, floor Y=0,
one shared geometry and one GLB load, with a **0.655 s** observed setup. Orbit,
zoom, reset and cutaway worked; Reset restored the initial pose. The narrow
component was **347 px**, with no horizontal overflow. Labels wrap; small-screen
detail benefits from zoom. Physical-phone and sustained performance were not tested.

Fault injection intercepted only the local Charles response. HTTP 404 and a
same-size hash-corrupt HTTP 200 both produced two unavailable chair placeholders
plus the intentional desk placeholder, retaining room/opening geometry. Setup was
approximately **0.122/0.182 s**. Removing interception and reopening recovered both
meshes in **0.351 s**, with one canvas and no stale scene. Normal inspection had
zero unexpected console errors and the existing Plotly canvas-readback advisory;
the intentional missing-asset test added one expected network 404. No unexpected
WebGL cleanup errors were observed. Exact GPU-memory reclamation and sustained
leak/frame-rate behavior were not measured; ownership/cancellation/disposal are
also covered by deterministic tests.

During active development, changing imported source while retaining a session
caused one stale Pydantic-class error. Final inspection restarted the server with
fixed source and file watching disabled. No canonical model, serializer or
geometry workaround was added; ordinary reruns passed. Refresh/restart after
source deployment remains distinct from durable project persistence.

Screenshots are outside Git under `/Users/macbook/Hack/`:
`08d-a-desktop.png`, `08d-b-desktop.png`, `08d-a-narrow.png`, `08d-b-narrow.png`,
`08d-charles-desktop.png`, `08d-charles-narrow.png`, `08d-missing-narrow.png`,
`08d-corrupt-narrow.png`, `08d-recovered-narrow.png`. Their SHA-256 values and
browser comparison data are in the [verification receipt](../data/SELECTED_LAYOUT_08D_VERIFICATION.json).

Original canonical models, geometry/generation/scoring, Plotly renderers, AI
workflow/styling, catalog, Policy B snapshots, qualified model/release and native
product placement remain unchanged. No dependency or asset was added. The
verification receipt records the protected-file comparison. `.agents/` and
`.claude/` remain untracked and untouched.

Checkpoint 1: [`bd0d77c`](https://github.com/ngstephen1/ArchiMind/commit/bd0d77c9c39c626e1545b1d111000f6dd1b7a8ef),
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40798514148).
Checkpoint 2: [`ef28ecc`](https://github.com/ngstephen1/ArchiMind/commit/ef28ecc0dd9e2af59b37b35cd517fad37607df28),
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40799119566).
The final response supplies the release checkpoint and its actual CI result once
they exist; the guide cannot contain its own future commit hash.

### Exact changed files

- `MANIFEST.in`
- `README.md`
- `app.py`
- `docs/data/SELECTED_LAYOUT_08D_VERIFICATION.json`
- `docs/developer/CHARLES_PRODUCT_RENDERING.md`
- `docs/developer/REALISTIC_ROOM.md`
- `docs/developer/SELECTED_REALISTIC_LAYOUTS.md`
- `docs/developer/STATUS.md`
- `frontend/realistic_viewer/package.json`
- `frontend/realistic_viewer/src/main.js`
- `frontend/realistic_viewer/src/room_viewer.js`
- `frontend/realistic_viewer/src/scene_lifecycle.js`
- `frontend/realistic_viewer/tests/lifecycle.test.js`
- `src/archimind/_viewer_assets/viewer.js`
- `src/archimind/assets/selection.py`
- `src/archimind/examples/sample_product_room.py`
- `src/archimind/render/product_scene.py`
- `src/archimind/render/selected_realistic.py`
- `src/archimind/ui/layout_generation.py`
- `src/archimind/ui/product_fixture.py`
- `src/archimind/ui/realistic_view.py`
- `tests/test_asset_catalog_packaging.py`
- `tests/test_product_fixture.py`
- `tests/test_selected_realistic.py`
- `tests/test_selected_realistic_ui.py`
- `tests/test_smoke.py`
