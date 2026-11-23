"""Plot the selected rectangular bedroom from a Town board, in room-local metres."""

import hashlib
from math import isclose
from pathlib import Path
from xml.etree import ElementTree as ET

from archimind.designer_handoff.survey import Survey
from archimind.models import Furniture, RoomDesign

INK, MUTED, PAPER = "#203d36", "#526b60", "#faf8f2"
WOOD, GLASS, DOOR = "#d3bc96", "#568799", "#b36838"


def _element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def _text(parent, x, y, label, size=15, color=INK, anchor="start"):
    node = _element(
        parent,
        "text",
        x=x,
        y=y,
        fill=color,
        **{"font-size": size, "text-anchor": anchor},
    )
    node.text = str(label)
    return node


def _line(parent, x, y, x2, y2, color=INK, weight=1.5, **attrs):
    return _element(
        parent,
        "line",
        x1=x,
        y1=y,
        x2=x2,
        y2=y2,
        stroke=color,
        **{"stroke-width": weight, **attrs},
    )


def _rect(parent, x, y, w, h, fill, stroke=INK, **attrs):
    return _element(
        parent, "rect", x=x, y=y, width=w, height=h, fill=fill, stroke=stroke, **attrs
    )


def _sheet(board, provenance, title, sheet_no, h=760, *, source_label=None):
    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 1170 {h}",
            "width": "420mm",
            "height": f"{420 * h / 1170:.3f}mm",
            "font-family": "Arial, sans-serif",
            "role": "img",
            "aria-label": title,
        },
    )
    _element(svg, "title").text = title
    _element(
        svg, "desc"
    ).text = f"Project {board['project']}, home {board['home_id']}, revision {board['revision']}. {provenance}."
    _rect(svg, 0, 0, 1170, h, PAPER, "none")
    _text(svg, 40, 40, "ARCHIMIND  /  DESIGN DEVELOPMENT", 16)
    _text(
        svg,
        1130,
        40,
        f"A-{sheet_no}   /   REVISION {board['revision']}",
        16,
        anchor="end",
    )
    _line(svg, 40, 55, 1130, 55, MUTED)
    _text(svg, 40, 105, title, 38).set("font-family", "Georgia, serif")
    source = source_label or (
        "Studio House demonstration geometry"
        if provenance == "demonstration"
        else "Selected design linked to supplied survey"
    )
    _text(
        svg,
        40,
        137,
        f"{source}  ·  Metres  ·  Use annotated dimensions  ·  Verify on site",
        16,
        MUTED,
    )
    _line(svg, 40, h - 54, 1130, h - 54, MUTED)
    _text(
        svg,
        40,
        h - 27,
        f"Project {board['project']}   /   Home {board['home_id'][:16]}",
        13,
        MUTED,
    )
    _text(
        svg,
        1130,
        h - 27,
        "Design development  /  Dimensions require field verification",
        13,
        MUTED,
        "end",
    )
    return svg


def _dimension(svg, x1, y, x2, value):
    _line(svg, x1, y, x2, y, MUTED, 1)
    for x in (x1, x2):
        _line(svg, x - 3, y + 4, x + 3, y - 4, MUTED, 1)
    _text(svg, (x1 + x2) / 2, y - 6, value, 13, MUTED, "middle")


def _room_design(board):
    bedrooms = [r for r in board["rooms"] if r["room"]["id"] == "bedroom"]
    if len(bedrooms) != 1:
        raise ValueError("Expected exactly one selected bedroom")
    record = bedrooms[0]
    furniture = [
        {key: item[key] for key in Furniture.model_fields if key in item}
        for item in record["furniture"]
    ]
    design = RoomDesign.model_validate({"room": record["room"], "furniture": furniture})
    for item in design.furniture:
        if item.rotation_deg:
            raise ValueError(
                f"Drawing requires an unrotated Town reservation: {item.id}"
            )
        if (
            min(item.x_m, item.y_m) < 0
            or item.x_m + item.width_m > design.room.width_m + 1e-9
            or item.y_m + item.depth_m > design.room.depth_m + 1e-9
            or item.height_m > design.room.ceiling_height_m + 1e-9
        ):
            raise ValueError(f"Furniture lies outside the selected shell: {item.id}")
    return design


def _openings(room):
    return [(op, 0.0, DOOR) for op in room.doors] + [
        (op, op.sill_height_m, GLASS) for op in room.windows
    ]


def _cut(design):
    desk = next((f for f in design.furniture if f.category == "desk"), None)
    return desk.x_m + desk.width_m / 2 if desk else design.room.width_m / 2


def _plan(board, provenance, design):
    room = design.room
    rows = len(design.furniture) + len(_openings(room))
    height = max(760, 425 + rows * 39)
    svg = _sheet(board, provenance, "Bedroom furniture plan", 101, height)
    scale = min(575 / room.width_m, 390 / room.depth_m)
    x0, y0 = 68, 221

    def xy(x, y):
        return x0 + x * scale, y0 + (room.depth_m - y) * scale

    w, h = room.width_m * scale, room.depth_m * scale
    _rect(svg, x0, y0, w, h, "#efeae0", INK, **{"stroke-width": 3})
    _dimension(svg, x0, y0 - 18, x0 + w, f"{room.width_m:.3f} m")
    dim = _element(svg, "g", transform=f"translate({x0 - 16} {y0 + h}) rotate(-90)")
    _dimension(dim, 0, 0, h, f"{room.depth_m:.3f} m")
    for n, f in enumerate(design.furniture, 1):
        x, y = xy(f.x_m, f.y_m + f.depth_m)
        _rect(
            svg,
            x,
            y,
            f.width_m * scale,
            f.depth_m * scale,
            WOOD,
            **{"data-furniture": f.id},
        )
        _text(
            svg,
            x + f.width_m * scale / 2,
            y + f.depth_m * scale / 2 + 4,
            f"F{n}",
            12,
            anchor="middle",
        )
    for op, _, col in _openings(room):
        a, b = op.offset_m, op.offset_m + op.width_m
        if op.wall in ("north", "south"):
            y = room.depth_m if op.wall == "north" else 0
            ends = (*xy(a, y), *xy(b, y))
        else:
            x = room.width_m if op.wall == "east" else 0
            ends = (*xy(x, a), *xy(x, b))
        _line(svg, *ends, col, 5, **{"data-opening": op.id})
    cx = xy(_cut(design), 0)[0]
    _line(
        svg, cx, y0 - 3, cx, y0 + h + 14, "#81583c", 1.4, **{"stroke-dasharray": "5 5"}
    )
    _text(svg, cx + 5, y0 + h + 26, "A–A", 13)
    _text(svg, x0, y0 + h + 46, "N ↑    Southwest origin  ·  X east, Y north", 14)
    _text(svg, 692, 190, "Furniture register", 22)
    y = 219
    for n, f in enumerate(design.furniture, 1):
        _text(svg, 692, y, f"F{n}  {f.name}")
        y += 18
        _text(
            svg,
            692,
            y,
            f"W/D/H {f.width_m:.3f} / {f.depth_m:.3f} / {f.height_m:.3f}  ·  X/Y {f.x_m:.3f} / {f.y_m:.3f}",
            13,
            MUTED,
        )
        y += 21
    _text(svg, 692, y + 12, "Opening register", 22)
    y += 41
    for op, z, color in _openings(room):
        _text(svg, 692, y, f"{op.id}   /   {op.wall}", 15, color)
        y += 18
        _text(
            svg,
            692,
            y,
            f"Offset {op.offset_m:.3f}   W {op.width_m:.3f}   Sill {z:.3f}   Head {z + op.height_m:.3f}",
            13,
            MUTED,
        )
        y += 21
    _text(
        svg,
        40,
        height - 86,
        "Furniture marks show planning envelopes. Door handing, swings, services and movable furniture clearances require separate evidence.",
        14,
    )
    return svg


def _elevations(board, provenance, design):
    room = design.room
    svg = _sheet(board, provenance, "Interior wall elevations", 201)
    for i, wall in enumerate(("north", "east", "south", "west")):
        x = 65 + 565 * (i % 2)
        y = 214 + 217 * (i // 2)
        span = room.width_m if wall in ("north", "south") else room.depth_m
        scale = min(440 / span, 125 / room.ceiling_height_m)
        w, h = span * scale, room.ceiling_height_m * scale
        _text(svg, x, y - 20, f"{wall.title()} wall · looking {wall}", 20)
        _rect(svg, x, y, w, h, "#eee9dc")
        for op, z, color in _openings(room):
            if op.wall != wall:
                continue
            # Inward observer facing the east or south wall sees increasing offsets to the left.
            offset = (
                span - op.offset_m - op.width_m
                if wall in ("east", "south")
                else op.offset_m
            )
            _rect(
                svg,
                x + offset * scale,
                y + h - (z + op.height_m) * scale,
                op.width_m * scale,
                op.height_m * scale,
                "#e4eaea",
                color,
                **{"data-opening": op.id},
            )
        _dimension(svg, x, y + h + 18, x + w, f"{span:.3f} m")
    _text(
        svg,
        40,
        670,
        f"Finished floor +0.000 m   /   Ceiling +{room.ceiling_height_m:.3f} m   /   Opening offsets, sill and head heights on A-101.",
        14,
    )
    return svg


def _section(board, provenance, design):
    room = design.room
    svg = _sheet(board, provenance, "Bedroom section A–A", 301)
    cut = _cut(design)
    scale = min(766 / room.depth_m, 326 / room.ceiling_height_m)
    x, y = 83, 225
    w, h = room.depth_m * scale, room.ceiling_height_m * scale
    _rect(svg, x, y, w, h, "#f1ece1")
    for i, f in enumerate(design.furniture, 1):
        if f.x_m <= cut <= f.x_m + f.width_m:
            fx = x + f.y_m * scale
            top = y + h - f.height_m * scale
            _rect(
                svg,
                fx,
                top,
                f.depth_m * scale,
                f.height_m * scale,
                WOOD,
                **{"data-furniture": f.id},
            )
            _text(
                svg, fx + f.depth_m * scale / 2, top - 7, f"F{i}", 13, anchor="middle"
            )
    _dimension(svg, x, y + h + 24, x + w, f"{room.depth_m:.3f} m  ·  south to north")
    _text(svg, x + w + 12, y + 7, f"+{room.ceiling_height_m:.3f} m ceiling")
    _text(svg, x + w + 12, y + h, "+0.000 m floor")
    _text(
        svg,
        40,
        613,
        f"Cut plane X = {cut:.3f} m looking west. Outlines are intersected furniture reservations keyed to A-101.",
        16,
    )
    _text(
        svg,
        40,
        651,
        "Desk apron height, knee recess, concealed structure and service routes require site or manufacturer details.",
        15,
        MUTED,
    )
    return svg


def _check_survey(room, survey: Survey) -> None:
    """Compare the measured room in its local SW, east/north coordinate system."""
    if (
        survey.source_kind != "measured"
        or survey.fixtures
        or survey.verification_items()
    ):
        raise ValueError(
            "Resolve field checks and unmodelled fixtures before linking a measured room."
        )
    width, depth = room.width_m, room.depth_m
    corners = [(0, 0), (width, 0), (width, depth), (0, depth)]

    def equal(a, b):
        return isclose(a, b, rel_tol=0, abs_tol=1e-9)

    if (
        len(survey.vertices_m) != 4
        or any(
            not equal(x, y)
            for observed, expected in zip(survey.vertices_m, corners)
            for x, y in zip(observed, expected)
        )
        or not equal(survey.height_m, room.ceiling_height_m)
    ):
        raise ValueError(
            "Survey boundary or ceiling differs from the selected rectangular room."
        )
    openings = {op.id: op for op in survey.openings}
    design_openings = [(op, "door", 0.0) for op in room.doors] + [
        (op, "window", op.sill_height_m) for op in room.windows
    ]
    if (
        len(openings) != len(survey.openings)
        or len(openings) != len(design_openings)
        or set(openings) != {op.id for op, _, _ in design_openings}
    ):
        raise ValueError("Survey opening IDs differ from the selected room.")
    for op, kind, sill in design_openings:
        observed = openings[op.id]
        wall = ("south", "east", "north", "west").index(op.wall)
        offset = op.offset_m
        if wall in (2, 3):
            offset = (width if wall == 2 else depth) - offset - op.width_m
        if (
            observed.wall != wall
            or observed.kind != kind
            or any(
                not equal(x, y)
                for x, y in zip(
                    (
                        observed.offset_m,
                        observed.width_m,
                        observed.height_m,
                        observed.sill_m,
                    ),
                    (offset, op.width_m, op.height_m, sill),
                )
            )
        ):
            raise ValueError(f"Survey evidence differs at opening {op.id}.")


def write_drawings(
    board: dict, destination: Path, *, provenance: str, survey: Survey | None = None
) -> list[Path]:
    """Write editable SVGs with explicit, checked geometry provenance."""
    if provenance not in ("demonstration", "survey-linked"):
        raise ValueError("Specify demonstration or survey-linked drawing provenance")
    design = _room_design(board)
    if provenance == "survey-linked":
        if survey is None:
            raise ValueError(
                "A measured survey is required for survey-linked drawings."
            )
        if survey.project_id is None or survey.surveyed_on is None:
            raise ValueError(
                "A dated survey with a project ID is required for linking."
            )
        if survey.project_id != board["project"]:
            raise ValueError("The survey belongs to a different project.")
        _check_survey(design.room, survey)
    elif survey is not None:
        raise ValueError("Select survey-linked provenance when supplying a survey.")
    sheets = [
        ("bedroom-plan.svg", _plan(board, provenance, design)),
        ("bedroom-elevations.svg", _elevations(board, provenance, design)),
        ("bedroom-section.svg", _section(board, provenance, design)),
    ]
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name, sheet in sheets:
        if survey is not None:
            sheet.set(
                "data-survey-sha256",
                hashlib.sha256(survey.drawing_source_json().encode()).hexdigest(),
            )
            sheet.set("data-survey-project-id", survey.project_id)
            sheet.set("data-survey-date", survey.surveyed_on.isoformat())
        ET.ElementTree(sheet).write(
            destination / name, encoding="utf-8", xml_declaration=True
        )
    return [destination / name for name, _ in sheets]
