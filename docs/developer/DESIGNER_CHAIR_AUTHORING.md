# Author the original writing chair in Blender

The chair has a laminated oak seat shell, four tapered legs, two back uprights, a bent backrest and a sage cushion with a separate welt. Both variants occupy **480 × 520 × 830 mm** (width × depth × height), with the top of the cushion at **455 mm**. The backrest measures 448 mm across. Its center sits 42 mm behind its tips on `gentle` (1.0.0) and 71 mm on `deep` (1.1.0), measured on the rear face above the recline transition. The uprights meet the back at the appropriate depth for each curve. The source defines the geometry in metres, with the front toward Blender −Y. Blender exports the chair with glTF +Y up, +Z front and native scale 1.

The recipe uses original mesh profiles, colors and material roughness values. Each run produces an **editable candidate**. Artifact review and explicit admission control which candidate the application can display. Either variant can be authored independently. [Authoring source](../../scripts/author_designer_chair.py)

## Connect a local Codex session to Blender

Use Blender 5.1+ in a dedicated operator environment. The add-on runs Python with the permissions of its Blender process. Use loopback for its socket, a fresh Blender document, and an authoring account without application credentials. Pin both the add-on and the MCP server to the same upstream release. The two components communicate locally. Standard Codex sign-in is sufficient for an interactive Codex session. Blender, the deterministic chair recipe and the operator test use no paid model or asset API. [Blender Lab overview](https://www.blender.org/lab/mcp-server/) · [Upstream v1.0.3](https://projects.blender.org/lab/blender_mcp/releases/tag/v1.0.3)

1. Run these setup commands from a terminal on the Blender workstation. The new Python environment is dedicated to the operator. The upstream project pins its release independently of its Python dependencies.

   ```sh
   author_root="$(mktemp -d "$HOME/archimind-blender.XXXXXX")"
   git clone --depth 1 --branch v1.0.3 https://projects.blender.org/lab/blender_mcp.git "$author_root/blender_mcp"
   test "$(git -C "$author_root/blender_mcp" rev-parse HEAD)" = 2cea8d566dde07fbac28a61d698909d69724e853
   curl --fail --location --output "$author_root/mcp-1.0.3.zip" https://projects.blender.org/lab/blender_mcp/releases/download/v1.0.3/mcp-1.0.3.zip
   (cd "$author_root" && echo 'a7a9da816192502e5a0a202a396444e266b47d8fc4f74ad4698048bd43040707  mcp-1.0.3.zip' | shasum -a 256 -c -)
   python3 -m venv "$author_root/operator"
   "$author_root/operator/bin/python" -m pip install "$author_root/blender_mcp/mcp"
   codex mcp add archimind-blender -- "$author_root/operator/bin/blender-mcp"
   ```

2. In Blender, open **Preferences → Get Extensions → menu → Install from Disk**. Select the verified ZIP, enable the extension, then start its listener from its preferences. Leave the add-on's default loopback endpoint in place. Open a new Codex session in the ArchiMind checkout. [Upstream setup](https://projects.blender.org/lab/blender_mcp/wiki/Setup.md)
3. Ask Codex to call `get_objects_summary` through `archimind-blender` and report a named object visible in the open Blender scene. This checks the complete Codex → stdio server → Blender connection.
4. Ask Codex to run the prompt below. Supply the absolute checkout path and a new directory under the operator workspace for each variant. The directory's parent must already exist. The recipe leaves any existing scene intact and activates the newly created chair scene. The CPU renders may take a few minutes.

   > Using the local archimind-blender MCP, build the original gentle writing chair from this checkout. Through execute_blender_code, use Python runpy.run_path with the absolute path to scripts/author_designer_chair.py. Call the returned author_chair function with my new output directory and variant "gentle". Return its receipt in the result variable. Inspect the scene with get_objects_summary and report how many separate chair parts there are. Repeat the same recipe into a second new directory with variant "deep". Report the two versions, backrest bends, seat heights, GLB hashes and paths to both preview pairs. Stop after export.

   The Python evaluated inside Blender follows this form. Replace both absolute paths with the ones chosen above.

   ```python
   import runpy

   recipe = runpy.run_path("/absolute/checkout/scripts/author_designer_chair.py")
   result = recipe["author_chair"]("/absolute/operator/gentle", "gentle")
   ```

## Inspect the resulting files

| Output | Operator check |
| --- | --- |
| `chair.blend` | Reopen the file in Blender. Inspect the ten individually editable mesh parts in the chair collection. The separate photography collection holds the ground, lights and cameras. |
| `chair.glb` | Import into a fresh scene. Check width, depth and height against the values above. Check the model rests on the floor and that only the chair geometry was exported. |
| `front.png` and `three-quarter.png` | View both 600 × 640 images at full size. Inspect the silhouette, leg contact, side-to-back joints, cushion and material separation. Compare the changed backrest wrap between variants. |
| `authoring.json` | Verify the four file hashes, recipe hash, Blender version, geometry inputs, finish parameters and attribution. The receipt accompanies the original bytes it describes. |

For deterministic batch authoring without a chat client, launch from the checkout in a shell where `blender` resolves to Blender 5.1+. The same function creates the candidate. Use a different new output directory on each run.

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python scripts/author_designer_chair.py -- \
  --output "$author_root/batch-gentle" --variant gentle
```

To repeat the real MCP acceptance exercise, set `BLENDER_BIN` to the Blender executable and run the following from the checkout. The driver invokes the pinned upstream background MCP integration, checks returned file hashes, reopens both editable scenes in a second Blender process and records the inspected scene summaries. The code-level regression checks run separately under the application development environment. [Operator exercise](../../scripts/test_blender_operator.py) · [CI workflow](../../.github/workflows/blender-chair.yml)

```sh
export BLENDER_BIN=/Applications/Blender.app/Contents/MacOS/Blender
export BLENDER_MCP="$author_root/operator/bin/blender-mcp"
GLOBAL_TIMEOUT_SCALE=10 "$author_root/operator/bin/python" scripts/test_blender_operator.py \
  "$author_root/blender_mcp" "$author_root/operator-test"
.venv/bin/python -m pytest -q tests/test_designer_chair_authoring.py
```

Both variants passed the Linux Blender 5.1.2 operator exercise at commit `c223397`. The run used the real upstream MCP server and add-on in background mode. The interactive Codex setup above can be checked separately on the operator workstation. [CI run with candidate artifacts](https://github.com/ngstephen1/ArchiMind/actions/runs/44219907523)

If a render or connection ends before the receipt arrives, inspect the operator console and the original output directory first. Use a fresh directory for a new run. Keep both preview views and source together when submitting a candidate for review. Stop the loopback listener from the add-on preferences when the session ends.

The app opens the approved GLBs through **3D Studio → Add a designer chair** or the **Town editor → Bedroom chair** picker. Both released versions also have millimetre-scale Rhino 8 archives with editable part skins and backrest curves. [Rhino CAD and Codex operator instructions](RHINO_CHAIR.md)
