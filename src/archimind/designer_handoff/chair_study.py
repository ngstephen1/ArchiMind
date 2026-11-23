"""Draw three chair operating states from a saved Town bedroom manifest."""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Annotated
from xml.etree import ElementTree as ET

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from archimind.designer_handoff.drawings import (
    DOOR,
    GLASS,
    INK,
    MUTED,
    WOOD,
    _element,
    _line,
    _rect,
    _room_design,
    _sheet,
    _text,
)
from archimind.geometry import validate_accessibility
from archimind.geometry.accessibility import AccessibilityConfig
from archimind.models import Furniture, RoomDesign

Length = Annotated[FiniteFloat, Field(gt=0)]
Offset = Annotated[FiniteFloat, Field(ge=0)]
MIN_TUCK_M = 0.15
PULLOUT_M = 0.30
TOLERANCE_M = 1e-9


class ChairFieldRecord(BaseModel):
    """Physical measurements keyed to one saved project, revision and pair."""

    model_config = ConfigDict(extra="forbid")
    project: str = Field(min_length=1)
    revision: int = Field(gt=0)
    home_id: str = Field(min_length=1)
    chair_id: str
    desk_id: str
    recorded_on: date
    source: str = Field(min_length=1)
    clear_width_m: Length
    clear_height_m: Length
    clear_depth_m: Length
    opening_offset_from_desk_west_m: Offset
    chair_width_m: Length
    chair_depth_m: Length
    chair_arm_height_m: Length


def _front_side(chair: Furniture, desk: Furniture) -> int:
    if not (
        desk.x_m <= chair.x_m and chair.x_m + chair.width_m <= desk.x_m + desk.width_m
    ):
        raise ValueError("The saved chair does not align within the desk reservation.")
    if chair.y_m >= desk.y_m + desk.depth_m - TOLERANCE_M:
        return 1
    if chair.y_m + chair.depth_m <= desk.y_m + TOLERANCE_M:
        return -1
    raise ValueError("The saved chair must start outside the desk reservation.")


def _rear_gap(chair, side, room, obstacles):
    rear = chair.y_m + chair.depth_m if side == 1 else chair.y_m
    candidates = [room.depth_m - rear if side == 1 else rear]
    for obstacle in obstacles:
        if not (
            chair.x_m < obstacle.x_m + obstacle.width_m
            and obstacle.x_m < chair.x_m + chair.width_m
        ):
            continue
        low, high = obstacle.y_m, obstacle.y_m + obstacle.depth_m
        if side == 1 and high > rear:
            candidates.append(max(0, low - rear))
        elif side == -1 and low < rear:
            candidates.append(max(0, rear - high))
    return max(0, min(candidates))


def _physical_fit(board, chair, desk, record):
    if record is None:
        return "awaiting verification", [
            "Measure the desk's clear width, underside height and usable knee depth.",
            "Measure chair width, depth and top of arms. Key each value to the field record.",
        ]
    if (
        record.project,
        record.revision,
        record.home_id,
        record.chair_id,
        record.desk_id,
    ) != (board["project"], board["revision"], board["home_id"], chair.id, desk.id):
        raise ValueError("The chair measurements do not belong to this saved pair.")
    x = desk.x_m + record.opening_offset_from_desk_west_m
    opening_end = x + record.clear_width_m
    if (
        opening_end > desk.x_m + desk.width_m + TOLERANCE_M
        or record.clear_height_m > desk.height_m + TOLERANCE_M
        or record.clear_depth_m > desk.depth_m + TOLERANCE_M
        or record.chair_width_m > chair.width_m + TOLERANCE_M
        or record.chair_depth_m > chair.depth_m + TOLERANCE_M
        or record.chair_arm_height_m > chair.height_m + TOLERANCE_M
    ):
        return "awaiting verification", [
            "Field measurements and model reservations disagree. Confirm the saved objects before checking fit."
        ]
    physical_chair_x = chair.x_m + (chair.width_m - record.chair_width_m) / 2
    failures = []
    if (
        physical_chair_x < x - TOLERANCE_M
        or physical_chair_x + record.chair_width_m > opening_end + TOLERANCE_M
    ):
        failures.append(
            "The chair width at the modeled centerline exceeds the measured opening."
        )
    if record.chair_arm_height_m >= record.clear_height_m - TOLERANCE_M:
        failures.append(
            "The measured chair arms have no vertical clearance under the desk."
        )
    front_setback = (chair.depth_m - record.chair_depth_m) / 2
    if record.clear_depth_m + TOLERANCE_M < MIN_TUCK_M - front_setback:
        failures.append("The measured knee depth cannot accommodate the modeled tuck.")
    return (
        ("measured interference", failures)
        if failures
        else (
            "measured fit at modeled position",
            [
                "Width, arm height and knee-depth checks passed for the supplied pair and modeled alignment."
            ],
        )
    )


def bedroom_board(snapshot: dict) -> dict:
    """Keep floor-standing dressing from a raw saved Town API snapshot."""
    if "home" not in snapshot:
        return snapshot
    home = snapshot["home"]
    return {
        "project": snapshot["project"],
        "revision": snapshot["revision"],
        "home_id": home["id"],
        "rooms": [
            {**part["design"], "dressing": part.get("style", {}).get("dressing", [])}
            for part in home["rooms"]
        ],
    }


def chair_study(
    board: dict, *, record: ChairFieldRecord | None = None, passage_m: float = 0.6
):
    design = _room_design(board)
    items = {item.id: item for item in design.furniture}
    try:
        chair, desk = items["desk-chair"], items["belaya"]
    except KeyError as error:
        raise ValueError(
            "The saved room needs its Belaya desk and writing chair."
        ) from error
    if min(chair.depth_m, desk.depth_m) <= MIN_TUCK_M:
        raise ValueError("The saved reservations are too shallow for the modeled tuck.")
    side = _front_side(chair, desk)
    fit, findings = _physical_fit(board, chair, desk, record)
    floor_dressing = [
        Furniture(
            id="decor:" + item["id"],
            name=item["kind"],
            category="decor",
            **{k: item[k] for k in ("x_m", "y_m", "width_m", "depth_m", "height_m")},
        )
        for item in next(r for r in board["rooms"] if r["room"]["id"] == "bedroom").get(
            "dressing", []
        )
        if item["kind"] in {"plant", "floor_lamp", "accent"}
    ]
    obstacles = [
        item for item in design.furniture if item.id != chair.id
    ] + floor_dressing
    config = AccessibilityConfig(walking_clearance_m=passage_m)
    if side == 1:
        tucked_y = desk.y_m + desk.depth_m - MIN_TUCK_M
    else:
        tucked_y = desk.y_m + MIN_TUCK_M - chair.depth_m

    rows = []
    for key, y in (
        ("tucked-in", tucked_y),
        ("occupied", chair.y_m),
        ("pulled-back", chair.y_m + side * PULLOUT_M),
    ):
        moved = chair.model_copy(update={"y_m": y})
        projected = moved
        if key == "tucked-in":
            # The desk remains an obstacle. Its footprint covers the inserted portion of the chair.
            projected = moved.model_copy(
                update={
                    "y_m": desk.y_m + desk.depth_m + TOLERANCE_M if side == 1 else y,
                    "depth_m": chair.depth_m - MIN_TUCK_M - TOLERANCE_M,
                }
            )
        layout = RoomDesign(room=design.room, furniture=[*obstacles, projected])
        report = validate_accessibility(layout, config=config)
        rear_gap = _rear_gap(moved, side, design.room, obstacles)
        rows.append(
            {
                "state": key,
                "chair": moved.model_dump(mode="json"),
                "rear_gap_m": round(rear_gap, 3),
                "min_passage_m": config.walking_clearance_m,
                "modeled_room_circulation": report.status,
                "modeled_failures": [
                    violation.message
                    for violation in report.violations
                    if violation.severity == "error"
                ],
                "modeled_rear_gap": "passed"
                if rear_gap + TOLERANCE_M >= passage_m
                else "obstructed",
                "physical_tuck": fit if key == "tucked-in" else "not applicable",
            }
        )
    return {
        "project": board["project"],
        "home_id": board["home_id"],
        "revision": board["revision"],
        "desk_id": desk.id,
        "chair_id": chair.id,
        "model": {
            "tuck_m": MIN_TUCK_M,
            "pullout_from_occupied_m": PULLOUT_M,
            "occupied_basis": "Saved chair footprint as an occupied-position proxy. Body reach was not measured.",
            "rear_gap_basis": "Straight gap from the chair back across its width; room circulation is checked separately.",
        },
        "field_record": record.model_dump(mode="json") if record is not None else None,
        "physical_findings": findings,
        "states": rows,
    }


def draw_study(board, report):
    design = _room_design(board)
    room = design.room
    # A measured furniture record can still be attached to a demonstration room.
    svg = _sheet(
        board,
        "demonstration",
        "Desk and chair operating study",
        402,
        source_label="Saved Town geometry",
    )
    scale = min(320 / room.width_m, 245 / room.depth_m)
    for index, state in enumerate(report["states"]):
        x, base = 40 + index * 380, 455
        _text(svg, x, 181, state["state"].replace("-", " ").title(), 22)
        _rect(
            svg,
            x,
            base - room.depth_m * scale,
            room.width_m * scale,
            room.depth_m * scale,
            "#f1ece1",
        )
        for opening in [*room.doors, *room.windows]:
            color = GLASS if opening in room.windows else DOOR
            if opening.wall in {"east", "west"}:
                wall_x = x + (room.width_m * scale if opening.wall == "east" else 0)
                y = base - opening.offset_m * scale
                _line(
                    svg,
                    wall_x,
                    y,
                    wall_x,
                    y - opening.width_m * scale,
                    color=color,
                    weight=4,
                )
            else:
                wall_y = base - (room.depth_m * scale if opening.wall == "north" else 0)
                start = x + opening.offset_m * scale
                _line(
                    svg,
                    start,
                    wall_y,
                    start + opening.width_m * scale,
                    wall_y,
                    color=color,
                    weight=4,
                )
        saved = [
            item.model_dump()
            for item in design.furniture
            if item.id != report["chair_id"]
        ]
        for item in [*saved, state["chair"]]:
            active = item["id"] == report["chair_id"]
            node = _rect(
                svg,
                x + item["x_m"] * scale,
                base - (item["y_m"] + item["depth_m"]) * scale,
                item["width_m"] * scale,
                item["depth_m"] * scale,
                "#88b3a4" if active else WOOD,
                **{"data-object": item["id"]},
            )
            _element(node, "title").text = item["name"]
        _text(
            svg,
            x,
            485,
            f"Rear gap {state['rear_gap_m']:.3f} m · target {state['min_passage_m']:.2f} m",
        )
        _text(
            svg,
            x,
            512,
            f"Modeled room circulation · {state['modeled_room_circulation']}",
        )
        _text(svg, x, 539, f"Modeled rear gap · {state['modeled_rear_gap']}")
        if state["state"] == "tucked-in":
            _text(svg, x, 566, "Physical tuck · " + state["physical_tuck"], color=MUTED)
    _text(svg, 40, 608, report["model"]["occupied_basis"], 14)
    _text(svg, 40, 631, report["model"]["rear_gap_basis"], 14)
    for index, finding in enumerate(report["physical_findings"]):
        _text(svg, 40, 654 + 20 * index, finding, 14, INK)
    return ET.tostring(svg, encoding="unicode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--field-record", type=Path)
    parser.add_argument("--passage-m", type=float, default=0.6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    board = bedroom_board(json.loads(args.manifest.read_bytes()))
    record = (
        ChairFieldRecord.model_validate_json(args.field_record.read_bytes())
        if args.field_record
        else None
    )
    report = chair_study(board, record=record, passage_m=args.passage_m)
    args.output.mkdir(parents=True)
    (args.output / "chair-operation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    (args.output / "chair-operation.svg").write_text(draw_study(board, report))


if __name__ == "__main__":
    main()
