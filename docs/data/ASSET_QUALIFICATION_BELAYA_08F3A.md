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

### R1 stop boundary — recurring storage loss; checkpoint 3 pending

**STOPPED_RECURRING_STORAGE_LOSS**, 2026-10-31 at 01:05:12 EDT.
The second sharp interval fell from **11,287,248,896 to 10,128,388,096 bytes**:
**1,158,860,800 bytes / 1105.18 MiB in approximately 30 seconds**.
This meets the recurrence stop rule even though free space exceeds 2 GiB.
The cause is unknown; no cleanup, owner-app termination or broad investigation
was performed. The finite observer exited and the task-owned private HTTP server
was stopped. The separate first-decline/reassessment/stage2 sample series are
retained in the JSON. Final one-off available capacity was **11,214,094,336 bytes**
using statvfs; that does not override the volatility stop.

Checkpoint 2 had already been pushed as
`b4b6115ff0d74108c927c1a9d633b4718eb69c98`.
[Its CI passed](https://github.com/ngstephen1/ArchiMind/actions/runs/41170994700):
**1,856 Python tests in 133.50s**, **80 frontend tests**, lint/format,
dependency/build/bundle and health200 checks. Both completed checkpoints are
synchronized with origin/main. The final stop addendum is intentionally **local
and uncommitted**; no further commit/push followed the storage stop.

Planning qualification and the trusted Belaya-only rendering API are complete.
**Checkpoint 3 has not started.** The existing application catalog preparation
still uses its pre-R1 behavior; no approved Belaya planning sidecar has yet been
connected to Select → Prepare → Review → Generate. Do not present the new native
mesh as available through that flow, or the private fixture as a generated,
spatially validated layout. Application A/B/pending-edit/camera acceptance for
Belaya and final workflow documentation remain pending. Morava/nightstand and
the original catalog records retain their metadata-only state.

Before/after comparison: **240 of 253 baseline files unchanged**;
every changed baseline path/hash and all 26 committed changed paths are recorded
in the JSON. Original catalog releases, search documents, Charles receipts/assets
and frozen retrieval evidence remain preserved. No source requests, model
reacquisition, new dependencies, encoder execution or retrieval integration
occurred during R1. Resume only after the separately required stable storage gate;
retain both completed commits and all interrupted-run evidence.

## R2 — application integration implemented; acceptance stopped

**BLOCKED_RECURRING_STORAGE_LOSS_APPLICATION_ACCEPTANCE_INCOMPLETE.**
31 October 2026, America/New_York. Baseline remains `b4b6115`; no checkpoint 3
commit or push was made. All R1 stopped-run observations above are preserved.

The narrow preparation change recognizes Belaya as requiring its already approved
Policy B envelope: exactly **1.6 × 0.8018731772899628 × 0.7516312003135682m**.
It uses the existing immutable sidecar/factory and explicit Prepare/Review/Generate
boundary. Missing required evidence disables preparation, without substituting
published1.6 ×0.8 ×0.75m dimensions. The selected viewer's attribution is product
specific and mixed Charles/Belaya scenes receive an explicit unqualified message.
Generator, validators, scoring, native asset bytes, hashes, budgets and retrieval
implementation are unchanged. These changes are **uncommitted**.

Focused offline verification passed **134 tests in 35.06s**, including nine new
cases covering Belaya preparation, stale evidence, serialization, actual AppTest
generation and exact A/B object handoff, no regeneration on selection, procedural
bed companions, mixed fallback and preservation. Three earlier failures were
stale pre-Belaya render-count expectations and a zero-argument release mock; the
updated tests assert exact new single-product/mixed outcomes and preserve safety
checks. Full Python/frontend/build/packaging/health release verification was not
run for R2. Updated installed-wheel assertions remain unexecuted.

The actual Streamlit app was opened at 1440×1000. Catalog selection, separate
published/planning labels, Belaya selection and the Prepare action were exercised.
The review heading appeared; the last browser observation still showed Generate
disabled. The transition was not resolved before the storage stop. **No actual
browser Generate/A/B/render acceptance is claimed.** Companion/mixed/regression/
corruption scenarios and 390×844 acceptance remain pending. No R2 screenshot was
captured. Tooling reported zero console errors and two warnings; warning contents
were not retained, so no clean-console acceptance claim follows. Earlier R1 private
fixture success and current AppTest success do not substitute for this acceptance.

Initial df availability: **12,773,683,200bytes**. The five-sample two-minute gate
passed. During subsequent finite monitoring, availability fell from
**12,311,220,224 to 11,438,329,856bytes** at **02:17:07 EDT**:
**872,890,368bytes (832.45MiB) in about 30 seconds**. Allocated swap increased from
**5GiB to6GiB**, used swap from 4018.56 to 4619.88 MiB, and raw pressure from 2 to 1.
This association is not proof of the source of disk consumption. The observer
exited; the alert was noticed on the next tool result, and local acceptance stopped.
The task-owned Streamlit server was terminated and its test page unloaded.
No owner application was terminated and no cleanup or broad investigation occurred.

Final one-off df at **02:23:08 EDT**: **11,232,292,864bytes (10.461GiB)**,
the minimum observed across this run. Swap: 6144 MiB allocated / 4435.88 MiB used;
raw pressure 2, memory_pressure reported 40% free. All observed samples exceeded
the 2 GiB gate and 1 GiB reserve, but recurring sharp loss independently blocks release.
The JSON retains all bounded samples, exact changed paths and before/after hashes.

**08F3A remains incomplete.** Preserve this work, establish a stable storage gate,
then finish actual browser acceptance and the full release checks before committing
checkpoint 3. Morava 08F3B is not ready to proceed under this task; it still requires
separate authorization after this checkpoint and storage readiness. No furniture
or encoder acquisition, semantic integration, texture optimization or later task
was started.

Sampling limitation: the requested 30-second observer produced 16 active-work
samples with several delays, the largest **1,019.646 seconds**. Their cause was
not investigated. This is not a continuous capacity or instantaneous-stop guarantee.
The final sharp-loss interval itself was **30.087 seconds**; the full timestamps
and gaps are retained in JSON.


## R3A — Generate gate resolved; checkpoint 3 remains pending

Observed 2026-10-31. **GENERATE_GATE_RESOLVED** on the ordinary `app.py`
entrypoint at HEAD `b4b6115ff0d74108c927c1a9d633b4718eb69c98`, retaining all
13 pre-existing modified tracked files. No application correction was needed.

### Exact gate and observed cause

`src/archimind/ui/layout_generation.py:146` passes
`disabled=pending.catalog_mode and pending.prepared is None`. In
`ui/furniture_assets.py`, catalog discovery must succeed, Prepare must store a
`PreparedCatalogSpecification` under `prepared_catalog_specification`, and
`specification_is_current()` must confirm the current selections, base geometry
and evidence. Only then are review and the non-null prepared return emitted.
Selection/evidence changes invalidate readiness; seed edits do not. There is no
additional review checkbox, spatial-validation step or hidden approval action.
Belaya must retain its Policy B reservation; published dimensions cannot replace it.
The JSON R3A section records state keys, update sites and displayed conditions.

Read-only DOM observations reproduced the transient exactly (UTC):

| Time | Script state | Review visible | Generate disabled |
| --- | --- | --- | --- |
| 21:15:51.156 | notRunning, before Prepare | no | yes |
| 21:15:51.327 | running | no | yes |
| 21:15:51.573 | running | yes | yes |
| 21:15:53.652 | running | yes | **no** |
| 21:15:53.837 | notRunning | yes | **no** |

Review appeared **2.079 seconds before** the button update. An immediate read
after the click also still saw the previous `notRunning` state. Therefore neither
review visibility nor an immediate idle read alone is sufficient synchronization.
The corrected browser sequence uses visible labels, fresh locators, the expected
post-action enabled state and a settled rerun. An initial checkbox-wrapper click
was intercepted and timed out; visible-label clicks then persisted all choices.
No forced clicks, fabricated session state, server diagnostic wrapper or readiness
bypass was used. This establishes the current timing issue; it does not recover
the unrecorded final R2 browser state or rewrite R2 as successful.

### Actual generation and focused regression

At desktop **1440 × 1000**, the existing 5 × 4 m bedroom, seed **42**, only
Belaya selected and no procedural companions, the enabled actual button was
clicked at approximately **21:16:42 UTC**. The page returned **two validated
alternatives in five attempts** and settled by **21:16:43.424 UTC**. Both displayed
validation as passed with zero issues/warnings; scores were 93.139053 and
90.566198. Plotly remained selected. Existing selected Plotly trace metadata
confirmed `catalog:abo-b074l4976t-amazon-co-uk:1`, desk category, Oak label and
exact **1.6 × 0.8018731772899628 × 0.7516312003135682 m** dimensions.
No smaller published-box substitution occurred. Browser-private server session
state was not extracted; immutable prepared/result state was checked in AppTest.

Only `tests/test_catalog_generation_ui.py` changed beyond the two evidence
reports. Both Belaya parameter cases now explicitly assert enabled Generate after
preparation, correct product/basis in review, readiness across an unchanged rerun
and exactly one real generator call. Existing stale-selection, missing planning,
rehydration mismatch and A/B no-regeneration coverage remains intact.

Focused result: **11 passed, 22 deselected in 13.48 seconds**. The initial added
dataframe assertion failed twice because AppTest does not expose its widget key;
the test locator was corrected to identify the unique review table by columns.
That initial run was **9 passed, 2 failed** and is not a successful receipt.
Ruff lint/format checks on the changed test and `git diff --check` passed.
No full suite, frontend/build, packaging, encoder or final CI was run.

External screenshots and raw browser receipts:

- `/Users/macbook/Hack/.archimind-08f3a/r3a/prepared-enabled.png`
- `/Users/macbook/Hack/.archimind-08f3a/r3a/generated-two-alternatives.png`
- `/Users/macbook/Hack/.archimind-08f3a/r3a/browser_preparation.json`
- `/Users/macbook/Hack/.archimind-08f3a/r3a/browser_generation.json`

Console: zero errors and one Plotly Canvas2D readback performance advisory.
No screenshot, GLB or external evidence file was added to Git.

### Storage and stopping boundary

Eight regular readings ran approximately 30 seconds apart; maximum interval
**30.068116 seconds**, with a final separate reading after monitoring ended.
Initial available capacity was **13,297,131,520 bytes**, minimum observed
**12,127,096,832 bytes**, and final **12,139,970,560 bytes**.
One interval lost **1,069,273,088 bytes (1,019.738 MiB)** while allocated swap
rose from **5 to 6 GiB**. Work paused when the alert was observed. Two subsequent
intervals stayed below the sharp-loss threshold, allowing this bounded task to
resume under the R3A plan. No second sharp decline or capacity-floor breach
occurred. Coincidence with swap growth is not complete causal attribution.
Periodic samples do not prove continuous or future storage stability.

The task-owned Streamlit server and finite observer were stopped; no owner
application was terminated, and no cleanup occurred. Historical report objects,
R1/R2 entries and the original Markdown prefix are preserved. All other tracked
files match their R3A starting hashes, including R2 implementation, qualification
records, assets, catalogs, geometry and retrieval artifacts.

No commit, push or new CI run: this narrow correction to verification depends
on the unfinished R2 integration. **Full checkpoint 3 remains pending**, including
2D/3D A/B acceptance, narrow-screen inspection, recovery scenarios, complete
regression/build/packaging checks and final delivery. No later furniture task began.


## R3B — generated-layout browser evidence; storage stop

2026-10-31: **BLOCKED_RECURRING_STORAGE_LOSS**. The historical status name is
retained, but the confirmed R3B rule stopped on its **first** sharp-loss interval.
R3B is not fully accepted; checkpoint 3 remains uncommitted.

### Storage and preservation

Local and remote `main` matched `b4b6115ff0d74108c927c1a9d633b4718eb69c98` at
preflight. All 13 existing modified tracked files were preserved. Fourteen regular
samples ran from **18:07:42.750 to 18:14:12.982 EDT**, maximum interval
**30.025592 s**. Initial capacity: **11,169,325,056 bytes**. The final regular
interval lost **390,586,368 bytes (372.492 MiB)** in **30.017870 s**, leaving
**10,778,255,360 bytes**. Allocated swap rose from **7 to 8 GiB**; causation is
unproven. Browser acceptance ended upon observing the alert and did not resume.

The separate final reading at **18:14:32.030 EDT** was **10,748,039,168 bytes**,
the minimum observed. The task-owned server was terminated; the observer had
exited on its alert. No reserve breach, cleanup, owner-app termination or broad
storage investigation occurred. Periodic samples do not prove continuous stability.

### Actual application observations

The ordinary `app.py` ran at `http://127.0.0.1:8771`, seed **42**, in the existing
**5 × 4 × 2.7 m** room. No standalone Three.js fixture was loaded. Each recorded
generation returned **two validated alternatives in five attempts**.

| Scenario | Revision | Browser observation |
| --- | ---: | --- |
| Belaya only | 1 | Plotly/Three.js A/B coordinates agree; one textured mesh, scale 1 |
| Belaya + procedural bed | 2 | A/B each show one native desk and a labeled procedural bed |
| Charles + Belaya | 3 | Explicit mixed-scene restriction; two placeholders, no new GLB request |
| Charles only | 4 | One native Charles mesh; received bytes match its pinned SHA |
| Morava only | 5 | Metadata-only wardrobe placeholder; no model request |
| Rivet nightstand only | 6 | Metadata-only table placeholder; no model request |
| Missing/corrupt/recovery | 7 | Faults produce placeholders; restoring responses recovers native Belaya |
| Narrow Belaya workflow | 8 | 390 × 844 selection, preparation, generation, A/B, viewer changes and orbit/reset observed |

Belaya ID: `catalog:abo-b074l4976t-amazon-co-uk:1`. Layout A position:
**(3.4, 3.1981268227100372)**; Layout B: **(0.83, 3.1981268227100372)**.
Both retain **1.6 × 0.8018731772899628 × 0.7516312003135682 m**. Displayed
scores: **93.139053 / 90.566198**. Labels and rendered-content digests identify
observations; complete server candidate hashes were not captured. Zero yaw is
required by the unchanged V3 contract and consistent with the rendered axes;
a separate raw server yaw/binding audit was not run before the stop.

Actual GLB response: **3,135,676 bytes**, SHA-256
`2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e`.
Three.js reported one textured mesh, **812 triangles**, scale **1.0**, floor
contact and bounds contained using the existing **1e-6 m** comparison tolerance.
Saved images show the desk appearance, walls, openings and footprint placement.
The registry release reference is recorded separately; it is not mislabeled as
an independently captured server binding.

A/B mounts reused the product without additional GLB loads and marked old roots
cleanup complete. One rapid, insufficiently settled switch reset camera/controls;
that observation remains in the receipt. Subsequent completed-rerun B→A→B kept
controls and viewpoint, with exact final A→B camera equality. No source defect
was isolated or fixed. Direct generator/validator counts and broader rapid-switch
robustness remain pending. One active selected canvas is bounded evidence, not
proof of universal leak freedom or total GPU-memory limits.

### Fallback, narrow-view and focused checks

Interception affected only local Belaya responses. Missing used intentional HTTP
**404**. Corrupt used HTTP **200**, unchanged length and a flipped response byte,
with SHA `6f1164023748b8c718e0bb80a8fdccc648ddf627d007c0241af78cebc957e81f`.
The committed GLB was never edited. Both faults yielded a partial viewer and
asset-unavailable placeholder while preserving dimensions and displayed validation.
Removing interception and reopening restored the original hash and native mesh.
The intentional 404 caused one expected network console error; one Plotly Canvas2D
performance advisory was recorded. No other acceptance-session console error was
captured before shutdown.

At verified **390 × 844**, Generate enabled after preparation and generation
succeeded. Both alternatives loaded natively; Plotly switching, orbit/reset,
wrapped attribution/status and essential controls were usable. Reset/front-wall/
footprint controls remained inside the viewport. This is resized Chromium,
not physical-phone or GPU-performance certification.

Focused existing integrity/stale-binding/fallback tests: **8 passed, 4 deselected
in 1.34 s**. No new test or production correction. No full suite, frontend build,
packaging, encoder or CI ran. The stale-binding **browser** harness was not run;
offline tests do not replace it.

Automation limitations: the initial dropdown interaction needed retry after load
settled. A premature companion capture still showed revision 1 and is excluded
from acceptance; `belaya-bed-verified.json` contains valid revision 2 evidence.
Later actions used a read-only completed-rerun counter and required revision
advance. No fabricated ready state, forced click or validation bypass was used.

### Evidence and remaining boundary

Raw receipts and screenshots remain outside Git in
`/Users/macbook/Hack/.archimind-08f3a/r3b/`. Key images:
`belaya-A-plotly-desktop.png`, `belaya-A-three-desktop.png`,
`belaya-B-plotly-desktop.png`, `belaya-B-three-desktop.png`,
`mixed-A-placeholders-desktop.png`, `belaya-missing-desktop.png`,
`belaya-corrupt-desktop.png`, `belaya-recovered-desktop.png`,
`belaya-B-three-narrow.png`. The structured addendum records per-scenario bounds,
coordinates, request hashes, times, control measurements and limitations.

Outstanding: stale/invalid-binding browser rejection/recovery; direct server call
counts and full candidate/binding/release identity capture; resolution or explicit
qualification of rapid overlapping-switch behavior; consolidated full acceptance.
**R3B_BROWSER_ACCEPTANCE_PASSED is not claimed.** R3C remains separate and unstarted.

Only this report pair changed during R3B. Prior R1/R2/R3A objects and Markdown
remain intact. No commit or push; `.agents/` and `.claude/` untouched.

## R3B2 — Remaining browser gaps; first-alert storage stop

**2026-10-31 UTC — `BLOCKED_RECURRING_STORAGE_LOSS`. Browser acceptance is not closed.**
HEAD and remote `main` matched `b4b6115ff0d74108c927c1a9d633b4718eb69c98` at
preflight. All 13 unfinished tracked changes were preserved. R3B's ordinary-app
acceptance remains historical evidence; completed product/narrow-screen scenarios
were not repeated. No production or test source changed in R3B2.

Raw artifacts are outside Git at
`/Users/macbook/Hack/.archimind-08f3a/r3b2/`: starting diff/hashes, external launcher,
`server.jsonl`, `browser.json`, screenshots, capacity samples/alert/final reading,
summary and preservation ledger. The paired JSON adds only `r3b2`; prior objects
and this Markdown's prior text remain unchanged.

### Storage and stop timing

The preliminary `df` reading was **8,156,774,400 bytes** (timestamp not separately
captured). The independent observer recorded seven samples from **22:35:55.384**
to **22:38:55.692 UTC**, at intervals **30.020–30.144 seconds**. Initial and minimum
monitored availability was **8,852,959,232 bytes (8.245 GiB)**; maximum was
**13,528,096,768 bytes**. The first sharp-loss alert recorded
**1,266,139,136 bytes (1,207.484 MiB) lost in 30.057 seconds**, leaving
**12,261,957,632 bytes**. The capacity floor was not crossed; the independent
sharp-loss condition required stopping regardless of remaining capacity.

Allocated swap stayed **7,168 MiB**; used swap ranged **5,618.31–5,781.19 MiB** in
the regular samples. Memory-pressure raw value stayed **2**. There was no swap-file
allocation growth explaining this alert; the writer/source is unverified.

**Observation limitation:** the observer wrote the alert at 22:38:55.692. The next
browser call issued rapid selections at **22:39:00.903–22:39:01.120**, and its trace
continued through **22:39:03.108**, before the assistant read the alert at the next
tool boundary. This is a monitoring-response gap, not an interval of established
stability. Those rapid observations are retained as diagnostics and excluded from
pre-alert acceptance. The observer did not automatically stop the server. No
further acceptance interactions, tests or corrections followed alert observation.
A continuation should check the alert before each browser call and provide prompt
alert delivery during calls without manipulating owner processes.

The browser was detached to `about:blank`, the task-owned Streamlit server shut
down gracefully, and the finite observer exited. No owner application was stopped.
The post-stop reading at **22:39:25.126** was **10,366,525,440 bytes (9.655 GiB)**;
used swap was **5,611.06 MiB**, allocated swap unchanged. No stability claim covers
the post-alert interval. No cleanup or broad disk investigation occurred.

### Binding faults — external harness, actual app workflow

A private external entrypoint invoked unchanged `app.py`. Pass-through wrappers
recorded actual browser-session server objects. Fault mode altered only copied
render evidence or an in-memory release read; it did not modify canonical objects,
session readiness, packaged release files, GLBs or production endpoints. Before
fault injection, the harness was restarted once to retain native Python types in
copied sidecars. Both independent sessions had one explicit Generate click.

The V3 wire contract has `envelope_sha256` and `render_version`; it does **not**
carry arbitrary asset-version or release-digest fields. Asset versions and the
pinned render-release digest are checked upstream. Tests therefore exercised the
supported upstream checks rather than inventing wire fields.

| Controlled case | Injected evidence | Actual adapter/browser outcome |
| --- | --- | --- |
| Invalid planning digest | Copied Belaya envelope digest replaced with 64 zeroes | `invalid_planning_binding`; one labeled placeholder, zero textured instances/new GLB requests |
| Mismatched asset version | Copied envelope asset version `9.0.0` | `invalid_planning_binding`; one placeholder, zero textured instances/new requests |
| Stale release | In-memory Belaya release `render_version` changed to `0.9.0`, expected release digest unchanged | `asset_release_unavailable`; one placeholder, zero textured instances/new requests |
| Authentic evidence restored | Fault flag cleared, original reader/sidecars | One native Belaya, scale 1.0; one successful local GLB request |

The restored response was **3,135,676 bytes**, SHA-256
`2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e`.
No Charles/substitute request occurred. The generation digest/revision, exact WDH,
zero yaw, scores and passing validation remained unchanged through faults and
recovery. Screenshots show the labeled box and subsequently the native desk.

These are **instrumented-app Chromium fault observations**, not a new ordinary-app
pass. The detailed rejection reasons were retained in server adapter diagnostics;
the viewer labels its placeholder. The detailed UI dataframe was not captured as
text/screenshot, so its visible reason wording remains unverified here. The
missing-network distinction is supported by the separate reason codes and zero
requests. No malformed raw V3 binding was sent through the browser.

### Actual server identity and counts

The launcher recorded `is` comparisons against the stored `candidate.design`, plus
SHA-256 of sorted compact JSON (`model_dump(mode="json")`, `allow_nan=False`).
These are **canonical-content digests**, not application-issued candidate IDs.
The direct observations belong to instrumented live sessions, not AppTest objects.

| Identity | SHA-256 / value |
| --- | --- |
| Prepared bundle content | `346951658213fae5e062cdcceb315e7c04723b82ddbfa9c0bf5146b225026f3f` |
| Submitted source specification | `f6a7d9b1a6afdb7596d90e9b20dfa7974540c4180124cab0d7d1c9b90c217388` |
| Stored generation result | `208f6c6743162e2ca06ce7785b171f497d18b99415979eb45c8d0a3b05fe479c` |
| A design content | `72b80803694b9476fe7f3152c546e77d9ca0b40ea46205cd87c14095e6a73bfc` |
| B design content | `ee9deff9141e0d654f2cb58d9c43aa187e63a71a619c54fae54d13b0f3c5b499` |
| Planning furniture sidecar | `e0cd9bcab0319c846bdafb417a896328b2560c0c4a80f518b2c2a1e43247c156` |
| Approved envelope | `f2b706c8111e5f9321d3d90856d914a60ab63aebdb0cf30dd4b8847f493723a5` |
| Catalog record | `e53ea735e094c49ce9fa432dbf9432cc86a6984e111d7a27a9aa6dfc65eb0387` |
| Trusted render-release pin | `cd07d2fa367f34c0ba3a7ea67a016d6f380d3165b51f83ed8992ddfa11ab4e55` |

Both sessions reproduced revision **1**, seed **42**, two alternatives/five attempts.
Furniture ID is `catalog:abo-b074l4976t-amazon-co-uk:1`; A position is
`(3.4, 3.1981268227100372)`, B `(0.83, 3.1981268227100372)`. Both retain
**1.6 × 0.8018731772899628 × 0.7516312003135682 m**, yaw **0**. Each candidate's
complete score/report is in the raw server receipt.

Each session recorded **one generator invocation and two UI acceptance-validator
calls**. A/B switches and the observed orbit/control changes added **zero** calls.
The two validator calls are only the UI's acceptance checks: generator-internal
spatial evaluations were not counted, so this is not a total-validation count.
Both A/B floorplans and Three.js received the exact stored candidate objects;
selected Plotly schematic 3D A was observed directly. Plotly schematic 3D B remains
covered by historical R3B browser evidence, not this new server trace. A fresh
explicit Generate within the same session and its revision increment were
**not reached**. Two separate sessions at revision 1 cannot prove that requirement.

### Camera/control persistence — unresolved host-remount finding

Before the alert, the first awaited A→B→A→B series preserved the custom camera
and unchecked controls for B, then reset them on A. The old root's cleanup marker
was `complete`; its observer no longer saw the replacement in the original shadow
root. This first series inferred a host replacement but did not directly label
host identities. A second B→A→B→A→B series directly tracked one host through four
settled replacements: camera/target and both unchecked controls persisted, each
mount reported zero new GLB loads and one active viewer canvas.

The later **post-alert diagnostic only** rapid sequence requested A, then B→A→B
while Streamlit reported `running`. The trace directly records host **1** disappearing
and host **7** mounting with default camera/front-wall/footprint controls. The final
server result committed B; two interrupted `run_start` records have no matching
`run_end`, and no completed intermediate selections are invented.

This supports a **host-remount persistence defect/limitation**, not simply a stale
radio label. The existing scene manager stores view state by host in a `WeakMap`;
its state does not survive replacement of that host. Why Streamlit replaced it in
these runs and the smallest safe correction remain unverified. No production fix
or regression test was attempted after the storage stop. A separately controlled
selection during remount and ordinary-entrypoint reproduction remain outstanding.
No universal leak or GPU-memory claim follows from sampled single-canvas traces.

### Verification, preservation and remaining work

No Python/frontend tests, Ruff, build, packaging, encoder, CI, commit or push ran.
Only saved-artifact JSON/hash reconciliation and historical preservation checks
were performed after the stop. Eight connection-refused console errors and one
service-restart warning belong to the deliberate external-harness server restart;
one later Plotly Canvas2D advisory was recorded. No console error occurred during
the copied-binding faults/recovery. A fourth local model request belongs to the
post-alert diagnostic host replacement and is not counted as accepted recovery.

**264 other tracked files are byte-identical to the R3B2 starting worktree**,
including all existing unfinished source/tests, catalogs, approved assets/releases,
geometry, renderer bundles and retrieval evidence. Historical report JSON objects
and Markdown prefix are preserved. Only the qualification report pair changed
relative to the R3B2 start; all work remains unstaged/uncommitted, with the original
13 modified tracked paths and protected `.agents/`/`.claude/` unchanged.

Remaining prerequisites before R3C: re-establish storage readiness and prompt
alert handling; reproduce/correct the host-remount issue with a focused regression;
verify same-session explicit regeneration and remaining control call counts;
repeat the core path through ordinary `app.py`, including visible rejection reasons;
run focused trust/identity/lifecycle tests. R3C then owns full regression, packaging,
final acceptance reconciliation and CI. It has **not** started automatically.

## R3B3 — Owner-scoped host-remount persistence

**2026-10-31 UTC — `HOST_REMOUNT_PERSISTENCE_VERIFIED` for the focused lifecycle
contract. This is not final Belaya release or full browser-acceptance closure.**
The expected HEAD and remote `main` matched
`b4b6115ff0d74108c927c1a9d633b4718eb69c98`. All unfinished checkpoint-3 work and
historical reports were preserved. No commit or push occurred.

### A. Root cause

The original `createSceneManager()` in
`frontend/realistic_viewer/src/scene_lifecycle.js` stored each mounted entry under
its disposable host. Its cleanup deleted that entry, and a different host had no
entry from which to capture the previous camera. The `WeakMap` was behaving
correctly; the ownership boundary was shorter than the required view lifetime.
Installed Streamlit source also generates its frontend component key per mount,
so that key is not a stable substitute.

The selected UI created `st.empty()` before rendering the Three.js component later
in the rerun. Streamlit's installed `EmptyMixin.empty()` enqueues an empty element,
introducing an avoidable clearing transition. Historical R3B2 runtime traces
established actual host replacement. This task does not assert that an empty delta
is the sole possible cause of every Streamlit remount.

### B. Narrow correction

`src/archimind/ui/layout_generation.py` now creates a stable selected-Three.js parent
container keyed `selected-realistic-owner-<generation revision>`. A/B changes retain
it; Plotly and empty results remove it, while a new generation has a different key.
The styling sequence, exact candidate handoff and display ordering are unchanged.

The frontend entrypoint resolves this explicit ancestor outside the component
shadow root. The scene manager accepts an internal optional owner, defaulting to
the host for existing standalone callers. Its owner-keyed `WeakMap` saves only
copied position/target arrays and `userCamera`, front-wall and footprint booleans
when a host is disposed. It captures before cleanup, releases scene resources and
clears active references. A replacement under the same owner/room restores that
snapshot; a new owner or room gets default framing.

Active-entry ownership checks and idempotent cleanup prevent an obsolete callback
from altering a replacement. Detached hosts/owners cannot supersede a live scene.
Existing disposed-scene guards still prevent late asset completions from attaching.
There is no global string-key cache, browser storage, new endpoint, scene-wire
field or product-authority change. The asset pool's **250 ms** release grace is
unchanged: immediate replacement reuses its load; a request after eviction is
legitimate and separately tested.

### C. Deterministic regressions and focused checks

The new direct teardown/remount test first failed against the old implementation:
**7 passed, 1 failed**, with `viewState=null` instead of the saved snapshot.
After the correction, all eight passed. Eleven new lifecycle cases now cover
explicit owner handoff, copied capture before disposal, settled and overlapping
replacements, delayed cleanup, late asynchronous completion, detached hosts,
independent owners/rooms, pool reuse/eviction, invalid state, rejected mount
recovery and shadow-host owner resolution.

Final focused results:

- **82 frontend tests passed**, zero failures/skips: lifecycle, room, product and
  Belaya suites. Existing binding/hash/budget/Charles/native-placement tests remain.
- **56 Python tests passed in 32.85 s**: catalog-generation UI, selected-realistic
  adapter and Belaya rendering. One added test checks parent identity across A/B,
  exact stored-object handoff, no A/B generation/revalidation, removal on Plotly
  and empty outcomes, and new identity on explicit generation. Its initial isolated
  run also passed; that repeat is not counted as another unique test.
- **One bundled-asset test passed**, 28 unrelated tests deselected.
- Frontend syntax, changed-Python Ruff lint/format, product-registry check and
  `git diff --check` passed.
- Two builds through the existing `npm ... run build` process produced byte-equal
  results across **24 viewer-asset files**. Only `viewer.js` differs from the starting
  asset tree; no manual minified edits. New bundle SHA-256:
  `955aa651b06abbdfaa28dc78f6563119cfcd881a00e846c2c9b9ac28e688d66e`.

Lifecycle canvas/listener/control counts use instrumented mount doubles, not an
actual GPU. Existing resource tests and real browser cleanup markers provide
separate corroboration. There is no universal memory-leak or GPU-bound claim.
Two existing Three.js texture-serialization warnings occurred in frontend tests;
all assertions passed. No full Python suite, installed-wheel packaging, encoder,
final CI or R3C work ran.

### D. Ordinary-app browser observation

One ordinary `app.py` session on local port **8773**, Chromium **1440 × 1000**, used
the 5 × 4 × 2.7 m room, seed 42 and Belaya only. This was not a server-wrapper or
fault-injection session. The known configuration produced two alternatives in five
attempts. The selected V3 view showed the native approved desk.

After setting a nondefault orbit and turning both toggles off, the requested
sequence was **B→A→B**. The A request occurred while Streamlit reported `running`;
no disabled-control bypass or forced DOM replacement was used. Final selected B
showed furniture `catalog:abo-b074l4976t-amazon-co-uk:1` at
**(0.83, 3.1981268227100372)**, with unchanged reservation
**1.6 × 0.8018731772899628 × 0.7516312003135682 m**, native scale **1.0**.

Observed owner **2** and host **1** stayed stable. Scene roots **3→4→5→6** changed;
all three old roots were detached with `cleanup=complete`. Front walls and
footprints remained **false**; target remained **[2.5, 1.35, -2]**. The nondefault
camera was retained, with small continuing damping differences: recorded position
changed from `[6.945393404577174, 10.972586300711445, -4.094958485710645]` to
`[6.944006797803328, 10.973112068389273, -4.095485240522542]`. These are not claimed
bit-identical, and no new placement or camera tolerance was introduced.

**Actual host replacement did not occur in this ordinary-app run.** Genuine
old-host teardown/new-host restoration is established by the deterministic
regression, not by a forced browser fixture. The browser verifies supported rapid
selection with the stable parent. No new server call-count instrumentation was
added; exact-object/no-regeneration assertions come from the focused Python tests,
separate from historical R3B2 live-server evidence.

### E. Resources and console

The browser recorded exactly **one** Belaya GLB request, HTTP **200**, **3,135,676
bytes**, SHA-256
`2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e`.
A/B switches added **zero** requests. The final scene had one canvas, one textured
desk and zero placeholders; setup was approximately **0.17 s**. No browser console
errors were observed. One initial Plotly Canvas2D readback advisory preceded the
custom console listener; the listener recorded no subsequent messages.

Screenshot: external `r3b3/ordinary-belaya-B.png`. Raw browser JSON includes
requests, lifecycle transitions, owner/host/root identities, camera and metrics.
This resized desktop Chromium run makes no physical-device performance claim.

### F. Storage and observer limits

The independent finite observer recorded **nine samples**,
**22:51:47.489–22:55:47.694 UTC**, with intervals **30.018–30.035 s**. Initial and
minimum availability: **13,924,843,520 bytes (12.969 GiB)**. Final observer reading:
**14,956,060,672 bytes (13.929 GiB)**. Largest interval loss:
**145,420,288 bytes (138.684 MiB)**. **No first-alert or floor stop occurred.**
Allocated swap decreased **7,168→6,144 MiB**; final used swap was **5,615.88 MiB**.
Memory-pressure raw value stayed 2. These readings do not identify disk writers or
establish future stability.

The external observer publishes `STOP.json` by atomic replacement on the existing
threshold. Task test/build supervision polls at 0.2 s and can stop only its own
worker process group. Browser actions each checked the signal first and used
bounded waits; in-flight browser calls cannot poll the local signal, so that
response limitation remains explicit. No alert occurred and no post-alert browser
acceptance was claimed. Abort behavior was prepared, not experimentally triggered.

The browser was detached to `about:blank`, the task-owned server shut down normally,
and the observer exited after the completion signal. No owner process was stopped;
no cleanup, swap manipulation or storage-policy change occurred. The four-minute
sample window does not prove stability between samples or after observer exit.

### G. Preservation and Git

Exactly these eight paths changed relative to the R3B3 starting worktree:

- `frontend/realistic_viewer/src/main.js`
- `frontend/realistic_viewer/src/scene_lifecycle.js`
- `frontend/realistic_viewer/tests/lifecycle.test.js`
- `src/archimind/_viewer_assets/viewer.js`
- `src/archimind/ui/layout_generation.py`
- `tests/test_catalog_generation_ui.py`
- `docs/data/ASSET_QUALIFICATION_BELAYA_08F3A.md`
- `docs/data/ASSET_QUALIFICATION_BELAYA_08F3A.json`

**258 other tracked files match their starting hashes.** The prior contents of the
already-modified catalog UI test are preserved as an exact byte prefix; the new
regression is appended. Historical qualification JSON objects and the Markdown
prefix remain unchanged. Asset bytes, catalogs/search documents, planning/render
releases, registry, room viewer, asset pool, geometry/scoring/validators and frozen
retrieval evidence are untouched. `.agents/` and `.claude/` remain protected.

HEAD remains `b4b6115ff0d74108c927c1a9d633b4718eb69c98`. There are now **18 modified
tracked paths** including existing unfinished work; nothing is staged, committed
or pushed. External evidence lives under
`/Users/macbook/Hack/.archimind-08f3a/r3b3/` with hashes, original diff, logs,
screenshot, browser receipt and a non-self-referential manifest.

### H. Decision and remaining boundary

**`HOST_REMOUNT_PERSISTENCE_VERIFIED`** applies to the tested owner/host contract.
The ordinary browser confirmed rapid-selection state retention but did not undergo
host replacement. This does not close all prior acceptance gaps or authorize a
release. Same-session browser regeneration remains outstanding and was not attempted.
R3C still owns full integration regression, packaging, overall acceptance
reconciliation and CI. No standalone lifecycle commit was made and R3C did not start.


## R3B4 — Same-session regeneration: storage stop before second Generate

**BLOCKED_RECURRING_STORAGE_LOSS.** Observed 2026-11-01 UTC. Baseline remains
`b4b6115ff0d74108c927c1a9d633b4718eb69c98`. No application defect was established
and no production implementation changed in this continuation. The first actual
browser generation completed; the required second click was not attempted.

### A. Storage and stop response

Four finite observer samples ran from 2026-11-01T05:24:56.939962+00:00 to
2026-11-01T05:26:27.072902+00:00, over 90.136 seconds.
Initial available capacity was **13,737,582,592 bytes**
(12.794 GiB), maximum **13,748,699,136 bytes**,
and final/minimum **12,660,301,824 bytes**
(11.791 GiB). Repository and temporary directory
shared the APFS pool. The independent samples were 30.024–30.087 seconds apart;
no observation gap is hidden. Sequential repo/tmp readings need not be identical.

The FIRST sharp-loss alert occurred at **2026-11-01T05:26:27.072902+00:00**:
**979,255,296 bytes (933.891 MiB)** lost over
**30.087 seconds**. Absolute free space stayed above 2 GiB
and the 1 GiB reserve, but the explicit sharp-loss rule independently requires
stopping. No automatic resumption followed the remaining capacity or any rebound.
Allocated swap rose from 7 to 8 GiB in the alert interval; used swap across the
four samples was 6234.88, 6185.81, 6960.12 and 6660.81 MiB. Pressure stayed raw 2.
This concurrent swap allocation is not a complete causal attribution of APFS loss.
No broad investigation or cleanup was performed.

The observer atomically published STOP.json. The 0.2-second polling supervisor
terminated only its task-owned app process group. The first browser shutdown
warning was at 05:26:27.243 UTC, approximately 0.17 seconds after the alert.
The next acceptance call checked STOP and dispatched no browser action. The
observer and server exited; the owned browser page was returned to about:blank.
Post-alert log export and shutdown errors are diagnostic only. Browser tool calls
are not preemptible mid-call; here generation settled at 05:26:24.880 UTC, before
the alert, and no acceptance action was in flight when the alert was observed.

### B–C. Session and first explicit generation

The actual Streamlit script was unchanged `app.py` on local port 8774 at
1440 × 1000. External `launch_observed.py` wrapped existing function aliases,
passed inputs and returned objects unchanged, and logged allowlisted values
without writing application session state. These are same-agent instrumented
observations, not independent production telemetry. A separate uninstrumented
run was not completed in R3B4; historical R3B3 ordinary-app evidence is preserved.

One hashed session identity, **90b1ed6dc8d306b5**, spans eight observed reruns.
Visible controls selected catalog mode, deselected all procedural items, selected
Belaya, and explicitly prepared the specification. Generate became enabled with
seed 42. The sole browser Generate click occurred at **05:26:24.249 UTC** and
settled at **05:26:24.880 UTC** with **revision 1**, **one generator call**,
**two UI acceptance-validator calls**, **two passing candidates**, **five search
attempts**, and zero reported violations. The validator count excludes internal
search checks. Preparation/reruns before the click invoked neither counted API.

Both candidates retain `catalog:abo-b074l4976t-amazon-co-uk:1`, zero yaw and exact
Policy B reservation **1.6 × 0.8018731772899628 × 0.7516312003135682 m**.

| Candidate | Position x, y (m) | Score | Canonical design SHA-256 |
| --- | --- | ---: | --- |
| A | 3.4, 3.1981268227100372 | 93.139053 | `72b80803694b9476fe7f3152c546e77d9ca0b40ea46205cd87c14095e6a73bfc` |
| B | 0.83, 3.1981268227100372 | 90.566198 | `ee9deff9141e0d654f2cb58d9c43aa187e63a71a619c54fae54d13b0f3c5b499` |

These are calculated content digests, not application-issued candidate IDs.
Prepared digest: `346951658213fae5e062cdcceb315e7c04723b82ddbfa9c0bf5146b225026f3f`.
Result digest: `208f6c6743162e2ca06ce7785b171f497d18b99415979eb45c8d0a3b05fe479c`.
The 2D and Plotly 3D calls both received the exact stored A design object, as
observed with Python identity comparison. Full canonical values, reports, score,
source specification and snapshot are retained in the private server receipt.

### D–G. Outstanding browser acceptance

The stop occurred before post-generation A/B navigation, Three.js selection,
camera/control actions, the second Generate, pending edits or reprepare. Therefore
**revision 2 is NOT VERIFIED in an actual browser**, and no native mesh or live
camera-persistence claim is added by R3B4. No GLB request occurred. Dedicated
Plotly trace capture and screenshots were not reached. The first-render textual
browser state and server object handoff do not substitute for those missing
visual observations. Before the alert there was one Plotly Canvas2D readback
advisory and no captured console error. Shutdown produced WebSocket close and
connection-refused messages; they are retained separately as expected diagnostic
consequences of stopping the server. No pageerror event was captured.

### H. Focused offline verification

Before the alert, **57 Python tests passed in 46.08s**, with no failures/skips,
covering catalog generation UI, selected adapter and Belaya rendering. All **18
frontend lifecycle tests passed**, including R3B3 host replacement, cancellation,
camera/control snapshots and pool reuse. Changed-test Ruff lint/format and
`git diff --check` passed before the stop. No full suite, build, packaging, encoder
run or CI was performed.

The only new test is `test_belaya_same_session_regeneration_and_pending_recovery`.
It uses the real generator and validations with existing offline tripwires. Two
explicit AppTest clicks produce revisions 1/2, generator counts 1/2 and UI
acceptance counts 2/4; a new result object correctly has identical deterministic
content. A/B handoff, exact dimensions/evidence, old/new result immutability,
stale pending selections and explicit reprepare without a third generation pass.
**AppTest proves the state contract, not completion of the missing browser gate.**
Existing tests remain byte-identical as the new test's prefix. A transient
insertion-position edit was corrected before the passing test run; an added
blank line was restored afterward without changing executable test statements.

### I–J. Preservation and delivery boundary

The starting ledger covers **266 tracked files**. Before report append,
**265 were byte-identical**, with only the new regression changing the test
file. Final task changes are that test and this historical report pair. Prior
Markdown is retained verbatim as a prefix and prior JSON objects are equal.
Catalogs, qualification/planning/render releases, native asset bytes, resource
budgets, geometry, validators, scores, retrieval artifacts and the R3B3 lifecycle
implementation remain byte-identical to the R3B4 start. All 18 preexisting tracked
modifications remain uncommitted. `.agents/` and `.claude/` were untouched.
HEAD and remote main matched at preflight; no staging, commit, push or CI occurred.

Raw records are outside Git in `/Users/macbook/Hack/.archimind-08f3a/r3b4`: starting diff/hash ledger, capacity samples,
STOP, supervised logs, read-only server observations, browser event export and
preservation/manifest records. There is no new screenshot. R3C and all remaining
browser gates are pending. **No task resumption or cleanup is authorized by this
blocked result.**


## R3B5 — Final same-session browser regeneration acceptance

**R3B_BROWSER_ACCEPTANCE_PASSED.** Observed 2026-11-01 UTC, using unchanged
`app.py`, desktop Chromium **1440 × 1000**, the 5 × 4 × 2.7 m room, seed 42,
Belaya only, and no procedural companions. The actual browser completed two
explicit Generate actions in one continuously running Streamlit session.
No production correction or new test run was needed. R3C remains unstarted.

### One-task storage authorization and actual observations

The owner explicitly replaced the earlier immediate-stop-on-200-MiB rule **for
R3B5 only**: require 6 GiB at launch; pause on a 200 MiB sharp loss; take three
additional samples about 15 seconds apart; resume at most once only with >=6 GiB,
no additional sharp loss or threatening trend, and healthy task processes. Stop
on <4 GiB, a >=2 GiB interval loss, another sharp warning after resumption,
uncontrolled decline or disk error. The absolute 1 GiB reserve remains mandatory.
This authorization neither revises historical storage stops nor applies to R3C.
The original request bytes and their hash are preserved externally.

A finite independent observer sampled both repository and temporary-directory
APFS availability and swap every **15.009–15.041 seconds**, atomically publishing
state. Browser calls checked the gate before dispatch. The task server supervisor
polled for a hard-stop signal every 0.2 seconds. In-flight browser tool calls are
not preemptible; no warning occurred, so no interaction fell in a pause interval.
The configured reassessment/resumption branches were **not exercised**.

| Observation | Actual result |
| --- | --- |
| Samples / window | 10 / 05:43:52.947–05:46:08.148 UTC |
| Initial available | 14,768,058,368 bytes (13.753826 GiB) |
| Minimum / final available | 14,755,397,632 / 14,755,397,632 bytes (13.742035 GiB final) |
| Largest monitored loss over up to approximately 30 seconds | 6,111,232 bytes (5.828125 MiB) |
| Warning / pause / resume / hard stop | 0 / 0 / 0 / none |
| Allocated swap | 6,144 MiB throughout |
| Used swap, initial / final | 5,342.44 / 4,986.88 MiB |
| Memory-pressure indicator | Raw 2 throughout |

No sampling gap is hidden, and no swap-to-capacity causal attribution is made.
The app server and observer exited normally; only the task-owned process received
SIGINT. The owned browser returned to about:blank. No cache, application, backup,
environment or swap cleanup occurred.

### Same-session operation and authoritative accounting

Actual session identity was recorded as a hash, **`6f1f87f3b51d8456`**,
across 21 completed observed application reruns. The external read-only wrapper
invoked Streamlit with the ordinary `app.py` entrypoint, observing existing
callable aliases and allowlisted state without changing inputs, results or
session state. Call counts and Python object identity are **instrumented-app
evidence**, not independent production telemetry. Visible controls, Plotly traces,
existing Three.js DOM metrics, responses and screenshots are browser evidence.
No separate uninstrumented server run was performed in R3B5.

| Operation | Browser click UTC | Revision | Generator calls | UI acceptance validations | Result observation token |
| --- | --- | ---: | ---: | ---: | ---: |
| Explicit Generate #1 | 05:44:25.610 | 1 | 1 | 2 | 1 |
| Explicit Generate #2 | 05:45:04.580 | 2 | 2 | 4 | 2 |
| Final navigation / pending edit / reprepare | No third click | 2 | 2 | 4 | 2 |

The tokens are private observation ordinals backed by retained object references,
not application-issued IDs. They prove a new stored result object for Generate
#2. The counts cover UI acceptance validation only; generator-internal spatial
checks are not included. Each operation returned **two passing candidates in five
attempts**, with zero reported violations. Both retained the exact approved
**1.6 × 0.8018731772899628 × 0.7516312003135682 m** reservation and zero yaw.
A/B and renderer changes invoked neither counted generator nor UI validator.

| Layout | Position x, y (m) | Score | Canonical design SHA-256 |
| --- | --- | ---: | --- |
| A | 3.4, 3.1981268227100372 | 93.139053 | `72b80803694b9476fe7f3152c546e77d9ca0b40ea46205cd87c14095e6a73bfc` |
| B | 0.83, 3.1981268227100372 | 90.566198 | `ee9deff9141e0d654f2cb58d9c43aa187e63a71a619c54fae54d13b0f3c5b499` |

These are calculated canonical-content digests. The same seed legitimately
returned the same A/B content across revisions. Prepared specification digest:
`346951658213fae5e062cdcceb315e7c04723b82ddbfa9c0bf5146b225026f3f`.
Result digest: `208f6c6743162e2ca06ce7785b171f497d18b99415979eb45c8d0a3b05fe479c`.
Stored source specifications, planning sidecars, reports, scores and candidates
agree across the two operations; the revision and stored result identity changed.

### Selected-view geometry, appearance and lifecycle

Both revisions' Plotly and Three.js calls received their **exact stored selected
candidate design objects**. Actual selected Plotly trace metadata/coordinates and
Three.js instance metrics agree for A and B. Belaya remained a textured native
mesh at **scale 1.0**, one mesh / **812 triangles**, with no placeholder. Inspected
images show the original light wood material and distinct room positions, with
floor contact and room openings retained. Per-instance native bounds remain
inside the unchanged canonical volume under the existing **1e-6 m** numerical
comparison tolerance; no new placement tolerance or fit scaling was introduced.

Two local GLB responses were captured, each **HTTP 200**, **3,135,676 bytes**, SHA-256
`2568fab387096a98eb58b12dc6906995a251c005a189b078808e074612b88a3e`.
The first was the initial mount; the second followed switching to Plotly and
reopening Three.js after the existing **250 ms** pool grace. A/B switches and
immediate generation replacement reused the asset. No extra source model or
concurrent duplicate request was observed. Initial room setup reported **373.5 ms**,
revision-1 B replacement **202.9 ms**, generation-2 A **148.0 ms**, and reopened B
**496.8 ms**. These are existing viewer setup metrics, not isolated network,
encoder, GPU-memory or physical-device measurements.

Nondefault camera and both toggles off persisted across A/B under the same DOM
owner. Revision-2 A→B preserved exactly the recorded position
`[10.367827868607593, 7.415812546743959, 2.2482635830036557]` and target
`[2.5, 1.35, -2]`; both toggles remained false. Earlier orbit samples still had
small damping changes, so bit-identical state is not claimed for those samples.
The second Generate created a different owner with deterministic default framing
and both toggles true. Closing/reopening Three.js likewise created fresh defaults.
One selected-view canvas remained at each settled capture; every recorded old
root was disconnected with `cleanup=complete`. No same-owner host replacement
occurred during this run; that case retains the historical R3B3 deterministic
coverage rather than a new live claim. Bounded observations do not prove universal
leak freedom or total GPU-memory bounds.

### Pending edits and scope of view persistence

Checking the pending Queen bed selection disabled Generate because preparation
was stale, while the stored revision-2 result object, selection, candidates,
bindings, scores and validation reports remained unchanged. Restoring the
original selection restored readiness; an additional visible Prepare action
also passed. Counts stayed **2 generator / 4 UI validations**, with no third
Generate or implicit result replacement.

Restoring the pending selection also reinserted a **different DOM owner** and
reset camera/toggles to defaults. This is explicitly narrower than persistence
across every possible UI rerun: the verified contract preserves state within the
same owner and resets across owners. The required A/B continuity and pending
result-preservation checks passed. No universal pending-control camera retention
claim is made.

### Console, minimal verification and preservation

There were **zero captured console errors / page errors** and one Plotly Canvas2D
readback advisory. Three initial hidden radio-input click attempts timed out due
to intercepted pointer events; ordinary visible-label clicks then succeeded.
There were no forced clicks, fabricated readiness or application edits for the
harness. Six screenshots and the raw browser/server records remain outside Git.

No new code change or contradiction justified rerunning tests. R3B4's **57 focused
Python / 18 lifecycle passes** remain historical results, not new R3B5 runs.
A standard-library evidence reconciliation checked same-session counts, fresh
result tokens, exact geometry/object handoff, native bounds, GLB hashes, stale
preparation/reprepare, camera/toggles and preservation. No full suite, build,
packaging, encoder or CI ran.

All **266 tracked files** were byte-identical to task start before report append.
Only this Markdown/JSON pair changes in R3B5; prior Markdown remains an exact
prefix and all prior JSON objects are preserved. The existing 18 modified tracked
paths remain uncommitted. `.agents/`, `.claude/`, approved assets, catalogs,
qualification releases, Policy B reservations, budgets, canonical geometry,
validators, scoring and frozen retrieval evidence remain untouched.

HEAD remains `b4b6115ff0d74108c927c1a9d633b4718eb69c98`; remote main matched at
preflight. No staging, commit, push or fresh CI claim is made. Evidence is under
`/Users/macbook/Hack/.archimind-08f3a/r3b5` with request, initial diff/hash ledger, storage observations, browser/server
records, screenshots, reconciliation and final manifest. **No remaining applicable
R3B5 browser gate is outstanding.** R3C release verification and delivery remain
separate and were not started; the one-task storage exception does not carry over.


## Delivery checkpoint — November 1, 2026

After R3B5, the owner requested updated status/documentation and commit/push of
accumulated work. This checkpoint includes the existing R2 workflow, R3B3
owner-scoped lifecycle correction, R3B4 regression and R3B5 browser evidence.
Current README/status/catalog/renderer guidance now reflects two approved native
products, the same-session acceptance result, mixed-scene restriction and owner
lifetime limits. Historical reports are retained. A dated before/after hash chain
records authorized documentation and attribution changes without replacing R2 pins.

Review found a hard-coded “Amazon.com” label in generic product attribution even
for the UK Belaya record. The generic caption now retains product/variant, ABO
source and CC BY 4.0 credit without asserting the wrong marketplace. Product
identity, license, model bytes, geometry and qualification authority are unchanged.
Current checks and actual commit/CI identities are in the delivery response. No
new browser matrix, asset acquisition, encoder or separately scoped R3C work is
claimed by this delivery checkpoint.

Local delivery checks: 93 focused Python cases initially passed; two frozen-file
checks exposed missing R3B3 migration links. A premature retry reproduced those
failures before the ledger was written. After adding verified historical-to-current
links, both checks passed: 95 distinct focused cases passed across runs. Frontend
91/91, syntax, byte-identical rebuild of 24 viewer files, Ruff (180 formatted files),
dependency compatibility, registry, HTTP 200 health and diff checks passed. No
full local Python suite is claimed; the new pushed CI run checks the full snapshot.
