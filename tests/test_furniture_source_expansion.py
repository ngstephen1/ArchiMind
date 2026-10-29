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


RECEIPT = ROOT / "docs/data/FURNITURE_EXPANSION_08F1.json"
PACKET = ROOT / "docs/data/FURNITURE_RETRIEVAL_HUMAN_REVIEW_08F1.md"


def validate_review(review, document):
    assert review["status"] == "pending_human_review_unevaluated"
    assert review["completed_human_reviews"] == 0
    assert (
        not review["benchmark_created"] and not review["existing_benchmarks_modified"]
    )
    assert review["protocol"] == "owner_first_optional_second_reviewer_and_adjudication"
    cases = review["queries"]
    assert len(cases) == review["query_count"] == 24
    assert {q["query_id"] for q in cases} == {
        f"{group}{n:02d}" for group in "CP" for n in range(1, 13)
    }
    assert len({q["prompt"].casefold() for q in cases}) == 24
    for q in cases:
        assert q["authorship"] == "implementation_agent"
        for key in (
            "reviewer_identity_or_role",
            "review_date",
            "hard_eligibility",
            "semantic_relevance",
            "query_outcome",
            "rationale",
            "second_review",
            "adjudication",
        ):
            assert q[key] is None
        assert "score" not in q and "judgments" not in q and "proposed_label" not in q
        assert document.count("### " + q["query_id"] + "\n") == 1
        assert document.count("**Prompt:** " + q["prompt"]) == 1
    assert document.count("| Primary | | | | | | |") == 24
    assert document.count("| Optional second | | | | | | |") == 24
    assert "Completed human reviews: 0" in document
    assert "PENDING HUMAN REVIEW — UNEVALUATED" in document
    assert "not a new gold benchmark" in document


def test_human_packet_is_blank_and_disjoint_from_frozen_queries():
    review = parse(RECEIPT.read_text())["human_review"]
    document = PACKET.read_text()
    validate_review(review, document)
    assert hashlib.sha256(PACKET.read_bytes()).hexdigest() == review["sha256"]
    assert sum(q["scope"] == "current_application" for q in review["queries"]) == 12
    assert sum(q["scope"] == "prospective_discussion" for q in review["queries"]) == 12
    original = set()
    for filename in (
        "furniture_retrieval_queries.json",
        "furniture_embedding_development_08r1.json",
        "furniture_embedding_held_out_08r1.json",
    ):
        original.update(
            " ".join(c["request"]["query"].casefold().split())
            for c in parse((ROOT / "data/benchmarks" / filename).read_text())["cases"]
        )
    assert not original & {
        " ".join(q["prompt"].casefold().split()) for q in review["queries"]
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewer_identity_or_role", "fabricated-owner"),
        ("review_date", "2026-10-29"),
        ("hard_eligibility", "eligible"),
        ("semantic_relevance", "relevant"),
        ("adjudication", "approved"),
    ],
)
def test_fake_human_review_is_rejected(field, value):
    review = parse(RECEIPT.read_text())["human_review"]
    review["queries"][0][field] = value
    with pytest.raises(AssertionError):
        validate_review(review, PACKET.read_text())


def test_source_receipt_budget_stage_counts_and_primary_joins():
    report = parse(RECEIPT.read_text())
    audit = report["transfer_audit"]
    requests = audit["requests"]
    assert len(requests) == audit["implementation_request_count"] == 52
    assert len({r["name"] for r in requests}) == 52
    assert (
        sum(r["body_bytes"] for r in requests)
        == audit["actual_body_bytes"]
        == 9948621
        <= audit["total_limit_bytes"]
        == 10 * 1024 * 1024
    )
    assert (
        max(r["body_bytes"] for r in requests)
        == audit["maximum_response_body_bytes"]
        == 1024 * 1024
    )
    assert (
        sum(r["method"] == "HEAD" for r in requests)
        == audit["model_head_requests"]
        == 30
    )
    for r in requests:
        assert r["url"].startswith("https://") and "error" not in r
        assert r["body_bytes"] <= 1024 * 1024
        if r["url"].endswith(".glb"):
            assert r["method"] == "HEAD" and r["body_bytes"] == 0
        if "listings/metadata/" in r["url"]:
            assert r["status"] == 206 and r["requested_range"]
    coverage = report["coverage"]
    assert (coverage["task_total"], coverage["new_ids"], coverage["revisited_ids"]) == (
        30,
        25,
        5,
    )
    assert coverage["current_task_decisions"] == {
        "eligible_for_acquisition": 3,
        "needs_evidence": 19,
        "excluded": 8,
    }
    assert {k: v["investigated"] for k, v in coverage["by_group"].items()} == {
        "bed": 8,
        "desk": 8,
        "wardrobe_dresser": 8,
        "additional": 6,
    }
    assert (
        coverage["active_packaged_metadata_qualified"],
        coverage["active_planning_envelope_qualified"],
        coverage["active_render_qualified"],
    ) == (2, 1, 1)
    assert not any(
        coverage[k]
        for k in (
            "new_packaged_metadata_qualified",
            "new_planning_envelope_qualified",
            "new_render_qualified",
        )
    )
    registry = {c["candidate_id"]: c for c in parse(REGISTRY.read_text())["candidates"]}
    investigations = report["investigations"]
    assert len(investigations) == len({i["candidate_id"] for i in investigations}) == 30
    assert report["source_excerpts_are_partial"] is True
    assert (
        report["resource_screen"]["shortlist_combined_reported_texture_estimate_bytes"]
        == 192 * 1024 * 1024
    )
    assert (
        report["resource_screen"]["shortlist_combined_estimate_exceeds_scene_limit"]
        is True
    )
    for i in investigations:
        source, model, assessment = (
            i["source_excerpts"],
            i["model_index_row"],
            i["assessment"],
        )
        assert (
            source["3dmodel_id"]
            == model["3dmodel_id"]
            == assessment["identity"]["model_id"]
        )
        assert source["item_id"] == assessment["identity"]["product_id"]
        assert source["domain_name"] == assessment["identity"]["marketplace_domain"]
        assert (
            i["record_sha256"]
            == assessment["source"]["listing_line_sha256_excluding_newline"]
        )
        assert assessment["source"]["model_url"].endswith("/" + model["path"])
        assert all(
            i["future_search_attributes"][k] is None
            for k in ("materials", "colors", "styles", "description")
        )
        if i["is_new"]:
            assert assessment == registry[i["candidate_id"]]
        for original in assessment["dimensions"]["original_item_fields"]:
            value = source["item_dimensions"][original["source_field"]]
            assert (original["value"], original["unit"]) == (
                value["value"],
                value["unit"],
            )
    assert {
        c["candidate_id"] for c in report["new_acquisition_shortlist"]
    } == NEW_ELIGIBLE.keys()
    assert not report["material_corrections_to_historical_evidence"]
    assert all(
        r["original_record_unchanged"] and not r["qualification_outcome_changed"]
        for r in report["reassessments"]
    )


def test_production_and_frozen_artifacts_and_historical_report_are_preserved():
    report = parse(RECEIPT.read_text())
    pins = report["preservation"]
    assert pins["verified_count"] == len(pins["baseline_files"]) == 142
    for path, expected in pins["baseline_files"].items():
        file = (ROOT / path).resolve()
        assert file.is_relative_to(ROOT) and not path.startswith(
            (".agents/", ".claude/")
        )
        assert hashlib.sha256(file.read_bytes()).hexdigest() == expected
    register = (ROOT / "docs/data/FURNITURE_SOURCE_REGISTER.md").read_text()
    start = register.index("# Furniture source qualification register — Task 08A")
    end = register.index("\n\n---\n\n# 08F1", start)
    assert (
        hashlib.sha256(register[start:end].encode()).hexdigest()
        == report["historical_snapshot"]["historical_register_body_sha256"]
    )
