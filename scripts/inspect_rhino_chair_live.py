"""Read the actual MCP-selected Rhino 8 document and compare it with a released chair."""

import hashlib
import json
from pathlib import Path


def inspect_open_chair(doc, version):
    """Use the __rhino_doc__ injected by McNeel's run_python tool."""
    import Rhino

    if Rhino.RhinoApp.ExeVersion != 8:
        raise ValueError("A Rhino 8 operator instance is required")
    if (
        version not in ("1.0.0", "1.1.0")
        or doc.ModelUnitSystem != Rhino.UnitSystem.Millimeters
    ):
        raise ValueError("Choose a released version and a millimetre document")
    root = Path(__file__).resolve().parents[1]
    folder = root / "design" / "oak-sage-writing-chair" / version
    receipt = json.loads((folder / "cad/cad-evidence.json").read_text())
    release = json.loads((folder / "release.json").read_text())["authoring"]
    for file, digest in (
        (folder / "cad/chair.3dm", receipt["cad_sha256"]),
        (
            root
            / "src/archimind/_viewer_assets"
            / ("designer-" + release["sha256"]["chair.glb"] + ".glb"),
            receipt["released_glb_sha256"],
        ),
    ):
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError("Local release digest mismatch for " + file.name)
    selection = Rhino.DocObjects.ObjectEnumeratorSettings()
    selection.ActiveObjects = True
    selection.HiddenObjects = True
    selection.LockedObjects = True
    meshes, skins, bends = {}, set(), []
    for obj in doc.Objects.GetObjectList(selection):
        attr, geometry = obj.Attributes, obj.Geometry
        if attr.GetUserString("archimind:variant") != release["variant"]:
            raise ValueError("Use a fresh, empty Rhino document for this chair")
        name = attr.Name
        if not geometry.IsValid:
            raise ValueError("Invalid document geometry: " + name)
        if isinstance(geometry, Rhino.Geometry.Mesh) and geometry.IsClosed:
            if name in meshes:
                raise ValueError("Duplicate mesh: " + name)
            meshes[name] = geometry.GetBoundingBox(True)
        elif name.endswith(" skin") and isinstance(
            geometry, (Rhino.Geometry.Surface, Rhino.Geometry.Brep)
        ):
            if name in skins:
                raise ValueError("Duplicate NURBS skin: " + name)
            skins.add(name)
        elif (
            name == "Backrest crown clearance arc"
            and isinstance(geometry, Rhino.Geometry.NurbsCurve)
            and geometry.Degree == 2
        ):
            bends.append(
                geometry.PointAt(geometry.Domain.Mid).Y - geometry.PointAtStart.Y
            )
        else:
            raise ValueError("Unexpected document object: " + name)
    parts = set(release["inputs"]["parts"])
    if (
        set(meshes) != parts
        or skins != {part + " skin" for part in parts}
        or len(bends) != 1
    ):
        raise ValueError(
            "Rhino scene did not contain the released CAD parts and controls"
        )
    floor = min(b.Min.Z for b in meshes.values())
    sizes = {
        axis: max(getattr(b.Max, axis) for b in meshes.values())
        - min(getattr(b.Min, axis) for b in meshes.values())
        for axis in "XYZ"
    }
    mm = {
        "width": sizes["X"],
        "depth": sizes["Y"],
        "height": sizes["Z"],
        "seat_height": meshes["Sage seat cushion"].Max.Z - floor,
    }
    if abs(bends[0] - release["inputs"]["back_bend_mm"]) > 0.001 or any(
        abs(value - receipt["glb_mm"][key]) > 1 for key, value in mm.items()
    ):
        raise ValueError("Geometry in the live Rhino document differs from the release")
    return {
        "rhino_version": str(Rhino.RhinoApp.Version),
        "document_serial": int(doc.RuntimeSerialNumber),
        "concept_id": release["concept_id"],
        "version": version,
        "mesh_parts": len(meshes),
        "nurbs_skins": len(skins),
        "back_bend_mm": bends[0],
        "document_mm": mm,
        "glb_mm": receipt["glb_mm"],
        "cad_sha256": receipt["cad_sha256"],
        "released_glb_sha256": receipt["released_glb_sha256"],
    }


def save_curve_study(doc, version, new_directory):
    """In a fresh operator document, add a 10 mm deeper guide and save a study copy."""
    import Rhino
    from System import Guid

    inspection = inspect_open_chair(doc, version)
    folder = Path(new_directory).expanduser().resolve()
    folder.mkdir(exist_ok=False)
    path = folder / "chair-backrest-study.3dm"
    criteria = Rhino.DocObjects.ObjectEnumeratorSettings()
    criteria.HiddenObjects = True
    source = next(
        obj
        for obj in doc.Objects.GetObjectList(criteria)
        if obj.Attributes.Name == "Backrest crown clearance arc"
    )
    curve = source.Geometry.DuplicateCurve().ToNurbsCurve()
    # For a three-CV quadratic, the middle control point has weight 1/2 at midspan.
    middle = curve.Points[1].Location
    middle.Y += 20.0
    if not curve.Points.SetPoint(1, middle) or not curve.IsValid:
        raise ValueError("Could not edit the backrest control point")
    name = "Study only - backrest arc 10 mm deeper"
    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.Name = name
    attrs.LayerIndex = doc.Layers.CurrentLayerIndex
    attrs.SetUserString("archimind:role", "unreleased guide study")
    identifier = doc.Objects.AddCurve(curve, attrs)
    if identifier == Guid.Empty:
        raise ValueError("Could not add the study curve to the operator document")
    try:
        if not doc.Write3dmFile(str(path), Rhino.FileIO.FileWriteOptions()):
            raise ValueError("Rhino could not write the new study file")
        saved = Rhino.FileIO.File3dm.Read(str(path))
        if saved is None:
            raise ValueError("Rhino could not reopen the saved study file")
        try:
            edited = next(
                o.Geometry for o in saved.Objects if o.Attributes.Name == name
            )
            bend = edited.PointAt(edited.Domain.Mid).Y - edited.PointAtStart.Y
            if abs(bend - inspection["back_bend_mm"] - 10.0) > 0.001:
                raise ValueError("Saved backrest edit did not survive reopening")
        finally:
            saved.Dispose()
    finally:
        doc.Objects.Delete(identifier, True)
        doc.Views.Redraw()
    return {
        "output": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "starting_bend_mm": inspection["back_bend_mm"],
        "study_bend_mm": bend,
        "scope": "Editable guide study; the chair skin and released mesh retain their original geometry.",
    }
