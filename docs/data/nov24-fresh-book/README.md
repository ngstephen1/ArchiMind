# Fresh Town home render and client book evidence

The live Town session and the two saved manifests are in the
[fresh replay record](../nov24-fresh-live). Both bedroom views use the same
camera, lens and exposure across revisions. The chair moves 0.300 m in the
saved model. Its nearest plan gap to the desk increases from 0.060 m to
0.360 m. The desk stays fixed.

| Revision | CPU whole-home proof | CPU 1080p render |
| --- | --- | --- |
| 1 | [7 min 50 s](https://github.com/ngstephen1/ArchiMind/actions/runs/45130361857) | [Two bedroom views, 18 min 48 s](https://github.com/ngstephen1/ArchiMind/actions/runs/45131718875) |
| 2 | [7 min 29 s](https://github.com/ngstephen1/ArchiMind/actions/runs/45130362035) | [Two bedroom views and a salon view, 20 min 39 s](https://github.com/ngstephen1/ArchiMind/actions/runs/45131718940) |

Times are GitHub step durations, which include scene loading, rendering and
verification. Blender 5.1.2 used Cycles on CPU with up to 96 samples per HD
shot. Both editable scenes reopened with 40 packed image dependencies.
The [paired receipt](verified-eye-pair.json) pins the render commit, original
1920 × 1080 PNGs, cameras, manifests, Blender scene hashes and source notices.

- [Bedroom approach, both revisions](bedroom-doorway-paired.jpg)
- [Writing desk, both revisions](bedroom-desk-paired.jpg)
- [Salon, revision 2](r2-salon-doorway.jpg)

Window mullions and folds read in the bright areas. The sage and rust textiles
separate the bed from the plaster and oak. The view from the bedroom door
still has a sparse foreground. These are design-development images for a
synthetic site. Opening dimensions, under-desk fit, supplier specifications
and the actual site's daylight need field evidence.

The [client book print](https://github.com/ngstephen1/ArchiMind/actions/runs/45134410119)
uses the same revision 2 inputs and includes a paired-revision comparison.
The independent cross-check and release decision are tracked in
[#67](https://github.com/ngstephen1/ArchiMind/issues/67) and
[#71](https://github.com/ngstephen1/ArchiMind/issues/71).

All 12 A3 landscape sheets were inspected at 150 DPI, including the design
scope note, citations, schedules, matching render views and continuous
folios. The wider portfolio includes lower-resolution proofs. The living
room repeats its proof view, and the bathroom, study and kitchen-dining
remain schematic. [Page-by-page inspection and PDF digest](book-inspection.json)

The [earlier staged designer transfer](https://github.com/ngstephen1/ArchiMind/actions/runs/45134685184)
passed an independent clean-download check of 31 digest-listed files,
including six readable SVGs, a concept DXF, three schedules and the packed
Blender scene. [Candidate verification](designer-candidate-verification.json)

The rehearsal candidate at `512ed26` preserves the same inspected PDF and
includes the original print receipt. Its clean-download check verified all 32
checksum-listed files. The designer ZIP SHA-256 is
`13e200835b80ae65c8fe9247623e1f76d6ec489aee2cf1ce8e72b8c20e63265a`.
[Rehearsal archive](https://github.com/ngstephen1/ArchiMind/actions/runs/45207279553/artifacts/14834053043) ·
[Rebuilt candidate verification](https://github.com/ngstephen1/ArchiMind/issues/69#issuecomment-7105933953)

GitHub Actions retains these artifact downloads for a limited period. This
record preserves the digests, inspection and preview images. The approved
PDF and editable transfer belong in the versioned GitHub Release after
the [publication gate](https://github.com/ngstephen1/ArchiMind/issues/72) passes.
