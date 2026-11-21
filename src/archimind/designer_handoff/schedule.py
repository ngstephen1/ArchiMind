"""Prepare revision-bound procurement and measured operational schedules."""

import csv
import json
import math
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Record(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class SupplierItem(_Record):
    """One documented product per placed reservation; quantities are derived."""

    category: str = Field(min_length=1)
    manufacturer: str = Field(min_length=1)
    model: str = Field(min_length=1)
    supplier: str = Field(min_length=1)
    source: str = Field(min_length=1)
    as_of: date
    finish: str = Field(min_length=1)
    availability: str = Field(min_length=1)
    dimensions_m: tuple[Decimal, Decimal, Decimal]
    unit_price: Decimal | None = Field(default=None, ge=0)
    selection: Literal["specified", "substitution", "retained", "custom"] = "specified"

    @model_validator(mode="after")
    def valid_dimensions(self):
        if any(value <= 0 for value in self.dimensions_m):
            raise ValueError("Supplier dimensions must be positive.")
        if self.selection == "retained" and self.unit_price not in (None, Decimal(0)):
            raise ValueError(
                "Account for work on retained items as a separate allowance."
            )
        return self


class Finish(_Record):
    """Order quantity is supplied by the estimator, independently of face area."""

    specification: str = Field(min_length=1)
    supplier: str = Field(min_length=1)
    source: str = Field(min_length=1)
    as_of: date
    unit: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class Allowance(_Record):
    label: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    basis: str = Field(min_length=1)


class DeskFit(_Record):
    """Minimum opening and highest chair part that must pass through it."""

    chair: str = Field(min_length=1)
    desk: str = Field(min_length=1)
    source: str = Field(min_length=1)
    clear_width_m: Decimal = Field(gt=0)
    underside_height_m: Decimal = Field(gt=0)
    chair_passage_width_m: Decimal = Field(gt=0)
    chair_passage_height_m: Decimal = Field(gt=0)


class SupplierData(_Record):
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    items: dict[str, SupplierItem] = Field(default_factory=dict)
    finishes: dict[Literal["floor", "walls", "ceiling"], Finish] = Field(
        default_factory=dict
    )
    allowances: list[Allowance] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    desk_fit: list[DeskFit] = Field(default_factory=list)

    @model_validator(mode="after")
    def currency_for_money(self):
        if not self.currency and (
            self.allowances
            or any(
                i.unit_price is not None
                for i in (*self.items.values(), *self.finishes.values())
            )
        ):
            raise ValueError(
                "A single reporting currency is required for priced entries."
            )
        if any(not line.strip() for line in self.exclusions):
            raise ValueError("Each exclusion needs a description.")
        return self


def _csv(path, rows, fields):
    """Keep text entered by a supplier literal when opened in a spreadsheet."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: "'" + value
                    if isinstance(value, str) and re.match(r"^\s*[=+@-]", value)
                    else value
                    for field, value in row.items()
                }
            )


def _money(amount):
    return format(amount, "f")


def write_schedule(
    room: dict,
    supplier_data: dict,
    output_dir: Path,
    *,
    project: str,
    revision: int,
    home_id: str,
) -> dict:
    """Write validated commercial records into the caller's staged revision directory."""
    data = SupplierData.model_validate(supplier_data)
    if (
        not project.strip()
        or not home_id.strip()
        or type(revision) is not int
        or revision < 1
    ):
        raise ValueError(
            "A project, positive saved revision and design identifier are required."
        )
    stamp = dict(
        project=project, revision=revision, home_id=home_id, room=room["room"]["id"]
    )
    placed = {}
    for item in room["furniture"]:
        key = item["id"]
        if not key or key in placed:
            raise ValueError(f"Duplicate or empty furniture ID: {key!r}")
        placed[key] = item
    if unknown := data.items.keys() - placed.keys():
        raise ValueError(f"Supplier records have no reservation: {sorted(unknown)}")
    rows = []
    subtotal = Decimal(0)
    unpriced = []
    for key, item in placed.items():
        spec = data.items.get(key)
        reserved = tuple(
            Decimal(str(item[k])) for k in ("width_m", "depth_m", "height_m")
        )
        if any(not v.is_finite() or v <= 0 for v in reserved):
            raise ValueError(f"Invalid reservation dimensions for {key}.")
        if spec and (
            spec.category != item["category"]
            or any(
                d > limit for d, limit in zip(spec.dimensions_m, reserved, strict=True)
            )
        ):
            raise ValueError(
                f"{key}: proposed item exceeds the reservation or changes category."
            )
        price = spec.unit_price if spec else None
        if spec and spec.selection == "retained":
            price = Decimal(0)
        if price is None:
            unpriced.append(key)
        else:
            subtotal += price
        rows.append(
            dict(
                **stamp,
                furniture_id=key,
                reservation_name=item["name"],
                category=item["category"],
                selection=spec.selection if spec else "unspecified",
                quantity=1,
                reserved_width_m=reserved[0],
                reserved_depth_m=reserved[1],
                reserved_height_m=reserved[2],
                **{
                    k: getattr(spec, k) if spec else ""
                    for k in (
                        "manufacturer",
                        "model",
                        "supplier",
                        "source",
                        "as_of",
                        "finish",
                        "availability",
                    )
                },
                **{
                    k: spec.dimensions_m[i] if spec else ""
                    for i, k in enumerate(
                        ("product_width_m", "product_depth_m", "product_height_m")
                    )
                },
                price_status="quote_required"
                if price is None
                else "retained"
                if spec.selection == "retained"
                else "priced",
                unit_price=price,
                currency=data.currency,
            )
        )
    checks = []

    def check(check_type, item_ids, result, measurement, source, outstanding):
        checks.append(
            dict(
                **stamp,
                check=check_type,
                item_ids=item_ids,
                result=result,
                measurement=measurement,
                source=source,
                outstanding=outstanding,
            )
        )

    pairs = {}
    for fit in data.desk_fit:
        pair = (fit.chair, fit.desk)
        if pair in pairs or any(
            placed.get(key, {}).get("category") != kind
            for key, kind in zip(pair, ("chair", "desk"), strict=True)
        ):
            raise ValueError(
                f"Ambiguous or missing chair-to-desk measurement IDs: {pair}."
            )
        pairs[pair] = fit
    for chair in (f for f in placed.values() if f["category"] == "chair"):
        for desk in (f for f in placed.values() if f["category"] == "desk"):
            pair = chair["id"], desk["id"]
            ids = " / ".join(pair)
            if all(f.get("rotation_deg") == 0 for f in (chair, desk)):
                gaps = [
                    max(
                        0,
                        chair[axis] - desk[axis] - desk[size],
                        desk[axis] - chair[axis] - chair[size],
                    )
                    for axis, size in (("x_m", "width_m"), ("y_m", "depth_m"))
                ]
                check(
                    "planned footprint gap",
                    ids,
                    "measured",
                    f"{math.hypot(*gaps):.3f} m",
                    "Saved plan reservations",
                    "Verify at site.",
                )
            fit = pairs.get(pair)
            if fit:
                width = fit.clear_width_m - fit.chair_passage_width_m
                height = fit.underside_height_m - fit.chair_passage_height_m
                check(
                    "under-desk opening",
                    ids,
                    "positive margins"
                    if min(width, height) > 0
                    else "interference or zero clearance",
                    f"width margin {width} m; height margin {height} m",
                    fit.source,
                    "Confirm required insertion depth, leg geometry and comfortable use.",
                )
            else:
                check(
                    "under-desk opening",
                    ids,
                    "field verification required",
                    "",
                    "",
                    "Measure clear width, underside height, chair passage envelope and insertion depth.",
                )
    for door in room["room"].get("doors", []):
        check(
            "door swing",
            door["id"],
            "field verification required",
            "",
            "Saved opening",
            "Confirm hinge, leaf, swing direction and swept clearance on site.",
        )
    for key, item in placed.items():
        if item["category"] in {"desk", "storage", "wardrobe", "table", "bed"}:
            check(
                "operating envelope",
                key,
                "field verification required",
                "",
                "",
                "Confirm moving parts, full extension and the adjacent walking route.",
            )
    shell = room["room"]
    width, depth, height = (
        Decimal(str(shell[k])) for k in ("width_m", "depth_m", "ceiling_height_m")
    )
    areas = {
        "floor": width * depth,
        "walls": 2 * (width + depth) * height,
        "ceiling": width * depth,
    }
    finishes = []
    finish_total = Decimal(0)
    unpriced_finishes = []
    for face, gross_area in areas.items():
        spec = data.finishes.get(face)
        amount = None
        if spec and spec.unit_price is not None:
            amount = spec.quantity * spec.unit_price
            finish_total += amount
        else:
            unpriced_finishes.append(face)
        finishes.append(
            dict(
                **stamp,
                surface=face,
                gross_face_area_m2=gross_area,
                basis="Saved rectangular shell; wall openings included. Verify net area, waste, coats and pack size.",
                **{
                    k: getattr(spec, k) if spec else ""
                    for k in (
                        "specification",
                        "supplier",
                        "source",
                        "as_of",
                        "quantity",
                        "unit",
                        "unit_price",
                    )
                },
                extended_price=amount,
                currency=data.currency,
                price_status="quote_required" if amount is None else "priced",
            )
        )
    allowance_total = sum((a.amount for a in data.allowances), Decimal(0))
    summary = dict(
        **stamp,
        currency=data.currency,
        priced_furniture_subtotal=_money(subtotal),
        allowances=[
            {"label": a.label, "amount": _money(a.amount), "basis": a.basis}
            for a in data.allowances
        ],
        allowance_subtotal=_money(allowance_total),
        priced_finish_subtotal=_money(finish_total),
        unpriced_finish_surfaces=unpriced_finishes,
        known_amount_including_allowances=_money(
            subtotal + finish_total + allowance_total
        ),
        unpriced_furniture_ids=unpriced,
        exclusions=data.exclusions,
        commercial_scope="One item per saved reservation. Totals cover only documented furniture, finish orders and explicit allowances.",
        complete_furniture_subtotal=None if unpriced else _money(subtotal),
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    furniture_fields = [
        *stamp,
        "furniture_id",
        "reservation_name",
        "category",
        "selection",
        "quantity",
        "reserved_width_m",
        "reserved_depth_m",
        "reserved_height_m",
        "manufacturer",
        "model",
        "supplier",
        "source",
        "as_of",
        "finish",
        "availability",
        "product_width_m",
        "product_depth_m",
        "product_height_m",
        "price_status",
        "unit_price",
        "currency",
    ]
    _csv(out / "finishes-schedule.csv", finishes, list(finishes[0]))
    _csv(out / "furniture-schedule.csv", rows, furniture_fields)
    _csv(
        out / "operational-checks.csv",
        checks,
        [*stamp, "check", "item_ids", "result", "measurement", "source", "outstanding"],
    )
    (out / "cost-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary
