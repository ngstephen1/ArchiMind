"""Apply the bedroom and salon finish study within saved room geometry."""

import hashlib
import math
import struct

import bpy
from mathutils import Vector


def bounds(obj):
    corners = [obj.matrix_world @ Vector(point) for point in obj.bound_box]
    return (
        Vector(tuple(min(p[i] for p in corners) for i in range(3))),
        Vector(tuple(max(p[i] for p in corners) for i in range(3))),
    )


def finish(source, name, color, grain=None):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    material = source.copy()
    material.name = name
    material.diffuse_color = (*color, 1)
    tree = material.node_tree
    if tree is None:
        raise ValueError(f"Expected node material: {source.name}")
    for node in list(tree.nodes):
        if node.type == "MIX_SHADER" and "curtains" in name:
            # A lined linen drape transmits less direct emitter energy than sheer proxy fabric.
            node.inputs[0].default_value = 0.12
        if node.type == "BSDF_TRANSLUCENT":
            node.inputs["Color"].default_value = (*color, 1)
        if node.type != "BSDF_PRINCIPLED":
            continue
        base = node.inputs["Base Color"]
        for link in list(base.links):
            tree.links.remove(link)
        base.default_value = (*color, 1)
        if grain:
            node.inputs["Roughness"].default_value = 0.78
            node.inputs["Sheen Weight"].default_value = 0.19
            coord = tree.nodes.new("ShaderNodeTexCoord")
            text = tree.nodes.new("ShaderNodeTexNoise")
            text.inputs["Scale"].default_value = grain
            text.inputs["Detail"].default_value = 2
            tree.links.new(coord.outputs["Object"], text.inputs["Vector"])
            weave = tree.nodes.new("ShaderNodeTexVoronoi")
            weave.voronoi_dimensions = "3D"
            weave.feature = "DISTANCE_TO_EDGE"
            weave.inputs["Scale"].default_value = grain * 0.60
            weave.inputs["Randomness"].default_value = 0.21
            tree.links.new(coord.outputs["Object"], weave.inputs["Vector"])
            tone = tree.nodes.new("ShaderNodeMixRGB")
            tone.inputs[1].default_value = (*(v * 0.73 for v in color), 1)
            tone.inputs[2].default_value = (*(v * 1.12 for v in color), 1)
            tree.links.new(text.outputs["Fac"], tone.inputs["Fac"])
            tree.links.new(tone.outputs["Color"], base)
            bump = tree.nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = 0.34
            bump.inputs["Distance"].default_value = 0.003
            tree.links.new(weave.outputs["Distance"], bump.inputs["Height"])
            tree.links.new(bump.outputs["Normal"], node.inputs["Normal"])
    return material


def rug_binding(obj, low, high):
    # A contrasting yarn binding inside the existing rug envelope.
    mesh = obj.data
    if mesh.users > 1:
        raise ValueError("Rug geometry must be local")
    border = finish(
        obj.material_slots[0].material, "Study | rug edge", (0.16, 0.12, 0.08), 100
    )
    mesh.materials.append(border)
    for polygon in mesh.polygons:
        center = obj.matrix_world @ polygon.center
        if (
            polygon.normal.z < 0.5
            or min(
                center.x - low.x, high.x - center.x, center.y - low.y, high.y - center.y
            )
            < 0.026
        ):
            polygon.material_index = len(mesh.materials) - 1


def cushion_welt(obj, source, low, high, color):
    """Shade a thin welt at a consistent height without changing the cushion mesh."""
    material = source.copy()
    material.name = f"{source.name} | welt · {obj.name}"
    tree = material.node_tree
    shader = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    base = shader.inputs["Base Color"]
    weave_color = base.links[0].from_socket
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    position = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(geometry.outputs["Position"], position.inputs["Vector"])
    compare = tree.nodes.new("ShaderNodeMath")
    compare.operation = "COMPARE"
    center = low.z + 0.24 * (high.z - low.z)
    width = 0.086 * (high.z - low.z)
    compare.inputs[1].default_value = center
    compare.inputs[2].default_value = width / 2
    tree.links.new(position.outputs["Z"], compare.inputs[0])
    accent = tree.nodes.new("ShaderNodeMixRGB")
    accent.inputs[2].default_value = (*(value * 0.60 for value in color), 1)
    tree.links.new(compare.outputs["Value"], accent.inputs["Fac"])
    tree.links.new(weave_color, accent.inputs[1])
    tree.links.new(accent.outputs["Color"], base)
    obj.material_slots[0].material = material
    return {"center_z_m": center, "width_m": width}


def blanket_bands(obj, spacing, width, color):
    """Couch a contrasting yarn into narrow bands at physical spacing."""
    material = obj.material_slots[0].material
    tree = material.node_tree
    shader = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    base = shader.inputs["Base Color"]
    woven = base.links[0].from_socket
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    position = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(geometry.outputs["Position"], position.inputs["Vector"])
    period = tree.nodes.new("ShaderNodeMath")
    period.operation = "PINGPONG"
    period.inputs[1].default_value = spacing / 2
    tree.links.new(position.outputs["Y"], period.inputs[0])
    band = tree.nodes.new("ShaderNodeMath")
    band.operation = "LESS_THAN"
    band.inputs[1].default_value = width / 2
    tree.links.new(period.outputs["Value"], band.inputs[0])
    accent = tree.nodes.new("ShaderNodeMixRGB")
    tree.links.new(band.outputs["Value"], accent.inputs["Fac"])
    tree.links.new(woven, accent.inputs[1])
    accent.inputs[2].default_value = (*color, 1)
    tree.links.new(accent.outputs["Color"], base)
    return {"spacing_m": spacing, "width_m": width, "linear_rgb": color}


def drape(obj, low, high, role):
    """Fit a softly rounded fabric layer wholly inside its original part envelope."""
    width, depth, height = high - low
    nx, ny = 56, 28
    vertices, faces = [], []
    inverse = obj.matrix_world.inverted()
    for upper in (True, False):
        for j in range(ny + 1):
            v = j / ny
            for i in range(nx + 1):
                u = i / nx
                # Contract the plan corners slightly rather than overhanging the saved furniture.
                corner = math.sin(math.pi * u) * math.sin(math.pi * v)
                edge = min(1, u * 13, (1 - u) * 13, v * 13, (1 - v) * 13)
                center = v - 0.5
                if role == "Pillow":
                    head = math.sin(math.pi * u) ** 0.7 * math.sin(math.pi * v) ** 0.7
                    hollow = math.exp(-18 * ((u - 0.45) ** 2 + center**2))
                    upper_profile = 0.47 + 0.48 * head - 0.15 * hollow
                    lower_profile = 0.34 - 0.22 * head
                elif role == "Folded throw":
                    fold = 0.5 + 0.5 * math.sin(math.tau * (6 * u + 0.33 * v))
                    upper_profile = 0.54 + edge * (0.16 + 0.17 * fold + 0.09 * corner)
                    lower_profile = 0.10
                else:
                    phase = math.tau * (
                        3.0 * u + 0.26 * v + 0.25 * math.sin(math.pi * v)
                    )
                    fold = 0.5 + 0.5 * math.sin(phase)
                    ridge = math.exp(-100 * (v - 0.80 - 0.028 * math.sin(phase)) ** 2)
                    # Keep the shallow top valleys above the mattress. The
                    # underside still sits within the original tucked envelope.
                    upper_profile = 0.78 + edge * (0.045 + 0.085 * fold + 0.05 * ridge)
                    lower_profile = 0.10
                z = low.z + height * (upper_profile if upper else lower_profile)
                x = low.x + width * (u * 0.986 + 0.007)
                y = low.y + depth * (v * 0.984 + 0.008)
                vertices.append(inverse @ Vector((x, y, z)))
    count = (nx + 1) * (ny + 1)
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            b, c, d = a + 1, a + nx + 2, a + nx + 1
            faces.extend(((a, b, c, d), (d + count, c + count, b + count, a + count)))
    rim = (
        list(range(nx + 1))
        + [j * (nx + 1) + nx for j in range(1, ny + 1)]
        + [ny * (nx + 1) + i for i in range(nx - 1, -1, -1)]
        + [j * (nx + 1) for j in range(ny - 1, 0, -1)]
    )
    faces.extend(
        (b, a, a + count, b + count)
        for a, b in zip(rim, rim[1:] + rim[:1], strict=True)
    )
    material = obj.material_slots[0].material
    mesh = bpy.data.meshes.new(f"Study draped {obj.name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    if role == "Pillow":
        welt = finish(material, f"{material.name} edge", (0.28, 0.20, 0.13), 140)
        mesh.materials.append(welt)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        if role == "Pillow" and polygon.index >= 2 * nx * ny:
            polygon.material_index = 1
    mesh.update()
    obj.data = mesh
    bpy.context.view_layer.update()
    adjusted_low, adjusted_high = bounds(obj)
    for axis in range(3):
        if (
            adjusted_low[axis] < low[axis] - 1e-5
            or adjusted_high[axis] > high[axis] + 1e-5
        ):
            raise ValueError(f"{obj.name} exceeded the original saved fabric envelope")
    return [list(adjusted_low), list(adjusted_high)]


def evaluated_geometry():
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    meshes = {}
    for source in bpy.context.scene.objects:
        if source.type != "MESH":
            continue
        obj = source.evaluated_get(graph)
        digest = hashlib.sha256()
        for vertex in obj.data.vertices:
            digest.update(struct.pack("<fff", *vertex.co))
        for polygon in obj.data.polygons:
            digest.update(struct.pack("<I", len(polygon.vertices)))
            for index in polygon.vertices:
                digest.update(struct.pack("<I", index))
        meshes[obj.name] = (
            tuple(tuple(row) for row in obj.matrix_world),
            tuple(tuple(point) for point in bounds(obj)),
            digest.hexdigest(),
        )
    return meshes


def compare_geometry(before, after):
    if before.keys() != after.keys():
        raise ValueError("The finish study must preserve the complete mesh inventory.")
    edited = {name for name in before if before[name] != after[name]}
    if edited != {"Duvet", "Folded throw", "Pillow 1", "Pillow 2"}:
        raise ValueError("Only the duvet and throw may have new mesh geometry.")
    for name in sorted(edited):
        old_transform, old_bounds, _ = before[name]
        new_transform, new_bounds, _ = after[name]
        if old_transform != new_transform or any(
            new_bounds[0][i] < old_bounds[0][i] - 0.00001
            or new_bounds[1][i] > old_bounds[1][i] + 0.00001
            for i in range(3)
        ):
            raise ValueError(f"{name} moved or exceeded its original fabric envelope.")
    return {
        "unchanged_meshes": len(before) - len(edited),
        "bounded_fabric_layers": sorted(edited),
    }


def inside_room(part, point):
    x, y = part["origin"]
    room = part["room"]
    return x <= point.x < x + room["width_m"] and y <= point.y < y + room["depth_m"]


def near_window(part, point):
    x, y = part["origin"]
    room = part["room"]
    walls = {
        "west": (point.x - x, point.y - y),
        "east": (point.x - x - room["width_m"], point.y - y),
        "south": (point.y - y, point.x - x),
        "north": (point.y - y - room["depth_m"], point.x - x),
    }
    for window in room["windows"]:
        perpendicular, tangent = walls[window["wall"]]
        offset = window["offset_m"]
        if (
            abs(perpendicular) <= 0.15
            and offset - 0.15 <= tangent <= offset + window["width_m"] + 0.15
        ):
            return True
    return False


def polish(board):
    bpy.context.view_layer.update()
    focal = {
        part["room"]["id"]: part
        for part in board["rooms"]
        if part["room"]["id"] in {"bedroom", "salon"}
    }
    if set(focal) != {"bedroom", "salon"}:
        raise ValueError("The paired finish study requires a saved bedroom and salon.")
    changes = []
    bedding = {
        "Duvet": ("soft sage linen duvet", (0.31, 0.39, 0.30)),
        "Folded throw": ("rust and flax knitted throw", (0.33, 0.12, 0.062)),
        "Pillow 1": ("warm stone pillow", (0.55, 0.44, 0.32)),
        "Pillow 2": ("burnt clay pillow", (0.34, 0.14, 0.075)),
        "Turned-down sheet": ("unbleached linen", (0.52, 0.47, 0.36)),
        "Upholstered headboard": ("warm flax headboard", (0.36, 0.28, 0.19)),
    }
    for obj in tuple(bpy.context.scene.objects):
        if obj.type != "MESH" or len(obj.material_slots) != 1:
            continue
        low, high = bounds(obj)
        middle = (low + high) / 2
        salon = inside_room(focal["salon"], middle)
        bed = inside_room(focal["bedroom"], middle)
        source = obj.material_slots[0].material
        choice = None
        if bed and obj.name in bedding:
            label, color = bedding[obj.name]
            choice = label, color, 140
        elif obj.name.startswith(("bedroom/decor/curtain:", "salon/decor/curtain:")):
            choice = "warm flax curtains", (0.56, 0.42, 0.29), 160
        elif obj.name.startswith(
            ("Window frame", "Window horizontal rail", "Sill")
        ) and any(near_window(part, middle) for part in focal.values()):
            choice = (
                ("warm matching joinery", (0.32, 0.24, 0.16), None)
                if obj.name.startswith(("Window horizontal rail", "Sill"))
                else ("bronzed window joinery", (0.095, 0.077, 0.051), None)
            )
        elif obj.name in {"bedroom/decor/rug", "Bound wool rug"}:
            choice = "woven taupe rug", (0.22, 0.17, 0.12), 76
        elif (
            salon
            and source.name in {"wool", "moss"}
            and obj.name.startswith(
                ("Back cushion", "Boxed seat cushion", "Upholstered deck", "Arm")
            )
        ):
            choice = (
                ("walnut-olive upholstery", (0.105, 0.157, 0.071), 125)
                if source.name == "moss"
                else ("warm nutmeg upholstery", (0.34, 0.23, 0.15), 116)
            )
        elif obj.name.startswith("salon/decor/plant") and source.name.split(" · ")[
            -1
        ] in {"365834", "45683c", "627e45"}:
            variants = {
                "365834": (0.055, 0.14, 0.022),
                "45683c": (0.11, 0.22, 0.039),
                "627e45": (0.22, 0.31, 0.064),
            }
            code = source.name.split(" · ")[-1]
            choice = f"salon foliage {code}", variants[code], None
        if choice:
            label, color, grain = choice
            slot = obj.material_slots[0]
            slot.link = "OBJECT"
            slot.material = finish(source, f"Study | {label}", color, grain)
            if label == "woven taupe rug":
                rug_binding(obj, low, high)
            record = {
                "object": obj.name,
                "finish": label,
                "world_bounds_m": [list(low), list(high)],
            }
            if salon and obj.name.startswith(("Back cushion", "Boxed seat cushion")):
                record["welt_band"] = cushion_welt(obj, slot.material, low, high, color)
            if bed and (
                obj.name in {"Duvet", "Folded throw"} or obj.name.startswith("Pillow ")
            ):
                role = "Pillow" if obj.name.startswith("Pillow ") else obj.name
                record["edited_bounds_m"] = drape(obj, low, high, role)
            if bed and obj.name == "Folded throw":
                record["woven_bands"] = blanket_bands(
                    obj, 0.086, 0.014, (0.66, 0.50, 0.34)
                )
            changes.append(record)
    for data in bpy.data.lights:
        if not data.name.startswith("Daylight through ") or not data.name.endswith(
            ("bedroom-window", "salon-window")
        ):
            continue
        # Camera and exposure stay pinned. The study changes aperture illuminance.
        previous_watts = data.energy
        data.energy *= 0.72
        changes.append(
            {"light": data.name, "previous_watts": previous_watts, "watts": data.energy}
        )
    for light in bpy.context.scene.objects:
        if light.type != "LIGHT" or not light.name.startswith("Pendant practical"):
            continue
        if not inside_room(focal["salon"], light.location):
            continue
        previous_watts = light.data.energy
        light.data.energy = max(previous_watts, 15)
        light.data.color = (1.0, 0.78, 0.58)
        changes.append(
            {
                "light": light.name,
                "previous_watts": previous_watts,
                "watts": light.data.energy,
            }
        )
    shade = bpy.data.objects.get("salon/decor/floor_lamp.002")
    if shade:
        low, high = bounds(shade)
        lamp = bpy.data.lights.new("Study | salon standing lamp", "POINT")
        lamp.color = (1.0, 0.72, 0.43)
        lamp.energy = 12
        lamp.shadow_soft_size = 0.07
        obj = bpy.data.objects.new(lamp.name, lamp)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = (low + high) / 2
        obj.location.z = low.z - 0.015
        changes.append(
            {"object": obj.name, "location_m": list(obj.location), "watts": lamp.energy}
        )
    return changes
