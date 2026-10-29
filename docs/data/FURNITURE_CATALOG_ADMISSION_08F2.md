# Metadata catalog admission — Task 08F2

**Three products admitted as metadata only. Active catalog: 1.1.0, schema 2.**
Observed October 29, 2026. Baseline:
`4052e1a4bf8d8919a34da249b356d9e4dec5296f`. The owner authorized metadata admission
from the unchanged 08F1 evidence. There are now **five metadata-qualified products**;
Charles remains the only product with approved planning and rendering evidence.
No GLB, texture, image, encoder, embedding service or database was acquired.

## Admission decisions and authoritative evidence

| Product / stable asset ID | Original type → canonical category / subtype | Published W × D × H, m | Original whole-item measurements | Decision |
| --- | --- | --- | --- | --- |
| Belaya, Oak — `abo-b074l4976t-amazon-co-uk` | DESK → desk / writing desk | 1.6 × 0.8 × 0.75 | width 160, length 80, height 75 cm | Metadata admitted |
| Morava, Oak Sonoma — `abo-b07h8jn9qf-amazon-co-uk` | CABINET → wardrobe / wardrobe | 2.0 × 0.59 × 2.12 | length 200, width 59, height 212 cm | Metadata admitted |
| Rivet, Brown — `abo-b07b4vxxjc-amazon-com` | TABLE → table / nightstand | 0.6096 × 0.4318 × 0.6096 | width 24, length 17, height 24 inches | Metadata admitted |

The exact IDs, marketplace, variants and manufacturer models are respectively
**B074L4976T / amazon.co.uk / T80505PL05LVO**, **B07H8JN9QF / amazon.co.uk /
M4-R3181/R3181-20**, and **B07B4VXXJC / amazon.com / 320-C070-052**. Belaya and Morava
use complete listing lines 1065 and 1852 in the recorded bounded
[official part-6 metadata response](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz);
the nightstand uses line 110 in
[part 3](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz).
These are links identifying the preserved evidence, not downloads made by 08F2.

Each entry binds the source register's SHA-256 and qualification revision, original
listing-line and compressed-response hashes, model-index hash, title, manufacturer
number and exact product/model join. The accompanying [JSON receipt](FURNITURE_CATALOG_ADMISSION_08F2.json)
records these bindings and new record/search digests. The source revision remains
unknown (`null`), distinct from the known ArchiMind qualification commit.
The 08F1 excerpts were cross-checked against their reviewed candidate records;
no new website research or fresh model-size observation is claimed.

Whole-item fields use Decimal conversions: cm × 0.01; inches × 0.0254. Morava's
source `length` is its frontage and `width` is depth. Published claims are not
independent physical measurements or inspected mesh bounds. Its reported mesh
height of approximately 2.15871644 m does not replace the published 2.12 m.
No individual metadata-admission blocker remains for these three exact variants.

Rights retain the reviewed [ABO CC BY 4.0 grant](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt):
attribution, license/change notices, preserved notices and no endorsement.
This is not a new chain-of-title, trademark or embedded-logo inspection.
Original marketing titles remain provenance. “Oak”, “Oak Sonoma” and “Brown” are
variant labels, not qualified physical materials/colors/styles. Descriptions and
all such qualified attributes remain null; the 08F2 subtype contract rejects their
promotion without a separately reviewed extension.

## Version and compatibility strategy

`load_catalog()` and `load_catalog(version="1.1.0")` load the fixed active resource.
`load_catalog(version="1.0.0")` loads the **byte-identical original** packaged
`assets/furniture_catalog_1_0_0.json`, SHA-256
`c1116a65558b2781f1ac979920dbd0b0b683dfdcc314681a70d8639ed87880dd`.
Both releases have fixed resource/hash checks; paths, URLs and unknown releases
are rejected with sanitized errors. There is no runtime source-register ingestion.

Schema 1 retains its original CHAIR/armchair and SHELF/bookcase scope. Schema 2
adds the three reviewed mappings above and requires release 1.1.0. All record
versions remain 1.0.0: the two existing bodies are identical, and each new record
is its first release. Search-document version 1 and its fixed field order remain;
the two original texts/digests are unchanged and each new product has its own digest.
Unsupported types, display-cabinet/wardrobe substitution, dining-table/desk
substitution, duplicate identities and contradictory unit/axis evidence fail.

Charles's existing envelope continues to validate against its original catalog
release **and** the identical active record. A changed current product record
invalidates that proof. Its receipt, placement transform, native scale 1.0, GLB,
render release and registry remain unchanged. Rebuilding the existing Policy B
proof uses its original release; newly admitted metadata cannot manufacture one.

## Fresh specifications and UI

The existing 08E controls discover all five records from the catalog. No product
facts are copied into a second UI catalog. New products use
`furniture_from_catalog()`, their published measurements and yaw zero. Immutable
`ProductAssignment` records retain asset/catalog versions, record hashes, exact
identity, dimensions and source/license references. Charles retains its separate
planning-envelope factory; the bookcase remains generic storage, not a wardrobe.

The flow remains **Select → Prepare → Review → Generate Layouts**. Pending choices
or preparation do not alter existing A/B results. Successful returned generation
outcomes replace the stored specification; exceptions preserve it. Rendering and
styling still read the exact stored candidate and source, not pending controls.
The UI explicitly says an approved planning envelope is unavailable for the four
metadata-only products. Their selected-view provenance uses the actual item name;
new desk/wardrobe/nightstand entries are never mislabeled as bookcases.

All three new products render as named procedural placeholders in Three.js. Plotly
uses its existing schematic desk/wardrobe/generic geometry. No product identity,
mesh availability or room suitability is inferred from those shapes. Canonical
models, generator, validators, scores and V3 renderer contracts are unchanged.

### Deterministic generation evidence

Unchanged 5 × 4 × 2.7 m bedroom, door/window, seed 42, 500-attempt budget:

| Fresh specification | Outcome | Attempts | Selected-candidate scores |
| --- | --- | ---: | --- |
| Belaya + Morava + nightstand | Two valid alternatives | 8 | 79.203287; 78.296791 |
| Same three + Charles + procedural queen bed | Two valid alternatives | 102 | 56.447838; 17.139016 |

Repeated results match exactly; validators pass and original saved designs/reports/
scores are unchanged. Scores are existing heuristics, not architectural or ergonomic
certification. No arbitrary room-fit or clothing-capacity claim follows.

## Retrieval and human-review boundaries

The active in-memory lexical corpus now has five records and a new identity;
construction remains an explicit backend call, with no retrieval UI or automatic
embedding rebuild. Old lexical/vector snapshots fail current authority checks,
including empty results. Old vectors cannot be loaded against the new corpus.
Source research entries outside the admitted five remain unavailable.

Frozen 08R0/08R1 queries, judgments, policy receipts and result signatures remain
byte-identical. Explicit historical providers use the exact original two-product
catalog and pinned qualification/index identity. They have no global version switch;
current `resolve_result()` rejects their outputs. The historical resolver explicitly
rejects preparation intent. New corpus effectiveness has **not** been measured.

For offline lexical replay only:

```bash
.venv/bin/python scripts/evaluate_furniture_retrieval.py --historical --output /tmp/08f2-new-replay.json
```

Use a new output path. Omitting `--historical` rejects the old benchmark as stale.
The existing embedding experiment CLI likewise requires explicit `--historical`
for old two-product replay; **no real encoder was run in 08F2**. Fixed-vector tests
exercise historical semantic/hybrid and stale-index boundaries without an SDK/model.
Historical lexical replay reproduces semantic signature
`6063a66e344188f60f2469453c19b3d21fd7a44ef4bb99b99c89b81bd3b34d31`.

The 24-prompt 08F1 packet is unchanged, pending and unevaluated, with zero human
judgments. Its “current” column means historical catalog 1.0.0. A future owner review
should explicitly choose a **new 1.1.0 snapshot** and revisit the former prospective
column under that scope. This report proposes that boundary; it adds no labels,
benchmark, threshold tuning or relevance-admission claim.

## Preservation and verification

The receipt binds all frozen research/asset files plus explicit before/after hashes
for authorized implementation migrations. 08F1's historical preservation receipt
is unchanged; its regression now checks declared migration pairs separately from
unchanged pins. All original test cases are retained, with release-dependent
expectations versioned or updated to the five-row active corpus.

Checkpoint 1: **1,803 Python tests in 119.61s**, 134 focused tests; commit
`0a2fd8c54331489a3720caeca24cbf774aa757fb`,
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/40954559708).
Checkpoint 2: **1,816 Python tests in 141.50s**, including final admission hardening. Final release counts,
packaging, browser receipts and delivery status are recorded at release below.
Frontend **75 passed**; syntax/build/bundle equality, Ruff, dependency checks,
registry and health passed. Real offline packaging/isolated-install checks are
part of the full suite. All unit retrieval calls use inert fixed vectors; no live
AI, model download or Codex subprocess is involved.

## Next separately authorized task

Belaya is the best first **individual** GLB acquisition/qualification candidate;
Morava and the nightstand may follow after their own evidence review. Retrieve no
model under 08F2. Each needs exact received-byte hashing, bounded static-geometry/
material inspection, native axes/anchor confirmation, strict containment or an
explicit approved planning-envelope decision, and desktop/narrow visual review.

Keep all limits: 15 MiB/asset, 50 MiB unique scene bytes, 100,000 triangles/asset,
300,000 instantiated triangles, 2048 px textures and 128 MiB unique decoded texture
memory. The three source estimates total **192 MiB**, so this shortlist does not
approve a combined detailed scene. No budget increase, fit-to-box scaling or
texture downsampling is introduced. Bed coverage remains unresolved. Stop at 08F2.
