# Experimental architectural room — Task 06E1

This extends the isolated Three.js experiment. The stable Plotly renderers,
canonical architectural models, spatial validators, deterministic generator,
bedroom fixture, generated alternatives and C01 integration are unchanged.
No additional furniture asset, dataset, framework or runtime CDN is introduced.

## Scene contract

`archimind.render.realistic_scene.ArchitecturalScene` contains the original
`RoomDesign`, not another definition of room/door/window/furniture models.
The version-2 JSON envelope adds complete per-furniture asset bindings and explicit
unavailable asset IDs. The immutable typed catalog contains only `sheen-chair`.
Other furniture categories use clearly labeled procedural placeholders. Callers
can explicitly choose a placeholder with `None`; paths and URLs are not accepted.

Dimensions and positions remain canonical meters. Doors start at elevation zero;
windows use `sill_height_m`. The mapping remains `(x,y,z) -> (x,z,-y)` with Three.js
Y-up and north -Z. Only rotation zero is supported. Limits are 24 furniture objects,
128 openings, room dimensions 0.1–20 m, furniture dimensions 0.05–10 m and positions
within ±20 m. These bound rendering work; they are not spatial validation rules.

The independent sample is `create_sample_realistic_room()`: 5 × 4 × 2.7 m, a south
entry and north window, two textured chairs of different declared sizes, and a
blue desk placeholder. It is not an automatically generated or validated layout.
`room-design.json` is a checked snapshot; tests require it to match the factory.

## Architecture and genuine openings

`room_geometry.js` partitions walls at opening endpoints. In each strip it
triangulates only the remaining vertical intervals, merging overlapping openings.
No wall triangle bridges a door/window rectangle. Window glass and outlines are
separate objects; there is no door leaf, hinge, swing or modeled wall thickness.
Numerical endpoint roundoff is clamped only at the existing wall/ceiling endpoint.

The floor uses a deterministic procedural plank texture, not a downloaded asset.
All four walls exist; front walls are translucent and can be hidden. The scene
uses PBR lighting, procedural environment reflections and filtered shadow maps.
Camera fitting projects the full room/canonical object volume into the perspective
frustum with padding; a reset fits the current viewport. Orbit, zoom, pan, front
wall visibility and footprint controls stay entirely in the browser.

## Shared assets and lifecycle

`asset_pool.js` reference-counts one promise per trusted asset ID. Two chair
instances clone object hierarchies and share geometry/material/texture resources;
only their IDs and root transforms differ. Scaling is uniform and the model is
grounded/centered within each unchanged declared footprint. Unused space remains
visible via the footprint outline. A short disposal grace period permits rapid
remount reuse. No automatic retry occurs for a failed request within a scene.

Shared resources are disposed only after their final owner releases them. Scene
cleanup separately disposes owned structural/placeholder geometry, canvas textures,
shadow targets, environment target, controls, observers, animation frames and the
renderer. GLB instances do not dispose their shared source resources individually.
Missing/corrupt known assets produce explicit unavailable placeholders and a
`partial` result; the architecture still renders. Empty rooms require no GLB.

## Standalone and compatibility

In Streamlit, enable **Load experimental realistic viewer**. **Architectural room**
is the default; **Single chair (06D)** retains the original studio. The opt-in
session-state key is preserved. The fixed room does not change when Layout A/B
changes, and selecting it neither generates nor spatially revalidates layouts.
All source coordinates and dimensions appear below the canvas.

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer run build
python -m http.server 8514 --bind 127.0.0.1 --directory src/archimind/_viewer_assets
```

Open http://127.0.0.1:8514/room.html. The old `index.html`, version-1 payload,
one-chair sample and Python wrapper remain supported. Both modes use the same
local bundled JS infrastructure. The new room mode is independent of A/B layouts.

## Verification record

Python: **593 passed in 22.02s** (570 prior + 23 scene/component cases).
Frontend: **27 passed** (9 prior + 18 room/resource cases), including intersections
between actual wall triangles and opening rectangles, independent uniform fits,
resource ownership and late-decode cleanup. Syntax/build, Ruff lint/format,
dependency check and Streamlit health all passed; health returned HTTP 200 ok.
Wheel contents and an isolated target installation also verified the room pages,
scene snapshot, bundled JS/CSS and exactly one checksum-verified furniture GLB.

Actual Chromium desktop (1440 × 1000) and narrow viewport (390 × 844) inspections
verified full room, door/window, textured chairs, desk, orbit, zoom, right-drag pan,
reset, front-wall visibility and original single-chair compatibility. The 347 px
mobile component had no horizontal overflow. A/B reruns preserved scene metrics
and triggered zero network requests. Empty room: ready, zero GLB requests.
Injected missing GLB: one request, partial result, three labeled placeholders,
structure preserved; normal rendering recovered after fault removal. Blocking
non-local requests did not prevent rendering, and no external host was attempted.
Normal console had zero errors and one existing Plotly readback advisory.

Ignored screenshots in `output/task06e1/`:
`streamlit-full-room-desktop.png`, `streamlit-full-room-mobile.png`,
`streamlit-room-orbit.png`, `streamlit-room-cutaway.png`,
`streamlit-chair-detail.png`, `streamlit-room-missing-asset.png`,
`standalone-empty-room.png`.

Two chairs share four source geometries after one GLB load. There are 79,884
furniture triangles (including the 12-triangle placeholder), plus 18 wall triangles.
Inspected local setup times ranged approximately 0.38–2.19 s; these include loading
and initialization and are observations, not an FPS, GPU-memory or device benchmark.

## Limits

Only the existing Sheen Chair is textured; the desk is explicitly a placeholder.
There is no full asset library, wall thickness, ceiling slab, door swing,
architectural certification, detailed-mesh validation, saving or agent behavior.
Translucent surfaces can have sorting artifacts. WebGL 2 is required; full-device
and multi-engine compatibility/performance require separate testing.
