# Task 08C-R - dimension policy review and recovery decision

Date: October 28, 2026. Baseline: `2ec35f7a28ca40fd6560029c6f80fe6e294fa41e`,
synchronized with `origin/main` before work. This is a **review**, with no production
behavior change. [08C qualification](ASSET_QUALIFICATION_08C.md), its immutable
[receipt](ASSET_QUALIFICATION_08C.json), and the
[implementation plan](../audits/REAL_DATA_IMPLEMENTATION_PLAN.md) remain intact.
Exact arithmetic, topology, fresh source receipts and preservation evidence are
in the companion [comparison receipt](ASSET_DIMENSION_POLICY_REVIEW.json).

**Decision:** retain **Policy A** as the active gate. Recommend **Policy B**, a
separate conservative planning envelope for explicitly prepared new specifications,
only after a documented owner decision. Policy C is an optional calibrated-visual
exception requiring its own approval. Neither B nor C is authorized or implemented
by this review. No product is render-qualified and 08D remains blocked.

## 1. What causes the current rejection?

The verified cause is a difference between **referenced mesh geometry** and
**nominal published item dimensions**, not an observed inspector-calculation bug.
The underlying physical reason remains unknown. These are independent evidence
levels:

| Question | Verified finding | Limit of the finding |
| --- | --- | --- |
| Exact product/model/variant join | Archived Amazon listing part 7, line 242: ASIN and `3dmodel_id` both `B075X2X4XS`, manufacturer model `LTD26020C`, amazon.com, Sod; official index maps that ID to `S/B075X2X4XS.glb` | Dataset association is verified. The GLB has no embedded ASIN/variant certificate, and the physical chair has not been measured independently |
| Same configuration | English listing describes overall width/depth/height 39/39/38 inches and separately distinguishes a 23-inch seat depth; ordinary assembled armchair, with no alternate articulated state documented | No evidence authorizes a different cushion state, accessory removal or another SKU; actual product/model configuration equivalence is not independently certified |
| Hidden or unused geometry | One scene, node, mesh, opaque material and triangle primitive; every one of 23,412 positions is referenced; no unused geometry, alpha masking, skin, morph or animation | Topology cannot prove which surface is an upholstery detail, accessory or authoring artifact; no pixel/material visibility review was performed here |
| Authored transforms | Root translation zero, quaternion identity, scale `(1,1,1)`; positions already contain the reported size | No scene-graph scaling explains the mismatch. A scale baked into positions before export cannot be reconstructed from identity TRS; authoring history is unknown |
| Axes/anchor | glTF X is width, Y height, Z depth; native minimum Y is exactly zero; X center zero, Z center -0.00010657310485839844 m | Natural-front appearance remains visually unverified. Swapping equal published width/depth cannot fix the mismatch; translation cannot change extents |
| Authoritative resolution | Fresh listing record/hash and model-index dimensions agree with 08A/08B; no different authoritative Charles dimensions or error/correction notice established | No replacement physical measurement, manufacturer uncertainty interval or approved model correction exists |

### Primary evidence and its freshness

- [Listing schema](https://amazon-berkeley-objects.s3.amazonaws.com/listings/README.md)
  distinguishes item dimensions; this review uses no package/shipping dimensions.
- [Listing part 7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz):
  exact Charles line hash
  `f98a699bf5a8540b8e1fad18233bb94b940d21a617b7cb670768733c36bcb99a`.
  The fresh 196,608-byte compressed prefix and selected records match 08A/08B.
- [Official model index](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/metadata/3dmodels.csv.gz):
  existing local snapshot SHA-256
  `90d061c3e3efa555a55bfc8ed7fc55cdb322086397443de1b33e91f7924d7d92`.
  This snapshot was hash-checked, not newly downloaded or silently treated as a new
  release. Unknown upstream release revision remains unknown.
- [Model conventions](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md):
  fresh body matches SHA-256
  `01d8c8b2ea90ab30b29979f77e7550deccc4a2b981ee71d4f5ee3ffdb894db86`.
- [Original Charles GLB](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/original/S/B075X2X4XS.glb):
  reused the 08C quarantine file, **4,252,440 bytes**, SHA-256
  `62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645`.
  Fresh HEAD size/ETag agree; HEAD is not a new model-byte verification. The reused
  file's computed SHA-256 was checked before and after analysis. No new GLB GET,
  edit, re-export or derived model occurred.

Primary product/model searches did not establish an exact-ASIN Charles manual or
replacement size. Similarly named chairs from other manufacturers are not evidence
for this variant. This is a bounded negative finding, not proof no manual exists.

### Components and extrema

Independent index-graph analysis finds **39 vertex-index components**, reduced to
**12 components after exact-position welding**. UV/normal seams can split indices;
this welding is diagnostic, not a model edit. There are zero unreferenced positions
and zero exactly zero-area triangles. Every component has at least **1,586
triangles**, so the measured envelope is not set by a lone unused point or tiny
isolated triangle.

| Boundary | Exact-position component, sorted by face count | Triangles |
| --- | ---: | ---: |
| Minimum X | 1 | 9,958 |
| Maximum X | 0 | 9,958 |
| Maximum Y / height | 2 | 5,012 |
| Minimum Z / depth | 3 | 2,508 |
| Maximum Z / depth | 5 | 2,302 |

After the existing center/floor normalization, **66 X vertices**, **200 Y vertices**
and **226 Z vertices** lie outside their respective canonical intervals by more
than 1e-6 m. Those sets need not be disjoint. Their incident triangle counts are
188, 348 and 510 respectively. An opaque material and referenced triangles do not
prove every surface is externally visible, but they provide no justification to
trim components. Disconnected upholstery/leg-like forms may be intentional;
semantic part labels or the author's reference geometry are missing.

### Plausible rounding, without invented tolerances

Measured W/D/H in inches are approximately **39.21672819 / 39.44650879 /
38.42886039**. Each rounds to the published **39 / 39 / 38** whole inches. This is
consistent with rounded retail dimensions. It does **not** establish that the
publisher used nearest-inch rounding, that the mesh is physically accurate, or
that +/- half an inch is an authorized measurement tolerance. Upholstery state,
model construction and pre-export calibration are other unverified explanations.
The millimeter differences are far greater than float32 arithmetic roundoff.

## 2. Exact discrepancy and hypothetical uniform calibration

Inputs below use the **exact decoded float32 values**, not the six-decimal figures
in the task summary. Inch conversion is exactly 0.0254 m. Width/depth/height order
is distinct from native glTF X/Y/Z order.

| Dimension | Published m | Exact decoded extent m | Native excess mm | Excess relative to publication |
| --- | ---: | ---: | ---: | ---: |
| Width | 0.9906 | 0.996104896068572998046875 | 5.504896068573 | 0.555713312% |
| Depth | 0.9906 | 1.00194132328033447265625 | 11.341323280334 | 1.144894335% |
| Height | 0.9652 | 0.9760930538177490234375 | 10.893053817749 | 1.128579965% |

The original 2%/1 cm agreement gate passes; original 1e-6 m containment fails.
A fresh execution of the unmodified inspector returned **exit 2** and reproduced
**every field** of the 08C inspection, including the failed canonical-envelope gate.
No genuine inspection-calculation defect was found; no correction is proposed.

For a fixed centered-X/Z, floor-Y anchor, the **largest fitting scale** is:

```text
s* = min(published_width / mesh_width,
         published_depth / mesh_depth,
         published_height / mesh_height)

axis limits W/D/H = 0.99447357794314662748...
                    0.98868065123494136094...
                    0.98884014820601016455...

s* = 1731198976 / 1751019375
   = 0.988680651234941360942965008596778091...
```

This is the **minimum required reduction**, **1.1319348765058639...%**. There is no
smallest positive fitting factor: smaller scales also fit. Depth is the limiting
axis. This calculation does not inflate the box using the numeric tolerance.
Future floating-point implementation, if approved, must conservatively round the
factor and recheck transformed bounds; it must not round upward blindly.

| Hypothetical result | Width | Depth | Height |
| --- | ---: | ---: | ---: |
| Calibrated size m | 0.9848296373433903323 | 0.9906 | 0.9650443161144347703 |
| Calibrated minus published mm | -5.770362656609668 | 0 | -0.155683885565230 |
| Calibrated minus published percent | -0.5825118773% | 0 | -0.0161297022% |

It would leave about **2.885181 mm** on each width side and **0.155684 mm** above
the mesh, with depth exact. Uniform scaling preserves mesh proportions, but cannot
make all three measured dimensions equal the published triple: the three required
axis factors differ. Nonuniform stretching would conceal that disagreement and is
excluded.

The native bounds are
`(-0.4980524480342865, 0, -0.5010772347450256)` to
`(0.4980524480342865, 0.976093053817749, 0.5008640885353088)` m.
The unchanged normalizer adds `(0, 0, 0.00010657310485839844)`, with scale 1.
A **hypothetical** calibrated normalized box would instead have X
`+/-0.4924148186716951661`, Y `0..0.9650443161144347703`, Z `+/-0.4953`.
For Furniture at `(x,y)`, Three.js translation would be
`(x + 0.4953, 0, -(y + 0.4953))` after normalization/calibration. None of this
hypothetical scale or placement was applied, rendered or saved as an approved
binding. Source GLB hash remains original; derived GLB hash is **null**.

## 3. Policy A/B/C comparison

| Criterion | A: strict native containment | B: conservative planning envelope | C: explicit uniform visual calibration |
| --- | --- | --- | --- |
| Original GLB | Unchanged | Unchanged | Unchanged source; approved transform sidecar or separately authorized derivative |
| Published product facts | Retained | Retained separately from mesh/planning measurements | Retained; rendered dimensions explicitly differ |
| Charles outcome | Reject | Potential recovery for **new** specifications | Mathematically fits with s*, pending exception/visual approval |
| Spatial implication | Existing published box authoritative, model must fit | New geometric planning box encloses both the nominal product box and verified mesh | Existing geometry/report stays unchanged; calibrated appearance is approximate |
| Principal benefit | Simple, strict native fidelity gate | Conservative mesh containment without claiming new product measurements | Small fixed visual correction, preserves existing specification sizes |
| Principal cost | Can exclude legitimate models paired with rounded retail dimensions | New envelope provenance, factory semantics and fresh generation/validation required | Underrepresents native width after calibration; may hide model/measurement uncertainty if unlabeled |
| Architecture work | None for continued rejection | Versioned sidecar schema/factory contract; canonical class fields need not change | Versioned fixed render-calibration contract and separate product renderer path |
| Existing candidates | Preserved | Never enlarged, moved or revalidated implicitly | Never resized or moved; binding rejects wrong version/dimensions |
| Owner decision | Already active | **Required before implementation** | **Required for the exception and threshold** |

### B: recommended planning contract, not a new physical measurement

For the agreed fixed floor/center anchor, the minimal geometric union envelope is
`max(published_extent, verified_mesh_extent)` per axis. Charles would require:

```text
W = 0.996104896068572998046875 m
D = 1.00194132328033447265625 m
H = 0.9760930538177490234375 m
```

These are **planning extents based on observed digital geometry**, not corrected
manufacturer dimensions or a physical metrology claim. Any extra discretization,
uncertainty or functional-access padding requires a separately labeled rule; none
is added by this review. A planning box is not chair pull-out space, ergonomic
clearance or code compliance.

`models/furniture.py::Furniture` already accepts one positive metric rectangle and
height. `geometry/footprints.py::furniture_footprint` uses its width/depth at yaw
zero. Existing containment, overlap, door and circulation checks can therefore
consume a **new** specification with these geometric extents. Those checks remain
unchanged and authoritative for their implemented X/Y scope. They do not establish
height clearance, window conflicts, mounting safety or furniture-function access;
future specification qualification needs an explicit ceiling/suitability preflight.

The single canonical object cannot itself record both product facts and the basis
of a planning envelope. The current `assets/catalog.py::furniture_from_catalog`
expressly copies published measurements, and strict schema 1 rejects extra fields.
Changing that factory silently would violate 08B. A separate immutable envelope
record and an explicitly named opt-in factory are required, bound to catalog and
asset versions, source GLB hash, inspection/anchor/policy version and Furniture ID.
Historical catalog bytes, original factory results and stored layouts stay valid.
No canonical model-field or validator change is inherently needed, but this is a
**separately authorized schema/factory semantic change**, not a renderer workaround.

A later explicit generation request must use the larger specification, retain its
bindings and policy version, and obtain new reports/scores from the existing
engine. Only that new candidate may be rendered against that envelope. View
switches never alter an old candidate or trigger automatic generation. Before any
future UI exposure, product measurements and planning sizes must be labeled
separately; existing dimension captions cannot imply both are the same fact.

### C: a narrowly reviewable alternative, still prohibited today

If the owner prefers calibrated visualization, a possible **proposed** threshold is
`0.98 <= s <= 1` (at most 2% uniform shrink), with the unchanged agreement gate and
strict transformed containment. Charles's s* would pass that proposed limit, but
2% is an engineering choice, not evidence of physical accuracy or approval. Do not
confuse it with the existing per-axis acquisition agreement tolerance.

A future C contract would require exact per-asset approval, the fixed s*, all
original/derived bounds and errors, a calibration label, policy/version identity,
source hash and deterministic transform-manifest digest. No enlargement,
nonuniform stretch, per-room dynamic scale or arbitrary caller transform is
permitted. A sidecar-only transformation keeps original bytes/hash and records no
new GLB hash; a re-export would require separate authorization, new derivative
hashes and a new immutable render-record version. No source bytes/version may be
silently overwritten.

The existing `frontend/realistic_viewer/src/geometry.js::fitBounds` computes a
minimum dimension ratio dynamically, and `room_objects.js::fittedInstance` applies
it to **illustrative Sheen** instances. Mathematical similarity to s* does not
make this legacy mechanism an approved product calibration API. A product would
need a fixed trusted transform, exact catalog dimensions/version binding, decoded
post-transform bounds checks, honest labels and placeholders on mismatch. Legacy
Sheen behavior must remain separate. This review adds none of those capabilities.

## 4. Bookcase and other existing candidates

The source-qualified Espresso bookcase `B07PQS58XN` / `SH01-0606-008-SG-A05` remains
unacquired. Current HEAD still reports **11,661,068 bytes**, below 15 MiB. The
hash-checked historical model index reports W/D/H
`0.6603998316218093 / 0.3809882714048694 / 1.8922999968886094` m. Relative to current
ABO item claims, those differ by **+0.507832 / -0.773729 / +0.507997 mm**. Thus fixing
textures alone cannot be assumed to pass Policy A against the current catalog.
These are index comparisons, not newly measured GLB bounds.

### New primary evidence: manufacturer-distributed guide

The [Amazon-hosted guide](https://m.media-amazon.com/images/I/C1g%2B2SZdUKS.pdf)
lists the exact ASIN alongside two related variants on its cover. Pages 1, 2, 3,
4 and 30 were rendered locally and visually reviewed; page 3 gives W/H/D
**26 / 74.5 / 15 inches**, with **66 / 189 / 38.2 cm** alongside. Footer revision:
**V1-08/20**. Inch-derived W/D/H are **0.6604 / 0.381 / 1.8923 m**, enclosing the
reported index extents. This supports a nominal-unit/rounding explanation, but the
unit strings are not exact equivalents. The guide also distinguishes wall-anchored
and standalone configurations. Mesh configuration remains unverified. An explicit
source/precision decision must resolve these competing claims before changing any
catalog measurement; choosing the larger set merely because it fits is prohibited.

The 4,249,372-byte PDF has SHA-256
`521425b5d980a7559901e668fa2046eee868c41d57a5ed5ccddf6ed7d374ffba`.
It was read using five range responses of at most 1 MiB. Neither this manual nor
its pages are redistributed in Git, and the ABO model license is not presumed to
cover manufacturer documentation. Its metric/imperial claims remain separate in
the receipt. No older reseller-hosted manual or unrelated manufacturer drawing is
substituted for this primary document.

### Texture preparation feasibility, not permission to execute

The index reports three 4096-pixel images and 54,996 faces. Under the same RGBA/full
mipmap estimate, three distinct 4096-square textures require **268,435,452 bytes**,
exceeding 128 MiB. Three at 2048 square would require **67,108,860 bytes**. Estimated
memory falls fourfold, but future encoded GLB size, codec roles/extensions and
actual decoded memory still require inspection.

A deterministic preparation process is technically feasible under published
[ABO CC BY 4.0](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt)
and its [conditions](https://creativecommons.org/licenses/by/4.0/legalcode.en):
retain attribution/license notices and clearly identify modifications. This is
permission in the source copyright license, not owner authorization for this task
or independent trademark/chain-of-title clearance. The current license text/hash
matches 08A/08C; older paper references to CC BY-NC are historical and do not replace
the current release's published CC BY terms. No derived asset was created.

A future preparation proposal must pin encoder/resampler and relevant library
versions, decode bounded original images, and inspect each material's map roles.
Filter sRGB base color in the proper color space; filter scalar data maps as data;
renormalize filtered tangent-space normal vectors. Preserve alpha, channel packing,
UVs, tangent conventions, color-space declarations and shared-map semantics. Do not
apply a generic photo resize to every texture. Image-buffer/view offsets may change
when repackaging; geometric data and evaluated transforms must not. Compare decoded
positions/indices, bounds, nodes and UVs before/after, preserve original GLB, record
source/derived image and GLB hashes and a new immutable version. Re-run **all**
resource/envelope gates and actual desktop/narrow image/material verification.
Do not promise byte-identical encoding across arbitrary unpinned platforms.

This remains proposed work: no bookcase GLB, texture, codec tool or derivative was
acquired/installed. Existing transitive image libraries alone do not establish a
reviewed reproducible preparation pipeline. Resolve configuration, source precision
and qualification evidence before acquisition/preparation authorization.

### Is there a better first product?

There is **no better already-qualified drop-in** under current A. Only Charles and
the bookcase are acquisition-qualified in the unchanged 32-candidate source
register. Charles is the only newly inspected real product and already meets the
resource limits. The bookcase is a promising **alternate evidence lead**, not yet
a better approved renderer candidate.

Existing Elmore chair `B075X33SSW` reports 2048 px textures but about 3.3%/6.8%
width/depth disagreement. Movian Dofsan `B075NR8HWJ` has closer reported bounds but
conflicting 86/96 cm height and 4096 px textures. Other source records retain their
existing identity/dimension/budget gaps. No arbitrary new entry, replacement model
or unsupported furniture category was introduced. Bed, desk and wardrobe gaps
remain; a bookcase does not qualify as a wardrobe.

## 5. Acceptance tests for an approved follow-up

These are requirements for future work, not claims that the new policies exist.

1. **Default A:** original Charles still rejects strict containment even though
   agreement passes. Keep 1e-6 m and all resource limits unchanged.
2. **Exact evidence:** recompute float32 referenced bounds, identities, original
   hash and source claim provenance; detect wrong variant/hash/configuration.
3. **No component deletion:** all source indices/vertices remain accounted for;
   uncertain components cannot be discarded as artifacts.
4. **B authority:** reject missing owner policy/version, stale inspection, altered
   anchor, nonfinite/nonpositive or undersized envelope. The envelope encloses
   both input boxes, with physical measurements unchanged in their original fields.
5. **Fresh specification:** old factory results, candidate coordinates/IDs/order,
   original reports/scores and catalog search-document digests are unchanged.
   New larger specifications require an explicit generation/validation boundary.
6. **B validation:** a boundary/door/circulation case safe with a smaller box but
   unsafe with the planning box is rejected by existing deterministic checks.
   Numeric/report tolerances are unchanged; no stored candidate is edited.
7. **Height/suitability:** reject unsupported mounting/configuration and envelopes
   above the ceiling in explicit qualification/request preflight; do not imply
   existing X/Y validators certify vertical or ergonomic safety.
8. **C approval:** no calibration without owner approval tied to exact asset/hash,
   policy, threshold and new render-record version. Derived-hash null is correct
   only when no derived file exists; otherwise require actual byte hashes.
9. **C factor:** one uniform constant for the approved asset; changing Furniture
   size/version causes a placeholder, never a newly computed fit factor. Reject
   scales outside an approved bound; equality boundaries need deterministic tests.
10. **Transformed box:** test every transformed extreme/corner, center/floor anchor,
    preserved aspect ratio and full canonical containment. Slightly increasing
    s* without tolerance padding must fail the exact depth condition.
11. **Derivatives:** repeatable inputs/toolchain produce matching output hashes;
    geometric data unchanged, correct color/data/normal resampling, no external
    resources, unsupported extensions or resource-budget bypass.
12. **Viewer boundaries:** legacy schema 1/2 and Sheen fitting remain unchanged;
    complete trusted bindings, shared load/disposal/cancellation, missing/corrupt
    and aggregate-budget placeholders, no input mutation or view-triggered AI,
    generation or backend revalidation.
13. **Visual approval:** inspect only after applicable automated gates pass, using
    a clearly labeled private harness; check front/up, floor, materials, image
    decode and product/planning/calibrated labels at desktop and narrow widths.
14. **No automatic approval:** dimension agreement, a useful manual, successful
    downsampling or a computed s* alone never marks a product render-qualified.

## 6. Recommended next task and required decision

Recommend **B for planning**, keeping A as default until the owner approves the
new contract. It preserves native mesh proportions, retains published facts and
makes any additional conservatism explicit before generation. C is reasonable
only if the owner specifically chooses approximate calibrated visualization and
its measurable width/height errors; this review grants neither exception.

**Proposed 08C-R1: opt-in planning-envelope metadata/factory prototype, backend only.**
Start only after a recorded owner decision approving B's semantics and exact scope.

- Likely new files: `src/archimind/assets/planning_envelopes.py`,
  `src/archimind/assets/planning_envelopes.json`,
  `tests/test_planning_envelopes.py`; extend installed-package regression and the
  asset/workflow guide only as needed. Existing `assets/*.json` package-data glob
  already covers a sidecar; verify rather than assume package inclusion.
- Define an immutable independently versioned envelope/binding contract referencing
  catalog/asset version, source GLB hash, reviewed static bounds, fixed floor/center
  anchor, basis and owner policy ID. Product dimensions remain separate unchanged
  facts. Prepare only fresh canonical specifications using an explicitly named
  factory; preserve `furniture_from_catalog` and schema-1 consumers.
- Acceptance: synthetic cases plus Charles's reviewed bounds; reject insufficient
  envelopes and missing/stale authority, demonstrate unchanged old objects and
  reports, and verify new specifications can pass/fail existing X/Y checks as
  expected. Qualification/preflight must explicitly handle unsupported height or
  mounting. No generation algorithm or validator modifications.
- Deliver one reviewed metadata/API/test checkpoint. No UI, rendering, raw asset
  packaging, downloads, live model calls, calibration, 08D or new dependencies.

Keep the bookcase as a separate source-adjudication/preparation proposal: reconcile
manual units/configuration and documented dimensional precedence, then seek bounded
individual acquisition and texture-derivative authorization if it still qualifies.
Do not start with a texture converter or silently substitute manual dimensions.
No API key, GPU, paid service, embedding store or dataset-scale pipeline is needed
for either proposed next step.

## 7. Verification, preservation and delivery

| Check | Fresh result |
| --- | --- |
| Focused Python inspection/catalog/packaging/render/model/geometry regressions | **435 passed in 11.15s**, no failures/skips |
| Offline arithmetic/topology checks | **6 passed** (standard-library review checks; not six new application tests) |
| Frontend syntax/tests | Passed; **27 passed, 0 failed, 0 skipped** |
| Ruff lint/format | Passed after formatting both review examples; 116 files already formatted |
| Dependency compatibility | No broken requirements found |
| Streamlit headless health | HTTP **200 ok** |
| Source/wheel + isolated installed loading | Passed within focused packaging regression |
| Original inspector against Charles | Exit **2**, every result field identical to 08C |
| Production preservation | All **163 pre-existing tracked files** match baseline Git objects and saved SHA-256 inventory |

No application tests were weakened or changed. A local complete suite was not
repeated for two documentation/data files; the final commit's CI runs the full
suite/frontend/build/health checks and its exact outcome is reported on delivery.
No new app/renderer visual behavior exists to claim browser-tested. Manual PDF
page inspection is source evidence, not real-product rendering verification.

Direct HTTPS reads totaled **4,472,634 body bytes**: 223,262 bytes of primary
metadata plus the 4,249,372-byte manual. Every direct response was at most 1 MiB;
model HEAD responses had zero bodies. Web search/text extraction was also used;
its backend transfer volume is not measurable here and is not included in that
direct-request accounting. Failed web extraction did not become evidence; local
PDF page rendering supplied the manual verification. No new GLB, standalone image
or texture download, model inference, Codex subprocess, dataset archive or new
dependency occurred.

Only this review and its JSON companion are intended Git changes. Original source
register/catalog/08C evidence, source GLB, canonical geometry, UI and bundle remain
unchanged; `.agents/` and `.claude/` remain untracked and untouched. Source/manual
bytes, page renderings and review scripts stay outside Git. The exact calculations
and deterministic source topology can be reproduced with the appendices below;
original model access remains subject to its source license and acquisition scope.
Initial review checkpoint `aeb53ad` failed [CI formatting](https://github.com/ngstephen1/ArchiMind/actions/runs/40788114791)
because the report's Python examples were added after the local formatting check.
The correction formats only those examples, re-executes both appendices and reruns
lint/format checks. No production file, test or acceptance gate is changed to
resolve the failure. Final commit/CI identities belong in the delivery response,
avoiding a self-hash.

## Appendix A - reproduce the exact arithmetic without applying it

Run with standard Python against the scalar inputs already in the comparison
receipt. This reads no model, changes no specification and writes no asset.

```python
import json
from fractions import Fraction
from decimal import Decimal, localcontext
from pathlib import Path

r = json.loads(Path("docs/data/ASSET_DIMENSION_POLICY_REVIEW.json").read_text())
a = r["arithmetic"]
p = list(map(Fraction, a["physical_wdh_m"]))
m = list(map(Fraction, a["mesh_wdh_exact_m"]))
s = min(pi / mi for pi, mi in zip(p, m))
assert s == Fraction(1731198976, 1751019375) == p[1] / m[1]
assert all(mi * s <= pi for mi, pi in zip(m, p))
assert m[1] * (s + Fraction(1, 10**12)) > p[1]
assert len(set(pi / mi for pi, mi in zip(p, m))) == 3
assert list(map(Fraction, a["planning_envelope_wdh_exact_m"])) == [
    max(pi, mi) for pi, mi in zip(p, m)
]
assert a["applied_scale"] is None and a["derived_glb_sha256"] is None
assert not r["decision"]["policy_B_authorized"]
assert not r["decision"]["policy_C_authorized"]
with localcontext() as ctx:
    ctx.prec = 60
    decimal = lambda q: Decimal(q.numerator) / Decimal(q.denominator)
    print("uniform factor:", decimal(s))
    for pi, mi, expected in zip(p, m, a["calibrated_minus_published_wdh_mm"]):
        error_mm = (decimal(mi) * decimal(s) - decimal(pi)) * 1000
        assert abs(error_mm - Decimal(expected)) < Decimal("1e-50")
        print("size, signed error mm:", decimal(mi * s), error_mm)
```

## Appendix B - reproduce source topology without editing the GLB

This narrow review snippet accepts only the already-hashed Charles source and
its observed single identity scene. It is not a replacement inspector for
arbitrary uploads. Provide the authorized original local quarantine path; it
never downloads, writes or removes geometry.

```python
import collections
import hashlib
import json
import struct
from pathlib import Path

path = Path("/path/to/authorized/B075X2X4XS.glb")
before = path.read_bytes()
assert hashlib.sha256(before).hexdigest() == (
    "62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645"
)
n = struct.unpack_from("<I", before, 12)[0]
d = json.loads(before[20 : 20 + n])
assert len(d["scenes"]) == len(d["nodes"]) == len(d["meshes"]) == 1
node = d["nodes"][0]
assert node["translation"] == [0, 0, 0] and node["scale"] == [1, 1, 1]
assert node["rotation"] == [0, 0, 0, 1] and node["mesh"] == 0
primitive = d["meshes"][0]["primitives"][0]
a = d["accessors"][primitive["attributes"]["POSITION"]]
v = d["bufferViews"][a["bufferView"]]
ia = d["accessors"][primitive["indices"]]
iv = d["bufferViews"][ia["bufferView"]]
assert a["componentType"] == 5126 and ia["componentType"] == 5123
assert not a.get("byteOffset", 0) and not ia.get("byteOffset", 0)
assert v.get("byteStride", 12) == 12
start = 20 + n + 8
points = [
    struct.unpack_from("<3f", before, start + v["byteOffset"] + 12 * i)
    for i in range(a["count"])
]
indices = struct.unpack_from("<" + "H" * ia["count"], before, start + iv["byteOffset"])
faces = list(zip(indices[::3], indices[1::3], indices[2::3]))
assert len(set(indices)) == len(points) == 23412


def count_components(points, faces, weld=False):
    parent = list(range(len(points)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        parent[find(a)] = find(b)

    if weld:
        first = {}
        for i, point in enumerate(points):
            if point in first:
                union(i, first[point])
            else:
                first[point] = i
    for a, b, c in faces:
        union(a, b)
        union(a, c)
    return len({find(i) for i in range(len(points))})


assert count_components(points, faces) == 39
assert count_components(points, faces, True) == 12
print(
    "native bounds:",
    [min(p[i] for p in points) for i in range(3)],
    [max(p[i] for p in points) for i in range(3)],
)
assert path.read_bytes() == before
```
