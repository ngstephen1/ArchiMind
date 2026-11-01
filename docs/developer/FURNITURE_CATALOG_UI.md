# Catalog selection and explicit generation (08E / 08F2)

> Current through 08F3A-R3B5 (November 1, 2026): Belaya preparation, same-session regeneration and synchronized native rendering passed browser acceptance. Historical storage stops remain in the qualification report; final R3C release acceptance remains separate.

The existing generation workflow supports one instance of each of five qualified
ABO metadata records. Catalog release 1.1.0 adds Belaya, Morava and the nightstand;
Charles and the bookcase retain their original record bodies and measurements.
This is a small curated catalog, not a dataset-wide importer, retrieval index or new AI agent.

## User workflow

**Procedural bedroom** remains the default under **Specification for next
generation**. Its Generate Layouts action is unchanged. **Catalog selection**
opens **Real Furniture Catalog**: keep/remove the procedural bed, desk and
wardrobe (initially checked), and optionally add any catalog product (initially
unchecked). There is no automatic category substitution.

Use **Select → Prepare new specification → Review → Generate Layouts**. Preparing
checks schema and packaged evidence only; it performs no layout generation or
spatial validation. Review shows retained/removed items, product identities,
dimension basis and sizes. Generate is the explicit confirmation; there is no
additional consent checkbox. Empty reviewed inputs are allowed: the existing
engine can find only one distinct empty arrangement, so its request for two
alternatives returns an honest partial/search-exhausted outcome.

Changing selections, the base design or qualification evidence makes a prepared
bundle stale; prepare again. Seed edits do not. Pending choices are retained when
the catalog section is hidden or temporarily unavailable. They never modify the
currently displayed candidates. Next-specification review and current-generation
provenance have separate labels.

## Dimensions and qualification

| Product | Published W × D × H, meters | Generation reservation | Three.js |
| --- | --- | --- | --- |
| Charles armchair, Sod / B075X2X4XS | 0.9906 × 0.9906 × 0.9652 | Policy B: 0.996104896068573 × 1.0019413232803345 × 0.9760930538177491 | Approved native-scale mesh, with current explicit sidecar/release |
| Five-shelf bookcase, Espresso / B07PQS58XN | 0.659892 × 0.381762 × 1.891792 | Published item dimensions, unchanged | Named storage placeholder; no bookcase model acquired |
| Belaya writing desk, Oak / B074L4976T | 1.6 × 0.8 × 0.75 | Policy B: 1.6 × 0.8018731772899628 × 0.7516312003135682 | Native-scale Belaya mesh with current sidecar/release; mixed Charles/Belaya scenes use placeholders |
| Morava wardrobe, Oak Sonoma / B07H8JN9QF | 2.0 × 0.59 × 2.12 | Published item dimensions; no approved envelope | Named wardrobe placeholder |
| Rivet nightstand, Brown / B07B4VXXJC | 0.6096 × 0.4318 × 0.6096 | Published item dimensions; no approved envelope | Named bedside-table placeholder |

“Verified” retains 08A's meaning: checked published product claims, not independent
physical measurements. Full precision, original inch/centimeter values, axis
evidence and source/license links are in the technical details. Planning dimensions are
reservations, not revised manufacturer claims or extra circulation allowances.
If Charles's or Belaya's Policy B evidence is unavailable, preparation is disabled for that
product; the smaller published box is never substituted. Render approval comes
from the existing current release, separately from historical catalog flags.

The bookcase is a bookcase, not a wardrobe. Plotly gives it the existing generic
storage solid; Three.js gives it a correctly sized, named placeholder. “Sod”,
“Espresso”, “Oak”, “Oak Sonoma” and “Brown” remain variant labels, not qualified
colors/materials. Existing two-product records/search text, source qualification
receipts, GLBs and render releases are unchanged. New records have new deterministic
search documents; unknown descriptions and material/style/color fields stay null.
CC BY 4.0 attribution/source notices remain mandatory; product provenance is not
an endorsement or a new rights determination.

## Preparation API and provenance

`archimind.assets.specifications` (also exported from `archimind.assets`) provides:

- `catalog_product_options()`: immutable, sorted active catalog records plus current
  planning/render status, evidence digests and preparation availability.
- `prepare_catalog_specification(base_design, *, retained_manual_ids, product_ids)`:
  a frozen `PreparedCatalogSpecification` with serialized canonical input,
  immutable assignments/sidecars and base/evidence/input fingerprints.
- `specification_is_current(...)`: schema/evidence comparison with current inputs;
  no generator or spatial-engine call.

`prepared.design()` creates a fresh input, not another authoritative selected
layout. Retained manual furniture keeps its identity, dimensions and input pose.
New product IDs are `catalog:{asset_id}:1`; compact names use the reviewed subtype
and variant, for example `Armchair (Sod)` and `Wardrobe (Oak Sonoma)`. Their initial
`(0, 0)` positions are unvalidated inputs;
only explicit generation chooses positions. Rooms and openings are preserved.
Unknown/duplicate selections, ID collisions and nonzero rotations are rejected.

`ProductAssignment` binds each generated furniture identity/category/dimensions
to catalog/record versions and digest, product/variant, reviewed name, source,
license and dimension basis. It is provenance, not an alternative catalog or mesh
approval. Charles and Belaya use `furniture_from_planning_envelope()`; the other three use
`furniture_from_catalog()`. Future retrieval must return these qualified asset IDs
and resolve them through the authoritative catalog/preparation checks. No embedding
or vector index is created here.

## Generation, styling and rendering state

Every normal returned generation outcome stores the exact submitted source JSON,
assignments and validated sidecars in `GenerationRenderSnapshot`, together with
its generation digest and session-local revision. Even identical-seed regeneration
increments the revision. Exceptions keep the previous result, selection, snapshot,
render choices and styling. Normal responses replace them, including unsupported,
infeasible, exhausted and zero-candidate responses. No old successful layout is
silently substituted for a normal failed outcome.

Styling reads the stored submitted specification, not pending controls or a seed
edit. Pending edits and preparation preserve matching styling. Existing A/B and
successful-replacement styling invalidation/authorization rules remain intact.
An explicitly requested styling check still rejects altered candidate geometry or
reports. Rendering uses the exact original stored selected `candidate.design`.

Plotly remains the default. Three.js uses the unchanged V3 contract, native-scale
placement, resource limits, integrity checks and pool/lifecycle. Only items with
current compatible Charles or Belaya evidence offer **Approved product mesh** or
**Procedural placeholder**. Other items have read-only placeholder diagnostics.
Choices persist through A/B/view changes and reset on generation replacement;
they cannot promote a generic chair or any metadata-only product. They do not change
geometry, validation, scores or styling metadata. A/B camera preservation and reset
behavior are inherited from 08D. Three.js retains original asset appearances;
reviewed styling colors remain a Plotly preview.

## Verification and limits

The [historical 08E receipt](../data/CATALOG_GENERATION_08E_VERIFICATION.json) records
commands, counts, hashes, screenshots and CI checkpoints. Tests block live providers,
external networking and process dispatch in deterministic cases; offline packaging
and controlled local HTTP browser fixtures are separate checks. Installed-wheel
coverage loads preparation APIs outside the repository and verifies original asset
bytes and metadata resources remain packaged.

Desktop Chromium (1440 × 1000) and resized Chromium (390 × 844) inspections cover
procedural/catalog generation, mixed layouts, pending edits, A/B/view switches,
native scale, camera persistence, placeholders and recovery. Missing/corrupt asset
responses are intercepted browser fixtures. Generation-exception/zero-result checks
use a temporary local harness, not a production fault switch. These checks are not
physical-phone testing, sustained performance measurements or architectural/code
certification. Screenshots remain outside Git.

08F2 supports five metadata products and one real mesh. No new model was acquired.
The [08F2 report](../data/FURNITURE_CATALOG_ADMISSION_08F2.md) records new desktop/
narrow checks, installed-wheel loading, three-item and mixed generation, frozen
historical replay and exact test counts. Those new browser checks do not repeat
the historical forced-corruption scenarios above. Geometry/rotation limitations,
bounded search and heuristic scores remain unchanged. No new asset, dependency,
renderer, live AI call or embedding is introduced.

`load_catalog(version="1.0.0")` and `catalog_product_options(catalog_version="1.0.0")`
are fixed historical reads. Fresh preparation always validates against the active
1.1.0 catalog; old research hits cannot authorize application preparation. The
Charles envelope still binds its original release and must also match the unchanged
active product. No reported mesh extent can qualify a new envelope or resize an
existing candidate. Stop after 08F2 for review.

## 08F3A-R2 application boundary

New Belaya selections use the pinned Policy B reservation and sidecar through the
existing explicit Prepare/Review/Generate boundary. Pending edits never migrate
stored candidates. Source measurements and catalog flags remain historical; the
separate planning/render releases govern new reservations and meshes. Mixed
Charles/Belaya bindings yield `mixed_scene_not_yet_qualified` for both products,
even though the texture estimate is eight bytes below 128 MiB. No generator,
validator, scoring, retrieval algorithm, asset, or resource-budget change is made
by R2. Final acceptance is recorded in the Belaya qualification report.


## R3B5 acceptance and viewer-state boundaries

The actual app completed two explicit Generate clicks in the same session: revision
1 → 2, generator calls 1 → 2, and UI acceptance checks 2 → 4. Seed 42 reproduced
the same two passing Belaya layouts in five attempts; a fresh result object was
stored. Plotly and Three.js received the exact selected candidate, and native
Belaya scale remained 1.0. Pending edits invalidated preparation without replacing
results; visible reprepare restored readiness with no third generation.

Three.js camera/target and front-wall/footprint toggles persist within the same
room and DOM owner across A/B changes. The generation-keyed parent supports host
replacement through owner-scoped WeakMap snapshots; obsolete cleanup cannot
overwrite a replacement. A new generation, closed/reopened view, or different DOM
owner resets framing. Restoring a pending selection can replace that owner and
reset view controls while leaving all stored results intact. Actual A/B continuity
passed; same-owner host replacement retains its deterministic regression evidence.

See [R3B5 evidence](../data/ASSET_QUALIFICATION_BELAYA_08F3A.md#r3b5--final-same-session-browser-regeneration-acceptance).
No physical-mobile, universal leak-freedom or total GPU-memory claim follows. Mixed
Charles/Belaya native scenes remain unqualified and use placeholders. Production
semantic retrieval, new assets and further qualification are outside this checkpoint.
