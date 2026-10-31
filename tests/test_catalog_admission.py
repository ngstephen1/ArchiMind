"""08F2 source-bound metadata admission and explicit release compatibility."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from retrieval_helpers import offline  # noqa: F401

from archimind.assets.catalog import (
    CatalogError,
    FurnitureAssetRecord,
    FurnitureCatalog,
    load_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/catalogs/furniture_source_candidates.json"
NEW = {
    "abo-b074l4976t-amazon-co-uk": (
        "desk",
        "writing desk",
        "Movian Belaya writing desk — Oak",
        ["desk", "writing desk"],
        ["writing", "study"],
    ),
    "abo-b07h8jn9qf-amazon-co-uk": (
        "wardrobe",
        "wardrobe",
        "Movian Morava wardrobe — Oak Sonoma",
        ["wardrobe"],
        ["clothing storage"],
    ),
    "abo-b07b4vxxjc-amazon-com": (
        "table",
        "nightstand",
        "Rivet bedside nightstand — Brown",
        ["nightstand", "bedside table"],
        ["bedside use"],
    ),
}


def source_record(asset_id):
    """Independent source projection for admission assertions, not runtime ingestion."""
    c = next(
        c
        for c in json.loads(SOURCE.read_bytes())["candidates"]
        if c["candidate_id"] == asset_id
    )
    category, subtype, name, aliases, uses = NEW[asset_id]
    r = load_catalog(version="1.0.0").records[0].model_dump(mode="json")
    s, identity, dims = c["source"], c["identity"], c["dimensions"]
    r.update(
        asset_id=asset_id,
        category=category,
        subtype=subtype,
        variant_label=identity["variant_labels"][0],
    )
    r["source"].update(
        product_id=identity["product_id"],
        model_id=identity["model_id"],
        marketplace_domain=identity["marketplace_domain"],
        manufacturer_model_numbers=identity["manufacturer_model_numbers"],
        variant_label=identity["variant_labels"][0],
        original_category=identity["product_type_values"][0],
        original_title=c["name"],
        metadata_url=s["metadata_url"],
        model_url=s["model_url"],
        source_revision=s["source_revision"],
        source_last_modified=s["source_last_modified"],
        source_etag=s["source_etag"],
        listing_line=s["listing_jsonl_line_1_based"],
        listing_record_sha256=s["listing_line_sha256_excluding_newline"],
        metadata_snapshot_sha256=s["metadata_response_sha256"],
        model_index_sha256=s["model_index_sha256"],
        qualification_candidate_id=asset_id,
        qualification_revision="4052e1a4bf8d8919a34da249b356d9e4dec5296f",
        qualification_file_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        qualification_date="2026-10-29",
    )
    r["dimensions"].update(
        original=dims["original_item_fields"],
        axis_map=[
            {"target": a, "source_field": v["source"].split(".")[-1]}
            for a, v in dims["normalization_inputs"].items()
        ],
        axis_evidence=dims["axis_interpretation"],
        evidence_urls=dims["evidence_urls"],
        **dims["normalized_m"],
    )
    r["search"].update(
        reviewed_name=name,
        evidence_urls=[s["metadata_url"]],
        aliases=aliases,
        usage_tags=uses,
    )
    assert c["decision"] == "eligible_for_acquisition"
    assert c["rights_status"] == c["dimension_status"] == "verified"
    assert c["rights"]["public_browser_delivery"] and c["rights"]["redistribution"]
    assert c["rights"]["license_identifier"] == r["legal"]["license_id"]
    return r


@pytest.mark.parametrize("asset_id", NEW)
def test_extended_record_source_mapping_and_roundtrip(asset_id):
    raw = source_record(asset_id)
    r = FurnitureAssetRecord.model_validate_json(json.dumps(raw))
    assert (r.category, r.subtype) == NEW[asset_id][:2]
    assert not r.render_qualified and r.rendering.model_sha256 is None
    assert r.search.materials is r.search.colors is r.search.styles is None
    assert r.source.original_title not in r.search_document()
    assert FurnitureAssetRecord.model_validate_json(r.model_dump_json()) == r
    with pytest.raises(ValueError):
        r.source.variant_label = "altered"


@pytest.mark.parametrize(
    "field,value",
    [
        ("category", "storage"),
        ("subtype", "bookcase"),
        ("subtype", "display cabinet"),
        ("subtype", "dining table"),
        ("rotation_deg", 90),
        ("variant_label", "Red"),
        ("qualification", "render_qualified"),
    ],
)
def test_functional_and_qualification_conflicts_rejected(field, value):
    raw = source_record("abo-b07h8jn9qf-amazon-co-uk")
    raw[field] = value
    with pytest.raises(ValueError):
        FurnitureAssetRecord.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize(
    "path,value",
    [
        (("source", "original_category"), "SOFA"),
        (("source", "model_id"), "B074L4976T"),
        (("source", "marketplace_domain"), "amazon.com"),
        (("source", "listing_record_sha256"), "bad"),
        (("legal", "public_browser_delivery"), False),
        (("legal", "license_id"), "CC0"),
        (("dimensions", "width_m"), 0.59),
        (("dimensions", "height_m"), 0),
        (("dimensions", "height_m"), float("inf")),
        (("dimensions", "kind"), "package"),
        (("rendering", "verified_bounds"), [0, 1]),
    ],
)
def test_identity_rights_dimensions_and_false_render_rejected(path, value):
    raw = source_record("abo-b07h8jn9qf-amazon-co-uk")
    raw[path[0]][path[1]] = value
    with pytest.raises(ValueError):
        FurnitureAssetRecord.model_validate_json(json.dumps(raw))


def test_version_boundary_and_fixed_resource_loading():
    old = load_catalog(version="1.0.0")
    assert len(old.records) == 2 and old.schema_version == 1
    raw = old.model_dump(mode="json")
    raw["records"] += [source_record(i) for i in NEW]
    raw["records"].sort(key=lambda r: r["asset_id"])
    with pytest.raises(ValueError):
        FurnitureCatalog.model_validate_json(json.dumps(raw))
    raw.update(schema_version=2, catalog_version="1.1.0")
    new = FurnitureCatalog.model_validate_json(json.dumps(raw))
    assert len(new.records) == 5
    assert all(new.get_record(r.asset_id) == r for r in old.records)
    for version in ("../../.env", "https://example.com/catalog.json", "9.0.0"):
        with pytest.raises(CatalogError):
            load_catalog(version=version)
    bad = copy.deepcopy(raw)
    bad["records"].append(bad["records"][-1])
    with pytest.raises(ValueError):
        FurnitureCatalog.model_validate_json(json.dumps(bad))


def test_active_release_records_equal_source_contract_and_original_records():
    current, old = load_catalog(), load_catalog(version="1.0.0")
    assert (
        current.schema_version,
        current.catalog_version,
        current.search_document_version,
    ) == (2, "1.1.0", 1)
    assert len(current.records) == 5
    for r in old.records:
        assert current.get_record(r.asset_id) == r
        assert (
            current.get_record(r.asset_id).search_document_sha256
            == r.search_document_sha256
        )
    receipt = json.loads(
        (ROOT / "docs/data/FURNITURE_EXPANSION_08F1.json").read_bytes()
    )
    for asset_id in NEW:
        record = current.get_record(asset_id)
        assert record == FurnitureAssetRecord.model_validate_json(
            json.dumps(source_record(asset_id))
        )
        entry = next(
            i for i in receipt["investigations"] if i["candidate_id"] == asset_id
        )
        excerpt = entry["source_excerpts"]
        assert excerpt["item_id"] == excerpt["3dmodel_id"] == record.source.product_id
        assert excerpt["domain_name"] == record.source.marketplace_domain
        assert entry["record_sha256"] == record.source.listing_record_sha256
        assert [v["value"] for v in excerpt["model_number"]] == list(
            record.source.manufacturer_model_numbers
        )
        assert record.variant_label in [v["value"] for v in excerpt["color"]]
        for measurement in record.dimensions.original:
            e = excerpt["item_dimensions"][measurement.source_field]
            assert (measurement.value, measurement.unit) == (e["value"], e["unit"])
        assert not any(
            term in record.search_document().casefold()
            for term in (
                "oak-effect",
                "brass finish",
                "modern",
                "classic",
                "leather",
                "mirror panel",
            )
        )


@pytest.mark.parametrize("asset_id", NEW)
def test_new_factory_preparation_and_placeholder_only(asset_id):
    from archimind.assets import furniture_from_catalog, load_planning_envelope
    from archimind.assets.selection import build_render_bindings
    from archimind.assets.specifications import (
        catalog_product_options,
        prepare_catalog_specification,
    )
    from archimind.examples import create_sample_bedroom
    from archimind.render.selected_realistic import build_selected_realistic_scene

    record = load_catalog().get_record(asset_id)
    option = next(o for o in catalog_product_options() if o.record.asset_id == asset_id)
    assert option.preparation_available and not option.render_qualified
    assert (
        option.planning_dimensions
        is option.planning_digest
        is option.render_release_digest
        is None
    )
    if asset_id == "abo-b074l4976t-amazon-co-uk":
        # 08F3A separately releases planning evidence; historical catalog flags
        # and this pre-render workflow remain metadata-only at this checkpoint.
        envelope = load_planning_envelope(asset_id)
        assert envelope.catalog_version == "1.1.0"
        assert not envelope.qualification.render_qualified
    else:
        with pytest.raises(ValueError):
            load_planning_envelope(asset_id)
    item = furniture_from_catalog(
        asset_id, furniture_id="fresh", name="Product", x_m=-1.0, y_m=20.0
    )
    assert (item.width_m, item.depth_m, item.height_m) == (
        record.dimensions.width_m,
        record.dimensions.depth_m,
        record.dimensions.height_m,
    )
    assert item.rotation_deg == 0 and item.x_m == -1
    base = create_sample_bedroom()
    before = base.model_dump_json()
    p = prepare_catalog_specification(
        base, retained_manual_ids=(), product_ids=(asset_id,)
    )
    assert (
        not p.planning_bindings
        and p.assignments[0].dimension_basis == "published_item_dimensions"
    )
    assert p.assignments[0].catalog_version == "1.1.0"
    p.assignments[0].validate_furniture(p.design().furniture[0])
    assert base.model_dump_json() == before
    result = build_selected_realistic_scene(p.design())
    assert result.scene.design == p.design()
    assert all(b.asset_id is None for b in result.resolution.bindings)
    assert all(
        b.asset_id is None
        for b in build_render_bindings(
            p.design(), overrides={p.assignments[0].furniture_id: asset_id}
        ).bindings
    )
    with pytest.raises(ValueError):
        p.assignments[0].dimensions.width_m = 4


def test_frozen_benchmark_and_stale_indexes_remain_separate(tmp_path):
    from embedding_helpers import FixedEncoder

    from archimind.retrieval import (
        FurnitureSearchRequest,
        LexicalRetrievalProvider,
        build_index,
        resolve_result,
    )
    from archimind.retrieval.embedding_index import (
        build_embedding_index,
        read_embedding_index,
        write_embedding_index,
    )
    from archimind.retrieval.evaluation import (
        RetrievalBenchmark,
        SyntheticCatalog,
        run_benchmark,
    )
    from archimind.retrieval.historical import (
        HistoricalHybridProvider,
        HistoricalLexicalProvider,
        HistoricalSemanticProvider,
        historical_index,
        resolve_historical_result,
    )
    from archimind.retrieval.semantic import AbstentionPolicy, SemanticRetrievalProvider

    old = historical_index()
    current = build_index()
    assert (
        old.identity.catalog_version == "1.0.0"
        and current.identity.catalog_version == "1.1.0"
    )
    assert len(old.documents) == 2 and len(current.documents) == 5
    request = FurnitureSearchRequest(query="Charles armchair")
    assert LexicalRetrievalProvider(index=old).search(request).status == "stale_index"
    historical = HistoricalLexicalProvider().search(request)
    assert (
        resolve_historical_result(historical)[0].record.source.product_id
        == "B075X2X4XS"
    )
    with pytest.raises(ValueError):
        resolve_result(historical)
    with pytest.raises(ValueError):
        resolve_historical_result(historical, for_preparation=True)
    encoder = FixedEncoder()
    with pytest.raises(ValueError):
        build_embedding_index(old, encoder)
    assert not encoder.document_inputs
    vectors = build_embedding_index(old, encoder, historical=True)
    path = tmp_path / "index"
    write_embedding_index(vectors, path)
    with pytest.raises(ValueError):
        read_embedding_index(path, encoder=encoder.spec, corpus=current)
    with pytest.raises(ValueError):
        read_embedding_index(path, encoder=encoder.spec, corpus=old)
    assert (
        read_embedding_index(path, encoder=encoder.spec, corpus=old, historical=True)
        == vectors
    )
    policy = AbstentionPolicy(
        mode="threshold", minimum_cosine=-1.0, method="test_double"
    )
    stale = SemanticRetrievalProvider(
        index=vectors, encoder=encoder, policy=policy
    ).search(request)
    assert stale.status == "stale_index" and not encoder.query_inputs
    replay = HistoricalSemanticProvider(
        index=vectors, encoder=encoder, policy=policy
    ).search(request)
    assert len(replay.hits) == 2
    with pytest.raises(ValueError):
        resolve_result(replay)
    hybrid = HistoricalHybridProvider(
        HistoricalLexicalProvider(),
        HistoricalSemanticProvider(index=vectors, encoder=encoder, policy=policy),
        corpus=old,
    )
    combined = hybrid.search(request)
    assert len(resolve_historical_result(combined)) == 2
    assert hybrid.search(request) == combined
    with pytest.raises(ValueError):
        resolve_result(combined)
    empty = HistoricalLexicalProvider().search(FurnitureSearchRequest(query="bed"))
    assert empty.status == "empty"
    with pytest.raises(ValueError):
        resolve_result(empty)
    root = ROOT / "data/benchmarks"
    benchmark = RetrievalBenchmark.model_validate_json(
        (root / "furniture_retrieval_queries.json").read_bytes()
    )
    fixture = SyntheticCatalog.model_validate_json(
        (root / "furniture_retrieval_synthetic.json").read_bytes()
    )
    with pytest.raises(ValueError):
        run_benchmark(benchmark, fixture)
    receipt = run_benchmark(benchmark, fixture, repeats=2, historical=True)
    assert (
        receipt["semantic_output_digest"]
        == "6063a66e344188f60f2469453c19b3d21fd7a44ef4bb99b99c89b81bd3b34d31"
    )


@pytest.mark.parametrize(
    "name,source_field",
    [
        ("materials", "material"),
        ("styles", "style"),
        ("colors", "color"),
        ("description", "item_name"),
    ],
)
def test_new_record_cannot_promote_unreviewed_marketing_attributes(name, source_field):
    raw = source_record("abo-b074l4976t-amazon-co-uk")
    value = dict(
        value="Oak",
        origin="source_verified",
        source_field=source_field,
        evidence_urls=[raw["source"]["metadata_url"]],
    )
    raw["search"][name] = value if name == "description" else [value]
    with pytest.raises(ValueError):
        FurnitureAssetRecord.model_validate_json(json.dumps(raw))


def test_active_loader_rejects_coherent_but_unapproved_product_change(monkeypatch):
    from unittest.mock import Mock

    from archimind.assets import catalog as module

    raw = load_catalog().model_dump(mode="json")
    raw["records"][0]["source"]["manufacturer_model_numbers"] = [
        "another-valid-looking-variant"
    ]
    resource = Mock()
    resource.joinpath.return_value.read_bytes.return_value = json.dumps(raw).encode()
    monkeypatch.setattr(module.resources, "files", lambda _: resource)
    with pytest.raises(CatalogError, match="unavailable or invalid"):
        load_catalog()


def test_admission_receipt_pins_frozen_research_and_original_asset_bytes():
    receipt = json.loads(
        (ROOT / "docs/data/FURNITURE_CATALOG_ADMISSION_08F2.json").read_bytes()
    )
    migrations = json.loads(
        (ROOT / "docs/data/ASSET_QUALIFICATION_BELAYA_08F3A.json").read_bytes()
    )["r1"]["authorized_migrations"]
    for name, expected in receipt["frozen_files"].items():
        if name in migrations:
            assert migrations[name]["before_sha256"] == expected
            expected = migrations[name]["after_sha256"]
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    catalog_bytes = (ROOT / "src/archimind/assets/furniture_catalog.json").read_bytes()
    assert hashlib.sha256(catalog_bytes).hexdigest() == receipt["catalog"]["sha256"]
    assert receipt["catalog"]["metadata_count"] == len(load_catalog().records) == 5
    assert (
        receipt["catalog"]["planning_count"] == receipt["catalog"]["render_count"] == 1
    )
    assert receipt["human_review"]["completed_judgments"] == 0
    assert receipt["human_review"]["status"] == "pending_unevaluated"
