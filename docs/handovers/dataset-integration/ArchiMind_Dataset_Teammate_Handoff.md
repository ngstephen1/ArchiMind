# 01 | Mission and current state

## ArchiMind dataset integration

**Teammate implementation handbook | November 5, 2026 | Public-demo target**

Build a small, auditable reference-data capability using **SSR-3DFRONT, MIDI-3D/3D-FRONT and 3D-FUTURE**. Users should retrieve relevant bedroom examples, read grounded explanations and inspect permitted reference geometry. This is reference retrieval, not model training or automatic furniture selection. The app must still work when every dataset is absent.

## Verified starting point

| State | What exists at this handoff |
| --- | --- |
| COMMITTED | Repository: https://github.com/ngstephen1/ArchiMind. Baseline: `4dc5c026cafdfec23cc0924b6bcca62ece0f29f7`. Backend conversation checkpoint and earlier housekeeping passed CI [7]. |
| IMPLEMENTED | Five metadata-qualified ABO products: Charles armchair, Belaya desk, Morava wardrobe, Rivet nightstand and AmazonBasics bookcase. Only Charles and Belaya have individual approved native meshes. Mixed Charles/Belaya scenes use placeholders. |
| LOCAL / UNRELEASED | 09A Chat bedroom UI, qualifier corrections and additional tests are uncommitted in the owner's checkout. A clone of the baseline does NOT contain that UI. The owner must finish its review, verification and delivery. |
| UNVERIFIED / BLOCKED | 09A live smoke: one extraction completed, two provider server errors; no full live conversation-to-layout pass. Verification stopped below the approved 4 GiB floor. Final full-suite, installed-wheel and narrow-browser checks remain pending. |
| NOT IMPLEMENTED | No runtime integration of these three datasets, dataset reference index, source-qualified FUTURE preview, learned placement prior, generated 3D assets or dataset-trained model. |

## Your delivery and its limits

- **You own:** M0-M4 isolated data modules, fixtures, CLI tools, evidence and reviewable PRs; M5 app wiring in a separate PR after the owner's reviewed 09A checkpoint; M6 integration acceptance.
- **Owner owns:** unfinished 09A, live chatbot acceptance, existing product qualification and approval of shared integration changes. Work on your own clone and branch, not the owner's dirty checkout.
- **Success:** all three source tracks have reproducible, bounded processing and documented public-use permission; eligible references and qualified previews work through the app/backend without changing generated A/B layouts. A source that is blocked is not a completed integration.
- **Outside this delivery:** training/fine-tuning, vector databases, semantic encoders, new agents, arbitrary room generation, rotation support in the spatial engine and automated 3D object synthesis.

> STATUS RULE: Report PASS, FAIL, BLOCKED or NOT RUN per gate. Code working with synthetic fixtures does not establish source rights, real-data correctness or public-demo readiness. Never turn an inaccessible source into a fabricated success count.

Read this handbook with its matching Markdown companion. Each M0-M6 prompt is self-contained for the specific milestone; give Claude the kickoff on page 10 first. The supplied `real_Data.pdf` is background, not an instruction to execute its older roadmap. This is an internal engineering handoff, not a course-assessment submission.

<!-- page -->

# 02 | Architecture and parallel ownership

## Preserve the authoritative path

```diagram
OFFLINE: sources -> rights + hashes -> source adapters -> reference pack
ON DEMAND: typed chat draft -> reference query -> local index -> reference panel
UNCHANGED: explicit choices -> Prepare -> Review -> Generate -> validated A/B
PREVIEW: qualified reference asset -> separate viewer; never a product binding
```

| Existing interface / location | Contract to preserve |
| --- | --- |
| `agents/catalog_conversation.py`: `interpret_catalog_conversation(turns, *, allow_live=False, client_factory=None)` | One explicitly authorized submission; typed extraction and source evidence. Legacy Requirements Interpreter remains compatible. |
| `assets/chat_specifications.py`: `retrieve_chat_candidates(draft)`; `prepare_chat_specification(draft, *, selections, procedural_ids)` | Current five-product lexical authority and immutable `PreparedCatalogSpecification`; no invented IDs, dimensions or approval. |
| `ui/layout_generation.py`: `_generate(specification, seed)` | Maximum two candidates / 500 attempts at the UI boundary; existing validator and scoring stay authoritative. |
| `render/selected_realistic.py`: `build_selected_realistic_scene(...)` | Exact selected design plus approved sidecars. Existing product binding/release types allow Charles and Belaya only. Do not insert dataset IDs into them. |

**Coordinates:** canonical meters; southwest origin; X east, Y north, Z up; furniture position is the lower-left footprint. North/south opening offsets start west; east/west start south. Rendering maps canonical `(x,y,z)` to Three.js `(x,z,-y)`. Source axes, pivots and quaternions must be verified separately. The canonical schema stores quarter turns, but the current generator and spatial/render-product path support **zero yaw only**.

## Ownership and shared interfaces

Own `src/archimind/datasets/`, `tests/datasets/`, `scripts/datasets/` and new dataset-specific documentation. External raw/processed data use a configured root outside Git. Until M5, do not edit owner UI/chat files, canonical schemas, generator/scoring, existing catalog/releases, historical receipts or the checked-in viewer bundle. Preserve `.agents/`, `.claude/` and secrets. New files and APIs below are **PROPOSED**, not existing repository features.

| New typed interface | Minimum responsibility |
| --- | --- |
| `SourceManifest` / `SceneReference` | Revision, hashes, permissions; source scene/object IDs, raw and normalized geometry, mapping version, split, opening knowledge, validation coverage and exclusions. |
| `ReferenceQuery` / `ReferenceSearchResult` | Typed room dimensions, categories and keywords -> bounded hits, snapshot identity, factual match reasons and source evidence. No executable text, raw paths or asset URLs. |
| `ReferenceAsset` / approved public pack | Source/derived hashes, tool versions, unit/anchor evidence, bounds, resource counts, attribution and permission receipt; separate from purchasable products. |

```sh
git clone --filter=blob:none https://github.com/ngstephen1/ArchiMind.git
cd ArchiMind
git switch -c data/dataset-reference-pilot 4dc5c026cafdfec23cc0924b6bcca62ece0f29f7
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Read applicable repository instructions first. Use one reviewed PR per milestone or coherent group. No automatic merge/push to `main`. Before M5, rebase onto the owner's agreed 09A commit and review changed contracts; do not assume access to the owner's Mac, `.env`, dataset copies or API keys.

<!-- page -->

# 03 | M0 - Sources, permissions and acquisition

**Prerequisites:** clean personal branch, repo instructions, external data root and measured free space. **Allowed:** new dataset contracts/tools/tests/docs; no app wiring. **Inputs:** source cards [1-3], original terms [4-5], existing readiness audit [8].

| Source track | Acquire only after verification |
| --- | --- |
| SSR-3DFRONT [1] | Pinned revision, schema and a small bedroom sample. Card reports structured boundaries, descriptions, sizes, positions, quaternions and FUTURE `jid` links. MIT metadata conflicts with its original-license section. |
| MIDI-3D / 3D-Front [2] | Pinned ID lists and a selectively accessible sample of GLBs plus available views/surfaces. The historical mirror is about 1.69 TB; that is NOT a verified current size or a download instruction. |
| 3D-FUTURE mirror [3] | Verified mirror manifest, original model IDs, mesh/material/texture members and actual transfer/extraction estimates. A Kaggle listing is not permission to redistribute assets. |

## Steps and required evidence

1. Record source URLs, exact revision, retrieval time, file inventory, expected/received bytes and SHA-256. Pin manifests; never rely on a mutable `main` URL for reproduction.
2. Track permissions separately for local research, derived metadata, thumbnails, public/browser bytes and external model-provider disclosure. Unknown means ineligible. SSR's license conflict and FUTURE's external-service restrictions [4] require documented applicable permission. Do not accept agreements, contact owners or upload restricted samples to Claude automatically.
3. Default budget: **1 GiB transferred and 2 GiB expanded per source**, with no bulk clone/LFS pull. Target at least 10 GiB free on the processing machine; project expansion plus a 4 GiB reserve must fit before starting. Request a revised budget before exceeding it. An archive requiring a larger full transfer is BLOCKED_NO_BOUNDED_ACCESS, including compressed tar files without selective access.
4. Use a finite, independent capacity observer during acquisition/conversion; stop task-owned workers below the reserved floor and do not auto-resume. The owner's previous 09A exception is historical, not blanket authorization for this new work.
5. Stream with byte/time limits, retain resumable partials and verify final hashes. Enforce limits when a server ignores Range or omits Content-Length. Reject archive traversal, symlinks, special files, duplicate paths and expansion bombs. Do not execute archive contents.

**Deliver:** source manifests, permission/evidence matrix, byte estimates, acquisition CLI and synthetic tests. Keep raw data, extracts, caches and restricted derived artifacts out of Git, CI artifacts and Claude context. A public pack must cover every dependency, including textures and previews.

**Gate:** all source decisions reproducible; bounded acquisition and unsafe-archive tests pass. Real processing is gated by applicable local-use permission. Unresolved public rights block public output, not synthetic engineering. Do not claim three-source completion while any required track is blocked.

### Claude prompt M0

```prompt
Implement M0 only for ArchiMind at the agreed baseline. Own the new
datasets package, dataset tests/tools and docs; preserve the current
ABO catalog, schemas, generator, UI and historical receipts. Audit all
three sources and permissions, pin manifests, and build bounded offline
acquisition with synthetic tests. Use the page-3 budgets; do not bulk
download, accept terms or send restricted data externally. Report exact
bytes/hashes, tests, permission evidence and BLOCKED gates. Stop before M1.
```

<!-- page -->

# 04 | M1 - Normalize SSR bedroom references

**Prerequisites:** M0 manifest and permitted local sample. **Allowed:** SSR adapter, shared reference contracts, dataset CLI/tests/docs. **Inputs:** pinned SSR records, preprocessing conventions [1,6], source hashes. Target 20-50 accepted bedrooms, scanning at most 200 deterministic candidate IDs; report shortfalls without enlarging the budget silently.

## Processing contract

1. Inspect one real row before coding against assumed field names. Verify whether `scene` is nested JSON or serialized text; use bounded JSON parsing, never `eval`. Inventory `bounds_bottom`, `bounds_top`, `objects`, `size`, `pos`, `rot`, `jid`, descriptions and split labels. Record schema/revision evidence.
2. Prove units, up axis, quaternion order, transform composition, position pivot and floor anchor using source code plus a known fixture. The card describes size as `[width,height,depth]` in meters and rotation as `[x,y,z,w]`; this does not prove every author's pivot convention. Unknown pivot/scale blocks geometric admission.
3. Once the Y-up convention is verified, use a recorded rigid basis transform. Example basis: canonical `(x,y,z) = (X-minX, maxZ-Z, Y-floorY)`. Convert orientation with the same basis, not by dropping quaternion components. Derive lower-left positions from transformed geometry/corners; never assume source positions already mean lower-left corners. Retain original and normalized values plus the transform matrix.
4. Check finite/positive dimensions, planar floor/ceiling, rectangular bounds and unique identities. Use a versioned reviewed category map; descriptions are untrusted metadata, not proof of product identity or intended use. Unknown categories/IDs get explicit exclusions. Keep source object IDs and `jid` even when a mesh is unavailable.
5. Export canonical `RoomDesign` only for fully supported rectangular, zero-yaw cases. Unsupported rotations, irregular rooms and tilted objects stay in audit/exclusion records; never rotate furniture to zero, replace an oriented footprint with an unlabelled AABB or modify canonical schemas to admit them.
6. Openings absent from source mean **unknown**, not zero real openings. A schema-only design may use empty opening lists with a mandatory sidecar flag. Run existing containment/collision checks at zero overlap tolerance. Do not label door/circulation checks passed when entrance evidence is missing; record them as not verifiable outside the canonical report.

**Deliver:** deterministic source-ID subset manifest, normalized reference JSONL, exclusion JSONL, transform/category-map versions and report. Every record carries source revision/hash, split, original identifiers, geometric eligibility, opening knowledge and check coverage. Do not copy real source rows into unit fixtures without the required distribution permission.

**Gate:** synthetic translation, quaternion sign equivalence, 90-degree/tilt rejection, floor-anchor, unit, corner and round-trip tests pass; a permitted real row is manually reconciled in 2D. Re-running gives identical content hashes. No fabricated doors, product approvals or successful-scene totals. Zero accepted scenes is a reported shortfall, not a reason to weaken validation.

### Claude prompt M1

```prompt
Implement only ArchiMind M1 using the M0-approved SSR snapshot. Keep
raw data external. Inspect a real row and prove units, quaternion order
and pivot before normalizing. Add a deterministic bounded bedroom
subset, original IDs, transforms, opening-knowledge sidecars and explicit
exclusions. Use existing RoomDesign and spatial checks only where
supported; never erase rotations or fabricate openings. Deliver offline
fixtures/tests, hashes and a manual 2D reconciliation. Preserve product,
generator and UI code. Report shortfalls and stop before M2.
```

<!-- page -->

# 05 | M2 - Process the MIDI-3D track

**Prerequisites:** M0 permission and a bounded-access route; M1 shared contracts. **Allowed:** MIDI adapter, cross-modal checks and dataset tests/tools/docs. **Inputs:** pinned room/furniture ID lists and approved source members [2]. Target up to five rooms, up to 20 objects per room and only the views/surfaces needed to establish alignment.

## Small, linked and auditable

1. Verify the actual file tree and association rules. The source card pairs the i-th room-ID entry with the i-th furniture-ID list. Preserve house, room and object IDs separately; do not flatten names and create accidental collisions. Keep original training/test identity; the card's MIDI test split uses the last 1,000 listed MIDI rooms [2].
2. Obtain individual members or an approved small sample. Do not clone the 1.69 TB distribution, concatenate multipart archives or download a large test archive just to obtain one GLB. If selective access cannot satisfy M0 budgets, document the exact required archive size and mark this real-data gate blocked; continue adapter work with synthetic fixtures.
3. Inventory each object's GLB, NPY surface and RGB/depth/normal/camera views. Distinguish source-provided, absent, malformed and excluded modalities. A scene GLB may already contain world-space placement; verify transforms before applying them a second time.
4. Parse bounded GLBs/JSON and restrict numeric NPY loading to `allow_pickle=False`, declared shape/dtype and size limits. Reject executable/object arrays, external model URIs, traversal and unbounded textures. Source image captions or metadata must not become coding-agent instructions.
5. Verify camera extrinsic direction, axis handedness, intrinsics, image origin and depth units against actual conventions. Test synthetic camera reprojection and source/object transforms. Save an alignment overlay for one permitted sample and list unresolved differences; a visually plausible screenshot alone is insufficient.
6. Use the M1 canonical eligibility rules. Keep source-normalized geometry distinct from product dimensions and public eligibility. Join SSR/FUTURE only through documented IDs or a verified mapping. Similar names, thumbnails or matching shapes do not prove identity. Record unjoined objects without guessing.

**Deliver:** per-room modality manifest, object associations, hashes, alignment report and shared `SceneReference` exports for eligible geometry. Views/point clouds support inspection and previews only; no diffusion model, point-cloud training or new runtime dependency is required. Samples from related SSR/MIDI sources are not independent evaluation data; record shared origin and split leakage risks.

**Gate:** fixtures cover list-length mismatch, orphan/duplicate objects, local/world transform handling, camera inversion, missing modalities and unsafe NPY payloads. One permitted real room is reconciled across available modalities, or the gate is explicitly blocked. Rights for images/surfaces/derived previews are checked separately from GLBs.

### Claude prompt M2

```prompt
Implement only the ArchiMind MIDI-3D adapter under the isolated dataset
boundary. Reuse M1 contracts, preserve room/object/split IDs and prove
camera and world/local transforms. Acquire at most five rooms through
M0-approved bounded access; do not fetch whole archives. Audit GLB,
numeric NPY and available views with offline synthetic tests and an
alignment receipt. Do not infer SSR/FUTURE joins from names or images.
Report inaccessible or missing modalities honestly. No training, core
schema, generator or UI changes. Stop before M3.
```

<!-- page -->

# 06 | M3 - Qualify FUTURE reference meshes

**Prerequisites:** M0 applicable access/permission, verified mirror manifest and M1/M2 identifiers where available. **Allowed:** dataset asset registry, isolated conversion tooling, tests and a local reference-preview prototype. **Inputs:** up to three specifically identified mesh/material/texture sets [3-6]. Meshes are visual reference assets, not newly qualified retail products.

## Conversion and release checklist

1. Establish an exact model-ID/member join, retaining original filenames and hashes. Unresolved `jid` links stay unresolved. Mirror or toolbox licensing is not automatically the asset license. Public approval must cover model bytes, textures, conversion and previews.
2. Preserve original OBJ/MTL/images privately. Resolve texture/material paths only within the admitted asset directory; reject remote references, missing dependencies and symlink/path escapes. Inspect all dependencies before conversion.
3. Use a version-pinned offline converter in a separate tool environment. Prefer an already available Blender installation; record its exact version and export settings. If unavailable, document the tool prerequisite rather than adding Blender to app dependencies. Disable scripts/network and execute only the known conversion script.
4. Export self-contained GLB with embedded textures. Verify source units, up/front axes, origin/pivot and floor anchor independently; glTF's meter convention is not evidence that an OBJ was authored in meters. Record every rigid/scale transform and compare source/derived bounds. Unknown scale blocks native preview. Do not resize a model to match ABO dimensions or a convenient canonical box.
5. Keep first-pass conversion free of decimation or texture resizing. Reject/hold assets exceeding existing ceilings: **15 MiB/asset, 100,000 triangles/asset, texture dimensions <=2,048 px**. Preview scene ceilings: **50 MiB unique encoded bytes, 300,000 instantiated triangles, 128 MiB decoded texture memory including mipmaps**. Missing textures and unsupported extensions/animation/skinning require explicit rejection or a separately reviewed policy, never silent degradation.
6. Release only reviewed `ReferenceAsset` entries: namespaced ID/version, source and GLB digests, converter receipt, unit/anchor/bounds evidence, resource inventory, attribution and public permission receipt. Inspect one original-scale preview, front/orientation and floor contact. No record enters `FurnitureAssetRecord`, ABO product releases or existing `ProductBinding`.

**Deliver:** conversion recipe, bounded asset inspector, allowlisted reference registry and up to three qualified previews. Original files remain unchanged; derived bytes and modifications are identified. A registry entry with unresolved permission is never packaged or served publicly.

**Gate:** missing/corrupt asset, stale digest, invalid dependency, unknown-scale and budget failures produce explicit unavailable/placeholder states. Test original-to-derived bounds, native-scale loading, repeated mount/disposal and restoration after a missing asset. Test with synthetic geometry in CI; real assets enter CI/package artifacts only with applicable redistribution permission.

### Claude prompt M3

```prompt
Implement only ArchiMind's isolated FUTURE reference-asset lane. Use
at most three exact, M0-approved model IDs. Preserve originals, pin the
offline converter, embed permitted dependencies and verify scale, axes,
anchor, bounds, hashes and the resource ceilings on page 6. Keep these
as source reference assets, never ABO product approvals or bindings.
Build a separate local preview prototype with reasoned failure states
and synthetic tests. Do not acquire replacements or shrink assets to
force a pass. Report every rights/resource blocker. Stop before M4.
```

<!-- page -->

# 07 | M4 - Unified reference retrieval

**Prerequisites:** M0-M3 contracts and fixture outputs; real packs only for eligible sources. **Allowed:** isolated index, facade and dataset tests/CLI. **Inputs:** versioned SSR/MIDI scene exports, FUTURE asset registry, permission receipts and the existing typed chat draft. No embeddings, model calls, product-catalog edits or UI changes.

## Proposed facade and index

```python
load_reference_pack(root, *, audience="public") -> ReferencePack
reference_query_from_chat(draft) -> ReferenceQuery
search_references(query, *, pack) -> ReferenceSearchResult
prepare_reference_preview(hit, *, pack) -> ReferencePreview
```

The server controls `root`; a user/model never supplies a filesystem path or URL. Use frozen, strict Pydantic records with explicit schema versions. `ReferenceQuery` contains verified room W/D/H, requested category counts, supported keywords and limits. Results have separate scene and asset hit tuples, each defaulting to at most three hits (maximum ten), with matches/empty/unavailable status and snapshot identity. A scene is not an asset or purchasable product.

- **Storage:** canonical JSON manifests/JSONL plus a small in-memory lexical index. Hash source revisions, exported content, category map, permissions and asset registry into the snapshot. Keep optional data outside package imports; absent data returns unavailable. No new database/service dependency.
- **Eligibility first:** public searches require documented public permission for every exposed record and dependency. Unknown, stale or revoked evidence is excluded. Unsupported room geometry is not shown as a validated rectangular example. Missing openings remain visibly unverified. Do not return raw restricted descriptions, images or paths when blocked.
- **Deterministic ranking:** scenes rank by requested-category coverage descending, normalized room-size distance ascending, keyword overlap descending, then namespaced source/scene ID. Assets rank separately by compatible category, keyword overlap and stable ID. A match is a reference, not proof of fit, intent or product availability. Do not broaden constraints silently.
- **Identity:** deduplicate byte-identical records and verified common-origin aliases; retain all provenance. Do not merge SSR/MIDI scenes just because dimensions or captions look similar. Preserve splits and related-source identity to prevent evaluation leakage.
- **Grounded output:** explanation text comes from checked result facts: matched categories, observed room dimensions, source, opening knowledge and preview availability. Treat descriptions as untrusted data, escape display text and never execute instructions embedded in it. No second LLM request composes explanations.
- **Freshness:** reject hits from a different snapshot during preview preparation. Recheck asset/permission digests before serving. Runtime never acquires, converts or repairs missing data; return explicit unavailable states.

**Deliver:** pure facade, reproducible public-pack builder, CLI search/preview manifest, index evaluation and unit fixtures. Evaluate expected-category retrieval, empty queries, deterministic order and latency; do not claim improved generated layout quality because the generator is unchanged.

**Gate:** shuffled input order yields identical ranks/hashes; stale, ineligible, missing-data, injection-like text and duplicate-source tests pass. Current `FurnitureSearchRequest`, `resolve_result()` and all five-product results remain unchanged. A FUTURE hit never resolves as an ABO product or planning sidecar.

### Claude prompt M4

```prompt
Implement only the four proposed dataset facade functions on page 7.
Build a small deterministic CPU lexical index from M1-M3 outputs, with
separate scene/asset hits, provenance and public-eligibility checks.
Derive queries from verified typed drafts; explain results from facts
without model calls. Test stale snapshots, duplicates, no matches,
injection-like descriptions and absence of data. Preserve ABO retrieval,
product qualification and generation. Deliver CLI evidence and tests;
report blocked real packs and stop before app wiring.
```

<!-- page -->

# 08 | M5 - Wire the app and backend safely

**Prerequisites:** M4 facade, reviewed module PRs and the owner's published/reviewed 09A checkpoint. **Allowed:** a separate integration PR for thin UI/backend hooks, reference viewer/build configuration and packaging. Agree the base commit before editing shared files. The owner's local uncommitted UI is not an integration base you can clone.

## User-visible behavior

1. Add a default-off server flag `ARCHIMIND_ENABLE_DATASET_REFERENCES=1` and server-only pack root `ARCHIMIND_DATASET_REFERENCE_ROOT`. Missing/invalid packs leave the app usable. No source data is loaded, downloaded or converted just by importing the app.
2. In Chat bedroom, use a ready/current typed draft to build a reference query. An explicit **Find bedroom references** action runs local retrieval. Show results under **References for next specification**, separate from **Currently displayed results**. Users still choose every actual product/template through existing controls.
3. Display source/scene identity, room dimensions, matched categories, opening knowledge, attribution and why the reference matched. Provide explicit **Preview reference** controls. Show a clear empty/unavailable explanation; never replace the current product search or suggest a reference asset is purchasable.
4. Changed pending measurements invalidate the reference query/result snapshot, not the stored generated layouts. A/B selection, camera changes, seed edits and ordinary reruns make no provider, acquisition or generator calls. Store reference state separately from 09A preparation and generation snapshots. Reset clears pending references, not displayed A/B results.

## Rendering and backend boundaries

- Preview supported normalized scene layouts through the existing Plotly renderer, with reference and incomplete-validation labels. Do not call a missing-opening example spatially approved. Unsupported source orientation stays excluded from canonical preview, with an explicit reason.
- Add a **separate** Components V2 reference-asset component and viewer entrypoint for qualified GLBs; compile it through the existing `frontend/realistic_viewer/build.mjs` pipeline. Do not widen the product ID literals, spoof V3 bindings or hand-edit generated bundles. New viewer/package resources need explicit manifest entries and owner review.
- The reference component accepts only an opaque approved ID/version/digest mapped by the server to an allowlisted public pack. No user URLs, uploads, arbitrary HTML/JS or restricted raw paths. Verify bytes, resource limits and cancellation before attachment. One active canvas per component, idempotent cleanup, released controls/listeners and no late asset attachment.
- Reference assets render at verified source scale with recorded normalization and their own state/attribution. They never substitute for selected A/B product meshes. MIDI image/surface evidence remains separately labeled; only permitted supported previews are exposed.
- Expose the same pure facade to backend callers; no changes to legacy interpreter schemas, graph agents or provider prompts are required. Do not send dataset descriptions/images to OpenAI or Claude as an automatic side effect. This feature adds no API request budget.

**Deliver/gate:** integration PR, packaged eligible reference pack or documented deployment prerequisite, default-off behavior and AppTest/browser evidence. Verify explicit actions, preservation of preparation/results, existing native/placeholder admission and both preview lifecycles. Public demo is blocked until the required real tracks and permissions pass.

### Claude prompt M5

```prompt
Rebase onto the owner-agreed reviewed 09A commit. Implement only the
thin M5 integration PR: default-off local reference retrieval, separate
next-specification panel, explicit previews and a distinct qualified
reference viewer. Reuse M4; do not change product selection, A/B inputs,
generation, validation or provider behavior. Preserve snapshots and
camera lifecycle. Build only via the existing script, update packaging
explicitly, and test disabled/missing/blocked packs. Report the exact
base and conflicts; do not merge or publish restricted artifacts.
```

<!-- page -->

# 09 | M6 - Acceptance and release delivery

**Prerequisites:** reviewed M5 branch, owner-approved integration base, M0 receipts and all source-specific gates. **Allowed:** verification, necessary integration fixes, packaging and evidence docs; no expansion into training or generator changes. Distinguish synthetic tests, real-data inspection, AppTest, ordinary-browser checks and fault-harness observations.

| Gate | Required scenarios and evidence |
| --- | --- |
| Acquisition / normalization | Pinned replay; interrupted/oversized downloads; unsafe archives/NPY; quaternion/pivot/units; missing openings; duplicate IDs, unsupported shapes/rotations and unresolved joins. Exact outputs and exclusions. |
| Search / eligibility | Stable rank/order; absent/stale/blocked packs; empty matches; injection-like text; verified dedup; source split leakage; no promotion of references into product identities or approvals. |
| Assets / lifecycle | Corrupt/missing/stale GLB, textures, native bounds/scale and budget limits; failure/recovery; one canvas per component; disposal/cancellation; no obsolete attachment or uncontrolled network request. |
| Existing app | All three specification modes; explicit product choices; immutable preparation; no provider/generator/candidate-acceptance calls from reference controls or reruns; pending/reset preserves A/B, selected object and camera behavior. |
| Public deployment | Every one of the three source tracks has real permitted outputs; attribution/dependencies covered; only eligible pack served; no raw/restricted files in Git, wheel, source archive, logs or CI artifacts. |

## Run once when the integrated branch is ready

These are commands, not claimed results. Use existing pinned dependencies and Node **20.13.1**. Develop with focused checks, then one coordinated full run. The full Python suite already includes offline source/wheel and isolated-install verification; do not rebuild repeatedly.

```sh
.venv/bin/python -m pytest -q tests/datasets
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_health.py
git diff --check
# From frontend/realistic_viewer, when the viewer changes:
npm ci --ignore-scripts --no-fund
npm run check
npm test
npm run build
```

Extend installed-package coverage: build offline `--no-isolation`; install `--no-deps --no-index`; import/query outside the checkout with networking blocked. Check eligible resources, artifact membership/hashes and reproducible viewer builds. Preserve old assertions and receipts; append tested hash-migration steps instead of replacing historical pins.

**Browser acceptance:** at 1440 x 1000 and 390 x 844, clarify a custom room, retrieve/preview references, choose products/templates, Prepare/Review/Generate seed 42 and compare A/B. Pending edits must preserve results. Test empty, missing, blocked and corrupt packs. Save external screenshots, console/network traces and selected identities. Exhaustion is not infeasibility. The owner owns 09A live acceptance; dataset checks need no live provider calls.

### Claude prompt M6

```prompt
Verify the reviewed integration branch against every page-9 gate.
Run focused checks, then coordinated full Python/frontend/health and
offline installed-wheel verification. Capture both browser viewports
and failure recovery separately from fixture evidence. Record exact
commits, commands, hashes, permissions and unexecuted gates. Confirm
the owner-approved 09A base and old preservation assertions. A missing
source or permission is BLOCKED, not PASS. Prepare reviewable PR and
CI links; do not auto-merge, publish data or extend feature scope.
```

<!-- page -->

# 10 | Claude kickoff, resume and handback

## Copy-ready kickoff

```prompt
You are implementing ArchiMind's dataset-reference feature on my own
clone/branch. Read this entire handbook and applicable repo instructions.
The handoff baseline is 4dc5c026cafdfec23cc0924b6bcca62ece0f29f7;
the owner's 09A UI is still local/unreleased. I own M0-M4 isolated data
modules and a separate M5 integration PR after the owner supplies its
reviewed 09A commit. All three sources are required for public-demo
completion: SSR-3DFRONT, MIDI-3D/3D-FRONT and 3D-FUTURE. Public rights
and bounded access are gates, not assumptions. First inspect Git state,
contracts, free space and evidence; then implement M0 only using its
prompt. Preserve current products, geometry, scoring and historical
receipts. No bulk downloads, terms acceptance, secret access, external
data uploads, model training or unapproved main-branch delivery. Keep
synthetic tests separate from real/public acceptance. Report deliverables,
commands, hashes, blockers and the exact next milestone, then stop.
```

## At every new Claude session

Read the latest milestone handback before editing. Confirm branch/base SHA, dirty files, accepted contracts, source revisions/permissions, available storage and remaining byte budgets. List the current milestone, allowed paths and unresolved gates. Run the focused relevant checks; do not replay acquisitions or API calls automatically. If facts differ from this snapshot, report the difference before shared-file integration.

**Dependency order:** M0 -> M1 -> M2 -> M3 -> M4; then owner-reviewed 09A + M4 -> M5 -> M6. A blocked real-data lane can continue on synthetic fixtures but remains blocked for public completion. Use one milestone prompt per task; do not ask Claude to implement all milestones in one unbounded run.

## Handback required with each PR

- Baseline/branch/commit, owned files, interface changes and integration dependencies.
- Source revisions; permission matrix; source/derived/index hashes; acquired/expanded bytes; accepted/excluded counts and reasons.
- Exact commands, pass/fail/not-run results, resource observations and evidence locations; real versus fixture coverage and browser limitations.
- PR/CI links, deployment configuration, data packaging/attribution inventory, rollback/off-switch and the next milestone prompt. No keys or restricted payloads.

## Source and repository reading list

Metadata and repository interfaces checked November 5, 2026; pin fresh source revisions before processing. The source PDF's older milestones are reconciled here, not silently treated as current.

- **[1]** [SSR-3DFRONT card and schema](https://huggingface.co/datasets/gradient-spaces/SSR-3DFRONT) - fields, source references and conflicting license signals.
- **[2]** [MIDI-3D/3D-Front card](https://huggingface.co/datasets/huanngzh/3D-Front) - modalities, ID lists and split convention.
- **[3]** [3D-FUTURE Kaggle mirror](https://www.kaggle.com/datasets/tobetheonly/3d-future-model) - verify actual inventory/access; listing is not permission.
- **[4]** [Original FUTURE agreement](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202004171628_60052.html) and **[5]** [original FRONT agreement](https://gw.alicdn.com/bao/uploaded/TB1ZJUfK.z1gK0jSZLeXXb9kVXa.pdf) - check applicable permissions, including external services.
- **[6]** [ReSpace](https://github.com/GradientSpaces/respace), [FRONT toolbox](https://github.com/3D-FRONT-FUTURE/3D-FRONT-ToolBox), [FUTURE toolbox](https://github.com/3D-FRONT-FUTURE/3D-FUTURE-ToolBox) - inspect conventions; code licenses do not clear dataset rights.
- **[7]** [Backend baseline CI](https://github.com/ngstephen1/ArchiMind/actions/runs/42139576080), [housekeeping CI](https://github.com/ngstephen1/ArchiMind/actions/runs/42137017804) - historical scope only.
- **[8]** Repo: `docs/audits/REAL_DATA_READINESS_AUDIT.md`, `docs/developer/STATUS.md`, `docs/developer/CHAT_BEDROOM.md`; owner's local `docs/data/CHAT_BEDROOM_09A.json` records the incomplete 09A run. Do not assume the local receipt is on the baseline branch.
