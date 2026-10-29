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
        "archimind/assets/render_qualification.py",
        "archimind/assets/render_assets.py",
        "archimind/assets/selection.py",
        "archimind/render/selected_realistic.py",
        "archimind/ui/realistic_view.py",
        "archimind/ui/product_fixture.py",
        "archimind/assets/product_render_release.json",
        "archimind/assets/charles_visual_review.json",
        "archimind/render/product_scene.py",
        "archimind/examples/sample_product_room.py",
        "archimind/_viewer_assets/furniture/CharlesArmchair.glb",
        "archimind/_viewer_assets/furniture/CHARLES_PROVENANCE.json",
        "archimind/_viewer_assets/furniture/ABO_ATTRIBUTION.txt",
        "archimind/_viewer_assets/furniture/ABO_SOURCE_README.md",
        "archimind/_viewer_assets/furniture/ABO_LICENSE_CC_BY_4.0.txt",
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
        assert {Path(n).name for n in archive.namelist() if n.endswith(".glb")} == {
            "SheenChair.glb",
            "CharlesArmchair.glb",
        }
        assert sum(n.endswith("/CharlesArmchair.glb") for n in archive.namelist()) == 1
        assert not any(n.endswith("/.env") for n in archive.namelist())
        assert not any("B075X2X4XS" in n for n in archive.namelist())
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        assert any(n.endswith("/scripts/inspect_furniture_assets.py") for n in names)
        assert any(n.endswith("/scripts/build_product_registry.py") for n in names)
        assert any(
            n.endswith("/docs/developer/CHARLES_PRODUCT_RENDERING.md") for n in names
        )
        assert any(
            n.endswith("/docs/developer/SELECTED_REALISTIC_LAYOUTS.md") for n in names
        )
        assert any(
            n.endswith("/docs/data/SELECTED_LAYOUT_08D_VERIFICATION.json")
            for n in names
        )
        assert any(
            n.endswith("/docs/data/ASSET_QUALIFICATION_08CR2.json") for n in names
        )
        assert sum(n.endswith("/CharlesArmchair.glb") for n in names) == 1
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
from archimind.assets.render_assets import (
    product_release, product_asset_path, verify_product_asset, product_projection)
from archimind.examples.sample_product_room import create_sample_product_room
# The existing render package imports optional styling SDK types. Catalog imports
# above stay SDK-free; renderer verification must never construct a provider.
import openai
def provider_forbidden(*args, **kwargs):
    raise AssertionError('Rendering attempted a live provider')
openai.OpenAI = openai.AsyncOpenAI = openai.Client = openai.AsyncClient = provider_forbidden
from archimind.render.product_scene import product_scene_payload
import archimind.assets.render_assets as render_module
assert Path(render_module.__file__).resolve().is_relative_to(target)
release = product_release()
assert release.render_qualified and release.asset_id == envelope.asset_id
assert product_asset_path().resolve().is_relative_to(target)
assert product_asset_path().stat().st_size == 4252440
technical = verify_product_asset()
assert technical['inspection']['original_sha256'] == release.source_glb_sha256
assert technical['envelope']['metadata_sha256'] == release.envelope_sha256
projection = product_projection()[release.asset_id]
assert projection['bytes'] == 4252440 and projection['triangles'] == 42706
room = create_sample_product_room()
bindings = {f.id: release.asset_id if f.category == 'chair' else None for f in room.furniture}
assert product_scene_payload(room, asset_bindings=bindings)['schema_version'] == 3
assert not any(n.startswith(('langgraph', 'fastembed', 'chromadb'))
               for n in sys.modules)
from archimind.render.selected_realistic import build_selected_realistic_scene
from archimind.assets.selection import build_render_bindings
from archimind.examples.sample_product_room import create_sample_product_fixture
fixture = create_sample_product_fixture()
prepared = build_selected_realistic_scene(fixture.design,
    planning_bindings={p.furniture_id:p for p in fixture.planning_bindings})
assert sum(b.asset_id is not None for b in prepared.resolution.bindings) == 2
assert prepared.scene.design.model_dump(mode='json') == fixture.design.model_dump(mode='json')
assert all(b.asset_id is None for b in build_render_bindings(room).bindings)
assert Path(sys.modules['archimind.assets.selection'].__file__).resolve().is_relative_to(target)
assert Path(sys.modules['archimind.render.selected_realistic'].__file__).resolve().is_relative_to(target)
print('INSTALLED_CATALOG_AND_PRODUCT_OK')
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
    assert result.stdout.strip() == "INSTALLED_CATALOG_AND_PRODUCT_OK"
