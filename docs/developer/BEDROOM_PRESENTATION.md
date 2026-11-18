# Present a saved bedroom

Open **Client presentation** in Town to see the applied revision, dimensioned floor plan, three camera views, material board and furniture schedule. **Print presentation** opens the browser's print dialog, where you can save a PDF. The photos use Doorway, Desk and chair, and Bedside. An obstruction message identifies a detail that uses the doorway framing. The printout includes the project revision and shortened home content ID.

**Download bedroom manifest** saves the operator input for the current revision. The Blender download appears for a published revision only when the project ID, revision number, full home content ID and SHA-256 of the canonical manifest all match. A newly edited home can immediately show its own browser photos and generate its own manifest. Offline renders can be published separately after inspection.

## Seed-42 showcase

[Download the Blender bedroom and three 1920 × 1080 Cycles stills](https://github.com/ngstephen1/ArchiMind/releases/download/bedroom-showcase-r5/bedroom-r5-cycles.zip) or [open the release with the film and PDF](https://github.com/ngstephen1/ArchiMind/releases/tag/bedroom-showcase-r5).

The example follows saved project `26bda387-7853-4fa9-99b7-13d6c1064de7` through two versions of the oak writing chair. Revision 5 combines the deep back, linen platform bed, bedside table with reading lamp and qualified Belaya desk. The [manifest](../../design/bedroom-showcase/manifest.json) records actual metre-space positions, opening offsets, native release hashes, surface-map provenance and three camera poses. Camera locations are bedroom-local with east, north and up axes. Both earlier applied chair manifests are retained in the adjacent history directory.

## Render another applied revision

The checked-in operator runs on Blender 5.1.2. Download a manifest from the presentation. If you already have an authorized Town API response containing `project`, `revision` and `home`, create identical bytes with Node 20+ and the viewer dependencies installed:

```sh
node frontend/realistic_viewer/town/export-bedroom.mjs revision.json manifest.json
```

From the checkout, point Blender at a new output directory. The last path may be empty or absent. It optionally holds high-resolution originals named by their source SHA-256 from the surface inventory. Each original or packaged derivative is checked before use. The render receipt records the actual surface digests and every output file digest.

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python scripts/render_saved_bedroom.py -- manifest.json output/bedroom-renders output/surface-originals
```

The operator imports release-verified assets at native scale, checks their occupied bounds, models openings at their recorded positions, places area daylight behind each window and reconstructs the saved camera poses. It packs the editable scene, reopens it and renders the three PNGs. A record with a procedural furnishing uses its labeled reservation volume in the offline scene. A requested native asset with missing or invalid bytes fails the render. Keep the receipt, manifest, material credits and Belaya attribution with the public download. The browser uses Three.js while the finished stills use Cycles indirect lighting and denoising.

The [operator workflow](../../.github/workflows/bedroom-presentation.yml) renders on a Linux CPU runner using a checksum-pinned Blender binary. To publish another revision, inspect its images and scene, publish its downloadable archive, and add the exact four identifiers and HTTPS archive URL to the Town publication index. [Publications](../../frontend/realistic_viewer/town/bedroom_publications.json)
