"""Revision-bound study drawings for validated Town service rooms."""

from xml.etree.ElementTree import Element, SubElement, tostring

from archimind.models import RoomDesign
from archimind.town.design import validate_home
from archimind.town.service_layout import swing_reserve

SCALE = 65
LEFT = 65
BASE = 520
INK = "#253347"
BLUE = "#285987"
MUTED = "#526680"


def sheet(title, project, revision, home_id):
    root = Element("svg", xmlns="http://www.w3.org/2000/svg", viewBox="0 0 1100 645")
    SubElement(root, "title").text = title
    SubElement(
        root, "metadata"
    ).text = f"project={project}; revision={revision}; home={home_id}"
    rect(root, 0, 0, 1100, 645, "#fff", stroke="none")
    label(root, 44, 38, title, 23)
    label(
        root, 44, 63, f"Project {project} · Revision {revision} · Home {home_id[:12]}"
    )
    label(
        root,
        44,
        625,
        "Design study · Dimensions in metres · Verify product and site conditions before specification",
    )
    return root


def label(root, x, y, value, size=14, *, fill=INK):
    SubElement(
        root,
        "text",
        {
            "x": f"{x:g}",
            "y": f"{y:g}",
            "font-size": str(size),
            "fill": fill,
            "font-family": "sans-serif",
        },
    ).text = value


def rect(root, x, y, w, h, fill, *, stroke=INK, dash=None):
    attributes = {
        "x": f"{x:g}",
        "y": f"{y:g}",
        "width": f"{w:g}",
        "height": f"{h:g}",
        "fill": fill,
        "stroke": stroke,
    }
    if dash:
        attributes["stroke-dasharray"] = dash
    SubElement(root, "rect", attributes)


def line(root, start, end, *, stroke=INK):
    SubElement(
        root,
        "line",
        {
            "x1": f"{start[0]:g}",
            "y1": f"{start[1]:g}",
            "x2": f"{end[0]:g}",
            "y2": f"{end[1]:g}",
            "stroke": stroke,
        },
    )


def plan(root, design, evidence):
    room = design.room
    scale = min(SCALE, 620 / room.width_m, 400 / room.depth_m)

    def plan_point(x, y):
        return LEFT + scale * x, BASE - scale * y

    def plan_rect(root, x, y, width, depth, fill, **style):
        left, top = plan_point(x, y + depth)
        rect(root, left, top, width * scale, depth * scale, fill, **style)

    plan_rect(root, 0, 0, room.width_m, room.depth_m, "#f8fafc")
    for zone in evidence["operating_zones"]:
        x, y, w = (zone[key] for key in ("x_m", "front_y_m", "width_m"))
        plan_rect(
            root, x, y, w, zone["working_depth_m"], "#deebf7", stroke=BLUE, dash="4 3"
        )
        if leaf := zone["leaf_projection_m"]:
            plan_rect(root, x, y, w, leaf, "#bfd9ef", stroke=BLUE)
    for index, item in enumerate(design.furniture, start=1):
        plan_rect(root, item.x_m, item.y_m, item.width_m, item.depth_m, "#f4dcc0")
        x, y = plan_point(item.x_m + item.width_m / 2, item.y_m + item.depth_m / 2)
        label(root, x - 4, y + 5, str(index))
        label(
            root,
            750,
            115 + index * 21,
            f"{index}. {item.name} · {item.width_m:g} × {item.depth_m:g} m",
        )
    for swing in evidence["door_swings"]:
        left, bottom, right, top = swing_reserve(swing).bounds
        plan_rect(
            root,
            left,
            bottom,
            right - left,
            top - bottom,
            "none",
            stroke=BLUE,
            dash="3 3",
        )
        hinge, shut, opened = (
            plan_point(*swing[key]) for key in ("hinge", "closed", "opened")
        )
        line(root, hinge, shut, stroke=BLUE)
        line(root, hinge, opened, stroke=BLUE)
        shut_dx, shut_dy = shut[0] - hinge[0], shut[1] - hinge[1]
        open_dx, open_dy = opened[0] - hinge[0], opened[1] - hinge[1]
        clockwise = int(shut_dx * open_dy - shut_dy * open_dx > 0)
        radius = swing["leaf_m"] * scale
        SubElement(
            root,
            "path",
            {
                "d": f"M {shut[0]:g} {shut[1]:g} A {radius:g} {radius:g} 0 0 {clockwise} {opened[0]:g} {opened[1]:g}",
                "fill": "none",
                "stroke": BLUE,
            },
        )
    label(root, 65, 552, f"Room interior {room.width_m:g} × {room.depth_m:g} m")
    label(root, 750, 275, "Dashed blue · working or door reserve", fill=BLUE)
    label(root, 750, 298, "Solid blue · modeled appliance leaf extent", fill=BLUE)
    label(root, 750, 323, "Service connections need field verification.", fill=MUTED)
    for index, zone in enumerate(evidence["operating_zones"]):
        note = f"{zone['fixture_id']} · {zone['working_depth_m']:g} m working depth"
        if leaf := zone["leaf_projection_m"]:
            note += f" · {leaf:g} m leaf"
        label(root, 750, 353 + 21 * index, note)


def elevation(root, design):
    room = design.room
    scale = min(SCALE, 620 / room.width_m, 400 / room.ceiling_height_m)
    rect(
        root,
        LEFT,
        BASE - room.ceiling_height_m * scale,
        room.width_m * scale,
        room.ceiling_height_m * scale,
        "#f8fafc",
    )
    fixtures = [item for item in design.furniture if item.id != "breakfast-suite"]
    for index, item in enumerate(fixtures, start=1):
        x = LEFT + item.x_m * scale
        y = BASE - item.height_m * scale
        rect(root, x, y, item.width_m * scale, item.height_m * scale, "#f4dcc0")
        label(root, x + 6, BASE - 15, str(index))
        label(
            root,
            750,
            140 + index * 25,
            f"{index}. {item.name} · {item.width_m:g} W × {item.height_m:g} H m",
        )
    label(
        root,
        LEFT,
        552,
        f"South wall run · {room.width_m:g} m across · {room.ceiling_height_m:g} m ceiling",
    )
    label(
        root,
        LEFT,
        577,
        "Confirm appliance cutouts, counter edges and installation gaps against selected products.",
    )


def bath_services(root, design):
    needs = {
        "toilet": "Cold water supply · soil waste · vent",
        "vanity": "Hot and cold supplies · basin waste · vent",
        "tub": "Hot and cold supplies · tub waste and overflow · vent",
    }
    label(root, LEFT, 115, "Proposed fixture demands", 18)
    for index, item in enumerate(design.furniture):
        services = needs.get(item.id)
        if not services:
            continue
        y = 150 + index * 86
        rect(root, LEFT, y, 195, 48, "#f4dcc0")
        label(root, LEFT + 12, y + 28, item.name)
        line(root, (LEFT + 195, y + 24), (LEFT + 225, y + 24), stroke=BLUE)
        label(root, LEFT + 235, y + 28, services)
    label(
        root,
        LEFT,
        450,
        "Unknown · existing branch positions, pipe sizes, falls, vent paths and shutoff locations.",
    )
    label(
        root,
        LEFT,
        478,
        "Field locate connections and verify routes and access before fixing fixture locations.",
    )


def service_study(project: str, revision: int, home: dict) -> dict[str, str]:
    """Rebuild sheets from saved geometry and return UTF-8 SVG content."""
    if revision < 1 or not home.get("service_layout"):
        raise ValueError("Select a saved revision with the fixture program.")
    evidence = validate_home(home, measure=True)["service_rooms"]
    designs = {
        part["design"]["room"]["id"]: RoomDesign.model_validate(part["design"])
        for part in home["rooms"]
        if part["design"]["room"]["id"] in evidence
    }
    sheets = {}
    for room_id, title in (
        ("kitchen-dining", "Kitchen operation plan"),
        ("bathroom", "Bathroom operation plan"),
    ):
        root = sheet(title, project, revision, home["id"])
        plan(root, designs[room_id], evidence[room_id])
        sheets[room_id + "-plan.svg"] = tostring(root, encoding="unicode")
    root = sheet("Kitchen south-wall elevation", project, revision, home["id"])
    elevation(root, designs["kitchen-dining"])
    sheets["kitchen-elevation.svg"] = tostring(root, encoding="unicode")
    root = sheet("Bathroom service coordination", project, revision, home["id"])
    bath_services(root, designs["bathroom"])
    sheets["bathroom-services.svg"] = tostring(root, encoding="unicode")
    return sheets
