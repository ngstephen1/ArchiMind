<p align="center">
  <img src="docs/assets/archimind-hero.svg" alt="ArchiMind AI — Multi-Agent Interior Design and 3D Spatial Planning. Task 06B: interactive 3D furnished room. Animated architectural concept illustration." width="100%" />
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="docs/assets/python.svg" alt="Python" height="36" /></a>
  <a href="https://streamlit.io/"><img src="docs/assets/streamlit.svg" alt="Streamlit" height="36" /></a>
  <a href="https://docs.pydantic.dev/"><img src="docs/assets/pydantic.svg" alt="Pydantic" height="36" /></a>
  <a href="https://docs.pytest.org/"><img src="docs/assets/pytest.svg" alt="pytest" height="36" /></a>
  <a href="https://docs.astral.sh/ruff/"><img src="docs/assets/ruff.svg" alt="Ruff" height="36" /></a>
</p>

<p align="center">
  <strong>Thoughtful spaces. Structured foundations.</strong><br />
  An interior design research prototype built one verified layer at a time.
</p>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="docs/developer/STATUS.md">Project status</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#models-and-coordinates">Models</a> ·
  <a href="#quality-checks">Quality checks</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

---

## Overview

**ArchiMind AI** is an ADS 5984 software project exploring how natural-language
room requirements can become validated floor plans and interactive 3D interiors.

The long-term direction is a multi-agent design assistant. The current release
includes a working Streamlit screen, typed architectural data, strict schema
validation, an interactive 2D sample floor plan, and a reproducible developer workflow.

| **Define the space** | **Trust the data** | **See the plan** |
| :--- | :--- | :--- |
| Describe one rectangular room, its doors, windows, and furniture. | Validate dimensions, IDs, containment, collisions, doors, and circulation. | Generate two seeded bedroom alternatives and compare their scores, coordinates, and 2D plans. |
| Available now | Available now | Interactive sample available |

> **Current stage · Task 06B — Interactive 3D furniture visualization**
>
> Generate and select bedroom alternatives in Streamlit, inspect their coordinates
> and heuristic scores, and review their spatial validation reports. The original
> Task 03 sample preview remains available, alongside structural and furnished
> 3D sample previews with real wall openings. Placement is deterministic seeded
> search; layout synchronization, AI reasoning, persistence, and export remain planned.
> **No API key is required.**

Tasks **01–03, 04A, 04B, 05A, 05B, 06A, and 06B are complete**. The
[project status record](docs/developer/STATUS.md) lists milestone progress,
capability boundaries, and the verified baseline. The current local suite contains
**528 passing tests**: all 485 previous cases plus 43 furniture/scene/integration cases.

The header is an original concept illustration, not an application screenshot or a
generated design.

## Quick start

### 01 · Create the environment

Use **Python 3.11+**. The local environment was configured with **CPython 3.11.13**
using `/opt/homebrew/bin/python3.11`.

```bash
cd /Users/macbook/Hack/ArchiMind
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Create `.venv` once. For an existing environment, activate it and reinstall after
dependency changes. The editable `src/` package imports without setting `PYTHONPATH`.

### 02 · Open the application

```bash
python -m streamlit run app.py
```

Open the printed Local URL, normally **http://localhost:8501**. Stop with
`Control-C`.

### 03 · Verify the foundation

```bash
python -m pytest -q
python -m pip check
```

<details>
<summary><strong>macOS, VS Code, and later terminal sessions</strong></summary>

The recorded interpreter resolves to
`/opt/homebrew/opt/python@3.11/bin/python3.11`. Ensure `python3.11` is available on
your PATH when creating a fresh environment.

For later sessions:

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python --version
```

In VS Code, select `${workspaceFolder}/.venv/bin/python` as the interpreter.

To launch without opening a browser:

```bash
python -m streamlit run app.py --server.headless true --server.address 127.0.0.1
```

</details>

## 2D floor plan preview

Launch the app and scroll to **2D Floor Plan Preview**. The sample contains a
5 × 4 × 2.7 m bedroom, a south-wall door, a north-wall window, a queen bed, desk,
and wardrobe. Wall gaps show openings; doors use gold dotted spans, windows use
blue spans, and furniture has readable labels and hover details.

Drag to pan, scroll to zoom, or use the Plotly toolbar to zoom and reset the view.
X/Y axes share the same meter scale. The chart uses Streamlit's supported
`width="stretch"` API.

The renderer also works independently of Streamlit:

```python
from archimind.examples import create_sample_bedroom
from archimind.render import render_floorplan

design = create_sample_bedroom()
figure = render_floorplan(design)
```

The factory returns fresh canonical Pydantic models. The renderer schema-revalidates
the design, returns a Plotly figure, and does not modify its input. Nonzero furniture
rotations raise a clear `ValueError`; rotated footprints are deferred. Out-of-room
furniture is included in the visible ranges, not hidden or declared valid. Door
swings are omitted because hinge and swing information is not part of the model.

The Task 03 sample geometry is preserved. Its caption now distinguishes the
manually specified preview from generated alternatives:

> Manually specified Task 03 demonstration. Generate and compare validated alternatives below.

The preview itself displays the fixed sample. The generator section below it
uses Task 04A/04B checks and reports validation for each generated alternative.

### Generate and compare layouts

The **AI-Assisted Room Layout Generator** section has five parts:

1. **Room Information** — the 5 × 4 × 2.7 m bedroom, bed, desk, wardrobe, south
   door, and north window.
2. **Layout Generation Controls** — random seed (default 42) and **Generate Layouts**.
3. **Generated Alternatives** — actual scores, passing status, issue/warning counts,
   generation seed/attempts, and an A/B selector.
4. **Selected 2D Floor Plan** — the existing interactive renderer and the selected
   candidate's furniture-position table in meters.
5. **Spatial Validation Summary** — containment, overlaps, door approaches,
   circulation, and any advisory warnings.

Generation happens only on the button click. Results and selection persist across
normal reruns in [Streamlit session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state).
Selecting A/B does not regenerate or revalidate. Editing the seed keeps the old
result and selection, with an explicit pending-seed notice. A successful generation
response replaces the stored result and selects A; a response with no candidates
clears the displayed alternatives. An exception keeps the prior result and
selection with an error message. Refreshing/disconnecting the browser may clear
the session; there is no database persistence.

`complete`, `search_exhausted`, `infeasible`, and `unsupported` responses are shown
explicitly. A single valid alternative is displayed on its own; search exhaustion
never claims infeasibility. Missing alternatives are never rendered. Candidate
geometry and reports are checked once on generation before storage. Scores are
placement heuristics, and the current generator uses no AI reasoning.

### Interactive 3D room structure

The **Interactive 3D Room Preview** section renders the sample room's floor and
four walls, with a south door gap and a north window at its actual sill height.
It is independent of the selected furniture alternative and contains no furniture.
The caption explicitly states:

> Structural-only preview of the fixed sample room. See the furnished sample below; selected-layout synchronization is planned.

Drag to orbit; scroll to zoom, or choose zoom/pan from the Plotly modebar. Use
**Reset camera to last save** to restore the initial isometric view. The scene
uses an orthographic camera and axis proportions matching width:depth:height;
a uniform framing factor leaves space for labels on narrow screens. X/Y/Z are
meters east/north/up from the southwest floor corner.

```python
from archimind.examples import create_sample_bedroom
from archimind.render import render_room_3d

figure = render_room_3d(create_sample_bedroom().room)
```

`render_room_3d(room)` returns a reusable Plotly figure without modifying the
canonical models. Floor and wall panels use [explicit mesh triangles](https://plotly.com/python/3d-mesh/).
Each wall is split at opening endpoints, and only solid vertical intervals are
triangulated. Door/window rectangles are **real holes in the wall mesh**. Window
panes are separate translucent blue surfaces; gold door outlines contain no leaf
or swing geometry. No Boolean mesh engine or new dependency is used.

All four walls support multiple openings, corner openings, shared opening edges,
and openings stacked at different heights. Positive-area overlap between openings
on the same wall raises `RoomGeometryError`. Schema-invalid rooms raise Pydantic
validation errors. Collapsed/non-finite panels, unusable scene proportions, and
more than 128 openings also raise explicit geometry errors. Decimal endpoint
arithmetic matches the canonical schemas.

This is a zero-thickness structural preview with no ceiling slab, wall reveals,
3D furniture, CAD/export, or synchronization with selected layouts. Plotly WebGL
requires browser graphics support. Browser verification observed no errors and
one non-fatal Plotly canvas readback performance advisory. Restart an already
running Streamlit server after adding renderer modules if it retains old imports.

### Interactive 3D furnished room

**Interactive 3D Furnished Room Preview** displays the fixed sample bedroom,
independently of the selected Layout A/B. It preserves the structural-only scene
and comparison above it. Task 06C will connect the selected layout to 3D.
Rendering alone does not establish spatial validity.

```python
from archimind.examples import create_sample_bedroom
from archimind.render import render_design_3d, render_furniture_3d

design = create_sample_bedroom()
figure = render_design_3d(design)
bed_meshes = render_furniture_3d(design.furniture[0])
```

`render_design_3d()` reuses `render_room_3d()` without changing any wall, floor,
door, or window vertices/triangles. Furniture parts are explicit Plotly `Mesh3d`
cuboids with eight vertices and twelve triangles each. Materials are muted,
opaque colors; every detail lies inside its declared bounding box.

| Appearance | Selection | Geometry |
| --- | --- | --- |
| Bed | Category `bed` | Full-footprint frame, inset mattress, two pillows |
| Desk | Category `desk` | Full-footprint tabletop and four corner legs |
| Wardrobe | Category `wardrobe`, or `storage` with name `Wardrobe` | Plinth, cabinet, two front panels, two handles |
| Generic | Other categories | One dimensionally accurate solid |

Category matching ignores case and surrounding whitespace. Furniture starts at
Z=0, preserving southwest-origin X/Y positions and metric dimensions. Only rotation
0 is supported; nonzero rotations raise `FurnitureGeometryError`. Schema errors,
collapsed/non-finite spans or face areas, and more than 100 furniture objects are
rejected explicitly. Out-of-room, overlapping, and above-ceiling objects remain
visible without relocation or any validity claim. Scene ranges include them;
axis proportions preserve equal physical units.

The furnished camera starts in an isometric direction with perspective projection
so modebar zoom visibly changes magnification. The independent structural preview
retains its orthographic camera. Drag to orbit; select **Pan** or **Zoom** in the
modebar and drag. **Reset camera to last save** restores the initial view. Scroll
zoom is enabled, but mouse-wheel magnification was not confirmed in this browser;
use the verified modebar zoom. Hover reports name, ID, category, X/Y position,
dimensions, height, and rotation. Legend items can toggle trace groups; hide
**Walls** when a wall intercepts a furniture hover target.

Desktop (1440 px) and narrow (390 px) browser inspection checked geometry,
openings, hover, orbit, zoom, pan, reset, and fixed-sample independence from A/B.
The furnished scene uses extra legend spacing and uniform framing to keep labels
visible at narrow widths. Screenshots are local ignored artifacts in
`output/task06b/`. Console: no application errors; one non-fatal Plotly Canvas2D
readback performance advisory. WebGL support is required.

The sample adds 15 cuboids / 180 furniture triangles. Warm rendering measured
about 23 ms per call locally (imports excluded; this is an observation, not a CI
threshold). No external assets, new dependency, geometry algorithm, model schema,
live Codex functionality, or 2D/3D selection synchronization was added.

## Models and coordinates

**One room. One consistent coordinate system. Explicit units.**

Import the public models from `archimind.models`.

| Model | What it represents |
| :--- | :--- |
| `Room` | ID, name, width, depth, ceiling height, doors, and windows |
| `Door` | ID, supporting wall, offset, opening width, and height |
| `Window` | ID, supporting wall, offset, dimensions, and sill height |
| `Furniture` | ID, name, category, position, dimensions, and stored rotation |
| `RoomDesign` | One room, its furniture list, and an optional design name |

### The spatial convention

| Convention | Meaning |
| :--- | :--- |
| Units | Meters throughout; distance fields use `_m` |
| Origin | `(0, 0)` is the southwest / bottom-left interior corner |
| Axes | X → east/right, Y → north/up, Z → vertically upward |
| Room dimensions | Width along X; depth along Y |
| Furniture position | Lower-left corner of the **unrotated** footprint |
| Furniture rotation | Stored as `0`, `90`, `180`, or `270` degrees; no transformation yet |
| North / south offsets | Measured from the west end, increasing eastward |
| East / west offsets | Measured from the south end, increasing northward |
| Opening elevation | Door bottoms at floor level; window bottoms at sill height |

### What validation guarantees

- Positive, finite dimensions and finite coordinates.
- Nonnegative opening offsets and sill heights.
- Supported walls and integer right-angle rotations.
- Openings that fit their supporting wall and the room ceiling.
- Unique IDs across the room, doors, windows, and furniture in a complete design.
- Strict input types, unknown-field rejection, and JSON serialization.

The data model can represent negative furniture positions, out-of-room furniture,
overlaps, and furniture taller than the ceiling. The separate Task 04A backend
checks planar containment and overlap for zero-rotation furniture. Task 04B adds
door approach and circulation checks through a separate combined API. Rotated
footprints and vertical furniture checks remain outside both scopes.
**Schema validity does not imply spatial validity.**

## Backend spatial validation — Task 04A

```python
from archimind.examples import create_sample_bedroom
from archimind.geometry import validate_layout

report = validate_layout(create_sample_bedroom())
print(report.status)  # passed for Task 04A's implemented checks only
payload = report.model_dump_json(indent=2)
```

`furniture_footprint(item)` and `room_footprint(room)` return Shapely polygons in
meters, using the canonical southwest origin and unrotated lower-left furniture
position. Only rotation `0` is supported. Low-level footprint helpers raise
`UnsupportedGeometryError` for unsupported rotations or geometry that cannot be
represented reliably; `validate_layout` records those conditions in its report.
The engine revalidates the input schema and preserves the original design.

| Check | Rule |
| :--- | :--- |
| Containment | Shapely `room.covers(footprint)`; wall contact is allowed; no outward buffer or area tolerance is applied |
| Collision | A unique pair collides when its intersection area exceeds the configured tolerance |
| Edge/corner contact | Zero-area contact is allowed |
| Overlap tolerance | Absolute **1e-9 m²**, configurable with `area_tolerance_m2`; set `0` for strict positive-area checks |
| Measurements | Out-of-room and overlap areas use square meters in finite JSON values |
| Numeric limits | Decimal endpoint sums avoid addition drift; collapsed, non-finite, or unreliable geometry is unverified |

Every supported pair is checked, including pairs outside the room. Issues are
ordered by unsupported geometry, containment, then overlap, with IDs sorted
lexicographically. Ordering is independent of furniture-list order.

`SpatialValidationReport` includes `room_id`, the explicit
`task_04a_containment_and_overlap` scope, `status`, `violations`, and
`area_tolerance_m2`. Each `SpatialViolation` includes `violation_type`, involved
`furniture_ids`, a human-readable `message`, and unit-named `measurements`.

| Status | Meaning |
| :--- | :--- |
| `passed` | All implemented containment/overlap checks passed |
| `failed` | Supported geometry has containment or overlap violations |
| `unverified` | Some geometry could not be checked; known violations for supported items are still reported |

Unsupported geometry takes precedence over `failed`. No design with unsupported
rotations is marked passed. Invalid canonical schemas raise Pydantic
`ValidationError` rather than producing a spatial report. Reports serialize with
`model_dump_json()` and reconstruct with
`SpatialValidationReport.model_validate_json(payload)`.

These are planar GEOS double-precision checks with an absolute area tolerance.
`validate_layout` retains its original Task 04A scope and JSON schema. Use the
combined API below for Task 04B. Neither API establishes architectural safety or
code compliance. The Streamlit generator uses the combined backend API; the
original manually specified preview remains a separate demonstration.

## Door access and circulation — Task 04B

```python
from archimind.examples import create_sample_bedroom
from archimind.geometry import (
    AccessibilityConfig,
    AccessibilityValidationReport,
    validate_accessibility,
)

report = validate_accessibility(
    create_sample_bedroom(),
    config=AccessibilityConfig(walking_clearance_m=0.6),
)
print(report.status)  # passed for this sample and these assumptions
print(report.checks["circulation"].status)
payload = report.model_dump_json(indent=2)
assert AccessibilityValidationReport.model_validate_json(payload) == report
```

`validate_accessibility` runs Task 04A and both Task 04B checks. Its report extends
`SpatialValidationReport` with `scope="task_04b_accessibility"`, the actual
configuration, and explicit results for `containment`, `furniture_overlap`,
`door_clearance`, and `circulation`. Extended issues retain the original fields
and add `door_ids` and `severity`. The original API and report remain unchanged;
deserialize combined reports with `AccessibilityValidationReport`.

| Assumption | Default and behavior |
| :--- | :--- |
| Required door approach | Opening-width rectangle extending **0.3 m** inward (`required_door_depth_m`); any positive-area furniture intrusion is a `blocked_door` error |
| Advisory approach | **0.9 m** inward (`advisory_door_depth_m`), **0.15 m** beyond each opening endpoint (`advisory_side_margin_m`); advisory-only intrusion is a `door_clearance_warning` |
| Corners | Both rectangles are clipped to the room interior; all four walls use canonical offsets |
| Contact | Boundary-only zone contact is allowed; the furniture-overlap tolerance does not hide a door obstruction |
| Walking clearance | A translating, axis-aligned **0.6 m square** (`walking_clearance_m`); room inset and obstacle expansion are each half that width |
| Usable area | Every positive-area component of the remaining occupant-center space; not the original floor area |
| Entrance | Each door's midpoint, inset by half the walking clearance; a door narrower than that clearance is inaccessible |
| Connectivity | Exactly one usable region, reachable from every door entry; separate doors do not excuse disconnected parts of a single room |
| Work bound | At most **256 furniture objects plus doors combined** for access checks; excess returns `unsupported`, preserving Task 04A results |

Door rectangles describe approach space. **No hinge, swing direction, or actual
door-swing geometry is inferred.** Every blocking furniture item is identified
per door. Advisory warnings alone do not fail an otherwise passing report.

Each check has `passed`, `failed`, `unsupported`, or `not_evaluated` status, an
explanation, and finite measurements where available. Overall `passed` requires
all four checks evaluated without errors; warnings may remain. Unknown or
unsupported checks take precedence over known failures and make the overall
result `unverified`. A room without doors has both access checks explicitly
`not_evaluated`; no entrance is invented. Unsupported rotations/numeric geometry
never become ignored obstacles in a circulation pass. Supported door blockers
are still reported when another object's footprint is unsupported.

The circulation method uses continuous [Shapely polygon difference and set
operations](https://shapely.readthedocs.io/en/stable/manual.html#set-theoretic-methods),
with no occupancy grid, sampling resolution, or snapping grid. It avoids grid
aliasing but remains a conservative proof of concept using double precision:

- The square can reject routes available to a circular body or diagonal motion.
- A blocked door midpoint can fail even if another part of a wide door is usable.
- Exact-width pinches that connect only by a line/point can be rejected. Tiny
  isolated positive-area regions also cause failure.
- Floating-point topology near tangencies can cause false positives or negatives;
  collapsed/unrepresentable geometry returns `unsupported`.
- Areas too small for the square are excluded from usable center space. This is
  not a guarantee of access to every floor patch or to each furniture function.
- Windows, furniture height, door swings, multi-room routes, and building-code
  compliance are outside scope. Only rotation `0` is supported.

Examples: the sample bedroom and an empty room with a 1 m door pass the defaults.
A cabinet in the first 0.3 m of that doorway produces `blocked_door`. A wall-to-wall
barrier produces `circulation_disconnected`; a barrier leaving a 0.5 m passage
fails the default 0.6 m clearance, while a 0.7 m alternative route passes.

<details>
<summary><strong>Field reference and validation behavior</strong></summary>

| Model | Fields |
| :--- | :--- |
| `Room` | `id`, `name`, `width_m`, `depth_m`, `ceiling_height_m`, `doors`, `windows` |
| `Door` | `id`, `wall`, `offset_m`, `width_m`, `height_m` |
| `Window` | `id`, `wall`, `offset_m`, `width_m`, `height_m`, `sill_height_m` |
| `Furniture` | `id`, `name`, `category`, `x_m`, `y_m`, `width_m`, `depth_m`, `height_m`, `rotation_deg` |
| `RoomDesign` | `room`, `furniture`, `name` |

IDs are caller-supplied nonblank strings. Furniture categories are nonblank strings;
there is no catalog integration yet. Lists default to empty, design names to
`None`, and rotations to `0`.

[Pydantic strict validation](https://docs.pydantic.dev/latest/concepts/strict_mode/)
rejects numeric strings and booleans as distances. Python integer distances are
accepted as floating-point meter values.

Opening endpoints and the ceiling may be touched. Span checks compare the decimal
representations of stored values, so `4.2 + 0.9` fits a `5.1` m wall without floating
addition roundoff or a clearance tolerance.

Models and lists are mutable. After nested edits, call
`RoomDesign.model_validate(design)` to validate the complete design again. Existing
nested model instances are revalidated; in-place edits themselves are not
automatically validated or transactional.

</details>

<details>
<summary><strong>Representative bedroom and JSON round-trip</strong></summary>

The reusable [sample bedroom](src/archimind/examples/sample_bedroom.py) constructs a
**5 × 4 × 2.7 m** room with one south-wall door, one north-wall window, a queen bed,
a desk, and a wardrobe. The original `bedroom` fixture in
[tests/test_models.py](tests/test_models.py) remains available for schema tests.

The round-trip test preserves the complete model and its data:

```python
payload = bedroom.model_dump_json()
restored = RoomDesign.model_validate_json(payload)

assert restored == bedroom
assert restored.model_dump() == bedroom.model_dump()
```

</details>

## Automatic furniture layouts — Task 05A

```python
from archimind.examples import create_sample_bedroom
from archimind.geometry import LayoutGenerationResult, generate_layout_candidates
from archimind.render import render_floorplan

requested = create_sample_bedroom()
result = generate_layout_candidates(
    requested.room,
    requested.furniture,
    seed=42,
    max_candidates=2,
    max_attempts=500,
)
for candidate in result.candidates:
    print(candidate.validation.status, candidate.score.model_dump())
    figure = render_floorplan(candidate.design)  # ordinary RoomDesign input

assert LayoutGenerationResult.model_validate_json(result.model_dump_json()) == result
```

The generator copies specifications, preserving IDs, names, categories, dimensions,
height, rotation, room, doors, and windows. It replaces only furniture positions.
Original positions are not fixed anchors; the original input objects are unchanged.
Only rotation `0` is supported. Windows/heights have no additional placement rules.

One attempt constructs an arrangement largest-footprint-first, breaking ties by
ID. A local seeded random source samples wall contacts and centimeter-rounded
interior coordinates. The existing Task 04A engine prunes failed partial layouts;
every complete candidate must pass Task 04B with **zero overlap tolerance**.
Unknown or unevaluated checks cannot be accepted. Exact position signatures remove
duplicates. The first one or two accepted arrangements are ranked by descending
score, then a stable ID/coordinate tie-break; the remaining budget is not searched
for a global optimum. Reproducibility assumes the same software versions.

The score is **80 × usable-space ratio + 20 × advisory-clearance ratio**:

- Usable-space ratio is the validator's usable occupant-center area divided by
  the empty room's inset area under the same walking clearance.
- Advisory-clearance ratio is the fraction of doors without advisory warnings.
- Ratios use 12 decimal places and totals 6. Hard violations disqualify a candidate;
  they cannot be offset by a favorable score. This is not a furniture-function,
  lighting, ergonomics, or code-compliance evaluation.

With the original **5 × 4 × 2.7 m** bedroom and seed **42**, default settings produce
two alternatives in **9 attempts**. Positions below are lower-left corners in
meters, with X east/Y north from the southwest origin. All rotations are zero.

| Furniture ID | Width × depth × height (m) | Original (x, y) | Layout A (x, y) | Layout B (x, y) |
| :--- | :--- | :--- | :--- | :--- |
| `queen-bed` | 1.6 × 2.0 × 0.6 | (0.4, 1.4) | (3.4, 1.69) | (1.96, 0.0) |
| `desk` | 1.2 × 0.6 × 0.75 | (3.2, 3.2) | (0.0, 1.36) | (3.74, 3.4) |
| `wardrobe` | 1.5 × 0.6 × 2.0 | (3.4, 0.4) | (0.0, 3.4) | (0.0, 3.4) |

Both alternatives pass all four spatial checks and have no advisory warnings.
Layout A: usable ratio **0.596524064171**, advisory ratio **1.0**, score
**67.721925**. Layout B: usable ratio **0.595187165775**, advisory ratio **1.0**,
score **67.614973**. These are heuristic alternatives, not optimal designs.

Run the complete example workflow (original specification plus alternative
coordinates, reports, and score components). JSON goes to stdout or `--output`;
runtime/status go separately to stderr so the JSON stays reproducible:

```bash
python -m archimind.examples.generate_bedroom
python -m archimind.examples.generate_bedroom --seed 42 --output /tmp/archimind-bedroom-layouts.json
```

| Result status | Meaning |
| :--- | :--- |
| `complete` | Requested one or two distinct passing candidates found |
| `search_exhausted` | Fewer candidates found within the budget; any valid alternatives are retained; no proof of infeasibility |
| `infeasible` | A necessary condition fails: oversized zero-rotation footprint, excess total footprint area, or unusable empty-room door/clearance |
| `unsupported` | Nonzero rotation, missing/unevaluable entrance, numeric limits, or object-count limit |

`max_attempts` defaults to 500 and accepts 0–10,000; `max_candidates` accepts 1 or 2.
Generation supports at most **32 furniture objects**, also respecting Task 04B's
256 combined furniture/door limit. Each attempt performs at most N partial
validations and one complete validation, plus one empty-room preflight per call.
Results include attempts used, rejection counts, seed, actual clearance config,
and structured candidates. Invalid schemas/options raise validation errors.

An empty furniture request has exactly one distinct arrangement: requesting two
returns that layout with `search_exhausted`. Searches can miss feasible placements
because of finite sampling, centimeter rounding, fixed rotation, ordering, or the
Task 04B conservative assumptions. There is no minimum visual difference rule
beyond distinct exact coordinates, and no optimality or architectural compliance
claim. Task 05B exposes these same results in Streamlit alongside the Task 03 preview.

## Technology

### In the project today

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| Language | Python 3.11+ | Application and package |
| Interface | Streamlit 1.66.1 | Sample preview, seeded layout comparison, structural 3D preview, and AppTest utilities |
| Data | Pydantic 2.14.1 | Room, opening, furniture, and design schemas |
| Visualization | Plotly 7.1.0 | Metric 2D floor plans and structural 3D meshes from canonical models |
| Spatial geometry | Shapely 2.2.0 | Zero-rotation furniture containment and overlap checks |
| Testing | pytest 9.1.1 | Smoke, model, renderer, and preview integration tests |
| Code quality | Ruff 0.17.3 | Linting and formatting |
| Packaging | build 1.6.1 + setuptools | Wheel and source distributions |

Streamlit, Pydantic, Plotly, and Shapely are runtime dependencies. pytest, Ruff, and build are
development extras. Required transitive dependencies install automatically;
future tools are not added to project requirements prematurely.

### Planned for later phases

| Capability | Proposed technology |
| :--- | :--- |
| Agent orchestration | LangGraph + OpenAI API |
| 3D furniture visualization | Plotly |
| 3D export | Trimesh |
| Local persistence | SQLite |

## Quality checks

The test suite covers package imports, the Streamlit screen and chart, schema
validation, wall/ceiling limits, opening and furniture coordinates, equal-scale
axes, containment, collisions, door zones on every wall, corner entrances,
circulation barriers and alternative routes, missing/multiple doors, tolerance behavior, unsupported geometry,
seeded generation, bounded failures, ranked alternatives, button-driven UI state,
A/B selection, seed changes, failure messages, actual 3D wall-triangle coverage and
opening gaps, input immutability, IDs, and lossless JSON
round-trips. Tests run without an API key or external model service.

```bash
python -m ruff check .
python -m ruff format --check .
python -m pip check
python -m pytest -q
python scripts/check_health.py
python -m build
```

`check_health.py` selects an available local port, starts a real headless Streamlit
server, checks for HTTP `200` / `ok`, and stops its temporary server.

### Every change, checked

[GitHub Actions CI](https://github.com/ngstephen1/ArchiMind/actions/workflows/ci.yml)
runs on pull requests targeting `main` and pushes to `main`, with manual runs
available too. Feature-branch pushes are checked through their PR to avoid
duplicate branch/PR runs. One Linux/Python 3.11 job installs dependencies once.

| Gate | What runs |
| :--- | :--- |
| Code quality | Ruff linting, import ordering, and formatting |
| Dependencies | `python -m pip check` |
| Application | All tests, including Streamlit, geometry, seeded generation, and comparison state |
| Runtime | A real headless Streamlit server must return HTTP `200` / `ok` |

Actions use pinned revisions, read-only repository permissions, and cancellation of
superseded runs. The extra OS/Python matrix, distribution builds, archive/wheel
checks, and artifact uploads were removed from routine CI for this local prototype.
Packaging remains available manually with `python -m build`. Hosting deployment
is not configured.

<details>
<summary><strong>Application tests, formatting, and manual server checks</strong></summary>

Smoke tests check imports from outside the repository without `PYTHONPATH`, package
metadata, branding, the preserved sample, and generated-layout comparison through Streamlit's
[AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
AppTest does not start a network server.

Apply formatting with `python -m ruff format .`. Build outputs in `dist/` are
ignored by Git.

For a manual server check, start the headless app and run this in another terminal:

```bash
curl --fail http://127.0.0.1:8501/_stcore/health
```

Adjust the port to match Streamlit's printed URL. A healthy response is `ok`.
Stop the server with `Control-C`.

</details>

## Repository map

```text
ArchiMind/
├── .github/workflows/ci.yml      Lint, dependency, test, and app-health checks
├── app.py                       Streamlit entry point
├── src/archimind/
│   ├── __init__.py               Package initialization
│   ├── models/
│   │   ├── __init__.py           Public model exports
│   │   ├── room.py               Room, Door, Window, RoomDesign
│   │   └── furniture.py          Furniture representation
│   ├── geometry/
│   │   ├── __init__.py           Public footprint/validation APIs
│   │   ├── footprints.py         Zero-rotation Shapely polygons
│   │   ├── accessibility.py      Door approach and circulation checks
│   │   ├── layout_generator.py   Bounded seeded placement and scoring
│   │   └── validator.py          Scoped, deterministic spatial reports
│   ├── render/
│   │   ├── __init__.py           Public rendering function
│   │   ├── floorplan_2d.py       Metric, interactive Plotly floor plan
│   │   ├── room_3d.py            Structural meshes with real opening gaps
│   │   ├── furniture_3d.py       Bounded furniture cuboids and hover information
│   │   └── design_3d.py          Furnished scene composition
│   ├── ui/
│   │   ├── __init__.py           Public Streamlit presentation helper
│   │   └── layout_generation.py  Button-driven generation, state, and comparison
│   └── examples/
│       ├── __init__.py           Public example factory
│       ├── sample_bedroom.py     Reproducible canonical-model bedroom
│       └── generate_bedroom.py   Original request and generated-alternatives CLI
├── tests/
│   ├── test_smoke.py             Package and application checks
│   ├── test_models.py            Model tests and bedroom fixture
│   ├── test_floorplan_2d.py      Coordinate and preview integration tests
│   ├── test_geometry.py          Backend containment/collision/report tests
│   ├── test_accessibility.py     Door/circulation/configuration/report tests
│   ├── test_layout_generator.py  Seeded alternatives, scores, bounds, and renderer tests
│   ├── test_layout_generation_ui.py  AppTest controls, selection, state, and error cases
│   ├── test_room_3d.py           Coordinates, wall triangles, gaps, and 3D integration
│   ├── test_furniture_3d.py      Bounds, surfaces, dimensions, and numeric limits
│   └── test_design_3d.py         Scene composition, 2D correspondence, and app preview
├── scripts/check_health.py      Temporary server health check
├── docs/
│   ├── assets/                  README artwork and logo badges
│   └── developer/STATUS.md      Milestones, capabilities, and verification record
├── .env.example                 Future configuration placeholder
├── .gitignore                   Local/generated-file exclusions
├── MANIFEST.in                  Source archive contents
├── pyproject.toml               Package metadata and dependencies
└── README.md
```

## Roadmap

See [project status](docs/developer/STATUS.md) for the detailed capability matrix
and verification record.

- [x] **Task 01 · Foundation** — package, environment, Streamlit screen, smoke tests.
- [x] **Task 02 · Core data models** — room, openings, furniture, schemas, JSON.
- [x] **Task 03 · 2D floor plan visualization** — interactive canonical-model preview.
- [x] **Task 04A · Spatial validation backend** — containment and furniture overlaps.
- [x] **Task 04B · Door clearance and walking-path validation** — bounded backend approximations.
- [x] **Task 05A · Deterministic furniture layout generation** — validated backend alternatives.
- [x] **Task 05B · Streamlit generation and comparison** — A/B plans, scores, validation, and session state.
- [x] **Task 06A · Basic interactive 3D room geometry** — structural room meshes and real wall openings.
- [x] **Task 06B · 3D furniture visualization** — bounded meshes and independent furnished sample.
- [ ] **Task 06C · Synchronize Selected 2D and 3D Layouts** — recommended next milestone.
- [ ] Export.
- [ ] Multi-agent collaboration and targeted design revisions.
- [ ] Versioned persistence and a reproducible offline demonstration.

Later phases remain proposed work. This prototype does not provide CAD/BIM outputs,
construction guidance, or building-code/accessibility certification.

## Configuration and project boundaries

The optional [Codex Design Advisor backend](docs/developer/CODEX_ADVISOR.md) is
implemented separately as C01. It is disabled by default
(`ARCHIMIND_ENABLE_CODEX_ADVISOR=0`), requires explicit per-call live-usage opt-in,
and is limited to local single-user testing. It returns unvalidated suggestions;
there is no advisor UI or automatic placement application.

`.env.example` documents a future `OPENAI_API_KEY` placeholder. The current app does
not load environment files or use an API key. Keep real credentials in ignored
local files when a later integration needs them.

Local virtual environments, secrets, caches, databases, generated renders, and
temporary outputs are excluded from Git.

This repository documents software implementation. The separate course
Requirements & Architecture assignment remains outside this development work.

---

<p align="center">
  <strong>ArchiMind AI</strong><br />
  <sub>Define carefully. Validate explicitly. Build incrementally.</sub><br />
  <sub><a href="docs/assets/README.md">Artwork &amp; logo credits</a> · <a href="#overview">Back to top ↑</a></sub>
</p>
