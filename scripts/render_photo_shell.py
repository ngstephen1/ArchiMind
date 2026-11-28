"""Build the confirmed photo-room shell for a bookmarked Cycles view."""

import bpy
from mathutils import Vector


def build(board):
    if board.get("shell_source") != "user-confirmed photo room dimensions":
        raise ValueError("Expected the saved photo-home shell.")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    scene = bpy.context.scene
    scene.world.use_nodes = True
    sky = scene.world.node_tree.nodes["Background"]
    sky.inputs[0].default_value = (0.8, 0.88, 1.0, 1)
    sky.inputs[1].default_value = 1.4
    materials = {}

    def box(name, position, size, hex_color):
        if hex_color not in materials:
            material = bpy.data.materials.new(hex_color)
            material.use_nodes = True
            rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [
                ((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in rgb
            ]
            material.node_tree.nodes["Principled BSDF"].inputs[
                "Base Color"
            ].default_value = (*linear, 1)
            materials[hex_color] = material
        bpy.ops.mesh.primitive_cube_add(size=1, location=position)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = size
        obj.data.materials.append(materials[hex_color])

    for part in board["rooms"]:
        room = part["room"]
        ox, oy = part["origin"]
        w, d, h = (room[k] for k in ("width_m", "depth_m", "ceiling_height_m"))
        overrides = part.get("finish_overrides", {})
        finishes = board["finishes"]
        floor = finishes.get("proposal-" + overrides.get("floor", ""), "#ba9a70")
        paint = finishes.get("proposal-" + overrides.get("wall", ""), "#e5d6bc")
        box("Floor", (ox + w / 2, oy + d / 2, -0.035), (w, d, 0.07), floor)
        box("Ceiling", (ox + w / 2, oy + d / 2, h + 0.02), (w, d, 0.04), "#f2ede5")
        for panel in part["panels"]:
            a, b = panel["points"][0], panel["points"][2]
            x, y = ox + (a[0] + b[0]) / 2, oy + (a[1] + b[1]) / 2
            # Offset each room's surface inward. Adjacent rooms can have distinct wall finishes.
            x += {"west": 0.025, "east": -0.025}.get(panel["wall"], 0)
            y += {"south": 0.025, "north": -0.025}.get(panel["wall"], 0)
            box(
                "Wall",
                (x, y, (a[2] + b[2]) / 2),
                (abs(b[0] - a[0]) or 0.05, abs(b[1] - a[1]) or 0.05, b[2] - a[2]),
                paint,
            )
            if panel["bottom"] == 0:
                box(
                    "Baseboard",
                    (x, y, 0.065),
                    (abs(b[0] - a[0]) + 0.075, abs(b[1] - a[1]) + 0.075, 0.13),
                    "#eadfcb",
                )
        for win in room["windows"]:
            side = win["wall"]
            if side == "west" and win["id"].startswith("join-window-"):
                continue
            width = win["width_m"]
            along = win["offset_m"] + width / 2
            sill, height = win["sill_height_m"], win["height_m"]
            horizontal = side in {"north", "south"}
            x = ox + (along if horizontal else w if side == "east" else 0)
            y = oy + (d if side == "north" else 0 if horizontal else along)
            if not win["id"].startswith("join-window-"):
                inward = {
                    "north": (0, -1, 0),
                    "south": (0, 1, 0),
                    "east": (-1, 0, 0),
                    "west": (1, 0, 0),
                }[side]
                light = bpy.data.lights.new("Window daylight", "AREA")
                light.shape, light.size, light.size_y = "RECTANGLE", width, height
                light.energy = 250 * width * height
                emitter = bpy.data.objects.new("Window daylight", light)
                scene.collection.objects.link(emitter)
                emitter.location = (
                    Vector((x, y, sill + height / 2)) - Vector(inward) * 0.12
                )
                emitter.rotation_euler = (
                    Vector(inward).to_track_quat("-Z", "Y").to_euler()
                )
            box(
                "Window sill",
                (x, y, sill),
                (width + 0.1, 0.19, 0.07) if horizontal else (0.19, width + 0.1, 0.07),
                "#e8dec9",
            )
            box(
                "Window mullion",
                (x, y, sill + height / 2),
                (0.045, 0.09, height) if horizontal else (0.09, 0.045, height),
                "#efe9dc",
            )
