"""Offline source-register evidence; no ingestion or runtime catalog promotion."""

import copy
import hashlib
import json
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from retrieval_helpers import offline  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/catalogs/furniture_source_candidates.json"
FROZEN = ROOT / "data/catalogs/furniture_source_candidates_08a.json"
FROZEN_SHA = "cb3d5b7a7382a31ec96ec709f4fdcf6f90d9202275fe41f40c04391dc53ddc5d"
FACTORS = {
    "meters": Decimal(1),
    "centimeters": Decimal(".01"),
    "millimeters": Decimal(".001"),
    "inches": Decimal(".0254"),
}
NEW_ELIGIBLE = {
    "abo-b074l4976t-amazon-co-uk": (
        "desk",
        {"width_m": 1.6, "depth_m": 0.8, "height_m": 0.75},
    ),
    "abo-b07h8jn9qf-amazon-co-uk": (
        "wardrobe",
        {"width_m": 2.0, "depth_m": 0.59, "height_m": 2.12},
    ),
    "abo-b07b4vxxjc-amazon-com": (
        "table",
        {"width_m": 0.6096, "depth_m": 0.4318, "height_m": 0.6096},
    ),
}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate research key")
        result[key] = value
    return result


def parse(text):
    def invalid(_):
        raise ValueError("Non-finite research value")

    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid)


def validate(data):
    assert type(data["schema_version"]) is int and data["schema_version"] == 1
    assert data["deployment_target"] == "noncommercial_public_demo"
    old = parse(FROZEN.read_text())
    legacy = {c["candidate_id"]: c for c in old["candidates"]}
    ids = [c["candidate_id"] for c in data["candidates"]]
    assert ids == sorted(set(ids))
    assert len(ids) == 57
    assert data["summary_counts"] == dict(
        Counter(c["decision"] for c in data["candidates"])
    )
    assert data["dimension_status_counts"] == dict(
        Counter(c["dimension_status"] for c in data["candidates"])
    )
    for group, counts in data["category_summary"].items():
        rows = [c for c in data["candidates"] if c["investigation_category"] == group]
        assert counts == dict(
            investigated=len(rows),
            by_decision=dict(Counter(c["decision"] for c in rows)),
        )
    qualified = set()
    for c in data["candidates"]:
        key = c["candidate_id"]
        assert c["decision"] in {
            "eligible_for_acquisition",
            "needs_evidence",
            "excluded",
            "fixture_only",
        }
        assert c["rights_status"] in {"verified", "unknown", "restricted"}
        assert c["dimension_status"] in {"verified", "unknown", "illustrative"}
        if key in legacy:
            assert c == legacy[key]
            continue
        assert c["source_name"] == "Amazon Berkeley Objects"
        identity = c["identity"]
        assert (
            key
            == f"abo-{identity['product_id'].lower()}-{identity['marketplace_domain'].replace('.', '-')}"
        )
        assert identity["kind"] == "real_product_record"
        assert identity["model_id"] == identity["product_id"]
        source = c["source"]
        assert source["model_url"].endswith("/" + identity["model_id"] + ".glb")
        for name in ("metadata_url", "model_url", "model_metadata_url"):
            parsed = urlsplit(source[name])
            assert (
                parsed.scheme == "https"
                and parsed.hostname == "amazon-berkeley-objects.s3.amazonaws.com"
                and not parsed.username
            )
        for name in (
            "metadata_response_sha256",
            "listing_line_sha256_excluding_newline",
            "model_index_sha256",
        ):
            assert len(source[name]) == 64 and all(
                v in "0123456789abcdef" for v in source[name]
            )
        assert source["source_revision"] is None
        assert source["listing_jsonl_line_1_based"] > 0
        dimensions = c["dimensions"]
        originals = {v["source_field"]: v for v in dimensions["original_item_fields"]}
        assert set(originals) == {"width", "length", "height"}
        for field, value in originals.items():
            assert value["unit"] in FACTORS
            assert (
                type(value["value"]) in (int, float)
                and math.isfinite(value["value"])
                and value["value"] > 0
            )
            assert (
                Decimal(str(dimensions["reported_source_field_conversions_m"][field]))
                == Decimal(str(value["value"])) * FACTORS[value["unit"]]
            )
        assert dimensions["original_units"] == sorted(
            {v["unit"] for v in originals.values()}
        )
        if c["dimension_status"] == "verified":
            assert set(dimensions["normalized_m"]) == {"width_m", "depth_m", "height_m"}
            inputs = dimensions["normalization_inputs"]
            assert {v["source"] for v in inputs.values()} == {
                "item_dimensions.width",
                "item_dimensions.length",
                "item_dimensions.height",
            }
            for axis, value in inputs.items():
                assert value["source"].startswith("item_dimensions.")
                assert (
                    Decimal(str(dimensions["normalized_m"][axis]))
                    == Decimal(str(value["value"])) * FACTORS[value["unit"]]
                )
        else:
            assert dimensions["normalized_m"] is None
        technical = c["technical"]
        assert (
            technical["model_sha256"] is None
            and technical["mesh_bounds_min_max"] is None
        )
        assert technical["extensions"] is None
        assert technical["model_bytes_downloaded"] == 0
        assert (
            not technical["anchor_verified_from_model"]
            and not technical["embedded_resources_verified"]
        )
        assert (
            dimensions["model_comparison"] is None
            or not dimensions["model_comparison"]["render_envelope_approved"]
        )
        if c["decision"] == "eligible_for_acquisition":
            qualified.add(key)
            assert (
                c["rights_status"] == "verified" and c["dimension_status"] == "verified"
            )
            assert (
                identity["identity_status"] == "verified_for_acquisition"
                and identity["variant_labels"]
                and identity["manufacturer_model_numbers"]
            )
            rights = c["rights"]
            assert rights["license_identifier"] == "CC-BY-4.0"
            assert (
                rights["public_browser_delivery"]
                and rights["redistribution"]
                and rights["attribution"]
            )
            assert rights["license_url"] in rights["evidence_urls"]
            assert (
                dimensions["evidence_urls"]
                and source["metadata_url"] in dimensions["evidence_urls"]
            )
            assert dimensions["model_comparison"][
                "passes_08c_acquisition_dimension_tolerance"
            ]
            assert technical["model_size_bytes"] <= 15 * 1024 * 1024
            assert (
                max(
                    technical["reported_max_texture_width"],
                    technical["reported_max_texture_height"],
                )
                <= 2048
            )
            assert technical["reported_faces"] <= 100000
            assert not technical["reported_resource_blockers"]
            category, expected = NEW_ELIGIBLE[key]
            assert (
                c["canonical_category"] == category
                and dimensions["normalized_m"] == expected
            )
    assert qualified == NEW_ELIGIBLE.keys()


def test_frozen_08a_and_expanded_register_are_consistent():
    assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == FROZEN_SHA
    validate(parse(REGISTRY.read_text()))


@pytest.mark.parametrize("text", ['{"x": 1, "x": 2}', '{"x":NaN}', '{"x":Infinity}'])
def test_duplicate_keys_and_nonfinite_json_are_rejected(text):
    with pytest.raises(ValueError):
        parse(text)


@pytest.mark.parametrize(
    "path,value",
    [
        (("decision",), "approved"),
        (("rights_status",), "unknown"),
        (("rights", "public_browser_delivery"), False),
        (("rights", "license_url"), "https://invalid.example/license"),
        (("dimensions", "normalized_m", "width_m"), 0),
        (
            ("dimensions", "normalization_inputs", "width_m", "source"),
            "package_dimensions.width",
        ),
        (("dimensions", "original_item_fields", 0, "unit"), "unknown"),
        (("dimensions", "original_item_fields", 0, "value"), float("inf")),
        (("identity", "model_id"), "UNKNOWN123"),
        (("identity", "variant_labels"), []),
        (("technical", "model_sha256"), "f" * 64),
        (("technical", "reported_max_texture_width"), 4096),
        (("canonical_category",), "chair"),
    ],
)
def test_forged_qualification_is_rejected(path, value):
    data = parse(REGISTRY.read_text())
    candidate = next(
        c
        for c in data["candidates"]
        if c["candidate_id"] == "abo-b074l4976t-amazon-co-uk"
    )
    node = candidate
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises((AssertionError, KeyError, TypeError)):
        validate(data)


def test_legacy_edit_duplicate_order_and_bad_counts_rejected():
    original = parse(REGISTRY.read_text())
    for mutation in (
        lambda d: d["candidates"].append(d["candidates"][0]),
        lambda d: d["candidates"].reverse(),
        lambda d: d["summary_counts"].update(eligible_for_acquisition=999),
        lambda d: next(
            c
            for c in d["candidates"]
            if c["candidate_id"] == "abo-b075x2x4xs-amazon-com"
        ).update(name="rewritten historical evidence"),
    ):
        data = copy.deepcopy(original)
        mutation(data)
        with pytest.raises(AssertionError):
            validate(data)


def test_no_wardrobe_bookcase_or_render_promotion():
    from archimind.assets.specifications import catalog_product_options

    current = catalog_product_options()
    assert tuple(o.record.asset_id for o in current) == (
        "abo-b075x2x4xs-amazon-com",
        "abo-b07pqs58xn-amazon-com",
    )
    assert [o.record.asset_id for o in current if o.render_qualified] == [
        current[0].record.asset_id
    ]
    assert sum(o.planning_dimensions is not None for o in current) == 1
    assert not set(NEW_ELIGIBLE) & {o.record.asset_id for o in current}
    display = next(
        c
        for c in parse(REGISTRY.read_text())["candidates"]
        if c["identity"].get("product_id") == "B07H8T8ZS7"
    )
    assert (
        display["decision"] == "excluded" and display["canonical_category"] == "storage"
    )
