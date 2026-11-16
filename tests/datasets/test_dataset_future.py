"""P2b 3D-FUTURE categories on synthetic rows (real data: docs/data/DATASET_FUTURE_P2B.md)."""

import pytest

from archimind.datasets.future import (
    FutureInfoError,
    merge_categories,
    normalize_super_category,
    parse_model_info,
)

BED = "83db09d8-0c4c-4b13-8909-404bdf4ea3ec"
DESK = "19e1a64d-a87f-4d82-8834-5c34b889a059"
MIDI_ONLY = "2a6d5ab2-bb75-462f-ab8f-471b7cc6a9fc"


def info(model_id=BED, super_category="Bed", category="King-size Bed", **extra):
    return {
        "model_id": model_id,
        "super-category": super_category,
        "category": category,
        "style": "Modern",
        "theme": None,
        "material": None,
    } | extra


def test_parse_normalizes_super_categories_and_keeps_fine_categories():
    parsed = parse_model_info(
        [
            info(),
            info(DESK, "Cabinet/Shelf/Desk", "Nightstand"),
            info(MIDI_ONLY, "Others", None),
        ]
    )
    assert parsed.super_categories == {
        BED: "Bed",
        DESK: "Cabinet_Shelf_Desk",
        MIDI_ONLY: "Others",
    }
    assert parsed.fine_categories == {BED: "King-size Bed", DESK: "Nightstand"}


@pytest.mark.parametrize(
    "rows",
    [
        [],
        {"model_id": BED},
        [info(), info()],  # duplicate model id
        [info(model_id="not-a-uuid")],
        [info(super_category="Bathtub")],
        [info(category="Bed\nFrame")],
        [info(category=7)],
        ["not an object"],
    ],
)
def test_parse_rejects_malformed_model_info(rows):
    with pytest.raises(FutureInfoError):
        parse_model_info(rows)


def test_normalize_matches_midi_spelling():
    assert normalize_super_category("Pier/Stool") == "Pier_Stool"
    with pytest.raises(FutureInfoError):
        normalize_super_category(None)


def test_merge_keeps_future_adds_midi_only_and_cross_checks_variants():
    future = {BED: "Bed", DESK: "Cabinet_Shelf_Desk"}
    midi = {BED: "Bed", f"{DESK}-(0.5)": "Cabinet_Shelf_Desk", MIDI_ONLY: "Sofa"}
    merged, report = merge_categories(future, midi)
    assert merged == {BED: "Bed", DESK: "Cabinet_Shelf_Desk", MIDI_ONLY: "Sofa"}
    assert report == {
        "future_models": 2,
        "midi_jids": 3,
        "midi_agrees_with_future": 2,
        "midi_only_jids": 1,
        "merged_jids": 3,
    }


def test_merge_stops_on_disagreement():
    with pytest.raises(FutureInfoError, match="MIDI says Sofa"):
        merge_categories({BED: "Bed"}, {BED: "Sofa"})
