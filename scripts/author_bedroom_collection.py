"""Author the two native-scale bedroom releases in a disposable Blender process."""

import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from author_designer_chair import (
    horizontal_part,
    loft,
    material,
    mesh_object,
    setup_studio,
)  # noqa: E402

FINISHES = {
    "Oiled oak": ("B39168", 0.42),
    "Oat upholstery": ("C9BAA0", 0.92),
    "Sage linen": ("849781", 0.92),
    "Ivory linen": ("EEE6D6", 0.91),
    "Antique brass": ("9D8161", 0.33),
    "Parchment": ("EFDCB6", 0.78),
}
ASSETS = {
    "upholstered-linen-bed": ("Linen platform bed", [1.6, 2.0, 0.6]),
    "oak-bedside-lamp": ("Oak nightstand and reading lamp", [0.48, 0.43, 1.06]),
}


def cushion(name, finish, x, y, w, d, lo, hi, radius, piping=False):
    # Softened shoulders and a thin parallel welt on each pillow and bolster.
    height = hi - lo
    shapes = [(0, 0.92), (0.15, 0.98), (0.45, 1), (0.76, 0.997), (1, 0.91)]
    if piping:
        shapes = [(0, 0.96), (0.23, 1), (0.75, 1), (1, 0.96)]
    return horizontal_part(
        name,
        finish,
        [
            (lo + height * z, x, y, w * scale, d * scale, radius * scale)
            for z, scale in shapes
        ],
    )


def turned(name, finish, x, y, profile, pleats=False):
    rings = []
    for z, radius in profile:
        points = []
        for i in range(96):
            a = i * 2 * math.pi / 96
            r = radius * (0.97 if pleats and i % 2 else 1)
            points.append((x + r * math.cos(a), y + r * math.sin(a), z))
        rings.append(points)
    return loft(name, finish, rings)


def bed():
    pieces = [
        cushion("Recessed oak plinth", "Oiled oak", 0, 0, 1.37, 1.78, 0, 0.14, 0.05),
        cushion(
            "Upholstered perimeter", "Oat upholstery", 0, 0, 1.6, 2, 0.10, 0.31, 0.08
        ),
        cushion(
            "Mattress, linen ticking",
            "Ivory linen",
            0,
            -0.005,
            1.55,
            1.94,
            0.29,
            0.42,
            0.09,
        ),
        cushion(
            "Slipcovered head rail",
            "Oat upholstery",
            0,
            0.918,
            1.58,
            0.16,
            0.19,
            0.60,
            0.06,
        ),
        cushion("Loft duvet", "Ivory linen", 0, -0.27, 1.58, 1.40, 0.34, 0.475, 0.09),
        cushion(
            "Duvet turnover", "Ivory linen", 0, 0.346, 1.54, 0.19, 0.416, 0.488, 0.055
        ),
    ]
    for side, x in [("Left", -0.37), ("Right", 0.37)]:
        pieces.append(
            cushion(
                side + " pillow", "Ivory linen", x, 0.66, 0.69, 0.36, 0.40, 0.535, 0.13
            )
        )
        pieces.append(
            cushion(
                side + " welt",
                "Oat upholstery",
                x,
                0.66,
                0.69,
                0.36,
                0.458,
                0.466,
                0.13,
                True,
            )
        )
    # Tessellated closed cloth shell with a gently uneven hem and organic folds.
    nx, ny = 52, 14
    vertices = []
    for layer in (0, 1):
        for j in range(ny + 1):
            v = j / ny
            for i in range(nx + 1):
                u = i / nx
                x = (u - 0.5) * 1.58
                y = -0.84 + 0.38 * v + 0.011 * math.sin(4 * math.pi * u + v)
                tuck = max(0, (abs(u - 0.5) - 0.424) / 0.076)
                z = (
                    0.49
                    - 0.105 * tuck * tuck
                    + 0.009 * math.sin(8 * math.pi * u + 1.7 * v)
                    + 0.005 * math.sin(23 * u - 3 * v)
                    - layer * 0.008
                )
                vertices.append((x, y, z))
    faces = []
    n = (nx + 1) * (ny + 1)
    for j in range(ny):
        for i in range(nx):
            q = j * (nx + 1) + i
            face = (q, q + 1, q + nx + 2, q + nx + 1)
            faces.extend([face, tuple(a + n for a in reversed(face))])
    perimeter = [
        *range(nx + 1),
        *[j * (nx + 1) + nx for j in range(1, ny + 1)],
        *range(n - 2, n - nx - 2, -1),
        *[j * (nx + 1) for j in range(ny - 1, 0, -1)],
    ]
    for k, a in enumerate(perimeter):
        b = perimeter[(k + 1) % len(perimeter)]
        faces.append((b, a, a + n, b + n))
    pieces.append(("Folded sage coverlet", "Sage linen", vertices, faces))
    return pieces


def bedside():
    pieces = []
    for ix, x in enumerate((-0.191, 0.191)):
        for iy, y in enumerate((-0.166, 0.166)):
            pieces.append(
                turned(
                    f"Tapered foot {ix + 1}.{iy + 1}",
                    "Oiled oak",
                    x,
                    y,
                    [(0, 0.017), (0.12, 0.022)],
                )
            )
    pieces.extend(
        [
            cushion("Open shelf", "Oiled oak", 0, 0, 0.46, 0.41, 0.095, 0.122, 0.025),
            cushion("Oak case", "Oiled oak", 0, 0, 0.47, 0.418, 0.375, 0.54, 0.024),
            cushion(
                "Left stile", "Oiled oak", -0.213, 0, 0.03, 0.38, 0.11, 0.39, 0.009
            ),
            cushion(
                "Right stile", "Oiled oak", 0.213, 0, 0.03, 0.38, 0.11, 0.39, 0.009
            ),
            cushion(
                "Drawer front", "Oiled oak", 0, -0.200, 0.423, 0.018, 0.395, 0.51, 0.008
            ),
            cushion(
                "Drawer edge pull",
                "Antique brass",
                0,
                -0.205,
                0.12,
                0.018,
                0.479,
                0.49,
                0.007,
            ),
            cushion(
                "Cantilevered top", "Oiled oak", 0, 0, 0.48, 0.43, 0.529, 0.557, 0.029
            ),
            turned(
                "Footed lamp base",
                "Antique brass",
                0.032,
                0.028,
                [(0.557, 0.071), (0.565, 0.086), (0.58, 0.08), (0.593, 0.034)],
            ),
            turned(
                "Lamp stem",
                "Antique brass",
                0.032,
                0.028,
                [(0.586, 0.016), (0.79, 0.012), (0.85, 0.019)],
            ),
            turned(
                "Pleated shade",
                "Parchment",
                0.032,
                0.028,
                [(0.816, 0.151), (0.824, 0.153), (1.043, 0.084), (1.049, 0.081)],
                True,
            ),
            turned(
                "Brass finial",
                "Antique brass",
                0.032,
                0.028,
                [(1.046, 0.01), (1.056, 0.012), (1.06, 0.006)],
            ),
        ]
    )
    return pieces


def author(directory, key):
    import bpy
    from mathutils import Vector

    name, dimensions = ASSETS[key]
    dest = directory / key
    dest.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = name
    scene.unit_settings.system = "METRIC"
    coll = bpy.data.collections.new("Editable furniture")
    scene.collection.children.link(coll)
    pieces = bed() if key == "upholstered-linen-bed" else bedside()
    mats = {n: material(bpy, n, *FINISHES[n]) for n in {p[1] for p in pieces}}
    if "Antique brass" in mats:
        mats["Antique brass"].node_tree.nodes.get("Principled BSDF").inputs[
            "Metallic"
        ].default_value = 0.76
    for part, finish, vs, fs in pieces:
        mesh_object(bpy, coll, part, vs, fs, mats[finish], True)
    bpy.ops.export_scene.gltf(
        filepath=str(dest / "model.glb"),
        export_format="GLB",
        use_active_scene=True,
        export_animations=False,
    )
    cameras = setup_studio(bpy, scene)
    isbed = key == "upholstered-linen-bed"
    for camera, loc, filename in zip(
        cameras,
        [(0, -3.5, 1.8), (2.35, -3.2, 2.1)],
        ["front.png", "three-quarter.png"],
        strict=True,
    ):
        camera.location = loc
        camera.rotation_euler = (
            (Vector((0, 0, 0.30 if isbed else 0.52)) - camera.location)
            .to_track_quat("-Z", "Y")
            .to_euler()
        )
        camera.data.ortho_scale = 2.85 if isbed else 1.28
        scene.camera = camera
        scene.render.filepath = str(dest / filename)
        bpy.ops.render.render(write_still=True)
    scene.render.filepath = "//preview.png"
    bpy.data.libraries.write(str(dest / "editable.blend"), {scene}, compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(dest / "editable.blend"))
    if sorted(
        o.name for o in bpy.data.collections["Editable furniture"].objects
    ) != sorted(p[0] for p in pieces):
        raise ValueError("Editable part inventory changed on reopening")
    files = ["editable.blend", "model.glb", "front.png", "three-quarter.png"]
    report = dict(
        concept_id=key,
        version="1.0.0",
        name=name,
        dimensions_wdh_m=dimensions,
        parts=[p[0] for p in pieces],
        finishes=sorted(mats),
        blender=bpy.app.version_string,
        reopened=True,
        sha256={f: hashlib.sha256((dest / f).read_bytes()).hexdigest() for f in files},
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (dest / "authoring.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    for asset in ASSETS:
        author(out, asset)
