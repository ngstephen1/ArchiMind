# Real-data integration readiness audit

**Decision: READY WITH PREREQUISITES for a small curated furniture MVP.**

Audit date: **2026-10-28**. Deployment target: **noncommercial public demo**, including serving model bytes to browsers. Audited baseline: `main`, `c240e85de670ff02927a7be3f383dd367837d32a`, synchronized with `origin/main`. The only initial untracked paths were `.agents/` and `.claude/`; neither was inspected recursively, changed or staged. This audit changes documentation only.

## 1. Executive summary

ArchiMind can start **source qualification now**, followed by a bounded real-asset integration. It already has canonical metric geometry, deterministic approval, synchronized Plotly alternatives, optional guarded AI adapters and a working local GLB experiment. Reuse them. It does not yet have an integrated product catalog, manufacturer-grounded dimensions, selected-layout Three.js rendering or dataset-grounded layout generation.

The five strongest findings are:

1. `Furniture` holds finite metric dimensions and IDs, but has no product identity, dimension provenance, mesh anchor, asset version or license fields. A separate catalog can supply these without changing canonical geometry.
2. `validate_accessibility()` and the generator support rotation zero only. The schema's other stored rotations do not establish algorithmic support. A zero-rotation furniture MVP is possible; arbitrary furnished-room ingestion is not.
3. `render_layout_generator()` hands the actual selected candidate to both Plotly renderers. In contrast, `app.py` mounts `create_sample_realistic_room()` in Three.js, independently of the selected candidate.
4. The existing GLB is genuinely textured and checksum-verified. Its author explicitly says it is **not a real product**. Proportional mesh fitting is a rendering demonstration, not verified product sizing. See the [pinned Sheen Chair author documentation](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair/README.md).
5. The original 3D-FRONT and 3D-FUTURE agreements restrict third-party distribution and external services. A public noncommercial demo is not automatically eligible. Mirror availability does not resolve those rights; see section 6.

Choose **Option C: curated assets first, then evaluate dataset-scale expansion**. Begin with source and dimension evidence, not an archive download. Better meshes improve visualization; they do not fix the generator's limited functional reasoning. No production-readiness or architectural code-compliance claim follows from this audit.

## 2. Current architectural capabilities

Classification: **1** working/tested within stated scope; **2** backend implemented but not exposed through the main application; **3** experimental/partially integrated; **4** fixture/mock demonstration; **5** missing. A subsystem may have different classifications for different paths. “Tested” does not imply live-provider verification.

Full repository paths are relative to the root. In the capability table, abbreviated Python package paths share the `src/archimind/` prefix; abbreviated test files share `tests/`. Frontend paths share `frontend/realistic_viewer/`. Evidence names refer to existing tests, not proposed coverage.

| Subsystem and status | Actual implementation/application entry | Test evidence and practical boundary |
| --- | --- | --- |
| Canonical geometry **1** | `src/archimind/models/room.py`: `Room`, `Door`, `Window`, `RoomDesign`; `models/furniture.py`: `Furniture` | `tests/test_models.py`: strict finite dimensions, openings, unique identifiers and JSON round trips. Single rectangular room, arbitrary nonblank category string; no product/asset schema. |
| Planar collision/containment **1**, rotations **5** | `geometry/footprints.py`: `furniture_footprint()`; `geometry/validator.py`: `validate_layout()` | `tests/test_geometry.py`; unsupported rotations raise/propagate explicit unsupported results. Rectangular footprints, not detailed mesh contact. |
| Door approach/circulation **1** within approximation | `geometry/accessibility.py`: `AccessibilityConfig`, `validate_accessibility()`, `_circulation()` | `tests/test_accessibility.py`: blocked entrances, all walls/corners, disconnected regions, narrow passages, alternatives, unknown checks and deterministic serialization. No hinge/swing or per-object functional access. |
| Layout generation/scoring **1** | `geometry/layout_generator.py`: `generate_layout_candidates()`, `_score()`; UI `_generate()` | `tests/test_layout_generator.py`, `test_layout_generation_ui.py`. Seeded bounded search, dimensions preserved, zero rotation. First requested distinct passing candidates are ranked; not global optimization. |
| LangGraph workflow **2**; offline demonstrations **4** | `workflow/graph.py`: `run_workflow()`; guarded nodes in `workflow/nodes.py` | `tests/test_workflow.py`, `test_requirements_workflow.py`, `test_layout_recommendation_workflow.py`, `test_spatial_critique_workflow.py`, `test_interior_styling_workflow.py`. Full graph is not the Streamlit generator's entry point. |
| Requirements interpreter **2** | `agents/requirements_agent.py`: `interpret_requirements()`; conversion/grounding in `requirements_conversion.py` | `tests/test_requirements_agent.py`, `test_requirements_workflow.py`. Optional bounded interpretation, not a public-app free-text-to-room flow. Live behavior not exercised in this audit. |
| Layout advisor **2** | `agents/layout_agent.py`: `recommend_layout()`; `workflow/layout_recommendation.py` | `tests/test_layout_agent.py`, `test_layout_recommendation_workflow.py`. Selects among already approved candidates; does not invent new furniture positions or product IDs. |
| Spatial critic **2** | `agents/spatial_critic_agent.py`; `workflow/spatial_critique.py` | `tests/test_spatial_critic_agent.py`, `test_spatial_critique_workflow.py`. Grounded advisory assessments cannot override deterministic approval. |
| Interior stylist **1** guarded panel, **4** direct fixture | `workflow/selected_styling.py`: `style_selected_layout()`; `ui/interior_styling.py`: `render_interior_styling()`; `agents/interior_stylist_agent.py`: `recommend_style()` | `tests/test_interior_stylist_agent.py`, `test_interior_styling_workflow.py`, `test_interior_styling_ui.py`. Catalog-constrained metadata, explicit consent, flag gates and fallback. No mesh/material application by the advisor. |
| Selected A/B UI and session state **1** | `ui/layout_generation.py`: `render_layout_generator()`, `RESULT_KEY`, `SELECTION_KEY`; `app.py` | `tests/test_layout_sync.py`, `test_layout_generation_ui.py`. Actual stored candidate goes to both renderers; view changes do not regenerate or call spatial validation. Styling invocation separately performs safety verification. |
| Plotly 2D/3D **1**, procedural representation | `render/floorplan_2d.py`: `render_floorplan()`; `render/design_3d.py`: `render_design_3d()`; `room_3d.py`, `furniture_3d.py` | `tests/test_floorplan_2d.py`, `test_room_3d.py`, `test_furniture_3d.py`, `test_design_3d.py`, `test_layout_sync.py`. Structural openings and recognizable cuboid furniture; no imported meshes. |
| Catalog-color preview **3** | `render/style_colors.py`: `render_styled_design_3d()`; optional styling-panel preview | `tests/test_style_color_preview.py`. Only trace colors and preview metadata change. One finish colors every furniture part; no textures or physical material properties. |
| Three.js architectural room **3**, fixed sample **4** | `render/realistic_scene.py`: `ArchitecturalScene`, `scene_payload()`, `render_realistic_scene()`; `app.py` calls `examples/sample_realistic_room.py` | `tests/test_realistic_scene.py`, `frontend/realistic_viewer/tests/room.test.js`. Canonical data envelope and complete bindings exist, but only one asset ID and a fixed chair/desk scene are exposed. |
| GLB loading/static serving **1** for one asset, catalog **5** | `render/realistic_viewer.py`: `asset_path()`, `verify_asset()`, `_component()`; frontend `room_viewer.js`, `asset_pool.js` | `tests/test_realistic_viewer.py`, frontend geometry/resource tests. Local Components V2 assets, fixed URL, size/hash checks, shared resources and explicit fallback. Not a general uploaded-model service. |
| C01 Codex advisor **2** | `integrations/codex_advisor.py`, `codex_schemas.py` | `tests/test_codex_advisor.py`: mocked subprocess/error paths. Optional, disabled by default; not called during this audit. |
| Real catalog/import/prior learning **5** | No product catalog importer, room dataset importer, ingestion CLI or dataset-grounded generator found | Existing stylist catalog is appearance metadata; existing `ASSET_CATALOG` is one trusted rendering entry, not a product database. |

### Deterministic scope that must remain authoritative

`AccessibilityConfig` defaults: required door depth **0.3 m**, advisory depth **0.9 m**, advisory side margin **0.15 m**, walking clearance **0.6 m**. Circulation uses geometric free-space/connectivity for an axis-aligned square occupant, not a sampled occupancy grid. It can conservatively reject diagonal routes, exact-width pinches, and entrances usable away from their midpoint. It does not prove access to a desk chair, wardrobe opening or bed side.

The generator score is **80 × usable-space ratio + 20 × advisory-clearance ratio**. It is a heuristic about these measured properties, not expert design quality. Search limits are 32 furniture items and at most 10,000 attempts; the present UI requests two candidates with a 500-attempt budget. Unsupported or unevaluated required checks cannot become a passing accessibility report.

## 3. Reusable components and gaps

| Concern | Reuse | Required addition; no change made here |
| --- | --- | --- |
| Geometry identity | `RoomDesign` and original candidate indices | Sidecar catalog snapshot and ID bindings; no second canonical room model. |
| Real dimensions | Positive finite width/depth/height in meters | Source measurement, item-versus-package distinction, unit conversion and uncertainty evidence before generation. |
| Categories | Existing `bed`, `desk`, `storage`, `chair` usage | Explicit source-category mapping. A wardrobe is not any generic storage mesh. |
| Asset selection | Immutable trusted `ASSET_CATALOG`, category check | Multiple versioned allowlisted entries, deterministic eligibility/selection and product variants. |
| Placement | `toThree()`, `fitBounds()`, floor grounding | Qualified native bounds/orientation/anchor and verified-size placement policy. Existing shrink-to-fit must not be presented as physical truth. |
| Storage | Bundled assets and package-data inclusion | Bounded curated storage, manifest-pinned cache, packaging/attribution checks and aggregate scene budgets. |
| Materials | GLTFLoader/PBR and original chair materials | Catalog-to-material-slot mapping, licensed texture references and compatible extensions. Flat stylist colors are not PBR materials. |
| Robustness | Placeholder handling, pool lifecycle, strict JSON envelopes | Per-asset geometry/texture budgets, extension validation, cancellation/failure coverage across multiple IDs. |
| AI recommendation | Grounded allowed-ID patterns in existing adapters | Only after catalog qualification: recommend eligible catalog entries, then deterministically check compatibility. No new agent required. |

The one-asset checks are intentionally narrow. `_glb_document()` requires embedded geometry/images and performs structural checks, not full glTF conformance, triangle limits or decoded texture-memory accounting. Expanding the allowlist without qualification would remove the practical safety afforded by the fixed known asset.

`frontend/realistic_viewer/src/room_viewer.js` configures GLTFLoader without Draco or KTX2 decoder setup. New assets requiring unsupported compression/extensions cannot be assumed loadable. Qualify extension requirements explicitly; do not add runtime decoder/CDN dependencies as an incidental catalog change.

## 4. Realism-gap analysis

| Factor | Current cause | Dataset needed? | Useful next treatment |
| --- | --- | --- | --- |
| Meshes | Plotly cuboids; only chairs textured in Three.js | Small curated models suffice | Add qualified bed/desk/storage assets; retain obvious placeholders. |
| Dimensions/proportions | Manually entered sizes; fitted mesh can underfill a footprint | Grounded product measurements needed | Use item-level dimensions before search; reject incompatible mesh ratios. |
| Category coverage/variety | Single chair repeated; bedroom has no matching real assets | Catalog expansion, not a huge dataset | Prefer distinct compatible categories before cosmetic variants. |
| Materials/textures | Flat Plotly colors; procedural floor; original chair PBR | Licensed textures/models help | Preserve model material slots; later map catalog finishes deliberately. |
| Lighting/shadows | Three.js already has environment reflections, tone mapping and shadows | No | Tune existing settings with reference scenes; do not change dimensions to improve appearance. |
| Room construction | Actual opening holes, but surface walls with no thickness, reveals, ceiling or door leaves | No for bounded renderer improvements | Separate room-construction task after selected-layout integration. No door-swing claim. |
| Orientation | Zero furniture yaw; native front conventions not general | No for supported rotations; data requires normalization | Pre-normalize asset axes for yaw-zero MVP. Broader rotation support is a separate cross-layer task. |
| Camera/navigation | Functional orbit/zoom/reset and responsive fit; translucent walls can obscure contrast | No | Improve existing cutaways/framing if measured; test physical mobile devices later. |
| Room/object relationships | Placement search lacks task-specific adjacency, daylight, bed-side and work-zone objectives | Data can inform future priors, but explicit constraints also help | Evaluate architectural utility separately from screenshot realism. |
| Source room fidelity | One rectangular room, no measured plans or connected rooms | Room data plus new import/model support | Defer arbitrary as-built ingestion; do not flatten it silently to a rectangle. |

New assets alone will not establish usable wardrobe doors, seated desk access, style compatibility, construction feasibility or regulatory compliance. Professional synthetic scenes can offer layout priors but are not measured evidence of real buildings.

## 5. Dataset and asset-source comparison

Documentation and small metadata descriptions were inspected; **no dataset archive or new model was downloaded**. “Unknown” means this audit did not establish the fact, not that the data lacks it.

### Primary candidates

| Candidate | Confirmed contents/access/size | Geometry, scale and relationships | MVP conclusion |
| --- | --- | --- | --- |
| [huanngzh/3D-Front card](https://huggingface.co/datasets/huanngzh/3D-Front/raw/main/README.md) | Processed MIDI-3D derivative: object GLBs, NPY surfaces, RGB/depth/normal views and cameras. Card declares CC BY-NC 4.0. | House/room/object organization and aligned room/object ID lists. Exact units, front axes, product dimensions and completeness require inspecting the processed schema/assets. | Useful research candidate; public-hosting rights unresolved against original terms. Not a drop-in room importer. |
| [Mirror file tree](https://huggingface.co/datasets/huanngzh/3D-Front/tree/main) | Displayed 1.69 TB at revision `156fc53`; scene parts include 42.9 GB chunks. Test scene archive alone is 13.3 GB. Public documentation accessible without credentials. | Split archives imply substantial extraction/storage; a small ID manifest is not a downloadable small model subset. | Do not clone/LFS-pull this repository for an MVP. Establish selective retrieval and rights first. |
| [3D-FUTURE Kaggle mirror](https://www.kaggle.com/datasets/tobetheonly/3d-future-model) | Landing page returned no extractable dataset details. Exact mirror revision, archive size, access/login requirements, inventory and mirror license were **not verified**. | Original [2020 report](https://arxiv.org/abs/2009.09633) describes 9,992 detailed textured furniture instances, 5,000 rooms and 20,240 synthetic images. These are that report's counts, not verified mirror counts. | No-go for public asset hosting without rights clearance. Do not infer a newer release's inventory from old paper counts. |

Original 3D-FRONT is a professionally designed **synthetic** furnished-scene collection; its [2021 paper](https://arxiv.org/abs/2011.09127) reports 18,968 rooms and 13,151 furniture objects. Its [official toolbox](https://github.com/3D-FRONT-FUTURE/3D-FRONT-ToolBox) consumes scene JSON, including layout/floor/furniture information. This differs from the processed GLB mirror.

The [official FUTURE toolbox](https://github.com/3D-FRONT-FUTURE/3D-FUTURE-ToolBox) demonstrates textured objects, poses and OBJ outputs; its example renderer normalizes models to (-1, 1). That normalization is not a meter-scale guarantee for source models. OBJ/material conversion, ID joins, texture packaging and transforms would need verification. Its historical Blender/Open3D environment is not an ArchiMind dependency requirement. Exact category coverage, manufacturer dimensions and model-to-room completeness of the Kaggle release remain unknown.

### Credible alternatives

| Source | Confirmed evidence | Limits and fit |
| --- | --- | --- |
| [Amazon Berkeley Objects (ABO)](https://amazon-berkeley-objects.s3.amazonaws.com/index.html) | CC BY 4.0; 147,702 product listings, over 7,900 textured glTF products, PBR maps and dimension metadata. Listing archive 83 MB; model archive 154 GB. | Strongest first **product-data** candidate. Not every listing has a model or complete usable dimensions. Item-level joins and dimension consistency need qualification; no room layouts supplied. Credit Amazon.com and dataset contributors, link license and record modifications. |
| [ABO model README](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) | Individual GLB paths, model-ID join, mesh/face/image counts and extents. +Y up, natural front +Z; floor-standing models sit at Y=0. | Existing Three.js mapping is compatible after validation. Hanging/wall-mounted objects need other anchors and are excluded from the initial MVP. Individual objects can be addressed without retrieving the full archive. |
| [Khronos Sheen Chair, pinned revision](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair/README.md) | Existing local GLB uses sheen, texture transforms and material variants; model is CC0, attributed to Eric Chadwick/Wayfair. | Best existing loader regression fixture. Not a real product or verified manufacturer size. The broader sample collection needs per-model rights review; do not assign one blanket license. |
| [Poly Haven asset license/terms](https://polyhaven.com/license) | Models, textures and HDRIs are CC0; asset redistribution is permitted. Website example renders/text/logos have different rights; scraping requires permission and API terms are separate. | Good realistic appearance-source candidate. Exact furniture-category coverage, selected model format, byte size and metric dimensions are not established here. Use asset-specific evidence and lawful retrieval, not website thumbnails as redistributable previews. |
| [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit) | Official page lists 140 3D files, CC0, furniture/interior/bed/chair/table tags; free download is available. | Low-complexity visual coverage alternative. Exact current archive size/formats/units and product measurements were not inspected. Stylized assets do not establish manufacturer fidelity or photorealism. |
| [CubiCasa5K](https://github.com/CubiCasa/CubiCasa5k) and [dataset license](https://raw.githubusercontent.com/CubiCasa/CubiCasa5k/master/LICENSE) | 5,000 annotated floor-plan images, SVG/polygon annotations across 80+ categories; CC BY-NC 4.0. | Later floor-plan interpretation research, not a textured furniture catalog. Usable metric scale, ceiling heights and conversion to a single rectangular room need per-record evidence. Attribution/noncommercial obligations apply; code or model rights must be reviewed separately. No ingestion recommended now. |

**Best first source:** retain the existing chair for regression tests; qualify a few **ABO product entries** for dimension-grounded additions, with CC0 sources as alternatives when both dimensions and formats can be established. ABO is a source recommendation, not approval of any specific SKU. A qualified three-category set has not yet been found. No API key, GPU or paid subscription is required to begin documentation-level qualification.

## 6. Data licensing and provenance concerns

This is a technical eligibility assessment against published terms, not a substitute for permission from a rights holder. Public browser delivery exposes asset bytes, even if the application has no download button.

| Evidence | Effect on the confirmed public-demo target |
| --- | --- |
| [Original 3D-FRONT agreement, June 18, 2020](https://gw.alicdn.com/bao/uploaded/TB1ZJUfK.z1gK0jSZLeXXb9kVXa.pdf?file=TB1ZJUfK.z1gK0jSZLeXXb9kVXa.pdf), §§3.2–3.3 | Research-only grant, no sublicense; restrictions include commercialization, third-party dataset availability and external services using data/derivatives/results. Preserve notices/source. Block public use unless applicable additional permission or superseding rights are documented. |
| [Original 3D-FUTURE agreement, March 28, 2020](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202004171628_60052.html), §§3.2–3.3 | Separately verified agreement has the same relevant research/distribution/external-service restrictions. The official toolbox links this agreement. Kaggle mirroring does not establish permission to rehost. |
| Mirror license labels | They are claims by the mirror publisher; no chain of authority overriding original restrictions was established. Do not combine them into a permissive conclusion. |
| CC0 / CC BY / CC BY-NC candidates | Check the exact asset, textures and accompanying metadata, not only repository code. Attribution and modification records must travel with derived assets where required. Noncommercial permission is not evidence of merchant suitability or ownership of trademarks. |

Keep source URL/revision, access date, creator, copyright, exact license URL/text identity, attribution, redistribution/hosting/commercial status and modification history separately. Record missing evidence as unknown/ineligible. An asset's measurement claim also needs provenance; permissive copyright does not certify physical accuracy.

## 7. Canonical model and renderer compatibility

### Minimum architecture

**No canonical schema change is needed for the first MVP.** Keep asset data outside `RoomDesign`. Evolve the existing sidecar binding pattern with a versioned catalog snapshot and exact furniture-ID bindings. Preserve normal canonical JSON consumers.

| Catalog concern | Minimum information to qualify later |
| --- | --- |
| Identity/provenance | Stable asset/version and source product/variant IDs; immutable source/retrieved/derived hashes and rights evidence. |
| Physical dimensions | Original units/values, width/depth/height in meters, item-versus-package interpretation, measurement source and qualification status. |
| Render geometry | Native up/front axes, transformed bounds, floor anchor and normalization transform; these are distinct from physical dimensions. |
| Materials/previews | Embedded texture/material inventory, required extensions, optional independently licensed preview and material-slot IDs. |
| Quality/storage | Encoded bytes, triangles, texture dimensions/decoded-memory estimate, supported category and approved local path. No user-supplied URL. |
| Suitability | Explicit supported room/category/use, dimension agreement, known exclusions and approved/unknown/rejected status. Clearance envelopes remain future metadata until an engine consumes them. |

Local cache keys should include source version and content hash. Preparation is offline; runtime loads only approved local entries. Missing, rejected, incompatible or unsupported assets use labeled canonical placeholders. AI may later recommend only qualified IDs; deterministic code owns eligibility and placement.

### Positioning without altering validated geometry

Canonical coordinates are meters, origin southwest interior corner, X east, Y north, Z up. Furniture `(x_m, y_m)` is the lower-left unrotated footprint corner. North/south opening offsets start west; east/west offsets start south. Three.js uses `(x, y, z) -> (x, z, -y)`; its +Z front maps to canonical south at yaw zero.

For a qualified floor-standing asset, first apply its documented unit/orientation transform offline or through a fixed catalog transform. Measure its resulting bounds. Ground its minimum vertical bound at zero and align its declared anchor to the canonical footprint; verify its metric envelope against the existing width/depth/height. Do not mutate those dimensions or x/y to accommodate a mesh.

Current `frontend/realistic_viewer/src/geometry.js:fitBounds()` instead chooses `s = min(width/native_X, height/native_Y, depth/native_Z)`, centers X/Z and grounds Y. It can produce a smaller visible chair than its nominal box. This remains acceptable only when labeled an illustrative fitted asset. A product-accurate binding must qualify scale/bounds and fail to a placeholder on mismatch. No nonuniform stretch or undocumented “helpful” shrink is appropriate.

When choosing real furniture **before generation**, instantiate a new specification using qualified product dimensions, then run the unchanged generator and validators explicitly. Choosing a visualization for an already validated design must not resize that design. If no compatible product exists, preserve its placeholder. Mesh collision and ergonomic envelopes are not substitutes for the authoritative footprint checks.

### Rotation decision

Proceed with a **yaw-zero** MVP and pre-normalized native axes. Native model-axis correction does not add furniture rotation support. Before importing arbitrary real-world layouts, a separate task must define rotated anchor semantics and update footprints, containment, circulation, generation, Plotly and Three.js together. Unknown yaw/quaternion values must be rejected or left unevaluated, never coerced to zero.

## 8. Readiness matrix

Readiness applies to the named workstream, not to the application as a whole. **READY** requires integrated verified prerequisites; **READY WITH PREREQUISITES** means bounded missing work with reusable foundations; **BLOCKED** means essential rights/data/representation remain unresolved.

| Workstream | Current/reusable evidence | Missing capability and dependency | Risk | Recommendation |
| --- | --- | --- | --- | --- |
| 1. Real furniture rendering | Working one-asset GLTFLoader, `realistic_scene.py`, Python/frontend renderer tests | Qualified multi-category models, generalized IDs, selected-layout handoff; depends on catalog and rights | Medium | **READY WITH PREREQUISITES** |
| 2. Catalog and real dimensions | Metric `Furniture`, sidecar bindings | Product/variant provenance, normalized measurements, bounds agreement; source qualification first | High | **READY WITH PREREQUISITES** |
| 3. Materials/textures | Original chair PBR works; flat-color preview separately tested | Qualified material slots/textures, budgets and stylist mapping; depends on asset selection | Medium | **READY WITH PREREQUISITES** for original asset materials, not arbitrary finish application |
| 4. Real-world room ingestion | Strict rectangular `RoomDesign`/openings | Licensed metrically grounded records; polygon/multi-room/rotation policy and importer absent | High | **BLOCKED** for general ingestion |
| 5. Dataset-grounded generation | Bounded deterministic generator and reports | Rights-cleared layouts, normalization, useful features/priors, held-out evaluation; depends on 4 | High | **BLOCKED** |
| 6. AI-assisted furniture selection | Existing closed-catalog grounding patterns and gates | Eligible furniture catalog, dimension-safe recommendation contract and deterministic checks | Medium | **READY WITH PREREQUISITES**; no live AI needed for MVP |
| 7. Streamlit/Three.js synchronization | Canonical scene envelope, Plotly selection/session tests | Main UI still mounts sample; connect selected object and catalog snapshot without backend work on view change | Medium | **READY WITH PREREQUISITES** for one-way viewing; editing is out of scope |
| 8. Performance/asset management | 15 MiB per-asset cap, shared pool/disposal, one known GLB | Aggregate bytes/decoded textures/triangles, bounded acquisition/cache and device measurements | High at scale | **READY WITH PREREQUISITES** for curated subset; not dataset-scale serving |
| 9. Licensing/redistribution | Pinned chair rights/notices; permissive alternatives documented | Entry-level rights register and attribution for each new asset | High | **READY WITH PREREQUISITES** for curated sources; **BLOCKED** for FRONT/FUTURE public hosting |
| 10. Testing/reproducibility | 1,219 Python + 27 frontend tests, committed bundle checks and CI | Catalog fixtures, real-dimension evidence, multi-asset packaging and browser/performance gates | Medium | **READY** to start qualification/testing; **READY WITH PREREQUISITES** for a new asset release |

## 9. Option A/B/C comparison

| Criterion | A — curated MVP only | B — FRONT/FUTURE pipeline first | C — curated first, then expansion |
| --- | --- | --- | --- |
| Difficulty | Low–medium; a few qualified entries | High; transforms, joins, conversion and unsupported rooms/rotations | Medium initially, incremental expansion |
| Licensing | Bounded per-asset review | Public-use blocker under reviewed original terms | Low initial exposure; large-source gate remains explicit |
| Storage/preprocessing | Small fixed assets; manual evidence review | Large archives/extraction and legacy tooling adaptation | Small first, measured costs before scaling |
| Visual impact | Immediate for qualified categories | Potentially large, delayed by pipeline/rights | Immediate improvement plus deliberate variety growth |
| Architectural impact | Accurate sizes if qualified; same limited placement heuristic | Potential scene priors, not automatic expert reasoning | Dimension grounding first; layout reasoning evaluated separately |
| Runtime | Can stay local and bounded | Needs derived, optimized, rights-cleared runtime subset | Same small runtime contract while offline tools evolve |
| Tests | Catalog, placement, fallback and A/B identity | All of A plus ingestion, distribution shifts and broader geometry | Stage tests before expanding data |
| Destabilization risk | Low if canonical code stays unchanged | High if importer drives model/rotation changes prematurely | Lowest practical integration risk with reusable boundaries |

**Order: C, starting with A's bounded proof.** B is not a shortcut to realism. Even successful preprocessing would not remove the reviewed license restrictions or prove useful layout quality.

## 10. Recommended MVP and roadmap

Target the existing 5 × 4 × 2.7 m bedroom and existing generator/validators. Seek **bed, desk, wardrobe/storage**, with chair as an optional fourth category. Three to five categories is a goal, not permission to substitute the wrong object. Ship only qualified entries; retain explicit placeholders elsewhere. Existing layouts can use dimension-compatible assets only. A separately explicit catalog-based specification may use real dimensions before generation. No live AI is required.

The ordered file-level tasks, acceptance tests and first-task prompt are in `REAL_DATA_IMPLEMENTATION_PLAN.md`. Their checkpoint boundaries are:

| Task | Gate/deliverable |
| --- | --- |
| 08A | Source/license/dimension qualification register. No ingestion/downloads. Honest unknowns allowed; no public-ready claims for unqualified assets. |
| 08B | Strict sidecar catalog and normalized dimensions; canonical schemas unchanged. |
| 08C | Small approved local GLB subset, metric placement and resource/rights manifests. |
| 08D | Exact selected candidate rendered by Three.js with compatible assets or placeholders. |
| 08E | Explicit asset choices, eligibility labels and session-safe fallback behavior. |
| 08F | Measured catalog expansion and larger-source feasibility, conditional on rights. |
| 08G | Separately evaluated room priors/functional planning; rotation/room support prerequisites first. |

08A–08E need no new API key, GPU, paid model, cloud service or asset subscription. Source permission may still be required for a selected entry; lack of permission means exclude it. Later large-scale work needs a separate storage/resource decision, not an assumed GPU requirement.

## 11. Risks, blockers and prerequisites

Ordered by priority:

1. **Rights to public model delivery:** exclude FRONT/FUTURE from public runtime assets unless applicable written permission resolves the restrictions. Preserve source and derived-asset license evidence.
2. **Physical accuracy:** no qualified multi-category product set exists yet. Item dimensions, variant identity, unit conversion and mesh bounds must agree before a product-size claim.
3. **Integration gap:** Three.js is independent of A/B selection. Preserve original candidates/reports/scores when adding its adapter.
4. **Unsupported geometry:** yaw-zero/single-room scope is intentional. General room/layout import must wait for a separate representation and rotation decision.
5. **Resource scaling:** 15 MiB encoded per asset is not a scene-memory limit. Multiple 4K textures and dense repeated meshes can overwhelm mobile devices despite small downloads.
6. **Architectural usefulness:** the score does not assess furniture use, daylight or relationships. Do not report visual realism as better planning accuracy.

Observed renderer limitations include translucent-wall contrast/sorting, no ceiling/wall thickness, repeated chair variants and no material-slot editing. Full glTF validation, arbitrary extension support, device FPS/GPU memory, physical mobile touch behavior and multi-browser compatibility remain unverified. No source changes were made to address them.

## 12. Verification results

### Executed baseline and CI

These checks were actually executed during this audit's read-only preparation against the same unchanged code baseline. Documentation additions do not change those implementations. No tests were removed or weakened.

| Check | Exact result |
| --- | --- |
| `python -m pytest -q` | **1,219 passed in 75.97s (0:01:15)**; no failures/skips reported |
| Frontend `npm test` | **27 passed, 0 failed, 0 skipped**, duration 181.911042 ms |
| Frontend `npm run check` | Exit 0 |
| Production bundle equivalence | esbuild with `write:false` matched committed JS/legal output; copied CSS/HTML/standalone files and Three.js notice matched byte-for-byte |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 104 files already formatted |
| `python -m pip check` | No broken requirements found |
| `python scripts/check_health.py` | HTTP 200 `ok`, temporary server stopped |
| Existing baseline GitHub CI | [Successful run for c240e85](https://github.com/ngstephen1/ArchiMind/actions/runs/40748777967) |

`.github/workflows/ci.yml` runs Python 3.11/Ubuntu, dependency checks, Ruff, Node frontend tests/syntax/build, committed-bundle diff, full pytest and Streamlit health. It is verification CI, not a deployment pipeline. It does not benchmark mobile hardware or enforce a multi-asset scene budget.

Reproduction commands (the normal build writes the existing committed bundle; require an empty diff):

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pytest -q
python -m pip check
python -m ruff check .
python -m ruff format --check .
python scripts/check_health.py
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer run build
git diff --exit-code -- src/archimind/_viewer_assets
```

### Asset inventory and licenses

One unique checked-in furniture GLB exists under `src/archimind/_viewer_assets/furniture/`: **SheenChair.glb, 4,125,648 bytes**, SHA-256 `f0af2a2b102d28d540236306ae19f8fb36842df76bd38cf76f063f9bd2853399`, matching `PROVENANCE.json`. An ignored `build/lib/` copy exists; it is not another catalog asset. The GLB has four meshes/four primitives, six materials, seven embedded images and no external image/buffer URI. The bundled `viewer.js` is **663,774 bytes**.

Local `CC0-1.0.txt`, `CC-BY-4.0.txt`, `UPSTREAM_LICENSE.md`, `README.md` and `PROVENANCE.json` are present. `UPSTREAM_LICENSE.md` distinguishes CC0 model-associated content from CC BY 4.0 metadocumentation; logos/trademarks are excluded. Three.js MIT notice is bundled separately. The pinned upstream revision is `8f492390ddc7a2ae221a1369ef560589cf8c70fb`. Runtime hashing reads the known GLB; a generalized catalog will need a measured verification/cache strategy, not repeated unchecked model reads.

### Actual browser inspection

Chromium local app at **1440 × 1000** and **390 × 844**; all AI/Codex flags explicitly disabled in the inspection server's process environment. No model/API/Codex calls occurred.

- Seed 42 produced two validated alternatives in nine attempts. A score **67.721925**, B **67.614973**. Selecting B updated both Plotly labels/views. The Three.js scene retained its two chairs/desk and unchanged coordinates, confirming its independent status.
- Direct fixture styling on B displayed `deterministic_fixture`, `not_evaluated`, and the original score/seed; no material application was claimed. This did not exercise live styling or a mocked accepted-plan color preview.
- The room rendered both textured chairs, one blue labeled desk placeholder, south door and north window, floor, walls and footprints. Its 704 px desktop component and 347 px narrow component fit without horizontal overflow; narrow stage height was 360 px. Text wrapped readably; small in-scene labels remain a narrow-screen limitation.
- Orbit drag, wheel zoom, reset and front-wall cutaway responded. This is a resized desktop browser, not physical-phone touch verification. Initial framing kept the room visible, with surrounding padding; no performance optimization was performed.
- Metrics: one GLB load, four shared source geometries, **79,884 furniture triangles** and 18 wall triangles. One measured setup was **412.2 ms**; this is not an FPS or device-performance claim.
- Browser-only GLB fault injection in a separate session blocked one request: state `partial`, zero textured objects, three placeholders, nine wall panels retained. No repository asset was removed or changed.
- Normal session console: **0 errors**, one existing Plotly Canvas2D readback advisory. Expected injected request failure was isolated from the normal-session result. A preliminary server-restart connection error was discarded by starting a fresh browser session before these observations.

Screenshots were saved and visually inspected outside the repository at `/Users/macbook/Hack/.playwright-mcp/archimind-real-data-audit-20261028/`: `desktop-room.png`, `mobile-room.png`, `mobile-cutaway.png`, `missing-asset.png`. They are local evidence, not tracked deliverables or portable GitHub links.

No full datasets, new furniture meshes, external textures, paid requests or Codex subprocess invocations were used. Kaggle content details, individual alternative assets and manufacturer-size agreement remain explicitly unverified. Source/wheel asset expansion was not tested because no expansion was implemented; existing packaging tests and prior documented checks are not a new multi-asset packaging proof.

## 13. Final go/no-go recommendation

**GO:** 08A source qualification, then a curated, local, zero-rotation real-furniture MVP with canonical geometry unchanged and safe placeholders. **NO-GO:** public FRONT/FUTURE asset hosting, arbitrary real-room ingestion or dataset-grounded generation on the present evidence.

The smallest useful improvement is a qualified set of real-size furniture assets rendered in actual selected candidates. Qualification and viewer synchronization are prerequisites. Retain deterministic approval, keep AI optional, and measure planning usefulness separately from image quality. Stop after these audit documents for owner review; none of tasks 08A–08G has been implemented here.
