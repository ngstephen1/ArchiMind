# Furniture source register — 08F1 update

**Current research register: 57 records, including 25 new candidates from 30 detailed
08F1 investigations. Three new acquisition-eligible source records; no bed qualifies.**

The active application still contains **two metadata-qualified products**, with
**one planning-envelope-qualified and one render-qualified product (Charles)**.
Nothing below expands that packaged catalog. The 08F1 appendix follows the preserved
historical report. Historical acquisition decisions are not current render approvals.

The 08A candidate JSON is now preserved byte-for-byte as
`data/catalogs/furniture_source_candidates_08a.json`, SHA-256
`cb3d5b7a7382a31ec96ec709f4fdcf6f90d9202275fe41f40c04391dc53ddc5d`.
The packaged catalog retains its original qualification pins. All 32 historical
candidate records remain unchanged in the expanded current register.

---

# Furniture source qualification register — Task 08A

**Result: 2 acquisition-eligible candidates; no complete bedroom set and no render-approved new assets.**

Checked **2026-10-28** against `main` at `28bcbdc5d5cb3d2236d7ab0cfb28565333212e86`. Target: a **noncommercial publicly hosted demo delivering asset bytes to browsers**. This is source qualification, not asset acquisition, a runtime catalog, supplier certification or a change to the application. Follow the [08A contract](../audits/REAL_DATA_IMPLEMENTATION_PLAN.md#08a--source-license-and-dimension-qualification) and [readiness audit](../audits/REAL_DATA_READINESS_AUDIT.md).

Only this register and `data/catalogs/furniture_source_candidates.json` are delivery files. The structured companion is committed in the second checkpoint. No model, image, texture, dataset archive, dependency or production code is added. Existing `.agents/` and `.claude/` content remains untouched.

## 1. Coverage and qualification decisions

31 distinct ABO product/model leads and the existing illustrative chair were investigated. Source-only investigations of Poly Haven and Kenney are not counted as individual models. This is a bounded sample, not an exhaustive search of ABO.

| Investigation category | Investigated | Eligible for acquisition | Needs evidence (unknown) | Excluded under current scope/budgets | Fixture only |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bed | 6 | 0 | 3 | 3 | 0 |
| Desk | 2 | 0 | 2 | 0 | 0 |
| Storage | 4 | 1 | 1 | 2 | 0 |
| Chair | 20 | 1 | 17 | 1 | 1 |
| **Total** | **32** | **2** | **23** | **6** | **1** |

`needs_evidence` is the plan's decision value for unresolved qualification; it is not a claim that the published source license is unknown. Five records have verified **published whole-item dimension claims and axis mappings**: the two eligible records plus three original-size budget exclusions. Twenty-six dimension contracts remain unknown; the existing chair is illustrative. Verified here means checked against authoritative source records, not independently measured against physical furniture.

The keyword hit B07MNYG18D is a **desk chair**, counted only as a chair. Three sofa-beds are bed-investigation leads but are excluded from the fixed-bedroom-bed scope; no canonical bed mapping is assigned. The qualified bookcase is appropriate book storage, **not a wardrobe replacement**. No wardrobe, bed or desk is acquisition-qualified.

## 2. Source and license comparison

| Source / primary evidence | Rights and access finding | Product/dimension result |
| --- | --- | --- |
| [ABO official release](https://amazon-berkeley-objects.s3.amazonaws.com/index.html#download), [license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt), [listing schema](https://amazon-berkeley-objects.s3.amazonaws.com/listings/README.md), [model conventions](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) | CC BY 4.0 covers the released dataset, including models/images. Public copying, browser delivery and commercial use are permitted under its conditions: attribution, license link, change notices, preserved notices, no endorsement and no additional restrictions. Documentation/metadata accessed without credentials. No acceptance form was submitted. | Strongest real-product source here, but dataset membership alone does not qualify a specific mesh. Item/variant evidence, exact model-ID join and reported extents were checked separately. |
| [Poly Haven asset license and website terms](https://polyhaven.com/license) | CC0 assets can be redistributed. Site text/example renders/logos have separate rights; website scraping is restricted. The [API README](https://raw.githubusercontent.com/Poly-Haven/Public-API/master/README.md) and [API terms](https://raw.githubusercontent.com/Poly-Haven/Public-API/master/ToS.md) distinguish live-service terms/credit from asset rights. | License documentation only: no API call, account, acceptance action or asset-page harvest. No concrete product/dimension record qualified. Next: obtain lawful asset-specific metadata and physical-dimension/product evidence; do not infer it from CC0. |
| [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit) | Official page lists 140 3D files and CC0, with bed/chair/table tags. Archive, thumbnails and individual models were not downloaded. | A game-asset collection is not manufacturer evidence. No exact bed/desk/storage model ID, actual item dimensions or real-product relationship verified. No individual candidate promoted from the collection. A table tag is not a verified desk. |
| [Pinned Khronos Sheen Chair author description](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair/README.md), [per-model notice](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair/LICENSE.md) | Model-associated content CC0; accompanying metadocumentation CC BY 4.0. Eric Chadwick, copyright 2020 Wayfair, LLC. Logos/trademarks excluded. Local license copy matches the pinned notice byte-for-byte. | Author explicitly says the model does not represent a real product. Existing fixture only; room-example dimensions never become product dimensions. Broader Khronos assets need individual review. |
| [Original FRONT agreement](https://gw.alicdn.com/bao/uploaded/TB1ZJUfK.z1gK0jSZLeXXb9kVXa.pdf?file=TB1ZJUfK.z1gK0jSZLeXXb9kVXa.pdf), [FUTURE agreement](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202004171628_60052.html) | The preceding audit verified research, redistribution and external-service restrictions. No authoritative additional permission was supplied in 08A. No assets acquired or included. | Excluded sources for this public-demo strategy. Mirrors do not supply an established exception. No invented individual candidate IDs or additional permission claim. |

The ABO copyright grant is documented; it is not independent proof of chain of title, trademark permissions, manufacturer endorsement or measurement accuracy. No new model-specific logos, embedded notices, PBR behavior or material appearance were inspected. Current retailer availability is not asserted. This register derives its product evidence from the official dataset snapshots, not live retailer pages.

### Attribution and modifications

ABO data credit: **Amazon.com**. Dataset contributors credited by the official release: Matthieu Guillaumin, Thomas Dideriksen, Kenan Deng, Himanshu Arora, Arnab Dhua, Xi (Brian) Zhang, Tomas Yago-Vicente, Jasmine Collins, Shubham Goel and Jitendra Malik. See [official attribution](https://amazon-berkeley-objects.s3.amazonaws.com/index.html#attribution) and the [CC BY 4.0 license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt).

Changes made to source metadata: selected fields extracted, unit conversions and review annotations added, records joined to the model index. No model/image/texture was downloaded or modified. Retain this attribution, license link and change description with the structured records and future derivatives. Khronos fixture provenance remains separately attributed to Eric Chadwick/Wayfair and the glTF-Sample-Assets contributors.

## 3. Method: identity, units and source-to-model checks

The [ABO listing README](https://amazon-berkeley-objects.s3.amazonaws.com/listings/README.md) identifies listings by **(item_id, domain_name)** and provides `3dmodel_id` as the model reference. The [model index](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/metadata/3dmodels.csv.gz) contains that ID, local model path, counts and extents. The index has 7,953 model rows. A same-ID join establishes a **declared association**, not automatic dimension or variant agreement.

Only the first **196,608 compressed bytes** of each `listings_0.json.gz` through `listings_9.json.gz` were retrieved, using HTTP Range and requiring 206 responses. Each full listing file is several megabytes and was not downloaded. Only complete decoded JSONL records were inspected; the incomplete final line was discarded. The structured file records the exact source URL, 1-based JSONL line, response range, response hash, ETag/last-modified, and SHA-256 of the original record line excluding its newline. Model-index hash and exact model ID provide the join locator. These are **metadata hashes**, never model hashes.

The source schema defines `item_dimensions` as product dimensions. Package dimensions were never used. Original numeric values/units are retained and converted independently using exact Decimal factors: inches × 0.0254, centimeters × 0.01, millimeters × 0.001. The dataset's own rounded normalized fields are not conversion authorities.

Width/depth cannot be assigned blindly from `length`/`width` field names: several bed/desk/chair records use length for front width. Explicit whole-item dimension text, domain/locale, product type and same-ID native extents were compared. Unresolved category, pose, quantity or variant conflicts keep the canonical dimension contract unknown. Localized statements were inspected for conflicts, not merged into a new invented product. A dimension claim can be retained while the candidate remains unqualified.

The [ABO conventions](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) specify +Y up, natural front +Z, and floor-standing objects centered in X/Z with their bottom at Y=0. [glTF 2.0 defines linear units as meters](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units). These are source conventions, **not per-asset verification** of decoded bounds, anchor or content. No bounds minimum/maximum, extensions or model SHA-256 is invented for an unacquired asset. Reported extents are labeled metadata values.

## 4. Candidate-level evidence

ABO IDs below each join the listing's `3dmodel_id` to the same model-index key. `part:line` points into that source JSONL stream. Links identify the official metadata file; send `Range: bytes=0-196607`, decode the prefix, and select the complete line. Full individual identities, product/model URLs, variant labels, original dimensions, metadata counts, evidence pointers and qualification reasons are retained in the structured companion.

### Bed investigation

| Candidate / official listing evidence | Variant / intended use | Decision and specific finding |
| --- | --- | --- |
| [B07B4SCB6T](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) (part 0, line 180) | Stone & Beam Tisbury Nailhead Trim Queen Bed, 66"W, Spinnsol Cocoa | `needs_evidence` — English queen dimensions conflict with king-size localized titles. The separate king ASIN has exactly the same reported model extents, so variant-to-model identity is unresolved. |
| [B07B4VY14V](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_9.json.gz) (part 9, line 205) | Amazon Brand – Stone & Beam Tisbury Nailhead Trim King Bed, 84"W, Curious Charcoal | `needs_evidence` — 84-inch king width converts to 2.1336 m, but model extent X is 1.7127519846 m and exactly equals the queen model extent. Hold variant identity. |
| [B07R15L3TD](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_5.json.gz) (part 5, line 96) | AmazonBasics, Dark Grey 3 Seater Sofa Bed 204 x 85 x 81 cm | `excluded` — Sofa-bed, not a fixed bedroom bed. Title/item height 81 cm and explicit bullet height 85 cm disagree; deployed sleeping configuration is unsupported/unverified. |
| [B086B5P473](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) (part 7, line 72) | solimo Sofa Cum Bed Luxe | `excluded` — Convertible sofa-bed in a sofa-sized envelope; sleeping configuration and mattress support are not established. Excluded from the fixed-bedroom-bed scope. |
| [B086B68MGZ](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_2.json.gz) (part 2, line 269) | solimo Sofa Cum Bed | `excluded` — Convertible sofa-bed in a sofa-sized envelope; sleeping configuration and mattress support are not established. Excluded from the fixed-bedroom-bed scope. |
| [B086TG9Q4V](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz) (part 3, line 24) | AmazonBasics Metal Bed with Modern Industrial Design Headboard - 14 Inch Height for Under-Bed Storage - Wood Slats - Easy Assemble, Queen | `needs_evidence` — The 14-inch item height is a frame/under-bed measurement, while the headboard model is about 0.967 m high. Overall height is not established. |

### Desk investigation

| Candidate / official listing evidence | Variant / intended use | Decision and specific finding |
| --- | --- | --- |
| [B07QC8772Q](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_4.json.gz) (part 4, line 66) | Amazon Brand – Ravenna Home Springdale Modern Desk, 47"W, White | `needs_evidence` — English title/bullets describe a 47-inch desk, but a localized title describes a children's chair. Keep the category/model linkage unresolved instead of silently selecting one claim. |
| [B084S6TSK7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) (part 8, line 17) | Amazon Brand - Movian -Drawer Console Desk, 100 x 80 x 40 cm, High Gloss White | `needs_evidence` — Item height is 60 cm, title and explicit W/H/D bullet height are 80 cm, model height is about 79 cm. Overall height unresolved. |

### Storage investigation

| Candidate / official listing evidence | Variant / intended use | Decision and specific finding |
| --- | --- | --- |
| [B07GFF11HV](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) (part 6, line 211) | Amazon Brand - Movian Indre 1-Door Shoe Cabinet/Cupboard/Organizer with Mirror, 23 x 50 x 179cm, Dark Grey | `excluded` — Item dimensions and model axes are consistent, but HEAD advertises 19,019,208 bytes, above the planned 15 MiB GLB budget; textures are 4096 px. Excluded as an original-size MVP asset. |
| [B07PQS58XN](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) (part 7, line 191) | AmazonBasics Classic 5-Shelf Open Bookcase Organizer with Solid Rubber Wood Frame - Espresso | `eligible_for_acquisition` — Espresso five-shelf open bookcase, model SH01-0606-008-SG-A05; listed item axes agree with same-ID model extents to less than 0.8 mm. Appropriate bedroom book storage, not a wardrobe. |
| [B07PXFVNXR](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) (part 8, line 36) | Ameriwood Home Classic 5 Drawer Dresser, White | `excluded` — Item dimensions and native model axes agree closely, but HEAD advertises 21,712,432 bytes, above 15 MiB, with 4096 px textures. Excluded as an original-size MVP asset. |
| [B07TSTJM5G](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_1.json.gz) (part 1, line 151) | Amazon Brand - Movian 2 tier MDF modular bookcase, Brown/White, 30 x 29 x 60 cm | `needs_evidence` — Title says 30 x 29 x 60 cm, item fields say 29.7 x 29 x 59.4 cm, model extents approximately 30 x 29 x 60 cm. Do not silently round away the discrepancy. |

### Chair investigation

| Candidate / official listing evidence | Variant / intended use | Decision and specific finding |
| --- | --- | --- |
| [B0723H8D37](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_2.json.gz) (part 2, line 145) | Amazon Brand – Stone & Beam Highland Modern Living Room Wingback Accent Chair, 32"W, Denim | `needs_evidence` — Published width/depth can be read from English bullets, but model extent X is about 5.7% below the stated width; resolve whether the model matches that variant. |
| [B075NR8HWJ](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) (part 0, line 167) | Amazon Brand Movian Dofsan Chair 100 x 93 x 86 cm Grey | `needs_evidence` — Title/item height is 86 cm, while English bullet height is 96 cm. No single unambiguous item-height contract. |
| [B075X2X4XS](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) (part 7, line 242) | Amazon Brand – Stone & Beam Charles Classic Oversized Leather Accent Arm Chair, 39"W, Sod | `eligible_for_acquisition` — Source-scoped Sod variant, model number LTD26020C, one armchair. Item fields and explicit overall dimensions agree; same-ID model extents corroborate axes within 1.15%. |
| [B075X33SSW](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) (part 7, line 248) | Amazon Brand – Stone & Beam Elmore Pillow-Top Armless Accent Chair, 24"W, Beige | `needs_evidence` — Model X/Z extents disagree with explicit overall width/depth by roughly 3.3%/6.8%; do not infer a dimension-grounded match. |
| [B07B4CZMNQ](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) (part 6, line 124) | Amazon Brand – Stone & Beam Andover Modern Living Room Accent Chair, 38"W, Linen | `needs_evidence` — Model width is about 14.7% above the 38-inch item width; investigate model/product mismatch. |
| [B07BZNXCWX](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_1.json.gz) (part 1, line 304) | Amazon Brand – Rivet Contemporary Leather Office Chair, 31"H, Black | `needs_evidence` — Adjustable height and declared 31.1-34.1-inch range do not explain the roughly 0.9221 m model height. Resolve full base/pose envelope. |
| [B07DBFSLH1](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_4.json.gz) (part 4, line 179) | Amazon Brand – Ravenna Home Sherman Curved Faux Leather Accent Chair, 30.5"W, Brown | `needs_evidence` — Published whole-chair dimensions are explicit, but model width exceeds them by about 2.28%; resolve envelope/variant mismatch. |
| [B07DBJQC1K](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) (part 7, line 23) | Amazon Brand – Ravenna Home Christian Upholstered mid-Century Modern Accent Chair, 31.89"W, Beige | `needs_evidence` — Model height is about 6.36% above item height; source-size-to-model agreement unresolved. |
| [B07F2X8K62](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) (part 0, line 164) | Amazon Brand – Ravenna Home Radford Modern Curved Arm Accent Chair, 28.15"W | `needs_evidence` — No item_dimensions or complete English dimension bullet is present. Title supplies width only; do not derive product dimensions from mesh extents. |
| [B07HSF3Y4B](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) (part 8, line 152) | Amazon Brand – Stone & Beam Leonardo Dining Room Kitchen Chair 41.5 Inch Height, Set of 2, Dove Grey | `needs_evidence` — Set-of-two identity and markedly larger model extents leave per-unit dimensions/model quantity unresolved. |
| [B07MNYG18D](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_9.json.gz) (part 9, line 273) | AmazonBasics Modern, Low-Back, Adjustable, Swivel, Armless Office Task Desk Chair with Casters, Brick Red | `needs_evidence` — This is a desk CHAIR, not a desk. Full caster/base envelope is wider/deeper than the listed chair dimensions; resolve per-pose footprint. |
| [B07N2YYSXK](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_2.json.gz) (part 2, line 126) | AmazonBasics Classic Faux Leather Extra Padded Recliner Chair - Brown | `needs_evidence` — Recliner state and width/depth axis interpretation are unresolved; model extents do not establish the complete usable/closed item envelope. |
| [B07P5LNMMS](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_4.json.gz) (part 4, line 137) | Amazon Brand – Ravenna Home Pull Recliner with Rotating 360 Swivel Glider, Living Room Chair, Fabric, Beige | `needs_evidence` — Swiveling/gliding recliner with L/W rather than physical front-width/depth labels. Static pose and orientation semantics require evidence. |
| [B07QCQ1J7M](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) (part 6, line 5) | Amazon Brand – Rivet Contemporary Welt-Trimmed Dining Chair, 35"H, Felt Gray, Set of 2 | `needs_evidence` — Set-of-two listing: item fields, title and dimension bullet disagree on width/depth/height. Per-unit model identity and dimensions unresolved. |
| [B07Y5Y1264](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_4.json.gz) (part 4, line 118) | AmazonCommercial Classic Folding Chair, 4-Pack, White Granite | `needs_evidence` — Four-pack folding-chair listing; per-chair versus pack identity and unfolded envelope have not been established from the metadata alone. |
| [B082QDDJV9](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) (part 7, line 205) | Amazon Brand – Rivet Bayard Contemporary Leather Living Room Chair with Curved Back and Armrests, 35.5"W, Cognac | `needs_evidence` — Title/bullets width 35.5 inches conflicts with item width 34.25 inches; same-ID model follows the narrower measurement. Variant sizing unresolved. |
| [B082VL6WKP](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) (part 8, line 296) | Amazon Brand – Stone & Beam Shorebrook Deep Upholstered Accent Chair, 27.6"W, Cream | `excluded` — Explicit whole-chair bullet dimensions agree with model extents, but HEAD advertises 54,982,380 bytes, above 15 MiB, with 4096 px textures. Excluded as an original-size MVP asset. |
| [B082VMTPJY](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_9.json.gz) (part 9, line 96) | Amazon Brand – Rivet Frederick Mid-Century Modern Tufted Velvet Living Room Chair, 38"W, Grey | `needs_evidence` — Item and rounded bullet dimensions differ, and model height is below the stated full height by about 2.7%; agreement needs clarification. |
| [B0856FQQKH](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_9.json.gz) (part 9, line 116) | AmazonBasics Armless Bistro Dining Chair - Set of 2, White, Premium Plastic | `needs_evidence` — Set-of-two listing with no explicit English per-chair dimension bullet. Per-unit versus set/model representation needs confirmation. |
| [Sheen Chair](https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/8f492390ddc7a2ae221a1369ef560589cf8c70fb/Models/SheenChair/README.md) (pinned existing fixture) | Sheen Chair — Mango Velvet (existing illustrative fixture) | `fixture_only` — Verified existing CC0 illustrative renderer fixture, explicitly not a real product; no manufacturer dimension claim. |

## 5. Acquisition shortlist — exactly two entries

An acquisition-eligible status verifies the required **source rights, item/model identity, category and published item dimensions** for 08A. It authorizes no download in this task and confers no render approval. Residual 08C checks are explicit rather than hidden.

| Candidate | Original whole-item W × D × H | Canonical metric W × D × H | Reported native model X × Y × Z (m) | HEAD size / metadata |
| --- | --- | --- | --- | --- |
| **B075X2X4XS**, Stone & Beam Charles oversized armchair, **Sod**, model **LTD26020C**, amazon.com | 39 × 39 × 38 inches; item fields and explicit overall-dimension bullet agree | **0.9906 × 0.9906 × 0.9652 m** | 0.9961048961 × 0.9760930538 × 1.0019413233 | **4,252,440 bytes**; 1 mesh, 42,706 faces; 3 texture/image resources, 2048 px maximum |
| **B07PQS58XN**, AmazonBasics five-shelf open bookcase, **Espresso**, model **SH01-0606-008-SG-A05**, amazon.com | 25.98 × 15.03 × 74.48 inches; source width/length/height mapped and corroborated against native axes | **0.659892 × 0.381762 × 1.891792 m** | 0.6603998316 × 1.8922999969 × 0.3809882714 | **11,661,068 bytes**; 1 mesh, 54,996 faces; 3 texture/image resources, 4096 px maximum |

Primary record links: [Charles listing, part 7 line 242](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz), [bookcase listing, part 7 line 191](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz), [model index](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/metadata/3dmodels.csv.gz). Original GLB locations, **not fetched**: `3dmodels/original/S/B075X2X4XS.glb` and `3dmodels/original/N/B07PQS58XN.glb` under the official ABO host. Successful HEAD checks confirm object size/existence only; ETags are not promoted to SHA-256.

The Charles armchair's source `material` field says “stone” despite its leather description. No physical-material claim is certified; retain original PBR materials only after inspection. Bookcase dimensions have no conflicting numeric title/bullet in the inspected record. It is open book storage, not clothes storage, a wardrobe or a desk chair.

**No approved render binding exists.** Reported meshes slightly exceed some stated dimensions: Charles maxima differ by about 5.5/10.9/11.3 mm in X/Y/Z; bookcase by about 0.5/0.5/-0.8 mm. These are reported-extent comparisons, not measured bounds. Acquisition-quality agreement is not the plan's strict canonical-volume gate. 08C must inspect the real assets and resolve envelope accuracy, or preserve placeholders. Never resize a validated footprint or silently shrink a product model. The bookcase's 4K textures also require a reviewed bounded derivative before the planned 2048 px / decoded-memory runtime limits can pass. No derivative or preparation tooling is implemented here.

### Verified dimension claims on excluded original-size candidates

| Candidate | Evidence / metric W × D × H | Why it is not shortlisted |
| --- | --- | --- |
| B07GFF11HV, Movian Indre shoe cabinet, dark grey, model T31136MM07LVO | Item W=50, D=23, H=179 cm → **0.5 × 0.23 × 1.79 m**, corroborated by model axes | **19,019,208 bytes** by HEAD, greater than 15 MiB; 4096 px textures. Not a wardrobe. |
| B07PXFVNXR, Ameriwood Classic five-drawer dresser, white, model 3658015ACOM | Item W=27.72, D=15.67, H=49.37 inches → **0.704088 × 0.398018 × 1.253998 m**, corroborated by model axes | **21,712,432 bytes** by HEAD, greater than 15 MiB; 4096 px textures. |
| B082VL6WKP, Stone & Beam Shorebrook accent chair, cream, model KF.A1030C-C-1281 | Explicit overall W=27.6, D=33.9, H=35.8 inches → **0.70104 × 0.86106 × 0.90932 m**; raw item fields retained as rounded equivalents | **54,982,380 bytes** by HEAD, greater than 15 MiB; 4096 px textures. |

Exclusion is under the **current original-size MVP acquisition policy**, not a revocation of source copyright permission or a claim that no optimized derivative could ever work. Reopening requires a separately scoped acquisition/preparation proposal; 08A does not change budgets or add a download path. None of these larger GLBs was downloaded.

## 6. Existing Sheen Chair — verified illustrative fixture

Local path: `src/archimind/_viewer_assets/furniture/SheenChair.glb`. Rechecked size **4,125,648 bytes**, SHA-256 **f0af2a2b102d28d540236306ae19f8fb36842df76bd38cf76f063f9bd2853399**, matching local provenance. Pinned source revision: **8f492390ddc7a2ae221a1369ef560589cf8c70fb**. Local structural inspection: 4 meshes, 6 materials, 7 embedded images; texture-transform, sheen and material-variant extensions. No remote GLB read occurred.

The author's explicit non-product statement takes precedence over any appearance of manufacturer realism. Mango Velvet is the existing default; Peacock Velvet is an alternate material variant, not another product/SKU. Canonical fixture dimensions and proportional fitting are illustrative. Product ID, item dimensions and manufacturer-qualified bounds remain null; status is `fixture_only`, dimension status `illustrative`.

## 7. Blockers and next actions

1. **Beds:** the Tisbury queen/king IDs share identical reported model extents despite different published widths; an additional frame height is not headboard height. Obtain unambiguous overall dimensions and actual variant/model confirmation before considering a bed. Sofa-bed leads do not fill this gap.
2. **Desks:** resolve the Springdale localized category conflict, or the Movian 60/80 cm height conflict, with authoritative product/model evidence. A chair containing “desk” in its title is not a desk.
3. **Wardrobe:** no wardrobe record qualified. One open bookcase does not replace the requested furniture function. Small/tall storage leads need source or budget resolution.
4. **Model preparation:** both shortlisted entries still need real-file integrity, extension/resource, mounting/pose, anchor, bounds and material checks. The bookcase needs texture-budget work. Existing canonical dimensions/validators remain authoritative; metadata-only qualification is not a license to fit anything into any footprint.
5. **Alternatives:** Poly Haven requires lawful model-specific metadata/product-size evidence, not website scraping. Kenney's collection needs exact model/size evidence and may remain illustrative. No public FRONT/FUTURE asset use without authoritative additional permission.

**08B can begin with two actual source-qualified metadata entries** after review: one armchair and one open bookcase. It cannot claim a complete bedroom catalog, verified meshes or render-ready assets. 08B remains unimplemented; do not acquire these models or start later stages as part of this checkpoint.

## 8. Budget, reproducibility and verification

Application response-body bytes received: **2,532,416 bytes (2.415100 MiB)**, below **5,242,880 bytes**. Maximum body in one response: **340,528 bytes**, below **1,048,576 bytes**. Ten 196,608-byte listing excerpts, the 340,528-byte compressed model index, small license/docs pages and 49,152 bytes of the glTF specification were inspected. No full listing file, model, image, texture or dataset archive was retrieved. Model HEAD requests received **zero body bytes**; their advertised object lengths are not downloaded bytes. Local decompression and HTTP headers are not counted as downloaded metadata bodies.

All request receipts, source URLs/ranges, body sizes and received-file hashes are retained in the structured companion. The initial six Python TLS attempts failed before any body was received; retrying used the existing system trust store without disabling TLS verification. Two nonexistent decimal-index listing URLs returned 404 with no error-body read; no absence-of-data inference follows. Only successfully received parts 0–9 were sampled. No hidden browser/web-search downloads, login, API inference, license acceptance or paid requests occurred.

Selected metadata identity checks:

| Received metadata | SHA-256 of received bytes |
| --- | --- |
| `abo-models.csv.gz` | `90d061c3e3efa555a55bfc8ed7fc55cdb322086397443de1b33e91f7924d7d92` |
| `abo-license.txt` | `419896aea50c15d6e40c5b4baf4bd346f78223b9a354c7357ad00262afdc08ec` |
| `abo-listings-readme.md` | `2a1c8c84dbe2e4f419db28be538fc353f22bff3540cbd48fc534497d74b12193` |
| `abo-models-readme.md` | `01d8c8b2ea90ab30b29979f77e7550deccc4a2b981ee71d4f5ee3ffdb894db86` |
| `listings-7-prefix.gz` | `12a0f37f5dd743b9eeeb5b98365efa1461e800bf5692c61b4865f3f82f54b458` |

Standard-library validation checks schema version/target/date, sorted unique candidate IDs, status domains, finite positive original measurements, exact unit conversions, complete normalized dimensions/evidence for eligible records, same-ID model joins, source snapshots and locators, model-download counters and transfer budgets. Eligibility decisions were manually reviewed against the primary record fields and model-index rows; strict success does not require a qualified candidate in every category. JSON counts must match the coverage table and shortlist exactly.

Only the two intended text/data paths may be staged. `git diff --check`, staged-diff inspection, remote synchronization and resulting CI runs are checkpoint gates. CI executes the unchanged full Python/frontend suite; no production behavior changed and no tests were weakened. Exact commit hashes and final CI outcomes are reported in the delivery response, avoiding self-referential commit hashes in this document.

**Stop after 08A.** No 08B catalog, ingestion, rendering, canonical-model, validator, UI or AI-agent work has been performed.


---

# 08F1 — bounded source expansion, 2026-10-29

This section is current research. Earlier sections are the unchanged **08A historical
report**, including its then-current status and next-task statements. Reassessments
below supplement rather than replace those findings. No asset acquisition occurred.

## Coverage of this task

| Investigation group | Reviewed this task | Newly added IDs | Eligible | Needs evidence | Excluded |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bed | 8 | 5 | 0 | 8 | 0 |
| Desk | 8 | 6 | 1 | 4 | 3 |
| Wardrobe / dresser leads | 8 | 8 | 1 | 2 | 5 |
| Additional furniture | 6 | 6 | 1 | 5 | 0 |
| **Total** | **30** | **25** | **3** | **19** | **8** |

Five historical records were revisited: the original Tisbury Queen/King, metal
headboard bed and both original desk leads. Their recorded conflicts persist.
The cumulative stored register has 57 records: **5 historical/current acquisition
eligibility decisions, 37 needs-evidence, 14 excluded and 1 illustrative fixture**.
This combines historical source decisions, not 57 acquisition approvals or products
in the app. The older bookcase decision remains preserved despite its known 4096 px
texture obstacle. The **new 08F1 shortlist contains only the following three IDs**.

## New acquisition shortlist — source evidence only

| Product / source | Variant label | Published W × D × H, m | Original measurements | HEAD bytes | Reported texture maximum |
| --- | --- | --- | --- | ---: | ---: |
| [Movian Belaya desk, B074L4976T](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | Oak; title says Light Brown Oak-Effect | 1.6 × 0.8 × 0.75 | Width 160, length/depth 80, height 75 cm | 3,135,676 | 2048 px |
| [Movian Morava 4-door / 2-drawer wardrobe, B07H8JN9QF](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | Oak Sonoma; title says Light Brown Oak-Effect | 2.0 × 0.59 × 2.12 | Length/front width 200, width/depth 59, height 212 cm | 2,362,880 | 2048 px |
| [Rivet two-drawer mirror-panel nightstand, B07B4VXXJC](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz) | Brown | 0.6096 × 0.4318 × 0.6096 | 24W × 17D × 24H inches | 1,298,676 | 2048 px |

These are checked **published claims**, not physical measurements. Exact source
records join official model-index rows and model URLs; native models have not been
retrieved. Each passes the existing source-level agreement screen
`max(0.01 m, 2% of each published dimension)` using **reported** extents. This does
not establish strict envelope containment, actual units/anchor, embedded resources,
material appearance, native-scale placement or render qualification.

Morava's reported model height is 2.158716440 m versus the 2.12 m published claim.
It passes the 2% acquisition screen but cannot be assumed to fit the published box.
A later inspection/reconciliation task must preserve both quantities and derive any
planning reservation through the approved process. Do not shrink or silently resize
it. Belaya's reported height/depth also slightly exceed the published dimensions;
all three require actual-file containment/placement inspection.

## Candidate decisions and primary locators

Each link identifies an official listing stream. `part:line` is its 1-based complete
JSONL record location. The candidate JSON retains the exact requested prefix,
response hash, original record-line hash, model join, item fields, conversions and
missing evidence. HEAD lengths are not downloaded model bytes; ETags are not SHA-256.

| Product ID / source | Group | New | Part:line | Decision | Finding |
| --- | --- | --- | --- | --- | --- |
| [B071FJR46L](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_2.json.gz) | additional | yes | 2:553 | `needs_evidence` | Published 24W x 16D x 23H inches agrees with item fields, but reported model X/Y/Z is about 26/28/33% larger; product-to-model envelope remains unresolved. |
| [B075X2WN36](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | additional | yes | 6:424 | `needs_evidence` | Published 28.7W x 29.9D x 31.1H inches is explicit, but reported mesh width/height exceed those claims substantially. Do not replace the product size with mesh extents. |
| [B075X543WR](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_4.json.gz) | additional | yes | 4:382 | `needs_evidence` | Published 32W x 36D x 37H inches is explicit; reported mesh width/depth are smaller by more than 2%. Resolve product/variant/model agreement before acquisition. |
| [B07B4VXXJC](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz) | additional | yes | 3:110 | `eligible_for_acquisition` | Brown mirror-panel two-drawer bedside nightstand; explicit 24W x 17D x 24H inches and item fields agree. Same-ID model metadata agrees within 2%; original size and texture metadata meet budgets. Localized warranty noise is not used as product evidence. |
| [B07B7JY9C5](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_9.json.gz) | additional | yes | 9:399 | `needs_evidence` | Whole-item height conflicts: item field 18.25 inches versus explicit bullet 18.75 inches; native X/Z also suggest a different front/axis assignment. No authoritative resolution. |
| [B07BZQQP5G](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz) | additional | yes | 3:693 | `needs_evidence` | Adjustable 36–39-inch height is a range, not a verified static model pose. Reported full base/depth differs from 21W x 16.5D inches and model height is below the stated range. Caster/pose envelope unresolved. |
| [B075XZMMG7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | bed | yes | 6:582 | `needs_evidence` | Item fields 83.5L x 77.1W x 39.6H inches conflict with explicit overall bullet 85L x 80.3W x 44.5H inches. Neither dimension set is silently selected. |
| [B07B4SCB6T](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) | bed | revisit | 0:180 | `needs_evidence` | Historical queen/king localized-title conflict persists. Queen and King B07B4VY14V share exactly the same reported extents despite 66-inch versus 84-inch width claims. |
| [B07B4VSW78](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | bed | yes | 6:1105 | `needs_evidence` | Fresh Dune queen: explicit 66W x 92D x 56H inches and item fields agree, but reported depth 2.386691689 m differs from 2.3368 m by 2.135%, beyond max(0.01 m, 2%). |
| [B07B4VY14V](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_9.json.gz) | bed | revisit | 9:205 | `needs_evidence` | Historical King has identical model extents to the Queen despite an 84-inch width claim. Preserve the unresolved variant/model conflict. |
| [B07B4W5V3C](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) | bed | yes | 0:989 | `needs_evidence` | English Curious Pearl Queen/66-inch title conflicts with multiple localized King/84-inch/Curious Charcoal titles; reported width also exceeds the English claim by more than 2%. |
| [B07B4ZFD1C](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) | bed | yes | 0:1831 | `needs_evidence` | King 84W x 92D x 56H inches is explicit, but reported width is about 1.696 m versus 2.1336 m (about 20.5% smaller). Source/model size identity unresolved. |
| [B07K6M8HKR](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | bed | yes | 6:1849 | `needs_evidence` | Twin item fields are 39W x 75L x 14H inches; reported extents are about 1.393 x 0.680 x 2.635 m. Full product/model envelope and localized size identity are unresolved; no mesh-size correction. |
| [B086TG9Q4V](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz) | bed | revisit | 3:24 | `needs_evidence` | Historical 14-inch frame/under-bed height does not establish whole headboard height; model metadata is about 0.967 m high. Reported 4096 px textures are an additional blocker. |
| [B074L4976T](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | desk | yes | 6:1065 | `eligible_for_acquisition` | Belaya curved-top desk: item fields width 160 cm, length/depth 80 cm, height 75 cm; title and same-ID reported X/Y/Z corroborate that axis assignment within 2%. Original size/texture metadata meet budgets. |
| [B075ZBVZST](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) | desk | yes | 8:905 | `needs_evidence` | Explicit 48.4W x 22.2D x 31.1H inches agrees with item fields, but reported depth is about 13.7% smaller and width about 2.2% larger. Source/model match unresolved. |
| [B07K6N5FVX](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | desk | yes | 6:489 | `excluded` | Ohrid source identity and explicit 120W x 55D x 76H cm agree with reported extents. Original model reports 4096 px textures, above 2048; no optimization authorized. |
| [B07QC8772Q](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_4.json.gz) | desk | revisit | 4:66 | `needs_evidence` | Historical English desk versus localized child-chair category conflict persists. Reported 4096 px textures add a separate resource blocker. |
| [B07QHKQLBH](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_3.json.gz) | desk | yes | 3:526 | `excluded` | Explicit 44W x 20D x 30H inches and same-ID dimensions agree; original GLB HEAD size 25,711,348 bytes exceeds 15 MiB and reported textures are 4096 px. |
| [B07R1JT4JL](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_5.json.gz) | desk | yes | 5:532 | `excluded` | Source item 39W x 19.63D x 26H inches and reported extents agree; title/use bullets identify computer/writing desk. Reported 4096 px textures exceed 2048. |
| [B07TJV6Q5W](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) | desk | yes | 7:673 | `needs_evidence` | Title lists 90 x 117 x 76 cm without W/D labels; item length/width assignment reverses native X/Z. Do not infer axes from shape alone. HEAD exceeds 15 MiB and textures are 4096 px as additional blockers. |
| [B084S6TSK7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) | desk | revisit | 8:17 | `needs_evidence` | Historical item height 60 cm versus title/explicit W/H/D bullet 80 cm persists. Model metadata about 79 cm does not settle the published conflict; textures are 4096 px. |
| [B075YZ16V7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) | wardrobe_dresser | yes | 0:1445 | `needs_evidence` | English DRESSER title and six-drawer bullets conflict with multiple localized Queen-bed titles. Published 61W x 18D x 32H inches is retained as a claim, not a resolved product/category contract. |
| [B07B3XXD3P](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_0.json.gz) | wardrobe_dresser | yes | 0:576 | `needs_evidence` | Explicit approximate H178 x W150 x D50 cm conflicts with reported height 187 cm/depth 57 cm. Original size exceeds 15 MiB and textures are 4096 px; no source/model reconciliation. |
| [B07GFFPKFV](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | wardrobe_dresser | yes | 6:912 | `excluded` | Inari enclosed two-door/two-drawer wardrobe, 100W x 57D x 180H cm; item/title/model dimensions agree within 2%. Original texture metadata is 4096 px; blocked under current unmodified-asset budget. |
| [B07H8JN9QF](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | wardrobe_dresser | yes | 6:1852 | `eligible_for_acquisition` | Morava four-door/two-drawer mirrored wardrobe: published 200W x 59D x 212H cm, model-number/variant join, reported dimensions within 2%, and original resource metadata meet acquisition gates. Reported mesh height is larger; future native inspection/reservation is mandatory. |
| [B07H8T8ZS7](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_8.json.gz) | wardrobe_dresser | yes | 8:688 | `excluded` | Localized titles identify a Vitrine/display cabinet, not a clothing wardrobe. Item fields 111 x 40 x 185 cm conflict with localized bullets 92 x 99 x 214 cm; no dimension or wardrobe qualification. |
| [B07H8V7P3H](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_2.json.gz) | wardrobe_dresser | yes | 2:460 | `excluded` | Moselle two-door wardrobe source dimensions 100W x 60D x 196H cm agree with reported extents, but original HEAD size 39,484,288 bytes and 4096 px textures exceed budgets. |
| [B07JGPKZYT](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_7.json.gz) | wardrobe_dresser | yes | 7:455 | `excluded` | Mira four-door mirrored wardrobe 181W x 58D x 207H cm; reported dimensions agree. Original HEAD size 43,865,700 bytes and 4096 px textures exceed budgets. |
| [B07JH147WS](https://amazon-berkeley-objects.s3.amazonaws.com/listings/metadata/listings_6.json.gz) | wardrobe_dresser | yes | 6:448 | `excluded` | Mira two-door wardrobe, original Italian title and item fields 98W x 58D x 193H cm agree with reported extents. Original HEAD size 30,781,556 bytes and 4096 px textures exceed budgets. |

## Source rights and alternative-source checks

The current official ABO [release](https://amazon-berkeley-objects.s3.amazonaws.com/index.html),
[CC BY 4.0 license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt),
[listing schema](https://amazon-berkeley-objects.s3.amazonaws.com/listings/README.md)
and [model conventions](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md)
were rechecked. Rights remain conditional on attribution, license/change notices,
retained notices and no implied endorsement. Product availability, manufacturer
certification, chain of title and trademark clearance were not independently proven.
The published dataset revision remains unknown; response identities are recorded.

[Poly Haven](https://polyhaven.com/license) describes CC0 assets separately from
website content and prohibits unpermitted scraping. Its [API terms](https://raw.githubusercontent.com/Poly-Haven/Public-API/master/ToS.md)
make API access subject to separate acceptance. No API endpoint, account, asset-page
harvest or acceptance action was used; no specific physical product was qualified.
The [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit) page still lists
140 3D files, CC0 and release 1.0 (2018), but does not establish manufacturer item
measurements or a product-to-model join. Its archive was not retrieved. These are
two **source-level investigations**, outside the 30 individual product reviews;
no invented candidate/product ID is assigned to a collection. FRONT/FUTURE remains
unavailable for public model delivery absent authoritative additional permission.

## Acquisition, catalog and retrieval boundary

Only the three new IDs above are defensible future individual-acquisition leads.
No new record is metadata-qualified in the packaged catalog, planning-qualified or
render-qualified. Charles remains the only current approved product mesh. Existing
Sheen Chair remains an illustrative fixture, not a manufacturer product.

A future task should inspect **Belaya first**, then **Morava**, then the nightstand,
subject to separately authorized acquisition. Belaya adds the missing desk
function with a small reported mesh; Morava adds genuine enclosed clothing storage
but needs particular envelope-height review. No bed is recommended for acquisition.

The packaged catalog currently restricts source categories to CHAIR/SHELF and
subtypes to armchair/bookcase. Admitting DESK, CABINET/wardrobe or TABLE/nightstand
requires a separate reviewed metadata-contract/category-mapping task. Source
qualification cannot bypass that contract, update the live index or modify existing
specifications. Preserve original marketing titles as provenance; future reviewed
names/categories/variants may be indexed only after catalog admission. Materials,
styles, physical colors, room suitability and clearances remain unqualified.

## Transfer budget and review limits

Exactly **9,948,621 metadata response-body bytes** were received in 52 recorded
implementation requests: five ABO documents/index files, ten 512 KiB listing
prefixes, four 1 MiB prefixes, 30 model HEAD requests and three alternative-source
documents. Maximum response body was **1,048,576 bytes**; total stayed below the
**10,485,760-byte** cap. Model HEAD bodies were zero bytes. Compressed metadata
transfer bytes are counted before bounded local decompression. HTML was read
without following image, font or script resources. Git/CI control traffic is outside
this source-metadata budget. No hidden browser/search downloads occurred.

Only complete JSONL lines were parsed; trailing incomplete lines were discarded.
The fixed small model index contains 7,953 rows. Prefix scanning identified leads;
**30** selected product/domain records received detailed qualification, not every
record decoded in the sample. The sample is not exhaustive. Resource data is
published metadata, not actual GLB validation. Review was by the implementing agent,
without an independent human judgment or new retrieval-effectiveness claim.
