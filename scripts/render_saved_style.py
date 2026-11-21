"""Transfer Town's verified high-tier style geometry into an editable Blender proof."""

import hashlib
import json
import re

import bpy
from mathutils import Matrix


def read_verified(path, sha, size):
    if not re.fullmatch(r"[0-9a-f]{64}", sha) or path.stat().st_size != size:
        raise ValueError("Invalid released model or material size")
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError("Invalid released model or material digest")
    return path


def tier_file(release, role):
    return next(
        (
            f
            for t in ("high", "both", "low")
            for f in release["files"]
            if f["role"] == role and f["tier"] == t
        ),
        None,
    )


def pack_file(root, entry):
    ext = entry["ext"]
    if not re.fullmatch(r"[a-z0-9]+", ext):
        raise ValueError("Invalid pack extension")
    path = root / "packs" / "assets" / (entry["sha256"] + "." + ext)
    return read_verified(path, entry["sha256"], entry["bytes"])


def pack_surface(root, role, spec, releases, ledger, base):
    release = releases[spec["asset_id"]]
    mat = base.surface(
        "Town pack · " + role, (spec.get("tint") or "#ffffff").lstrip("#")
    )
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    coord = tree.nodes.new("ShaderNodeNewGeometry")
    scale = tree.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs["Scale"].default_value = 1 / spec["tiling_m"]
    tree.links.new(coord.outputs["Position"], scale.inputs[0])
    ledger[role] = {
        "asset_id": spec["asset_id"],
        "source": release["source_url"],
        "license": release["license"],
        "tiling_m": spec["tiling_m"],
        "files": {},
    }
    for file_role, socket in (
        ("diffuse", "Base Color"),
        ("roughness", "Roughness"),
        ("metalness", "Metallic"),
        ("normal", "Normal"),
    ):
        entry = tier_file(release, file_role)
        if not entry:
            continue
        path = pack_file(root, entry)
        image = bpy.data.images.load(str(path), check_existing=True)
        if file_role != "diffuse":
            image.colorspace_settings.name = "Non-Color"
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.projection = "BOX"
        tree.links.new(scale.outputs[0], tex.inputs["Vector"])
        output = tex.outputs["Color"]
        if file_role == "normal":
            normal = tree.nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value = 0.35
            tree.links.new(output, normal.inputs["Color"])
            output = normal.outputs["Normal"]
        if file_role == "diffuse" and spec.get("tint"):
            tint = tree.nodes.new("ShaderNodeMixRGB")
            tint.blend_type = "MULTIPLY"
            tint.inputs[0].default_value = 1
            tint.inputs[2].default_value = base.rgb(spec["tint"].lstrip("#"))
            tree.links.new(output, tint.inputs[1])
            output = tint.outputs[0]
        tree.links.new(output, shader.inputs[socket])
        ledger[role]["files"][file_role] = entry["sha256"]
    return mat


def import_model(model, path, label):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = set(bpy.data.objects) - before
    axes = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    values = model["matrix"]
    transform = Matrix([values[i : i + 4] for i in range(0, 16, 4)]).transposed()
    transform = axes @ transform @ axes.inverted()
    for obj in objects:
        if obj.parent is None:
            obj.matrix_world = transform @ obj.matrix_world
        obj["saved_town_slot"] = label
    bpy.context.view_layer.update()
    points = [
        obj.matrix_world @ vertex.co
        for obj in objects
        if obj.type == "MESH"
        for vertex in obj.data.vertices
    ]
    low, high = model["bounds"]
    expected = ((low[0], -high[2], low[1]), (high[0], -low[2], high[1]))
    actual = (
        [min(p[i] for p in points) for i in range(3)],
        [max(p[i] for p in points) for i in range(3)],
    )
    # Three's bounding-box projection can be looser than transformed mesh vertices.
    if any(
        actual[0][i] < expected[0][i] - 0.0001 or actual[1][i] > expected[1][i] + 0.0001
        for i in range(3)
    ):
        raise ValueError("Imported asset leaves its browser-world bounds: " + label)
    return {
        "slot": label,
        "sha256": model["sha256"],
        "three_expected_blender_bounds": expected,
        "blender_mesh_bounds": actual,
        "three_world_matrix": values,
    }


def decor_shape(shape, label, base, palette):
    mesh = bpy.data.meshes.new(label)
    indices = shape["triangles"]
    mesh.from_pydata(
        shape["vertices"], [], [indices[i : i + 3] for i in range(0, len(indices), 3)]
    )
    mesh.update()
    obj = bpy.data.objects.new(label, mesh)
    bpy.context.collection.objects.link(obj)
    obj["saved_town_slot"] = label
    key = tuple(
        shape[k] for k in ("color", "roughness", "metalness", "emission", "strength")
    )
    sheer = shape["group"].startswith("decor/curtain:")
    key += (sheer,)
    if key not in palette:
        mat = base.surface(
            "Town decor · " + shape["color"], shape["color"], shape["roughness"]
        )
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Metallic"].default_value = shape["metalness"]
        shader.inputs["Emission Color"].default_value = base.rgb(shape["emission"])
        shader.inputs["Emission Strength"].default_value = shape["strength"]
        if sheer:
            # Town's rectangular drape is a proxy. Transmit daylight through its
            # fabric in Cycles while keeping the exact exported shape and transform.
            tree = mat.node_tree
            fabric = tree.nodes.new("ShaderNodeBsdfTranslucent")
            fabric.inputs["Color"].default_value = base.rgb(shape["color"])
            mix = tree.nodes.new("ShaderNodeMixShader")
            mix.inputs[0].default_value = 0.8
            tree.links.new(shader.outputs[0], mix.inputs[1])
            tree.links.new(fabric.outputs[0], mix.inputs[2])
            tree.links.new(
                mix.outputs[0], tree.nodes.get("Material Output").inputs["Surface"]
            )
        palette[key] = mat
    mesh.materials.append(palette[key])


def dress_scene(plan, board, base, out):
    root = base.ASSETS
    ref = plan["style_pack"]
    if not re.fullmatch(r"[a-z_]+", ref["id"]):
        raise ValueError("Unknown style pack")
    pack = json.loads((root / "packs" / (ref["id"] + ".json")).read_bytes())
    if (pack["id"], pack["version"]) != (ref["id"], ref["version"]):
        raise ValueError("Saved pack version missing")
    releases = {
        a["asset_id"]: a
        for a in json.loads((root / "packs/releases.json").read_bytes())
    }
    registry = json.loads((root / "designer_registry.json").read_bytes())["pieces"]
    models = {
        a["sha256"]: (
            root / ("designer-" + a["sha256"] + ".glb"),
            a["bytes"],
            "designer:" + a["concept_id"] + "@" + a["version"],
        )
        for a in registry
    }
    for asset, release in releases.items():
        if release["kind"] == "model" and (f := tier_file(release, "model")):
            models[f["sha256"]] = (pack_file(root, f), f["bytes"], asset)
    surfaces = {}
    materials = {
        role: pack_surface(root, role, pack["surfaces"][role], releases, surfaces, base)
        for role in ("floor", "wall", "ceiling", "trim", "tile")
    }
    for obj in list(bpy.data.objects):
        label = re.sub(r"\.\d+$", "", obj.name)
        if label == "Oak floorboard":
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        role = (
            "wall"
            if label.endswith(" plaster")
            else {"Skirting": "trim", "Ceiling": "ceiling", "Hall end": "wall"}.get(
                label
            )
        )
        if role and obj.type == "MESH":
            obj.data.materials[0] = materials[role]
    for room in board["rooms"]:
        r = room["room"]
        ox, oy = room["origin"]
        w, d = r["width_m"], r["depth_m"]
        base.box(
            "Town pack floor " + r["id"],
            (ox + w / 2, oy + d / 2, 0.008),
            (w, d, 0.014),
            materials["tile" if r["id"] == "bathroom" else "floor"],
        )
    env = releases[pack["lighting"]["environment_asset_id"]]
    env_file = tier_file(env, "hdr")
    env_path = pack_file(root, env_file)
    scene = bpy.context.scene
    env_nodes = scene.world.node_tree.nodes
    env_texture = next(n for n in env_nodes if n.type == "TEX_ENVIRONMENT")
    env_texture.image = bpy.data.images.load(str(env_path), check_existing=True)
    env_nodes.get("Background").inputs["Strength"].default_value = pack["lighting"][
        "environment_intensity"
    ]
    rooms = {}
    palette = {}
    for part in plan["rooms"]:
        rid = part["id"]
        imported = []
        for model in part["models"]:
            digest = model["sha256"]
            path, size, asset_id = models[digest]
            bound = import_model(
                model, read_verified(path, digest, size), rid + "/" + model["group"]
            )
            bound["asset_id"] = asset_id
            imported.append(bound)
        for shape in part["shapes"]:
            decor_shape(shape, rid + "/" + shape["group"], base, palette)
        rooms[rid] = {
            "rendered_native_models": imported,
            "saved_bindings": part["bindings"],
            "saved_dressing": part["dressing"],
            "procedural_dressing_slots": sorted({s["group"] for s in part["shapes"]}),
        }
    summary = {
        "project": board["project"],
        "revision": board["revision"],
        "home_id": board["home_id"],
        "snapshot_sha256": plan["snapshot_sha256"],
        "manifest_sha256": plan["manifest_sha256"],
        "style_pack": ref,
        "rooms": rooms,
        "surfaces": surfaces,
        "environment": {
            "id": env["asset_id"],
            "source": env["source_url"],
            "license": env["license"],
            "sha256": env_file["sha256"],
        },
        "rendering_scope": "High-tier Town furniture placements and saved dressing. Floor, tile, wall, ceiling and trim use release textures. Cycles uses physical window emitters, a shared sun and its own exposure. Drapes retain the exact saved proxy and use thin translucent cloth for window light. Browser AO, postprocessing and interactive cutaways are outside the offline render.",
    }
    (out / "saved-style-receipt.json").write_text(json.dumps(summary, indent=2))
    return summary
