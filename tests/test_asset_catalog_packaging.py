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
        "archimind/assets/furniture_catalog_1_0_0.json",
        "archimind/retrieval/historical.py",
        "archimind/assets/catalog.py",
        "archimind/assets/inspection.py",
        "archimind/assets/render_qualification.py",
        "archimind/assets/render_assets.py",
        "archimind/assets/selection.py",
        "archimind/assets/specifications.py",
        "archimind/retrieval/__init__.py",
        "archimind/retrieval/contracts.py",
        "archimind/retrieval/eligibility.py",
        "archimind/retrieval/lexical.py",
        "archimind/retrieval/evaluation.py",
        "archimind/retrieval/embedding_index.py",
        "archimind/retrieval/semantic.py",
        "archimind/retrieval/offline_encoder.py",
        "archimind/retrieval/embedding_experiment.py",
        "archimind/retrieval/hybrid.py",
        "archimind/ui/furniture_assets.py",
        "archimind/ui/bedroom_chat.py",
        "archimind/agents/catalog_conversation.py",
        "archimind/agents/catalog_requirements.py",
        "archimind/assets/chat_specifications.py",
        "archimind/render/selected_realistic.py",
        "archimind/ui/realistic_view.py",
        "archimind/ui/product_fixture.py",
        "archimind/assets/product_render_release.json",
        "archimind/assets/charles_visual_review.json",
        "archimind/assets/belaya_visual_review.json",
        "archimind/assets/belaya_render_release.json",
        "archimind/assets/belaya_planning_release.json",
        "archimind/assets/belaya_planning_envelope.json",
        "archimind/assets/belaya_qualification.json",
        "archimind/_viewer_assets/furniture/BelayaDesk.glb",
        "archimind/_viewer_assets/furniture/BELAYA_PROVENANCE.json",
        "archimind/_viewer_assets/furniture/BELAYA_ATTRIBUTION.txt",
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
            "BelayaDesk.glb",
        }
        assert sum(n.endswith("/CharlesArmchair.glb") for n in archive.namelist()) == 1
        assert not any(n.endswith("/.env") for n in archive.namelist())
        assert not any("furniture_source_candidates" in n for n in archive.namelist())
        assert not any("08F1" in n for n in archive.namelist())
        assert not any("08F2" in n for n in archive.namelist())
        assert not any("furniture_retrieval_synthetic" in n for n in archive.namelist())
        assert not any("B075X2X4XS" in n for n in archive.namelist())
        assert not any(
            n.endswith((".onnx", ".f32")) or "furniture_embedding_" in n
            for n in archive.namelist()
        )
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
        assert any(n.endswith("/docs/developer/FURNITURE_CATALOG_UI.md") for n in names)
        assert any(
            n.endswith("/docs/data/CATALOG_GENERATION_08E_VERIFICATION.json")
            for n in names
        )
        for required in (
            "/scripts/run_chat.py",
            "/docs/developer/CHAT_BEDROOM.md",
            "/docs/data/CHAT_BEDROOM_09A.json",
            "/docs/data/CHAT_BEDROOM_09A.md",
            "/data/catalogs/furniture_source_candidates.json",
            "/data/catalogs/furniture_source_candidates_08a.json",
            "/docs/data/FURNITURE_SOURCE_REGISTER.md",
            "/docs/data/FURNITURE_EXPANSION_08F1.md",
            "/docs/data/FURNITURE_EXPANSION_08F1.json",
            "/docs/data/FURNITURE_RETRIEVAL_HUMAN_REVIEW_08F1.md",
            "/docs/data/FURNITURE_CATALOG_ADMISSION_08F2.md",
            "/docs/data/FURNITURE_CATALOG_ADMISSION_08F2.json",
            "/data/benchmarks/furniture_retrieval_queries.json",
            "/data/benchmarks/furniture_retrieval_synthetic.json",
            "/scripts/evaluate_furniture_retrieval.py",
            "/docs/developer/FURNITURE_RETRIEVAL_ARCHITECTURE.md",
            "/docs/data/RETRIEVAL_BASELINE_08R0.md",
            "/docs/data/RETRIEVAL_BASELINE_08R0.json",
        ):
            assert any(n.endswith(required) for n in names)
        for required in (
            "/data/benchmarks/furniture_embedding_development_08r1.json",
            "/data/benchmarks/furniture_embedding_held_out_08r1.json",
            "/scripts/acquire_furniture_encoder.py",
            "/scripts/build_furniture_embedding_index.py",
            "/scripts/evaluate_furniture_embeddings.py",
            "/docs/data/RETRIEVAL_EMBEDDING_08R1.md",
            "/docs/data/RETRIEVAL_EMBEDDING_08R1.json",
            "/docs/data/ENCODER_ACQUISITION_08R1.json",
            "/docs/data/ENCODER_ENVIRONMENT_08R1.json",
        ):
            assert any(n.endswith(required) for n in names)
        assert not any(n.endswith((".onnx", ".f32")) for n in names)
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
catalog = load_catalog(version="1.0.0")
assert len(load_catalog().records) == 5
assert load_catalog().catalog_version == "1.1.0"
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
from archimind.retrieval import (
    FurnitureSearchRequest, FurnitureSearchFilters, LexicalRetrievalProvider, resolve_result)
import archimind.retrieval.lexical as retrieval_module
assert Path(retrieval_module.__file__).resolve().is_relative_to(target)
provider = LexicalRetrievalProvider()
retrieved = provider.search(FurnitureSearchRequest(query='Charles armchair'))
assert retrieved.hits[0].reference.asset_id == 'abo-b075x2x4xs-amazon-com'
assert resolve_result(retrieved)[0].record.source.product_id == 'B075X2X4XS'
assert not provider.search(FurnitureSearchRequest(query='queen bed')).hits
assert not provider.search(FurnitureSearchRequest(query='bookcase', required_qualification='render')).hits
assert not any(n.startswith(('openai', 'langgraph', 'fastembed', 'chromadb', 'onnxruntime')) for n in sys.modules)
from archimind.retrieval.embedding_index import EmbeddingError, build_embedding_index
from archimind.retrieval.semantic import SemanticRetrievalProvider, AbstentionPolicy
from archimind.retrieval.hybrid import HybridRetrievalProvider
from archimind.retrieval.offline_encoder import FastEmbedCPUEncoder
for name in ('embedding_index', 'semantic', 'hybrid', 'offline_encoder'):
    assert Path(sys.modules['archimind.retrieval.'+name].__file__).resolve().is_relative_to(target)
try:
    FastEmbedCPUEncoder(Path('no-model-cache'))
except EmbeddingError:
    pass
else:
    raise AssertionError('Missing encoder cache was accepted')
assert not any(n.startswith(('fastembed', 'onnxruntime', 'tokenizers')) for n in sys.modules)
import numpy as np
from archimind.retrieval.embedding_index import EncoderSpec, ModelArtifact
class TinyEncoder:
    spec = EncoderSpec(model_name='BAAI/bge-small-en-v1.5',
        upstream_repository='BAAI/bge-small-en-v1.5', upstream_revision='0'*40,
        artifact_repository='Qdrant/bge-small-en-v1.5-onnx-Q', artifact_revision='0'*40,
        fastembed_version='test', onnxruntime_version='test', numpy_version=np.__version__,
        tokenizers_version='test', execution_kind='test_double',
        artifacts=(ModelArtifact(filename='test.onnx', size_bytes=1, sha256='0'*64),))
    def encode_documents(self, texts): return np.eye(384, dtype=np.float32)[:len(texts)]
    def encode_queries(self, texts): return np.eye(384, dtype=np.float32)[:1]
from archimind.retrieval import build_index
encoder = TinyEncoder()
corpus = build_index()
semantic = SemanticRetrievalProvider(index=build_embedding_index(corpus, encoder),
    encoder=encoder, policy=AbstentionPolicy(mode='threshold', minimum_cosine=-1.0, method='test_double'))
request = FurnitureSearchRequest(query='Charles armchair')
assert len(resolve_result(semantic.search(request))) == 5
hybrid = HybridRetrievalProvider(provider, semantic, corpus=corpus)
assert len(resolve_result(hybrid.search(request))) == 5
from archimind.retrieval.historical import (
    historical_index, HistoricalLexicalProvider, HistoricalSemanticProvider,
    HistoricalHybridProvider, resolve_historical_result)
old_corpus = historical_index()
old_lexical = HistoricalLexicalProvider()
old_semantic = HistoricalSemanticProvider(
    index=build_embedding_index(old_corpus, encoder, historical=True), encoder=encoder,
    policy=AbstentionPolicy(mode='threshold', minimum_cosine=-1.0, method='test_double'))
old_result = HistoricalHybridProvider(old_lexical, old_semantic, corpus=old_corpus).search(request)
assert len(resolve_historical_result(old_result)) == 2
assert LexicalRetrievalProvider(index=old_corpus).search(request).status == 'stale_index'
for resolution in (resolve_result, lambda r: resolve_historical_result(r, for_preparation=True)):
    try:
        resolution(old_result)
    except ValueError:
        pass
    else:
        raise AssertionError('Historical research result authorized current preparation')
assert Path(sys.modules['archimind.retrieval.historical'].__file__).resolve().is_relative_to(target)
assert not any(n.startswith(('fastembed', 'onnxruntime', 'tokenizers')) for n in sys.modules)
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
belaya_id = 'abo-b074l4976t-amazon-co-uk'
belaya_release = product_release(belaya_id)
assert belaya_release.render_qualified
assert product_asset_path(belaya_id).resolve().is_relative_to(target)
assert product_asset_path(belaya_id).stat().st_size == 3135676
belaya_technical = verify_product_asset(belaya_id)
assert belaya_technical['inspection']['original_sha256'] == belaya_release.source_glb_sha256
assert product_projection()[belaya_id]['triangles'] == 812
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
from archimind.assets import catalog_product_options, prepare_catalog_specification, specification_is_current
from archimind.examples import create_sample_bedroom
base = create_sample_bedroom()
options = catalog_product_options(catalog_version="1.0.0")
assert len(catalog_product_options()) == 5
assert options[0].render_qualified and not options[1].render_qualified
submission = prepare_catalog_specification(base,
    retained_manual_ids=tuple(f.id for f in base.furniture),
    product_ids=tuple(o.record.asset_id for o in options))
assert len(submission.design().furniture) == 5 and len(submission.planning_bindings) == 1
assert specification_is_current(submission, base,
    retained_manual_ids=submission.retained_manual_ids, product_ids=submission.product_ids)
assert submission.design().furniture[3].id == 'catalog:abo-b075x2x4xs-amazon-com:1'
assert submission.assignments[1].product_id == 'B07PQS58XN'
assert Path(sys.modules['archimind.assets.specifications'].__file__).resolve().is_relative_to(target)
new_ids = ('abo-b074l4976t-amazon-co-uk', 'abo-b07h8jn9qf-amazon-co-uk', 'abo-b07b4vxxjc-amazon-com')
new_dimensions = ((1.6, .8, .75), (2.0, .59, 2.12), (.6096, .4318, .6096))
for asset_id, dimensions in zip(new_ids, new_dimensions):
    item = furniture_from_catalog(asset_id, furniture_id=asset_id, name='Product', x_m=-1.0, y_m=0.0)
    assert (item.width_m, item.depth_m, item.height_m) == dimensions and item.rotation_deg == 0
new_submission = prepare_catalog_specification(base, retained_manual_ids=(), product_ids=new_ids)
assert len(new_submission.assignments) == 3 and len(new_submission.planning_bindings) == 1
assert all(a.catalog_version == '1.1.0' for a in new_submission.assignments)
assert all(a.dimension_basis == ('planning_envelope_B' if a.asset_id == belaya_id else 'published_item_dimensions') for a in new_submission.assignments)
assert new_submission.planning_bindings[0].envelope.asset_id == belaya_id
assert new_submission.planning_bindings[0].canonical_dimensions.wdh == (1.6, .8018731772899628, .7516312003135682)
resolved = build_render_bindings(new_submission.design(), planning_bindings={p.furniture_id:p for p in new_submission.planning_bindings})
assert {b.asset_id for b in resolved.bindings} == {None,belaya_id}
assert all(b.asset_id is None for b in build_render_bindings(new_submission.design()).bindings)
print('INSTALLED_CATALOG_AND_PRODUCT_OK')
"""
    from catalog_chat_helpers import TEXT, extraction

    code = (
        code.replace("print('INSTALLED_CATALOG_AND_PRODUCT_OK')", "")
        + """
import json
from archimind.agents.catalog_conversation import (
    reconcile_catalog_extraction, interpret_catalog_conversation)
from archimind.agents.catalog_requirements import CatalogChatTurn, CatalogConversationExtraction
from archimind.assets.chat_specifications import prepare_chat_specification
for name in ('archimind.agents.catalog_conversation',
             'archimind.agents.catalog_requirements',
             'archimind.assets.chat_specifications'):
    assert Path(sys.modules[name].__file__).resolve().is_relative_to(target)
data = CatalogConversationExtraction.model_validate_json(sys.argv[2])
conversation = (CatalogChatTurn(id=1,role='user',content=sys.argv[3]),)
assert interpret_catalog_conversation(conversation).status == 'unavailable'
draft = reconcile_catalog_extraction(data,conversation).draft
chat = prepare_chat_specification(draft,
    selections={'request-2':belaya_id}, procedural_ids={'request-1':'queen-bed'})
assert len(chat.design().furniture) == 2
assert not chat.design().room.windows
assert chat.planning_bindings[0].canonical_dimensions.wdh == (
    1.6,.8018731772899628,.7516312003135682)
assert all(f.rotation_deg == 0 for f in chat.design().furniture)
assert not any(n.startswith(('fastembed','onnxruntime','tokenizers')) for n in sys.modules)
print('INSTALLED_CATALOG_AND_PRODUCT_AND_CHAT_OK')
"""
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            code,
            str(target),
            extraction().model_dump_json(),
            TEXT,
        ],
        cwd=outside,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip() == "INSTALLED_CATALOG_AND_PRODUCT_AND_CHAT_OK"
