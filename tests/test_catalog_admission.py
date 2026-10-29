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
