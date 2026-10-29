# Conservative planning envelopes - Task 08C-R1

Policy B is approved for **explicit fresh backend specifications only** by the
owner's 08C-R1 instruction. This module does not approve rendering, modify an
existing design, acquire a GLB, implement Policy C, or expose a new UI control.
The [08C report](../data/ASSET_QUALIFICATION_08C.md) and
[policy review](../data/ASSET_DIMENSION_POLICY_REVIEW.md) remain historical evidence.
The original inspector still rejects Charles against the published product box.

## Four meanings of dimension

| Value | Meaning | Source of authority |
| --- | --- | --- |
| Published product dimensions | Reviewed published whole-item claims, not independent metrology | Unchanged schema-1 furniture catalog and original unit/axis evidence |
| Measured mesh dimensions | Extents of all inspected static geometry, after authored transforms | Pinned 08C inspection and received-source SHA-256 |
| Planning dimensions | Conservative geometric reservation for this native-scale mesh and published box | Explicit versioned Policy B envelope |
| Canonical Furniture dimensions | The values actually given to existing geometry/generation | Original factory uses published values; new explicit factory uses planning values |

The canonical `Furniture` schema remains unchanged. Product facts and planning
provenance live in a separate immutable binding, never extra canonical fields.
A planning box is not ergonomic clearance, chair pullback, wardrobe-door space,
mounting safety, independent physical measurement or architectural compliance.

## Public interfaces

`archimind.assets` exports `PlanningEnvelope`, `PlanningEnvelopeEvidence`,
`PlanningEnvelopeQualification`, `PlanningEnvelopePlacement`, `PlanningDimensions`,
`PlanningFurnitureBinding`, `PlanningFurnitureSpecification`,
`PlanningEnvelopeError`, `qualify_planning_envelope`, `load_planning_envelope` and
`furniture_from_planning_envelope`.

```python
from archimind.assets import (
    furniture_from_catalog,
    furniture_from_planning_envelope,
    load_planning_envelope,
)

asset = "abo-b075x2x4xs-amazon-com"
envelope = load_planning_envelope(asset)
original = furniture_from_catalog(
    asset, furniture_id="old", name="Charles", x_m=1.0, y_m=1.0
)
proposal = furniture_from_planning_envelope(
    asset, furniture_id="new", name="Charles", x_m=1.0, y_m=1.0
)
furniture, binding = proposal
binding.validate_furniture(furniture)
assert original.width_m == 0.9906
assert furniture.width_m == envelope.planning_dimensions.width_m
assert not binding.envelope.qualification.render_qualified
```

The factory preserves ID, name and requested finite X/Y, including negative or
out-of-room values, and requires integer yaw zero. It returns a fresh mutable
canonical Furniture plus a deeply immutable binding. It does not call generation,
room validation or rendering. Every caller must explicitly build and validate a
new specification before relying on its spatial properties.

`binding.validate_furniture(item)` verifies current evidence, identity/name/category,
reservation dimensions and zero yaw. It deliberately takes position from the
canonical item, permitting an explicitly generated candidate to carry the same
binding. It does not keep a competing pose or certify a changed position. Changing
identity/geometry invalidates the binding; changing X/Y still needs the unchanged
spatial engine. Neither factory nor binding check migrates or edits stored layouts.

## Exact reservation and placement

Version 1 supports meters, native +Y up / source-reported +Z front, zero furniture
yaw, identity added orientation and **scale (1,1,1)**. Unsupported/ambiguous anchors,
nonzero yaw and scaling are rejected. The complete native AABB and normalized AABB
are retained in the evidence. The fixed added translation centers native X/Z and
sets minimum native Y to zero; recorded normalized bounds must enclose that exact
translation of the native box.

For that fixed anchor, reserve at least the maximum of the published extents and
verified mesh extents. The implementation also considers both signed distances
from the translated center, so a numerical center residual cannot put a corner
outside the reservation. Minimum W/D/H are:

```text
W >= max(published W, native X extent, 2*abs(translated min X), 2*abs(translated max X))
D >= max(published D, native Z extent, 2*abs(translated min Z), 2*abs(translated max Z))
H >= max(published H, native Y extent, translated max Y)
```

Exact `Fraction` arithmetic treats decoded mesh bounds as their binary64 values
and published measurements as decimal-meter claims. The minimum is rounded toward
positive infinity only when needed so **both** the stored binary64 value and its
shortest decimal JSON/meter representation are at least the exact minimum. This
matches the existing geometry engine's decimal-meter convention. Version 1 requires
that deterministic minimum; a 2% padding rule or extra user clearance is not part
of this policy. No inward tolerance is used for this proof.

After normalization, the native mesh would be offset in Three coordinates by
`(planning_width/2, 0, -planning_depth/2)`. Canonical `(X,Y,Z)` is Three `(X,-Z,Y)`.
The envelope validator checks all eight transformed AABB corners with exact
rational comparisons against `[0,W] x [0,D] x [0,H]`, without epsilon. This object-
local proof bounds every vertex represented by the verified box. A future renderer
must use the canonical Furniture's X/Y and this recorded anchor; it cannot fit,
rescale, independently reposition or silently enlarge canonical geometry.

## Charles reference and evidence chain

Product/variant: Charles, Sod, ASIN/model `B075X2X4XS`. Variant identity uses that
specific ASIN plus its recorded Sod label; no additional upstream variant code is
invented. Catalog ID `archimind-furniture`, schema/version **1 / 1.0.0**, original
record version **1.0.0** are unchanged. Planning schema, envelope version and policy
version are independently **1 / 1.0.0 / 1.0.0**.

| Axis | Published m | Exact inspected mesh m | Planning and new canonical float m |
| --- | ---: | ---: | ---: |
| Width | 0.9906 | 0.996104896068572998046875 | 0.996104896068573 |
| Depth | 0.9906 | 1.00194132328033447265625 | 1.0019413232803345 |
| Height | 0.9652 | 0.9760930538177490234375 | 0.9760930538177491 |

Height advances one float step because the original float's shortest decimal
representation is slightly below the exact inspected bound. This is numerical
outward rounding, not a material allowance or correction to published height.

The fixed normalization translation is `(0,0,0.00010657310485839844)` in Three axes;
placement at a canonical origin uses `(W/2,0,-D/2)`. Source SHA-256:
`62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645`.
The receipt ID is `08C:charles:2026-10-28:inspection-v1`; its SHA-256 is the canonical
JSON digest of the original inspection payload:
`3ab3b103e8cbaa4b93cd05b825d0a5d4ab819cd62e12b2e5b253aa07c479fd5d`.
The separate original qualification-report byte hash is also pinned. The explicit
owner-decision ID is `08C-R1-policy-B`, with the submitted instruction's digest;
that approval has no rendering or calibration scope.

`planning_envelopes.json` packages one metadata-only reference, including the
original receipt. Code pins the reviewed receipt/report digests, rather than
trusting an arbitrary 64-character hash or claimed approval flag. Adding another
source requires explicit reviewed evidence and a release/requalification. The
bookcase has no planning record. No source GLB is read or shipped by this API.
The recorded source hash refers to historical received bytes; a future renderer
must independently check the actual file and decoded geometry before displaying it.

## Versions, integrity and safe rejection

All metadata is strict, frozen and JSON-serializable, with immutable tuples/nested
records. Unknown fields, duplicate keys/IDs, unsupported schema/policy versions,
nonfinite values, missing evidence, changed source hashes, stale catalog versions,
wrong variants, inconsistent transforms and nonminimal/undersized reservations
fail closed. The loader reads only a fixed packaged resource, capped at 512 KiB;
it accepts no path or URL. No network, GLB inspection, AI or external process is
performed by these interfaces.

Envelope and binding digests use sorted compact JSON, `ensure_ascii=True`, no
nonfinite numbers, excluding only the object's own `metadata_sha256`. Rebuilding
the same metadata yields identical digests. A digest detects inconsistency; the
separate pinned receipt and current catalog checks establish qualification.
Direct typed-model construction raises Pydantic `ValidationError`; public
qualification/loader/factory/binding boundaries raise sanitized
`PlanningEnvelopeError` with a stable `.code`.

Current catalog identity/version, complete record digest and original physical
measurement evidence must match. Changing policy, record, variant or GLB requires
explicit requalification; recomputing a metadata digest cannot authorize new
source evidence. Old canonical RoomDesign JSON continues to deserialize with its
original dimensions. A historical sidecar may fail current eligibility checks
when its catalog changes, but is never automatically migrated or used to rewrite
the old design. Historical evidence files remain unchanged.

## Boundaries and 08C-R2 prerequisites

Charles is **planning-approved**, not render-qualified. The catalog still reports
no render-qualified product and the original physical-envelope inspection still
reports its historical rejection. No new room choice, Three.js path, Plotly behavior,
renderer binding or asset was introduced. Policy C remains prohibited.

Before a separately authorized 08C-R2 rendering-qualification task:

1. Use only the original authorized GLB with matching source hash; verify actual
   decoded bounds/resources against the pinned receipt, not just its filename.
2. Build an explicit trusted native-scale product path that consumes this envelope
   and exact catalog/version binding. Preserve legacy illustrative Sheen fitting.
3. Verify actual post-placement bounds/floor contact, including runtime numeric
   limits, at the canonical Furniture pose. The current proof is object-local;
   it does not guarantee arbitrary huge world-coordinate arithmetic is usable.
4. Inspect actual materials, image decoding, front/up interpretation, desktop and
   narrow rendering and failure/cleanup behavior with a private harness before
   any render-qualification flag or approved GLB packaging.
5. Keep source-reported natural front visibly unverified until that review. The
   planning proof verifies numerical axes/anchor, not appearance or metrology.
6. Apply existing room/collision/door/circulation checks to a **new** specification;
   preserve old candidates/scores. Vertical, window, mounting and furniture-function
   checks remain outside the current X/Y engine's scope and must be explicit
   suitability blockers where needed. Stored rotations other than zero remain
   unsupported. No selected-layout 08D integration is part of R1 or automatically
   authorized by these prerequisites.

## Verification commands

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pytest -q tests/test_planning_envelopes.py
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pip check
python scripts/check_health.py
(cd frontend/realistic_viewer && npm run check && npm test && npm run build)
git diff --exit-code -- src/archimind/_viewer_assets
python -m pytest -q tests/test_asset_catalog_packaging.py
```

Tests block network/process/provider/GLB execution in the envelope unit suite.
Packaging is a separate offline test: source/wheel inclusion, dependency-free
isolated target installation, installed-path verification and actual installed
factory/loading. The canonical geometry, catalog facts, renderer bundle and
previous qualification evidence remain unchanged. Local verification: **1,477 passed in 80.71s**, including all 1,380 previous tests
and 97 new envelope cases. Frontend **27 passed, 0 failed, 0 skipped**; syntax/build,
bundle equality, Ruff lint/format (119 files), dependency compatibility and HTTP 200
health passed. Source/wheel inclusion and isolated installed factory/sidecar loading
passed. [Schema checkpoint CI](https://github.com/ngstephen1/ArchiMind/actions/runs/40790949419)
and [factory checkpoint CI](https://github.com/ngstephen1/ArchiMind/actions/runs/40791341648)
passed. Final checkpoint/CI identities are reported at delivery; R1 stops before
acquisition or rendering.
