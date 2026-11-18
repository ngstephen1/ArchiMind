"""Build the original ArchiMind writing chair in a fresh Blender scene.

The numeric mesh generator uses metres and also runs under ordinary Python. The
Blender entry point is author_chair(output_directory, variant); the CLI below
accepts arguments after Blender's -- separator.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

WIDTH = 0.48
DEPTH = 0.52
HEIGHT = 0.83
SEAT_HEIGHT = 0.455
BACK_HALF_WIDTH = 0.224
VARIANTS = {"gentle": ("1.0.0", 0.042), "deep": ("1.1.0", 0.071)}
NAME = "Oak writing chair with sage upholstery"
ATTRIBUTION = (
    "Original ArchiMind chair geometry, materials and studio lighting. "
    "Modeled from numeric profiles; no external mesh, image or texture inputs."
)
# sRGB base color, roughness. Coordinates in this file are Blender XYZ.
FINISHES = {
    "Oak": ("BA8D61", 0.42),
    "Oak end grain": ("986C48", 0.50),
    "Sage upholstery": ("91A388", 0.85),
    "Upholstery piping": ("697F61", 0.76),
}


def rounded_rect(width, depth, radius):
    """Counter-clockwise vertices, centred on the origin."""
    points = []
    for corner, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        cx = sx * (width / 2 - radius)
        cy = sy * (depth / 2 - radius)
        for step in range(7):
            angle = (corner + step / 6) * math.pi / 2
            points.append(
                (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            )
    return points


def loft(name, material, rings):
    count = len(rings[0])
    vertices = [point for ring in rings for point in ring]
    faces = [tuple(reversed(range(count)))]
    for row in range(len(rings) - 1):
        a = row * count
        for i in range(count):
            j = (i + 1) % count
            faces.append((a + i, a + j, a + count + j, a + count + i))
    faces.append(tuple(range(len(vertices) - count, len(vertices))))
    return name, material, vertices, faces


def horizontal_part(name, material, sections):
    rings = [
        [(cx + x, cy + y, z) for x, y in rounded_rect(w, d, radius)]
        for z, cx, cy, w, d, radius in sections
    ]
    return loft(name, material, rings)


def chair_meshes(variant):
    """Named parts of the upright chair; the seat faces Blender -Y (glTF +Z)."""
    _, bend = VARIANTS[variant]

    def back_y(x, z):
        # A continuous arc with the centre behind the shoulders and a slight recline.
        recline = min(1, max(0, (z - 0.65) / 0.155))
        return DEPTH / 2 - bend * (x / BACK_HALF_WIDTH) ** 2 - 0.023 * (1 - recline)

    parts = []
    for side, sx in (("Left", -1), ("Right", 1)):
        for end, sy in (("front", -1), ("rear", 1)):
            parts.append(
                horizontal_part(
                    f"{side} {end} leg",
                    "Oak",
                    [
                        (0.000, sx * 0.211, sy * 0.205 - 0.010, 0.025, 0.027, 0.006),
                        (0.009, sx * 0.211, sy * 0.205 - 0.010, 0.029, 0.031, 0.007),
                        (0.365, sx * 0.181, sy * 0.161 - 0.012, 0.039, 0.043, 0.009),
                        (0.396, sx * 0.180, sy * 0.160 - 0.012, 0.040, 0.045, 0.009),
                    ],
                )
            )
        x = sx * 0.188
        parts.append(
            horizontal_part(
                f"{side} back upright",
                "Oak",
                [
                    (0.369, sx * 0.180, 0.147, 0.040, 0.042, 0.008),
                    (0.555, sx * 0.183, 0.174, 0.033, 0.033, 0.007),
                    (0.759, x, back_y(x, 0.759) - 0.009, 0.028, 0.027, 0.006),
                ],
            )
        )
    parts.append(
        horizontal_part(
            "Laminated oak seat shell",
            "Oak end grain",
            [
                (0.368, 0, -0.025, 0.394, 0.368, 0.055),
                (0.390, 0, -0.031, 0.444, 0.411, 0.063),
                (0.402, 0, -0.032, 0.462, 0.427, 0.066),
            ],
        )
    )
    # A low crowned pad, with a separate slim upholstered welt along its edge.
    parts.append(
        horizontal_part(
            "Sage seat cushion",
            "Sage upholstery",
            [
                (0.397, 0, -0.035, 0.451, 0.418, 0.062),
                (0.406, 0, -0.035, 0.471, 0.439, 0.066),
                (0.425, 0, -0.035, WIDTH, 0.450, 0.070),
                (0.440, 0, -0.035, 0.472, 0.443, 0.069),
                (0.449, 0, -0.035, 0.452, 0.421, 0.067),
                (SEAT_HEIGHT, 0, -0.035, 0.400, 0.367, 0.060),
            ],
        )
    )
    parts.append(
        horizontal_part(
            "Seat perimeter welt",
            "Upholstery piping",
            [
                (0.408, 0, -0.035, 0.471, 0.439, 0.067),
                (0.410, 0, -0.035, 0.477, 0.444, 0.068),
                (0.412, 0, -0.035, 0.475, 0.442, 0.068),
            ],
        )
    )
    rings = []
    for slice_index in range(33):
        t = slice_index / 16 - 1
        x = t * BACK_HALF_WIDTH
        top = HEIGHT - 0.018 * t * t
        bottom = 0.657 + 0.025 * t * t
        thickness = 0.022 - 0.005 * t * t
        ring = []
        for dy, dz in rounded_rect(thickness, top - bottom, 0.006):
            z = (top + bottom) / 2 + dz
            ring.append((x, back_y(x, z) - thickness / 2 + dy, z))
        rings.append(ring)
    parts.append(loft("Steam-bent oak backrest", "Oak", rings))
    return parts


def linear_rgb(hex_color):
    def linear(v):
        c = int(v, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(linear(hex_color[i : i + 2]) for i in (0, 2, 4)) + (1,)


def material(bpy, name, hex_color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = linear_rgb(hex_color)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    return mat


def mesh_object(bpy, collection, name, vertices, faces, mat, smooth):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if smooth:
        for face in mesh.polygons:
            face.use_smooth = 0 < face.index < len(faces) - 1
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj


def setup_studio(bpy, scene):
    from mathutils import Vector

    stage = bpy.data.collections.new("Photography studio")
    scene.collection.children.link(stage)
    mesh_object(
        bpy,
        stage,
        "Warm paper sweep",
        [(-20, -20, -0.001), (20, -20, -0.001), (20, 20, -0.001), (-20, 20, -0.001)],
        [(0, 1, 2, 3)],
        material(bpy, "Paper sweep", "E5DFD1", 0.9),
        False,
    )
    target = Vector((0, 0, 0.42))

    def aim(obj):
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()

    for name, position, power, size, color in (
        ("Window key", (-1.1, -1.25, 1.85), 83, 1.35, (1, 0.93, 0.84)),
        ("Soft fill", (1.35, -0.65, 1.1), 37, 1.0, (0.86, 0.93, 1)),
        ("Back rim", (0.4, 1.05, 1.66), 60, 0.85, (1, 0.92, 0.82)),
    ):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.shape, light.size, light.color = power, "DISK", size, color
        obj = bpy.data.objects.new(name, light)
        stage.objects.link(obj)
        obj.location = position
        aim(obj)
    cameras = []
    for name, position in (
        ("Front", (0, -2.55, 0.78)),
        ("Three-quarter", (1.42, -2, 1.15)),
    ):
        camera = bpy.data.cameras.new(name)
        camera.type = "ORTHO"
        camera.ortho_scale = 1.05
        obj = bpy.data.objects.new(name, camera)
        stage.objects.link(obj)
        obj.location = position
        aim(obj)
        cameras.append(obj)
    scene.world = bpy.data.worlds.new("Ambient studio")
    scene.world.color = (0.23, 0.23, 0.23)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 600, 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return cameras


def author_chair(output_directory, variant="gentle"):
    """Create a fresh scene and export a candidate. The caller chooses a new directory."""
    import bpy

    if tuple(bpy.app.version[:2]) < (5, 1):
        raise ValueError("Blender 5.1 or newer is required")
    parts = chair_meshes(variant)
    output = Path(output_directory).expanduser().resolve()
    output.mkdir(exist_ok=False)
    scene = bpy.data.scenes.new(NAME + " — " + variant)
    scene.unit_settings.system = "METRIC"
    collection = bpy.data.collections.new("ArchiMind chair")
    scene.collection.children.link(collection)
    mats = {name: material(bpy, name, *finish) for name, finish in FINISHES.items()}
    for part_name, finish, vertices, faces in parts:
        mesh_object(bpy, collection, part_name, vertices, faces, mats[finish], True)
    scene["archimind_variant"] = variant
    scene["archimind_version"] = VARIANTS[variant][0]
    scene["seat_height_m"] = SEAT_HEIGHT
    # Activate the new scene for operator inspection. Keep all prior scenes intact.
    bpy.context.window.scene = scene
    with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
        result = bpy.ops.export_scene.gltf(
            filepath=str(output / "chair.glb"),
            export_format="GLB",
            export_yup=True,
            use_active_scene=True,
            export_animations=False,
            export_cameras=False,
            export_lights=False,
            export_extras=False,
        )
        if result != {"FINISHED"}:
            raise RuntimeError("Blender GLB export did not finish")
        cameras = setup_studio(bpy, scene)
        for camera, filename in zip(
            cameras, ("front.png", "three-quarter.png"), strict=True
        ):
            scene.camera = camera
            scene.render.filepath = str(output / filename)
            result = bpy.ops.render.render(write_still=True, scene=scene.name)
            if result != {"FINISHED"}:
                raise RuntimeError("Blender preview render did not finish")
        scene.render.filepath = "//preview.png"
        # Save only the new scene and its datablock dependencies. It reopens as an
        # editable project without copying other open documents into the asset.
        bpy.data.libraries.write(str(output / "chair.blend"), {scene}, compress=True)

    version, bend = VARIANTS[variant]
    metadata = {
        "schema_version": 1,
        "concept_id": "oak-sage-writing-chair",
        "version": version,
        "name": NAME,
        "variant": variant,
        "seat_height_m": SEAT_HEIGHT,
        "dimensions_wdh_m": [WIDTH, DEPTH, HEIGHT],
        "blender_version": bpy.app.version_string,
        "attribution": ATTRIBUTION,
        "inputs": {
            "author_script_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "width_mm": 480,
            "depth_mm": 520,
            "height_mm": 830,
            "seat_height_mm": 455,
            "back_bend_mm": round(bend * 1000),
            "parts": [p[0] for p in parts],
            "blender_axes": "X width, -Y front, Z up",
            "glb_axes": "X width, +Z front, Y up",
            "finishes": FINISHES,
        },
        "sha256": {
            f: hashlib.sha256((output / f).read_bytes()).hexdigest()
            for f in ("chair.blend", "chair.glb", "front.png", "three-quarter.png")
        },
    }
    (output / "authoring.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--output", type=Path, required=True)
    args.add_argument("--variant", choices=tuple(VARIANTS), default="gentle")
    selected = args.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None
    )
    author_chair(selected.output, selected.variant)
