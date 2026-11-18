"""Author and independently compare an editable Rhino 8 chair with the released GLB."""

import argparse
import hashlib
import json
import math
import runpy
import struct
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/author_designer_chair.py"
VERSIONS = {"gentle": "1.0.0", "deep": "1.1.0"}
SEAT = "Sage seat cushion"
SKINS = "NURBS side skins"
GUIDES = "Design curves"
SPINE = "Backrest crown clearance arc"
TOLERANCE_MM = 1.0


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def released(variant):
    version = VERSIONS[variant]
    folder = ROOT / "design/oak-sage-writing-chair" / version
    receipt = json.loads((folder / "release.json").read_bytes())["authoring"]
    glb = (
        ROOT
        / "src/archimind/_viewer_assets"
        / ("designer-" + receipt["sha256"]["chair.glb"] + ".glb")
    )
    if (
        receipt["variant"] != variant
        or receipt["version"] != version
        or digest(glb) != receipt["sha256"]["chair.glb"]
        or digest(SOURCE) != receipt["inputs"]["author_script_sha256"]
    ):
        raise ValueError("Released geometry or source does not match the chair receipt")
    return receipt, glb


def bounds(points):
    points = list(points)
    return tuple((min(c), max(c)) for c in zip(*points, strict=True))


def measurements(boxes):
    axes = list(zip(*boxes.values(), strict=True))
    return {
        key: max(b for a, b in axis) - min(a for a, b in axis)
        for key, axis in zip(("width", "depth", "height"), axes, strict=True)
    } | {"seat_height": boxes[SEAT][2][1] - min(a for a, b in axes[2])}


def glb_measurements(path):
    """Read the pinned static GLB's actual POSITION bytes, in millimetres/Z up."""
    data = path.read_bytes()
    magic, version, size, json_len, tag = struct.unpack_from("<4sIIII", data)
    if (magic, version, size, tag) != (b"glTF", 2, len(data), 0x4E4F534A):
        raise ValueError("Expected the released embedded glTF 2.0 file")
    document = json.loads(data[20 : 20 + json_len])
    binary_len, binary_tag = struct.unpack_from("<II", data, 20 + json_len)
    binary = memoryview(data)[28 + json_len :]
    if binary_tag != 0x004E4942 or len(binary) != binary_len:
        raise ValueError("Expected an embedded geometry buffer")
    boxes = {}
    scene = document["scenes"][document["scene"]]
    for idx in scene["nodes"]:
        node = document["nodes"][idx]
        if set(node) != {"name", "mesh"}:
            raise ValueError(
                "Expected released root mesh instances with identity transforms"
            )
        positions = []
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            acc = document["accessors"][primitive["attributes"]["POSITION"]]
            view = document["bufferViews"][acc["bufferView"]]
            if (
                acc["componentType"] != 5126
                or acc["type"] != "VEC3"
                or "sparse" in acc
                or view["buffer"] != 0
            ):
                raise ValueError("Expected unpacked float positions")
            offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
            for i in range(acc["count"]):
                x, y, z = struct.unpack_from(
                    "<fff", binary, offset + i * view.get("byteStride", 12)
                )
                positions.append((1000 * x, -1000 * z, 1000 * y))
        part = node["name"].removesuffix(".001")
        if part in boxes:
            raise ValueError("Duplicate GLB part")
        boxes[part] = bounds(positions)
    return boxes


def write_cad(path, recipe, meta):
    import rhino3dm as r

    doc = r.File3dm()
    doc.Settings.ModelUnitSystem = r.UnitSystem.Millimeters
    doc.Settings.ModelAbsoluteTolerance = 0.01
    doc.ApplicationName = "ArchiMind CAD authoring"
    for key in ("concept_id", "variant", "version"):
        doc.Strings["archimind:" + key] = meta[key]

    def layer(name, color, visible=True):
        obj = r.Layer()
        obj.Name, obj.Color, obj.Visible = name, color, visible
        return doc.Layers.Add(obj)

    layers = {}
    for finish, (rgb, _) in recipe["FINISHES"].items():
        layers[finish] = layer(finish, (*bytes.fromhex(rgb), 255))
    layers[SKINS] = layer(SKINS, (72, 122, 155, 255), False)
    layers[GUIDES] = layer(GUIDES, (196, 95, 40, 255), False)

    def attr(name, layer_name):
        a = r.ObjectAttributes()
        a.Name, a.LayerIndex = name, layers[layer_name]
        a.SetUserString("archimind:variant", meta["variant"])
        return a

    for name, finish, vertices, faces in recipe["chair_meshes"](meta["variant"]):
        mm = [(1000 * x, 1000 * y, 1000 * z) for x, y, z in vertices]
        mesh = r.Mesh()
        for p in mm:
            mesh.Vertices.Add(*p)
        for face in faces:
            if len(face) == 4:
                mesh.Faces.AddFace(*face)
            else:
                for a, b in zip(face[1:-1], face[2:], strict=True):
                    mesh.Faces.AddFace(face[0], a, b)
        mesh.Normals.ComputeNormals()
        if not mesh.IsValid or not mesh.IsClosed:
            raise ValueError("Invalid closed part: " + name)
        doc.Objects.AddMesh(mesh, attr(name, finish))

        # Preserve the original loft grid as an editable control-point side skin.
        # Duplicate its seam column. The separate closed meshes include end caps.
        n = len(faces[0])
        rings = [mm[start : start + n] for start in range(0, len(mm), n)]
        skin = r.NurbsSurface.Create(3, False, 2, 2, n + 1, len(rings))
        skin.KnotsU.CreateUniformKnots(1)
        skin.KnotsV.CreateUniformKnots(1)
        for j, ring in enumerate(rings):
            for i, p in enumerate([*ring, ring[0]]):
                skin.Points[i, j] = r.Point4d(*p, 1)
        if not skin.IsValid:
            raise ValueError("Invalid NURBS skin: " + name)
        doc.Objects.AddSurface(skin, attr(name + " skin", SKINS))

    # A true quadratic Bézier on the back surface, above its recline transition.
    # At t=.5 Bernstein weights are 1/4, 1/2, 1/4; the middle CV is beyond the arc.
    half = 1000 * recipe["BACK_HALF_WIDTH"]
    rear = meta["inputs"]["depth_mm"] / 2
    bend = meta["inputs"]["back_bend_mm"]
    pts = [(-half, rear - bend, 805), (0, rear + bend, 805), (half, rear - bend, 805)]
    curve = r.NurbsCurve.Create(False, 2, [r.Point3d(*pt) for pt in pts])
    doc.Objects.AddCurve(curve, attr(SPINE, GUIDES))
    if not doc.Write(str(path), 8):
        raise ValueError("Could not write the Rhino 8 archive")


def verify_cad(path, variant):
    import rhino3dm as r

    meta, glb = released(variant)
    doc = r.File3dm.Read(str(path))
    if (
        not doc
        or doc.ArchiveVersion != 80
        or doc.Settings.ModelUnitSystem != r.UnitSystem.Millimeters
    ):
        raise ValueError("Expected a readable Rhino 8 millimetre document")
    if any(
        doc.Strings["archimind:" + key] != meta[key]
        for key in ("variant", "version", "concept_id")
    ):
        raise ValueError("CAD identity does not match release")
    boxes, skins = {}, set()
    bend = None
    for obj in doc.Objects:
        geometry = obj.Geometry
        name = obj.Attributes.Name
        layer = doc.Layers.FindIndex(obj.Attributes.LayerIndex)
        if (
            not geometry.IsValid
            or obj.Attributes.GetUserString("archimind:variant") != variant
        ):
            raise ValueError("Invalid geometry or variant: " + name)
        if isinstance(geometry, r.Mesh) and layer.Name in meta["inputs"]["finishes"]:
            if name in boxes or not geometry.IsClosed:
                raise ValueError("Duplicate or open part: " + name)
            boxes[name] = bounds((p.X, p.Y, p.Z) for p in geometry.Vertices)
        elif (
            layer.Name == SKINS
            and any(name == part + " skin" for part in meta["inputs"]["parts"])
            and isinstance(geometry, r.NurbsSurface)
        ):
            surface = geometry
            if surface.Degree(0) != 1 or surface.Degree(1) != 1 or name in skins:
                raise ValueError("Invalid editable side skin: " + name)
            skins.add(name)
        elif (
            name == SPINE
            and layer.Name == GUIDES
            and isinstance(geometry, r.NurbsCurve)
            and geometry.Degree == 2
            and bend is None
        ):
            mid = geometry.PointAt((geometry.Domain.T0 + geometry.Domain.T1) / 2)
            bend = mid.Y - geometry.PointAtStart.Y
        else:
            raise ValueError("Unexpected CAD object: " + name)
    expected_parts = set(meta["inputs"]["parts"])
    reference = glb_measurements(glb)
    if (
        set(boxes) != expected_parts
        or set(reference) != expected_parts
        or skins != {name + " skin" for name in expected_parts}
        or bend is None
        or not math.isclose(bend, meta["inputs"]["back_bend_mm"], abs_tol=0.001)
    ):
        raise ValueError("CAD parts, control skins or backrest bend do not match")
    cad_mm, glb_mm = measurements(boxes), measurements(reference)
    deltas = {key: abs(cad_mm[key] - glb_mm[key]) for key in cad_mm}
    max_part_error = max(
        abs(a - b)
        for name in boxes
        for left, right in zip(boxes[name], reference[name], strict=True)
        for a, b in zip(left, right, strict=True)
    )
    if max(*deltas.values(), max_part_error) > TOLERANCE_MM:
        raise ValueError("CAD differs from released GLB by more than 1 mm")
    return {
        "schema_version": 1,
        "concept_id": meta["concept_id"],
        "version": meta["version"],
        "variant": variant,
        "rhino3dm_version": r.__version__,
        "archive_version": doc.ArchiveVersion,
        "unit": "millimeter",
        "cad_sha256": digest(path),
        "released_glb_sha256": digest(glb),
        "author_script_sha256": digest(SOURCE),
        "cad_author_script_sha256": digest(Path(__file__)),
        "closed_mesh_parts": len(boxes),
        "editable_nurbs_side_skins": len(skins),
        "quadratic_backrest_bend_mm": bend,
        "cad_mm": cad_mm,
        "glb_mm": glb_mm,
        "absolute_deltas_mm": deltas,
        "max_per_part_bound_error_mm": max_part_error,
        "tolerance_mm": TOLERANCE_MM,
        "verification": "offline file write/reopen and binary GLB comparison",
        "licensed_rhino_mcp_acceptance": "pending",
    }


def create(variant, output):
    meta, _ = released(variant)
    output.mkdir(exist_ok=False)
    with TemporaryDirectory(dir=output) as temp:
        file = Path(temp) / "chair.3dm"
        write_cad(file, runpy.run_path(str(SOURCE)), meta)
        receipt = verify_cad(file, variant)
        file.rename(output / file.name)
        (output / "cad-evidence.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=tuple(VERSIONS), required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path, help="A new candidate directory")
    action.add_argument(
        "--verify", type=Path, help="An existing chair.3dm to reopen and measure"
    )
    args = parser.parse_args()
    result = (
        verify_cad(args.verify, args.variant)
        if args.verify
        else create(args.variant, args.output)
    )
    print(json.dumps(result, indent=2))
