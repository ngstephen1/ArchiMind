# Native-scale Charles product rendering — 08C-R2

The optional experimental viewer now has **Charles product (08C-R2)**, a fixed room with two Stone & Beam Charles armchairs (Sod, ABO B075X2X4XS) and one labeled desk placeholder. It is independent of A/B candidates, generation, Plotly and AI. The legacy architectural room and single Sheen Chair remain available. Load the experiment explicitly; there are no runtime external asset downloads.

## Authority and qualification

`assets/catalog.py` and `furniture_catalog.json` retain the original published product facts and metadata qualification. `planning_envelopes.py/json` retain the exact owner-approved B envelope, including their historical false render flags. **Neither historical snapshot is rewritten.** The separate `assets/product_render_release.json`, pinned by digest in `assets/render_assets.py`, approves only this original source hash for native-scale rendering after automated and browser review. `charles_visual_review.json` is also digest-bound. This is an explicit render release layered on immutable product/planning evidence, not a second product catalog or a caller-supplied approval.

`requalify_product(local_path)` freshly inspects the bytes and compares the entire inspection digest against the reviewed receipt. It then revalidates the current catalog/version/variant and all eight exact-rational planning-envelope corners. The old inspector continues to report failure against the published physical box. Its other gates must all pass; B supersedes only that containment target. The technical result still says visual pending because technical inspection alone cannot grant visual approval. `product_release()` represents the separate completed visual release.

Only `abo-b075x2x4xs-amazon-com`, render version `1.0.0`, is approved. The bookcase remains metadata-only. Sheen remains an illustrative CC0 fixture, with its old fitting semantics.

## Coordinates and scale

Published W/D/H: **0.9906 × 0.9906 × 0.9652 m**. B planning W/D/H: **0.996104896068573 × 1.0019413232803345 × 0.9760930538177491 m**. These are distinct facts; the planning box is not a correction to product specifications.

The original GLB uses +Y up, +Z front. Source geometry/materials and authored transforms remain unchanged. Add normalization translation `(0, 0, 0.00010657310485839844)` and then canonical placement `(x+W/2, 0, -(y+D/2))` in Three coordinates. All added scales are exactly `(1,1,1)`; no yaw, deformation or product fitting is permitted. Native +Z front points canonical south. The floor is Y=0.

`nativeProductInstance()` lives in `product_assets.js` and has no fitting dependency. Only the legacy Sheen dispatch calls `fittedInstance()`/`fitBounds()`. Decoded actual vertex bounds and materials/images are checked before cloning. Rendering allows 1e-6 m numeric world-comparison tolerance to account for floating-point translation; the exact object-local B proof and spatial validators are unchanged.

## Trusted V3 scene contract

`render/product_scene.py` exports `ProductScene`, `product_scene_payload()` and `render_product_scene()`. Complete per-furniture bindings contain only `furniture_id`, `asset_id`, `render_version` and `envelope_sha256`. A placeholder uses null for the last three. The Python and frontend validators require current release/envelope IDs, exact B dimensions, chair category, zero rotation and complete unique coverage. They reuse the existing V2 structural/size/label checks. They do not generate layouts or run spatial validation.

V1 single Sheen and V2 architectural scenes retain their existing contracts. V3 cannot smuggle an illustrative asset, URL, path, transform or approval flag. The fixed local path is provided only by the reviewed release. `scripts/build_product_registry.py` derives the deeply frozen frontend projection from authoritative metadata; `--check` and a Python regression reject stale generated output. Run it before rebuilding when an explicitly reviewed release changes. Runtime payloads cannot update that projection.

The source GLB is checked by SHA-256 both offline and in the browser before GLTFLoader receives bytes. The browser streams with a hard cap, rejects external references/extensions/deformation and checks decoded finite vertices, indices, exact bounds, triangles, material count, image sizes and texture memory. Known corrupt/missing or incompatible assets become labeled canonical placeholders. HTTPS is needed for WebCrypto on a hosted demo; localhost works for development. Insecure non-local hosting is not qualified.

## Resource ownership and budgets

Unchanged limits: **15 MiB/asset**, **50 MiB unique encoded/scene**, **100,000 triangles/asset**, **300,000 instantiated furniture triangles/scene**, **2048 px/image edge**, **128 MiB unique estimated decoded RGBA with mipmaps/scene**. Structural/procedural triangles are reported separately from the product budget. Shared resources are counted once for bytes/textures and once per instance for triangles.

Charles: 4,252,440 encoded bytes, 42,706 triangles, three embedded 2048² images and 67,108,860 estimated texture bytes. Two copies share one geometry/material/texture source; product triangles total 85,412. Eight copies exceed the triangle budget: the browser displays eight placeholders and performs zero GLB loads. An individual load failure affects only that asset's instances. A scene budget failure suppresses all detailed products.

The existing reference-counted asset pool owns shared GPU resources. Clones own their transforms only. Last release cancels pending retrieval and disposes a late successful decode once; failures do not trigger automatic retries. Explicit remount can retry. Scene cleanup is idempotent, removes observers/controls/frame callbacks and releases the WebGL context. Browser inspection confirms replacement/recovery; unit tests confirm exact geometry/material/texture disposal. Sustained memory/leak/frame-rate profiling remains future work.

## Provenance, rights and packaging

Original bytes: **62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645**, unchanged, only one packaged GLB copy. The [official model README](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) grants CC BY 4.0 use with credit to Amazon.com and the named dataset builders. The package includes `ABO_ATTRIBUTION.txt`, `ABO_SOURCE_README.md` (whitespace normalized, source/packaged hashes retained), original `ABO_LICENSE_CC_BY_4.0.txt` and `CHARLES_PROVENANCE.json`. The existing Sheen license texts remain unchanged; the separately retained ABO license has different upstream bytes. Attribution/license/modification information also appears in the UI. No additional restrictions or endorsement claim is made.

Source/wheel tests compare exact asset/resource bytes, check one Charles copy, preserve Sheen assets, install the wheel offline without dependencies, then load/verify the asset and V3 payload from outside the repository with external operations blocked. The existing package-data glob already covers the new files; no dependency or packaging pattern expansion is required. The source manifest adds this guide and paired technical report.

## Visual evidence and limits

Private qualification used the same renderer with a build-time pending registry in an external localhost harness. No public approved binding or binary was committed before review. Desktop **1440 × 1000** and resized narrow Chromium **390 × 844** showed source upholstery textures, rolled arms, cushions and turned legs consistent with Charles's source description. Front/back, floor contact, canonical bounds, openings, orbit/zoom/reset/cutaway, missing/corrupt fallback, recovery and cleanup were inspected. Screenshots and hashes are in the review receipt; image files stay outside Git.

The live Streamlit route also loaded the product at unit scale, preserved legacy Sheen choices, and fit a 347 px component at narrow width without page overflow. One existing Plotly canvas-readback advisory was observed, with zero final console errors. An early rapid cold rerun hit an unrelated pandas partial-import error; clean restart with sequential completed reruns did not reproduce it. No production import workaround was introduced. The report retains this observation rather than treating health HTTP 200 as a complete UI test.

This is source-consistent rendering, not manufacturer metrology, calibrated color/material verification, independent human review, physical-phone testing or architectural certification. No reference product photo was acquired. Native source scale and mesh bounds are trusted only for the inspected hash. The demonstration is not advertised as a validated generated layout. Do not confuse better meshes with better architectural reasoning.

## Local checks

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python scripts/build_product_registry.py --check
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
python scripts/check_health.py
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run build
git diff --exit-code -- src/archimind/_viewer_assets
python -m pytest -q tests/test_asset_catalog_packaging.py
python -m streamlit run app.py
```

08D may be separately scoped to explicit compatible B-sized specifications and safe placeholders. Existing A/B furniture must never be resized for a mesh. Bed, desk and wardrobe still lack qualified assets; the bookcase is deferred because of 4096 px textures. No selected-layout integration, embeddings, new AI or further acquisition was implemented here.

## Task 08D follow-up

Selected A/B layouts now have an optional Three.js view using this same renderer.
Normal bedroom items remain placeholders without explicit product evidence. The
standalone Charles fixture now retains its planning sidecars and caches a real
spatial report per session; its geometry and native asset remain unchanged.
Legacy contracts and demonstrations stay supported. Current state/lifecycle
behavior and verification are in the [selected-layout guide](SELECTED_REALISTIC_LAYOUTS.md).
