# Project status

## November 28 Town home editor

A saved Town home now supports edits to loose furniture, shared gallery partitions and finishes. The client can reopen adjacent revisions at a bookmarked room camera, compare them with a wipe, and render that camera locally in Blender. The local photo importer connects two to four rectangular rooms with user-confirmed dimensions and matched thresholds. The intake rehearsal used synthetic source photos.

The furniture walkthrough verified its modeled 90 cm route and reopened all five edited revisions in Walk. The salon comparison used the same 1176 × 720 camera in Town and Cycles. [Editor walkthrough and screenshots](../data/milestone7/README.md) · [Rendering receipt](../data/milestone7/cameras/salon-town-cycles.json) · [Photo-home rehearsal](../data/milestone7/photo-home/README.md)

## November 28 demo and field work

The November 28 single-home rehearsal used a fresh six-room project. Town returned two validated designs in 16.5 seconds. In the selected Layout B, the modeled kitchen-to-salon route measured 7.99 m, down from 12.87 m in A. The bedroom-to-bathroom route increased from 3.72 m to 14.12 m. The saved chair edit moved its footprint 300 mm and increased the measured gap to the Belaya desk from 60 mm to 360 mm. [68-second film](https://github.com/ngstephen1/ArchiMind/releases/download/town-photo-studio-demo-2026-11-28/ArchiMind-One-Home-Live-Design.mp4) · [Live run and both snapshots](https://github.com/ngstephen1/ArchiMind/issues/70#issuecomment-7235520471)

The film replays all 35 recorded agent events. The edit was repeated on a copy and reproduced the full original revision 2. The new project reused the November 24 bedroom geometry. One live image edit of its desk camera took 24.1 seconds and proposed a rug, framed art and brass lamp. Use the saved model for clearances. On the local Apple M5 laptop, High and Low both measured 16.7 ms median frame time on the same 30-second route. Venue projector performance awaits an on-site check. [Recording receipt](https://github.com/ngstephen1/ArchiMind/issues/119#issuecomment-7235849191) · [Camera and finish study](https://github.com/ngstephen1/ArchiMind/releases/download/town-photo-studio-demo-2026-11-28/Town-Revision-2-Photographic-Study.zip) · [Laptop timing](https://github.com/ngstephen1/ArchiMind/issues/70#issuecomment-7235633196)

The [73-second captioned walkthrough](https://github.com/ngstephen1/ArchiMind/releases/tag/town-photo-studio-demo-2026-11-28) was captured from `35d5ecc`. The new local project saved a 300 mm chair movement between revisions 1 and 2. The recorded photographic redesign and the earlier agent run each have their own source. A clean download matched the published video checksum and decoded all 1,825 frames. [Goal and issue tracker](https://github.com/ngstephen1/ArchiMind/issues/119)

The [current-bedroom field sheets](../handovers/current-bedroom/Bedroom-Field-Visit-Sheets.pdf) are ready for an observer to record the shell, openings, desk underside and chair clearances. The surveyed-room work still needs a dated visit. The public Town site currently serves a static tour. [Survey intake #92](https://github.com/ngstephen1/ArchiMind/issues/92) · [Hosted configuration check](https://github.com/ngstephen1/ArchiMind/issues/66#issuecomment-7235267388)

The delegated decision approved both demo films and held the November 30 designer release. A clean download verified all 32 entries in the separate November 24 home’s handoff. Its revision 2 presentation now opens the matching package after GitHub sign-in. The original two-owner rehearsal and release freeze remain tracked. [Release decision](https://github.com/ngstephen1/ArchiMind/issues/71#issuecomment-7235896626) · [Rehearsal and package access](https://github.com/ngstephen1/ArchiMind/issues/70#issuecomment-7235754337)

## November 22–30 release sprint

As of November 25, **14 of the original 19 issues are closed**. Milestones 2
through 5 are at 5/5, 6/7, 3/4 and 0/3 respectively. The
archived bedroom finish comparison met the material and window-detail
criteria at 1080p. [Sprint tracker](https://github.com/ngstephen1/ArchiMind/issues/54) ·
[Archived finish comparison](../data/nov24-baseline/layered-finish)

A fresh Town browser run used the live provider and returned two validated
whole-home alternatives. Layout A was saved as revision 1. Revision 2 moved
the bedroom chair by 0.300 m and increased its plan gap to the desk from
0.060 m to 0.360 m. Both revisions also reopened in a provider-free Chrome
replay. The live receipt identifies the exact code tested.
[Fresh run, saved inputs and local replay commands](../data/nov24-fresh-live#reopen-both-revisions)

The delegated revision review on `512ed26` verified both saved homes,
the 300 mm chair move, the matched renders, and ten replayed chatbot answers
at desktop and narrow widths. The rebuilt designer handoff passed all 32
checksum-listed files. The revision review and designer handoff issues are closed.
[Delegated review](https://github.com/ngstephen1/ArchiMind/issues/67#issuecomment-7106415558) ·
[Verified rehearsal handoff and checksums](../data/nov24-fresh-book) ·
[Portable replay and launch commands](../data/nov24-fresh-live#rehearse-from-the-portable-download)

Hieu approved the held-out evaluation at five passes and one partial. The
original cases ran at `301762b`, and three affected cases were rerun at
`45871da`. H06 had a medium-severity saved-explanation defect on that evaluation. A subsequent delegated browser check passed on the saved-answer branch while preserving the original scores. [Affected-case replay](https://github.com/ngstephen1/ArchiMind/issues/68#issuecomment-7235638192). The
evaluation issue is closed. The combined implementation fixes dining
requirements, preserves unsupported clearances for clarification, and verifies
the serving Town instance in new evaluation runs.
[Evaluation sign-off](https://github.com/ngstephen1/ArchiMind/issues/68#issuecomment-7153331714) ·
[Combined Town PR](https://github.com/ngstephen1/ArchiMind/pull/114)

The artifact upload upgrade is merged. Both the Town browser and real Blender
queue artifacts downloaded and unpacked under their existing names on PR CI.
[Artifact upgrade](https://github.com/ngstephen1/ArchiMind/pull/113)

Both owners' [rehearsal](https://github.com/ngstephen1/ArchiMind/issues/70),
the [release freeze](https://github.com/ngstephen1/ArchiMind/issues/71) and
[publication](https://github.com/ngstephen1/ArchiMind/issues/72) remain open.
Residential design development is at four of six issues. The current survey
and surveyed-bedroom visual checks still require field measurements.
[Residential milestone](https://github.com/ngstephen1/ArchiMind/milestone/6)

The public Vercel walkthrough serves static content. Managed design-service
acceptance remains open. [Hosted scope and prior launch commands](CONFERENCE_REPLAY.md)

## Historical implementation status

Last reviewed: **November 5, 2026**.

**November 17 branch addition — 3D Studio.** The separate
`feat/spoken-world-3d-studio` workspace adds concept-only furnished bedrooms,
living rooms and home offices using bounded declarative primitive recipes.
Offline examples and a gated Structured Outputs provider adapter are implemented.
An authorized four-request backend smoke produced three custom recipes and two
validated alternatives; actual Three.js geometry checks passed. Full live-UI
acceptance remains pending. The qualified catalog,
dataset eligibility gates and 09A workflow keep their existing contracts.
See [3D Studio](3D_STUDIO.md) and its [verification receipt](../data/3D_STUDIO_10A.json).
The November 5 milestone below is historical context for the existing chatbot.

**November 18 branch addition — photoreal style packs (11A).** Five styles
(modern classic, industrial loft, Scandinavian, Japandi, mid-century) with released
CC0 surfaces, HDR lighting, measured CC0 furniture models, decor, plan themes, a
Quality toggle and a Plan ↔ Room sweep in Studio and Town. Homes saved before the
feature render as before (0.51% pixel difference against `main`, all in the new
footer control). 21 original Blender signature pieces (beds, sofas, desks,
storage, pendants, a tripod lamp) are released across the packs; frame-rate
acceptance is pending.
See [Style packs](STYLE_PACKS.md) and the [receipt](../data/STYLE_PACKS_11A.json).

**Current milestone: Task 09A live conversation-to-layout acceptance passed;
1,927 Python tests and installed-wheel/lint/dependency/health checks pass.
Final checkpoint CI/delivery is recorded in the 09A report.** Three newly authorized
requests all completed: a desktop complete request and a two-turn narrow-screen
clarification. Each produced two passing seed-42 alternatives for its custom room,
with native Belaya and an explicitly accepted queen-bed placeholder. Pending
choices and New conversation retain displayed results; reset keeps input usable.
No further API requests are authorized by this smoke budget. Offline, live,
AppTest and fault-harness evidence remain distinct in
[the 09A report](../data/CHAT_BEDROOM_09A.md#current-09a-continuation).
Use `scripts/run_chat.py` for local opt-in chat. No asset generation was added.
The earlier 3.32 GiB storage stop is preserved as historical evidence. In the
resumed run, the owner's continuation instruction makes 4 GiB advisory, with
supervised verification requiring 2 GiB and a retained 1 GiB absolute reserve.

**Prior release: R3C_RELEASE_VERIFIED.** Release `a38a2e1` passed CI with
1,867 Python and 91 frontend tests. Five metadata-qualified catalog products;
Charles and Belaya have individual approved Policy B/native-render releases.
Mixed Charles/Belaya scenes remain placeholders.

Other live OpenAI behavior is unverified; the separate local CPU encoder experiment is measured below. Full material editing and Task 06E2 remain separate future renderer work; Charles and Belaya use their original embedded source materials.
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
| Task 07E2 — Interior Stylist workflow integration | Complete backend; live behavior unverified | Optional final E1 node, fresh approval, separate checked plan/provenance and safe explicit fixture fallback; 61 new integration/demo tests |
| Task 07F — Streamlit styling panel | Complete UI/backend; live behavior unverified | Stored selected-layout E2 handoff, catalog theme/preferences, per-attempt consent, explicit fixture/AI provenance and 55 new tests |
| Task 09A — Chat bedroom | Live and local acceptance verified; see delivery receipt | Evidence-grounded room clarification, five-product lexical retrieval, explicit selection/Prepare/Review and synchronized validated A/B generation |
| Later phases | Planned | Agents, targeted revisions, persistence, and export |

## Capability status

| Capability | Current support | Boundary |
| --- | --- | --- |
| Room representation | One rectangular room in meters | No arbitrary room polygons or multiple-room plans |
| Openings | Wall-relative doors and windows | Schema checks wall endpoints and ceiling limits; hinge/swing information is not modeled |
| Furniture data | IDs, names, categories, positions, dimensions, and right-angle rotations | Data can represent overlaps and out-of-room objects |
| Schema validation | Strict types, finite numbers, positive dimensions, opening extents, and design-wide unique IDs | Does not establish spatial validity |
| 2D rendering | Walls with opening gaps, blue windows, gold door spans, furniture footprints, and labels | Only zero-rotation furniture; unsupported rotations raise `ValueError` |
| Interaction | Generate button, seed, A/B selector and explicit catalog Select → Prepare → Review → Generate | One instance per catalog product; no arbitrary furniture editor |
| Sample data | Fresh 5 × 4 × 2.7 m bedroom with a south door, north window, bed, desk, and wardrobe | Manually specified demonstration, not an optimized or spatially validated layout |
| JSON | Model serialization and reconstruction | No project-save UI or revision database |
| Spatial checks | Backend containment, furniture overlaps, door approaches, and circulation for rotation 0 | Separate from renderer; rectangular/square approximations, no swing or vertical checks |
| Validation reports | Unchanged Task 04A API plus combined Task 04B report; typed JSON, errors/warnings, per-check results, and overall passed/failed/unverified | Unsupported/unevaluated required checks cannot pass; supported violations remain visible |
| Layout generation | Backend and Streamlit expose up to two distinct validator-approved alternatives with deterministic seeds/scores and validation summaries | Rotation zero; manual or reviewed catalog reservations; no global-optimality claim |
| Session state | Results and selection survive normal reruns; generation and acceptance checks run only on button click | Refresh/disconnect may clear results; no database persistence |
| 3D structure | Floor, four zero-thickness walls, real door/window gaps, optional blue glazing, and orbit/zoom/pan | No 3D furniture, ceiling slab, reveals, or synchronization with selected layouts |
| 3D furniture | Bed frame/mattress/pillows, desk tabletop/legs, wardrobe/plinth/panels/handles, and generic solids | Rotation 0 only; at most 100 items; generated selection and separate fixed sample; no rendering-based validity claim |
| Selected 2D/3D views | Both renderers receive the same stored candidate design | Selection does not generate or spatially revalidate; Three.js camera/controls persist within one room/DOM owner across A/B |
| Experimental realistic room | Selected candidates plus separate samples; native Charles or Belaya with explicit current evidence | Rotation zero; mixed real-product scenes unqualified; other products use placeholders; legacy viewers retained |
| Export | Not implemented | No GLB, CAD, or BIM integration |
| Workflow orchestration | Default requirements → generation → deterministic critique → fixture; independent optional advisor, critic and E1 styling; selected-styling UI entry point | Full graph stays separate; UI never regenerates or invokes other roles; no persistence/revisions |
| Requirements interpretation | Optional OpenAI Responses API with structured extraction and canonical conversion | Disabled by default; explicit per-call authorization/key required; only rectangular bedrooms/studios and a three-item furniture catalog; verified with mocks only |
| Layout recommendation | Optional standalone C1 adapter and C2 post-critic workflow handoff | Default-off; only critic-approved candidates, Python-grounded facts and safe deterministic fallback; no UI connection or live verification |
| AI design critique | Standalone D1 adapter and optional D2 workflow node review the approved selected candidate | At most three grounded observations; challenge/failure cannot change selection or deterministic approval; no UI integration or live verification |
| Interior style planning | Optional standalone E1 adapter and E2 final graph node return checked catalog colors/finishes for one approved selected candidate | Separate appearance metadata; no material rendering, physical assets or performance certification |
| Workflow stylist | Deterministic fixture by default; independently gated E1 plan or explicit safe fixture fallback | Original geometry/score/reports/selection preserved; unsafe selections rejected; mock/API/fixture provenance explicit |
| Streamlit styling panel | Optional section after selected-layout validation, with fixture action, catalog themes/palette preview and preference text | AI disabled by default; server flag plus one-request authorization and click required; A/B/input changes clear results; no rendered materials |
| Catalog-color preview POC | Opt-in wall/floor/furniture tint on existing selected Plotly 3D meshes | Accepted bound catalog plan required; no geometry changes, textures, new assets or accent placement; fixture fallback stays untinted |
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

## Task 07E2 optional final workflow styling

[Workflow stylist guide](INTERIOR_STYLIST_WORKFLOW.md) documents the additive
`DesignRequest.style_request`, `AIStylingState` and conditional final E1 handoff.
The existing `interior_stylist` node remains the default fixture. An authorized
`ai_interior_stylist` replaces it on checked success; safe failure runs the fixture
afterward with explicit provenance. One generation iteration and a seven-node
maximum (recursion backstop 9) cover advice, critique, attempted styling and fallback.

Styling requires `use_ai_stylist=True`, existing flag
`ARCHIMIND_ENABLE_OPENAI_STYLIST=1`, and exact per-call
`allow_live_stylist=True`, including trusted offline injection. Disabled or
unauthorized requests do not invoke the AI node. Other roles retain independent
opt-ins and gates. `ai_styling.result` reuses E1's checked result/plan; its mode and
model distinguish mock/API provenance. AI success leaves legacy fixture `styling`
empty. Fallback preserves the typed error/clarification result and labels both
style-source fields `deterministic_fixture`; it never invents an AI plan.

Before and after invocation, the existing validator reruns at zero tolerance and
the original score is verified through the existing helper. E2 compares full
authoritative workflow data and retains the original selection, room/openings,
furniture IDs/coordinates/dimensions/rotations, scores, reports and prior advice.
E1 grounding verifies exact context, immutable catalog values, ID coverage and
canonical explanations. A stale, invalid, unverified or changed selection stops
without an approved design; a fixture cannot rehabilitate unsafe geometry.
Strict JSON round-trips retain E1 catalog tuples and legacy fixture provenance.

`python -m archimind.examples.styled_workflow [--json]` demonstrates A: default
fixture, B: explicitly mocked Scandinavian `scandi_warm_sage` plan, and C:
simulated timeout with labeled fixture fallback. A and B execute four nodes, C
five. All retain Layout A/index 0, original score **67.721925**, complete geometry
and reports. The E1 mock was extracted into a reusable example helper receiving
an existing candidate, with no regeneration or live-client fallback. Its original
standalone CLI remains compatible. No demo option can enable a live request.

Actual baseline: `main` at `2b93cc1`, synchronized with origin, **1,075 passed in
41.32s**. Checkpoint A `5c83c30` passed **1,133 tests in 45.02s** locally and
[GitHub Actions](https://github.com/ngstephen1/ArchiMind/actions/runs/40627621163)
passed **1,133 in 84.22s**, frontend 27/27 and health 200.

Final local verification: **1,136 passed in 49.79s**, preserving all 1,075 previous
cases and adding **61** workflow/demo cases. The combined E1/E2 focused run passed
**150 tests in 7.53s**. Ruff lint and formatting (**97 files**) passed; `pip check`
reported no broken requirements; Streamlit health returned **HTTP 200**.
Frontend **27/27** tests, syntax and production build passed, with no rendering
bundle differences. Existing workflow, interpretation, advice, critique and E1
demo CLIs plus the E2 CLI passed in text/JSON modes; the generation CLI returned
valid JSON with its expected completion summary on stderr.

Source archive and wheel builds passed with the new workflow module/demo,
integration tests and guide present in their appropriate distributions. No
secrets, unrelated agent directories, virtual environment, caches or node modules
were included. Installed-wheel A/B/C and strict JSON ran outside the repository
with DNS/socket connections and real-client creation blocked. Temporary package
artifacts were removed. MANIFEST includes the new workflow guide.

No canonical model, generator, spatial algorithm, app or renderer was modified.
No dependency/provider, live OpenAI/Codex request, material application, chat,
revision, persistence or separate course write-up was added. The existing small
catalog and spatial assumptions remain. All AI quality/account availability is
unverified; appearance metadata is not realistic rendered material. Unrelated
`.agents/` and `.claude/` remain untouched and uncommitted.

## Task 07F selected-layout Streamlit styling panel

The [panel guide](INTERIOR_STYLIST_WORKFLOW.md#task-07f--streamlit-selected-layout-panel)
documents the new optional section after the selected layout's validation summary.
The UI offers the existing neutral fixture without a key, and independently gated
AI styling with catalog theme selection, palette preview and bounded preference
text. The current one-palette-per-theme catalog is reused; no competing theme,
palette, material or styling implementation was added.

Public `style_selected_layout` accepts an existing generation and original selected
index, reuses deterministic spatial critique and E2's guarded final steps, and
returns `WorkflowState`. `selection_source="user_selection"` records the actual
caller choice without pretending it was ranking or AI advice. The original
deterministic/advisor source rules remain enforced. Trace contains only actual
verification/styling, generation iteration count stays zero, and no layout search
or other AI role executes. Complete generation data and source indices are retained.

Fresh checks verify geometry, specification, reports, config and score before AI
or fixture approval; original reports/scores are compared, never replaced.
Accepted E1 plans remain separate metadata. Typed failed/clarification results
retain explicit safe fixture fallback; an unsafe selection gets no approved style.
AI assistance starts unchecked. Server enablement, independent per-request consent
and an explicit button click are required; authorization is consumed before
invocation and reset for retries. Raw provider errors, credentials and environment
values are not displayed. No environment file is loaded or changed by the panel.

Separate session state binds style results to original specification/generation,
selected index and inputs. A/B changes, successful regeneration, missing/unverified
selections and styling-input changes clear results and consent. A failed generation
keeps the preceding result/selection/style; a pending seed edit does not replace
the displayed generation. In-flight/submission guards prevent duplicate work.
Ordinary reruns and selection/input changes make no styling or spatial-validation
calls. Existing renderers still receive the actual stored selected design object.

Verification preserved all **1,136** baseline cases and adds **55** selected-layout
and UI tests. Checkpoint 1 `973bd84` passed **1,149 in 54.50s** locally and
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40636687904).
Checkpoint 2 `b413ab8` passed a **149-test focused regression run in 39.02s** and
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40637050304).
Final local suite: **1,191 passed in 63.60s**. Ruff lint/format (**100 files**),
`pip check` and Streamlit health **HTTP 200** passed. Frontend **27/27**, syntax
and build passed; committed rendering bundles are unchanged.

All eight existing workflow/agent demo CLIs passed in text/JSON modes; the original
generation CLI returned valid JSON and its expected completion summary. Source
archive and wheel builds include the new UI/handoff modules and appropriate tests,
app and guide. Installed-wheel A/B fixture and mocked-AI requests, strict JSON and
panel AppTest passed outside the repository with networking/real clients blocked.
No secrets, unrelated agent directories, environment, caches or node modules were
packaged. Temporary distribution artifacts were removed.

Actual browser inspection at **1440 × 1000** and **390 × 844** checked the fixture,
catalog controls, disabled AI configuration, readable labels, selected-layout
association, consent reset and A/B stale-result removal. A separate temporary
wrapper with real-client creation blocked verified the successful mocked E1 plan
at both widths, explicitly labeled `offline_fixture`. No horizontal page overflow
or application console error was observed. The existing non-fatal Plotly Canvas2D
readback advisory remains. The furniture table uses its normal internal horizontal
scroll at narrow widths. Screenshots are outside the repository in
`/Users/macbook/Hack/.playwright-mcp/`: `task07f-desktop.png`, `task07f-mobile.png`,
`task07f-mock-desktop.png` and `task07f-mock-mobile.png`; none is committed.

No canonical model, spatial algorithm, generator, renderer, rendering bundle,
dependency, new agent, asset or material application was changed/added. No live
OpenAI/Codex request or separate course write-up was performed. Existing small
catalog, zero-rotation and single-room limitations remain; real model quality,
account availability, conversational input, persistence and material rendering
are unverified/unimplemented. Pre-existing `.agents/` and `.claude/` remain untouched.

## Catalog-color mapping proof of concept

[Preview guide](STYLE_COLOR_PREVIEW.md) documents `render_styled_design_3d` and the
new **Preview catalog colors in selected 3D view** checkbox. The optional adapter
starts from the original furnished Plotly figure and changes only wall/floor and
furniture colors plus a separate preview metadata record. The checkbox starts
off and can restore the original view. It is offered only for accepted E1/E2
catalog plans; fixture/fallback output cannot invent a plan or activate it.

Strict output/catalog validation, exact source `RoomDesign` equality, furniture
ID coverage and explicit mock/API provenance are required. The rendering step
does not run AI, generation or the spatial validation engine; workflow approval
remains authoritative. Source models, scores, complete reports, vertices,
triangles, room/opening gaps, IDs, dimensions, camera, ranges, aspect ratio,
lighting, opacity, hover and legend stay unchanged. The original metadata plan
retains `rendered=False`; the new figure records its preview separately.

Every part of a furniture object receives its one finish color, including bed
pillows/mattress and wardrobe handles. Component finishes, textures and PBR are
not implemented. Glass/opening outlines retain their existing appearance and
accents remain unplaced metadata. The 2D, standalone and experimental Three.js
views are unchanged. A/B changes, new generation, input changes and new requests
clear the preview. Old/malformed plans revert safely to the original 3D view.

The baseline at `480af08` passed **1,191 in 75.77s**. The new suite adds **28**
cases: all themes/both candidates, exact figure preservation except colors,
catalog/provenance/ID rejection, stale-layout rejection, source immutability,
no backend work on preview changes, reversal/reset and offline exports. Focused
tests: **28 passed in 11.14s**. Full suite: **1,219 passed in 82.51s**, preserving
all prior tests. Ruff lint/format, pip dependency check and Streamlit health
**HTTP 200** passed. Frontend **27/27**, syntax and build passed with unchanged
committed rendering bundles. No dependencies, canonical models, layout/scoring
or spatial algorithms were changed.

`python -m archimind.examples.preview_style_colors --output output/style-color-preview.html`
exports a self-contained, explicitly **OFFLINE MOCK** preview using the existing
mock client. Its assertions preserve Layout A/index 0 and score **67.721925**,
geometry/camera and full workflow/advice data. All nine workflow/agent/preview
examples passed text/JSON checks. Source/wheel contents and installed-wheel
offline preview assertions passed outside the repository with network and real
clients blocked; temporary package artifacts were removed.

Actual browser inspection at **1440 × 1000** and **390 × 844** verified catalog
colors, unchanged camera metadata, reversal and clearing on Layout B, with no
horizontal page overflow or application console error. The existing non-fatal
Plotly Canvas2D advisory remains. Verification used a temporary mock-only app with
real-client construction blocked. Screenshots and exported HTML are outside the
repository in `/Users/macbook/Hack/.playwright-mcp/archimind-color-preview/`.
The implementation checkpoint is `c51984b`; generated artifacts are not committed.

No live model requests, new assets, dataset integration, training or separate
course write-up occurred. Existing constructed room layouts remain the data
source. `.agents/` and `.claude/` remain untouched and uncommitted.

## Task 08B — qualified, embedding-ready furniture metadata

The [08A source register](../data/FURNITURE_SOURCE_REGISTER.md) qualifies two ABO
product records for acquisition investigation. The independent `archimind.assets`
package now represents both as metadata-qualified records in the versioned
`archimind-furniture` catalog (`1.0.0`, schema `1`). The [workflow guide](WORKFLOW.md#qualified-furniture-metadata--task-08b)
documents the public API, qualification boundaries and future retrieval contract.

| Product | Canonical category / subtype | W × D × H (m) | Rendering |
| --- | --- | --- | --- |
| Stone & Beam Charles, Sod | chair / armchair | 0.9906 × 0.9906 × 0.9652 | Not qualified; no acquired GLB |
| AmazonBasics five-shelf bookcase, Espresso | storage / bookcase | 0.659892 × 0.381762 × 1.891792 | Not qualified; no acquired GLB |

Strict frozen records preserve original measurements, Decimal-checked conversions,
explicit axes, source evidence/snapshot hashes, identities/variants and CC BY 4.0
rights/attribution. Unknown dataset revision is distinct from the known 08A
qualification commit. Published dimension claims are not independent physical
measurements. Missing/uncertain evidence, duplicate keys/IDs, category/variant
conflicts, unsafe render references and unsupported approval claims fail closed.

`load_catalog()` reads only a fixed packaged resource. The canonical furniture
factory creates fresh zero-rotation specifications, with no placement, validation,
score changes or modification of stored designs. Ordinary app/workflow behavior,
geometry, renderers and Streamlit controls remain unchanged.

Deterministic search documents contain reviewed names, categories/subtypes,
aliases, usage, variants and IDs. Original marketing titles stay in provenance;
description/material/style/color fields remain unknown. No style or physical
color is inferred from the names Sod/Espresso. Future index keys include catalog,
record and text versions plus a text digest. No embeddings, retrieval service,
new agent, database, dependency or live model request is introduced.

Both render qualifications remain `not_evaluated`; verified mesh bounds,
orientation, anchors, local paths, bindings and model hashes are null. Source
conventions are reported, not inspected. The original Sheen Chair remains an
independent illustrative fixture. Bed, desk and wardrobe coverage is still absent.

Verification commands are in the workflow guide. Catalog tests cover offline
validation/factory boundaries and match the frozen 08A evidence. The separate
packaging regression builds source/wheel artifacts offline, verifies catalog and
existing-asset bytes, installs the wheel without dependencies/network and loads
it outside the repository. No source data or historical audit evidence is changed.

Task 08B local verification: **85 catalog tests + 1 packaging regression passed**
(86 focused cases in 3.48s); full suite **1,305 passed in 80.69s**, retaining all
1,219 baseline tests. Ruff lint/format (111 files), `pip check`, frontend
syntax/build and committed-bundle equality passed; frontend **27 passed, 0 failed,
0 skipped**. Streamlit health returned HTTP 200 `ok`. The catalog checkpoint
`ec646ac` also passed [CI](https://github.com/ngstephen1/ArchiMind/actions/runs/40761660929).
No live provider/Codex requests, embeddings or asset downloads were used.

## Task 08C — inspection complete; Charles rendering blocked

The [qualification report](../data/ASSET_QUALIFICATION_08C.md) and paired JSON
record one authorized Charles GLB acquisition into external quarantine. Received
bytes: **4,252,440**, SHA-256
`62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645`.
Primary identity, variant, item dimensions and CC BY 4.0 release terms were
revalidated. Actual decoded W/D/H are **0.9961048961 × 1.0019413233 ×
0.9760930538 m**, independently cross-checked using Three.js. The model passes
the 2%/1 cm agreement check but exceeds the canonical envelope by **5.50 / 11.34 /
10.89 mm**. Strict containment at **1e-6 m** fails. No product mesh is approved,
packaged or served; the model was not resized and canonical dimensions are intact.

The new offline `archimind.assets.inspection` module and
`scripts/inspect_furniture_assets.py` inspect bounded static embedded GLBs without
downloads or rendering approval. Synthetic tests cover malformed data, actual
bounds, transforms, strict containment, resource budgets and sanitized failures.
The immutable 08B catalog remains schema/version **1 / 1.0.0**, with its historical
render fields null; the separate receipt records the rejection. Sheen, A/B views,
generation, geometry, UI and renderer code remain unchanged.

A temporary external fixture used explicit `None` bindings: two Charles-sized
boxes and a desk, **0 textured meshes and 0 GLB loads**. Desktop 1440 × 1000 and
narrow 390 × 844 inspection confirmed framing, orbit/zoom/reset, controls and
openings with no console errors/warnings. Narrow in-scene labels overlap; the
object list is readable. This does not verify product appearance or image
decoding and is not physical-phone testing. Screenshots stay outside Git.

Final local suite: **1,380 passed in 80.12s** (all 1,305 prior cases plus 75 new
inspection cases). Source/wheel and isolated installed-inspector regression passed.
Frontend **27 passed, 0 failed, 0 skipped**; syntax/build and committed bundle
equality, Ruff lint/format, dependency compatibility and Streamlit HTTP 200 health
checks passed. See the qualification receipt for exact commands and limitations.

## Task 08C-R1 - explicit planning-envelope contract

The owner-approved backend Policy B now keeps published product measurements,
inspected mesh bounds and planning reservations separate. The [guide](PLANNING_ENVELOPES.md)
documents strict immutable schemas, fixed packaged metadata, pinned source/receipt
digests, current catalog/version checks and an explicit fresh-specification factory.
Original catalog bytes and `furniture_from_catalog` behavior are unchanged.

Charles's new reserved W/D/H are **0.996104896068573 x 1.0019413232803345 x
0.9760930538177491 m**. Exact corner checks establish native-scale containment under
the recorded floor/center anchor, with only deterministic outward numeric rounding.
No 2% margin, functional clearance or visual calibration is inferred. Factory
results contain a new canonical item and immutable evidence binding; they do not
replace stored layouts, run generation or claim spatial validity.

There are **97 new offline envelope tests**, covering authority, hashes, versions,
axes/anchors, strict containment, invalid metadata, immutable sidecars and the
unchanged old factory, candidates, reports and scores. Source/wheel and isolated
installed-package checks include the reference metadata and actual new factory.
Final local verification: **1,477 passed in 80.71s**, preserving all 1,380 baseline
cases and adding 97 envelope cases. Frontend **27 passed, 0 failed, 0 skipped**;
syntax/build and unchanged-bundle checks passed. Ruff lint/format (119 files),
`pip check`, Streamlit HTTP 200 health, source/wheel builds and isolated installed
factory/resource loading passed. No GLB acquisition, new render qualification,
Policy C, retrieval, UI change or live model call occurred.

## Next milestone

Review Task 08C-R1 before separately authorizing **08C-R2 native-scale rendering
qualification**. Charles has sufficient backend envelope evidence for that next
investigation, but real bytes/decoded bounds, front/materials/image decoding,
runtime placement/resources, private desktop/narrow review and safe renderer
bindings still require approval. No product is render-qualified; **08D remains
blocked**. Bookcase acquisition/preparation is still deferred, including its
4096 px textures and source-dimension/configuration questions.
Conversational input remains unimplemented.
Task 06E2 rendering refinements, rotated-footprint
support, furniture editing, persistence and export remain separate future work.

For setup, local commands, coordinates, and renderer usage, see the
[project README](../../README.md).

## Task 08C-R2 — first native-scale real product

The official Charles/Sod B075X2X4XS GLB was freshly retrieved alone, verified at
4,252,440 bytes / SHA-256 `62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645`,
and approved in a separate digest-bound render release after actual desktop and
narrow Chromium inspection. Original published dimensions, catalog/planning
snapshots, geometry, A/B generation/selection, scores, Plotly and AI are unchanged.

The experimental selector now offers a fixed two-Charles/desk-placeholder room
using V3 ID/version/envelope bindings, fixed local bytes, streaming integrity
checks, actual decoded bounds/material/image verification and unit scale only.
The illustrative V1/V2 Sheen scenes retain fitting behavior. Budgets are unchanged;
two Charles instances share one source, 67,108,860 estimated texture bytes and
85,412 product triangles. Eight instances trigger all-product placeholders before
any load. Missing/corrupt assets are explicit and recover on a later remount.

Full integration verification: **1,507 Python tests passed in 88.78s**, including
all 1,477 baseline cases; **68 frontend tests passed**, no failures/skips. The
source/wheel and isolated installed-package regression has been extended to
verify the approved Charles file, notices, metadata and V3 path while preserving
the catalog's SDK-free import check. The existing renderer imports optional
styling SDK types; provider construction/network/process work remain blocked in
the installed render check. Final verification: **1,507 passed in 86.21s**, **68 frontend passed**, Ruff lint/format (129 files), pip compatibility, health HTTP 200, exact bundle/registry, offline packaging and isolated installed product checks passed. Full evidence is in the paired R2 report.

See [qualification receipt](../data/ASSET_QUALIFICATION_08CR2.md) and
[product rendering guide](CHARLES_PRODUCT_RENDERING.md) for exact data, files,
local commands and limitations. Browser setup times are observations, not device
benchmarks. No physical phone, calibrated color, independent metrology, sustained
GPU-memory/FPS or architectural certification claim is made.

08D may be separately scoped to explicit compatible planning-sized specifications
and safe placeholders. No automatic binding/resizing of current A/B items is
implemented. Bed, desk and wardrobe models remain unqualified; the bookcase is
deferred for 4096 px textures. No further assets, embeddings, new agents or
dataset pipeline were acquired or implemented.

## Task 08D — selected canonical layout in Three.js

The 3D selector now offers **Plotly schematic** (default) or **Realistic Three.js**,
while the 2D floor plan remains visible. Every active view receives the actual
stored candidate. No render action generates, spatially validates, rescores or
calls AI. Camera/cutaway settings survive A/B changes within the same room;
identical reruns keep the same scene. New successful generation advances the
render revision and replaces stored product evidence; failure preserves the
previous result, selection and render context. Styling safeguards are unchanged.

The default bedroom's three items lack explicit product evidence and remain
labeled placeholders. Charles requires its immutable planning sidecar and current
qualified release; dimensions/category alone cannot select it. The separate
Charles fixture retains its factory sidecars, passes the real accessibility
validator and caches only its report/fingerprint per session. Its two native-scale
meshes share one source geometry; missing/corrupt responses safely fall back and
recover after reopening. No new model was acquired.

Final local results: **1,556 Python tests passed in 94.81s**; **75 frontend tests
passed**, zero failures/skips. Ruff lint/format (137 files), dependencies, health
HTTP 200, source/wheel packaging, isolated installed adapter/asset checks, registry
projection and unchanged-bundle verification passed. All 1,507 baseline tests are
preserved; the existing smoke assertion's development-phase label was updated to
08D. New tests cover identity/evidence, A/B and pending inputs, failures, empty
results, separate sessions, fixture gating, lifecycle and camera behavior.

Actual Chromium desktop 1440×1000 and resized 390×844 inspections confirmed
canonical agreement, readable labels, controls, placeholders and recovery. The
347 px component has no horizontal overflow. Normal rendering had zero unexpected
console errors and the existing Plotly advisory; one intentional HTTP 404 was
recorded during fault injection. Source hot-reloading during development produced
one stale-class session error; the final checks used a clean server with fixed
source. Physical phones and sustained device performance remain unverified.

See [selected-layout guide](SELECTED_REALISTIC_LAYOUTS.md) and
[verification receipt](../data/SELECTED_LAYOUT_08D_VERIFICATION.json) for exact
interfaces, browser data, screenshots, file inventory and checkpoint CI links.
08E may now be scoped to explicit catalog-sized specifications and compatible
choices before generation. Bed/desk/wardrobe coverage, bookcase texture limits,
and a broader rights-cleared catalog remain gaps. No 08E controls, retrieval,
embeddings, new AI functionality or dataset integration were implemented.


## Task 08E — reviewed catalog inputs and generation

The default procedural path remains one-click. Optional catalog selection retains
or removes manual bed/desk/wardrobe inputs and adds at most one Charles armchair
and one Espresso bookcase. Preparation is pure schema/evidence work; explicit
Generate confirms the reviewed input. Published item claims, Charles's Policy B
reservation and current mesh approval have separate labels. Empty reviewed inputs
are supported with an honest single-distinct-arrangement limitation.

Submitted source JSON, product provenance and sidecars are frozen with the
revision/digest-bound generation snapshot. Pending inputs and seed changes do not
replace current results or matching styling; styling uses that stored source.
Exceptions preserve prior context; all normal outcomes replace it, even zero
candidates. Compatible Charles mesh/placeholder choices persist across A/B and
reset on replacement. Bookcase remains a storage placeholder, not a wardrobe.
Plotly is still default; 08D camera/lifecycle and exact candidate handoff remain.

No canonical geometry, validator, generator, scoring, catalog/search evidence,
render release, GLB, Three.js source/bundle or dependency changed. No acquisition,
embedding, retrieval index or live AI work was performed. This is two curated
ABO records with one approved mesh, not dataset-wide integration.

See [the workflow guide](FURNITURE_CATALOG_UI.md) and
[08E verification receipt](../data/CATALOG_GENERATION_08E_VERIFICATION.json) for
exact local checks, browser evidence, file inventory and checkpoint CI. Historical
08A–08D results below/above retain their original scope and counts. Stop after
08E; larger catalogs and dataset-grounded generation require separate review.

08E final local verification: **1,581 Python tests passed in 123.42s** (25 new
tests; all 1,556 prior tests preserved), **75 frontend tests passed, 0 failed or
skipped**. Ruff lint/format (143 files), pip compatibility, registry/bundle
equality, Streamlit HTTP 200, asset integrity and offline source/wheel/isolated
installation checks passed. Browser views were inspected at 1440×1000 and
390×844; screenshots are outside Git. First two checkpoints have green CI; the
final commit/CI links are reported in the delivery response.


## Task 08R0 — offline retrieval contract and evaluation

New backend-only `archimind.retrieval` contracts/provider return stable qualified
IDs, current evidence and explainable reasons. Hard gates cover identities,
versions, rights, verified attributes/functions, dimensions and qualification.
Default bounds use actual 08E generation reservations. Published-only fact finding
cannot pass the preparation handoff without an explicit different intent.
Stale/current source checks never repair or mutate prior layouts.

The Python lexical baseline and optional in-memory SQLite FTS5 comparison use
reviewed search text only. There is no persistent production database, embedding,
model download, AI call or UI/LangGraph wiring. Existing canonical geometry,
generation/scoring, rendering and 08E state are unchanged. The application's phase
label therefore stays 08E. Future retrieval consumers must still prepare/review
and explicitly generate through that existing API.

Benchmark: 38 real queries (20 positive, 17 negative, one version check) over two
ABO products; 24 separately reported synthetic queries over eight artificial
products. Both real methods: recall/MRR/NDCG@2 0.90, P@2 0.475 with fixed-k
precision, category 2/2, hard violations 0/19 and unauthorized IDs 0/19. Two real
paraphrases are missed. Synthetic mechanics do not inflate real effectiveness;
judgments are agent-authored with no independent human adjudication.

See [architecture](FURNITURE_RETRIEVAL_ARCHITECTURE.md),
[baseline findings](../data/RETRIEVAL_BASELINE_08R0.md) and the accompanying JSON
receipt for exact metric denominators, failure cases, local CPU timings, source
references, replay commands and delivery checkpoints. Final verification is
recorded after execution; a separate bounded 08R1 encoder benchmark and 08F source
qualification are recommendations, not tasks executed here.

Final 08R0 local verification: **1,688 Python tests passed in 108.64s**, including
107 new retrieval checks and all 1,581 prior tests; **75 frontend tests passed,
zero failures/skips**. Ruff (155 formatted files), dependencies, health HTTP 200,
bundle/registry equality and offline source/wheel/isolated-install checks passed.
The 124 protected baseline production/frontend/catalog/dependency files are
byte-identical. The first two checkpoints have green CI; final release CI and
commit identity are reported in the delivery response. Stop after 08R0.


## Task 08R1 — offline semantic and hybrid benchmark

One official FastEmbed representation of BAAI/bge-small-en-v1.5 ran locally on
Apple M1 CPU only. No weights or vectors enter the package; no new default
dependency, UI, generator, geometry, styling, asset or catalog/search-document
change. Derived indices bind exact current source and model evidence. Source
resolution stays mandatory before any future specification preparation.

Development and held-out splits were frozen before real inference, authored by
the implementation agent with no independent human adjudication. The real 0.75
threshold was sealed before test scoring. Original real recall: BM25/FTS5 .90,
frozen cosine .35, RRF .90. Held-out real recall: .125, .0, .125 respectively.
Raw cosine found all real positives but produced 4/17 original and 4/8 held-out
negative-query false positives. Frozen synthetic/hybrid also produced 1/6 held-out
negative-query false positives. Hard filters/leakage remained zero in observed
outputs; those checks do not certify relevance. All results remain provisional.

[Full findings](../data/RETRIEVAL_EMBEDDING_08R1.md) and the paired JSON preserve
per-query results, frozen policy/model/corpus identities, resources and recovery
notes. Keep exact NumPy for offline experiments. No measured case for Chroma or
pgvector exists. Human-reviewed abstention and expanded qualified furniture
coverage precede unrestricted 08R2. No 08R2/08F work was started.

Final local release: **1,754 Python tests passed in 117.49s**, including 173
retrieval tests (66 new, all 1,688 baseline tests retained); **75 frontend tests**
passed. Ruff lint/format (171 files), default/experiment dependency checks,
Streamlit HTTP 200, registry/integrity, unchanged bundle, offline source/wheel
builds and outside-repository installed-wheel loading passed. No model is needed
for CI. Final commit/CI identities are reported in the delivery response.


## Task 08F1 — source expansion and owner-review preparation

The source register now has **57 records**, retaining all 32 historical records
and adding 25. Thirty detailed product/domain investigations produced **3 new
acquisition-eligible source leads, 19 needs-evidence and 8 exclusions**. The new
shortlist is Movian Belaya desk B074L4976T, Movian Morava wardrobe B07H8JN9QF and
Rivet nightstand B07B4VXXJC. No bed qualifies. Seventeen of the 30 reviewed records
have checked published-dimension contracts; that is not 17 validated models.

The entire 08A candidate JSON is preserved byte-for-byte in a frozen research
snapshot. The existing catalog test retains its original assertions against that
snapshot; new tests validate the expanded register. Active catalog/search text,
planning envelopes, releases, renderer assets, geometry, UI and frozen 08R0/08R1
results remain unchanged: **two packaged products, one planning-qualified and one
render-qualified product (Charles)**. New source leads do not enter the application.

Research received **9,948,621 metadata bytes**, below 10 MiB, with at most 1 MiB per
response. Thirty model HEAD requests read zero bodies. No assets, images, textures,
archives, dependencies or encoders were acquired. The three new leads meet individual
source/resource screens, but their combined reported texture estimate is 192 MiB,
above the existing 128 MiB scene limit. Actual decoding, placement and any approved
reservation require later inspection, not silent fitting or relaxed budgets.

The [24-prompt owner-first packet](../data/FURNITURE_RETRIEVAL_HUMAN_REVIEW_08F1.md)
contains blank judgments and no model scores. Completed human reviews: **zero**.
Source-only/prospective discussion is separate from current-application eligibility.
A future category-contract/catalog admission review is justified before separately
authorized asset qualification, with Belaya first. No 08F2, acquisition, embeddings
or 08R2 work was started. See [full evidence and limits](../data/FURNITURE_EXPANSION_08F1.md).

Final local release: **1,781 Python tests passed in 125.07s**, preserving all 1,754
baseline tests plus 27 new source/evidence tests; **75 frontend tests passed**.
Syntax/build, bundle equivalence, Ruff lint/format (174 files), dependency checks,
registry/asset integrity, Streamlit HTTP 200, source/wheel builds and isolated
installed-wheel checks passed. Checkpoints 1 and 2 passed CI; final delivery
identities and CI are reported in the response.


## Task 08F2 — versioned metadata-only catalog admission

Schema 2 / catalog 1.1.0 admits exactly Belaya B074L4976T, Morava B07H8JN9QF and
Rivet nightstand B07B4VXXJC, using the unchanged 08F1 identity/license/dimension
receipts. Published W/D/H are 1.6/0.8/0.75 m, 2.0/0.59/2.12 m and
0.6096/0.4318/0.6096 m. These are checked published claims. Variant labels do not
qualify physical colors/materials. None has an approved mesh or planning envelope.

The original two-product 1.0.0 release is retained byte-for-byte. Charles/bookcase
record bodies and search text, approved Charles assets/releases, canonical geometry,
scoring and frontend bundles are unchanged. Existing 08E controls discover five
products; explicit preparation/generation uses current evidence and preserves
active candidates under pending edits. Three new products generate two passing
alternatives in 8 attempts; adding Charles and the procedural bed takes 102,
under the unchanged 500-attempt budget. These checks are not design certification.

Historical retrieval providers/CLI scope preserve frozen two-product results;
current resolution rejects stale historical hits/vectors. No encoder ran, no new
benchmark was evaluated, and the 24-prompt owner packet remains blank. The active
five-product catalog has no measured retrieval effectiveness. See the
[admission report](../data/FURNITURE_CATALOG_ADMISSION_08F2.md) for exact release
checks, screenshots outside Git, preservation pins and delivery evidence.

Belaya can proceed to a separately authorized individual acquisition/qualification
review. Morava's reported height mismatch and the three assets' combined reported
192 MiB texture estimate need later inspection; the 128 MiB scene limit stays.
No bed qualifies. No acquisition, new planning proof, render approval, embeddings,
dependency, database or AI agent is included in 08F2.

Final local release: **1,817 Python tests passed in 136.62s** (36 new; all 1,781
baseline cases retained), **75 frontend tests passed**, zero failures/skips.
Syntax/build/bundle equality, Ruff lint/format (177 files), dependency checks,
registry/asset integrity, Streamlit HTTP 200 and offline source/wheel/isolated-install
verification passed. A disk-exhaustion attempt is retained in the report; these
numbers are from the fresh successful rerun. Checkpoints 1 and 2 have green CI;
final commit/CI identities are in the delivery response. Stop after 08F2.


## Current checkpoint — 08F3A workflow through R3B5

Belaya uses its approved Policy B reservation, exactly **1.6 × 0.8018731772899628
× 0.7516312003135682 m**, instead of silently falling back to published dimensions.
Current sidecars/releases govern admission. Charles remains supported; bookcase,
Morava and nightstand remain metadata-only. No catalog, asset bytes, geometry,
scoring, validation rule, scene budget or frozen retrieval judgment changed here.

R3B5 verified two actual Generate clicks in one Streamlit session, revision 1 → 2,
generator count 1 → 2 and UI validation count 2 → 4. Both results contain two
passing seed-42 alternatives in five attempts; deterministic content matches while
the stored result object is new. Plotly/native Three.js synchronize with the exact
selected objects. Pending edits preserve results and require fresh preparation.

The R3B3 lifecycle correction retains camera/control snapshots under a stable DOM
owner. Actual A/B navigation passes; new generations and new owners reset defaults.
Restoring pending controls can replace an owner, so view persistence across every
possible rerun is not claimed. The generated Belaya GLB hash matches its approved
release, at native scale 1.0. Mixed Charles/Belaya scenes remain explicitly unqualified.

Evidence: [qualification report](../data/ASSET_QUALIFICATION_BELAYA_08F3A.md).
R3B4 passed 57 focused Python and 18 lifecycle tests; R3B3 previously passed 82
focused frontend tests and reproducible bundle checks. R3B5 required no code/test
rerun and recorded zero browser errors, one Plotly advisory and no storage warning.
These are bounded acceptance results, not production or architectural certification.

The owner authorized committing/pushing accumulated work after R3B5. Current
delivery checks and GitHub CI are reported with the commit; older green CI does
not certify this new snapshot. R3C reconciliation is recorded below. No new asset, dependency, encoder, retrieval integration or AI
agent is included. Historical milestone sections above describe their own checkpoints.


## R3C — Current release reconciliation (November 5, 2026)

**R3C_RELEASE_PENDING_DELIVERY_CI** at commit time. The existing narrow prototype
is supported by exact baseline CI (1,867 Python / 91 frontend tests), retained
offline source/wheel and isolated-install checks, installed fail-closed binding
checks and HTTP 200 health. All 30 R3B5 evidence-manifest entries reverified.
The final delivery response reports the new commit’s actual CI result; successful
baseline CI is never attributed to another SHA. No browser matrix was repeated.

The [current release evidence](../data/ASSET_QUALIFICATION_BELAYA_08F3A.md#r3c-final-reconciliation--november-5-2026)
preserves the initial and interrupted storage stops. Its JSON `current_release`
points to the current verdict; original top-level blocked fields describe October
30 only. Same-owner A/B camera continuity and explicit same-session regeneration
are verified within their recorded evidence boundaries. New owners reset the view.

Five ABO products remain in the catalog, with individual native approval for
Charles and Belaya only. Their mixed detailed scene remains unqualified and uses
placeholders; Morava, nightstand and bookcase remain metadata-only. No full verified
live-AI design journey, production semantic retrieval, arbitrary rotation,
nonrectangular/multi-room design, CAD/BIM export or production/device certification
is claimed. Published product dimensions remain source claims.

This continuation changes only release docs and mechanical preservation-chain
tests. Owner-first review of the existing 24-prompt relevance packet is the next
recommended product task; no new asset or feature work started.


## Confirmed R3C delivery

**R3C_RELEASE_VERIFIED** for release commit
`a38a2e121d66c5a755cf9fe5fed8a4e3dfc4db6c`.
[Delivery CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/42127832828):
**1,867 Python tests, 91 frontend tests**, lint/format, dependency compatibility,
viewer build/bundle equality and HTTP 200 health. The preceding pending-CI text
records the state when that commit was created; this addendum records the result.
The current JSON verdict is at `r3c.delivery_followup`, leaving historical events
intact. Prototype limitations above continue to apply.
