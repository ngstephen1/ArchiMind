"""Build an editable whole-home scene from Town's downloaded client manifest."""

import argparse
import hashlib
import json
import math
import sys
import tempfile
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_saved_bedroom as bedroom  # noqa: E402


def translate_new(before, origin):
    for obj in set(bpy.data.objects) - before:
        if not obj.parent:
            obj.location += Vector((*origin, 0))


def camera(view, name):
    data = bpy.data.cameras.new(name)
    data.sensor_fit = "VERTICAL"
    data.lens = data.sensor_height / (2 * math.tan(math.radians(view["fov"]) / 2))
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)

    def convert(p):
        return (p[0], -p[2], p[1])

    obj.location = convert(view["eye"])
    bedroom.aim(obj, convert(view["target"]))
    return obj


def studio_piece(piece, finishes):
    name, mat, dims = piece["name"], finishes[piece["finish"]], piece["wdh"]
    if piece["shape"] == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=24, ring_count=14, radius=0.5, location=piece["xyz"]
        )
    elif piece["shape"] == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32, radius=0.5, depth=1, location=piece["xyz"]
        )
    else:
        return bedroom.box(name, piece["xyz"], dims, mat, piece["radius"])
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) <= 4
    return obj


def gray_studies(scene, board, out):
    """Six unobstructed eye positions per benchmark room, all inside its shell."""
    assessments = []
    previous = scene.camera
    width, height = scene.render.resolution_x, scene.render.resolution_y
    count = scene.cycles.samples
    scene.render.resolution_x, scene.render.resolution_y = 480, 270
    scene.cycles.samples = 4
    scene.view_layers[0].material_override = bedroom.surface("Gray model", "BEBEBA")
    for part in board["rooms"]:
        room = part["room"]
        if room["id"] not in ("bedroom", "salon"):
            continue
        w, d = room["width_m"], room["depth_m"]
        focus = part["cameras"][0]["target"]
        poses = []
        for sx, sy in [
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
            (0.5, 0),
            (0, 0.5),
            (0.5, 1),
            (1, 0.5),
            (0.25, 0.25),
            (0.75, 0.75),
            (0.25, 0.75),
            (0.75, 0.25),
        ]:
            x = 0.24 + sx * (w - 0.48)
            y = 0.24 + sy * (d - 0.48)
            if any(
                f["x_m"] - 0.16 < x < f["x_m"] + f["width_m"] + 0.16
                and f["y_m"] - 0.16 < y < f["y_m"] + f["depth_m"] + 0.16
                for f in part["furniture"]
            ):
                continue
            poses.append([part["origin"][0] + x, 1.52, -(part["origin"][1] + y)])
        for index, eye in enumerate(poses[:6]):
            name = f"study-{room['id']}-{index + 1}"
            scene.camera = camera({"eye": eye, "target": focus, "fov": 58}, name)
            scene.render.filepath = str(out / (name + ".png"))
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(scene.render.filepath)
            pixels = np.empty(len(image.pixels), dtype=np.float32)
            image.pixels.foreach_get(pixels)
            rgb = pixels.reshape((-1, 4))[:, :3]
            luma = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
            low, high = np.percentile(luma, [5, 95])
            assessments.append(
                {
                    "view": name,
                    "eye": eye,
                    "range_p05_p95": [float(low), float(high)],
                    "review": "check flat lighting"
                    if high - low < 0.10
                    else "tonal range present",
                }
            )
            bpy.data.images.remove(image)
    (out / "camera-studies.json").write_text(json.dumps(assessments, indent=2))
    scene.camera = previous
    scene.view_layers[0].material_override = None
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.cycles.samples = count


def sample_benchmark(scene, out):
    """Compare linear RGB on the central salon detail against the 512-sample crop."""
    scene.render.use_border = scene.render.use_crop_to_border = True
    scene.render.border_min_x, scene.render.border_max_x = 0.42, 0.54
    scene.render.border_min_y, scene.render.border_max_y = 0.38, 0.56
    scene.render.image_settings.file_format = "OPEN_EXR"
    crops = {}
    timings = {}
    for samples in (128, 256, 512):
        scene.cycles.samples = samples
        path = out / f"benchmark-{samples}.exr"
        scene.render.filepath = str(path)
        start = time.monotonic()
        bpy.ops.render.render(write_still=True)
        timings[samples] = round(time.monotonic() - start, 2)
        img = bpy.data.images.load(str(path))
        rgba = np.empty(len(img.pixels), dtype=np.float32)
        img.pixels.foreach_get(rgba)
        crops[samples] = rgba.reshape((-1, 4))[::4, :3].copy()
        bpy.data.images.remove(img)
    errors = {}
    for n, vals in crops.items():
        errors[n] = float(np.percentile(np.abs(vals - crops[512]), 95))
    selected = next(n for n in (128, 256, 512) if errors[n] <= 0.015)
    scene.render.use_border = scene.render.use_crop_to_border = False
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = selected
    return {"max_samples": selected, "seconds": timings, "p95_linear_rgb_error": errors}


def save_view(scene, out, name, linear_master):
    scene.render.filepath = str(out / (name + ".png"))
    bpy.ops.render.render(write_still=True)
    if linear_master:
        scene.render.image_settings.file_format = "OPEN_EXR"
        bpy.data.images["Render Result"].save_render(
            str(out / (name + ".exr")), scene=scene
        )
        scene.render.image_settings.file_format = "PNG"


def lighting_studies(scene, out, hero, linear_master):
    scene.camera = bpy.data.objects[hero]
    scene.render.use_freestyle = True
    scene.view_layers[0].material_override = bedroom.surface("Drawing paper", "EEEDE8")
    settings = scene.view_layers[0].freestyle_settings
    outline = (
        settings.linesets[0]
        if len(settings.linesets)
        else settings.linesets.new("Silhouettes")
    )
    outline.select_silhouette = outline.select_border = True
    outline.select_crease = False
    if not outline.linestyle:
        outline.linestyle = bpy.data.linestyles.new("Silhouette ink")
    outline.linestyle.color = (0.025, 0.033, 0.031)
    outline.linestyle.thickness = scene.render.resolution_x / 960
    crease = settings.linesets.new("Furniture and joinery")
    crease.select_silhouette = crease.select_border = False
    crease.select_crease = True
    if not crease.linestyle:
        crease.linestyle = bpy.data.linestyles.new("Joinery ink")
    crease.linestyle.color = (0.19, 0.18, 0.15)
    crease.linestyle.thickness = 0.48 * scene.render.resolution_x / 960
    save_view(scene, out, hero + "-drawing", linear_master)
    scene.render.use_freestyle = False
    scene.view_layers[0].material_override = None
    scene.world.node_tree.nodes.get("Background").inputs[
        "Strength"
    ].default_value = 0.035
    for lamp in bpy.data.lights:
        if lamp.type == "SUN":
            lamp.energy = 0
        elif "aylight" in lamp.name:
            lamp.energy *= 0.045
    save_view(scene, out, hero + "-evening", linear_master)


def render(args):
    source = args.manifest.read_bytes()
    board = json.loads(source)
    if board.get("kind") != "whole-home-presentation" or any(
        board[k] != board["bedroom"][k]
        for k in ("project", "revision", "home_id", "palette")
    ):
        raise ValueError("Expected one applied whole-home revision")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "manifest.json").write_bytes(source)
    for name in ("BELAYA_ATTRIBUTION.txt", "ABO_LICENSE_CC_BY_4.0.txt"):
        (out / name).write_bytes((bedroom.ASSETS / "furniture" / name).read_bytes())
    (out / "surface-sources.json").write_bytes(
        (bedroom.SURFACES / "bedroom-sources.json").read_bytes()
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        path = tmp / "manifest.json"
        path.write_text(json.dumps(board["bedroom"]))
        bedroom.render(path, tmp / "base", args.originals, True, include_hall=False)
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        if obj.type == "CAMERA":
            bpy.data.objects.remove(obj, do_unlink=True)
    translate_new(set(), board["bedroom"]["origin_xy_m"])
    mats = {
        key: bpy.data.materials[name]
        for key, name in {
            "oak": "Oak veneer",
            "edge": "Subfloor",
            "ivory": "Warm ivory",
            "brass": "Brushed brass",
            "linen": "Linen",
            "rug": "Woven wool",
            "plaster": "Bedroom plaster",
            "sage": "Sage",
            "clay": "Clay",
        }.items()
    }
    finishes = {
        k: bedroom.surface(k, v.lstrip("#")) for k, v in board["finishes"].items()
    }
    finishes["oak"] = mats["oak"]
    finishes["brass"].node_tree.nodes.get("Principled BSDF").inputs[
        "Metallic"
    ].default_value = 0.82
    finishes["wool"].node_tree.nodes.get("Principled BSDF").inputs[
        "Sheen Weight"
    ].default_value = 0.55
    # A side-lit finish study uses one soft sun shared by all rooms.
    sun_data = bpy.data.lights.new("Late afternoon sun", "SUN")
    sun_data.energy = 1.6
    sun_data.angle = math.radians(7)
    sun_data.color = (1.0, 0.91, 0.79)
    sun = bpy.data.objects.new("Late afternoon sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = Vector((1.0, 0.27, -0.39)).to_track_quat("-Z", "Y").to_euler()
    for key, roughness, metal in (
        ("brass", 0.23, 0.82),
        ("marble", 0.30, 0),
        ("glass", 0.12, 0.05),
    ):
        shader = finishes[key].node_tree.nodes.get("Principled BSDF")
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metal
    glass = finishes["glass"].node_tree.nodes.get("Principled BSDF")
    glass.inputs["Transmission Weight"].default_value = 0.72
    glass.inputs["IOR"].default_value = 1.48
    for key in ("wool", "moss", "paper"):
        shader = finishes[key].node_tree.nodes.get("Principled BSDF")
        shader.inputs["Sheen Weight"].default_value = 0.43
        tree = finishes[key].node_tree
        tex = tree.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 360
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.18
        bump.inputs["Distance"].default_value = 0.0016
        tree.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    coverlet = None
    views = []
    for part in board["rooms"]:
        room = part["room"]
        if textile := part.get("textile"):
            cloth_mesh = bpy.data.meshes.new(textile["name"])
            cloth_mesh.from_pydata(textile["vertices"], [], textile["faces"])
            cloth_mesh.update()
            coverlet = bpy.data.objects.new(textile["name"], cloth_mesh)
            bpy.context.collection.objects.link(coverlet)
            coverlet.location = (*part["origin"], 0)
            cloth_mesh.materials.append(mats["linen"])
            for poly in cloth_mesh.polygons:
                poly.use_smooth = True
            seam = coverlet.modifiers.new("Turned fabric edge", "SOLIDIFY")
            seam.thickness = 0.003
        if room["id"] != "bedroom":
            before = set(bpy.data.objects)
            bedroom.architecture(room, mats)
            for piece in part["details"]:
                studio_piece(piece, finishes)
            for item in part["furniture"]:
                for piece in item["parts"]:
                    studio_piece(piece, finishes)
                if not item["parts"]:
                    bedroom.box(
                        "Reservation / " + item["name"],
                        (
                            item["x_m"] + item["width_m"] / 2,
                            item["y_m"] + item["depth_m"] / 2,
                            item["height_m"] / 2,
                        ),
                        (item["width_m"], item["depth_m"], item["height_m"]),
                        mats["sage"],
                        0.02,
                    )
                if item["id"] == "salon-dining":
                    x = item["x_m"] + item["width_m"] / 2
                    y = item["y_m"] + item["depth_m"] / 2
                    for dx in (-0.42, 0, 0.42):
                        bedroom.light(
                            "Pendant practical",
                            (x + dx, y, 1.98),
                            (x + dx, y, 0.75),
                            0.18,
                            0.18,
                            30,
                            (1, 0.75, 0.45),
                        )
            translate_new(before, part["origin"])
        for v in part["cameras"]:
            obj = camera(v, room["id"] + "-" + v["id"])
            views.append((room["id"], obj.name))
    depth = board["depth"]
    for z, mat in ((-0.04, "oak"), (2.84, "ivory")):
        bedroom.box(
            "Hall", (board["hall"] + 0.8, depth / 2, z), (1.6, depth, 0.08), mats[mat]
        )
    bedroom.box(
        "Hall end", (board["hall"] + 0.8, depth, 1.4), (1.6, 0.1, 2.8), mats["plaster"]
    )
    scene["board_sha256"] = hashlib.sha256(source).hexdigest()
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.025 if args.proof else 0.012
    scene.cycles.samples = 16 if args.proof else 128
    scene.render.resolution_x, scene.render.resolution_y = (
        (960, 540) if args.proof else (3840, 2160)
    )
    devices = []
    if args.gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.refresh_devices()
        for device in prefs.devices:
            device.use = device.type == "OPTIX"
            if device.use:
                devices.append(device.name)
        if not devices:
            raise RuntimeError("No OptiX device detected")
        scene.cycles.device = "GPU"
    hero = next((name for room, name in views if room == "salon"), views[0][1])
    scene.camera = bpy.data.objects[hero]
    cloth_name = coverlet.name if coverlet else None
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "home.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(out / "home.blend"))
    scene = bpy.context.scene
    assert scene["board_sha256"] == hashlib.sha256(source).hexdigest()

    gray_studies(scene, board, out)
    benchmark = sample_benchmark(scene, out) if not args.proof else None

    for room, name in views:
        scene.camera = bpy.data.objects[name]
        save_view(scene, out, name, not args.proof)
    if cloth_name:
        scene.camera = bpy.data.objects["bedroom-bedside"]
        cloth = bpy.data.objects[cloth_name]
        cloth.hide_render = True
        save_view(scene, out, "bedroom-bedside-before", not args.proof)
        cloth.hide_render = False
    lighting_studies(scene, out, hero, not args.proof)
    (out / "receipt.json").write_text(
        json.dumps(
            {
                "home_id": board["home_id"],
                "revision": board["revision"],
                "manifest_sha256": scene["board_sha256"],
                "devices": devices or ["CPU"],
                "samples": scene.cycles.samples,
                "benchmark": benchmark,
                "size": [scene.render.resolution_x, scene.render.resolution_y],
                "files": {p.name: bedroom.sha(p) for p in out.iterdir() if p.is_file()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--originals", type=Path, default=Path("output/surface-originals"))
    p.add_argument("--gpu", action="store_true")
    p.add_argument("--proof", action="store_true")
    render(p.parse_args(sys.argv[sys.argv.index("--") + 1 :]))
