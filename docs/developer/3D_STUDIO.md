# 3D Studio: furnished procedural concepts

This branch introduces a separate room-concept workspace at `/?workspace=studio`.
It supports rectangular bedrooms, living rooms and home offices. It creates
furniture geometry from bounded data and passes its whole-object reservations
through the existing deterministic placement and accessibility checks. It does
not change the qualified ABO catalog or dataset reference modules.

## Try it

From the existing environment:

```sh
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Open `http://127.0.0.1:8503/?workspace=studio`, or follow **Open 3D Studio** from
the main app. Select a room type, edit its measurements/openings, then click
**Load example furnishing plan → review → Build 3D room**. The examples use fixed
furniture and colors; they do not interpret the design brief and make no API calls.
Choose a **Style** before building to dress the room with a [style pack](STYLE_PACKS.md);
the 2D plan uses the pack's plan colours.

For custom AI concepts, the local launcher reads only `OPENAI_API_KEY` and
`ARCHIMIND_OPENAI_MODEL` from the ignored `.env` file; existing process values win:

```sh
.venv/bin/python scripts/run_studio.py --port 8503
```

The normal app never loads `.env` automatically. The launcher enables
`ARCHIMIND_ENABLE_OPENAI_STUDIO=1` server-side, binds to localhost and prints no
credentials. Live buttons also require the visible consent checkbox. No key is
included in component data, snapshots or the frontend bundle. Existing chat and
other agent flags remain separate.

Example brief for a custom furnishing plan:

> A calm contemporary bedroom with a double bed, a compact writing desk and
> low storage. Use pale wood, soft blue-green fabric and rounded-looking details.

Room measurements and openings come from the form. The model proposes furniture
types, quantities, dimensions and a palette, then creates detailed recipes after
the user reviews the plan. Spatial placement wishes in prose are not enforced;
review the generated alternatives and their stated validation scope.

## Workflow and state

1. Enter a room from 1–20 m wide/deep and a ceiling from 1–6 m in the UI. Supply at
   least one measured entrance and up to 16 total openings. North/south offsets
   start at west; east/west offsets start at south. Windows may be omitted explicitly.
   The initial measurements are editable examples, not inferred measurements.
2. **Propose AI furnishing plan** makes one server-side request. It may return up
   to eight unique concepts and twelve instances, with at most three instances
   of a unique concept. Each proposed object must fit the room individually.
3. Review the names, quantities, concept dimensions and source label. Editing
   room/type/brief invalidates pending preparation. Seed changes do not.
4. **Build 3D room** runs the existing seeded generator with two candidates and
   500 attempts. Independent zero-tolerance acceptance checks must agree with
   each candidate's stored report. No candidates means an honest exhausted,
   infeasible or unsupported outcome; recipes are not requested for an empty result.
5. A successful placement stage requests one recipe per unique concept, at most
   two concurrently. A common 180-second request deadline, 30-second per-request
   timeout and zero retries bound this stage. A proposed plan plus one build uses
   at most nine model requests. Each recipe response has an 8,192-token cap.
6. Frozen room, plan, recipes and result JSON form a content-hashed snapshot.
   A/B, orbit/reset, cutaway and view changes make no model requests or generation
   calls. Pending edits preserve displayed results. Failed actions preserve the
   previous build; an ordinary returned empty outcome replaces it honestly.

The selected candidate supplies both the Plotly floor plan and procedural 3D
scene. The existing generation-owner camera lifecycle also applies to Studio.
Downloading a snapshot exports JSON; no file import or executable-code loading
path is included. A brief is not persisted outside the Streamlit session by the
application; the authorized provider requests contain that brief and measured room.

## What is reused from Spoken World

Upstream: [ryannli/spoken-world at
2c398a545eca4364ff6029940cecc4719c21b862](https://github.com/ryannli/spoken-world/tree/2c398a545eca4364ff6029940cecc4719c21b862),
Apache-2.0, copyright 2026 ryannli. `src/spoken_world/parts.js` isolates its pure
`makeBuilder` part recorder as an ES module. The original full license and an
ArchiMind modification notice are in `frontend/realistic_viewer/vendor/spoken-world/`;
the build copies both into the installed viewer resources and adds attribution.

ArchiMind's adapter calls only box, cylinder/cone and sphere recording methods.
It builds geometry with the repository's existing Three.js 0.187.0 dependency.
It does not import upstream voice, speech, provider host, fonts/media, world
runtime, persistence, worker execution or model-written JavaScript. No dependency
or model download was added.

## Include a Blender designer chair

After loading a plan, use **Add a designer chair** to choose a released version.
The review shows both packaged previews and its measured width, depth and height.
**Build 3D room** adds one chair to the submitted furniture list before placement
and accessibility validation. Selecting a version or changing layouts makes zero
model requests. Rebuilding with a different version creates a new snapshot.

Chair-enabled scenes use schema version 5. The snapshot pins the concept ID,
version and GLB SHA-256. The renderer loads the matching packaged mesh at native
scale into its validated reservation. An unavailable mesh leaves a labeled
placeholder at the same coordinates. The selector appears when an approved
release is available. Plans built without a chair continue to use version 4.

## Recipe and renderer contract

The model returns strict JSON data, checked again by Python and the frontend:

| Bound | Accepted behavior |
| --- | --- |
| Shape types | Axis-aligned box, vertical cylinder, vertical cone, sphere/ellipsoid |
| Geometry | 1–64 parts per unique object; normalized local X/Y/Z size and center |
| Size | Each normalized size component 0.001–1; every part inside the whole W/H/D reservation |
| Floor | At least one part contacts local Y=0; all objects are floor-standing |
| Materials | Hex colors and roughness 0–1; at most eight unique finishes per recipe |
| Scene | At most eight recipes and twelve instances; combined payload at most 256 KiB |
| Resolution | Fixed 16-segment cylinders and 16×8 spheres; merged geometry by finish |
| Native bounds | Scale 1; actual Three.js bounds must fit the canonical reservation |

Canonical data is X east, Y north, Z up, in meters. The adapter maps to Three.js
X east, Y up, negative Z north. Outer yaw stays zero. The renderer uses a 2 μm
Float32 measurement allowance for its bounds comparison; this does not alter
the spatial validator or placement tolerances. Invalid recipes fail closed;
unavailable concept geometry is explicitly labeled as a placeholder.

The new **schema version 4** is concept-only: all product asset bindings are null
and only application-created `studio:<concept>:<instance>` IDs may reference
recipes. Versions 1–3 retain their existing behavior and product release checks.
Recipes cannot carry URLs, external assets, textures, scripts, animations,
arbitrary groups or rotations. Generated concepts are not purchasable products,
physically engineered objects, CAD/BIM, construction or code-compliance evidence.

Strict output schemas follow the existing SDK's Responses/Pydantic interface.
Coordinates use homogeneous arrays with exact length three, avoiding positional
`prefixItems`. Schema conformance is followed by bounds, grounding and resource
checks; it does not establish visual quality or suitability. See
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Source map and verification

| Files | Responsibility |
| --- | --- |
| `src/archimind/studio/{contracts,provider,fixtures,workflow}.py` | Immutable concepts, opt-in provider calls, fixed examples, placement and snapshots |
| `src/archimind/ui/studio.py`, `scripts/run_studio.py` | Separate workspace and local launcher |
| `frontend/realistic_viewer/src/concept_assets.js` | Strict recipe/binding validation, primitive geometry and measured bounds |
| `frontend/realistic_viewer/src/spoken_world/parts.js` | Pinned upstream recorder extraction |
| `tests/test_studio*.py`, `frontend/realistic_viewer/tests/concept.test.js` | Mocked provider, state, geometry, failure and camera contracts |
| `tests/test_asset_catalog_packaging.py` | Offline source/wheel build and isolated installed Studio smoke |

The machine-readable [receipt](../data/3D_STUDIO_10A.json) records commands,
results, current acceptance limits and append-only historical hash migrations.
Tests use mocked providers and blocked network/process operations. Fixed examples
cover all three room types in both Python and actual Three.js geometry tests.
A separately authorized four-request backend smoke produced one furnishing plan,
three recipes (20, 21 and 26 parts) and two passing seed-42 alternatives in nine
search attempts. Both live scene payloads passed actual Three.js geometry checks
at scale 1, with 804 furniture triangles per room and no model/texture downloads.
These dimensions are conservative reservations; actual concept meshes may
underfill them. No additional requests remain authorized by that smoke budget.

Native Chrome inspection of the ordinary app verified the offline bedroom plan,
two validated alternatives and a visible three-concept room. Browser automation's
DOM host was unavailable; native inspection stopped when the user switched to
other work. Exact desktop/narrow viewport acceptance, a complete ordinary-browser
live workflow and visual quality of model-created furniture remain pending.
Mocked, live backend, Node geometry and browser evidence remain separate.
Existing product and dataset evidence is preserved.
