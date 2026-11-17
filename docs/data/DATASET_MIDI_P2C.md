# P2c: MIDI-3D adapter audit (5 bedrooms)

Machine-readable receipt: [DATASET_MIDI_P2C.json](DATASET_MIDI_P2C.json).
Status: **IMPLEMENTED, local audit only.** No training, no schema change, no UI change, nothing published.
This stops before M3.

## What was done

- **Bounded access.** The five rooms were pulled from `huanngzh/3D-Front` at revision `156fc531…`
  using exact member names and a hard cap on bytes streamed. No archive was downloaded in full.

  | Archive | Full size | Streamed | Cap | Kept |
  |---|---|---|---|---|
  | 3D-FRONT-TEST-SCENE.tar.gz | 13.27 GB | 382.3 MB | 512 MiB | 40 files, 56.9 MB |
  | 3D-FRONT-TEST-RENDER.tar.gz | 3.52 GB | 108.5 MB | 160 MiB | 280 files, 22.2 MB |

  No requested member was missing. The data lives outside git, in `E:/archimind-data/p2c/`.
- **New code.**
  - `glb.py`: a bounded GLB reader that returns node hierarchy, world bounds, triangles and texture sizes.
  - `remote.py: gzip_tar_select`: an exact-member streaming extractor with a byte cap.
  - `midi_adapter.py`: file classification, the object association, the view inventory, the SSR↔MIDI
    similarity fit and the camera hypothesis test.
  - CLI command `midi-audit`.

## Rooms

All five are MIDI **test** split and SSR **train** split. The SSR side comes from pack
`ssr-bedrooms-p2b` (snapshot `8cfb3125…`).

| Room | SSR tier | Objects | Fit scale | Max centre error | Camera (documented / best alternative IoU) |
|---|---|---|---|---|---|
| fe6717d3…/MasterBedroom-2820 | reference_only | 6 | 0.5263 | 0.43 cm | 0.925 / 0.380 |
| fd987ee8…/MasterBedroom-11997 | reference_only | 5 | 0.4456 | 0.55 cm | 0.949 / 0.195 |
| fd987ee8…/Bedroom-18956 | reference_only | 3 | 0.7313 | 0.43 cm | 0.654 / 0.255 |
| e8924da7…/Bedroom-338 | reference_only | 4 | 0.5583 | 0.54 cm | 0.591 / 0.410 |
| fd9984b0…/Bedroom-9575 | canonical | 2 | 0.6979 | 0.27 cm | 0.964 / 0.694 |

Summary: alignment PASS 5/5, camera PASS 5/5, association clean 5/5. There were no missing,
orphan or duplicate objects.

## Proven conventions

1. **Archive layout.** `<house>/<room>.glb` holds the furniture only. `<house>/<room>_full.glb` adds
   structure. Objects are in `<house>/<room>/<Category>_<jid>_<n>.glb`. Structure parts
   (`ceil`, `floor`, `wall`, `others`) vary by room.
2. **Placement.** Object GLBs are already placed in room space.
3. **Normalization.** `MIDI = s · (SSR − t)` with no axis flip. The furniture union box is centred on the
   origin and its longest side is 1.9. The rule predicts `s` from the SSR row in 4 of 5 rooms. In
   MasterBedroom-11997, MIDI contains an object the SSR row lacks (a 2.7 m
   `Cabinet_Shelf_Desk_311ff139…_4`), so the union box differs. The fitted `s` is still exact for every shared object.
4. **Extents.** Extents are compared only for objects at a quarter turn. In 11997, two `27afe8b6`
   nightstands sit at 116° yaw. Their centres agree to within 0.4 cm, but a mesh box at that yaw cannot be compared with
   the rotated SSR box, so the report sets their extent error to `null` rather than failing it.
5. **Cameras.**
   - Image `k` belongs to `meta.json` `locations[k]`. The frame names inside `meta.json` are stale:
     only 21 of 44 name a file that exists. They are ignored.
   - A glTF point `(x, y, z)` maps to camera-world `(x, −z, y)`. The camera looks along −Z with +Y up, and
     focal = `(W/2) / tan(camera_angle_x / 2)`.
   - This is evidenced, not assumed: in every room the documented convention had the best median IoU
     between projected object boxes and semantic-label boxes, ahead of the y-up world and the frame-name ordering.
     Two local overlays were inspected by eye: `audit/overlays/camera_Bedroom-9575.png` and `camera_Bedroom-338.png`.

## Not verified / not acquired

- **Depth.** `depth_k.exr` is present for all 55 views, but no EXR reader is installed, so the depth units are unverified.
- **Surfaces / NPY.** `3D-FRONT-TEST-SURFACE` is 70 GB in 3 gzip parts. It was not acquired because it is not needed for alignment.
- **SSR/FUTURE joins.** Rooms are linked by room key and objects by jid plus position under the fit. Nothing is
  inferred from names or images.

## Decision: no MIDI SceneReference export

MIDI geometry duplicates the SSR room it aligns to, and object facing cannot be recovered from
axis-aligned bounding boxes. The SSR SceneReference therefore stays the reference record, and MIDI is linked
through the room key plus this audit. The P2b pack still has **no MIDI SourceManifest**.

## Permissions (unchanged, provisional)

- MIDI 3D-Front is `cc-by-nc-4.0`.
- 3D-FUTURE (Kaggle mirror) is "Unknown".
- SSR is provisional.

Only `local_research` is allowed. The owner must decide before any public pack.

## Reproduce

```
python -m archimind.datasets midi-audit \
  --scene-root E:/archimind-data/p2c/raw/scene/3D-FRONT-TEST-SCENE \
  --render-root E:/archimind-data/p2c/raw/render/3D-FRONT-TEST-RENDER \
  --midi-dir <P1 midi id lists> --ssr-pack E:/archimind-data/p2b/pack \
  --out <new empty dir>
```

The audit needs Pillow and numpy for semantic masks. They are imported lazily and are not declared dependencies.
