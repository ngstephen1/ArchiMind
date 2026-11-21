import csv
import json
from pathlib import Path

import pytest

from archimind.designer_handoff.schedule import write_schedule


@pytest.fixture
def board():
    return json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs/data/conference-sprint/manifest.json"
        ).read_bytes()
    )


def schedule(board, data, path):
    room = next(r for r in board["rooms"] if r["room"]["id"] == "bedroom")
    return write_schedule(
        room,
        data,
        path,
        project=board["project"],
        revision=board["revision"],
        home_id=board["home_id"],
    )


def supplier():
    return {
        "selection": "substitution",
        "manufacturer": "Test workshop",
        "model": "Chair 2",
        "supplier": "=TEST",
        "source": "Synthetic QA record 1",
        "as_of": "2026-11-21",
        "finish": "Painted oak",
        "availability": "Quoted",
        "category": "chair",
        "dimensions_m": [0.45, 0.50, 0.8],
        "unit_price": "120.50",
    }


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def test_saved_board_without_quotes_preserves_unknowns(board, tmp_path):
    result = schedule(board, {}, tmp_path)
    assert result["complete_furniture_subtotal"] is None
    assert set(result["unpriced_furniture_ids"]) == {
        "belaya",
        "desk-chair",
        "queen-bed",
        "bedside-lamp",
    }
    rows = read(tmp_path / "operational-checks.csv")
    assert all(r["home_id"] == board["home_id"] and r["revision"] == "2" for r in rows)
    assert (
        next(r for r in rows if r["check"] == "planned footprint gap")["measurement"]
        == "0.360 m"
    )
    assert (
        next(r for r in rows if r["check"] == "under-desk opening")["result"]
        == "field verification required"
    )


def test_sourced_substitution_and_costs(board, tmp_path):
    data = {
        "currency": "USD",
        "items": {"desk-chair": supplier()},
        "allowances": [
            {"label": "Delivery", "amount": "49.90", "basis": "Synthetic example"}
        ],
        "exclusions": ["Installation"],
    }
    result = schedule(board, data, tmp_path)
    assert result["known_amount_including_allowances"] == "170.40"
    assert result["complete_furniture_subtotal"] is None
    row = next(
        r
        for r in read(tmp_path / "furniture-schedule.csv")
        if r["furniture_id"] == "desk-chair"
    )
    assert row["supplier"] == "'=TEST"
    assert row["product_width_m"] == "0.45" and row["reserved_width_m"] == "0.48"
    assert row["quantity"] == "1"
    assert all(
        r["price_status"] == "quote_required"
        for r in read(tmp_path / "furniture-schedule.csv")
        if r["furniture_id"] != "desk-chair"
    )


@pytest.mark.parametrize(
    "delta",
    [
        {"dimensions_m": [0.49, 0.4, 0.8]},
        {"dimensions_m": [0.45, 0.4, 0.9]},
        {"category": "table"},
        {"dimensions_m": [0.4, 0, 0.8]},
        {"source": ""},
        {"unit_price": "-10"},
    ],
)
def test_rejects_invalid_substitutions_before_writing(board, tmp_path, delta):
    with pytest.raises(ValueError):
        schedule(
            board,
            {"currency": "USD", "items": {"desk-chair": supplier() | delta}},
            tmp_path,
        )
    assert not list(tmp_path.iterdir())


def test_desk_fit_with_sourced_dimensions_and_explicit_limits(board, tmp_path):
    data = {
        "desk_fit": [
            {
                "chair": "desk-chair",
                "desk": "belaya",
                "source": "QA tape measurements",
                "clear_width_m": 0.49,
                "underside_height_m": 0.55,
                "chair_passage_width_m": 0.48,
                "chair_passage_height_m": 0.55,
            }
        ]
    }
    schedule(board, data, tmp_path)
    row = next(
        r
        for r in read(tmp_path / "operational-checks.csv")
        if r["check"] == "under-desk opening"
    )
    assert row["result"] == "interference or zero clearance"
    assert "insertion depth" in row["outstanding"]
    with pytest.raises(ValueError):
        schedule(board, {"desk_fit": data["desk_fit"] * 2}, tmp_path)


def test_unknown_supplier_id_and_missing_currency_rejected(board, tmp_path):
    for data in (
        {"currency": "USD", "items": {"unknown": supplier()}},
        {"items": {"desk-chair": supplier()}},
    ):
        with pytest.raises(ValueError):
            schedule(board, data, tmp_path)


def test_finish_takeoff_keeps_order_quantity_and_scope_explicit(board, tmp_path):
    floor = dict(
        specification="QA plank",
        supplier="QA",
        source="QA-1",
        as_of="2026-11-20",
        unit="box",
        quantity=12,
        unit_price="31.50",
    )
    result = schedule(
        board, {"currency": "USD", "finishes": {"floor": floor}}, tmp_path
    )
    row = read(tmp_path / "finishes-schedule.csv")[0]
    assert row["gross_face_area_m2"] == "31.388588"
    assert row["quantity"] == "12" and row["unit"] == "box"
    assert result["priced_finish_subtotal"] == "378.00"
    assert result["unpriced_finish_surfaces"] == ["walls", "ceiling"]
