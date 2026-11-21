"""Blender equivalents of the three known Town procedural bedroom templates.

All offsets and dimensions are relative to the saved reservation. The quilt uses
the same parametric fold profile as frontend/realistic_viewer/src/bedroom_finishes.js.
These pieces remain visualizations of procedural furniture, including in receipts.
"""

import math

import bpy


def town_template(item, materials, box):
    kind = item["id"]
    if kind not in {"queen-bed", "desk-chair", "bedside-lamp"}:
        return False
    cx, cy, _ = item["center_floor_xyz_m"]
    w, d, h = item["reservation_wdh_m"]
    prefix = "Procedural / " + kind + " / "

    def part(name, material, center, size, radius):
        x, y, z = center
        width, depth, height = size
        return box(
            prefix + name,
            (cx + x * w, cy + y * d, z * h),
            (width * w, depth * d, height * h),
            materials[material],
            radius,
        )

    if kind == "queen-bed":
        part("Plinth", "edge", (0, 0, 0.08), (0.83, 0.86, 0.16), 0.015)
        part("Frame", "oak", (0, 0, 0.22), (1, 1, 0.17), 0.025)
        part("Mattress", "linen", (0, -0.005, 0.47), (0.985, 0.98, 0.34), 0.065)
        part("Headboard", "oak", (0, 0.4815, 0.5), (1, 0.037, 1), 0.025)
        _quilt(prefix, materials["sage"], (cx, cy), (w, d, h))
        part("Turned hem", "linen", (0, 0.12, 0.741), (0.975, 0.077, 0.052), 0.021)
        for x in (-0.245, 0.245):
            pillow = part("Pillow", "linen", (x, 0.30, 0.72), (0.445, 0.19, 0.22), 0.06)
            pillow.rotation_euler.z = x * 0.12
        part("Foot throw", "clay", (-0.012, -0.29, 0.766), (0.91, 0.185, 0.06), 0.024)
        for y in (0.212, 0.22, 0.36, 0.368):
            part("Stripe", "linen", (-0.012, -y, 0.797), (0.88, 0.003, 0.006), 0.001)
    elif kind == "desk-chair":
        for x in (-0.396, 0.396):
            for y in (-0.385, 0.385):
                part("Leg", "oak", (x, y, 0.253), (0.0896, 0.0827, 0.506), 0.004)
        part("Seat", "sage", (0, 0, 0.530), (1, 1, 0.0964), 0.016)
        side = -1 if item["rotation_deg"] == 180 else 1
        part("Back", "oak", (0, side * 0.442, 0.778), (1, 0.0923, 0.434), 0.014)
    else:
        part("Cabinet", "oak", (0, 0, 0.264), (1, 1, 0.528), 0.009)
        part("Drawer pull", "brass", (0, -0.475, 0.340), (0.27, 0.042, 0.024), 0.003)
        part("Lamp stem", "brass", (0, 0, 0.66), (0.052, 0.058, 0.236), 0.005)
        for name, bottom, top, z, height, mat in [
            ("Lamp foot", 0.100, 0.090, 0.575, 0.025, "brass"),
            ("Lamp shade", 0.146, 0.102, 0.950, 0.220, "ivory"),
        ]:
            # Scale the original Town dimensions from its 0.48 × 0.43 × 1.06 m template.
            factor = min(w / 0.48, d / 0.43)
            bpy.ops.mesh.primitive_cone_add(
                vertices=48,
                radius1=bottom * factor,
                radius2=top * factor,
                depth=height * h / 1.06,
                location=(cx, cy, z * h / 1.06),
            )
            obj = bpy.context.object
            obj.name = prefix + name
            obj.data.materials.append(materials[mat])
            for polygon in obj.data.polygons:
                polygon.use_smooth = len(polygon.vertices) == 4
    return True


def _quilt(prefix, material, center, size):
    cx, cy = center
    w, d, h = size
    cols, rows = 64, 56
    vertices, faces = [], []
    for j in range(rows + 1):
        for i in range(cols + 1):
            u, v = i / cols, j / rows
            crease = math.sin(14 * u + 4 * math.sin(5 * v)) * math.sin(11 * v + 3 * u)
            channel = math.cos(math.pi * (7 * u + 0.10 * math.sin(5 * v))) ** 12
            z = (
                0.747
                - 0.23 * abs(2 * u - 1) ** 16
                - 0.105 * v**14
                + 0.023 * crease
                - 0.015 * channel
            )
            vertices.append(
                (cx + (u - 0.5) * w * 0.997, cy + d * (0.158 - 0.655 * v), h * z)
            )
            if i < cols and j < rows:
                n = j * (cols + 1) + i
                faces.append((n, n + cols + 1, n + cols + 2, n + 1))
    mesh = bpy.data.meshes.new(prefix + "Quilt")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
