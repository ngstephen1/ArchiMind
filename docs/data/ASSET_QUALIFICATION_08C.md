# Task 08C — Charles asset qualification: blocked

**Decision: no real product mesh approved.** October 28, 2026. Baseline:
`3159f653e4bd8c6a3672ab55a97ba243b124f486`. The Charles GLB passes the published-size
agreement test but fails the separately required strict canonical-envelope test.
The authorized failure branch is complete; product rendering and 08D remain blocked.
The paired [machine-readable receipt](ASSET_QUALIFICATION_08C.json) records exact
bounds, source receipts, hashes, budgets, preservation and browser observations.

## 1. Identity, acquisition and rights

The one inspected product is `abo-b075x2x4xs-amazon-com`, Charles armchair, Sod,
ASIN/model `B075X2X4XS`, marketplace `amazon.com`, manufacturer model `LTD26020C`.
Fresh primary metadata matched the frozen 08A/08B product/model/variant join:

- [ABO listings part 7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz):
  line 242, published **item** width/length/height 39/39/38 inches; exact record
  SHA-256 `f98a699bf5a8540b8e1fad18233bb94b940d21a617b7cb670768733c36bcb99a`.
  The bounded prefix was retrieved, not the full listing archive.
- [Official model index](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/metadata/3dmodels.csv.gz):
  same model ID, `S/B075X2X4XS.glb`, one mesh/material, three 2048 px images,
  23,412 vertices and 42,706 faces. Its compressed SHA-256 is
  `90d061c3e3efa555a55bfc8ed7fc55cdb322086397443de1b33e91f7924d7d92`.
- [Official models README](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md),
  [release page](https://amazon-berkeley-objects.s3.amazonaws.com/index.html#download)
  and [license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt)
  confirm the published models release uses **CC BY 4.0**. Public browser delivery
  is permitted under that copyright license with credit, license link, preserved
  notices and change indications. Commercial permission is also present; this
  project still targets a noncommercial demo. No new agreement was accepted.

Attribution: Amazon.com; Matthieu Guillaumin, Thomas Dideriksen, Kenan Deng,
Himanshu Arora, Arnab Dhua, Xi (Brian) Zhang, Tomas Yago-Vicente, Jasmine Collins,
Shubham Goel and Jitendra Malik. No endorsement is implied. Individual mesh creator
is not separately identified. This verifies published terms, not independent
chain-of-title, trademark, privacy or warranty clearance. Actual visible logos and
material appearance were not reviewed because the geometry gate failed. The known
source revision remains null; HTTP dates and the ArchiMind qualification revision
are separate evidence.

Exactly one [individual GLB](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/original/S/B075X2X4XS.glb)
was downloaded into external quarantine, using certificate/hostname-verified HTTPS,
a fixed URL, redirects disabled, a matching HEAD/If-Match condition and a **15 MiB
body cap**. HEAD and GET both reported 4,252,440 bytes. No retry, alternative model,
bookcase, archive or separate image/texture download occurred. Small primary
metadata bodies totaled **605,117 bytes**; the individual GLB contained its own
embedded images. The model GET receipt is dated `2026-10-28T20:58:59.046196+00:00`.

| Received bytes | Value |
| --- | --- |
| Size | 4,252,440 bytes |
| Computed SHA-256 | `62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645` |
| HEAD/GET ETag | `409963d4d47700bc94b3f6faa8c0f04e` — **not** a SHA-256 |
| Last-Modified | Thu, 17 Jun 2021 08:05:47 GMT |
| Local quarantine | `/tmp/archimind-08c-20261028.T4uIlT/` |
| Committed GLB / approved binding | None |

The SHA-256 identifies received bytes; there is no independently published SHA-256
attestation. The CLI's expected hash checks consistency with this acquisition
receipt. Quarantine is temporary local evidence, not a durable hosted asset or a
runtime cache. Retrieval metadata and the complete inspection remain in Git as
JSON; raw model bytes remain outside the repository.

## 2. Decoded geometry and the two independent gates

The new offline inspector reads the actual float32 positions and unsigned indices,
applies authored static scene transforms, and computes vertex bounds. It does not
trust accessor min/max or the dataset's extent columns. A separate Node buffer
reader using Three.js `Box3` reproduced **identical bounds** from all 23,412
referenced positions. All positions are referenced; the scene has one identity
root transform, one static mesh and one triangle primitive. No extension,
animation, skin or morph is present.

The source documents meters, +Y up and +Z natural front. This inspection confirms
numeric bounds and floor position, **not natural-front semantics visually**.

| Space / order | Minimum | Maximum |
| --- | --- | --- |
| Native glTF XYZ (m) | (-0.4980524480342865, 0, -0.5010772347450256) | (0.4980524480342865, 0.976093053817749, 0.5008640885353088) |
| Floor/center-normalized glTF XYZ (m) | (-0.4980524480342865, 0, -0.5009706616401672) | (0.4980524480342865, 0.976093053817749, 0.5009706616401672) |
| Canonical XYZ at furniture (0, 0) | (-0.002752448034286481, -0.005670661640167218, 0) | (0.9933524480342866, 0.9962706616401673, 0.976093053817749) |
| Canonical envelope XYZ (m) | (0, 0, 0) | (0.9906, 0.9906, 0.9652) |

The only proposed added normalization is translation
`(0, 0, 0.00010657310485839844)` in glTF coordinates: center X/Z, floor Y=0.
Its scale is **1**, orientation identity. At canonical furniture lower-left
`(x, y)`, the Three.js placement translation would be
`(x + width/2, 0, -(y + depth/2))`; canonical `(X,Y,Z)` maps to Three `(X,Z,-Y)`.
These transforms are recorded as evidence only and were never bound to a product
renderer. No corrective scaling, geometry editing, dimension change or yaw was
performed.

| Axis | Published item envelope (m) | Actual mesh extent (m) | Excess (mm) | Agreement tolerance (m) | Agreement |
| --- | ---: | ---: | ---: | ---: | --- |
| Width | 0.9906 | 0.996104896068573 | 5.504896069 | 0.019812 | Pass |
| Depth | 0.9906 | 1.0019413232803345 | 11.341323280 | 0.019812 | Pass |
| Height | 0.9652 | 0.976093053817749 | 10.893053818 | 0.019304 | Pass |

**Strict containment fails:** after fixed anchoring the model extends 2.752448 mm
past each X side, 5.670662 mm past each Y side and 10.893054 mm above the canonical
height. All exceed the **0.001 mm (1e-6 m)** numerical tolerance. Passing the
`max(0.01 m, 2%)` agreement check cannot override this failure. Published sizes
remain published claims rather than independent physical measurements. There is
no evidence authorizing replacement dimensions.

## 3. Containers, materials and resource costs

All buffers/images are embedded. PNG chunks/CRCs and JPEG frame headers/end markers
were checked without decoding pixels. The original material references one normal
PNG, one metallic/roughness JPEG and one base-color JPEG, each **2048 × 2048**.
Presence of a PBR material does not certify physical material properties or visual
quality. No original material or image was displayed in a browser.

| Gate | Measured | Limit | Result |
| --- | ---: | ---: | --- |
| Encoded individual GLB | 4,252,440 B | 15 MiB | Pass |
| Asset triangles | 42,706 | 100,000 | Pass |
| Largest image edge | 2048 px | 2048 px | Pass |
| Unique RGBA + complete mip estimates | 67,108,860 B | 128 MiB | Pass |
| Two-instance unique encoded data | 4,252,440 B | 50 MiB | Pass, offline calculation |
| Two-instance rendered triangles | 85,412 | 300,000 | Pass, offline calculation |
| Two-instance shared texture estimate | 67,108,860 B | 128 MiB | Pass, offline calculation |
| Strict canonical envelope | See section 2 | 1e-6 m | **Fail** |

Textures are counted by image/sampler identity within an asset and shared once
across repeated instances of the same asset. Triangle costs count every instance.
These are deterministic accounting estimates, not measured decoded GPU memory or
phone performance. A passing scene-resource assessment cannot approve geometry.
The optional Espresso bookcase remains deferred and unacquired because its index
reports 4096 px images. No texture conversion or replacement acquisition was made.

## 4. Delivered inspector, tests and boundaries

- `src/archimind/assets/inspection.py`: fixed-cap local GLB reader, strict JSON,
  static transforms, actual bounds, embedded image headers, resource estimates,
  immutable JSON-serializable inspection and separate aggregate-budget reports.
- `scripts/inspect_furniture_assets.py`: thin local-file/catalog-ID CLI; no URL
  argument, downloader, file rewriting or runtime application integration.
- `tests/test_asset_inspection.py`: synthetic GLBs only. External networking,
  process spawning and real provider constructors are blocked in these tests.
- `tests/test_asset_catalog_packaging.py`: extended source/wheel preservation and
  outside-repository installed-inspector loading checks.

This supported subset accepts one static scene using core GLB 2, triangle meshes,
embedded buffers and PNG/JPEG. It rejects external/data URIs, extensions (including
compression), animation, skins, morphs, sparse accessors, unused scene geometry,
invalid indices/references, nonfinite values and unsafe/unbounded files. Work is
also limited to 4,096 items per inspected top-level array, 4 million decoded
components and 1 million transformed vertex visits. Symlinks, nonregular files and
oversized inputs are rejected. Authored TRS/matrices are distinguished from added
normalization. The inspector is not a complete Khronos validator, image decoder,
OS sandbox, source-identity oracle or final render approval authority.

Tests cover malformed structures, duplicate/nonfinite JSON, buffer/accessor/index
errors, transform hierarchy, anchoring, actual-vs-declared bounds, a 2%-passing but
containment-failing mesh, all resource thresholds, shared counting, missing/hash
failures, sanitized CLI exit paths, deterministic reports and input preservation.
Existing legacy schema-1/schema-2, illustrative Sheen fitting, pool ownership,
cancellation/disposal and fallback tests remain intact. No schema-3 product scene,
qualified renderer projection, product loading or aggregate renderer fallback is
claimed: those belong to the unentered conditional branch.

The catalog remains **schema 1 / version 1.0.0**, both record versions 1.0.0.
All 08A source evidence and the immutable 08B snapshot are byte-identical. Its
historical `not_evaluated` fields stay null; this separate receipt records the
new rejection. Sheen remains an illustrative fixture. App, A/B selection, Plotly,
Three.js, canonical models, validators, generation, scoring and dependencies are
unchanged. There were no live AI/Codex calls, embeddings or new agents.

## 5. Actual browser inspection — placeholders only

A temporary external Streamlit fixture invokes the **same existing**
`render_realistic_scene` with two Charles-sized canonical Furniture objects, the
sample desk and **explicit `None` bindings for every furniture ID**. This avoids
automatic Sheen-chair substitution. The original 5 × 4 × 2.7 m room, south entry
and north window are preserved. The fixture clearly labels the mesh as rejected
and the objects as procedural placeholders; it is not a new app choice or 08D.

Desktop **1440 × 1000** and resized narrow **390 × 844** inspections confirmed:

- Three labeled procedural boxes, **0 textured instances, 0 asset IDs and 0 GLB
  loads/network requests**. Setup observation: **237 ms** for this one local mount;
  resizing reused that mount, so it is not a second cold-load measurement.
- Exact canonical dimensions/positions in viewer metrics and readable object list;
  placeholder float32 envelope residuals are below 1e-6 m. Furniture has floor
  contact. Nine wall panels/18 structural triangles retain the door/window gaps.
- Orbit and wheel zoom changed the camera; Reset restored the identical initial
  camera at both widths. Front-wall and footprint toggles operated at both widths.
- **0 console warnings, 0 errors**, no horizontal document overflow. Full room
  framing is visible. Small overlapping in-scene sprites remain an existing narrow
  view limitation; the full list below the canvas is readable.

Screenshots were saved and visually inspected outside Git:

- `/Users/macbook/Hack/.playwright-mcp/archimind-08c-20261028/desktop-1440x1000.png`
- `/Users/macbook/Hack/.playwright-mcp/archimind-08c-20261028/narrow-top-390x844.png`
- `/Users/macbook/Hack/.playwright-mcp/archimind-08c-20261028/narrow-390x844.png`

These are desktop Chromium viewports, not physical-phone testing. No real product
material, image decoding, natural-front appearance or detailed-mesh floor contact
is verified. Missing/corrupt Charles runtime behavior is unevaluated because no
Charles runtime binding exists; unchanged legacy fallback coverage passes.

## 6. Verification and reproduction

Final local results:

| Check | Actual result |
| --- | --- |
| Full Python suite | **1,380 passed in 80.12s**; 0 failures/skips, all 1,305 previous tests retained |
| New offline inspection tests | **75 passed** in the full suite; final focused rerun **75 passed in 1.20s** |
| Source/wheel regression | Passed; offline builds, preserved catalog/legacy assets, no product GLB, isolated installed-inspector load |
| Frontend | **27 passed, 0 failed, 0 skipped**; syntax and production build passed |
| Bundle equality | `git diff --exit-code -- src/archimind/_viewer_assets` passed |
| Ruff | Lint and format passed; 115 Python files already formatted |
| Dependencies | `No broken requirements found.` |
| Streamlit | Actual headless application health HTTP **200 ok** |
| Charles CLI | Exit **2**, rejected; no approved binding |
| Bounds cross-check | Independent Node/Three bounds exactly match Python |

The existing full baseline remains intact. Packaging builds use existing tools
offline, preserve bundled assets, install with `--no-deps --no-index` into a target
and verify loading outside the repository. No downloaded model is packaged.

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
python scripts/check_health.py
(cd frontend/realistic_viewer && npm run check && npm test && npm run build)
git diff --exit-code -- src/archimind/_viewer_assets
python -m pytest -q tests/test_asset_catalog_packaging.py
```

To inspect an already authorized local copy (this command downloads nothing):

```bash
python scripts/inspect_furniture_assets.py \
  --asset-id abo-b075x2x4xs-amazon-com \
  --file /path/to/quarantined/B075X2X4XS.glb \
  --expected-sha256 62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645
```

The actual Charles command returned **exit 2**, structured `rejected`,
`render_qualified: false`. Exit 0 means automated checks passed **with visual review
still pending**; exit 1 means unreadable/malformed/unsupported input or invalid
catalog reference. No exit value alone approves a model for public rendering.

## 7. Stop decision and next evidence

Stop after the inspection/qualification checkpoint. There is no trusted-integration
checkpoint or approved asset commit to perform. Keep strict containment and the
published canonical dimensions. Do not resize Charles, enlarge its furniture
footprint, update catalog approval or fit it with Sheen's illustrative function.

A future separately scoped investigation could obtain authoritative evidence
resolving the model/product dimension discrepancy, or qualify another appropriate
model under 08A rules. Any revised product claim must have independent evidence,
not be chosen to enclose this mesh. The bookcase needs a separately approved,
licensed texture-preparation policy before acquisition. No 08D implementation,
substitute purchase/download, conversion tooling or policy relaxation is authorized
by this report. Git commit and CI links are provided in the delivery response;
the receipt cannot contain its own future commit identity.
