"""Blender 5 operator. Run with --background --factory-startup and --python-exit-code 1."""

import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/archimind/_viewer_assets"
SURFACES = ROOT / "frontend/realistic_viewer/town/materials"
DESK = "2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(code):
    channels = [int(code[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return [
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels
    ] + [1]


def surface(name, color, rough=0.6):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgb(color)
    m.use_nodes = True
    shader = m.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = m.diffuse_color
    shader.inputs["Roughness"].default_value = rough
    return m


def box(name, location, dimensions, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("Rounded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        obj.modifiers.new("Plane normals", "WEIGHTED_NORMAL")
    return obj


def material_image(row, directory):
    original = directory / row["asset"]
    if original.is_file() and sha(original) == row["source_sha256"]:
        return original
    thumbnail = SURFACES / row["local"]
    if sha(thumbnail) != row["sha256"]:
        raise ValueError("Surface image digest mismatch")
    return thumbnail


def texture(mat, image, period, normal=False):
    # Object coordinates in metres keep the grain consistent across boards.
    tree = mat.node_tree
    uv = tree.nodes.new("ShaderNodeTexCoord")
    scale = tree.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs["Scale"].default_value = 1 / period
    tree.links.new(uv.outputs["Object"], scale.inputs[0])
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.projection = "BOX"
    tex.projection_blend = 0.15
    tree.links.new(scale.outputs[0], tex.inputs["Vector"])
    shader = tree.nodes.get("Principled BSDF")
    if normal:
        bump = tree.nodes.new("ShaderNodeNormalMap")
        bump.inputs["Strength"].default_value = 0.27
        tree.links.new(tex.outputs["Color"], bump.inputs["Color"])
        tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    else:
        tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])


def aim(obj, target):
    obj.rotation_euler = (
        (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def light(name, position, target, width, height, power, color):
    lamp = bpy.data.lights.new(name, "AREA")
    lamp.shape = "RECTANGLE"
    lamp.size, lamp.size_y, lamp.energy, lamp.color = width, height, power, color
    obj = bpy.data.objects.new(name, lamp)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, target)


def architecture(room, materials):
    w, d, h = room["width_m"], room["depth_m"], room["ceiling_height_m"]
    box(
        "Ceiling", (w / 2, d / 2, h + 0.05), (w + 0.2, d + 0.2, 0.1), materials["ivory"]
    )
    # Narrow gaps between boards reveal the warm underfloor.
    box("Subfloor", (w / 2, d / 2, -0.06), (w, d, 0.08), materials["edge"])
    row = 0
    while (y := row * 0.19) < d - 1e-6:
        depth = min(0.19, d - y)
        x = -0.57 * (row % 3)
        while x < w:
            a, b = max(0, x), min(w, x + 1.88)
            if b - a > 0.006:
                box(
                    "Oak floorboard",
                    ((a + b) / 2, y + depth / 2, -0.011),
                    (b - a - 0.002, depth - 0.002, 0.022),
                    materials["oak"],
                    0.001,
                )
            x += 1.88
        row += 1
    openings = room["doors"] + room["windows"]
    for wall in ("north", "south", "east", "west"):
        east_west = wall in ("east", "west")
        length = d if east_west else w
        inward = -1 if wall in ("east", "north") else 1
        wall_axis = {"west": 0, "east": w, "south": 0, "north": d}[wall]

        def point(t, z, inset=0, axis=wall_axis, sign=inward, ew=east_west):
            v = axis + sign * inset
            return (v, t, z) if ew else (t, v, z)

        def segment(
            name, start, end, lo, hi, thickness, inset, mat, pos=point, ew=east_west
        ):
            if end - start < 1e-6 or hi - lo < 1e-6:
                return
            sizes = (thickness, end - start) if ew else (end - start, thickness)
            box(
                name,
                pos((start + end) / 2, (lo + hi) / 2, inset),
                (*sizes, hi - lo),
                mat,
            )

        holes = [o for o in openings if o["wall"] == wall]
        cuts = sorted(
            {
                0,
                length,
                *(
                    x
                    for o in holes
                    for x in (o["offset_m"], o["offset_m"] + o["width_m"])
                ),
            }
        )
        for left, right in itertools.pairwise(cuts):
            mid = (left + right) / 2
            exclusions = sorted(
                (o.get("sill_height_m", 0), o.get("sill_height_m", 0) + o["height_m"])
                for o in holes
                if o["offset_m"] < mid < o["offset_m"] + o["width_m"]
            )
            z = 0
            for low, high in [*exclusions, (h, h)]:
                segment(
                    wall + " plaster",
                    left,
                    right,
                    z,
                    low,
                    0.12,
                    -0.06,
                    materials["plaster"],
                )
                if z == 0 and low > 0.1:
                    segment(
                        "Skirting",
                        left,
                        right,
                        0,
                        0.095,
                        0.024,
                        0.012,
                        materials["ivory"],
                    )
                z = max(z, high)
        for win in (o for o in room["windows"] if o["wall"] == wall):
            x, span, sill, high = (
                win["offset_m"],
                win["width_m"],
                win["sill_height_m"],
                win["height_m"],
            )
            mid = x + span / 2
            segment(
                "Sill",
                x - 0.035,
                x + span + 0.035,
                sill - 0.045,
                sill,
                0.20,
                0.02,
                materials["ivory"],
            )
            for t in (x, mid, x + span):
                segment(
                    "Window frame",
                    t - 0.025,
                    t + 0.025,
                    sill,
                    sill + high,
                    0.08,
                    0,
                    materials["ivory"],
                )
            upper = min(sill + high + 0.16, h - 0.12)
            segment(
                "Curtain rail",
                x - 0.14,
                x + span + 0.14,
                upper,
                upper + 0.025,
                0.028,
                0.11,
                materials["brass"],
            )
            # Folded fabric hangs from the actual window with guaranteed room clearance.
            for center in (max(0.2, x), min(length - 0.2, x + span)):
                verts = [
                    point(
                        center + (i / 40 - 0.5) * min(span * 0.23, 0.38),
                        z,
                        0.13 + 0.043 * math.cos(i * math.pi / 4),
                    )
                    for z in (0.10, upper)
                    for i in range(41)
                ]
                geom = bpy.data.meshes.new("Pleated linen")
                geom.from_pydata(
                    verts, [], [(i, i + 1, i + 42, i + 41) for i in range(40)]
                )
                panel = bpy.data.objects.new("Window linen panel", geom)
                bpy.context.collection.objects.link(panel)
                geom.materials.append(materials["linen"])
                for poly in geom.polygons:
                    poly.use_smooth = True
            light(
                "Daylight through " + win["id"],
                point(mid, sill + high * 0.6, -0.18),
                point(mid, 0.45, min(w, d) * 0.65),
                span,
                high,
                310 * span * high,
                (1, 0.89, 0.76),
            )
    # Same three-layer wall art as the Town walkthrough.
    ax = w * 0.51
    for name, dx, z, width, height, inset, mat in [
        ("Oak print frame", 0, 1.55, 1.05, 0.73, 0.055, "oak"),
        ("Paper", 0, 1.55, 0.96, 0.64, 0.095, "ivory"),
        ("Landscape", 0, 1.45, 0.84, 0.21, 0.111, "sage"),
        ("Terracotta", 0.16, 1.66, 0.18, 0.17, 0.12, "clay"),
    ]:
        box(name, (ax + dx, d - inset, z), (width, 0.016, height), materials[mat])


def load_furniture(item, registry, materials):
    w, d, h = item["reservation_wdh_m"]
    center = Vector(item["center_floor_xyz_m"])
    source = item["source"]
    if not source:
        box(
            "Procedural reservation · " + item["name"],
            center + Vector((0, 0, h / 2)),
            (w, d, h),
            materials["sage"],
            0.015,
        )
        return "procedural reservation"
    digest = source["sha256"]
    if (
        source["kind"] == "catalog"
        and source["id"] == "abo-b074l4976t-amazon-co-uk"
        and digest == DESK
    ):
        path = ASSETS / "furniture/BelayaDesk.glb"
    elif (
        source["kind"] == "concept"
        and (source["id"], source["version"], digest) in registry
    ):
        path = ASSETS / ("designer-" + digest + ".glb")
    else:
        raise ValueError("Unreleased mesh requested for " + item["id"])
    if sha(path) != digest:
        raise ValueError("Native mesh hash mismatch")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = set(bpy.data.objects) - before
    meshes = [o for o in objects if o.type == "MESH"]
    anchor = bpy.data.objects.new(item["id"] + " · " + source["version"], None)
    bpy.context.collection.objects.link(anchor)
    for obj in objects:
        if obj.parent is None:
            obj.parent = anchor
    anchor.location = center + Vector(source["translation_m"])
    anchor.rotation_euler.z = math.radians(item["rotation_deg"])
    anchor["source_sha256"] = digest
    bpy.context.view_layer.update()
    vertices = [obj.matrix_world @ Vector(v) for obj in meshes for v in obj.bound_box]
    if not vertices:
        raise ValueError("Released mesh is empty")
    x, y = item["footprint_xy_m"]
    limits = [(x, x + w), (y, y + d), (0, h)]
    if any(
        min(v[i] for v in vertices) < a - 0.0001
        or max(v[i] for v in vertices) > b + 0.0001
        for i, (a, b) in enumerate(limits)
    ):
        # Some imported parts have rotated local bounding boxes. Evaluate actual
        # vertices for a tight test when the broad-phase box crosses a boundary.
        points = [obj.matrix_world @ v.co for obj in meshes for v in obj.data.vertices]
        if any(
            min(p[i] for p in points) < a - 0.0001
            or max(p[i] for p in points) > b + 0.0001
            for i, (a, b) in enumerate(limits)
        ):
            raise ValueError("Native mesh exceeds its saved reservation: " + item["id"])
    return digest


def render(manifest_path, output, originals):
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("schema_version") != 1 or manifest.get("revision", 0) < 1:
        raise ValueError("A version 1 applied bedroom manifest is required")
    if [cam["id"] for cam in manifest["cameras"]] != ["doorway", "desk", "bedside"]:
        raise ValueError("Unexpected camera set")
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_bytes(manifest_path.read_bytes())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene["manifest_sha256"] = sha(manifest_path)
    scene["saved_revision"] = manifest["revision"]
    scene["home_id"] = manifest["home_id"]
    scene["project"] = manifest["project"]
    m = {
        key: surface(label, col, rough)
        for key, label, col, rough in [
            ("oak", "Oak veneer", "A88361", 0.58),
            ("edge", "Subfloor", "694B38", 0.79),
            ("ivory", "Warm ivory", "EFE9DB", 0.77),
            ("sage", "Sage", "929C82", 0.87),
            ("clay", "Clay", "BD815B", 0.85),
            ("linen", "Linen", "EAE1D1", 0.91),
            ("rug", "Woven wool", "BD9471", 0.92),
            ("brass", "Brushed brass", "9A7546", 0.31),
            (
                "plaster",
                "Bedroom plaster",
                {"oak": "E5D6BC", "sage": "BAC6AD", "terracotta": "D8AB91"}[
                    manifest["palette"]
                ],
                0.85,
            ),
        ]
    }
    rows = json.loads((SURFACES / "bedroom-sources.json").read_text())
    images = {}
    surface_hashes = {}
    for row in rows:
        file = material_image(row, originals)
        images[row["asset"]] = bpy.data.images.load(str(file))
        surface_hashes[row["asset"]] = sha(file)
    images["rough_linen"].colorspace_settings.name = "Non-Color"
    texture(m["oak"], images["oak_veneer_01"], 1.8)
    for mat in (m["rug"], m["linen"]):
        texture(mat, images["rough_linen"], 0.30, normal=True)
    scene.world = bpy.data.worlds.new("Courtyard daylight")
    scene.world.use_nodes = True
    env = scene.world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = images["urban_courtyard_02"]
    bg = scene.world.node_tree.nodes.get("Background")
    scene.world.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.8
    room = manifest["room"]
    architecture(room, m)
    registry_data = json.loads((ASSETS / "designer_registry.json").read_text())
    registry = {
        (a["concept_id"], a["version"], a["sha256"])
        for key in ("chairs", "bedroom")
        for a in registry_data.get(key, [])
    }
    used = {f["id"]: load_furniture(f, registry, m) for f in manifest["furniture"]}
    for f in manifest["furniture"]:
        if f["id"] == "queen-bed":
            x, y = f["footprint_xy_m"]
            w, d, _ = f["reservation_wdh_m"]
            x0, x1 = max(0.06, x - 0.58), min(room["width_m"] - 0.06, x + w + 0.58)
            y0, y1 = max(0.06, y - 0.55), min(room["depth_m"] - 0.06, y + d * 0.72)
            box(
                "Bedroom woven rug",
                ((x0 + x1) / 2, (y0 + y1) / 2, 0.012),
                (x1 - x0, y1 - y0, 0.018),
                m["rug"],
                0.008,
            )
        if f["id"] == "bedside-lamp":
            x, y, _ = f["center_floor_xyz_m"]
            light(
                "Reading lamp",
                (x, y, 0.85),
                (x, y, 0.25),
                0.19,
                0.19,
                10,
                (1, 0.78, 0.49),
            )
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 7
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for cam in manifest["cameras"]:
        data = bpy.data.cameras.new(cam["label"])
        data.sensor_fit = "VERTICAL"
        data.lens = data.sensor_height / (
            2 * math.tan(math.radians(cam["vertical_fov_degrees"]) / 2)
        )
        obj = bpy.data.objects.new(cam["id"], data)
        bpy.context.collection.objects.link(obj)
        obj.location = cam["eye_xyz_m"]
        aim(obj, cam["target_xyz_m"])
        if cam["reason"]:
            obj["framing_notice"] = cam["reason"]
    scene.camera = bpy.data.objects["doorway"]
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "bedroom.blend"), compress=True)
    # Reopen the portable scene before producing the downloadable images.
    bpy.ops.wm.open_mainfile(filepath=str(output / "bedroom.blend"))
    scene = bpy.context.scene
    for cam in manifest["cameras"]:
        scene.camera = bpy.data.objects[cam["id"]]
        scene.render.filepath = str(output / (cam["id"] + ".png"))
        bpy.ops.render.render(write_still=True)
    for name in ("BELAYA_ATTRIBUTION.txt", "ABO_LICENSE_CC_BY_4.0.txt"):
        (output / name).write_bytes((ASSETS / "furniture" / name).read_bytes())
    (output / "surface-sources.json").write_text(json.dumps(rows, indent=2))
    receipt = {
        "manifest_sha256": sha(manifest_path),
        "project": manifest["project"],
        "revision": manifest["revision"],
        "home_id": manifest["home_id"],
        "asset_sha256_or_fallback": used,
        "surface_hashes": surface_hashes,
        "blender": bpy.app.version_string,
        "image_size": [1920, 1080],
        "engine": "Cycles CPU",
        "files": {p.name: sha(p) for p in sorted(output.iterdir())},
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    render(*(Path(arg).resolve() for arg in sys.argv[sys.argv.index("--") + 1 :]))
