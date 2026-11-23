"""Render the pinned November finish study with frozen cameras and verified geometry."""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_studio_eye_views import architectural_camera, camera, sha  # noqa: E402
from studio_finish_study import compare_geometry, evaluated_geometry, polish  # noqa: E402
from studio_photography import attach_textile_detail  # noqa: E402


def camera_signature(scene):
    camera = scene.camera
    return {
        "camera": camera.name,
        "rotation_quaternion": list(camera.matrix_world.to_quaternion()),
        "location_m": list(camera.matrix_world.translation),
        "shift_y": camera.data.shift_y,
        "lens_mm": camera.data.lens,
        "exposure_ev": scene.view_settings.exposure,
    }


def render(source, baseline_folder, spec, output, *, proof_only=False):
    pinned = json.loads(spec.read_bytes())
    model = source / "home.blend"
    if (
        sha(model) != pinned["proof_blend_sha256"]
        or sha(source / "manifest.json") != pinned["manifest_sha256"]
    ):
        raise ValueError(
            "The packed model and manifest must match the frozen studio proof."
        )
    for shot in pinned["shots"]:
        if sha(baseline_folder / shot["file"]) != shot["sha256"]:
            raise ValueError("A baseline photograph differs from the frozen receipt.")
    if pinned["transmitted_window_emitters"]:
        raise ValueError("This finish study uses the original window lights only.")

    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    if scene.get("board_sha256") != pinned["manifest_sha256"]:
        raise ValueError("The scene refers to a different Town manifest.")
    used_images = [
        image for image in bpy.data.images if image.source == "FILE" and image.users
    ]
    if len(used_images) != pinned["packed_file_image_count"] or any(
        not image.packed_file for image in used_images
    ):
        raise ValueError("The studio proof is missing packed images.")
    scene.cycles.device = "CPU"
    scene.cycles.samples = pinned["max_samples"]
    scene.cycles.adaptive_threshold = pinned["threshold"]
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = pinned["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = pinned["view_transform"]
    scene.view_settings.look = pinned["view_look"]
    for light in bpy.data.lights:
        if light.name.startswith("Daylight through "):
            light.color = pinned["daylight_rgb"]

    notices = pinned["source_notices"]
    for name, expected in notices.items():
        if Path(name).name != name or sha(source / name) != expected:
            raise ValueError(f"Source notice does not match the frozen proof: {name}")
    before = evaluated_geometry()
    attach_textile_detail()
    alterations = polish(json.loads((source / "manifest.json").read_bytes()))
    geometry_receipt = compare_geometry(before, evaluated_geometry())
    geometry_receipt["scope"] = "Blender evaluated meshes from the loaded view layer"
    scene["finish_study_manifest_sha256"] = pinned["manifest_sha256"]
    output.mkdir(parents=True, exist_ok=False)
    for name in notices:
        (output / name).write_bytes((source / name).read_bytes())
    photos = []
    photospecs = []
    editable = output / "Studio-House-Finish-Study.blend"
    for shot in pinned["shots"]:
        pose = shot["camera"]
        if shot["room"] == "salon":
            camera_obj, projection = architectural_camera(pose)
            if projection != shot["architectural_projection"]:
                raise ValueError(
                    "The salon framing differs from the frozen projection."
                )
        else:
            camera_obj = camera(pose, "Matched " + pose["id"])
        photospecs.append((shot, camera_obj))

    # Each editable shot keeps its own camera and exposure while sharing the same objects.
    bpy.context.view_layer.update()
    originals = set(scene.objects.keys())
    signatures = {}
    for index, (shot, camera_obj) in enumerate(photospecs):
        view = scene if index == 0 else scene.copy()
        view.name = Path(shot["file"]).stem
        view.use_fake_user = True
        if set(view.objects.keys()) != originals:
            raise ValueError(
                "The editable camera scenes must share the mesh inventory."
            )
        view.camera = camera_obj
        view.view_settings.exposure = shot["exposure_ev"]
        view.render.filepath = "//" + shot["file"]
        signatures[view.name] = camera_signature(view)

    bpy.ops.wm.save_as_mainfile(filepath=str(editable))
    bpy.ops.wm.open_mainfile(filepath=str(editable))
    for name, signature in signatures.items():
        reloaded = bpy.data.scenes[name]
        if (
            set(reloaded.objects.keys()) != originals
            or camera_signature(reloaded) != signature
        ):
            raise ValueError(f"Reopened scene does not reproduce the {name} framing.")

    if not proof_only:
        for shot, _ in photospecs:
            view = bpy.data.scenes[Path(shot["file"]).stem]
            path = output / shot["file"]
            view.render.filepath = str(path)
            start = time.monotonic()
            bpy.ops.render.render(write_still=True, scene=view.name)
            photos.append(
                {
                    "file": path.name,
                    "sha256": sha(path),
                    "baseline_sha256": shot["sha256"],
                    "camera": shot["camera"],
                    "exposure_ev": shot["exposure_ev"],
                    "crop": shot["crop"],
                    "seconds": round(time.monotonic() - start, 3),
                }
            )
    (output / "finish-receipt.json").write_text(
        json.dumps(
            {
                "home_id": pinned["home_id"],
                "revision": pinned["revision"],
                "manifest_sha256": pinned["manifest_sha256"],
                "proof_blend_sha256": pinned["proof_blend_sha256"],
                "editable_sha256": sha(editable),
                "blender": bpy.app.version_string,
                "resolution": pinned["resolution"],
                "max_samples": pinned["max_samples"],
                "device": "CPU",
                "geometry": geometry_receipt,
                "source_notices": notices,
                "editable_shots": signatures,
                "proof_only": proof_only,
                "alterations": alterations,
                "new_external_assets": [],
                "shots": photos,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("source", "baseline_folder", "spec", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--proof-only", action="store_true")
    render(**vars(parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])))
