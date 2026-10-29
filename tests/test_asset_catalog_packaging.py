"""Real offline source/wheel builds and isolated installed-resource verification."""

import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_in_source_wheel_and_isolated_install(tmp_path):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PIP_NO_INDEX"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))
    catalog_path = "archimind/assets/furniture_catalog.json"
    preserved = [
        catalog_path,
        "archimind/assets/catalog.py",
        "archimind/assets/inspection.py",
        "archimind/assets/planning_envelopes.py",
        "archimind/assets/planning_envelopes.json",
        "archimind/assets/__init__.py",
        "archimind/_viewer_assets/viewer.js",
        "archimind/_viewer_assets/furniture/SheenChair.glb",
        "archimind/_viewer_assets/furniture/PROVENANCE.json",
        "archimind/_viewer_assets/furniture/CC0-1.0.txt",
        "archimind/_viewer_assets/furniture/CC-BY-4.0.txt",
        "archimind/_viewer_assets/THIRD_PARTY_NOTICES.txt",
    ]
    with zipfile.ZipFile(wheel) as archive:
        for name in preserved:
            assert archive.read(name) == (ROOT / "src" / name).read_bytes()
        assert not any(n.endswith("/.env") for n in archive.namelist())
        assert not any("B075X2X4XS" in n for n in archive.namelist())
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        assert any(n.endswith("/scripts/inspect_furniture_assets.py") for n in names)
        assert any(n.endswith("/docs/developer/PLANNING_ENVELOPES.md") for n in names)
        for name in preserved:
            member = next(n for n in names if n.endswith("/src/" + name))
            assert (
                archive.extractfile(member).read() == (ROOT / "src" / name).read_bytes()
            )
        assert not any(
            "/.agents/" in n or "/.claude/" in n or n.endswith("/.env") for n in names
        )

    target = tmp_path / "installed"
    outside = tmp_path / "outside"
    outside.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-index",
            "--no-compile",
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=outside,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    code = """
import sys
from pathlib import Path
target = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(target))
def offline(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system'):
        raise AssertionError('Catalog attempted external work')
sys.addaudithook(offline)
import archimind
import archimind.assets.catalog as module
from archimind.assets import load_catalog, furniture_from_catalog
import archimind.assets.inspection as inspection
import archimind.assets.planning_envelopes as planning
from archimind.assets import load_planning_envelope, furniture_from_planning_envelope
assert Path(archimind.__file__).resolve().is_relative_to(target)
assert Path(module.__file__).resolve().is_relative_to(target)
assert Path(inspection.__file__).resolve().is_relative_to(target)
assert Path(planning.__file__).resolve().is_relative_to(target)
catalog = load_catalog()
assert len(catalog.records) == 2
assert catalog.catalog_version == '1.0.0'
assert all(not r.render_qualified for r in catalog.records)
assert all(r.source.source_revision is None for r in catalog.records)
try:
    inspection.inspect_furniture_asset(Path('does-not-exist.glb'), catalog.records[0])
except inspection.InspectionError as error:
    assert str(error) == 'asset_unavailable'
else:
    raise AssertionError('Missing local asset was accepted')
item = furniture_from_catalog(catalog.records[0].asset_id,
    furniture_id='isolated', name='Chair', x_m=-1.0, y_m=20.0)
assert (item.width_m, item.depth_m, item.height_m) == (.9906, .9906, .9652)
assert (item.x_m, item.y_m, item.rotation_deg) == (-1.0, 20.0, 0)
envelope = load_planning_envelope(catalog.records[0].asset_id)
fresh, binding = furniture_from_planning_envelope(envelope.asset_id,
    furniture_id='reserved', name='Charles', x_m=-1.0, y_m=20.0)
assert (fresh.width_m, fresh.depth_m, fresh.height_m) == (
    .996104896068573, 1.0019413232803345, .9760930538177491)
assert (fresh.x_m, fresh.y_m, fresh.rotation_deg) == (-1.0, 20.0, 0)
assert binding.envelope.published_dimensions.width_m == .9906
assert not binding.envelope.qualification.render_qualified
binding.validate_furniture(fresh)
assert type(binding).model_validate_json(binding.model_dump_json()) == binding
assert not any(n.startswith(('openai', 'langgraph', 'fastembed', 'chromadb'))
               for n in sys.modules)
print('INSTALLED_CATALOG_OK')
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(target)],
        cwd=outside,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip() == "INSTALLED_CATALOG_OK"
