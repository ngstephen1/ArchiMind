# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ArchiMind AI is a Python 3.11+ research prototype that turns natural-language room briefs into validated floor plans and interactive 3D interiors. The installable package is `src/archimind` (editable install, no `PYTHONPATH` needed). `docs/developer/STATUS.md` records milestone status and capability boundaries; `docs/developer/*.md` has one guide per subsystem — read the relevant one before changing a subsystem.

## Commands

Setup (README uses POSIX paths; on Windows the interpreter is `.venv/Scripts/python`):

```sh
python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
npm ci --prefix frontend/realistic_viewer                      # Three.js viewer / Town
.venv/bin/python -m pip install -r services/town/requirements.txt  # Town API + worker
```

Checks — these mirror `.github/workflows/ci.yml`, all must pass:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pip check
python -m pytest -q                                   # testpaths = tests/
python -m pytest -q tests/test_town.py::test_name     # single test
cd frontend/realistic_viewer && npm run check && npm test && npm run build
git diff --exit-code -- src/archimind/_viewer_assets  # built viewer must be committed
python scripts/check_health.py                        # headless Streamlit smoke
```

Run:

| What | Command |
| --- | --- |
| Main Streamlit app (offline) | `python -m streamlit run app.py --server.port 8501` (`?workspace=studio` → 3D Studio) |
| Live Bedroom Chat | `python scripts/run_chat.py --port 8502` |
| Live 3D Studio | `python scripts/run_studio.py --port 8503` |
| Design agent panel | `python scripts/run_with_agent.py` |
| Town (API+worker on 8790, editor on 8791) | `python scripts/run_town.py` (SQLite at `storage/town-designer.sqlite3`, override with `TOWN_DB`) |
| Bedroom showcase / Studio House | `python scripts/run_bedroom_showcase.py`, `python scripts/run_studio_home.py` |

## Architecture

**Core data and geometry (deterministic, authoritative).**
- `models/` — canonical Pydantic room/furniture schemas (meters; X/Y = east/north from the southwest floor corner, Z up; Decimal-precise endpoint arithmetic).
- `geometry/` — `layout_generator.py` produces seeded A/B candidates (seed 42 is the standard fixture); `validator.py` checks containment, overlaps, door approaches and circulation. Validation is the source of truth everywhere — AI components may advise, explain or choose among already-validated candidates, but never set coordinates or override validation.
- `render/` — Plotly 2D/3D renderers (`render_floorplan`, `render_room_3d`, `render_design_3d`) that revalidate input and never mutate it; `realistic_viewer.py`/`selected_realistic.py` feed the Three.js viewer.

**Agents and workflows.** All OpenAI use is opt-in: each path needs an `ARCHIMIND_ENABLE_OPENAI_*` env flag *and* a per-call authorization argument/UI consent (see `.env.example`). The default app, tests and demos run offline with mocked clients; `.env` is not auto-loaded except by the `run_*` launchers.
- `workflow/graph.py` — bounded sequential LangGraph: requirements → layout → spatial critique → styling, deterministic by default, with optional AI nodes (`agents/*_agent.py` + `*_schemas.py` + `*_grounding.py`). LangSmith tracing is forcibly disabled.
- `design_agent/` — single-model tool loop; only the code gate in `gate.py` can release a design.
- `studio/` — procedural 3D Studio furnishing plans (`ui/studio.py`).
- `ui/` — Streamlit sections composed by `app.py`.

**Town** (`src/archimind/town/`, frontend in `frontend/realistic_viewer/town/`). Multi-room home designer: `api.py` (HTTP API, `archimind.town.api:app`), `worker.py` (job runner, `python -m archimind.town.worker`), `service.py` (storage: SQLite locally, Postgres/Supabase hosted), `design.py` (partition generation + whole-home validation), `agents.py` (five specialist roles A–E: brief, furniture/references, layout, critic, style), `brief_review.py` (deterministic brief clause parsing — negation/clause scoping is regression-tested in `tests/test_town_live_quality.py`). `pages/Town_Editor.py` is the Streamlit editor sharing the same API. Hosting: Vercel static (`vercel.json`), Render API/worker (`render.yaml`). Details in `docs/developer/TOWN.md`.

**Supporting packages.** `assets/` (furniture catalog, qualification and planning-envelope JSON — products are only "qualified" with recorded evidence), `retrieval/` (lexical/semantic/hybrid catalog search), `style_packs/` (CC0 surface/lighting packs, see `STYLE_PACKS.md`), `datasets/` (`python -m archimind.datasets` reference pipeline, data lives outside git under `ARCHIMIND_DATA_ROOT`), `designer_handoff/` + `design/` (released Blender/Rhino designer pieces with `release.json`).

**Frontend build output is checked in.** `frontend/realistic_viewer/build.mjs` bundles into `src/archimind/_viewer_assets/` (shipped as package data). After any change under `frontend/realistic_viewer/src`, run `npm run build` and commit the regenerated assets, or CI fails. New `src/*.js` files must also be added to the `check` script in `package.json`.

## Conventions

- Ruff: line length 88, rules `E4,E7,E9,F,I` (import sorting enforced); dependencies are pinned exactly in `pyproject.toml`.
- Docs and evidence files (`docs/data/*`) are written with careful, non-overclaiming language — state what was verified and what remains unverified; keep that style when updating docs.
- Merging to `main` requires a PR with a passing **Devin Review** status and all review threads resolved (`python scripts/check_devin_review.py <PR#>`; see `docs/developer/DEVIN_REVIEW.md`).
