# Charles product requalification — 08C-R2

Technical checkpoint, 2026-10-29 UTC (October 28 in New York). **Automated pass; visual approval pending. No approved product binding or model is published by this checkpoint.**

The paired [machine receipt](ASSET_QUALIFICATION_08CR2.json) records the current HTTPS retrieval, received-byte SHA-256, complete recomputed offline inspection and revalidated Policy B envelope. Acquisition used the official individual object only, capped at 15 MiB with system CA verification and redirects rejected; no preview, external texture, bookcase or dataset archive was acquired. Quarantine remains outside Git.

## Identity, rights and dimensions

Charles, Sod, ASIN/model B075X2X4XS, remains bound to `abo-b075x2x4xs-amazon-com`, catalog/record 1.0.0 and the existing 08A product evidence. The [official object](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/original/S/B075X2X4XS.glb) is **4,252,440 bytes**, SHA-256 **62c03e59b674cfb3163d2d35fbc50874a46f9d8ebd7c4be73a60e82eb6d1f645**. ETag is retained separately and is not treated as SHA-256.

The freshly read [ABO model README](https://amazon-berkeley-objects.s3.amazonaws.com/3dmodels/README.md) and [CC BY 4.0 license](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt) support public browser redistribution subject to attribution, license linking, retained notices and modification disclosure. Include dataset/contributor credit and no endorsement claim. This does not independently clear trademarks, individual mesh authorship or certify physical product fidelity. Historical source qualification remains in [08A](FURNITURE_SOURCE_REGISTER.md).

| W × D × H (m) | Values | Meaning |
| --- | --- | --- |
| Published | 0.9906 × 0.9906 × 0.9652 | Published item claims, unchanged; not measured by ArchiMind |
| Current native mesh | 0.996104896068573 × 1.0019413232803345 × 0.976093053817749 | Current decoded positions and static transforms |
| Planning envelope | 0.996104896068573 × 1.0019413232803345 × 0.9760930538177491 | Exact approved outward envelope, not corrected product dimensions |

Native +Y up/+Z front convention, identity orientation and scale **1.0**, normalized translation `(0, 0, 0.00010657310485839844)`. Floor/center anchoring and all eight AABB corners are revalidated by the exact-rational R1 contract with no inward epsilon. Placement for canonical furniture `(x,y)` is Three `(x+W/2, 0, -(y+D/2))` after normalization. Renderer integration must never use illustrative fitting.

## Recomputed technical gates

One mesh/primitive/material, **42,706 triangles**, three embedded **2048 × 2048** images and **67,108,860 bytes** estimated unique decoded RGBA including mipmaps. No extensions, animation, deformation or external resources. Per-asset resource gates pass. Two instances require 85,412 furniture triangles, 4,252,440 unique encoded bytes and 67,108,860 unique texture bytes, below unchanged scene budgets.

The original offline inspection still rejects containment in the published physical box. That historical gate is retained; Policy B independently proves containment in its approved planning box. The new helper compares the complete freshly recomputed receipt digest with reviewed evidence, not just caller-supplied bounds. Missing/currently corrupt files and mismatched receipts fail with sanitized errors.

## Pending gates and verification

Image pixel decoding, recognizable front/back, source materials, floor contact, browser compatibility, interaction, fallback and cleanup require the private native-scale inspection harness. No render approval follows from this technical checkpoint. No device-performance or manufacturer-metrology claim is made.

Focused tests cover current-inspection handoff, altered hashes/counters/unchecked integrity, unsupported IDs and missing files, alongside the existing inspection and exact-envelope tests. Full CI is required before the next checkpoint. Original catalog, planning JSON, canonical models, geometry, A/B and legacy renderer are unchanged.
