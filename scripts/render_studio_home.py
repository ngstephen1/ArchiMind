"""Build an editable whole-home scene from Town's downloaded client manifest."""

import argparse
import hashlib
import json
import math
import sys
import time
import tempfile
from pathlib import Path

import bpy
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
        crops[samples] = list(img.pixels)[::16]
        bpy.data.images.remove(img)
    errors = {}
    for n, vals in crops.items():
        err = sorted(abs(a - b) for a, b in zip(vals, crops[512], strict=True))
        errors[n] = err[int(0.95 * (len(err) - 1))]
    selected = next(n for n in (128, 256, 512) if errors[n] <= 0.015)
    scene.render.use_border = scene.render.use_crop_to_border = False
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = selected
    return {"max_samples": selected, "seconds": timings, "p95_linear_red_error": errors}


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
    views = []
    for part in board["rooms"]:
        room = part["room"]
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
    scene.cycles.samples = 16 if args.proof else args.samples
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
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "home.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(out / "home.blend"))
    scene = bpy.context.scene
    assert scene["board_sha256"] == hashlib.sha256(source).hexdigest()

    gray_studies(scene, board, out)
    benchmark = sample_benchmark(scene, out) if not args.proof else None

    def photo(name):
        scene.render.filepath = str(out / (name + ".png"))
        bpy.ops.render.render(write_still=True)
        if not args.proof:
            scene.render.image_settings.file_format = "OPEN_EXR"
            bpy.data.images["Render Result"].save_render(
                str(out / (name + ".exr")), scene=scene
            )
            scene.render.image_settings.file_format = "PNG"

    for room, name in views:
        scene.camera = bpy.data.objects[name]
        photo(name)
    scene.camera = bpy.data.objects[hero]
    scene.render.use_freestyle = True
    scene.view_layers[0].material_override = bedroom.surface("Drawing paper", "EEEDE8")
    photo(hero + "-drawing")
    scene.render.use_freestyle = False
    scene.view_layers[0].material_override = None
    scene.world.node_tree.nodes.get("Background").inputs[
        "Strength"
    ].default_value = 0.035
    for lamp in bpy.data.lights:
        if "aylight" in lamp.name:
            lamp.energy *= 0.045
    photo(hero + "-evening")
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
    p.add_argument("--samples", type=int, choices=(128, 256, 512), default=128)
    render(p.parse_args(sys.argv[sys.argv.index("--") + 1 :]))
