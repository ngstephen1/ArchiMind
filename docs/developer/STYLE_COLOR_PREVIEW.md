# Catalog-color preview proof of concept

The selected Plotly 3D view can optionally display flat colors from an accepted
E1/E2 style plan. It adds no geometry, physical materials, textures, assets,
dataset, training or live model verification. Default views are unchanged.

## Use and API

After an accepted style result, enable **Preview catalog colors in selected 3D
view**. It starts unchecked and is reversible. The 2D view, standalone samples
and experimental Three.js viewer are unaffected. Fixture/fallback output has no
catalog plan, so it keeps the original view. Switching layouts, regenerating,
changing styling inputs or requesting another style clears the preview.

```python
from archimind.examples.style_bedroom import offline_style_bedroom
from archimind.render import render_styled_design_3d

workflow, advice = offline_style_bedroom()  # fixed mock; never a live client
figure = render_styled_design_3d(workflow.approved_design, advice)
assert advice.plan.rendered is False
assert figure.layout.meta["style_preview"]["kind"] == "catalog_flat_color"
```

The renderer checks the strict E1 result schema, catalog entries, furniture IDs,
exact source-design match and mock/API provenance. `StyleColorPreviewError`
rejects invalid/stale metadata; the UI shows the original view with a safe warning.
The styling workflow owns spatial approval. Rendering makes no generation,
validation-engine or model calls, and does not certify geometry or code compliance.
Existing AI gates still govern obtaining advice; showing colors authorizes no request.

Only trace colors and `layout.meta.style_preview` change. Vertices, triangles,
openings, IDs, dimensions, opacity, lighting, hover, legend, camera, ranges,
aspect ratios and revision remain identical. Inputs, scores and reports are
untouched. The advisor's `rendered=False` metadata contract is preserved; the
explicit rendering step is recorded separately on the new figure.

| Target | Mapping |
| --- | --- |
| Walls / floor | Corresponding catalog finish color |
| Furniture | Existing ID → finish color, on every mesh part |
| Glass, opening outlines and other traces | Existing appearance retained |
| Accents | Metadata only; no placement targets invented |

One finish colors every part of an object, including bed pillows/mattress and
wardrobe handles. There is no component-material assignment. Existing lighting
and transparency can make pixels differ from catalog hex values. Wood, linen
and metal remain appearance labels, not physical properties, textures or PBR
materials. This is not photorealistic or learned from a room dataset.

## Offline demo and verification

```bash
python -m archimind.examples.preview_style_colors
python -m archimind.examples.preview_style_colors --json
python -m archimind.examples.preview_style_colors --output output/style-color-preview.html
python -m pytest -q tests/test_style_color_preview.py
```

The permanently mocked example verifies color-only changes and preserves Layout A's
score **67.721925** and full workflow/advice data. Optional HTML embeds Plotly and
labels itself **OFFLINE MOCK**; it needs no API key or CDN. Generated output is
not committed and is not CAD/BIM or saved-project export.

Tests cover all five themes/both layouts, geometry/camera preservation, malformed
catalog values/IDs/provenance, stale plans, immutability, no backend work on view
changes, reversible UI state, fallback/reset and offline HTML/JSON.
Review this limited preview before selecting datasets, component materials,
asset expansion or another renderer integration.
