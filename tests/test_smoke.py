"""Smoke tests for the installed package and application."""

import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from streamlit.testing.v1 import AppTest

import archimind

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_imports_without_pythonpath(tmp_path: Path) -> None:
    """An editable install must work outside the repository directory."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", "import archimind; print(archimind.__version__)"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert result.stdout.strip() == archimind.__version__


def test_project_initialization() -> None:
    """Package metadata and the editable src package must agree."""
    assert version("archimind") == archimind.__version__
    assert Path(archimind.__file__).resolve() == (
        PROJECT_ROOT / "src" / "archimind" / "__init__.py"
    )


def test_streamlit_app_runs() -> None:
    """The application must render its current status and branding without errors."""
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30).run()

    assert not app.exception
    assert app.title[0].value == "ArchiMind AI"
    assert app.subheader[0].value == (
        "Multi-Agent Interior Design & 3D Spatial Planning"
    )
    assert {metric.label: metric.value for metric in app.metric} == {
        "Current development phase": "Task 06E1",
        "Application status": "Running",
    }
    assert app.subheader[1].value == "Planned capabilities"
    for capability in (
        "AI-assisted room planning",
        "Full 3D furniture asset catalog",
        "Multi-agent collaboration",
        "Versioned projects and export",
    ):
        assert capability in app.markdown[1].value
    assert "These capabilities are planned." in app.caption[0].value
