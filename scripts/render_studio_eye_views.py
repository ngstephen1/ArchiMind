"""Render two camera-locked eye-level compositions from an accepted whole-home CPU proof."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_studio_home import camera  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(proof, manifest, camera_manifest, output):
    receipt = json.loads((proof / "receipt.json").read_bytes())
    source_sha = sha(manifest)
    board = json.loads(manifest.read_bytes())
    framing = json.loads(camera_manifest.read_bytes())
    if (
        receipt["manifest_sha256"] != source_sha
        or sha(proof / "manifest.json") != source_sha
        or sha(proof / "home.blend") != receipt["files"]["home.blend"]
        or (board["home_id"], board["revision"])
        != (receipt["home_id"], receipt["revision"])
        or board["project"] != framing["project"]
    ):
        raise ValueError(
            "The approved proof or comparison project does not match the selected manifest."
        )
    bedroom = next(p for p in board["rooms"] if p["room"]["id"] == "bedroom")
    frame = next(p for p in framing["rooms"] if p["room"]["id"] == "bedroom")
    if (bedroom["origin"], bedroom["room"]) != (frame["origin"], frame["room"]):
        raise ValueError(
            "The reference camera requires an identical bedroom shell and origin."
        )
    bpy.ops.wm.open_mainfile(filepath=str((proof / "home.blend").resolve()))
    scene = bpy.context.scene
    if scene["board_sha256"] != source_sha:
        raise ValueError("Reopened blend identifies another room revision.")
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.adaptive_threshold = 0.010
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    # A neutral daylight key separates pale bedding from the warm plaster.
    # Keep emitter transforms, intensities, object positions and camera pose fixed.
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    daylight_color = (1.0, 0.955, 0.91)
    daylight = [
        lamp for lamp in bpy.data.lights if lamp.name.startswith("Daylight through ")
    ]
    for lamp in daylight:
        lamp.color = daylight_color
    poses = [
        next(c for c in frame["cameras"] if c["id"] == name)
        for name in ("doorway", "desk")
    ]
    if all(poses[0][key] == poses[1][key] for key in ("eye", "target", "fov")):
        raise ValueError(
            "Desk view fell back to the doorway. Two distinct eye-level views are required."
        )
    output.mkdir(exist_ok=False)
    notices = (
        "BELAYA_ATTRIBUTION.txt",
        "ABO_LICENSE_CC_BY_4.0.txt",
        "surface-sources.json",
    )
    for name in notices:
        data = (proof / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != receipt["files"][name]:
            raise ValueError("Source notice differs from the accepted proof: " + name)
        (output / name).write_bytes(data)
    shots = []
    for pose in poses:
        name = pose["id"]
        scene.camera = camera(pose, "Comparison " + name)
        path = output / f"bedroom-{name}.png"
        scene.render.filepath = str(path.resolve())
        bpy.ops.render.render(write_still=True)
        shots.append(
            {"view": name, "camera": pose, "file": path.name, "sha256": sha(path)}
        )
    (output / "eye-view-receipt.json").write_text(
        json.dumps(
            {
                "home_id": board["home_id"],
                "revision": board["revision"],
                "manifest_sha256": source_sha,
                "camera_manifest_sha256": sha(camera_manifest),
                "proof_blend_sha256": receipt["files"]["home.blend"],
                "blender_version": bpy.app.version_string,
                "engine": scene.render.engine,
                "device": "CPU",
                "max_samples": 96,
                "threshold": 0.010,
                "resolution": [1920, 1080],
                "view_transform": scene.view_settings.view_transform,
                "view_look": scene.view_settings.look,
                "daylight_rgb": daylight_color,
                "daylight_emitters": sorted(lamp.name for lamp in daylight),
                "source_notices": {name: receipt["files"][name] for name in notices},
                "shots": shots,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("proof", "manifest", "camera_manifest", "output"):
        p.add_argument(key, type=Path)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    render(a.proof, a.manifest, a.camera_manifest, a.output)
