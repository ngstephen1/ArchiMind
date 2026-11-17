# P7: preview every reference (receipt)

- `ui/dataset_references.py` (not hash-pinned) gains `reference_figure(preview)`, a Plotly figure of its own. It draws the room outline, plus one filled rectangle per footprint labelled with its category and turn (for example "bed · turned 90°"). It draws no doors or windows and is titled "Reference footprints (not validated)".
- Quarter-turn hits now show this chart above the footprint table. Canonical hits still use `render_floorplan`, which keeps rejecting rotated app furniture. No pinned file changed.
- Tests: `tests/test_dataset_references_ui.py` adds trace-count and bounds assertions without snapshots, and the AppTest now expects a chart for the quarter-turn hit. All 6 pass, with P4's tests unchanged otherwise.
- Real pack (snapshot `8cfb3125…`, local): a preview built for **every one of the 4,170 references** through `prepare_reference_preview`. 4,117 are drawn with `reference_figure` and 53 with `render_floorplan`, with **0 failures** in 27 s. The script output is in `E:/archimind-data/p5/p7_all_previews.json`.
