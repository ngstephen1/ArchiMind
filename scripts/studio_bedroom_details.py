"""Draw an editable bedroom window and bed-wall study from a Town manifest."""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from studio_bedroom_dims import (
    EXTERIOR_REVEAL_M,
    FRAME_DEPTH_M,
    SILL_DEPTH_M,
    SILL_THICKNESS_M,
    WALL_DEPTH_M,
    saved_curtain_mount,
)

from archimind.designer_handoff.drawings import (
    GLASS,
    MUTED,
    WOOD,
    _dimension,
    _line,
    _rect,
    _room_design,
    _sheet,
    _text,
)


def _detail_board(manifest: dict) -> dict:
    """Accept either the whole-home scene or Town's standalone bedroom export."""
    if "rooms" in manifest:
        saved_bed = next(
            (
                item
                for item in (manifest.get("bedroom") or {}).get("furniture", [])
                if item["id"] == "queen-bed"
            ),
            None,
        )
        if saved_bed and saved_bed.get("source") is not None:
            raise ValueError("The bed-head study requires the procedural queen bed.")
        return manifest
    if (
        manifest.get("schema_version") != 1
        or manifest.get("coordinates")
        != "Bedroom-local metres: +X east, +Y north, +Z up"
        or manifest.get("room", {}).get("id") != "bedroom"
    ):
        raise ValueError("Supply a Town scene manifest or a version-1 bedroom export.")
    furniture = []
    for item in manifest["furniture"]:
        if item["id"] != "queen-bed":
            continue
        if item.get("source") is not None:
            raise ValueError("The bed-head study requires the procedural queen bed.")
        x, y = item["footprint_xy_m"]
        width, depth, height = item["reservation_wdh_m"]
        furniture.append(
            {
                "id": item["id"],
                "name": item["name"],
                "category": "bed",
                "x_m": x,
                "y_m": y,
                "width_m": width,
                "depth_m": depth,
                "height_m": height,
                "rotation_deg": item["rotation_deg"],
            }
        )
    return {
        **manifest,
        "rooms": [{"room": manifest["room"], "furniture": furniture}],
    }


def rendered_mount(board, room, window, receipt):
    if any(
        board[key] != receipt.get(key) for key in ("project", "revision", "home_id")
    ):
        raise ValueError("The styled render receipt belongs to another revision.")
    bedroom = receipt.get("rooms", {}).get("bedroom", {})
    curtain_id = f"curtain:{window.id}"
    saved = next(
        (
            item
            for item in bedroom.get("saved_dressing", [])
            if item["id"] == curtain_id
        ),
        None,
    )
    mount = bedroom.get("modeled_curtain_mounts", {}).get(curtain_id)
    if (
        not saved
        or saved["wall"] != window.wall
        or mount != saved_curtain_mount(room.model_dump(), saved)
    ):
        raise ValueError("The render receipt has no matching modeled curtain mount.")
    return mount


def study(board: dict, *, render_receipt: dict | None = None) -> tuple[str, dict]:
    board = _detail_board(board)
    design = _room_design(board)
    room = design.room
    try:
        window = next(
            opening for opening in room.windows if opening.id == "bedroom-window"
        )
        bed = next(item for item in design.furniture if item.id == "queen-bed")
    except StopIteration as exc:
        raise ValueError(
            "The revision needs the identified bedroom window and bed."
        ) from exc
    if bed.category != "bed":
        raise ValueError("The bed-head study requires the procedural queen bed.")
    sill, head = window.sill_height_m, window.sill_height_m + window.height_m
    if head > room.ceiling_height_m - 0.06:
        raise ValueError("The modeled head gap is too small for this mounting study.")
    rail = min(head + 0.16, room.ceiling_height_m - 0.12)
    span = room.depth_m if window.wall in {"east", "west"} else room.width_m
    rail_left = max(0.0, window.offset_m - 0.14)
    rail_right = min(span, window.offset_m + window.width_m + 0.14)

    mount = (
        rendered_mount(board, room, window, render_receipt)
        if render_receipt is not None
        else None
    )
    mounting_label = "Proposed track datum"
    if mount:
        rail = mount["elevation_m"]
        rail_left = mount["start_m"]
        rail_right = rail_left + mount["span_m"]
        mounting_label = "Modeled track underside"

    # Town's unrotated procedural queen-bed template places the head at +Y.
    head_y = bed.y_m + bed.depth_m
    head_gap = room.depth_m - head_y
    svg = _sheet(
        board,
        "demonstration",
        "Bedroom window and bed head",
        401,
        source_label="Saved Town geometry and modeled detail",
    )
    _text(svg, 40, 184, f"Window elevation · {window.id} · {window.wall} wall", 21)
    _text(svg, 620, 184, "Bed head and north wall · plan", 21)

    s = min(
        300 / room.ceiling_height_m, 230 / max(window.width_m, rail_right - rail_left)
    )
    center = 300
    finish_floor = 544
    x = center - window.width_m * s / 2
    y_head = finish_floor - head * s
    y_sill = finish_floor - sill * s
    _line(svg, 65, finish_floor, 540, finish_floor, MUTED)
    _rect(svg, x, y_head, window.width_m * s, window.height_m * s, "#e2edf0", GLASS)
    _line(svg, center, y_head, center, y_sill, GLASS)
    _rect(
        svg,
        x - 0.035 * s,
        y_sill,
        (window.width_m + 0.07) * s,
        SILL_THICKNESS_M * s,
        WOOD,
    )
    y_rail = finish_floor - rail * s
    left = x + (rail_left - window.offset_m) * s
    right = x + (rail_right - window.offset_m) * s
    _line(svg, left, y_rail, right, y_rail, MUTED, 2, **{"stroke-dasharray": "5 3"})
    _text(
        svg,
        40,
        217,
        f"{mounting_label} +{rail:.3f} m · {rail_right - rail_left:.3f} m span",
        14,
    )
    _text(svg, 40, 238, f"Saved head +{head:.3f} m · sill +{sill:.3f} m", 14)
    if mount:
        _text(
            svg,
            40,
            579,
            f"Rail section {mount['rail_size_m'] * 1000:.0f} mm square · "
            f"center {mount['wall_projection_m'] * 1000:.0f} mm from wall",
            14,
        )
    _dimension(svg, x, y_sill + 30, x + window.width_m * s, f"{window.width_m:.3f} m")

    scale = min(460 / room.width_m, 320 / room.depth_m)
    px = 620
    py = 544
    _rect(
        svg,
        px,
        py - room.depth_m * scale,
        room.width_m * scale,
        room.depth_m * scale,
        "#f1ece1",
    )
    bed_x = px + bed.x_m * scale
    bed_top = py - head_y * scale
    _rect(svg, bed_x, bed_top, bed.width_m * scale, bed.depth_m * scale, WOOD)
    _line(svg, bed_x, bed_top, bed_x + bed.width_m * scale, bed_top, MUTED, 3)
    _text(svg, bed_x + 6, bed_top + 21, bed.id, 13)
    _dimension(svg, bed_x, py + 24, bed_x + bed.width_m * scale, f"{bed.width_m:.3f} m")
    _text(
        svg,
        620,
        595,
        f"Bed head to north wall · {head_gap:.3f} m in the saved layout",
        14,
    )

    _text(
        svg,
        40,
        616,
        f"Renderer assembly · {WALL_DEPTH_M:.3f} m wall, {FRAME_DEPTH_M:.3f} m frame,",
        14,
    )
    _text(
        svg,
        40,
        637,
        f"{SILL_DEPTH_M:.3f} m deep × {SILL_THICKNESS_M:.3f} m sill · {EXTERIOR_REVEAL_M:.3f} m modeled exterior reveal.",
        14,
    )
    _text(
        svg,
        40,
        669,
        "Confirm glazing position, sill construction, track fixing and bed-head services before specification.",
        14,
    )
    evidence = {
        "project": board["project"],
        "revision": board["revision"],
        "home_id": board["home_id"],
        "window": {
            "id": window.id,
            "width_m": window.width_m,
            "sill_m": sill,
            "head_m": head,
        },
        "nominal_render_assembly": {
            "wall_depth_m": WALL_DEPTH_M,
            "frame_depth_m": FRAME_DEPTH_M,
            "sill_depth_m": SILL_DEPTH_M,
            "sill_thickness_m": SILL_THICKNESS_M,
            "exterior_reveal_m": EXTERIOR_REVEAL_M,
        },
        "mounting_study": {
            "status": "modeled" if mount else "proposed",
            "track_elevation_m": round(rail, 3),
            "track_span_m": round(rail_right - rail_left, 3),
        },
        "bed": {
            "id": bed.id,
            "head_faces_wall": "north",
            "saved_head_to_wall_m": round(head_gap, 3),
        },
        "field_status": "awaiting verified reveal, sill, mount and bed-head services",
    }
    if mount:
        evidence["mounting_study"]["rendered_geometry"] = mount
    return ET.tostring(svg, encoding="unicode"), evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--render-receipt",
        type=Path,
        help="Saved-style receipt for the selected revision",
    )
    args = parser.parse_args()
    receipt = (
        json.loads(args.render_receipt.read_bytes()) if args.render_receipt else None
    )
    svg, evidence = study(
        json.loads(args.manifest.read_bytes()), render_receipt=receipt
    )
    args.output.mkdir(parents=True)
    (args.output / "window-and-bed-head.svg").write_text(svg, encoding="utf-8")
    (args.output / "window-and-bed-head.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
