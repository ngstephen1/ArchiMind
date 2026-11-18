# Style packs

A style pack dresses a room or a Town home in one of five interior styles. Each
pack gives the room its surfaces, lighting, a 2D plan theme, furniture models and
decor. Styles change finishes only: room geometry, openings and furniture
reservations stay as the layout generator placed them, and every view renders
offline with no model call and no third-party fetch.

| Style ID | Name | Default |
| --- | --- | --- |
| `modern_classic` | Modern classic | |
| `industrial_loft` | Industrial loft | |
| `scandinavian` | Scandinavian | yes |
| `japandi` | Japandi | |
| `mid_century` | Mid-century | |

Captures of every pack are in [`docs/images/style-packs/`](../images/style-packs/):
plan and walkthrough at 1440 × 1000 and 390 × 844, Studio rooms per pack and
tier, and the legacy comparison.

## Choosing a style

- **Town.** Pick a style in **Design a home → Style**, or name it in the brief:
  `bright study in industrial loft`, `make it japandi`, `quiet bedroom and
  modern classic style`. An offline brief must consist only of supported clauses,
  so `A home in an industrial loft style` is answered with a clarification and
  the saved home is unchanged. A style-only edit keeps the geometry.
- **Studio.** Choose **Style** before **Build 3D room**. The style carries into
  the 3D scene, the 2D plan colours and saved builds.
- **Legacy palettes.** Briefs and saved homes that name a palette map to a
  style: `oak` → Scandinavian, `sage` → Japandi, `terracotta` → mid-century.
  Homes saved before style packs keep their original rendering and request no
  pack files.

## In the viewers

- **Quality** toggles the high and low tiers. Low uses 1k textures and draws the
  first half of the decor in priority order (rug, curtain, pendant, art,
  accents, plant, floor lamp, mouldings).
- **Plan ↔ Room** sweeps from a line drawing to the full render with a vertical
  clipping plane. It is a view change only.
- **Fallbacks.** A missing or corrupt texture, environment or model falls back to
  the pack's plain colour or the procedural object. The status line names the
  fallback materials and furniture, and the room keeps its layout.

## Furniture binding

Each pack lists furniture choices per category with measured width, depth and
height. A reservation uses the first choice that fits inside it **and** fills at
least half its footprint and height, so a small piece never stands in for a large
one. Kitchen counters, vanities and baths are always procedural. Models are
floor-centred on their reservation and never scaled. Pieces with no fitting CC0
model (beds, desks, dining and coffee tables, and some sofas) stay procedural
until the Blender signature pieces are released.

## Releasing assets

Assets are CC0 (Poly Haven, ambientCG) or original Blender pieces. Every asset has
a release record in `src/archimind/_viewer_assets/packs/releases.json`, a line in
`packs/THIRD_PARTY_NOTICES.txt`, and content-addressed files in
`packs/assets/<sha256>.<ext>`.

```sh
.venv/bin/python -I scripts/fetch_cc0_asset.py --source polyhaven --id oak_wood_planks --kind material
.venv/bin/python -I scripts/fetch_cc0_asset.py --source ambientcg --id Metal009 --kind material
.venv/bin/python -I scripts/fetch_cc0_asset.py --source polyhaven --id sofa_02 --kind model
```

The script downloads only from the provider hosts, checks published checksums,
re-encodes maps as WebP (1k, plus a 2k diffuse for the high tier), inspects GLBs
and writes the release and notice line. Re-running it replaces the asset's
record and notice. Caps: 15 MB per file, 25 MB per pack, 120 MB in total.
Measure a model's size from its GLB bounds (x = width, z = depth, y = height)
before adding it to a pack's `furniture` list.

## Operator setup for designer pieces

Blender-authored pieces need Blender 5.1 with the Blender MCP add-on registered
for Codex, then `scripts/release_designer_piece.py`. This is installed outside
the repository and needs the owner's go-ahead; until then, packs use CC0 models
and procedural furniture.

## Verification

```sh
.venv/bin/python -m pytest -q tests/test_style_packs.py tests/test_style_pack_release.py \
  tests/test_style_pack_binding.py tests/test_style_pack_decor.py tests/test_style_pack_receipt.py
npm test --prefix frontend/realistic_viewer
```

Changes to pinned files are authorized migrations recorded in
[`docs/data/STYLE_PACKS_11A.json`](../data/STYLE_PACKS_11A.json); run
`scripts/record_style_pack_migrations.py` after staging them.
