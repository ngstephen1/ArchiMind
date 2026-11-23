# Qualified bedroom and salon finish comparison

This comparison uses the archived Studio House revision 2 from the frozen
visual baseline. The preceding [woven trial](https://github.com/ngstephen1/ArchiMind/actions/runs/45124335766)
still let the mattress show through some duvet folds. The final pass raised
those shallow folds within the original envelope. A woven band distinguishes
the folded throw, and the salon uses a deeper cloth tone with a visible
cushion welt. The curtains and jambs read around the opening at the same
camera and exposure. The test also retains the bound rug edge, practical
lighting and salon foliage treatment.

[Build ebd1c37 and 1080p artifact](https://github.com/ngstephen1/ArchiMind/actions/runs/45128050577) ·
[Matched receipt and digests](verified-render.json) ·
[Frozen rubric and original camera sources](../README.md#revision-2-visual-baseline)

The left panels are from the [previous finish render](https://github.com/ngstephen1/ArchiMind/actions/runs/45119308941),
which already applied the earlier trim, curtain and lighting treatment to
the frozen packed scene. Its 1080p PNGs differ from the original frozen
crops. This comparison uses the original camera, exposure and crop bounds.
Both detail panels fit within 850 × 700 pixels without upscaling. The
receipt records the original proof digest, the previous finish's editable
scene digest and all three previous render hashes separately. The numerical
RGB differences use those previous-finish PNGs and the new layered PNGs.
The nested render receipt still points to the original frozen PNGs for
source integrity.

| Camera | Whole frame | Matched detail crop | CPU render time |
| --- | --- | --- | --- |
| Bedroom doorway | [Pair](bedroom-doorway-full.jpg) | [Bed and window](bedroom-doorway-detail.jpg) | 461.459 s |
| Bedroom desk | [Pair](bedroom-desk-full.jpg) | [Desk, chair and timber](bedroom-desk-detail.jpg) | 455.364 s |
| Salon overview | [Pair](salon-overview-full.jpg) | [Seating and window](salon-overview-detail.jpg) | 463.871 s |

## Visual checks

| Frozen criterion | Doorway | Desk | Salon | Observation |
| --- | --- | --- | --- | --- |
| Believable bedding and materials | 2 | 2 | 2 | The sage duvet has a continuous edge with room for the turned-down sheet and visible pillow. The throw and timber remain distinct from plaster. The deeper sofa fabric and cushion seam are legible in the salon. |
| Window highlight detail | 2 | — | 2 | Mullions, a lit jamb and curtain folds remain visible around the two windows. The desk angle does not frame an opening. |
| Grounded furniture | 2 | 2 | 2 | Desk panels and visible chair and salon feet meet the floor. |
| Coherent furnishing | 1 | 2 | 2 | The wide bedroom foreground still feels sparse. The writing station and salon groups read together at their intended scales. |
| Visible circulation | 2 | 2 | 2 | The desk approach and the path between salon groups remain visible. The evaluated floor-standing meshes and their placements match the frozen scene. |

The archived editable Blender file reopened with all three saved camera
poses and exposures. The rendered images are 1920 × 1080, up to 96
Cycles CPU samples on Blender 5.1.2. The proof compares mesh connectivity,
transforms and world bounds. It found **645 unchanged evaluated meshes**.
Only the duvet, folded throw and two pillows changed mesh shape, within
their original bounds. There are no new floor-standing pieces.

The finish additions use procedural Blender materials, bounded geometry
and lighting. They add zero external assets. The artifact keeps the exact
Belaya attribution and CC BY license, surface source manifest and saved
style receipt, with their hashes in the verification record.

These are model-derived concept visuals. Actual glare, installed fittings
and on-site clearances require site evidence. The separate fresh candidate
has its own manifest, editable scene and [presentation review](https://github.com/ngstephen1/ArchiMind/issues/69).
