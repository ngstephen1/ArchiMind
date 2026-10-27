# Realistic 3D Viewer — Experimental (Task 06D)

This is an isolated, reversible one-asset experiment. Plotly renderers, synchronized
A/B selection, canonical models, spatial validation and layout generation remain
unchanged. C01 stays disabled; no live model or image-generation API is used.

## Architecture and local setup

Node 20.13.1 / npm 10.5.2 were available locally. The frontend pins Three.js
**0.186.1** and esbuild **0.28.2**, with a committed lockfile. Plain ES modules
avoid an extra UI framework. `npm run build` writes the bundled ES module and
static files under `src/archimind/_viewer_assets/`; these are intentionally
versioned and included in the Python wheel. No Node process, npm installation,
CDN, decoder service, or internet connection is required at viewing time.

The dedicated Python wrapper is `archimind.render.realistic_viewer`; the dedicated
sample factory is `archimind.examples.sample_chair.create_sample_chair`. The
Streamlit Components V2 manifest is `src/archimind/pyproject.toml`. Only the public
viewer directory is served. Frontend code is trusted application code with page
privileges; style isolation is not a security sandbox. No user-provided code,
HTML, asset URL, or file path is accepted. JSON labels use `textContent`.

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm --prefix frontend/realistic_viewer ci --ignore-scripts
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer run build
python -m http.server 8512 --bind 127.0.0.1 --directory src/archimind/_viewer_assets
```

Open http://127.0.0.1:8512 for the standalone viewer. Use HTTP, not `file://`.
After setup all resources load locally. The GLB source/credit links are information
only and are never fetched automatically. Node modules, screenshots and wheel
outputs are ignored. Python and Node tests do not fetch network data.

## One asset, provenance and redistribution

Exactly one furniture GLB is bundled: **Sheen Chair**, Eric Chadwick, © 2020
Wayfair, LLC, from [Khronos glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair).
The model is CC0-1.0. Its upstream metadata/license notice is separately CC-BY-4.0;
both full license texts and attribution are preserved. See the bundled
[provenance](../../src/archimind/_viewer_assets/furniture/README.md) and machine-readable
`PROVENANCE.json` for the pinned download URL, revision, date and checksum.

Original file: **4,125,648 bytes**, unchanged. GLB 2.0 contains embedded geometry
and seven image resources. Four meshes contain **39,936 triangles**. The original
Mango Velvet PBR materials, wood grain, metal and label are retained. Material
variants contained in the same file are not exposed by this experiment.

## Coordinates, origin, orientation and proportional fit

ArchiMind `(x,y,z)` meters map to Three.js `(x,z,-y)`: east +X, north -Z, up +Y.
This is a right-handed rotation, not a reflection. The GLB is Y-up, front +Z;
zero yaw faces canonical south (-Y). The sample has one chair at X/Y `(1.1,0.8)`,
with declared W/D/H `0.85 × 0.70 × 0.85 m`, in a `3.2 × 2.8 × 2.7 m` room.

The actual loaded node transforms are applied before measuring `Box3` bounds.
Uniform scale is the minimum of width/source-X, height/source-Y, depth/source-Z.
The model is grounded at Y=0 and centered in the unchanged canonical footprint.
There is no independent axis scaling. The result is approximately W/D/H
**0.850 × 0.586 × 0.706 m**, leaving intentional unused depth and height. A teal
floor outline shows the full canonical footprint, independently toggleable.

The canonical volume and detailed mesh are distinct. Neither rendering nor the
fit proves mesh collision, accessibility, door clearance, or building-code validity.
This does not run or modify the spatial engine. The wrapper accepts exactly one
rotation-0 chair, finite bounded dimensions/positions, and one fixed local asset.

## Renderer and lifecycle

GLTFLoader preserves supplied materials/textures, including sheen and texture
transforms. Hemisphere and directional lights, a procedurally generated
RoomEnvironment/PMREM environment, sRGB output, ACES filmic tone mapping,
antialiasing, a neutral floor and filtered shadow map provide readable materials.
There is no downloaded HDRI or second model. OrbitControls supports orbit, zoom,
pan and reset. ResizeObserver adapts the canvas; pixel ratio is capped at two.
IntersectionObserver pauses drawing offscreen. Cleanup cancels frames/requests,
observers and controls and disposes geometries, materials, textures and renderer.

Loading and error states are explicit. Missing/corrupt assets never trigger a
replacement model or remote fallback. Python validates file size, SHA-256,
GLB structure and embedded resource ranges. This is a lightweight fixed-asset
integrity check, not a universal glTF validator or an upload security boundary.

## Primary references

- [Streamlit package-based Components V2](https://docs.streamlit.io/develop/concepts/custom-components/components-v2/package-based)
- [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)
- [OrbitControls](https://threejs.org/docs/pages/OrbitControls.html)
- [WebGLRenderer](https://threejs.org/docs/pages/WebGLRenderer.html)
