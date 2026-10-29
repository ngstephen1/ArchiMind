# Catalog selection and explicit generation (08E)

The existing generation workflow can now reserve one Charles armchair and one
five-shelf bookcase using the two qualified ABO metadata records. This is a small
curated catalog, not a dataset-wide importer, retrieval index or new AI agent.

## User workflow

**Procedural bedroom** remains the default under **Specification for next
generation**. Its Generate Layouts action is unchanged. **Catalog selection**
opens **Real Furniture Catalog**: keep/remove the procedural bed, desk and
wardrobe (initially checked), and optionally add either catalog product (initially
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

“Verified” retains 08A's meaning: checked published product claims, not independent
physical measurements. Full precision, original inch values, axis evidence and
source/license links are in the technical details. Planning dimensions are
reservations, not revised manufacturer claims or extra circulation allowances.
If Charles's Policy B evidence is unavailable, preparation is disabled for that
product; the smaller published box is never substituted. Render approval comes
from the existing current release, separately from historical catalog flags.

The bookcase is a bookcase, not a wardrobe. Plotly gives it the existing generic
storage solid; Three.js gives it a correctly sized, named placeholder. “Sod” and
“Espresso” remain variant labels, not qualified colors/materials. Existing source
catalog, search documents, qualification receipts, GLBs and releases are unchanged.
CC BY 4.0 attribution/source notices remain mandatory; product provenance is not
an endorsement or a new rights determination.

## Preparation API and provenance

`archimind.assets.specifications` (also exported from `archimind.assets`) provides:

- `catalog_product_options()`: immutable, sorted catalog records plus current
  planning/render status, evidence digests and preparation availability.
- `prepare_catalog_specification(base_design, *, retained_manual_ids, product_ids)`:
  a frozen `PreparedCatalogSpecification` with serialized canonical input,
  immutable assignments/sidecars and base/evidence/input fingerprints.
- `specification_is_current(...)`: schema/evidence comparison with current inputs;
  no generator or spatial-engine call.

`prepared.design()` creates a fresh input, not another authoritative selected
layout. Retained manual furniture keeps its identity, dimensions and input pose.
New product IDs are `catalog:{asset_id}:1`; compact names are `Armchair (Sod)` and
`Bookcase (Espresso)`. Their initial `(0, 0)` positions are unvalidated inputs;
only explicit generation chooses positions. Rooms and openings are preserved.
Unknown/duplicate selections, ID collisions and nonzero rotations are rejected.

`ProductAssignment` binds each generated furniture identity/category/dimensions
to catalog/record versions and digest, product/variant, reviewed name, source,
license and dimension basis. It is provenance, not an alternative catalog or mesh
approval. Charles uses `furniture_from_planning_envelope()`; the bookcase uses
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
current compatible Charles evidence offer **Approved product mesh** or
**Procedural placeholder**. Other items have read-only placeholder diagnostics.
Choices persist through A/B/view changes and reset on generation replacement;
they cannot promote a generic chair or metadata-only bookcase. They do not change
geometry, validation, scores or styling metadata. A/B camera preservation and reset
behavior are inherited from 08D. Three.js retains original asset appearances;
reviewed styling colors remain a Plotly preview.

## Verification and limits

See [the 08E receipt](../data/CATALOG_GENERATION_08E_VERIFICATION.json) for exact
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

Only two products and one real mesh are supported; no bed/desk/wardrobe product
assets were acquired. Geometry/rotation limitations, bounded search and heuristic
scores remain unchanged. No new asset, dependency, renderer, live AI call,
embedding or larger-source ingestion is introduced. Stop after 08E for review.
