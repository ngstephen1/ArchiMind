# Furniture retrieval human-review packet — 08F1

**PENDING HUMAN REVIEW — UNEVALUATED. Completed human reviews: 0.**

Prepared 2026-10-29 by the implementation agent. All **24 prompts are machine-authored**;
none has a machine-proposed relevance answer, human judgment or retrieval score.
This document is preparation material, not a new gold benchmark, model evaluation,
threshold-development set or independent adjudication. Do not add it to 08R0/08R1.

## Owner-first review protocol

Primary reviewer identity or role: ____________________

Review date/time and timezone: ____________________

Evidence/corpus revision reviewed: ____________________

Optional second reviewer identity/role and date: ____________________

Adjudicator identity/role and date, if needed: ____________________

1. Read the scope and evidence cards before judging. Review independently of
   model rankings; none is provided. Identify which scope you are assessing.
2. Judge **hard eligibility separately from semantic relevance**, using the actual
   product evidence. Record a row for each considered card ID; duplicate the blank
   row if necessary. A semantically relevant source lead can still be ineligible.
3. Use hard-eligibility values `eligible`, `ineligible` or `insufficient_evidence`.
   In the current-application scope, only packaged records can be eligible. All
   prospective leads remain outside the active catalog. Qualification is not room-fit
   certification; real geometry, circulation and clearances still require validation.
4. Use semantic labels `relevant`, `partially_relevant`, `irrelevant`, or
   `unsupported_request`. Relevant means the verified product function and stated
   requirements match. Partial means a genuine functional match with an unmet soft
   preference; never relax a hard size, identity, rights or qualification constraint.
   Irrelevant means a different function or contradicted requirement. Unsupported
   means the reviewed scope cannot establish a defensible recommendation. Record
   missing evidence rather than inventing a property or giving the nearest object.
5. Record query outcome `recommendation_supported`, `no_recommendation`, or
   `clarification_needed`, with reasons. Unverified finish/rail/clearance claims need
   evidence, not inference from an attractive title. Distinguish product dimensions
   from planning reservations and actual room fit. Ask for clarification when a
   requested dimension basis or ambiguous requirement matters.
6. Do not interchange desk/table, wardrobe/bookcase, dresser/wardrobe, or
   illustrative model/real product. A broad source category is not a functional
   equivalence. Review both positive-looking and unsupported-intent prompts without
   assuming an intended label from their wording or group.
7. A second reviewer is optional and should initially work without the first
   reviewer's labels. Retain both labels, disagreements and evidence; do not overwrite
   disagreement with a fabricated consensus. The owner records any final adjudication.
8. Before a later benchmark exists, freeze completed judgments, reviewer provenance,
   exact candidate/evidence scope and agreed relevance mapping in a **new** versioned
   artifact. Independent human review and explicit freezing remain outstanding.

## Evidence cards — current active catalog

These facts describe the unchanged packaged catalog `archimind-furniture`, version
1.0.0. Published dimensions are checked source claims, not independent physical
measurements. Current planning/render state comes from the approved sidecars/release,
not from source-shortlist membership. “Sod” and “Espresso” are source variant labels;
physical color/material/style fields are unqualified.

| Card | Stable asset/product identity | Published W × D × H, m | Generation reservation W × D × H, m | Current qualification |
| --- | --- | --- | --- | --- |
| A1 | `abo-b075x2x4xs-amazon-com` / B075X2X4XS; Charles, Sod | .9906 × .9906 × .9652; 39W × 39D × 38H inches | .996104896068573 × 1.0019413232803345 × .9760930538177491 (Policy B) | Packaged metadata, planning and current render release |
| A2 | `abo-b07pqs58xn-amazon-com` / B07PQS58XN; five-shelf bookcase, Espresso | .659892 × .381762 × 1.891792 | Same published dimensions used by current preparation | Packaged metadata only; no planning envelope or approved detailed mesh |

[Charles source](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz)
uses JSONL line 242; [bookcase source](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz)
uses line 191. Frozen source evidence and hashes are in
`data/catalogs/furniture_source_candidates_08a.json`; application evidence is in
`src/archimind/assets/furniture_catalog.json`, `planning_envelopes.json` and
`product_render_release.json`. Both source entries are subject to
[ABO CC BY 4.0](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt)
attribution/change-notice requirements. Review the [source register](FURNITURE_SOURCE_REGISTER.md).

Sheen Chair is a separately licensed illustrative demonstration, explicitly not a
real product. It has no manufacturer-qualified dimensions and is not a third active
product. See the [pinned author description](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair/README.md).

## Evidence cards — prospective source shortlist

**Not in the application.** These three records have source qualification only.
No model was downloaded, inspected, planning-qualified or render-approved by 08F1.
The following dimensions are published claims; actual model envelopes remain
unverified. Variant labels do not qualify physical colors, materials or styles.

| Card | Stable candidate/product identity | Variant / original model number | Published W × D × H | Primary locator |
| --- | --- | --- | --- | --- |
| S1 | `abo-b074l4976t-amazon-co-uk` / B074L4976T; Movian Belaya desk | Oak; T80505PL05LVO | 1.6 × .8 × .75 m; original width 160, length 80, height 75 cm | [listing part 6](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz), line 1065 |
| S2 | `abo-b07h8jn9qf-amazon-co-uk` / B07H8JN9QF; Movian Morava four-door/two-drawer wardrobe | Oak Sonoma; M4-R3181/R3181-20 | 2.0 × .59 × 2.12 m; original length 200, width 59, height 212 cm | [listing part 6](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz), line 1852 |
| S3 | `abo-b07b4vxxjc-amazon-com` / B07B4VXXJC; Rivet two-drawer nightstand | Brown; 320-C070-052 | .6096 × .4318 × .6096 m; original 24W × 17D × 24H inches | [listing part 3](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz), line 110 |

The [expansion receipt](FURNITURE_EXPANSION_08F1.json) includes exact response ranges,
hashes, source excerpts, joins, dimensions and resource evidence. All three have
ABO CC BY 4.0 obligations. Morava's **reported** model height is 2.158716440 m versus
the 2.12 m published claim; no planning envelope resolves this yet. Belaya's reported
depth/height and the nightstand's reported height also slightly exceed their
published boxes. No card proves space for a person, garment rail, drawers opening,
chair access or ergonomic use. Those claims require separate evidence.

No bed is source-qualified by this investigation. The Stark dresser B075YZ16V7 is
unresolved because English dresser text conflicts with localized Queen-bed titles.
Moselle B07H8T8ZS7 is a display cabinet/Vitrine lead with inconsistent dimensions,
not a verified clothing wardrobe. These gaps are evidence constraints, not human
relevance labels. Do not invent additional source cards to fill the six-card ceiling.

## Query group C — current application scope (12)

Assess only current active catalog facts and current planning/render status.
Prospective cards can be discussed in notes but cannot become active recommendations.

### C01

**Prompt:** I need the Sod armchair rather than a different Charles variant.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C02

**Prompt:** Show the Charles seat only if its planning width fits 1.01 metres.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C03

**Prompt:** I have a 0.995-metre-wide space and want the Charles chair.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C04

**Prompt:** Which catalog item could hold a row of novels on open shelves?

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C05

**Prompt:** I need the Espresso five-shelf unit, at most 1.9 metres tall.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C06

**Prompt:** Show a storage product that already has an approved detailed mesh.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C07

**Prompt:** I want a freestanding closet with doors and hanging space.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C08

**Prompt:** Find a workstation for a laptop and handwritten notes.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C09

**Prompt:** I want the armchair in a verified tan leather finish.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C10

**Prompt:** Show a real bed frame for a queen mattress.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C11

**Prompt:** Find Charles ASIN B075X2X4XS with an original source licence I can review.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### C12

**Prompt:** Can I use the Sheen demonstration as a dimension-certified product?

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

## Query group P — prospective coverage discussion (12)

Discuss semantic fit against the source cards and coverage gaps, while keeping
**current-application hard eligibility separate**. A source-only lead is not an
active product or permission to prepare/generate/render it. Record clarification
or missing evidence where appropriate; no proposal is admitted automatically.

### P01

**Prompt:** I need a desk around 1.6 metres wide and 0.8 metres deep with a curved top.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P02

**Prompt:** Show a writing desk no more than 1.2 metres wide.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P03

**Prompt:** I want a smaller writing desk that is already in the live catalog.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P04

**Prompt:** I need a cupboard for clothes with four doors and two drawers.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P05

**Prompt:** Find a mirrored wardrobe under 2.13 metres high.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P06

**Prompt:** I need a wardrobe with a verified hanging rail and garment clearance.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P07

**Prompt:** An open bookcase will not work; I need enclosed clothing storage.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P08

**Prompt:** Find a bedside unit with two drawers that is 24 inches wide.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P09

**Prompt:** I want a nightstand no more than 0.40 metres deep.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P10

**Prompt:** Show a six-drawer dresser whose product identity has no conflicting titles.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P11

**Prompt:** Find a compact twin bed frame with matching model dimensions.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

### P12

**Prompt:** I need a wardrobe and desk that already have approved meshes in the app.

| Reviewer | Candidate/card IDs considered | Hard eligibility | Semantic relevance | Query outcome | Rationale / evidence | Date |
| --- | --- | --- | --- | --- | --- | --- |
| Primary | | | | | | |
| Optional second | | | | | | |

Disagreement and final adjudication (if applicable): ____________________

## Review completion and future freeze — blank

Primary review completed: ____________________

Second review status, if any: ____________________

Outstanding disagreements/evidence: ____________________

Owner adjudication decision and date: ____________________

Final approved query IDs / scope: ____________________

Frozen artifact ID, SHA-256 and approving reviewer: ____________________

**Status remains pending until actual independent human review is supplied.**
No completed reviewer, relevance label, adjudication or benchmark approval has been
recorded by the implementation agent. Do not edit frozen 08R0/08R1 judgments or
thresholds to match this packet, and do not evaluate a model on unreviewed labels.
