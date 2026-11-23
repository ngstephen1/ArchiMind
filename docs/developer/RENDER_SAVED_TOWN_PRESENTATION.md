# Render a saved conference revision

Export the whole-home manifest from Town and record its SHA-256. The Studio home proof workflow can read an export from `docs/data/` at an exact public commit in this repository. Replace `MANIFEST_COMMIT` below with that full commit SHA and `MANIFEST_PATH` with the export path.

```sh
gh workflow run studio-home.yml -f fresh_home=true \
  -f "manifest_source=$MANIFEST_COMMIT:$MANIFEST_PATH"
```

Open the resulting `studio-home-proof` artifact. Compare the receipt’s manifest digest, revision and home ID to the Town export, then inspect the doorway and desk views. Known procedural bedroom templates retain their recognizable shapes and materials. The receipt identifies procedural templates, unrecognized reservation boxes, and native mesh hashes separately.

After accepting the CPU proof, render two 1920 × 1080 images from its packed Blender file. For a comparison between revisions, give both runs the **same** camera-source commit and path, referencing either revision of the same project and bedroom shell. Use a source with distinct doorway and desk views. A desk camera that fell back to the doorway needs another saved camera source with the same shell. Leave out `camera_source` to use the current revision’s cameras.

```sh
gh workflow run studio-home.yml -f fresh_home=true \
  -f "manifest_source=$MANIFEST_COMMIT:$MANIFEST_PATH" \
  -f "approved_proof_run=$ACCEPTED_RUN_ID" \
  -f "camera_source=$CAMERA_COMMIT:$CAMERA_MANIFEST_PATH"
```

The `studio-eye-views` artifact includes the two PNGs and each camera’s eye, target, field of view, manifest hash, proof-scene hash and image hash. The eye-level pass applies the same neutral daylight color and AgX medium-high contrast to each revision. The saved-style edition models transmitted daylight on the inside of each window curtain, and meters exposure from the ratio of room glazing to floor area. The receipt records the window IDs, powers and exposure in EV for each image. The two bedroom camera poses are frozen. The optional salon photograph keeps its saved eye and azimuth and uses lens shift for straight verticals. The renderer also verifies that all in-use external images are packed inside the editable scene. Inspect the daylight and oak grain at native resolution.

### Use the saved Town style in the book

Supply `snapshot_source` alongside `manifest_source` to render the saved pack furniture and dressing. The snapshot is a JSON object with `project`, `revision` and the applied `home`. The file can live at a different pinned commit from the manifest. Its home content hash must match its Town ID, and running the production manifest exporter over it must reproduce the supplied manifest bytes exactly.

The export resolves high-tier assets with Town’s pack loader. It uses Town’s actual furniture and dressing functions to capture native model transforms and procedural geometry for all rooms. The Blender receipt lists resolved slots and file digests per room. Floors, tile, walls, ceilings and trim use released pack textures. Cycles renders with window-aligned lights and the pack environment. The offline renderer has its own light transport, board cameras and tone mapping.

The packed proof scene retains the room lights and materials. For a standard daytime view, select its named camera and apply the matching exposure from the proof receipt. The coverlet, clay and evening studies also change object visibility, materials or light settings. Rerun the proof workflow to reproduce those study images. For photography, the renderer reopens the approved scene and uses its hash-verified style receipt to select the daylight treatment. The eye-view receipt records the exposure and window emitters used for each shot. Supplying the original snapshot again also checks its SHA-256.

For the final R2 presentation, pass `-f salon_cover=true` with the accepted proof run ID. The resulting `studio-eye-views` artifact includes the finished ten-page PDF when the source contains six rooms, its bedroom eye-level PNGs, the optional salon PNG, the render receipt and credit files. The plan identifies the saved pack and illustrates its authenticated surface textures. The edition with matched bedroom cameras is labeled on the bedroom sheet.

## Send a checked two-revision designer handoff

Save the two scene proof folders, the edited revision's three 1080p eye views
and the corresponding client book. Keep the visual inspection receipt with the
book. Record each inspected page in order and include both manifest hashes,
the edited proof receipt hash and the exact doorway, desk and salon image
hashes. The standard `scripts/print_revision_book.py --eye-views` receipt
records those hashes when the edited render includes the salon view. Add the
visual inspection rows after reviewing the rendered book at print scale.

With Python dependencies installed and Poppler's `pdfinfo` on `PATH`, run from
the checkout used to verify the release:

```sh
.venv/bin/python scripts/package_town_release.py \
  output/release/r1/proof output/release/r2/proof output/release/r2/hd \
  output/release/Client-Book.pdf output/release/book-inspection.json \
  output/release/Designer-Handoff.zip --commit "$(git rev-parse HEAD)"
```

The ZIP binds the two saved manifests to the book, photographs and editable
Blender file. It also includes dimensioned bedroom drawings, a concept DXF in
metres, the furniture schedule, source notices and file checksums. Compare the
declared release commit to the accepted CI run before publishing. The output
path must be fresh. Unpack the ZIP and run `shasum -a 256 -c SHA256SUMS.txt` in
its root. For an existing home, confirm the actual site dimensions and
supplier clearances before using the concept for procurement or construction.

### Bedroom lighting proofs

Dispatch the Studio Home workflow with `fresh_home=true` and `lighting_proof=true` and the accepted proof run, manifest and snapshot for each revision. Supply the **same pinned** `camera_source=<sha>:<manifest-path>` for both dispatches. The bedroom doorway and desk views use this common camera, and the task view repeats the desk pose. Add `salon_cover=true` to include optional salon and living detail images. They document the selected revision and use that revision's own cameras. The receipt identifies the camera source for every shot. For example, on a branch with the lighting-proof workflow:

```bash
rev=2
pin=85cd2c548a96a0f62127891bb0adc6d92f75fbf2
gh workflow run studio-home.yml --ref "$(git branch --show-current)" \
  -f fresh_home=true -f lighting_proof=true -f salon_cover=true \
  -f approved_proof_run=45130362035 \
  -f manifest_source="$pin:docs/data/nov24-fresh-live/manifest-r$rev.json" \
  -f snapshot_source="$pin:docs/data/nov24-fresh-live/snapshot-r$rev.json" \
  -f camera_source="$pin:docs/data/nov24-fresh-live/manifest-r2.json"
```

For the matching before view, set `rev=1`, use approved run `45130361857`, and keep the camera source unchanged.

The 960 × 540 outputs are published as `studio-lighting-proof`. Use `studio-eye-views` for the 1920 × 1080 revision-book input. The evening proof disables existing light objects and material emission before adding the modeled task and fill sources. The result shows a lighting concept. Fixture specification and work-surface illuminance require separate evidence.
