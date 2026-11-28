"""Render one perspective with the saved Town pose from an already verified proof."""

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

spec, output, *source = sys.argv[sys.argv.index("--") + 1 :]
view = json.loads(Path(spec).read_text(encoding="utf8"))
if source:
    import runpy

    manifest = Path(source[0]).read_bytes()
    if hashlib.sha256(manifest).hexdigest() != view["manifest_sha256"]:
        raise ValueError("Photo-home manifest and camera revision differ.")
    build = runpy.run_path(str(Path(__file__).with_name("render_photo_shell.py")))[
        "build"
    ]
    build(json.loads(manifest))
    bpy.context.scene["board_sha256"] = view["manifest_sha256"]
if bpy.context.scene.get("board_sha256") != view["manifest_sha256"]:
    raise ValueError("Scene and revision manifest differ.")
scene = bpy.context.scene
data = bpy.data.cameras.new("Bookmarked Town view")
cam = bpy.data.objects.new("Bookmarked Town view", data)
scene.collection.objects.link(cam)


def xyz(p):
    return Vector((p[0], -p[2], p[1]))


cam.location = xyz(view["eye"])
cam.rotation_euler = (
    (xyz(view["target"]) - cam.location).to_track_quat("-Z", "Y").to_euler()
)
data.sensor_fit = "VERTICAL"
data.lens = data.sensor_height / (2 * math.tan(math.radians(view["fov"]) / 2))
data.clip_start = 0.04
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = round(min(1280, 720 * view["aspect"]))
scene.render.resolution_y = round(scene.render.resolution_x / view["aspect"])
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = output
bpy.ops.render.render(write_still=True)
