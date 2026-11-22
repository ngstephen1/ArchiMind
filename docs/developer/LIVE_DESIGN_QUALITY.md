# Live design review and Blender rendering

In Town, choose **Design a home** and set a 15 × 16 m lot. Submit a brief for two residents and four dinner guests, a formal salon, a study far from the living room, and an explanation of the plan. The brief retains the six requested places. Decide whether separate four-seat tables in the salon and kitchen-dining room work for the household. Select the split-dining control before resubmitting if they do.

Compare the validated layouts using doorway-to-doorway routes through the center hall, modeled openings, seating counts and furniture reservations. Room-center preferences remain plan measurements. The route numbers cover the section between the marked points inside the doorways. To check screen glare, sound transmission, hardware clearances and other site conditions, record those measurements separately.

Apply a layout to ask about its actual evidence. A question starting with **Why** can use the saved-design panel directly. For a brief that also asks for an explanation, Town opens the answer after you apply your chosen layout. The main view stays available while an optional Blender render runs.

## Render an applied revision

Install Blender, Chrome or Chromium, and the Town frontend dependencies described in the README. Run this from the checkout:

```sh
TOWN_BLENDER_BIN="/Applications/Blender.app/Contents/MacOS/Blender" \
  .venv/bin/python scripts/run_town.py
```

On Linux, set `TOWN_BLENDER_BIN` to the installed `blender` executable. Open **Design presentation → Render this revision**. Inspect the proof, then choose **Approve proof and render HD**. Completed shots, editable Blender scene, receipts and the client PDF can be downloaded from that same revision. Turn off model calls using `ARCHIMIND_ENABLE_OPENAI_STUDIO=0` when replaying a saved home.

The local queue renders one task at a time. It reports actual pipeline phases and stores completed jobs next to the Town database under `town-renders/`. Repeated requests for the same snapshot and renderer settings reuse verified files. Failed jobs can be retried. Keep the launcher running until the render finishes.

For a CPU/GPU comparison, use the identical saved snapshot, manifest, style export and camera. Run the whole-home renderer with `--quick-proof` on CPU and with `--quick-proof --gpu` on a Blender host with OptiX. Compare wall-clock time, device names and the same rendered crop at the same resolution and samples. Record GPU memory on the host and calculate cost per accepted image from the actual runner charges.
