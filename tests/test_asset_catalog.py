"""Offline product qualification, searchable metadata and canonical boundaries."""

import copy
import hashlib
import json
import socket
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from archimind.assets import (
    CatalogError,
    FurnitureAssetRecord,
    FurnitureCatalog,
    furniture_from_catalog,
    load_catalog,
)
from archimind.assets import catalog as module
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates, validate_accessibility
from archimind.models import Furniture

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "src/archimind/assets/furniture_catalog.json"
CHAIR = "abo-b075x2x4xs-amazon-com"
BOOKCASE = "abo-b07pqs58xn-amazon-com"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Catalog must not invoke external services or processes")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    # Catalog imports must not instantiate any model/service client either.
    import openai

    monkeypatch.setattr(openai, "OpenAI", forbidden)
    monkeypatch.setattr(openai, "AsyncOpenAI", forbidden)


@pytest.fixture
def raw():
    return json.loads(RESOURCE.read_text())


def parse(raw):
    return FurnitureCatalog.model_validate_json(json.dumps(raw))


def set_path(obj, path, value):
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = value


def test_load_identity_order_and_json_round_trip():
    catalog = load_catalog()
    assert catalog.catalog_id == "archimind-furniture"
    assert catalog.catalog_version == "1.0.0"
    assert catalog.schema_version == catalog.search_document_version == 1
    assert tuple(r.asset_id for r in catalog.records) == (CHAIR, BOOKCASE)
    assert FurnitureCatalog.model_validate_json(catalog.model_dump_json()) == catalog
    for r in catalog.records:
        assert r.asset_version == "1.0.0"
        assert FurnitureAssetRecord.model_validate_json(r.model_dump_json()) == r


def test_records_match_frozen_08a_evidence():
    path = ROOT / "data/catalogs/furniture_source_candidates_08a.json"
    source = json.loads(path.read_text())
    eligible = {
        c["candidate_id"]: c
        for c in source["candidates"]
        if c["decision"] == "eligible_for_acquisition"
    }
    assert set(eligible) == {CHAIR, BOOKCASE}
    for record in load_catalog().records:
        c = eligible[record.asset_id]
        assert record.source.product_id == c["identity"]["product_id"]
        assert record.source.model_id == c["identity"]["model_id"]
        assert record.source.manufacturer_model_numbers == tuple(
            c["identity"]["manufacturer_model_numbers"]
        )
        assert record.variant_label == c["identity"]["variant_labels"][0]
        assert record.source.original_title == c["name"]
        assert record.source.source_revision is None
        assert (
            record.source.metadata_snapshot_sha256
            == c["source"]["metadata_response_sha256"]
        )
        assert (
            record.source.listing_record_sha256
            == c["source"]["listing_line_sha256_excluding_newline"]
        )
        assert record.source.listing_line == c["source"]["listing_jsonl_line_1_based"]
        assert (
            record.source.qualification_file_sha256
            == hashlib.sha256(path.read_bytes()).hexdigest()
        )
        assert (
            record.source.qualification_revision
            == "c9f1941a16985e775ff4923acc344a3d9bdb23dd"
        )
        for axis, value in c["dimensions"]["normalized_m"].items():
            assert getattr(record.dimensions, axis) == value
        for original in record.dimensions.original:
            expected = next(
                v
                for v in c["dimensions"]["original_item_fields"]
                if v["source_field"] == original.source_field
            )
            assert (original.value, original.unit) == (
                expected["value"],
                expected["unit"],
            )
        assert record.category == c["canonical_category"]
        assert record.legal.license_id == c["rights"]["license_identifier"]
        for name in source["attribution"]["ABO_contributors"]:
            assert name in record.legal.attribution


def test_deep_immutability():
    c = load_catalog()
    for obj, key, value in [
        (c, "catalog_version", "9.0.0"),
        (c.records[0], "asset_version", "9.0.0"),
        (c.records[0].dimensions, "width_m", 9.0),
        (c.records[0].dimensions.original[0], "value", 9.0),
        (c.records[0].source, "variant_label", "invented"),
    ]:
        with pytest.raises(ValidationError):
            setattr(obj, key, value)
    assert isinstance(c.records, tuple)
    assert isinstance(c.records[0].search.aliases, tuple)
    with pytest.raises(TypeError):
        c.records[0].legal.evidence_urls[0] = "https://example.org"


@pytest.mark.parametrize(
    "path,value",
    [
        (["schema_version"], 2),
        (["schema_version"], True),
        (["search_document_version"], 2),
        (["catalog_id"], "wrong"),
        (["catalog_version"], "latest"),
        (["records", 0, "unexpected"], "ignored"),
        (["records", 0, "asset_id"], "another-id"),
        (["records", 0, "source", "model_id"], "B000000000"),
        (["records", 0, "source", "variant_label"], "Espresso"),
        (["records", 0, "source", "listing_record_sha256"], "not-a-hash"),
        (["records", 0, "source", "metadata_url"], "file:///private/secret"),
        (["records", 0, "source", "model_url"], "https://example.org/model.glb"),
        (["records", 0, "source", "manufacturer_model_numbers"], []),
        (["records", 0, "category"], "storage"),
        (["records", 1, "subtype"], "wardrobe"),
        (["records", 1, "search", "aliases"], ["wardrobe"]),
        (["records", 0, "search", "usage_tags"], ["sleeping"]),
        (["records", 0, "search", "aliases"], ["armchair", "armchair"]),
        (["records", 0, "search", "materials"], []),
        (["records", 0, "search", "evidence_urls"], []),
        (
            ["records", 0, "search", "evidence_urls"],
            ["https://user:secret@example.org"],
        ),
        (["records", 0, "rotation_deg"], 90),
        (["records", 0, "rotation_deg"], True),
        (["records", 0, "qualification"], "render_qualified"),
        (["records", 0, "rendering", "status"], "render_qualified"),
        (["records", 0, "rendering", "local_glb_path"], "../../secret.glb"),
        (
            ["records", 0, "rendering", "local_glb_path"],
            "https://example.org/model.glb",
        ),
        (["records", 0, "rendering", "model_sha256"], "a" * 64),
        (["records", 0, "rendering", "verified_bounds"], [0, 1]),
        (["records", 0, "rendering", "verified_orientation"], "+Y"),
        (["records", 0, "rendering", "verified_anchor"], "floor"),
        (["records", 0, "rendering", "model_asset_id"], "sheen-chair"),
        (["records", 0, "source_conventions", "status"], "verified"),
        (["records", 0, "dimensions", "kind"], "package"),
        (["records", 0, "dimensions", "status"], "uncertain"),
        (["records", 0, "dimensions", "original", 0, "unit"], "feet"),
        (["records", 0, "dimensions", "axis_evidence"], ""),
        (["records", 0, "dimensions", "evidence_urls"], []),
        (["records", 0, "dimensions", "width_m"], 1.0),
        (["records", 0, "dimensions", "height_m"], 0),
        (["records", 0, "dimensions", "height_m"], -1),
        (["records", 0, "dimensions", "original", 0, "value"], True),
        (["records", 0, "dimensions", "axis_map", 0, "source_field"], "height"),
        (["records", 0, "legal", "status"], "unknown"),
        (["records", 0, "legal", "status"], "restricted"),
        (["records", 0, "legal", "license_id"], "unknown"),
        (["records", 0, "legal", "public_browser_delivery"], False),
        (["records", 0, "legal", "redistribution"], False),
        (["records", 0, "legal", "commercial_use"], False),
        (["records", 0, "legal", "attribution"], ""),
        (["records", 0, "legal", "evidence_urls"], []),
    ],
)
def test_invalid_catalogs_rejected(raw, path, value):
    set_path(raw, path, value)
    with pytest.raises((ValidationError, CatalogError)):
        parse(raw)


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_measurements_rejected(raw, value):
    raw["records"][0]["dimensions"]["original"][0]["value"] = value
    with pytest.raises(CatalogError):
        parse(raw)


@pytest.mark.parametrize(
    "unit,factor",
    [("meters", 1), ("centimeters", 0.01), ("millimeters", 0.001), ("inches", 0.0254)],
)
def test_exact_conversion_and_asymmetric_axes(raw, unit, factor):
    from decimal import Decimal

    d = raw["records"][1]["dimensions"]
    for m in d["original"]:
        m["unit"] = unit
        d[
            {"width": "width_m", "length": "depth_m", "height": "height_m"}[
                m["source_field"]
            ]
        ] = float(Decimal(str(m["value"])) * Decimal(str(factor)))
    result = parse(raw).get_record(BOOKCASE).dimensions
    assert result.width_m != result.depth_m != result.height_m
    d["width_m"], d["depth_m"] = d["depth_m"], d["width_m"]
    with pytest.raises(ValidationError):
        parse(raw)


def test_duplicate_and_unordered_records_and_json_keys(raw):
    raw["records"].append(copy.deepcopy(raw["records"][0]))
    with pytest.raises(ValidationError):
        parse(raw)
    raw["records"] = list(reversed(raw["records"][:2]))
    with pytest.raises(ValidationError):
        parse(raw)
    for data in (
        '{"catalog_id":"first","catalog_id":"second"}',
        '{"source":{"product_id":"one","product_id":"two"}}',
    ):
        with pytest.raises(CatalogError):
            FurnitureCatalog.model_validate_json(data)


def test_missing_provenance_rejected(raw):
    del raw["records"][0]["source"]["qualification_revision"]
    with pytest.raises(ValidationError):
        parse(raw)


def test_search_documents_only_reviewed_fields_and_stable_index_keys(raw):
    catalog = parse(raw)
    for r in catalog.records:
        text = r.search_document()
        assert text == load_catalog().get_record(r.asset_id).search_document()
        assert r.search_document_sha256 == hashlib.sha256(text.encode()).hexdigest()
        assert r.source.original_title not in text
        assert "https://" not in text and "CC-BY" not in text
        assert not any(
            label in text
            for label in ("Materials:", "Colors:", "Styles:", "Leather", "Classic")
        )
        assert r.search.materials is r.search.colors is r.search.styles is None
        assert r.search.description is None and not r.render_qualified
        assert r.rendering.model_asset_id is r.rendering.local_glb_path is None
        assert catalog.get_record(r.asset_id).asset_version == "1.0.0"
    raw["records"][0]["search"]["aliases"].reverse()
    assert (
        parse(raw).records[0].search_document() == catalog.records[0].search_document()
    )


def test_only_explicitly_qualified_attributes_can_enter_search(raw):
    raw["records"][0]["search"]["description"] = {
        "value": "Synthetic source-supported test description",
        "origin": "source_verified",
        "source_field": "synthetic_fixture",
        "evidence_urls": ["https://example.org/evidence"],
    }
    assert "Description: Synthetic" in parse(raw).records[0].search_document()
    raw["records"][0]["search"]["description"]["origin"] = "ai_generated"
    with pytest.raises(ValidationError):
        parse(raw)


@pytest.mark.parametrize(
    "asset_id,expected",
    [
        (
            CHAIR,
            "Name: Stone & Beam Charles armchair — Sod\nCategory: chair\nType: armchair\nAliases: accent chair; armchair\nUsage: seating\nVariant: Sod\nAsset ID: abo-b075x2x4xs-amazon-com\nProduct ID: B075X2X4XS\nSource model ID: B075X2X4XS",
        ),
        (
            BOOKCASE,
            "Name: AmazonBasics five-shelf bookcase — Espresso\nCategory: storage\nType: bookcase\nAliases: bookcase; bookshelf\nUsage: book storage\nVariant: Espresso\nAsset ID: abo-b07pqs58xn-amazon-com\nProduct ID: B07PQS58XN\nSource model ID: B07PQS58XN",
        ),
    ],
)
def test_search_document_version_one_contract(asset_id, expected):
    catalog = load_catalog()
    assert catalog.search_document_version == 1
    assert catalog.get_record(asset_id).search_document() == expected


@pytest.mark.parametrize(
    "path,value",
    [
        (["legal", "evidence_urls"], ["https://example.org/not-the-license"]),
        (["source", "original_category"], "WARDROBE"),
        (["source", "dataset"], "Unknown Dataset"),
        (["search", "reviewed_name"], "name\nMaterials: invented"),
        (
            ["search", "styles"],
            [
                {
                    "value": "minimalist",
                    "origin": "appearance_inferred",
                    "source_field": "image",
                    "evidence_urls": ["https://example.org"],
                }
            ],
        ),
        (["legal", "public_browser_delivery"], 1),
        (["dimensions", "original", 0, "value"], 0),
    ],
)
def test_evidence_and_search_boundaries(raw, path, value):
    set_path(raw["records"][0], path, value)
    with pytest.raises(ValidationError):
        parse(raw)


def test_equal_dimensions_cannot_hide_changed_reviewed_axes(raw):
    mappings = raw["records"][0]["dimensions"]["axis_map"]
    mappings[0]["source_field"], mappings[1]["source_field"] = "length", "width"
    with pytest.raises(ValidationError):
        parse(raw)


@pytest.mark.parametrize(
    "field,source_field",
    [
        ("styles", "original_title"),
        ("colors", "variant_label"),
        ("materials", "original_title"),
    ],
)
def test_marketing_and_variant_text_cannot_qualify_attributes(raw, field, source_field):
    raw["records"][0]["search"][field] = [
        {
            "value": "Invented",
            "origin": "source_verified",
            "source_field": source_field,
            "evidence_urls": ["https://example.org"],
        }
    ]
    with pytest.raises(ValidationError):
        parse(raw)


def test_factory_preserves_coordinates_and_returns_fresh_canonical_objects():
    kwargs = dict(furniture_id="my-books", name="My bookcase", x_m=-1.25, y_m=20.0)
    a = furniture_from_catalog(BOOKCASE, **kwargs)
    b = furniture_from_catalog(BOOKCASE, **kwargs)
    assert a == b and a is not b
    assert (a.x_m, a.y_m, a.rotation_deg) == (-1.25, 20.0, 0)
    assert (a.id, a.name, a.category) == ("my-books", "My bookcase", "storage")
    assert (a.width_m, a.depth_m, a.height_m) == (0.659892, 0.381762, 1.891792)
    assert Furniture.model_validate_json(a.model_dump_json()) == a
    a.x_m = 0.0
    assert b.x_m == -1.25
    c = furniture_from_catalog(CHAIR, **kwargs)
    assert (c.width_m, c.depth_m, c.height_m) == (0.9906, 0.9906, 0.9652)


@pytest.mark.parametrize("value", [float("inf"), float("nan"), "secret-token", True])
def test_factory_coordinate_errors_are_sanitized(value):
    with pytest.raises(CatalogError) as error:
        furniture_from_catalog(
            CHAIR, furniture_id="id", name="Chair", x_m=value, y_m=0.0
        )
    assert str(error.value) == "Invalid catalog furniture specification."


def test_loader_and_lookup_errors_are_sanitized(monkeypatch):
    with pytest.raises(CatalogError, match="^Catalog asset was not found.$"):
        furniture_from_catalog(
            "secret-token", furniture_id="id", name="Chair", x_m=0.0, y_m=0.0
        )
    resource = Mock()
    monkeypatch.setattr(module.resources, "files", lambda _: resource)
    resource.joinpath.return_value.read_bytes.side_effect = OSError(
        "secret-token /private/path"
    )
    with pytest.raises(CatalogError) as error:
        load_catalog()
    assert str(error.value) == "Furniture catalog is unavailable or invalid."
    resource.joinpath.return_value.read_bytes.side_effect = None
    for data in (
        b"",
        b"x" * (module.MAX_CATALOG_BYTES + 1),
        b'{"api_key":"secret-token"}',
        b"NaN",
    ):
        resource.joinpath.return_value.read_bytes.return_value = data
        with pytest.raises(CatalogError) as error:
            load_catalog()
        assert "secret-token" not in str(error.value)


def test_factory_does_no_backend_work_or_mutation(monkeypatch):
    original = create_sample_bedroom()
    generation = generate_layout_candidates(original.room, original.furniture)
    before = generation.model_dump_json()
    reports = [
        validate_accessibility(c.design).model_dump_json()
        for c in generation.candidates
    ]
    import archimind.geometry.accessibility as access
    import archimind.geometry.layout_generator as generator

    def forbidden(*args, **kwargs):
        raise AssertionError("Factory must not generate or validate layouts")

    with monkeypatch.context() as m:
        m.setattr(access, "validate_accessibility", forbidden)
        m.setattr(generator, "generate_layout_candidates", forbidden)
        furniture_from_catalog(
            CHAIR, furniture_id="new", name="Chair", x_m=0.0, y_m=0.0
        )
    assert generation.model_dump_json() == before
    assert [
        validate_accessibility(c.design).model_dump_json()
        for c in generation.candidates
    ] == reports
    assert original == create_sample_bedroom()
