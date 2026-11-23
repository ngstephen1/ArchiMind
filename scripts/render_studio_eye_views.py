"""Render two camera-locked eye-level compositions from an accepted whole-home CPU proof."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_saved_bedroom import light  # noqa: E402
from render_studio_home import camera  # noqa: E402
from stage_studio_manifest import proof_has_saved_style  # noqa: E402
from studio_photography import attach_textile_detail, daylight_exposure  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transmitted_daylight(board, scene):
    """Place a diffused daylight source immediately inside each saved window covering."""
    directions = {"west": (1, 0), "east": (-1, 0), "south": (0, 1), "north": (0, -1)}
    emitters = []
    for part in board["rooms"]:
        for opening in part["room"]["windows"]:
            source = bpy.data.objects.get("Daylight through " + opening["id"])
            if source is None or source.type != "LIGHT":
                raise ValueError("Missing daylight source for " + opening["id"])
            inset = directions[opening["wall"]]
            lamp = source.copy()
            lamp.data = source.data.copy()
            lamp.name = "Diffuse daylight at " + opening["id"]
            lamp.data.name = lamp.name
            scene.collection.objects.link(lamp)
            # The proof's exterior light stays 0.18 m outside. This area models
            # transmitted daylight on the room-facing side of the thick drape proxy.
            lamp.location.x += 0.40 * inset[0]
            lamp.location.y += 0.40 * inset[1]
            lamp.data.energy *= 0.42
            emitters.append(
                {
                    "window": opening["id"],
                    "position": list(lamp.location),
                    "power_W": lamp.data.energy,
                }
            )
    return emitters


def architectural_camera(pose):
    """Keep the salon's eye and azimuth, with level verticals and optical lens shift."""
    eye, target = pose["eye"], pose["target"]
    horizontal = math.hypot(target[0] - eye[0], target[2] - eye[2])
    slope = (target[1] - eye[1]) / horizontal
    level_target = [target[0], eye[1], target[2]]
    obj = camera({**pose, "target": level_target}, "Salon architectural perspective")
    obj.data.shift_y = slope / (2 * math.tan(math.radians(pose["fov"]) / 2))
    return obj, {"level_target": level_target, "shift_y": obj.data.shift_y}


def desk_task_scene(scene, bedroom):
    """Switch the reopened proof to a controlled, modeled desk task light."""
    desk = next(
        (piece for piece in bedroom["furniture"] if piece["id"] == "belaya"), None
    )
    if desk is None or desk["rotation_deg"]:
        raise ValueError("Task lighting needs the saved unrotated writing desk.")
    ox, oy = bedroom["origin"]
    center_x = ox + desk["x_m"] + desk["width_m"] / 2
    center_y = oy + desk["y_m"] + desk["depth_m"] / 2
    working_top = desk["height_m"]
    location = (center_x - desk["width_m"] * 0.28, center_y, working_top + 0.44)
    target = (center_x + 0.08, center_y, working_top)
    for obj in scene.objects:
        if obj.type == "LIGHT":
            obj.hide_render = True
    if scene.world and scene.world.use_nodes:
        for node in scene.world.node_tree.nodes:
            if node.type == "BACKGROUND":
                strength = node.inputs["Strength"]
                for link in list(strength.links):
                    scene.world.node_tree.links.remove(link)
                strength.default_value = 0.04
    color = (1.0, 0.79, 0.57)
    name = "Modeled bedroom desk task emitter"
    light(name, location, target, 0.22, 0.14, 9.0, color)
    return {
        "source": "Modeled task emitter for this proof",
        "fixture_status": "awaiting product and site measurements",
        "desk_id": desk["id"],
        "location_m": location,
        "target_m": target,
        "size_m": [0.22, 0.14],
        "power_W": 9.0,
        "color_rgb": color,
        "ambient_world_strength": 0.04,
    }


def render(
    proof,
    manifest,
    camera_manifest,
    output,
    salon_cover=False,
    expected_snapshot=None,
    lighting_proof=False,
):
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
    styled = proof_has_saved_style(proof, receipt, expected_snapshot)
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
    file_images = [
        image for image in bpy.data.images if image.source == "FILE" and image.users
    ]
    if any(not image.packed_file for image in file_images):
        raise ValueError("The accepted scene has an unpacked external image")
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32 if lighting_proof else 96
    scene.cycles.adaptive_threshold = 0.02 if lighting_proof else 0.010
    scene.cycles.use_denoising = True
    resolution = (960, 540) if lighting_proof else (1920, 1080)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    # A neutral daylight key separates pale bedding from the warm plaster.
    # Grading and transmitted window light are shared identically across revisions.
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    daylight_color = (1.0, 0.955, 0.91)
    daylight = [
        lamp for lamp in bpy.data.lights if lamp.name.startswith("Daylight through ")
    ]
    for lamp in daylight:
        lamp.color = daylight_color
    diffuse_windows = (
        transmitted_daylight(board, scene)
        if styled and not board.get("presentation_detail")
        else []
    )
    fabrics = attach_textile_detail() if styled else []
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
    if styled:
        notices += ("saved-style-receipt.json",)
    for name in notices:
        data = (proof / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != receipt["files"][name]:
            raise ValueError("Source notice differs from the accepted proof: " + name)
        (output / name).write_bytes(data)
    shots = []
    photo_sources = [("bedroom", pose, sha(camera_manifest)) for pose in poses]
    if salon_cover:
        salon = next(r for r in board["rooms"] if r["room"]["id"] == "salon")
        photo_sources.append(("salon", salon["cameras"][0], source_sha))
    for room_id, pose, pose_source in photo_sources:
        name = pose["id"]
        if room_id == "salon":
            scene.camera, projection = architectural_camera(pose)
        else:
            scene.camera, projection = camera(pose, "Comparison " + name), None
        room = next(
            part["room"] for part in board["rooms"] if part["room"]["id"] == room_id
        )
        scene.view_settings.exposure = daylight_exposure(room) if styled else 0.0
        path = output / f"{room_id}-{name}.png"
        scene.render.filepath = str(path.resolve())
        bpy.ops.render.render(write_still=True)
        shots.append(
            {
                "room": room_id,
                "exposure_ev": scene.view_settings.exposure,
                "view": name,
                "camera": pose,
                "architectural_projection": projection,
                "camera_manifest_sha256": pose_source,
                "file": path.name,
                "sha256": sha(path),
            }
        )
    if lighting_proof:
        desk_pose = poses[1]
        scene.camera = camera(desk_pose, "Comparison task-lit desk")
        scene.view_settings.exposure = (
            daylight_exposure(bedroom["room"]) if styled else 0.0
        )
        rig = desk_task_scene(scene, bedroom)
        path = output / "bedroom-desk-task.png"
        scene.render.filepath = str(path.resolve())
        bpy.ops.render.render(write_still=True)
        shots.append(
            {
                "room": "bedroom",
                "exposure_ev": scene.view_settings.exposure,
                "view": "desk-task",
                "camera": desk_pose,
                "architectural_projection": None,
                "camera_manifest_sha256": sha(camera_manifest),
                "lighting": rig,
                "file": path.name,
                "sha256": sha(path),
            }
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
                "max_samples": scene.cycles.samples,
                "threshold": 0.02 if lighting_proof else 0.010,
                "resolution": list(resolution),
                "view_transform": scene.view_settings.view_transform,
                "view_look": scene.view_settings.look,
                "textile_relief_materials": fabrics,
                "transmitted_window_emitters": diffuse_windows,
                "packed_file_image_count": len(file_images),
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
    p.add_argument("--salon-cover", action="store_true")
    p.add_argument("--lighting-proof", action="store_true")
    p.add_argument("--expected-snapshot", type=Path)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    render(
        a.proof,
        a.manifest,
        a.camera_manifest,
        a.output,
        a.salon_cover,
        a.expected_snapshot,
        a.lighting_proof,
    )
