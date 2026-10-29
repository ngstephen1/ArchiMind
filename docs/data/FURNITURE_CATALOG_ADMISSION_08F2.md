# Metadata catalog admission — Task 08F2

Checkpoint 1: the strict catalog contract supports DESK/writing desk,
CABINET/wardrobe and TABLE/nightstand. Metadata admission is pending the second
checkpoint. The application still uses the original two-product release here.

Baseline: `4052e1a4bf8d8919a34da249b356d9e4dec5296f`. The owner authorized
metadata-only admission using the unchanged 08F1 evidence. This is neither human
relevance adjudication nor authority to acquire or approve a model.

## Compatibility contract

The byte-identical original catalog is packaged as
`assets/furniture_catalog_1_0_0.json`. `load_catalog(version="1.0.0")` resolves only
that fixed, hash-checked resource. Unsupported versions, paths and URLs fail.
The default loader continues to resolve the active release. Schema 1 retains its
original armchair/bookcase domain; schema 2 is reserved for catalog 1.1.0 and the
five explicitly supported functional mappings. Search-document version remains 1.
Existing record bodies and search documents do not require migration.

| Source type | Canonical category | Functional subtype | Dimension axis mapping |
| --- | --- | --- | --- |
| CHAIR | chair | armchair | width/length/height → W/D/H |
| SHELF | storage | bookcase | width/length/height → W/D/H |
| DESK | desk | writing desk | width/length/height → W/D/H |
| CABINET | wardrobe | wardrobe | length/width/height → W/D/H |
| TABLE | table | nightstand | width/length/height → W/D/H |

These are reviewed functional mappings, not a claim that arbitrary CABINET or
TABLE records are suitable wardrobes or bedside tables. Admission additionally
requires exact source/product/variant and whole-item evidence. Unsupported
subtypes, mismatched categories, package dimensions and render claims fail.

All existing Decimal conversion, immutable-record, rights, duplicate-key/identity,
finite-dimension and evidence-link checks remain. Morava's source-axis swap is
explicit; its published height is not replaced with the reported mesh height.

## Historical preservation

08A and 08F1 research files and the pending 24-prompt human-review packet remain
unchanged. The 08F1 preservation test now distinguishes its historical code
fingerprints from explicitly authorized 08F2 migrations: each changed path binds
both its previous hash and exact replacement hash in the accompanying receipt.
All other historical pins remain enforced. This does not rewrite the old receipt.

The remaining checkpoints will add the three source-grounded metadata records,
current specification compatibility and explicit historical retrieval replay.
No mesh, envelope, benchmark, judgment, embedding or asset budget is changed.

Checkpoint 1 verification: **1,803 Python tests passed in 119.61s**, including
134 focused catalog/source tests. Frontend **75 passed**; syntax/build/bundle
equality, Ruff lint/format, dependency, registry and health (HTTP 200) passed.
The full suite includes real offline packaging and isolated installation.
