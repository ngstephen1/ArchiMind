<p align="center">
  <img src="docs/assets/archimind-hero.svg" alt="ArchiMind AI — Multi-Agent Interior Design and 3D Spatial Planning. Task 03: 2D floor plan preview. Animated architectural concept illustration." width="100%" />
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
| Describe one rectangular room, its doors, windows, and furniture. | Validate dimensions, opening limits, IDs, and JSON round-trips. | Inspect a manually specified bedroom in an interactive, scaled 2D preview. |
| Available now | Available now | Demonstration available |

> **Current stage · Task 03 — 2D floor plan visualization**
>
> The original Foundation content is preserved, with a **2D Floor Plan Preview**
> beneath it. Spatial validation, automatic placement, 3D rendering, agents,
> persistence, and export remain planned. **No API key is required.**

Tasks **01–03 are complete**; **Task 04 has not started**. The
[project status record](docs/developer/STATUS.md) lists milestone progress,
capability boundaries, and the verified baseline. The current local suite contains
**194 passing tests**: 171 existing cases plus 23 preview-related cases.

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

**Demonstration layout — spatial validation and automatic placement are not yet implemented.**

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

Furniture overlap, containment, clearance, and rotated footprints belong to the
future spatial engine. Furniture may currently have negative positions, extend
outside the room, overlap, or exceed its ceiling. **Schema validity does not imply
spatial validity.**

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

## Technology

### In the project today

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| Language | Python 3.11+ | Application and package |
| Interface | Streamlit 1.66.1 | Foundation screen, 2D preview, and AppTest utilities |
| Data | Pydantic 2.14.1 | Room, opening, furniture, and design schemas |
| 2D visualization | Plotly 7.1.0 | Interactive floor plans from canonical models |
| Testing | pytest 9.1.1 | Smoke, model, renderer, and preview integration tests |
| Code quality | Ruff 0.17.3 | Linting and formatting |
| Packaging | build 1.6.1 + setuptools | Wheel and source distributions |

Streamlit, Pydantic, and Plotly are runtime dependencies. pytest, Ruff, and build are
development extras. Required transitive dependencies install automatically;
future tools are not added to project requirements prematurely.

### Planned for later phases

| Capability | Proposed technology |
| :--- | :--- |
| Agent orchestration | LangGraph + OpenAI API |
| Spatial validation | Shapely |
| 3D visualization | Plotly |
| 3D export | Trimesh |
| Local persistence | SQLite |

## Quality checks

The test suite covers package imports, the Streamlit screen and chart, schema
validation, wall/ceiling limits, opening and furniture coordinates, equal-scale
axes, unsupported rotations, input immutability, IDs, and lossless JSON
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
runs on pushes and pull requests targeting `main` or `stephen-develop`, with manual
runs available too.

| Gate | What runs |
| :--- | :--- |
| Code quality | Ruff linting, import ordering, and formatting |
| Compatibility | Dependency checks, pytest, and server health on Linux with Python 3.11/3.13 and macOS with Python 3.11 |
| Package integrity | Wheel/source builds, application-file checks, and a clean wheel installation |
| Delivery | Verified distribution artifacts, retained for 14 days |

Actions use pinned revisions, read-only repository permissions, and cancellation of
superseded runs. Package artifacts are available from successful workflow runs;
hosting deployment is not configured.

<details>
<summary><strong>Application tests, formatting, and manual server checks</strong></summary>

Smoke tests check imports from outside the repository without `PYTHONPATH`, package
metadata, and the Foundation screen through Streamlit's
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
├── .github/workflows/ci.yml      Automated checks and package artifacts
├── app.py                       Streamlit entry point
├── src/archimind/
│   ├── __init__.py               Package initialization
│   ├── models/
│   │   ├── __init__.py           Public model exports
│   │   ├── room.py               Room, Door, Window, RoomDesign
│   │   └── furniture.py          Furniture representation
│   ├── render/
│   │   ├── __init__.py           Public rendering function
│   │   └── floorplan_2d.py       Metric, interactive Plotly floor plan
│   └── examples/
│       ├── __init__.py           Public example factory
│       └── sample_bedroom.py     Reproducible canonical-model bedroom
├── tests/
│   ├── test_smoke.py             Package and application checks
│   ├── test_models.py            Model tests and bedroom fixture
│   └── test_floorplan_2d.py      Coordinate and preview integration tests
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
- [ ] **Task 04 · Spatial validation** — room containment, overlaps, and door clearance.
- [ ] Furniture layout generation.
- [ ] Interactive 3D visualization and export.
- [ ] Multi-agent collaboration and targeted design revisions.
- [ ] Versioned persistence and a reproducible offline demonstration.

Later phases remain proposed work. This prototype does not provide CAD/BIM outputs,
construction guidance, or building-code/accessibility certification.

## Configuration and project boundaries

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
