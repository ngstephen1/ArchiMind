# Studio House · bedroom design development

**Issue for designer review | demonstration project | saved revision 2.** Start with the doorway picture and dimensioned bedroom plan. The room has a real editable Blender model and saved layout coordinates. Its dimensions describe the conference demonstration. An existing-property commission needs its own measured survey, procurement records and professional review before anyone orders or builds.

## Read the issue

| Open | What to check |
|---|---|
| `presentation/Studio-House-Presentation.pdf` | Whole-home concept. The separate doorway, desk and salon PNGs show three CPU Cycles renders at 1920 × 1080. |
| `drawings/r2/bedroom-plan.svg`, elevations and section | Review furniture reservations and openings. Each sheet can be edited in a vector editor. Use labeled dimensions. |
| `drawings/bedroom-concept-shell.dxf` | Import in metres. The associated JSON gives the source and field checks. This shell is derived from Town's geometry. |
| `native/home.blend` | Open the editable proof scene. The final eye-view run used the camera and lighting settings recorded in the presentation receipt. |
| `revisions/` | Compare saved revisions and the fixed doorway view. Use project, revision, home ID and object IDs to match comments back to the original. |
| `procurement/` | Review four furniture reservations, three finish takeoff rows, operating checks and cost reconciliation. Each row carries the saved revision. |
| `sources/` | Retain the Amazon Berkeley Objects attribution and license with the Belaya desk. Surface receipts describe the render materials. They supply no manufacturer finish approval. |

## Design change to review

The chair `desk-chair` moved 0.300 m north. The desk `belaya` stayed fixed. On the plans the chair-to-desk footprint gap increases from 0.060 m to 0.360 m. A chair back can clear the desk footprint and still interfere with its apron. Measure the chair passage width, arm height, desk clear width, underside height and insertion depth. Check pullback with a seated occupant and verify the actual door swing.

## Procurement and field work

All four furniture lines and all three finish lines await pricing. The known subtotal is zero because no supplier quotation has been entered. The project budget is unknown. Confirm exact supplier, model, dimensions, finish sample, quote date, delivery route and availability. Obtain separate allowances or quotations for installation, freight, labor and tax. The floor and ceiling quantities describe gross area, and the gross wall area includes openings. Measure net finishes, coats, waste and pack sizes before ordering.

For an actual home, survey the finished faces, ceiling, diagonals, fixed services, sill and head heights, hinge locations and nearby obstructions. Record the site, date, source, units and measurement uncertainty. Coordinate any electrical, structural and accessibility questions with the responsible professionals. Issue a new project revision after those checks, and regenerate all outputs. The PDF, PNG, SVG, DXF and model here belong to the conference example.

## File integrity and rebuild

Unzip into one directory and run `shasum -a 256 -c SHA256SUMS.txt` there. For a repository rebuild, place the unmodified conference proof release under `output/designer-inputs/scene` and the HD eye-view release under `output/designer-inputs/photos`. Run `.venv/bin/python scripts/package_designer_demo.py` from the repository. The script checks both saved board hashes, the native model against its render receipts, the three image hashes, source notices and the presentation PDF before replacing the ZIP.
