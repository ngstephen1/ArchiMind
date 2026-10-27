# ArchiMind AI

Multi-Agent Interior Design & 3D Spatial Planning

ArchiMind AI is an ADS 5984 software prototype intended to transform natural-language
room requirements into validated 2D floor plans and interactive 3D interiors.

## Current status: Foundation (Task 01)

The current implementation includes an installable Python package, a minimal
Streamlit status screen, and smoke tests. The screen displays the Foundation phase,
Running status, and planned capabilities. It does not generate designs or call an AI
service. No API key is needed.

Planned capabilities include:

- AI-assisted room planning
- 2D/3D visualization
- Spatial validation
- Multi-agent collaboration
- Versioned projects and export

Room and furniture models, layout generation, geometry, rendering, agents, API
integration, persistence, and exports are not implemented yet.

## Technology stack

| Status | Technology | Purpose |
| --- | --- | --- |
| Current | Python 3.11+ | Application and package |
| Current | Streamlit 1.66.1 | Native application interface and AppTest utilities |
| Current, development only | pytest 9.1.1 | Smoke tests |
| Current, development only | Ruff 0.17.3 and build 1.6.1 | Linting, formatting, and package builds |
| Future | Pydantic | Structured room and furniture models |
| Future | LangGraph and OpenAI API | Multi-agent orchestration |
| Future | Shapely | Geometry and spatial validation |
| Future | Plotly and Trimesh | 2D/3D visualization and export |
| Future | SQLite | Local persistence |

Only Streamlit is declared as a runtime dependency. pytest, Ruff, and build are development extras.
Their required transitive dependencies are installed automatically. Future libraries
are not added to the project requirements. setuptools provides the build backend.

## Repository structure

```text
ArchiMind/
├── .github/workflows/ci.yml      # Automated checks and build artifacts
├── app.py                       # Streamlit entry point
├── scripts/
│   └── check_health.py           # Temporary headless server check and cleanup
├── src/
│   └── archimind/
│       └── __init__.py           # Package initialization and version
├── tests/
│   └── test_smoke.py             # Import, package, and application checks
├── docs/
│   └── developer/
│       └── .gitkeep
├── .gitignore
├── .env.example                 # Future credential placeholder only
├── MANIFEST.in                  # Application files included in source archives
├── pyproject.toml               # Package metadata and dependencies
└── README.md
```

The local `.venv/`, caches, package build metadata, secret files, databases, and
generated outputs are ignored by Git.

## macOS setup

This foundation was configured with **CPython 3.11.13**, using
`/opt/homebrew/bin/python3.11` (resolved interpreter:
`/opt/homebrew/opt/python@3.11/bin/python3.11`). Use a compatible Python 3.11+
interpreter; `python3.11` below must be available on your PATH. The existing local
`.venv` already uses the recorded interpreter.

From the project directory, create the environment once and install the package:

```bash
cd /Users/macbook/Hack/ArchiMind
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The editable installation discovers `archimind` under `src/` and makes it importable
without setting `PYTHONPATH`. Runtime and development dependency versions are pinned
in `pyproject.toml`; transitive dependencies are resolved by pip.

For later terminal sessions, activate the environment before running commands:

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python --version
```

In VS Code, select `${workspaceFolder}/.venv/bin/python` as the Python interpreter.

## Run the application

```bash
python -m streamlit run app.py
```

Open the Local URL printed by Streamlit, normally `http://localhost:8501`.
Stop the server with `Control-C`.

To run without automatically opening a browser:

```bash
python -m streamlit run app.py --server.headless true --server.address 127.0.0.1
```

## Run tests

```bash
python -m pytest -q
```

The smoke suite checks package import from outside the repository without
`PYTHONPATH`, package metadata and editable source discovery, and application
execution through Streamlit's
[AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
with the expected Foundation screen. AppTest does not start a network server.

For a separate server health check, run the headless command above and use a second
terminal (adjust the port if Streamlit selected a different one):

```bash
curl --fail http://127.0.0.1:8501/_stcore/health
```

A healthy server returns `ok`. Stop the server with `Control-C` afterward.

The automated version selects an available local port and always stops its server:

```bash
python scripts/check_health.py
```

## CI and package delivery

[GitHub Actions CI](https://github.com/ngstephen1/ArchiMind/actions/workflows/ci.yml)
runs on pushes and pull requests targeting `main` or `stephen-develop`, and can also
be started manually. It checks:

- Ruff lint rules, including import ordering, and consistent formatting.
- Dependency compatibility, pytest, and the real headless Streamlit health endpoint
  on Linux with Python 3.11/3.13 and macOS with Python 3.11.
- Wheel and source distribution builds after all quality and test jobs succeed,
  including verification that the source archive contains the app and smoke checks.
- Installation of the wheel into a clean environment and import without the source
  tree on Python's import path.

Successful builds upload the distributions as workflow artifacts retained for 14
days. This provides verified package downloads; hosting deployment is not configured.
The workflow uses read-only repository permissions, pinned action revisions, and
cancels superseded runs on the same branch or pull request.

Run the same checks locally after installing the development extra:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pip check
python -m pytest -q
python scripts/check_health.py
python -m build
```

To apply formatting changes, use `python -m ruff format .`. Generated packages in
`dist/` remain ignored by Git. Install the development dependencies again after
changes to `pyproject.toml` with `python -m pip install -e ".[dev]"`.

## Configuration and limitations

`.env.example` documents a placeholder for a future `OPENAI_API_KEY`. The Foundation
application does not read it or load environment files. Keep actual credentials in
local ignored files when a later integration requires them.

This repository currently provides the application foundation only. Planned design
features require later implementation and validation. The separate course
Requirements & Architecture assignment is outside this implementation repository's
development documentation.
