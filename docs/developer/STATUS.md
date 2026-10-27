# Project status

Last reviewed and locally verified: **October 27, 2026**.

**Current milestone: Task 05A complete — deterministic furniture layout generation.**
Task 05B is recommended next. The UI remains at the Task 03 preview.

## Milestones

| Milestone | Status | Delivered behavior |
| --- | --- | --- |
| Task 01 — Foundation | Complete | Editable Python package, local environment, Streamlit screen, smoke tests, and CI |
| Task 02 — Core data models | Complete | Typed room, door, window, furniture, and design models; strict schema validation and JSON round-trips |
| Task 03 — 2D floor plan visualization | Complete | Reusable Plotly renderer, reproducible bedroom factory, Streamlit preview, and coordinate-based tests |
| Task 04A — Containment and collisions | Complete | Zero-rotation Shapely footprints, containment, all-pair overlaps, scoped JSON reports, and geometry tests |
| Task 04B — Door clearance and paths | Complete | Configurable rectangular door approach checks, bounded polygon circulation connectivity, explicit check states, and 69 new tests |
| Task 05A — Deterministic furniture layout generation | Complete | Bounded seeded placement, validator-backed alternatives, reproducible scores, bedroom CLI, and 52 new tests |
| Task 05B — Expose generated alternatives in Streamlit | Recommended next | Not implemented |
| Later phases | Planned | 3D, agents, targeted revisions, persistence, and export |

## Capability status

| Capability | Current support | Boundary |
| --- | --- | --- |
| Room representation | One rectangular room in meters | No arbitrary room polygons or multiple-room plans |
| Openings | Wall-relative doors and windows | Schema checks wall endpoints and ceiling limits; hinge/swing information is not modeled |
| Furniture data | IDs, names, categories, positions, dimensions, and right-angle rotations | Data can represent overlaps and out-of-room objects |
| Schema validation | Strict types, finite numbers, positive dimensions, opening extents, and design-wide unique IDs | Does not establish spatial validity |
| 2D rendering | Walls with opening gaps, blue windows, gold door spans, furniture footprints, and labels | Only zero-rotation furniture; unsupported rotations raise `ValueError` |
| Interaction | Hover details, panning, scroll zoom, and equal X/Y metric scale | No editing or generated-alternative controls in the UI |
| Sample data | Fresh 5 × 4 × 2.7 m bedroom with a south door, north window, bed, desk, and wardrobe | Manually specified demonstration, not an optimized or spatially validated layout |
| JSON | Model serialization and reconstruction | No project-save UI or revision database |
| Spatial checks | Backend containment, furniture overlaps, door approaches, and circulation for rotation 0 | Separate from renderer; rectangular/square approximations, no swing or vertical checks |
| Validation reports | Unchanged Task 04A API plus combined Task 04B report; typed JSON, errors/warnings, per-check results, and overall passed/failed/unverified | Unsupported/unevaluated required checks cannot pass; supported violations remain visible |
| Layout generation | Up to two distinct validator-approved RoomDesign alternatives; local seeds, attempt limits, deterministic score components, and JSON | Backend only; rotation zero; fixed dimensions; no LLMs or global-optimality claims |
| 3D / export | Not implemented | No 3D viewer, GLB, CAD, or BIM integration |
| Agents / API | Not implemented | No LangGraph or OpenAI calls; no API key required |

## What the app currently shows

The original branding, Foundation metric, and planned-capabilities section remain
intact. The **2D Floor Plan Preview** beneath them displays the canonical sample
bedroom. The Foundation label is preserved UI content, not the current project
milestone; the current backend milestone is Task 05A. The UI has not been wired to
the spatial engine or generator, and the caption continues to describe the demonstration UI.

The preview caption explicitly states:

> Demonstration layout — spatial validation and automatic placement are not yet implemented.

The animated isometric README header is concept artwork. The live app's actual
rendering is a top-down 2D Plotly chart.

## Verified baseline

| Component | Version |
| --- | --- |
| Local CPython | 3.11.13 |
| Streamlit | 1.66.1 |
| Pydantic | 2.14.1 |
| Plotly | 7.1.0 |
| Shapely | 2.2.0 |

Local verification for this milestone:

- `python -m pytest -q`: **369 passing tests**, preserving all 317 previous cases
  and adding 52 generation/scoring/search-result/example tests.
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
  preservation of the original design. The UI, renderer, and canonical models are unchanged.
- Task 04B covers all four walls, both wall endpoints, every door blocker,
  advisory-only warnings, strict zone contact, barriers, narrow passages, alternate
  routes, multiple/no doors, unsupported rotations, work limits, numeric precision,
  configuration validation, deterministic reports, JSON round-trips, and no mutation.
- Task 05A covers validated alternatives, dimensions/identity preservation,
  containment, zero-tolerance overlaps, door/circulation checks, same/different
  seeds, input-order independence, no global random-state changes, unchanged and
  independent inputs, scores, advisory penalties, budget limits, infeasibility vs
  exhaustion, empty requests, unsupported features, JSON, CLI, and rendering.

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
without changes. The UI remains unchanged.

Measured locally with Python 3.11.13, ten function calls per case (imports and
rendering excluded; these are observations, not CI timing thresholds):

| Case | Outcome / attempts | Median | Observed range |
| --- | --- | --- | --- |
| Bedroom, seed 42 | 2 candidates / 9 | 0.006529 s | 0.006423–0.011673 s |
| Bedroom, seed 7 | 2 candidates / 15 | 0.012595 s | 0.012558–0.012655 s |
| Two 3 × 2.5 m objects in 5 × 4 m | Search exhausted / 500 | 0.143187 s | 0.142380–0.146941 s |
| Four 3 × 2 m objects in 5 × 4 m | Excess area / 0 | 0.000059 s | 0.000055–0.000074 s |

The exhausted search returned at its configured limit; no unbounded retry loop
is used. Cost increases with item count and attempt budget.

GitHub Actions uses one Linux/Python 3.11 job with one dependency installation for
Ruff lint/format checks, `pip check`, all 369 tests, and a real Streamlit health
check. It runs for PRs targeting main, pushes to main, and manual dispatches.
The redundant OS/Python matrix, separate quality/build jobs, distribution/archive
checks, clean-wheel installation, and artifact uploads were removed from routine
CI. Manual builds remain available; deployment is not configured. See the
[workflow results](https://github.com/ngstephen1/ArchiMind/actions/workflows/ci.yml)
for the result of a particular commit.

## Next milestone

**Task 05B — Exposing Generated Alternatives in the Streamlit UI** is recommended
next. It is not implemented here. Rotated-footprint support, 3D, and agents remain
separate future work.

For setup, local commands, coordinates, and renderer usage, see the
[project README](../../README.md).
