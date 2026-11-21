# Print two saved revisions for client review

Download each revision's Blender proof artifact into its own directory. The client-book command uses the proof manifests, room schedule, renders and receipt from each directory. Chrome or Chromium and Poppler (`pdfunite` and `pdftotext`) are required.

```sh
python scripts/print_revision_book.py proof-r1 proof-r2 output/Fresh-Home-Client-Book.pdf
```

The book includes the edited home's floor plan, finishes, room views and furniture schedule, followed by a two-page bedroom comparison. The footer identifies each revision. The neighboring JSON records project identity, actual image hashes, physical distances and the final book digest. CPU-proof views with different cameras are explicitly labeled. For each HD image set, first run the Studio Home photography workflow with the accepted proof run as `approved_proof_run` and the original project’s revision-1 board as `camera_source`. Download its `studio-eye-views` artifact, which includes `eye-view-receipt.json`. Then append `--eye-views hd-r1 hd-r2` using images rendered from the revision-1 comparison cameras. To print the comparison independently, run `python scripts/publish_revision_study.py proof-r1 proof-r2 comparison.html`.
