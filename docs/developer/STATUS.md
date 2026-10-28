# Project status

Last reviewed and locally verified: **October 27, 2026**.

**Current milestone: Task 07E1 complete — standalone catalog-based AI Interior Stylist.**
Live model behavior is unverified. Task 07E2 is recommended next; Task 06E2 remains
separate proposed renderer work.
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
| Task 07B — OpenAI-backed Requirements Interpreter | Complete backend; live behavior unverified | Gated Responses/Pydantic extraction, canonical evidence/catalog conversion, clarification, optional graph adapter, 77 mock-only tests |
| Task 07C1 — OpenAI-powered Layout Designer advice | Complete standalone; live behavior unverified | Existing-candidate recommendation/abstention, grounded fact refs, preserved scores/reports, 65 offline tests; no graph integration |
| Task 07C2 — Layout Designer graph integration | Complete backend; live behavior unverified | Optional approved-candidate selection after critique, grounded handoff, provenance, deterministic fallback and 50 new offline tests |
| Task 07D1 — AI Spatial Design Critic | Complete standalone; live behavior unverified | Strict evidence-based observations, independent support/challenge, preference tradeoffs and abstention; deterministic reports authoritative |
| Task 07D2 — AI critic graph integration | Complete backend; live behavior unverified | Independent optional critic after deterministic approval/advice, grounded read-only review, fresh fallback verification, 66 new tests and three offline scenarios |
| Task 07E1 — Standalone AI Interior Stylist | Complete backend; live behavior unverified | Five-theme immutable catalog, verified selected candidate, controlled finish/accent metadata, conflicts/clarification and 89 new offline tests |
| Task 07E2 — Interior Stylist workflow integration | Recommended next | Not implemented; existing graph fixture styling remains deterministic |
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
| Workflow orchestration | Default requirements → generation → deterministic critique → styling; independently optional advisor and AI critic | Four default/five with either AI node/six with both, separate opt-ins and live gates; no UI connection/persistence/revisions |
| Requirements interpretation | Optional OpenAI Responses API with structured extraction and canonical conversion | Disabled by default; explicit per-call authorization/key required; only rectangular bedrooms/studios and a three-item furniture catalog; verified with mocks only |
| Layout recommendation | Optional standalone C1 adapter and C2 post-critic workflow handoff | Default-off; only critic-approved candidates, Python-grounded facts and safe deterministic fallback; no UI connection or live verification |
| AI design critique | Standalone D1 adapter and optional D2 workflow node review the approved selected candidate | At most three grounded observations; challenge/failure cannot change selection or deterministic approval; no UI integration or live verification |
| Interior style planning | Optional standalone E1 adapter returns catalog colors/finishes for one approved selected candidate | Separate appearance metadata; no graph integration, material rendering, physical assets or performance certification |
| Workflow stylist | Existing deterministic fixture | Standalone E1 does not replace it; E2 integration remains future work |
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

## Task 07B optional Requirements Interpreter

The [interpreter guide](REQUIREMENTS_AGENT.md) records the software implementation,
contracts, model support sources, configuration, mocked examples and limitations.
The official **openai 3.40.0** SDK is pinned. It uses `responses.parse` with
Pydantic Structured Outputs. Default model **gpt-5.4-mini-2026-03-17** and allowed
aliases/models have documentation-verified Responses/Structured Outputs support;
account access and live extraction accuracy have not been tested.

`RequirementsSchema` captures room type/shape, original lengths/units with source
quotes, furniture types/quantities/dimensions, doors/windows, style, hard/soft
preferences, ambiguity, assumptions and unsupported features. It is extraction
metadata; existing canonical Pydantic models are reused for the prepared design.
Python checks numeric/unit evidence and converts feet using 0.3048 m/ft.
Only sample-catalog queen bed, desk and wardrobe dimensions may fill omitted
furniture dimensions, with every default disclosed. Room/opening measurements
are not invented. Missing information returns `needs_clarification`; unsupported
furniture/shapes/rooms/additional hard constraints stop before generation.
Style and soft preferences are preserved without claiming generator enforcement.

The adapter is disabled by default (`ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS=0`).
Live use also requires exact per-call authorization, a verified model and an
environment API key. Codex CLI login provides no API authorization. One request,
zero retries, 30-second timeout, bounded input/output, no tools, fixed instructions
separate from user data, and typed sanitized failures keep the integration scoped.
No API credential value or raw provider error is returned/logged by the adapter.
No .env file is loaded automatically; only the placeholder template was updated.

LangGraph adds explicit `interpret_free_text=True` mode and forwards separate
`allow_live_requirements` authorization. Existing structured inputs bypass the
interpreter, and 07A prose metadata behavior remains the default. State adds the
typed interpretation result and necessary terminal/error statuses. Ready data is
reconverted and checked at the handoff; assumptions and retained preferences enter
the trace. Non-ready results terminate without generation. The other three nodes'
algorithms and all spatial/generator code are unchanged.

Actual offline CLI `python -m archimind.examples.interpret_bedroom` reports
**ready (offline_fixture)** → workflow **succeeded**, **2 candidates in 9/500
attempts**, selected index **0**. It uses a fixed mock client, temporarily scoped
fixture settings/key, and marks the result as offline with no claimed live model.
It is not a fallback for unavailable API calls. Full JSON reconstructs the typed
workflow state. The trace includes catalog assumptions followed by the existing
generated → approved → fixture-styled decisions.

Final local verification: **708 passed in 29.14s**, preserving all 631 prior tests
and adding 63 adapter/conversion plus 14 workflow integration cases. **27 frontend
tests passed**, syntax/build passed, and committed bundles were unchanged.
Editable installation and pip compatibility passed. Ruff lint/format passed.
Streamlit health returned **HTTP 200 ok**. Real SDK mock-HTTP
tests exercise schema serialization and successful/refused/incomplete/malformed
responses; network attempts are blocked in new tests. The offline CLI was executed.

Checkpoint A `e05cce8681599dbfde442a463c5b722079bf801b` was pushed to `origin/main`;
[GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40613614693).
The final checkpoint adds graph integration, the offline CLI, stronger SDK tests
and documentation. No live API/C01 request, new asset, dataset, UI redesign,
rendering change, spatial algorithm change or persistent store was introduced.
Unrelated `.agents/` and `.claude/` content remains untouched and uncommitted.

Limits: mock verification does not establish real-model semantic accuracy or
account availability. Evidence checks cannot prove intent/negation or detect every
omitted requirement. Catalog defaults are demonstration values; additional hard
constraints are unsupported, style/preferences are not enforced, and existing
spatial approximations do not establish vertical/ergonomic/code compliance.
The SDK buffers/parses before the application response-size check; it is not a
streaming memory quota. Live evaluation remains separate future work.

## Task 07C1 standalone Layout Designer advice

The [layout-advisor guide](LAYOUT_AGENT.md) records contracts, API gates, grounding,
actual demonstration output, tests and limitations. `LayoutAdviceRequest` reuses
canonical `RoomDesign` and `LayoutGenerationResult` plus bounded soft preferences.
`LayoutProposal` contains only a supplied index or abstention, controlled rationale
codes, known fact refs, subjective preference assessments and limitation codes.
The model cannot return geometry, scores or free-form measurement claims.
`LayoutAdviceResult` keeps a copied source context, checked proposal, Python-rendered
explanation, factual comparisons, subjective tradeoffs/unmet preferences and errors.

Read-only screening checks canonical identity/dimension preservation and calls the
existing accessibility API at zero tolerance for every candidate. Invalid,
unverified or mismatched reports reject the request before a model call; indices
are preserved. Shapely's existing footprints provide shortest planar distances to
canonical door/window segments on all four walls. Original scores/ratios and
usable-center area are also supplied. There is no regeneration or rescoring.

Fact refs must exist and belong to the proposed candidate. Measured rationale
codes must agree with actual extrema across supplied candidates: minimum cited
window gap, maximum cited door gap, or maximum usable-center ratio. A subjective
balance code allows tradeoffs without claiming metric optimality. Matching peer
facts are attached automatically; no model-supplied number enters the explanation.
Common unsupported daylight/ergonomic/certification requests must remain uncertain.
All judgments are advisory, and `requires_spatial_critic=True` remains explicit.

`ARCHIMIND_ENABLE_OPENAI_LAYOUT=0` is the default. Exact per-call authorization,
an environment API key and a supported model are also required. The adapter reuses
07B's client/model conventions: official SDK 3.40.0, Responses/Pydantic parse,
30-second timeout, zero retries, no tools/search, fixed endpoint and sanitized
failures. Request/context limit: 65,536 bytes; output: 4,096 tokens and 131,072
serialized bytes. At most two candidates, 32 furniture objects and 16 openings.
Disabled/unavailable advice never fabricates a recommendation.

Actual CLI `python -m archimind.examples.advise_layout` is **OFFLINE MOCK** only.
It generates the existing 5 × 4 m bedroom's two real alternatives, mocks a grounded
proposal, and recommends candidate **1 / Layout B**. Desk-to-north-window planar
gaps are **2.532114 m** (A) and **0.000000 m** (B). Original scores remain
**67.721925** (A) and **67.614973** (B); the lower-scored choice is explicitly
reported. Both candidate designs/reports remain unchanged. JSON round-trip and
environment restoration were verified. Daylight and ergonomics are not evaluated.

Final local verification: **773 passed in 31.03s**, preserving all 708 prior Python
tests and adding 65 focused cases. **27 frontend tests passed**; syntax/build,
Ruff lint/format, pip compatibility and Streamlit health (**HTTP 200 ok**) passed.
Committed frontend bundles were unchanged. Tests block network attempts, exercise
the real SDK with mock HTTP, and cover grounding, invalid candidates/selections,
abstention, unavailable/gated/error paths, immutability, deterministic mocks,
Requirements Interpreter compatibility and actual CLI JSON output.

No live OpenAI or C01 call, new dependency, workflow behavior change, UI/rendering
change, spatial/generation algorithm change, persistent store, asset or dataset
was introduced. The new module is not registered in LangGraph; its Layout Designer
node remains the original deterministic generator. Unrelated `.agents/` and
`.claude/` directories remain untouched and uncommitted.

Limits: mocked verification does not establish live model quality or account
availability. Rationale vocabulary and candidate set are intentionally small;
preference judgments cannot prove arbitrary intent. Planar gaps do not measure
daylight, ergonomics, actual minimum clearances, vertical collisions or code
compliance. The SDK buffers/parses before the application response-byte check.
Final spatial approval remains the independent Spatial Critic's responsibility.

## Task 07C2 workflow integration

[Developer guide](LAYOUT_WORKFLOW.md) records API/state, index mapping, routing,
gates, fallback, limitations and commands. The default four-node path remains
Requirements → Generation → Spatial Critic → Stylist. Explicit `use_ai_layout`
and the existing environment flag add the C1 advisor between critic and stylist.
Live API use additionally requires `allow_live_layout=True` and existing key/model
preflight. Disabled/unrequested advice invokes no adapter, including injected
callables. No live API or C01 invocation was made for this task.

One nested state contract records request/eligibility/execution, original choice,
proposed source index, checked C1 advice and failure reason; `selection_source`
distinguishes deterministic fallback from accepted recommendations. Existing
selected-index/design fields are preserved. Legacy JSON infers deterministic
defaults. Trace records eligibility, critique, proposal mapping, outcome and source;
offline fixtures are explicitly labeled. Bounds are one generation iteration,
four default/five optional nodes, recursion backstop 7, no duplicate edges or retry.

Only independently approved candidates enter the copied C1 packet. A local-to-source
index map handles filtering rejected alternatives. Original generation metadata,
scores, candidate geometry and authoritative critic reports are never overwritten.
The node reuses C1 context preparation and proposal interpretation, comparing the
full canonical context and grounded result to reject fabricated facts or outputs.
Abstention, unavailable/error responses and rejected recommendations preserve the
original deterministic choice only if its independent approval still matches.
With no safe candidate the workflow stops before selection/styling.

`python -m archimind.examples.advised_workflow` reuses C1's existing mock advisor
without regenerating inside the node. For the canonical 5 × 4 m bedroom, seed 42,
the default run selects A/index 0, score **67.721925**, in four nodes. The advised
run selects B/index 1, score **67.614973**, in five nodes, after critique. Desk gap
to the north window is **2.532114 m** versus **0 m**. Both runs retain identical
generation results and independent reviews; original input and JSON round-trips
are checked. The preference judgment does not certify daylight or ergonomics.

Baseline rerun: **773 passed in 34.94s**; **27 frontend tests passed**. Final local
verification: **823 passed in 30.75s**, preserving all 773 tests and adding 50 C2
cases. **27 frontend tests passed**; frontend syntax/build, Ruff lint/format,
dependency compatibility and Streamlit health (**HTTP 200 ok**) passed. Committed
frontend bundles remain unchanged. Tests deny network attempts and mock clients,
including actual C1 success/timeout handling, invalid/forged responses, all gates,
safe fallback, approved-only mapping, bounds, isolation/concurrency, old JSON,
Requirements Interpreter compatibility and real offline demo CLI execution.

Checkpoint A: `2adcae47ea3f0abcee4a3aafbf1e88b3f62f0675` contains the state,
node/routing and first 47 tests, verified at **820 passing tests** before push to
`origin/main`; [GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40618324526).
The subsequent documentation/demo checkpoint adds three CLI/demo
tests. Unrelated `.agents/` and `.claude/` remain untouched and uncommitted.

No dependencies, Streamlit/renderers, spatial/generation algorithms, C01, assets,
new agent, persistence or automatic geometry revision were added or activated.
Live quality/account availability is unverified; small candidate/rationale sets,
trusted-code DI and existing planar/spatial approximations remain limitations.

## Task 07D1 standalone AI Spatial Design Critic

[Developer guide](SPATIAL_CRITIC_AGENT.md) documents the API, contracts, grounding,
limits, failure handling and commands. `critique_design` embeds the existing C1
canonical packet and accepts optional designer advice and additional constraints.
Strict structured output contains controlled categories, candidate/object/evidence
refs, comparison relations, preference assessments and a recommendation stance.
Python renders at most three substantive observations and all measured values.

The critic reuses C1 independent candidate/report checks and opening metrics,
verifies scores with the existing deterministic helper, and adds Shapely wall-gap
and scoped spatial-check facts. Returned observations must match exact evidence,
objects and candidate order. Designer advice must equal C1's grounded output for
the same packet. Invented metrics, forged context/reports/scores, unsupported IDs
and inconsistent comparisons or recommendation stances are rejected.

Support/challenge is allowed only under a real comparative advantage of the
recommended/other candidate under a stated proxy. A challenge is not a spatial
violation. Preference tradeoffs need different categories favoring different
candidates. Unknown/unsupported judgments remain unverified; wholly unsupported
requests require abstention or an information request. Additional hard constraints
are retained but never certified by the advisory output.

`ARCHIMIND_ENABLE_OPENAI_CRITIC=0` is the default. Exact per-call live authorization,
the feature flag, validated/bounded inputs and existing key/model preflight are
required. The adapter reuses the fixed client/allowlist, 30-second request timeout,
zero retries, no tools, no storage/background execution and sanitized error patterns.
Inputs/context are each capped at 65,536 UTF-8 bytes; responses use the existing
4,096-token and 131,072-byte limits. SDK buffering precedes the byte check.

`python -m archimind.examples.critique_layout` runs the canonical 5 × 4 m bedroom,
seed 42, through the unchanged default graph, then invokes C1 and D1 mocked
adapters outside it. The critic supports B's **0 m** desk/window gap versus A's
**2.532114 m**, while retaining A's higher score **67.721925** versus **67.614973**
and usable-space ratio **0.596524064171** versus **0.595187165775**. Actual daylight,
ergonomics, furniture usability, code compliance and full preference satisfaction
remain unverified. The workflow selection remains A/index 0, designer proposal B/index 1;
all candidate geometry/scores/reports are preserved and JSON round-trips pass.

Checkpoint A: `80cde69fa103ddcc35deb117da0e0024a3e57ad0` contains the schemas,
grounding, adapter and first 93 offline tests;
[GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40619689170).
The example/documentation checkpoint adds CLI/demo and mixed usability coverage.

Verification: baseline rerun **823 passed in 31.43s**, with **27 frontend tests**
passing. Final local run **920 passed in 43.30s**, preserving all 823 cases and
adding **97 critic tests**. The 27 frontend tests, frontend syntax/build,
editable `.[dev]` installation, Ruff lint/format, pip compatibility and real
Streamlit health (**HTTP 200 ok**) all passed. Committed frontend bundles are
unchanged. Checkpoint A CI verified **916 tests in 58.79s** and 27 frontend tests.
Tests prohibit network attempts and use mocked clients, including actual SDK
mock-HTTP parsing, typed provider errors/refusals, input/context limits,
grounded support/challenge, forged reports/scores/evidence/recommendations,
unsupported/mixed usability judgments, abstention/information requests,
immutability, JSON, existing-agent compatibility and actual offline CLI execution.

No live OpenAI or C01 call, new dependency, geometry-generation algorithm, model,
LangGraph routing, Streamlit/rendering change, asset, dataset, persistence or revision
loop was introduced. Unrelated `.agents/` and `.claude/` remain untouched.
Live model quality/account availability, general preference interpretation and
architectural suitability are not established by mocks; existing spatial and
small candidate/rationale-set limitations still apply.

## Task 07D2 optional workflow critique

[Workflow critic guide](SPATIAL_CRITIC_WORKFLOW.md) records API/state, routes,
mapping, gates, fallback, limits and commands. The default path remains four nodes.
Advisor-only and critic-only modes use five nodes; enabling both uses six, ordered
Requirements → Generation → Deterministic Critic → Advisor → AI Critic → Stylist.
Each routing node has only conditional outgoing routing, avoiding duplicate
execution. One generation iteration, a six-node bound and recursion backstop 8
limit execution; no retry or revision loop is introduced.

One nested `SpatialCritiqueState` records opt-in, execution/status, reviewed source
index, packet mapping, checked D1 result and failure reason. Existing selection
fields remain authoritative and old JSON defaults to no critique. D1's request
adds optional `reviewed_candidate_index=None` to explicitly focus on the selected
local candidate without fabricating a designer recommendation. Normal critique
must cite target evidence; abstention/information requests may lack conclusions.

Only independently approved candidates enter the copied D1 packet, reusing the
C2 filtering/mapping helpers. Original IDs, coordinates, geometry, scores and
deterministic reports are preserved. Accepted C2 advice is passed exactly; skipped,
abstained, rejected or failed advisor responses are omitted. Context/result must
match existing D1 preparation and interpretation. Bad refs, targets, facts,
provenance or explanations are rejected and retained as sanitized typed failures.
Deterministic violations and unknown checks remain visible in original reviews.

Support, challenge, information requests, abstention and safe failure all retain
the selected candidate and source. The AI critic node has no selection-update
code path; only metadata/trace updates. With no safe independent selection it
terminates. Subsequent styling failure preserves critique history while clearing
final approval. Trace distinguishes deterministic approval, optional advice,
critic execution/stance/provenance, final unchanged selection/source and styling.

Live critique requires `ARCHIMIND_ENABLE_OPENAI_CRITIC=1`, `use_ai_critic=True` and
exact `allow_live_critic=True`, plus D1 key/model/input preflight. Disabled or
unrequested critique calls no adapter, including DI. The two AI feature flags
are independent. Offline DI stays explicitly labeled, with model `None`. D1's
provider handling, limits and no-tools/client configuration are reused.

`python -m archimind.examples.critiqued_workflow` uses the canonical bedroom and
seed 42 with factored existing C1/D1 mocked clients. Scenario A selects A/index 0,
score **67.721925**, in four nodes with no AI invocation. Scenario B selects B/index 1,
score **67.614973**, in six nodes with support for its **0 m** desk/window gap versus
A's **2.532114 m**. Scenario C records a grounded challenge using A's actual higher
score and usable-space ratio, but still selects B with the same score in six nodes.
All scenarios retain identical candidate geometries/scores and deterministic
reviews. Input immutability, environment restoration and JSON round-trips pass.

Verification: baseline **920 passed in 33.81s**, plus **27 frontend tests**.
The demonstration checkpoint passed **984 tests in 36.81s**. The 27 frontend tests, syntax/build, Ruff lint/format, pip
compatibility and real Streamlit health (**HTTP 200 ok**) passed. Frontend bundles
are unchanged. The prior C2 bound assertion now checks its five-node execution
against D2's expanded six-node maximum; no original test was removed.

Checkpoint A `631321b00c76711f13a385eb26fb274da1d9311c` contains state, routing,
integration, backward-compatible target scoping and the first 58 cases, verified
with **978 tests in 39.18s** before push;
[GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40622683656).
The demonstration/documentation checkpoint adds six demo/independent-flag/styling
failure cases. Tests block networking and use mock clients, including actual D1
adapter success/timeout, all paths/counts, support/challenge/abstention/errors,
forged data, safe fallback, filtered indices, no selection change, old JSON,
free-text compatibility, isolation/concurrency and actual offline CLI execution.

Checkpoint B `3f4bc30f1694c79c977e173bdf70ce747941a3ca` contains the demo and
documentation; [GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40623105874).
Final hardening adds fresh selected-geometry verification before critic invocation
and before continuing, using the existing accessibility API. Stale passing reports
cannot permit unsafe fallback if both source/approved copies are altered. A failed
fresh check clears final selection and accurately retains actual adapter execution
with a typed invalid-candidates result. Two new tests cover alteration before
invocation and during an error response; **66 D2 tests** now preserve all 920
baseline cases for **986 total tests**. The focused suite passed in **6.09s**.
Final full local verification passed **986 tests in 39.20s**, with Ruff lint/format,
pip compatibility and real Streamlit health (**HTTP 200 ok**) passing again.

No live OpenAI/C01 request, new agent/dependency, geometry/generation algorithm,
score change, furniture modification, UI/renderer change, asset, dataset or
persistent storage was introduced. `.agents/` and `.claude/` remain untouched and
uncommitted. Remaining limits include unverified live quality/account access,
trusted-code DI, conservative preference vocabulary and inherited planar/spatial
approximations. No daylight, ergonomics, furniture-function or code certification
is established by these tests or mocks.

## Task 07E1 standalone Interior Stylist

[Stylist guide](INTERIOR_STYLIST_AGENT.md) documents the request/proposal/plan,
catalog, validation, failure behavior, commands and rendering boundary. The adapter
accepts exactly one caller-selected `LayoutCandidate` with its canonical design,
original report/score, stated style, 0–8 soft preferences and optional checked
critique. It has no selection API. Geometry is independently rechecked with the
existing accessibility API, the entire report must match, and the existing score
helper verifies the original score. Optional critique must be genuine grounded
D1 output concerning this exact candidate and any explicit local review target.

Catalog `archimind_style_v1` provides five themes/palettes: Scandinavian,
Modern, Minimalist, Industrial and Neutral. Frozen records, immutable mappings
and tuple allowlists define 15 wall/floor/furniture representations and six accent
colors. Model output contains one theme/palette, compatible wall/floor tokens,
exact existing furniture IDs and at most three distinct accents, plus controlled
rationale/conflict/assessment codes. Python resolves all fixed hex values and
explanations. Unknown IDs, wrong surfaces/palette combinations, paths/code,
invented measurements/performance claims and hidden recognized conflicts fail.

Style metadata is separate from `RoomDesign`. A plan has a furniture-ID-keyed
finish map, preference notes, unmet indices, conflicts, assumptions and limitations.
Preference notes are subjective; multiple named themes require compromise or
clarification. Known performance/spatial-improvement requests remain unverified.
Missing main style details produce explicit non-evaluated clarification without
a client. Failed/unavailable requests never fabricate an AI style plan.

Material/accent records expose future flat-color metadata and
`physical_asset_available=False`; the plan has `rendered=False`. No texture,
material asset, component mapping, physical specification, actual rendering or
performance evidence is supplied. No claim of improved verified circulation is
made. LangGraph routing, its deterministic Stylist fixture, canonical models,
geometry/generation algorithms, Streamlit and both renderers remain unchanged.

`ARCHIMIND_ENABLE_OPENAI_STYLIST=0` is the default. Live use requires the flag,
exact per-call `allow_live_usage=True`, valid bounded data and existing key/model
preflight. The existing SDK/client, endpoint/allowlist, 30-second timeout, zero
retries, no-tools policy and sanitized errors are reused. Input/context each have
a 65,536-byte cap, responses use 4,096 tokens and a 131,072-byte application cap;
SDK buffering precedes that check. No new client wrapper or dependency was added.

`python -m archimind.examples.style_bedroom` uses the canonical 5 × 4 × 2.7 m
bedroom and independently approved Layout A/index 0, seed 42, score **67.721925**.
The mocked plan selects `scandinavian` / `scandi_warm_sage`, warm white walls
(`#F5F1E8`), light oak floor (`#D4B58C`), `finish_light_oak` (`#CDB18A`) for desk,
queen bed and wardrobe, and muted sage accents (`#9BAE98`). Complete candidate,
geometry, coordinates, validation, scores, selected index and workflow JSON remain
identical. The four-node fixture workflow and environment are preserved; output
is labeled `offline_fixture`, model `None`, without rendered/physical-asset claims.

Verification: baseline **986 passed in 42.49s**, plus **27 frontend tests**.
Final local run **1,075 passed in 49.32s**, preserving all 986 cases and adding
**89 stylist tests**. Frontend **27/27**, syntax/build, Ruff lint/format, pip
compatibility and real Streamlit health (**HTTP 200 ok**) all passed. Committed
frontend bundles are unchanged. Tests block network attempts, mock clients and
exercise real SDK mock-HTTP parsing, all themes, catalog/ID/compatibility rules,
conflicts, unsupported claims, input validity/limits, authorization/errors,
immutability/JSON, existing-agent compatibility and actual offline CLI output.

Checkpoint A `05863b81d95d61d07b5dd113bc79a07afeb093b6` contains the four modules
and first 86 cases, verified with **1,072 tests in 46.67s** before push;
[GitHub Actions passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40624916653).
The demo/documentation checkpoint adds three actual CLI/environment-restoration
cases. Source archive and wheel builds passed; contents include the four modules,
demo, source tests and guide, with no secrets/caches/unrelated directories. A wheel
installed into an isolated temporary target ran the mock demo outside the repository
under isolated Python, with its import location verified. Temporary artifacts were
removed; no generated package output is staged.

No live OpenAI or C01 request, new asset/dataset, physical material rendering,
LangGraph integration, persistent storage, chat or automatic revision was added.
Unrelated `.agents/` and `.claude/` remain untouched/uncommitted. Live quality/account
availability, general intent matching and physical performance are unverified.
The small catalog, one finish per object and existing spatial limits still apply.

## Next milestone

**Task 07E2 — Optional Interior Stylist workflow integration** is recommended next,
preserving selected canonical geometry and deterministic approval. It is not implemented here.
Task 06E2 rendering refinements, rotated-footprint
support, furniture editing, persistence and export remain separate future work.

For setup, local commands, coordinates, and renderer usage, see the
[project README](../../README.md).
