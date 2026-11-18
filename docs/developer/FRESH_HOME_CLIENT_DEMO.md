# Nguyen’s runbook · One fresh Town home from prompt to client book

**Owner:** Nguyen Phan Nguyen. **Reviewed baseline:** `c03ecc2`. **Run status:** pending. A successful run delivers one client PDF, the source manifest and render receipt, and a short acceptance record linking the chair edit to the walkthrough, plan, and rendered bedroom. [Hieu’s parallel evidence task](HIEU_DESIGN_EVIDENCE_HANDOFF.md)

## 1. Start with an empty project

From the checkout root with the [Town prerequisites](../../README.md#quick-start) installed, use a fresh run directory and local database. Keep this terminal open. If the normal ports are occupied, use a free pair, for example `TOWN_PORT=8828 TOWN_EDITOR_PORT=8829` on the launch command. Use the same run directory when restarting.

```sh
mkdir -p output
RUN="$(mktemp -d "$PWD/output/fresh-home.XXXXXX")"
printf '%s\n' "$RUN"
git rev-parse HEAD > "$RUN/commit.txt"
TOWN_DB="$RUN/town.sqlite3" .venv/bin/python scripts/run_town.py
```

Open Town at the launched port (default 8790), choose **Design a home**, and confirm the starting project has no applied home. Record project ID, lot **15 × 16 m**, and seed **42**. The live launcher loads its configured credentials server-side. Use the live design action and retain its reported provider outcome. The seeded Studio House launcher is for rehearsing the interface.

## 2. Submit one brief and inspect the alternatives

> Design a home for two people who work from home and host four guests for dinner. Include a formal salon as well as the living room. Give the study a quiet location, and explain which placement decisions you can support from the floor plan.

Record the job ID and each agent card’s engine, result, overlap or ordering, and any skip or failure. A interprets the brief, B retrieves evidence, C inspects the lot and proposes layouts, D checks geometry and can critique candidate floor plans, and E handles material and presentation advice. An optional Codex step can skip. Record the actual events. [Town worker guide](TOWN.md)

Review A/B if both exist. Check for a formal salon **and** living room, kitchen–dining room, bedroom, study, and bathroom. Count dining places for the hosts and guests. Assess the study’s separation from social spaces using the plan; measured acoustics require further evidence. Record the validator result, candidate ID, choice, and any unmet request. If exhausted or incomplete, preserve the first outcome and label any revised brief as a separate attempt.

## 3. Apply, reopen, and make one visible edit

1. Apply the chosen candidate. Reopen its project link, enter **Visit house**, and inspect the bedroom. Record its home ID and first applied revision. In **Design presentation**, select **Download whole-home scene manifest** and save it as `before.json` in the run directory.
2. In **Design a home**, request a move of the bedroom desk chair along the desk. Preview the changed reservation, check validation, and apply once. Record the second revision, bedroom chair and desk IDs, and the chair’s old and new plan coordinates in metres. If the edit also changed finishes or another object, record that explicitly.
3. Reopen the second revision and inspect the chair in **Desk and chair** view. Save its **whole-home** export as `manifest.json`. The adjacent **Download bedroom manifest** control exports a different format. Keep one screenshot per revision from the same viewpoint.

## 4. Render and inspect the client book

In a second terminal at the checkout root, set `RUN` to the absolute directory printed in step 1. Use Blender 5.1.2 with Cycles. Keep both downloaded manifests byte-for-byte as exported.

```sh
shasum -a 256 "$RUN/before.json" "$RUN/manifest.json"
blender -b --factory-startup --python-exit-code 1 -P scripts/render_studio_home.py -- "$RUN/manifest.json" "$RUN/proof" --proof
.venv/bin/python scripts/publish_studio_board.py "$RUN/proof"
open "$RUN/proof/index.html"
```

The CPU proof uses 960 × 540 frames. Inspect the dimensioned floor plan, two composed eye-level views including the bedroom, material board, and furniture schedule. Compare the bedroom chair’s position relative to the desk in the plan, walkthrough, and bedroom frame. Print the book to PDF at **A3 landscape**, with browser headers and footers off. Reopen the PDF and check labels, image framing, page breaks, and the revision footer.

Compare the exported digest with `manifest_sha256` in `proof/receipt.json`, and check the home ID and revision against Town. Keep the PDF with the render receipt, manifest, proof assets, and notices. A published book link in Town requires an exact showcase identity. Open the locally produced book for this fresh project. If the renderer or publisher rejects the manifest, save the exact command, error, and failed input digest. Reserve 4K GPU time until the chair and book pass this CPU check. [Studio House render guide](STUDIO_HOME.md)

## 5. Exchange evidence and close the run

| Record | Capture during the run |
|---|---|
| Generation | Commit, launch command and ports, job and project IDs, prompt, lot, seed, agent outcomes, alternatives and selection rationale |
| Revision change | Both revision numbers and home IDs, both manifest hashes, chair and desk IDs, before/after chair positions and screenshots |
| Publication | Blender version, commands, receipt digest and path, PDF path, checked plan and bedroom pages, observed flaws or skipped steps |
| Hieu’s acceptance | One supported answer and one explicit insufficient-evidence answer, with the edited revision and source locators |

Send Hieu the revision change row and edited manifest when ready; he can build fixtures before then. Close the milestone when another teammate can follow the chair move across all three outputs and trace a chatbot answer to evidence from that same home.
