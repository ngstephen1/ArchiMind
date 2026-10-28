# Project status

Last reviewed and locally verified: **October 27, 2026**.

**Current milestone: Task 07A complete — deterministic LangGraph backend foundation.**
Task 07B is recommended next; Task 06E2 remains separate proposed renderer work.
The Task 03 preview, Task 05B comparison, and
Task 06A structural-only preview are preserved.
Optional C01 is complete separately: a disabled-by-default, backend-only Codex
advisor with offline tests. C02 remains a separate proposed integration.

## Milestones

| Milestone | Status | Delivered behavior |
| --- | --- | --- |
| Task 01 — Foundation | Complete | Editable Python package, local environment, Streamlit screen, smoke tests, and CI |
| Task 02 — Core data models | Complete | Typed room, door, window, furniture, and design models; strict schema validation and JSON round-trips |
| Task 03 — 2D floor plan visualization | Complete | Reusable Plotly renderer, reproducible bedroom factory, Streamlit preview, and coordinate-based tests |
| Task 04A — Containment and collisions | Complete | Zero-rotation Shapely footprints, containment, all-pair overlaps, scoped JSON reports, and geometry tests |
| Task 04B — Door clearance and paths | Complete | Configurable rectangular door approach checks, bounded polygon circulation connectivity, explicit check states, and 69 new tests |
| Task 05A — Deterministic furniture layout generation | Complete | Bounded seeded placement, validator-backed alternatives, reproducible scores, bedroom CLI, and 52 new tests |
| Task 05B — Streamlit layout generation and comparison | Complete | Seed/button controls, A/B selection, real coordinates/scores/reports, session state, explicit failures, and 20 frontend tests |
| Task 06A — Basic interactive 3D room geometry | Complete | Structural meshes with real door/window holes, orthographic camera, equal metric scaling, 3D preview, and 43 tests |
| Optional C01 — Codex CLI advisor backend | Complete, live behavior unverified | Typed suggestions, fixed isolated read-only invocation, default-off and per-call gates, bounded I/O, sanitized failures, and 53 mocked tests |
| Task 06B — 3D furniture visualization | Complete | Bounded bed/desk/wardrobe/generic meshes, furnished scene, fixed-sample app preview, 43 new tests, and browser verification |
| Task 06C — Selected 2D/3D layout synchronization | Complete | Exact selected candidate feeds both views, compact camera framing, 13 new tests, and desktop/mobile verification |
| Task 06D — Realistic 3D asset/renderer proof of concept | Complete | One CC0 textured chair, pinned local Three.js bundle, opt-in Components V2 viewer, standalone fallback, 29 Python/9 frontend tests |
| Task 06E1 — Realistic 3D architectural room foundation | Complete | Canonical scene contract, genuine wall openings, shared chair instances, labeled placeholders, independent opt-in room; 23 new Python/18 new frontend tests |
| Task 06E2 | Proposed rendering work | Curated asset bindings and room interaction refinements; not implemented |
| Task 07A — LangGraph workflow foundation | Complete, deterministic backend only | Typed state, four future-agent roles, independent spatial critique, fixture styling, bounded conditional execution, offline CLI, 38 tests |
| Task 07B — OpenAI-backed Requirements Interpreter | Recommended next | No model integration or natural-language interpretation implemented yet |
| Later phases | Planned | Agents, targeted revisions, persistence, and export |

## Capability status

| Capability | Current support | Boundary |
| --- | --- | --- |
| Room representation | One rectangular room in meters | No arbitrary room polygons or multiple-room plans |
| Openings | Wall-relative doors and windows | Schema checks wall endpoints and ceiling limits; hinge/swing information is not modeled |
| Furniture data | IDs, names, categories, positions, dimensions, and right-angle rotations | Data can represent overlaps and out-of-room objects |
| Schema validation | Strict types, finite numbers, positive dimensions, opening extents, and design-wide unique IDs | Does not establish spatial validity |
| 2D rendering | Walls with opening gaps, blue windows, gold door spans, furniture footprints, and labels | Only zero-rotation furniture; unsupported rotations raise `ValueError` |
| Interaction | Hover, pan/zoom, equal metric scale, Generate Layouts button, seed control, and A/B selector | Fixed sample specification; no furniture-editing controls |
| Sample data | Fresh 5 × 4 × 2.7 m bedroom with a south door, north window, bed, desk, and wardrobe | Manually specified demonstration, not an optimized or spatially validated layout |
| JSON | Model serialization and reconstruction | No project-save UI or revision database |
| Spatial checks | Backend containment, furniture overlaps, door approaches, and circulation for rotation 0 | Separate from renderer; rectangular/square approximations, no swing or vertical checks |
| Validation reports | Unchanged Task 04A API plus combined Task 04B report; typed JSON, errors/warnings, per-check results, and overall passed/failed/unverified | Unsupported/unevaluated required checks cannot pass; supported violations remain visible |
| Layout generation | Backend and Streamlit expose up to two distinct validator-approved alternatives with deterministic seeds/scores and validation summaries | Rotation zero; fixed sample dimensions in UI; no LLMs or global-optimality claims |
| Session state | Results and selection survive normal reruns; generation and acceptance checks run only on button click | Refresh/disconnect may clear results; no database persistence |
| 3D structure | Floor, four zero-thickness walls, real door/window gaps, optional blue glazing, and orbit/zoom/pan | No 3D furniture, ceiling slab, reveals, or synchronization with selected layouts |
| 3D furniture | Bed frame/mattress/pillows, desk tabletop/legs, wardrobe/plinth/panels/handles, and generic solids | Rotation 0 only; at most 100 items; generated selection and separate fixed sample; no rendering-based validity claim |
| Selected 2D/3D views | Both renderers receive the same stored candidate design | Selection does not generate or spatially revalidate; no furniture editing or camera-pose persistence across A/B switches |
| Experimental realistic room | Local Three.js room, four walls with real holes, glazing, procedural floor, two textured chairs and a labeled desk placeholder | Independent fixed sample; rotation 0; no generator connection or detailed-mesh validity claim; legacy single-chair mode retained |
| Export | Not implemented | No GLB, CAD, or BIM integration |
| Workflow orchestration | Backend-only LangGraph requirements → layout → critique → styling graph | Four deterministic future-agent roles; no LLMs, free-form parsing, UI connection, persistence or automatic revisions |
| LLM agents / API | Not implemented | No model-provider calls; no API key required |
| Optional Codex advisor | Backend only, disabled by default | Local single-user CLI integration; no UI or automatic application; no live request made |

## What the app currently shows

The original branding and canonical **2D Floor Plan Preview** remain. The phase
metric now reads Task 06E1, and planned-capabilities text reflects current support.
Below the sample, **AI-Assisted Room Layout Generator** presents Room Information,
Layout Generation Controls, Generated Alternatives, Selected 2D Floor Plan,
Selected 3D Furnished Room, and
Spatial Validation Summary. It calls the existing deterministic generator, uses
the existing renderer, and makes no AI-reasoning claim.

The preview caption explicitly states:

> Manually specified Task 03 demonstration. Generate and compare validated alternatives below.

The new **Interactive 3D Room Preview** below the comparison displays only the
fixed sample room structure, with this explicit caption:

> Structural-only preview of the fixed sample room. Independent of Layout A/B; synchronized views appear in the generator section.

**Interactive 3D Furnished Room Preview** follows it, showing the canonical sample
bedroom with all three furniture items. Its caption explicitly identifies it as a
fixed sample, independent of Layout A/B, and says rendering does not establish
spatial validity. The fixed scene survives generation, selection, and regeneration.

The animated isometric README header remains concept artwork. The live app now
provides synchronized generated 2D/3D views and separate sample demonstrations.

## Verified baseline

| Component | Version |
| --- | --- |
| Local CPython | 3.11.13 |
| Streamlit | 1.66.1 |
| Pydantic | 2.14.1 |
| Plotly | 7.1.0 |
| Shapely | 2.2.0 |

Task 06A verification retained from that milestone:

- `python -m pytest -q`: **432 passing tests**, retaining all 389 previous cases
  and adding 43 3D geometry/integration cases. Existing app assertions reflect
  the new phase/planned-copy; comparison tests count 2D charts independently
  from the added 3D structural chart.
- `python -m pip check`: no broken requirements.
- `python -m ruff check .` and `python -m ruff format --check .`: passed.
- Headless Streamlit health endpoint: HTTP `200` with `ok`.
- Task 03 browser inspection: correct opening/furniture positions, readable labels,
  identical X/Y pixels per meter, functioning hover/pan/zoom, and no console
  warnings or errors. Desktop and narrow layouts were inspected.
- Renderer input immutability and explicit rotation rejection are covered by tests.
- Task 04A geometry tests cover wall contact, each room boundary, complete exclusion,
  every overlapping pair, shared edges/corners, tolerance, unsupported rotations
  and numeric geometry, deterministic issue ordering, report JSON round-trips, and
  preservation of the original design. The renderer, geometry APIs, generator,
  and canonical models remain unchanged in Task 05B.
- Task 04B covers all four walls, both wall endpoints, every door blocker,
  advisory-only warnings, strict zone contact, barriers, narrow passages, alternate
  routes, multiple/no doors, unsupported rotations, work limits, numeric precision,
  configuration validation, deterministic reports, JSON round-trips, and no mutation.
- Task 05A covers validated alternatives, dimensions/identity preservation,
  containment, zero-tolerance overlaps, door/circulation checks, same/different
  seeds, input-order independence, no global random-state changes, unchanged and
  independent inputs, scores, advisory penalties, budget limits, infeasibility vs
  exhaustion, empty requests, unsupported features, JSON, CLI, and rendering.
- Task 05B uses AppTest and real/mocked results for generation parameters,
  A/B coordinates/plots, scores/reports, no repeated generation or revalidation,
  pending/new seeds, separate sessions, warnings, partial/empty/failed outcomes,
  exception recovery, and rejection of stale reports on invalid geometry.
- Task 06A tests actual wall triangles and coverage, opening gaps on all walls,
  corner/stacked/multiple/touching openings, overlap rejection, full-wall holes,
  2D projection agreement, metric scaling, determinism, immutability, JSON,
  numeric/work limits, and independent Streamlit 3D geometry across A/B selection.

The overlap area tolerance is **1e-9 m²** by default; containment uses Shapely
`covers` without buffering. The original `validate_layout` remains scoped to
Task 04A. The additive `validate_accessibility` API runs all four checks with
`AccessibilityConfig` and returns `AccessibilityValidationReport`. Defaults:
required opening-width approach depth **0.3 m**, advisory depth **0.9 m** plus
**0.15 m** at each side, and walking clearance **0.6 m**. Door rectangles are clipped
at room corners; positive-area required-zone intrusion is an error, while an
advisory-only intrusion is a warning. No actual door swing is evaluated.

Circulation uses continuous polygon connectivity, not a grid (no sampling
resolution): inset the room and expand obstacles by half the walking clearance
to represent an axis-aligned square. Every door midpoint entry must reach the
single connected positive-area occupant-center region. Door width is checked.
Access work is capped at **256 furniture objects plus doors combined**; excess is
unsupported. Unknown geometry prevents a circulation pass. No doors gives explicit
`not_evaluated` access checks. Overall `unverified` takes precedence over known
failures, and `passed` permits advisory warnings only when all checks are evaluated.

Known limits: square/midpoint assumptions can reject otherwise usable routes;
exact-width point/line pinches can fail; tiny disconnected regions count; areas
too small for the square are excluded. Double-precision topology near tangencies
can produce false positives/negatives. Numeric collapse is unsupported. There are
no furniture-function, vertical, multi-room, door-swing, or code-compliance claims.
The sample bedroom passes the default checks. A cabinet at a door causes a strict
violation; a full-width barrier or a 0.5 m passage fails circulation at 0.6 m,
while a 0.7 m alternative route passes. No dependencies were added for Task 04B.

## Task 05A implementation

`generate_layout_candidates(room, furniture, seed=42, max_candidates=2,
max_attempts=500, config=None)` samples one pose per item per attempt, largest
footprint first with ID tie-breaks. Wall contacts and centimeter-rounded interior
coordinates are sampled with a local random source. Existing Task 04A checks
prune partial layouts; Task 04B must pass every complete accepted candidate with
zero overlap tolerance. The first distinct validated alternatives are ranked by
score and coordinates; the remaining budget is not searched for a global optimum.

Scores are `80 × usable-space ratio + 20 × advisory-clearance ratio`, using
existing circulation measurements and door warnings only. The former normalizes
usable occupant-center area against the empty inset room; the latter is the
fraction of doors without advisory warnings. Scores never excuse hard violations.
All original room/opening data and furniture identities/dimensions are preserved;
only output positions change. Original inputs remain unchanged.

`LayoutGenerationResult` reports `complete`, `search_exhausted`, `infeasible`, or
`unsupported`, with seed/config, attempts, rejection counts, and any passing
candidates. Only oversized footprints, excess total area, or failed empty-room
entry/clearance checks justify infeasible outcomes. Search exhaustion makes no
infeasibility claim. Empty furniture has only one distinct alternative; no-door
rooms cannot be accepted. Limits are 32 furniture objects, 10,000 attempts, and
the access engine's 256 combined object cap. Finite sampling and fixed orientation
can miss valid layouts. This adds no functional furniture-access, daylight,
ergonomics, or code-compliance evaluation. No external dependencies were added.

Run `python -m archimind.examples.generate_bedroom` for deterministic JSON of the
original specification and alternatives, with execution timing separately on
stderr. Seed 42 returns two alternatives in 9 attempts; both pass every spatial
check, with scores **67.721925** and **67.614973**. Exact coordinates and components
are documented in the README. Existing `render_floorplan(candidate.design)` works
without changes. Task 05B now exposes these same alternatives in the UI.

## Task 05B integration

The button calls `generate_layout_candidates` with the canonical sample, seed 42
by default, two requested candidates, and 500 maximum attempts. Results are schema
revalidated and candidate geometry/reports checked through the existing spatial
API once before storage. Session state owns the result, last error, and selection.
Changing the seed or A/B selection never invokes generation or acceptance checks.
New responses replace the stored result and select A; exceptions retain the old
result/selection, while structured no-candidate responses clear the alternatives.
No database, AI calls, new layout algorithm, or dependency was added.

The UI displays actual heuristic scores, furniture coordinates, report status,
issue counts, advisory warnings, and check results. Search exhaustion is distinct
from necessary-condition infeasibility. Unsupported inputs show backend reasons,
including the zero-rotation restriction. Browser refresh/session loss can clear
results. The interface is limited to the fixed sample bedroom in this phase.

Playwright verification: Generate Layouts, A/B selection, seed 42-to-43 pending
state, explicit regeneration, actual coordinates, hover, drag-pan, scroll zoom,
and reset all worked. The default seed returned the same two passing layouts and
scores as Task 05A. Desktop (1440 px) and narrow (390 px) views were inspected;
room axes preserve equal pixels per meter, labels are readable, and the page has
no horizontal overflow. Browser console: zero warnings/errors. Screenshots are
local, ignored artifacts in `output/task05b/`.

Task 05A backend measurements, retained from that phase: Python 3.11.13, ten
function calls per case (imports, rendering, and UI integration excluded; these
are observations, not CI timing thresholds):

| Case | Outcome / attempts | Median | Observed range |
| --- | --- | --- | --- |
| Bedroom, seed 42 | 2 candidates / 9 | 0.006529 s | 0.006423–0.011673 s |
| Bedroom, seed 7 | 2 candidates / 15 | 0.012595 s | 0.012558–0.012655 s |
| Two 3 × 2.5 m objects in 5 × 4 m | Search exhausted / 500 | 0.143187 s | 0.142380–0.146941 s |
| Four 3 × 2 m objects in 5 × 4 m | Excess area / 0 | 0.000059 s | 0.000055–0.000074 s |

The exhausted search returned at its configured limit; no unbounded retry loop
is used. Cost increases with item count and attempt budget.

## Task 06A structural renderer

`render_room_3d(room)` revalidates canonical schemas/IDs and builds explicit
triangles for the floor and solid wall panels. Wall strips are cut at opening
endpoints, with opening height intervals omitted. Separate blue glazing and
door/window outlines do not fill wall holes. Positive-area opening overlap on a
wall raises `RoomGeometryError`; shared edges and disjoint stacked openings work.
Limits include 128 openings, finite positive panel areas, and representable spans.

Axis proportions are width:depth:height, uniformly scaled for narrow-screen
framing. The initial camera is orthographic and isometric. Orbit, scroll zoom,
modebar pan/zoom, and reset are available. Scene backgrounds are hidden so they
cannot visually mask the openings. No furniture or synchronization is added.
The sample floor spans 5 × 4 m at Z=0 and the walls reach Z=2.7 m. Its south door
is X=0.6–1.45, Z=0–2.1; its north window is X=2.7–4.2, Z=0.9–2.1.

Browser verification inspected desktop and 390 px views with no initial geometry
or axis-label clipping and no page overflow. Camera controls and existing A/B
comparison were checked. Console: zero errors; one non-fatal Plotly Canvas2D
readback performance advisory. Screenshots are ignored local artifacts under
`output/task06a/`. An older running server required restart to load the new
renderer export; a fresh launch works. Geometry models, validation, 2D renderer,
and layout-generation algorithms remain unchanged. No dependency was added.

GitHub Actions uses one Linux/Python 3.11 job with one dependency installation for
Ruff lint/format checks, `pip check`, the full test suite, and a real Streamlit health
check. It runs for PRs targeting main, pushes to main, and manual dispatches.
The redundant OS/Python matrix, separate quality/build jobs, distribution/archive
checks, clean-wheel installation, and artifact uploads were removed from routine
CI. Manual builds remain available; deployment is not configured. See the
[workflow results](https://github.com/ngstephen1/ArchiMind/actions/workflows/ci.yml)
for the result of a particular commit.

## Optional C01 verification

The [Codex advisor guide](CODEX_ADVISOR.md) documents the API, opt-in gates,
sanitized example, limits, failure codes, and confidentiality limitations.
CLI preflight: `codex-cli 0.135.0` on PATH, saved authentication available;
help confirms required flags. No model request was made. The optional reference
addendum PDF was not located in the repository, Desktop, Downloads, or supplied
attachments; implementation follows the supplied C01 specification.

Latest local verification: **485 passed in 7.56s**, including all 432 baseline
tests and 53 mocked adapter cases. `pip check`: no broken requirements. Ruff:
all checks passed; **35 files already formatted**. The real Streamlit health
check returned HTTP **200 ok**. All 14 protected Python files (app, models,
geometry/generator, renderers, and UI helpers) match the pre-C01 SHA-256 snapshot.
No dependency was added. Existing uncommitted work and unrelated agent directories
are preserved; nothing was committed or pushed during C01. These verified changes
were subsequently checkpointed and pushed under the explicit Task 06B authorization.

Live model/provider behavior remains unverified. Read-only sandboxing does not
guarantee confidentiality, and the adapter must remain local-only. C02, an optional
Streamlit Design Advisor panel, is recommended for a separate reviewed task.

## Task 06B furnished renderer

`render_furniture_3d(furniture)` returns bounded, explicit `Mesh3d` cuboids.
Category selects bed, desk, wardrobe, or a generic fallback; the canonical
`storage` / `Wardrobe` item uses the wardrobe appearance. All parts remain within
the object's declared X/Y/Z bounds. Decimal endpoint arithmetic, finite spans
and face areas, strict schema revalidation, and explicit nonzero-rotation rejection
prevent silent geometry errors. Parts carry raw IDs/metadata and escaped hover
text with names, categories, metric position, dimensions, height, and rotation.

`render_design_3d(design)` reuses the existing room figure without changing any
structural vertices, triangles, or opening geometry. Furniture is sorted by ID.
Scene bounds include out-of-room and above-ceiling furniture without relocation;
axis proportions retain equal units. Input data and generated layout reports are
not changed. This is rendering only; no spatial algorithm or Pydantic schema was
modified, and no Codex live functionality was activated or changed.

The furnished viewer uses an isometric eye direction with perspective projection
for visible modebar zoom; the original structural-only viewer remains orthographic.
Browser verification at desktop 1440 px and narrow 390 px checked initial framing,
door/window visibility, orbit, modebar zoom, pan, reset, furniture hover, A/B
independence, and absence of page overflow. Narrow legend/title overlap and tight
axis framing found during inspection were corrected. Wheel zoom is enabled but
visible magnification was not confirmed; modebar zoom was confirmed visually.
Console: zero application errors and one non-fatal Plotly Canvas2D readback advisory.
Screenshots are ignored local artifacts under `output/task06b/`.

The sample adds 15 cuboids / 180 furniture triangles, for 23 total scene traces.
Warm local scene construction measured a median 23.39 ms (23.24–24.30 ms across
10 calls, imports excluded, before final camera/framing adjustments). This is an
observation, not a performance guarantee. Mesh work is capped at 100 items;
WebGL/browser resources and translucent-wall sorting remain practical limits.
No assets were downloaded and no dependency was added.

Final local verification: **528 passed in 14.15s**, retaining all 485 previous
cases and adding 43 furniture/scene/app cases. Existing UI assertions were updated
for Task 06B copy, and the 2D-chart helper now excludes both types of 3D scene.
`pip check`: no broken requirements. Ruff: all checks passed, **39 files already
formatted**. A fresh real Streamlit launch returned HTTP **200 ok**. The app was
also launched explicitly on local port 8510 for the browser checks. The source
diff confirms no changes to canonical models, existing renderers, geometry,
layout generation, UI generation logic, or the C01 integration.

Checkpoint A (`a349cfb21756a086f8508ad66524d3fdc117755c`) preserves the verified
prior milestones; checkpoint B (`533d713dd7de7683caee1260184fd64d72a1010c`) adds
backend furniture/scene geometry. Both were pushed to `origin/main`, synchronized
after each push, and passed GitHub Actions. The final integration checkpoint
contains the preview, browser-driven framing/projection adjustments, tests, and docs.
Unrelated `.agents/` and `.claude/` remain untracked and untouched.

## Task 06C selection synchronization and framing

One local `candidate` is resolved from the existing session-state result and A/B
radio. Its exact `candidate.design` object is passed to both renderers. No second
selected-design state, coordinate conversion, automatic placement, or geometry
algorithm is introduced. Generation and spatial acceptance checks remain confined
to Generate Layouts. Renderers retain their existing schema-revalidation contracts.

Normal reruns and pending seed edits preserve results and selection. A new
successful generation selects A; normal empty/failure outcomes show no generated
2D/3D pair. An exception preserves both views of the previous selected candidate.
Standalone sample charts remain clearly labeled and independent. The selected
chart keys stay stable, but actual browser inspection found Streamlit resets the
camera to its initial framing when A/B changes; camera pose is not persisted.

The furnished renderer now uses 400 px height (previously 600), a 36 px top margin
(previously 140), a closer perspective eye `(1.35, -1.65, 1.35)`, and center
`(0, 0, -0.06)`. Aspect ratios follow scene-span ratios with equal physical units.
Only the Walls legend control remains; the modebar is vertical and axis titles
are compact. This reduces blank space and keeps the Z label readable at 390 px.
Only presentation changes; furniture coordinates, mesh vertices/triangles,
structural geometry, dimensions, identities, and canonical room ranges are retained.

The seed-42 browser inspection confirmed these exact meter positions in both
the selected 2D and 3D chart data:

| Furniture ID | Layout A X/Y | Layout B X/Y |
| --- | --- | --- |
| `desk` | 0, 1.36 | 3.74, 3.4 |
| `queen-bed` | 3.4, 1.69 | 1.96, 0 |
| `wardrobe` | 0, 3.4 | 0, 3.4 |

Actual desktop (1440 px) and mobile (390 px) inspection covered both views of A/B,
matching IDs/positions/heights, unchanged room structure, initial framing, readable
labels, orbit, modebar zoom, pan, reset, and no page overflow. Eight screenshots
are ignored artifacts in `output/task06c/`. Console: no application errors and
one non-fatal Plotly Canvas2D readback advisory. The app was started explicitly
on port 8511. Modebar zoom is verified; wheel magnification remains unconfirmed.

All previous test cases remain active. New tests cover exact object identity at
both renderer calls, coordinate and ID agreement, immutable results, structural
geometry, no generation/spatial validation on switches or normal reruns, pending
seeds, empty/failed/partial outcomes, exception recovery, fresh sessions, and
deterministic framing with equal units. Models, furniture meshes, structural and
2D renderers, spatial algorithms, layout generation, dependencies, and C01 source
remain unchanged. No live Codex call was made; no asset or AI feature was added.

Final local verification: **541 passed in 21.52s**, including all 528 previous
cases and 13 new synchronization/framing cases. Existing tests retain their
behavioral coverage with updated phase/caption assertions, standalone-chart
selection, and presentation expectations. `pip check`: no broken requirements.
Ruff: all checks passed; **40 files already formatted**. The real headless
Streamlit health check returned HTTP **200 ok**. Protected source paths were
compared against `e455efe`; only UI synchronization, furnished-scene presentation,
tests, and software documentation changed. Screenshots, secrets, and unrelated
agent directories are excluded from the checkpoint.

## Task 06D realistic renderer proof of concept

The [realistic-viewer guide](REALISTIC_VIEWER.md) records architecture, launch
commands, asset provenance, coordinate mapping, observed performance, browser
verification, and remaining limits. Plotly is unchanged and remains the default.
An opt-in **Realistic 3D Viewer — Experimental** section loads one independent
chair studio sample using Streamlit Components V2. No dataset, full-room migration,
new agent, live Codex call, or image-generation API is included.

The Sheen Chair by Eric Chadwick / Wayfair is CC0-1.0, pinned to the Khronos asset
repository revision. Its original 4,125,648-byte GLB contains four meshes, 39,936
triangles and seven embedded images. Supplied fabric, wood, metal and label
materials remain intact. Ten active texture objects were observed in the loaded
scene (some image resources are reused with different texture transforms).
Source/license/checksum/date records and license texts are bundled with the model.

Canonical `(x,y,z)` maps to Three.js `(x,z,-y)`. Uniform scale 1.028361 grounds
and centers the model in the unchanged 0.85 × 0.70 × 0.85 m declared volume at
X/Y 1.1/0.8 m. Actual fitted W/D/H is approximately 0.850 × 0.586 × 0.706 m.
The footprint outline makes unused volume visible. Detailed mesh validity is
not inferred from canonical footprint validation.

Actual browser inspection verified the textured chair, shadows, responsive
desktop/mobile framing, orbit, wheel zoom, right-drag pan, reset, loading state,
missing-asset error, and normal recovery. Local-only rendering also succeeded
with all non-local requests blocked. The independent chair remained available
while Layout B was selected in the unchanged Plotly viewer. Screenshots are
ignored local artifacts under `output/task06d/`. Normal rendering: no console
errors; one existing Plotly readback advisory. Fault injection intentionally
produced a 404 and a clear viewer error, then was removed.

Final verification: **570 passed in 20.09s**, preserving all 541 previous cases
and adding 29 focused asset/component cases. Frontend: **9 passed**, syntax and
production build checks passed, npm audit reported zero vulnerabilities. Pip:
no broken requirements; Ruff lint/format passed. Streamlit health: HTTP **200 ok**.
Wheel build, contents and an isolated target installation verified the bundled
asset. Python dependencies are unchanged; only pinned frontend dependencies and
component package-data configuration were added. CI now verifies the frontend
tests/build and rejects stale committed bundles.

Checkpoint A `d72eea0d8185194bc71122452c14dc97b5aaefb2` was verified, pushed to
`origin/main`, and passed GitHub Actions. The integration checkpoint adds the
Streamlit opt-in section, app tests, mounting/lifecycle refinements and docs.
Unrelated agent directories and generated screenshots remain excluded.

## Task 06E1 architectural room foundation

The [room guide](REALISTIC_ROOM.md) records the version-2 scene contract,
wall geometry, shared-resource lifecycle, local commands and limits. The original
`RoomDesign` supplies all architectural dimensions and coordinates. The typed,
immutable catalog still contains exactly one existing GLB, `sheen-chair`.
No canonical model, Plotly renderer, validator, generator, bedroom fixture,
generated alternative, C01 integration or dependency version changed.

Enable **Load experimental realistic viewer** and select **Architectural room**.
The independent 5 × 4 × 2.7 m room has a south door, north window with glass,
two separately fitted chairs and a clearly labeled blue desk placeholder.
**Single chair (06D)** preserves the original demonstration. Wall meshes exclude
the actual opening rectangles; glass and outlines are separate meshes. All
measurements remain meters with `(x,y,z) -> (x,z,-y)`; models are uniformly scaled.
Front-wall and canonical-footprint controls accompany orbit/zoom/pan/reset.

Actual Chromium inspection at 1440 × 1000 and 390 × 844 verified room framing,
openings, textured instances, the extra placeholder, camera controls and reset,
and readable coordinate rows. At mobile width the component was 347 px wide
with a 360 px scene and no horizontal overflow. A/B switches retained identical
scene metrics with zero new network requests. Original single-chair mode rendered.
With non-local requests blocked the full room still rendered; none were attempted.
Simulated GLB 404 produced one request, a `partial` result, three explicit
placeholders and intact room geometry. Removing the fault restored textured
rendering. An empty room rendered its structure with zero GLB requests.
Normal console: zero errors and one existing Plotly Canvas2D advisory; injected
404 intentionally produced a resource error. Screenshots remain ignored under
`output/task06e1/`.

Observed scene: one GLB load, two chair instances sharing four source geometries,
one procedural object, 79,884 furniture triangles and 18 wall triangles.
Measured local room setup ranged from about 0.38–2.19 seconds across inspected
mounts (includes loading/initialization, not a controlled FPS or memory benchmark).
The two uniform scales were 1.028361 and 0.907377, leaving declared footprints
unchanged. No additional asset was downloaded.

Final Python verification: **593 passed in 22.02s**, retaining all 570 baseline
tests and adding 23 scene/component cases. Frontend: **27 passed**, retaining all
9 baseline cases; syntax and production build passed. Pip reported no broken
requirements; Ruff lint passed and all 50 Python files were already formatted.
Streamlit health returned **HTTP 200 ok**. The Components V2 registration now
mounts via JS/CSS directly, removing a literal HTML filename previously exposed
by the installed component API. The standalone pages keep their own hosts.
Wheel contents and an isolated target installation verified the room assets and
the single checksum-verified GLB.

Core checkpoint `1abdc6a37a3f485cd538d78cf188a8fef54660b4` was pushed to
`origin/main`; [GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40608045325).
The final integration checkpoint adds the Streamlit mode selection, compatibility
tests, label/shadow refinements and updated documentation.

Limits: zero rotation only, 24 furniture objects, 128 openings, bounded dimensions;
no wall thickness, door swing, ceiling slab, asset library, editing, persistence,
automatic-generation connection, agent action or detailed-mesh spatial validation.
Transparent surfaces may exhibit sorting artifacts. Real mobile devices and
other browser engines are unverified; hardware performance remains unbenchmarked.
Unrelated `.agents/` and `.claude/` content remains untouched and uncommitted.

## Task 07A deterministic workflow foundation

The [workflow guide](WORKFLOW.md) documents the actual software contracts, API,
demonstration, failure semantics and local testing commands. LangGraph **1.2.18**
is pinned as a runtime dependency; its current Graph API and Python >=3.10 support
were verified. Existing pinned Python/frontend versions are unchanged. Required
LangGraph dependencies include `langchain-core` and LangSmith; no model-provider
SDK is added, and remote tracing is disabled per invocation.

`DesignRequest` retains optional original prose plus a canonical `RoomDesign`,
seed/budget/config and styling preference. `WorkflowState` carries that original
request, canonical working specification, `LayoutGenerationResult`, individual
`CandidateReview` records, approved selection, fixture styling, stage/status,
ordered `AgentActivity` trace, `WorkflowError` and a bounded iteration count.
Completed handoffs and final outputs are explicitly Pydantic-validated and JSON
serializable. No new architectural model or placement/geometry algorithm exists.

The four deterministic roles are:

1. Requirements Interpreter: revalidate/copy structured data; prose-only requests
   terminate with `missing_specification`.
2. Layout Designer: one call to the existing seeded generator, preserving requested
   options and the original input; retain complete/partial/failure generation data.
3. Spatial Critic: re-run the actual accessibility API at zero overlap tolerance,
   reject failed/unverified checks, altered identities/dimensions/room or mismatched
   claimed reports, then select the first independently approved ranked candidate.
4. Interior Stylist: attach neutral/warm/cool deterministic fixture metadata without
   changing coordinates, assets, scores or validation reports.

One generation iteration, a four-node acyclic graph and recursion limit 6 bound
execution. Unsupported/infeasible inputs terminate safely; empty search exhaustion
is distinguished from proved infeasibility. A partial result can complete if one
candidate passes critique. Exceptions return sanitized errors and clear any final
selection/styling. There is no retry/revision loop, persistence or mutable workflow
singleton. Repeated fixed-seed results and concurrent runs are isolated.

Actual CLI `python -m archimind.examples.workflow_bedroom`: **succeeded**, two
alternatives found in **9/500 attempts**, candidate **0** selected, independently
passing spatial report, neutral `deterministic_fixture` styling. Selected X/Y in
meters: desk **(0, 1.36)**, queen-bed **(3.4, 1.69)**, wardrobe **(0, 3.4)**.
Trace decisions: requirements **accepted** → layout **generated** → critique
**approved** → styling **styled**. Complete JSON reconstructs the typed state.
`--max-attempts 0` returns `exhausted`, no approved design and exit code 1.

Final local verification: **631 passed in 23.75s**, preserving all 593 previous
Python tests plus 38 workflow cases. Frontend **27 passed**, syntax/build passed
with unchanged committed bundles. Editable installation, pip compatibility,
Ruff lint and format (56 files) passed. Streamlit health returned **HTTP 200 ok**.
Tests block socket/DNS access and verify no attempted in-process networking,
remote tracing, subprocess/C01 call or mutation. Actual CLI subprocess tests cover
success/exhaustion JSON and exit codes. Workflow tests additionally cover forged
reports, changed specifications, partial outcomes, errors and concurrent isolation.

Core checkpoint `4ea8dfe8d49703eb44fa83a07b4b7b9fb3a6aafa` was pushed to
`origin/main`; [GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40611699419).
The final checkpoint adds the CLI, broader acceptance tests and documentation.

Streamlit, all renderers/assets, canonical models, spatial algorithms, generator,
sample bedroom and optional C01 implementation remain unchanged. The app continues
to label agent reasoning as planned, and its phase metric stays at Task 06E1.
No live model call, API credential use, dataset or asset download occurred.
Unrelated `.agents/` and `.claude/` directories remain untouched and uncommitted.

## Next milestone

**Task 07B — OpenAI-Backed Requirements Interpreter Agent** is recommended next.
It is not implemented here. Task 06E2 rendering refinements, rotated-footprint
support, furniture editing, persistence and export remain separate future work.

For setup, local commands, coordinates, and renderer usage, see the
[project README](../../README.md).
