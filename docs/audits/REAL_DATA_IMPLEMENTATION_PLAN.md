# Real-data implementation plan

**Status: proposed; no roadmap production code or new asset is implemented by this audit.**

Date: 2026-10-28. Basis: [readiness audit](REAL_DATA_READINESS_AUDIT.md), baseline `c240e85`; the readiness report was committed separately as `1303a86a09925e8840b0a02017e998b987ccc647`. Deployment target is a **noncommercial public demo with asset bytes delivered to browsers**. Strategy is **C: small curated catalog first, dataset-scale investigation later**.

## 1. Invariants and release gates

- Reuse canonical `RoomDesign`/furniture/room/opening models. No canonical field or geometry-rule changes in 08A–08E. Preserve existing consumers and zero-rotation limitations.
- Keep product dimensions, mesh bounds and validated footprints separate. Real product sizes enter a new specification **before explicit generation**. Rendering an existing candidate never changes dimensions, coordinates, IDs, reports or scores.
- Use catalog and per-furniture sidecar bindings. No user paths/URLs, runtime downloads, arbitrary model uploads or live AI dependency. Existing procedural views and clearly labeled standalone demonstrations remain available.
- Rights, dimension accuracy, rendering correctness and architectural usefulness are independent gates. Passing one cannot imply the others.
- Each task stops at its checkpoint. A failed prerequisite produces a documented blocker or fewer qualified entries, never invented dimensions, relaxed validation or a category substitution.

The initial visual target is the existing rectangular bedroom, seeking bed, desk and wardrobe/storage, with an optional chair. Do not promise three to five textured categories before assets qualify. A wardrobe needs a genuinely appropriate storage model; a chair cannot stand in for a desk. Product variants must be distinguished.

Default scope is floor-standing, static, pre-normalized assets at furniture yaw zero. Wall-hung/ceiling assets, arbitrary rotations, connected/nonrectangular rooms, material editing and learned layout priors are excluded from the first MVP.

## 2. Ordered tasks and checkpoints

### 08A — Source, license and dimension qualification

**Goal:** establish which sources and candidate products may be acquired for a public demo, without acquiring models or implementing ingestion. This is the first authorized-next-task recommendation, not work already performed.

**Dependencies:** the audit only. Start with the local pinned chair as an illustrative regression fixture; investigate individual ABO product entries for real dimensions, then CC0 alternatives. Treat the original FRONT/FUTURE restrictions as a blocking condition unless authoritative additional rights are supplied.

**Files to create:**

- `docs/data/FURNITURE_SOURCE_REGISTER.md`: human-readable evidence, rights decisions, category gaps and acquisition shortlist.
- `data/catalogs/furniture_source_candidates.json`: machine-readable qualification records; not packaged or consumed by the application.

Use a top-level `schema_version: 1`, `checked_on`, `deployment_target: "noncommercial_public_demo"` and `candidates` sorted by stable `candidate_id`. Each candidate records:

| Information | Required contract |
| --- | --- |
| Identity | `candidate_id`, source name, source product/variant ID when known, canonical category, model/metadata URLs and source revision/date. Null is permitted when genuinely unknown. |
| Rights | Creator/copyright, license identifier and URL, authoritative evidence URLs, attribution/modification obligations; `rights_status`: `verified`, `unknown` or `restricted`. Record public hosting/redistribution separately from commercial use. |
| Dimensions | Original item dimensions/units and normalized width/depth/height in meters when justified; source and axis interpretation; `dimension_status`: `verified`, `unknown` or `illustrative`. Never use shipping/package dimensions. |
| Technical evidence | Known format, units/up/front/anchor, model byte size and mesh/texture information where documented. Hash only files actually present; unknown hashes/bounds remain null. |
| Decision | `eligible_for_acquisition`, `needs_evidence`, `excluded` or `fixture_only`; reasons and missing evidence. Acquisition eligibility is not final render approval. |

**Acceptance criteria:**

1. Recheck the local chair hash/license and identify its non-product status. It may be `fixture_only`, never manufacturer-qualified.
2. Document at least one source investigation for each target category, using concrete product records where accessible. If no defensible candidate exists, record the category gap; success does not require fabricating a complete shortlist.
3. Every `eligible_for_acquisition` entry has verified public-hosting rights, item-level metric dimension evidence, an identifiable model/product relationship and no unresolved category/variant conflict. Unknown evidence prevents this status.
4. Record conflicting mirror/original terms explicitly. No source qualifies solely through a mirror label or a permissive code license.
5. Use only primary documentation and bounded metadata: at most **1 MiB per response and 5 MiB total downloaded content**, no archive, GLB, texture, image, LFS clone, API inference or paid service. Inspect existing local files freely. If evidence cannot be obtained within this budget, record it as unresolved.

**Verification:** parse JSON with the standard library; reject duplicate/unsorted candidate IDs, invalid decision values, non-finite/nonpositive claimed dimensions, missing evidence for eligible entries and any checked-in binary. Manually cross-check every eligibility decision and conversion. No app test change is necessary for two data/documentation files; the baseline production suite remains untouched. No new visual behavior to inspect.

**Deliverable/checkpoint:** evidence register, candidate JSON, category-level go/no-go table and exact remaining permissions. Selectively commit these two files after checking synchronization; push normally and require green CI. Stop before 08B or acquisition.

**Access:** no API key, GPU, cloud account or paid subscription. If a source requires authentication or additional rights, exclude/defer it; do not sign agreements or accept terms on the user's behalf.

### 08B — Strict catalog and dimension normalization

**Goal:** implement a small independent catalog using qualified source metadata; do not load new models yet.

**Dependencies:** reviewed 08A results. If no real-size candidate qualifies, implement only synthetic catalog tests and report the data blocker; do not claim an approved product catalog.

**Anticipated files:** new `src/archimind/assets/__init__.py`, `assets/catalog.py`, `assets/furniture_catalog.json`, `tests/test_asset_catalog.py`; update `pyproject.toml` only for catalog package-data inclusion. Read 08A's JSON; do not make the application consume an unreviewed source register directly.

**Public interfaces:** typed frozen `FurnitureAssetRecord` and `FurnitureCatalog`; `load_catalog()`; `furniture_from_catalog(asset_id, *, furniture_id, name, x_m, y_m) -> Furniture`. The factory creates a fresh item at yaw zero using qualified physical dimensions. It never edits an existing candidate or generates/validates a layout.

Catalog records retain stable asset/version/product IDs, category, original measurement evidence, canonical metric dimensions, rights/attribution and separate render-qualification metadata. Define `metadata_qualified` and `render_qualified` states; only 08C can establish the latter. Asset versions/content changes produce a new identity, not a silent overwrite. Use explicit unit conversions, including inch = 0.0254 m; reject ambiguous axis assignments, unknown units, package dimensions and non-finite values.

**Acceptance/tests:** strict JSON round trip, duplicate IDs, finite bounds, known unit conversions, exact source category mapping, SKU variants, immutable records, unknown/restricted rights and dimension evidence rejection. Existing furniture schema and all old tests remain unchanged. Package a wheel/sdist and verify the catalog is available in an isolated target installation. No new dependency or renderer/UI change.

**Deliverable/checkpoint:** catalog API, qualified metadata entries and synthetic deterministic tests. Diff review, full Python/Ruff/pip/health checks, packaging verification, selective commit/push, green CI. No new browser appearance is expected. No credentials, GPU or cloud service required.

### 08C — Curated acquisition, asset inspection and metric placement

**Goal:** acquire only explicitly shortlisted assets and establish safe, correct local loading. This is a separate future task; no acquisition is authorized by the present audit implementation.

**Dependencies:** 08A rights/acquisition decisions and 08B catalog. Stop before downloads whose license, size or permitted retrieval method is unresolved. Use individual object paths; never retrieve a full dataset archive. A useful minimum is one qualified new category; expand toward three only within all gates.

**Anticipated files:** new `scripts/inspect_furniture_assets.py`, `tests/test_asset_preparation.py`; updates to `assets/catalog.py`, `assets/furniture_catalog.json`, `render/realistic_scene.py`, `render/realistic_viewer.py`, `_viewer_assets/furniture/` manifests/notices and approved GLBs; frontend `src/geometry.js`, `room_objects.js`, `room_viewer.js`, `asset_pool.js`, `room_geometry.js` plus corresponding tests and regenerated bundle. Extend `pyproject.toml` only if genuinely needed for packaged license subpaths.

Use existing Python/Three.js capabilities for inspection; no new conversion framework. Prefer directly supported, self-contained GLB. OBJ/unsupported-compression conversion is a separate proposal if needed. Retain the legacy one-chair API/payload while adding a versioned multi-asset contract; older envelopes continue through their existing decoder. Runtime uses only catalog-derived local filenames and IDs, never a user path/URL.

**Placement policy:** normalize documented units and native axes; measure transformed bounds/anchor. Ground floor-standing models, preserve aspect ratios and verify each dimension against the product envelope. Initial agreement threshold is **max(0.01 m, 2% of that dimension)** per axis. This is an acquisition-quality tolerance, not a collision tolerance and not authority to edit dimensions. Render bindings also require the model envelope to remain within the canonical furniture volume, allowing only a 1e-6 m numeric comparison tolerance. An oversized/incompatible asset becomes a placeholder; do not shrink it silently. Legacy fitted chair demonstrations remain explicitly illustrative and separate.

**Initial new-asset budgets:** at most 15 MiB encoded per GLB, 50 MiB unique encoded assets per scene, 100,000 triangles per asset, 300,000 instantiated furniture triangles per scene; maximum texture dimension 2048 px and estimated unique decoded RGBA textures including mipmaps at most 128 MiB per scene. Count shared textures once and instances' rendered triangles separately. These are starting qualification limits, not measured device guarantees. Budget-driven derivation must be deterministic, licensed and hash-recorded; if preparation needs new tooling, stop and propose it instead of adding dependencies silently.

**Acceptance/tests:** source/derived hashes and license texts, extension allowlist, no external URIs, sane bounds, verified dimensions, anchor/up/front mapping, unsupported mounting/orientation rejection, complete binding IDs and category consistency. Test missing/corrupt/oversized assets, shared pool ownership, failed and canceled loads, aggregate budget fallback and input immutability. Keep the existing fixed-scene and legacy tests passing. Bundle reproduction and source/wheel inclusion must pass.

**Visual check/deliverable:** local desktop/narrow inspection of every admitted asset with metric axes/footprints, original materials, visible placement evidence and forced failure. Record load metrics; screenshots stay outside Git. A catalog entry becomes `render_qualified` only after automated and visual checks. Commit prepared assets and evidence in one bounded reviewed checkpoint; no unapproved large files. Green full CI required. No model API key/GPU/cloud requirement; source permission remains mandatory.

### 08D — Render exact selected layout candidates in Three.js

**Goal:** synchronize the existing selected validated `RoomDesign` with a new optional realistic view.

**Dependencies:** 08C approved loader/catalog and at least one compatible asset or an explicitly identified mismatch case. Missing coverage must remain visible rather than overstated.

**Anticipated files:** new `assets/selection.py`, `tests/test_asset_selection.py`; update `ui/layout_generation.py`, `render/realistic_scene.py`, `tests/test_layout_sync.py`, `tests/test_realistic_scene.py`; frontend `src/main.js` only if component update handling requires it, with lifecycle tests/bundle regeneration. Keep `app.py`'s standalone demonstration separate and labeled.

Add `build_render_bindings(design, catalog, *, overrides=None)` with deterministic default selection: eligible exact category and compatible dimensions first, then stable asset ID/version order. An explicit compatible override wins; an invalid override returns a reasoned placeholder, not a different product. Bindings include the catalog version and complete furniture-ID coverage. Do not persist a second mutable selected-design object.

**Acceptance/tests:** A/B switches use the exact existing candidate, preserve index/order/IDs/coordinates/room/openings, reports and score; no generation, spatial validation or AI calls on rendering/view change. Catalog mismatch, unsupported yaw, empty room, failed generation and stale bindings are safe. A failed regeneration preserves the prior valid result. Reruns retain selection and clean up old asset references; two browser sessions remain independent. Legacy scenes still work.

**Visual check/deliverable:** inspect both alternatives at desktop/narrow widths, demonstrate at least one real compatible model or clearly document why existing dimensions admit only placeholders. Force an asset failure and recover. Camera/reset/orbit/zoom and structure must remain correct. Full Python/frontend/build/Ruff/pip/health/packaging checks, selective checkpoint and green CI. No new credentials or live AI calls.

### 08E — User-visible eligibility, selection and catalog-sized specifications

**Goal:** make the real catalog useful without changing validated layouts implicitly.

**Dependencies:** 08D selected viewer and qualified catalog. This checkpoint completes the useful first MVP; 08D alone may have insufficient dimensional matches with manually specified furniture.

**Anticipated files:** new `ui/furniture_assets.py`, `tests/test_furniture_assets_ui.py`; updates to `ui/layout_generation.py`, `assets/selection.py`, `tests/test_layout_generation_ui.py`, `tests/test_layout_sync.py`, README and developer status/asset guide.

For existing candidates, offer only compatible render bindings plus an explicit procedural option. Show product/source, verified dimensions, rights/attribution, illustrative status and fallback reasons. Keep these choices separate from original generation/selection state.

For different product sizes, provide an explicit **Prepare catalog-sized bedroom** action before generation. It creates a fresh specification using 08B's factory and the existing room/openings; show the dimension changes for review. Only an explicit Generate action runs the unchanged generator. Store the specification/catalog version with that result. Never apply pending size/product edits to active candidates or their reports. Retain the existing manually sized bedroom path and standalone samples.

**Acceptance/tests:** compatibility filters, stale catalog/selection resets, retryable load failures, deterministic choices, no work on ordinary reruns, no cross-session contamination, correct stored specification versus pending controls, explicit generation boundary and safe fallback when a category has no eligible product. Preserve original selected-layout and styling safeguards; stale style results cannot apply to a newly generated specification.

**Visual check/deliverable:** generate catalog-sized alternatives, compare both views, inspect each supported category, labels and attributions at desktop/narrow widths; test placeholders and regeneration. Record honest coverage, not an unsupported three-category claim. Run full checks/packaging; update docs, selectively commit/push and require green CI. No AI key/GPU/cloud/paid asset subscription required.

### 08F — Expand catalog and investigate larger-source feasibility

**Goal:** grow useful coverage only after the end-to-end contract proves stable.

**Dependencies:** 08E results, measured scene/device budgets and rights eligibility. FRONT/FUTURE remains blocked for public hosting absent applicable permission. Research-only data must never leak into the distributable catalog or caches.

**Anticipated files:** `docs/data/FURNITURE_SOURCE_REGISTER.md`, `data/catalogs/furniture_source_candidates.json`, packaged catalog/provenance, new `scripts/prepare_catalog_subset.py`, `tests/test_catalog_subset.py`, `docs/data/DATASET_PREPROCESSING.md`. Add an importer under `src/archimind/data/` only in a separately scoped follow-up after source/schema selection; do not build a universal ingestion framework first.

**Acceptance/tests:** bounded deterministic subset manifest, reproducible ID joins, unit/axis/anchor conversion evidence, rights and material completeness, missing/corrupt/duplicate records, interrupted caching and package-size review. Hold out reference entries; compare physical dimensions and appearance rather than only parser success. Profile cold/warm loading and representative device behavior before raising budgets.

**Deliverable/checkpoint:** category coverage/cost report plus a small reproducible subset, or a documented no-go if rights/retrieval is unresolved. No bulk download without a separate size/storage decision. GPU, account, paid services or conversion tooling are not assumed; document any new requirement before proceeding.

### 08G — Real-world room/layout priors and architectural usefulness

**Goal:** improve planning with grounded relationships, separately from graphics.

**Dependencies:** suitable rights-cleared, metrically interpretable room records and an explicit representation decision. General room imports need a prior cross-layer rotation/room-support task; it must cover anchors, footprints, containment, circulation, generation and both renderers before accepting arbitrary poses or polygons.

**Anticipated first files:** `docs/data/ROOM_LAYOUT_PRIORS.md`, `data/benchmarks/room_layout_cases.json`, new `tests/test_layout_benchmark_cases.py`, `scripts/evaluate_layout_priors.py`. Any future changes to `geometry/layout_generator.py`, models or validators require a separate reviewed feature task, not a silent data-pipeline patch.

**Acceptance/tests:** distinguish professional synthetic scenes from measured buildings; establish units, openings, room-object IDs and transforms; reject unsupported records without flattening or yaw coercion. Predeclare held-out evaluation for circulation, bed-side/desk/storage use, adjacency and diversity. Compare against the current deterministic baseline; preserve safety and report unsupported checks. No trained/learned improvement claim from prettier renders or data import alone.

**Deliverable/checkpoint:** reviewed benchmark/protocol and representation gaps before algorithm changes. Record data permissions and resource needs explicitly. A GPU or live AI service is unnecessary for a small descriptive benchmark; any later training is separately authorized.

## 3. Verification, delivery and audit receipts

The audit's exact baseline and browser evidence are recorded in [section 12 of the readiness report](REAL_DATA_READINESS_AUDIT.md#12-verification-results). Python: **1,219 passed in 75.97s**. Frontend: **27 passed, 0 failed, 0 skipped**. Ruff lint/format, dependency compatibility, non-writing bundle equivalence and Streamlit health passed. Normal browser inspection had zero console errors and one Plotly readback advisory. No production changes justified repeating the same complete baseline locally; documentation checkpoints are also verified by GitHub CI.

For implementation checkpoints, execute the full Python suite, Ruff lint/format, pip check, Streamlit health, frontend syntax/tests/build with unchanged-bundle checks after intentional rebuilds, and source/wheel packaging when assets/catalog contents change. Block live providers, network and subprocess execution in deterministic unit tests using the existing mocking conventions; controlled local HTTP browser tests are separate. Do not weaken existing tests to accommodate source data. Record failures and stop release rather than marking required unknowns passed.

Commit only intended files after reviewing staged diffs, checking remote synchronization and running relevant checks. Never stage secrets, screenshots, `.agents/`, `.claude/`, raw datasets or unrelated modifications. Push normally; remote divergence stops the checkpoint for review. Require the final CI run to pass and report its actual result. Documentation commits do not authorize feature implementation.

Audit delivery checkpoint 1: `1303a86a09925e8840b0a02017e998b987ccc647` ([readiness report commit](https://github.com/ngstephen1/ArchiMind/commit/1303a86a09925e8840b0a02017e998b987ccc647)); [checkpoint CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40751640528), including **1,219 Python tests in 146.37s**, **27 frontend tests**, build/bundle equality and health. Additional local lint, format (106 files), pip compatibility, asset-integrity and health checks passed while reviewing these documents. The second checkpoint contains this plan. Final hashes/CI status belong in the delivery response; no document can contain its own future commit hash without changing that hash.

## 4. Ready-to-paste Codex CLI task prompt — 08A only

The following is task text to paste into a future Codex CLI session. It was **not executed** by this audit.

```text
You are continuing ArchiMind in /Users/macbook/Hack/ArchiMind.

Complete only Task 08A — Source, license and dimension qualification.
Read docs/audits/REAL_DATA_READINESS_AUDIT.md and the 08A contract in
docs/audits/REAL_DATA_IMPLEMENTATION_PLAN.md first. Inspect Git status,
branch, remote synchronization and applicable AGENTS.md. Preserve unrelated
changes and untracked .agents/ and .claude/ content; do not inspect secrets.

Target: noncommercial public demo serving furniture model bytes to browsers.
Create only:
1. docs/data/FURNITURE_SOURCE_REGISTER.md
2. data/catalogs/furniture_source_candidates.json

Follow the plan's schema_version=1 candidate contract, statuses, eligibility
gates and budget exactly. Record existing Sheen Chair as fixture-only:
verify its local source/hash/license, but it is not a real product and has
no manufacturer-qualified dimensions. Investigate ABO product records first
for bed, desk and wardrobe/storage; investigate per-asset CC0 alternatives
where useful. Record at least one source investigation per category. Concrete
candidate IDs are preferred; unavailable evidence must remain unknown, with
an explicit category gap. Zero qualified new assets is an acceptable finding.

For each candidate record identity/variant, primary source/revision/date,
license and attribution, public hosting/redistribution/commercial status,
item dimensions and original units, normalized metric axes, technical
metadata and missing evidence. Never substitute shipping dimensions, invent
mesh bounds/hashes, or treat mirror availability as redistribution rights.
FRONT/FUTURE public use remains blocked unless authoritative additional
permission resolves the reviewed restrictions.

Use only primary documentation and lightweight metadata: <=1 MiB per
response and <=5 MiB total downloaded content. Do not download GLB/models,
textures/images, archives, datasets or LFS content. No new dependencies,
production code, schema/geometry/validator/generator/UI/renderer changes,
new agents, paid services, live AI requests or Codex subprocess calls.
Do not accept license agreements or seek credentials on the user's behalf.

Validate JSON with the standard library: unique sorted candidate IDs,
allowed statuses, finite positive claimed dimensions, and complete evidence
for acquisition eligibility. Manually check conversions and rights decisions.
Run git diff --check, inspect intended diffs and confirm no binary or unrelated
files were added. Preserve all existing tests; no test weakening or new app
behavior. No visual behavior should change.

If main is synchronized, selectively commit these two verified files and push
normally to origin/main; verify CI. Never force-push or overwrite concurrent
work. Report exact files, candidate/category decisions, source citations,
verification, commit/push/CI results and unresolved rights/dimension evidence.
Stop after 08A for review. Do not start 08B, acquisition or ingestion. Do not
work on the separate course Requirements & Architecture write-up.
```
