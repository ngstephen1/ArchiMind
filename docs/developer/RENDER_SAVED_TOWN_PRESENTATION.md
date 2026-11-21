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

The `studio-eye-views` artifact includes the two PNGs and each camera’s eye, target, field of view, manifest hash, proof-scene hash and image hash. The eye-level pass applies the same neutral daylight color and AgX medium-high contrast to each revision. Emitter positions and intensities are inherited from the proof. Inspect the daylight and oak grain at native resolution.

### Use the saved Town style in the book

Supply `snapshot_source` alongside `manifest_source` to render the saved pack furniture and dressing. The snapshot is a JSON object with `project`, `revision` and the applied `home`. The file can live at a different pinned commit from the manifest. Its home content hash must match its Town ID, and running the production manifest exporter over it must reproduce the supplied manifest bytes exactly.

The export resolves high-tier assets with Town’s pack loader. It uses Town’s actual furniture and dressing functions to capture native model transforms and procedural geometry for all rooms. The Blender receipt lists resolved slots and file digests per room. Floors, tile, walls, ceilings and trim use released pack textures. Cycles renders with window-aligned lights and the pack environment. The offline renderer has its own light transport, board cameras and tone mapping.

For the final R2 presentation, pass `-f salon_cover=true` with the accepted proof run ID. The resulting `studio-eye-views` artifact includes the finished ten-page PDF when the source contains six rooms, its bedroom eye-level PNGs, the optional salon PNG, the render receipt and credit files. The plan identifies the saved pack and illustrates its authenticated surface textures. The edition with matched bedroom cameras is labeled on the bedroom sheet.
