# Furniture source expansion and review preparation — Task 08F1

**Source qualification complete; human review pending; active catalog unchanged.**
Checked 2026-10-29. Baseline `5f7ee20b685a06511d9ea89aea67f1839c131d6e`.
Target: a noncommercial public demo that delivers asset bytes to browsers.

This task researched sources and prepared review material. It downloaded **no
furniture model, texture, image, asset collection or encoder**, ran no embedding
experiment and changed no application behavior. The [structured receipt](FURNITURE_EXPANSION_08F1.json)
contains all 30 assessments, primary record excerpts, exact response/record hashes,
model-index joins, HEAD measurements, rights evidence, unknowns and preservation pins.
The [source register](FURNITURE_SOURCE_REGISTER.md) retains the original 08A report
and appends the new findings.

## A. Source coverage and honest denominators

| Group | Detailed reviews in 08F1 | New IDs | Revisited IDs | Eligible for acquisition | Needs evidence | Excluded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bed | 8 | 5 | 3 | 0 | 8 | 0 |
| Desk | 8 | 6 | 2 | 1 | 4 | 3 |
| Wardrobe / dresser leads | 8 | 8 | 0 | 1 | 2 | 5 |
| Additional furniture | 6 | 6 | 0 | 1 | 5 | 0 |
| **Total** | **30** | **25** | **5** | **3** | **19** | **8** |

Eight wardrobe/dresser investigations include six actual wardrobe leads, one
inconsistent display-cabinet lead and one dresser with conflicting titles. The
additional group contains two nightstands, two reading-chair leads, an office
chair and a filing cabinet. No bookcase or display cabinet counts as a wardrobe.

The cumulative register now contains **57 records**: **5 stored acquisition
eligibility decisions, 37 needs-evidence, 14 excluded and 1 illustrative fixture**.
Those counts retain historical decisions; they do not mean five newly approved
assets. Five historical records were revisited, with identical source record-line
hashes and unchanged unresolved outcomes. All **32 historical candidate records**
remain unchanged. Twenty-five genuinely new IDs were added.

The 08A JSON is frozen verbatim at
`data/catalogs/furniture_source_candidates_08a.json`, **260,796 bytes**, SHA-256
`cb3d5b7a7382a31ec96ec709f4fdcf6f90d9202275fe41f40c04391dc53ddc5d`.
The original catalog provenance test now checks this exact frozen file while
retaining its two-product, dimensions, revision and hash assertions. New validation
checks the expanded research register separately. No packaged qualification pin
was rewritten to match an expanded file.

### Qualification stages remain separate

| Stage | Existing active products | New products approved by 08F1 |
| --- | ---: | ---: |
| Packaged metadata-qualified | 2 | 0 |
| Planning-envelope-qualified | 1 (Charles) | 0 |
| Render-qualified product mesh | 1 (Charles) | 0 |
| New source/acquisition shortlist | Not an active-catalog stage | 3 source leads only |

Sheen Chair remains an illustrative non-product fixture. Charles and the Espresso
bookcase remain the only packaged products. The older bookcase acquisition decision
is preserved historically; its known 4096 px texture obstacle has not been fixed.

## B. Best new candidates and public-hosting rights

| Priority | Product / exact identity | Source variant / manufacturer model | Primary listing locator |
| --- | --- | --- | --- |
| 1 | Movian Belaya desk — `abo-b074l4976t-amazon-co-uk` / B074L4976T | Oak; title says Light Brown Oak-Effect / T80505PL05LVO | [part 6](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz), line 1065 |
| 2 | Movian Morava four-door/two-drawer wardrobe — `abo-b07h8jn9qf-amazon-co-uk` / B07H8JN9QF | Oak Sonoma; title says Light Brown Oak-Effect / M4-R3181/R3181-20 | [part 6](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz), line 1852 |
| 3 | Rivet two-drawer nightstand — `abo-b07b4vxxjc-amazon-com` / B07B4VXXJC | Brown / 320-C070-052 | [part 3](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz), line 110 |

Each listing's `3dmodel_id` joins the same official model-index ID and path. Source
product/model identity, variant context, whole-item dimensions and copyright grant
were reviewed separately; the join alone is not certification.

The official [ABO release](https://amazon-berkeley-objects.s3.amazonaws.com/index.html),
[license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt),
[listing schema](https://amazon-berkeley-objects.s3.amazonaws.com/listings/README.md)
and [model conventions](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md)
support the recorded CC BY 4.0 dataset grant. Public copying/browser delivery is
conditional on attribution, license links, preserved notices and change notices;
it must not imply endorsement or impose incompatible restrictions. Reuse the ABO
credit and contributor attribution retained in the source register. No independent
chain-of-title, trademark clearance or manufacturer endorsement is claimed. Current
retailer availability and an exact dataset release revision remain unverified.

### Alternatives and exclusions

- [Poly Haven](https://polyhaven.com/license): CC0 asset declaration, separate
  website rights and scraping restrictions. Its [API terms](https://raw.githubusercontent.com/Poly-Haven/Public-API/master/ToS.md)
  treat API access as separate acceptance. No API call, asset harvest or agreement
  acceptance occurred. No model-specific real-product dimensions were established.
- [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit): official page
  declares CC0, 140 3D files and release 1.0 (2018). It does not establish a
  manufacturer product, exact model identity or item measurements. No archive or
  model was retrieved. Collection tags are not dimensions or desk/wardrobe evidence.
- FRONT/FUTURE public delivery remains blocked without authoritative additional
  permission resolving the historical restrictions. No mirror label overrides them.

These two CC0 checks are source-level investigations, not extra individual product
reviews. No illustrative model is promoted into a real product to fill a category.

## C. Dimensions, resources and unresolved native placement

| Product | Published W × D × H, m | Original item fields / justified mapping | HEAD size | Reported triangles / texture max |
| --- | --- | --- | ---: | --- |
| Belaya desk | 1.6 × .8 × .75 | Width 160 cm → W; length 80 cm → D; height 75 cm → H; title and same-ID reported X/Y/Z corroborate axes | 3,135,676 B | 812 / 2048 px |
| Morava wardrobe | 2.0 × .59 × 2.12 | Length 200 cm → W; width 59 cm → D; height 212 cm → H; title/bullet/item/model comparison | 2,362,880 B | 1,460 / 2048 px |
| Rivet nightstand | .6096 × .4318 × .6096 | Explicit 24W × 17D × 24H inches; matching item fields; exact inch factor .0254 m | 1,298,676 B | 6,388 / 2048 px |

“Verified dimensions” means **checked published item claims and axis evidence**,
not independent physical measurements. Source fields and exact Decimal conversion
inputs are preserved. Shipping/package measurements were never substituted.
Seventeen of the 30 reviewed records have a defensible published-dimension contract;
13 remain unresolved. That is not 17 qualified models: identity, resource and native
mesh agreement are separate gates.

All three shortlisted records report one mesh/material and three 2048-square
images. A conservative RGBA+mipmap estimate using those reported maxima is
**67,108,864 bytes per asset**, not observed decoded memory. Actual image decoding,
materials, shared resources, extensions and aggregate scene budgets are unverified.
All three distinct assets together would estimate **201,326,592 bytes (192 MiB)**,
above the **134,217,728-byte (128 MiB)** scene limit. They are individual acquisition
leads, not an approved combined scene; actual resource review may limit concurrent
models. No texture conversion or resource-budget increase is authorized here.

| Product | Reported native X × Y × Z, m | Specific future issue |
| --- | --- | --- |
| Belaya | 1.599999905 × .751631200 × .801873177 | Depth/height slightly exceed published box; strict containment is not established |
| Morava | 1.998472214 × 2.158716440 × .598133087 | Height exceeds published 2.12 m by .038716440 m; depth exceeds .59 m by .008133087 m |
| Nightstand | .604509503 × .611116171 × .427476466 | Height slightly exceeds published .6096 m |

They pass the source-screen agreement rule **max(.01 m, 2% per axis)** using
reported model-index extents. None is certified to satisfy the **1e-6 m strict
planning-envelope containment** rule. Any future Policy B reservation requires
actual, version-bound inspection and review; do not fit/shrink a product to its
published box or create an envelope from published dimensions alone.

Source conventions say glTF meters, +Y up, natural front +Z and floor-standing
X/Z centering with bottom Y=0. These are not per-file transform/anchor observations.
Actual GLB hashes, min/max bounds, static pose, orientation, placement anchor,
extensions, embedded resources, material appearance and browser behavior remain
**unknown**. Model ETags are retained as HTTP metadata, never as SHA-256.

### Important unresolved findings

- No bed qualifies. Queen/King Tisbury variants have incompatible shared extents;
  Prudence Queen depth exceeds the 2% screen, Prudence King width is inconsistent,
  the Twin frame envelope disagrees substantially, and the upholstered King has
  conflicting whole-item dimension sets. The headboard bed's 14-inch frame height
  still does not establish its overall height.
- English Stark dresser text conflicts with multiple localized Queen-bed titles.
  Attractive dimensions and a small model do not resolve product identity.
- Moselle B07H8T8ZS7 is a localized Vitrine/display cabinet with inconsistent
  dimensions; it cannot fill clothing-wardrobe coverage.
- Twelve reviewed records report 4096 px textures and six exceed 15 MiB; counts
  overlap and include some unresolved records. Seven exclusions are resource-only;
  one is the display-cabinet/category exclusion. Other resource failures remain
  additional blockers on already unresolved identities/dimensions.

## D. Retrieval implications without an effectiveness claim

The three shortlist records supply potentially useful reviewed names, exact IDs,
source categories, variants, dimensions and use evidence. Future names should be
compact (for example “Movian Belaya desk”), while original marketing titles remain
provenance. Physical colors, materials, styles, descriptions, internal rails,
clearances and ergonomic/room suitability remain unqualified. Variant strings such
as Oak, Oak Sonoma and Brown do not establish physical finishes.

**No new record enters an embedding index or the active catalog here.** The current
catalog contract restricts source categories to CHAIR/SHELF and subtypes to
armchair/bookcase. A separately reviewed extension/version must precede admitting
DESK, CABINET/wardrobe or TABLE/nightstand. A schema change must not weaken identity,
license, axis/dimension or evidence rules. Existing search text, retrieval ranking,
index snapshots, thresholds and frozen 08R0/08R1 judgments remain unchanged.

A broader shortlist cannot establish better search or repair the 08R1 abstention
trade-off. No new encoder, lexical evaluation, semantic evaluation or production
08R2 flow was run. Existing deterministic reviewed preparation/generation remains
authoritative.

## E. Human evaluation preparation

The [owner-first review packet](FURNITURE_RETRIEVAL_HUMAN_REVIEW_08F1.md) contains
**24 fresh machine-authored prompts**: 12 current-application and 12 prospective
coverage discussions. It provides two active-product cards and three prospective
source cards, with source links, dimensions, qualification limits and a rubric.
There are no ranking scores, suggested relevance answers or fabricated reviewers.

All reviewer identity/role, date, eligibility, relevance, outcome, rationale and
adjudication fields are **blank**. Completed independent human reviews: **0**.
A second reviewer is optional; disagreements and any real final adjudication must
be retained. Hard eligibility and semantic relevance are separate. Prospective
source leads remain ineligible for current application preparation even if a
reviewer finds their described function relevant.

Before any new benchmark: obtain actual owner/expert judgments, fix the exact
catalog/evidence scope and label mapping, adjudicate where needed, then freeze a
new artifact. This pending packet is not gold, training data, threshold tuning or
independent evidence. Original 08R0/08R1 benchmarks are not overwritten or reused
as editable review forms.

## F. Transfer, validation and preservation

**9,948,621 bytes** of metadata bodies were received under the **10,485,760-byte**
limit, with a maximum response of **1,048,576 bytes**. The 52 implementation requests
comprise five ABO documents/index files, ten 512 KiB listing prefixes, four 1 MiB
prefixes, 30 model HEAD requests and three alternative-source documents. Every
status/range, response-body hash, length, ETag, Last-Modified and retrieval time is
recorded in JSON. HEAD model body bytes: **0**. No HTML images/fonts/scripts were
followed, no API agreement was accepted and no unmetered browser/search retrieval
occurred. Git/CI control traffic is outside this metadata-body budget.

The small compressed metadata index contains 7,953 rows; only complete JSONL lines
from bounded prefixes were examined. Incomplete trailing records were discarded.
Detailed review count is 30 selected product/domain records; scanning metadata to
find leads is not claimed as thousands of product qualifications. The sample is
not exhaustive. Raw response prefixes remain outside Git; reproducibility locators,
hashes and explicitly partial source excerpts are in the receipt.

Validation checks strict JSON, duplicate IDs/keys, ordering/counts, old-record
preservation, rights/identity/variant evidence, Decimal conversions, stage boundaries
and no acquisition/promotion. Historical source qualification remains hash-bound to
the frozen copy; the old test's original assertions were preserved. **142 existing
production/frontend/catalog/dependency/frozen-evaluation files** are pinned and
unchanged; the receipt lists their SHA-256 values.

Pre-expansion suite: **1,754 passed in 126.73s**. Checkpoint 1: **1,773 passed in
139.19s**, focused catalog/source **104 passed**, and offline packaging **1 passed**.
Checkpoint 2 source/catalog/packaging coverage: **113 passed in 10.31s**.
Final full regression, health, frontend and packaging results will be added at the
release checkpoint. No new visual behavior exists; no new browser acceptance is
claimed. Existing renderer/Streamlit regressions still apply.

## G. Git delivery

Checkpoint 1: `5d194367b47906a1bcd5aececdd293dc5a99f587`,
[source expansion CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40870065472).
Checkpoints 2/3 and their actual CI outcomes are reported in the delivery response;
a document cannot contain its own future commit hash without changing that hash.
Only intended research data/docs, source-distribution metadata and focused tests
are staged. `.agents/`, `.claude/`, unrelated files and existing model bytes remain
untouched. No force-push or history rewrite is permitted.

## H. Recommended follow-up — separately authorized

1. Obtain owner review using the blank packet. Keep current/prospective scope
   distinct; do not evaluate or tune against unreviewed proposed judgments.
2. A narrow future **08F2 catalog-contract/metadata admission** is justified for
   Belaya, Morava and the nightstand after review. Preserve source/version snapshots
   and extend categories explicitly; it is not permission to change the catalog now.
3. After that contract supports the records, separately authorize individual asset
   qualification: **Belaya first**, **Morava second**, **nightstand third**. Inspect
   original bytes and native transforms/resources before any approved envelope or
   rendering binding. Morava particularly needs height/depth reconciliation.
4. Keep bed acquisition blocked until authoritative identity/dimension conflicts
   are resolved. Do not substitute a sofa-bed, display cabinet or generic collection
   model. No optimization tooling or new source acquisition is authorized here.

No 08F2, acquisition, new embeddings, production semantic retrieval or 08R2 work
was started. **Stop after 08F1 for review.**
