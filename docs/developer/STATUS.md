# Project status

Last reviewed and locally verified: **October 27, 2026**.

**Current milestone: Task 03 complete — interactive 2D floor plan visualization.**
Task 04 is next and has not been implemented.

## Milestones

| Milestone | Status | Delivered behavior |
| --- | --- | --- |
| Task 01 — Foundation | Complete | Editable Python package, local environment, Streamlit screen, smoke tests, and CI |
| Task 02 — Core data models | Complete | Typed room, door, window, furniture, and design models; strict schema validation and JSON round-trips |
| Task 03 — 2D floor plan visualization | Complete | Reusable Plotly renderer, reproducible bedroom factory, Streamlit preview, and coordinate-based tests |
| Task 04 — Spatial validation | Not started | Proposed containment, overlap, and door-clearance checks |
| Later phases | Planned | Layout generation, 3D, agents, targeted revisions, persistence, and export |

## Capability status

| Capability | Current support | Boundary |
| --- | --- | --- |
| Room representation | One rectangular room in meters | No arbitrary room polygons or multiple-room plans |
| Openings | Wall-relative doors and windows | Schema checks wall endpoints and ceiling limits; hinge/swing information is not modeled |
| Furniture data | IDs, names, categories, positions, dimensions, and right-angle rotations | Data can represent overlaps and out-of-room objects |
| Schema validation | Strict types, finite numbers, positive dimensions, opening extents, and design-wide unique IDs | Does not establish spatial validity |
| 2D rendering | Walls with opening gaps, blue windows, gold door spans, furniture footprints, and labels | Only zero-rotation furniture; unsupported rotations raise `ValueError` |
| Interaction | Hover details, panning, scroll zoom, and equal X/Y metric scale | No editing controls or automatic placement |
| Sample data | Fresh 5 × 4 × 2.7 m bedroom with a south door, north window, bed, desk, and wardrobe | Manually specified demonstration, not an optimized or spatially validated layout |
| JSON | Model serialization and reconstruction | No project-save UI or revision database |
| Spatial checks | Not implemented | Containment, furniture overlap, door clearance, and walkability remain future work |
| 3D / export | Not implemented | No 3D viewer, GLB, CAD, or BIM integration |
| Agents / API | Not implemented | No LangGraph or OpenAI calls; no API key required |

## What the app currently shows

The original branding, Foundation metric, and planned-capabilities section remain
intact. The **2D Floor Plan Preview** beneath them displays the canonical sample
bedroom. The Foundation label is preserved UI content, not the current project
milestone; the current milestone is Task 03.

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

Local verification for this milestone:

- `python -m pytest -q`: **194 passing tests**, including all 171 Task 02 tests and
  23 additional rendering/example/integration cases.
- `python -m pip check`: no broken requirements.
- `python -m ruff check .` and `python -m ruff format --check .`: passed.
- Headless Streamlit health endpoint: HTTP `200` with `ok`.
- Browser inspection: correct opening/furniture positions, readable labels,
  identical X/Y pixels per meter, functioning hover/pan/zoom, and no console
  warnings or errors. Desktop and narrow layouts were inspected.
- Renderer input immutability and explicit rotation rejection are covered by tests.

GitHub Actions independently runs linting, tests and health checks on Linux with
Python 3.11/3.13 and macOS with Python 3.11, followed by distribution builds, clean
wheel installation, and artifact upload. See the
[workflow results](https://github.com/ngstephen1/ArchiMind/actions/workflows/ci.yml)
for the result of a particular commit.

## Next milestone

**Task 04 — Spatial validation** should evaluate room containment, furniture
overlap, and door clearance against the existing canonical models. It remains
separate from schema validation and rendering. No Task 04 implementation is
included in the current milestone.

For setup, local commands, coordinates, and renderer usage, see the
[project README](../../README.md).
