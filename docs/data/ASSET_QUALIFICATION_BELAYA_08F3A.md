# Belaya native-scale qualification — Task 08F3A

**BLOCKED_STORAGE_VOLATILITY — incomplete; no Belaya rendering approval.**
Observed October 30, 2026, America/New_York (October 31 UTC).
Baseline: `2b4ba23494881a76b44c66ecb6c68437d91fec96`.
[Machine receipt](ASSET_QUALIFICATION_BELAYA_08F3A.json) preserves acquisition,
inspection, draft dimensions and the storage stop. No checkpoint was committed.

## A. Disk readiness

Fresh preflight passed with **8,008,585,216 bytes** available on the shared APFS
pool. Acquisition began with **8,127,504,384 bytes** and ended
with **8,110,452,736 bytes**. The finite observer then
recorded:

| Time, EDT | Available bytes |
| --- | ---: |
| 23:22:10 | 7,009,435,648 |
| 23:22:40 | 6,824,796,160 |
| 23:23:11 | 5,751,578,624 — sharp-decline stop |

The last interval lost **1,073,217,536 bytes (1,023.50 MiB) in 31.24 seconds**.
A subsequent command measured **5,705,760,768 bytes**, the minimum captured.
Allocated swap was observed at 10.5 GiB, up from 8.5 GiB in S4; later it fell to
9.5 GiB with a capacity rebound. This supports swap allocation as a contributor,
not exhaustive attribution. The 1 GiB reserve was not breached. Repeated rapid
losses nevertheless triggered the owner's stop rule. Final report measurement:
**6,954,377,216 bytes**. No cleanup was performed; the observer exited.

## B. Asset acquisition and identity

Only the authorized [official Belaya GLB](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/original/T/B074L4976T.glb)
was acquired: **3,135,676 bytes**, received-byte SHA-256:

`2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e`.

The external quarantine is
`/Users/macbook/Hack/.archimind-08f3a/B074L4976T.glb`; no model was added to Git.
TLS verification, a 15 MiB read cap, official final URL, exact Content-Length and
HEAD/GET agreement were checked. ETag is stored separately, never used as SHA-256.

The exact B074L4976T / amazon.co.uk / Oak / T80505PL05LVO join comes from unchanged
08F1 evidence and catalog 1.1.0. Fresh official model-index bytes retain SHA
`90d061c3e3efa555a55bfc8ed7fc55cdb322086397443de1b33e91f7924d7d92`.
No new listing archive was downloaded. Small official documentation/index
responses were retained externally with timestamps, headers and hashes.

The [official model README](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md)
and [CC BY 4.0 text](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt)
were re-read. Public delivery requires attribution to Amazon.com and the named
dataset builders, license/change notices, retained notices and no endorsement.
This does not independently certify trademarks, authorship or product fidelity.

## C. Native geometry

| W × D × H, meters | Meaning |
| --- | --- |
| 1.6 × 0.8 × 0.75 | Unchanged published whole-item claims |
| 1.5999999046325684 × 0.8018731772899628 × 0.7516312003135681 | Inspected transformed mesh |

Native min XYZ: `(-0.7999999523162842, 0, -0.31751760840415955)`.
Native max XYZ: `(0.7999999523162842, 0.7516312003135681, 0.4843555688858032)`.
One static identity node matrix; native Y is up by source convention.
Floor/center normalization translates Z by **−0.08341898024082184 m**, with
scale exactly 1.0 and no rotation.

Depth exceeds the published claim by 1.873177 mm and height by 1.631200 mm.
Per-axis agreement passes the unchanged 0.032 / 0.016 / 0.015 m allowances.
The published canonical box fails strict containment. Natural front, material
appearance and actual image decoding remain unverified without browser review.

## D. Draft Policy B envelope

The existing exact-rational outward-rounding procedure computed:

**1.6 × 0.8018731772899628 × 0.7516312003135682 m**.

The generated draft passed the existing eight-corner rational containment
validator without an inward epsilon. Published measurements remain separate;
no mesh resizing was performed. Draft envelope digest:
`f2b706c8111e5f9321d3d90856d914a60ab63aebdb0cf30dd4b8847f493723a5`.

**This is an uncommitted, untested release candidate, not completed qualification.**
The generated object's internal `planning_approved` flag describes its draft
contract construction; it must not be presented as a verified delivery checkpoint.
The working-tree trust-contract extension and new resources still require focused
regressions, historical compatibility checks and review before release.

## E. Resource budget

Belaya has one mesh/material, **812 triangles**, three embedded 2048×2048 images
(one PNG, two JPEG), no extensions or external resources, and **67,108,860 bytes**
estimated decoded RGBA/mipmaps. All individual resource gates pass.

One Belaya plus one Charles: **7,388,116 encoded bytes**, **43,518 triangles**,
**134,217,720 estimated texture bytes**. This is eight bytes below the unchanged
128 MiB texture limit, counting each model's resources independently. It is an
arithmetic pass, not measured GPU memory or browser approval. No texture
optimization, resource-sharing assumption or budget increase was introduced.

## F. Rendering and workflow

**Not implemented or browser-verified.** No approved Belaya release, registry entry,
packaged GLB, viewer change, screenshots, A/B verification or fallback exercise.
The existing workflow still uses metadata-only Belaya preparation and placeholders.
Charles remains the only released product mesh. Morava and nightstand remain
metadata-only.

## G. Preservation

All **252 of 253** pre-existing tracked files except the
explicit draft planning module match the baseline hashes. Both catalog releases,
Charles's original envelope/release/GLB, Sheen, renderer sources/bundle, canonical
geometry, validators, scoring, 08F1/08F2 receipts and frozen 08R0/08R1 artifacts
are unchanged. No encoder ran. `.agents/` and `.claude/` were untouched.

Uncommitted task files:

- `src/archimind/assets/planning_envelopes.py` — draft trust-contract extension.
- `src/archimind/assets/belaya_qualification.json` — fixed acquisition/inspection receipt.
- `src/archimind/assets/belaya_planning_envelope.json` — draft computed reservation.
- `docs/data/ASSET_QUALIFICATION_BELAYA_08F3A.md`
- `docs/data/ASSET_QUALIFICATION_BELAYA_08F3A.json`

## H. Verification

Completed: bounded acquisition, SHA-256, existing GLB inspection, draft envelope
construction, targeted Ruff lint/format and `git diff --check`. JSON reports were
parsed after writing. No claim is made that the historical 1,817 tests passed on
this changed working tree.

**Not run after the storage stop:** new focused tests, full Python/frontend
regressions, builds, registry/integrity suite, pip check, health, packaging,
installed-wheel checks or desktop/narrow Chromium acceptance. No new tests were
written before the stop. Full release verification remains outstanding.

## I. Git

HEAD remains the baseline; remote main matched at initial preflight.
No staging, commits, pushes or CI runs. No unverified checkpoint was manufactured.
The five task files above are intentionally left for review/resumption.

## J. Next recommendation

Stop here. Resume only after a fresh storage preflight and renewed stability.
Reuse the quarantined bytes after rechecking their SHA-256; another download is
unnecessary. Review the draft contract, add focused tests and reconcile historical
preservation assertions before checkpoint 1, then complete browser/render gates.

Do not start Morava 08F3B, nightstand, texture optimization or retrieval integration.
Measured Belaya-only and Belaya-plus-Charles budgets do not currently require
texture optimization; actual browser feasibility remains pending.

## R1 continuation — qualification checkpoint

October 31, 2026, America/New_York. The stopped-run sections above are historical
and remain intact. **Checkpoint 1 is locally verified; rendering remains pending.**
No source request or download occurred. The existing quarantined GLB was rehashed
and re-inspected; its full receipt and candidate digest reproduce exactly.
Independent Fraction arithmetic confirms eight contained corners and zero inward
error. The reservation remains 1.6 × 0.8018731772899628 × 0.7516312003135682 m.

Candidate rebuilding does not grant public-use authority. Belaya's loader and
planning furniture bindings now require a separately pinned planning-release
resource plus the unchanged acquisition/inspection receipt. The release binds
catalog/product/variant, source model, inspection, envelope, policy and R1 owner
authorization identities. Charles's existing receipt authority and resource bytes
are unchanged. A caller-supplied approval flag cannot bypass this gate. This is
same-agent implementation and separate arithmetic/testing, not independent human
or manufacturer verification.

**191 focused tests passed in 4.19s**, including 27 new Belaya cases and existing
Charles, planning, source-preservation and catalog-admission checks. Coverage
includes fixed release/receipt absence or alteration, forged/stale identities,
inward rounding, published-box failure, scale/yaw, source hashes and metadata-only
Morava/nightstand. Ruff lint and formatting passed (179 files). An initial test
syntax error was corrected; an obsolete 08F2 no-envelope assertion was explicitly
updated while retaining published-factory and placeholder behavior checks.
No full-suite or new browser result is claimed at this checkpoint.

Both catalog releases, original Charles envelope/release/assets, and frozen
retrieval evidence remain unchanged. The new receipt records the exact authorized
source migration; historical 08F1/08F2 receipts are not rewritten. The GLB remains
outside Git. Checkpoint commit/CI identity will be added after it exists.

Owner-selected rendering scope is **Belaya-only first**. Mixed Charles/Belaya
scenes must use truthful placeholders with a distinct not-yet-qualified reason,
not a false numerical budget failure. Estimated product texture bytes exclude
room textures, environment targets, shadows and other GPU allocations.

### R1 checkpoint 2 — Belaya-only native rendering

Checkpoint 1 was pushed as `e56333d3a076819f8c32e885afba490755682d3c`;
[CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/41170171461):
1,844 Python tests and 75 frontend tests.

The private pending-qualification harness reused the actual product loader,
native placement, resource pool and room renderer. Desktop 1440×1000 and resized
Chromium 390×844 showed the source wood-grain appearance, vertical up, an open
working side facing canonical south, floor contact and scale exactly 1. Two desks
shared geometry and one 3,135,676-byte GLB load. Initial setup was 686.9 ms;
missing/corrupt/recovery setups were 163.0/149.3/264.5 ms. These are local
observations, not physical-mobile or total GPU-memory measurements.

A forced HTTP 404 and corrupt response each produced three placeholders;
recovery restored both desks. Repeated cleanup and rapid replacement produced no
page errors. The deliberate 404 caused one expected browser network error.
Orbit, zoom, reset, cutaway, walls/openings and narrow framing were inspected.
Screenshots and the private harness remain outside Git under
`/Users/macbook/Hack/.archimind-08f3a/harness/`; hashes and detailed limits are in
`src/archimind/assets/belaya_visual_review.json`. This is same-agent review,
not independent human certification or manufacturer measurement.

A separate pinned render release approves unchanged Belaya bytes. Charles's
release, visual receipt, envelope, GLB and default APIs remain preserved.
Registry generation is a projection of the reviewed releases. Runtime scenes
still contain only IDs/version/digest bindings; no URL/transform admission was
added. The V3 shape and original native-scale loader/cleanup paths remain intact.

Mixed Charles/Belaya requests are **not yet qualified**. In the private browser
test, the numerical 128 MiB estimate passed by eight bytes, while the separate
admission decision rejected the scene: all detailed product meshes became labeled
placeholders and zero GLB requests occurred. The backend adapter and direct
mounting path enforce the same policy. This is distinct from numerical budget
failure; the 128 MiB ceiling is unchanged. Texture accounting does not include
environment, structural, shadow or framebuffer allocations.

At this checkpoint the Select/Prepare workflow is intentionally unchanged;
Belaya planning-sidecar integration remains checkpoint 3.

Local checkpoint 2 verification: 80 frontend tests, syntax/build, registry,
Ruff (180 files), pip compatibility and health200 passed. The initial full Python
run had 1,851 passes and one stale exact-GLB-inventory assertion (161.87s).
The assertion now requires exactly Sheen/Charles/Belaya, preserving old integrity
checks. Corrected inventory plus Belaya tests: 41 passed; separate offline
source/wheel/isolated-install, catalog and preservation checks: 61 passed.
The new Belaya suite totals 12 passing cases. Full CI must pass before checkpoint3.
