# Edit and inspect the chair in Rhino

Two Rhino 8 archives accompany the Blender releases. Each holds ten closed mesh parts on four finish layers. Two hidden construction layers contain ten editable degree-one NURBS side skins and a degree-two backrest arc. The skins preserve the original loft control grids so a CAD editor can move an entire section or individual control points. The quadratic arc exposes the backrest bend using three control points. Turn on **Design curves** or **NURBS side skins** in the Layers panel to edit them. The closed mesh, open control skin and guide curve are separate editable objects. Changing a guide requires updating the corresponding geometry before releasing a revision.

| Version | Backrest bend | Editable source | Measurement receipt |
| --- | ---: | --- | --- |
| Gentle 1.0.0 | 42 mm | [chair.3dm](../../design/oak-sage-writing-chair/1.0.0/cad/chair.3dm) | [cad-evidence.json](../../design/oak-sage-writing-chair/1.0.0/cad/cad-evidence.json) |
| Deep 1.1.0 | 71 mm | [chair.3dm](../../design/oak-sage-writing-chair/1.1.0/cad/chair.3dm) | [cad-evidence.json](../../design/oak-sage-writing-chair/1.1.0/cad/cad-evidence.json) |

Both files measure **480 × 520 × 830 mm**, with the cushion top at **455 mm**. The authoring CLI reopens each saved file, measures its ten named meshes and compares each part's six extremes as well as the four overall dimensions to the released GLB’s binary position data. It converts glTF metres and Y-up coordinates into Rhino millimetres and Z-up coordinates before comparison. The largest overall dimensional difference for these files is below 0.000020 mm against a 1 mm tolerance. These values describe the digital models. A desktop Rhino operator still needs to check the live connection and viewport.

## Rebuild or verify on a CAD workstation

Use an isolated Python 3.11 environment with McNeel's `rhino3dm==8.35.0`. The application, viewer and ordinary test suite run independently of this operator environment. The script takes geometry from the same numeric recipe identified in the immutable Blender release receipt. It uses the approved GLB solely for independent comparison. [McNeel File3dm API](https://mcneel.github.io/rhino3dm/python/api/File3dm.html) · [CAD authoring source](../../scripts/author_rhino_chair.py)

```sh
# From the ArchiMind checkout, with Python 3.11 available
cad_work="$(mktemp -d)"
python3.11 -m venv "$cad_work/operator"
"$cad_work/operator/bin/python" -m pip install --only-binary=:all: rhino3dm==8.35.0
"$cad_work/operator/bin/python" scripts/author_rhino_chair.py --variant gentle --verify design/oak-sage-writing-chair/1.0.0/cad/chair.3dm
"$cad_work/operator/bin/python" scripts/author_rhino_chair.py --variant deep --output "$cad_work/deep"
```

A successful run prints the file and GLB SHA-256 hashes, archive version, units, part counts, back curve and measured deltas. A newly written archive can have a different binary hash due to object IDs or archive metadata. Each CAD receipt identifies its own exact artifact. The operator refuses to overwrite an output directory.

## Connect Codex to a licensed Rhino 8 session

1. Open a licensed copy of desktop Rhino 8. Use `PackageManager` to install McNeel’s **Rhino-MCP-Platform** and run `MCPConnect`. The official registry published version 0.4.0 for this workflow. Record the installed plugin and Rhino versions along with any test artifacts. [Official package](https://yak.rhino3d.com/packages/Rhino-MCP-Platform) · [McNeel getting started](https://mcneel.github.io/RhinoAI/docs/getting-started/)
2. On the same workstation, register the router in Codex with the **exact executable and arguments printed by MCPConnect**. On a setup that prints `rhino-mcp-router --default-version 8`, the registration is `codex mcp add rhino -- rhino-mcp-router --default-version 8`. Restart Codex. Use your existing Codex account. The local McNeel router requires access to the licensed application. [Official Codex setup](https://mcneel.github.io/RhinoAI/docs/getting-started/codex/)
3. Open a fresh, empty, millimetre-model Rhino document. In Codex, choose that session and inspect the tools it advertises. Ask the official `open_doc` tool to import one archived `chair.3dm` using its absolute path and `clearFirst=false`. Use `list_objects` with `includeHidden=true` to see ten mesh parts, their side skins and the backrest arc. Using a fresh document preserves your existing work.
4. Ask `run_python` to execute the following operator check. Substitute the absolute checkout path and choose the same version you opened. The helper reads the document selected by the MCP router. It checks mesh validity and identity, hidden construction geometry, bend, release hashes and the four dimensions. Save the JSON tool reply with the test artifacts, then use `get_viewport_image` to capture the chair in Rhino. Repeat in a second fresh document for the other version. [Pinned official run_python implementation](https://github.com/mcneel/RhinoAI/blob/28c20cbad300f4966d0fe08a4b59b1a44353ac5f/rhino/plugin/Tools/RunPythonTool.cs) · [Live inspector](../../scripts/inspect_rhino_chair_live.py)

   ```python
   import json
   import runpy

   inspector = runpy.run_path("/absolute/checkout/scripts/inspect_rhino_chair_live.py")
   result = inspector["inspect_open_chair"](__rhino_doc__, "1.0.0")
   print(json.dumps(result, indent=2))
   ```

5. To exercise an actual CAD edit, ask `run_python` to execute the following on the same fresh gentle document. Supply a **new** directory on the operator workstation. The helper duplicates the quadratic backrest guide, moves its middle control point by 20 mm to deepen the arc by 10 mm, saves a new editable study and reopens it with RhinoCommon. It checks the saved bend is 52 mm, then removes the temporary guide from the open document. Open the saved study in a separate Rhino window to edit it further. This study changes the guide only. A change to the finished chair requires refitting the skins and a new release review.

   ```python
   import json
   import runpy

   operator = runpy.run_path("/absolute/checkout/scripts/inspect_rhino_chair_live.py")
   study = operator["save_curve_study"](
       __rhino_doc__, "1.0.0", "/absolute/operator/new-backrest-study"
   )
   print(json.dumps(study, indent=2))
   ```

A missing Rhino license, unavailable router, empty object list, differing measurements or missing viewport capture leaves the live check pending. An offline file check proves the archive and dimensions. Record desktop results against the actual tested workstation, router version, CAD hash and GLB hash.

McNeel’s platform provides the operator route above. The community RhinoMCP project uses its own Rhino plugin, Python server and `mcpstart` command. The community route would need its own live qualification before substituting it for McNeel’s tools. Keep modeling and editable CAD files in the operator workflow. The published viewer continues to consume the approved GLB. [McNeel platform](https://mcneel.github.io/RhinoAI/) · [Community implementation](https://github.com/jingcheng-chen/rhinomcp)
