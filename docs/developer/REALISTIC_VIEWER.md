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

## Streamlit demonstration and actual verification

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m streamlit run app.py
```

Enable **Load experimental chair viewer** beneath the experimental heading. It is
unchecked initially, so normal Plotly usage does not allocate another WebGL
renderer. The component registers file-backed JS/CSS from its dedicated package
asset directory and mounts trusted JSON data; there is no script interpolation.
The existing bedroom fixture, Plotly renderers and synchronization, schemas,
spatial validators, layout generator, and C01 source remain unchanged.

Observed in actual Chromium browser inspection:

- Desktop 1440 px and mobile-width 390 px: textured chair visible and unclipped,
  footprint/labels readable, no page overflow. Physical touch devices, Safari and
  Firefox have not been tested.
- Four meshes, 39,936 triangles, four active materials, seven embedded images,
  ten active texture objects. The normal-map/wood/fabric surface detail, curved
  upholstery, tuft buttons and shaped legs improve on Plotly's schematic cuboids.
- Orbit, wheel zoom, right-drag pan, footprint toggle and reset operate locally.
  Floor edges can enter the view while orbiting; this is a finite floor, not a full
  room interior. Filtered shadows are visible; this is raster PBR, not path tracing.
- Loading state was inspected by delaying the GLB request. A deliberate GLB 404
  produced the explicit error without a replacement model. Recovery was verified.
- Rendering succeeded with non-local requests blocked; no external origin was
  requested. Normal console: no errors, with the existing Plotly Canvas2D advisory.
  The intentional fault test generated the expected 404, removed afterward.
- Initial standalone local load/setup/first-render observation: **3.06 s**.
  Subsequent Streamlit mounts: approximately **0.31–0.33 s** with warm browser/GPU
  caches. These measurements begin at component mounting and exclude the JS module
  download/parse before mounting; they are observations, not FPS or cross-device
  benchmarks. Camera interaction appeared responsive; no FPS benchmark was run.

Screenshots (local, ignored): `output/task06d/streamlit-desktop.png`,
`streamlit-mobile.png`, `standalone-desktop.png`, `loading-state.png`, and
`missing-asset-state.png`.

Final checks: **570 passed in 20.09s**, all 541 prior cases retained plus 29 new
Python cases; **9 frontend tests passed**; frontend syntax/build and npm audit
passed (zero vulnerabilities); pip check, Ruff lint/format, and real Streamlit
health check passed. A wheel was built, inspected and installed in an isolated
temporary target to verify packaged assets. Node/npm are build-time requirements
only. CI rebuilds the frontend and checks for bundle drift.

## Suitability and limits

This is a suitable basis for a small curated room viewer: local glTF loading, PBR,
coordinate mapping, proportional fitting, packaging and controls work together.
Expanding it requires per-asset provenance and orientation/bounds metadata,
resource budgets, progressive loading, selection synchronization, representative
browser/device tests and a deliberate policy for detailed-mesh spatial checks.
It does not yet prove multi-asset performance or collision/clearance correctness.

Remain within the one-chair experiment: rotation 0, no uploads, arbitrary URLs,
material-variant UI, asset catalog, full room structure, saving or agent actions.
WebGL 2 is required and GPU memory depends on decoded textures, not just GLB file
size. Three.js/Streamlit upgrades need a fresh build and browser verification.

Recommended next: **Task 06E — Realistic 3D Room and Furniture Asset Catalog**.
It is not implemented automatically by this task.
