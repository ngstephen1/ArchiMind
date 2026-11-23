# Fresh Town revision pair

The ordinary Town UI started from a fresh local database on November 23, 2026.
It submitted the synthetic brief at [`e0d70e8`](https://github.com/ngstephen1/ArchiMind/commit/e0d70e816e77574568f4c726e1af743c21c7ee2d)
and returned two validated alternatives in **8.56 seconds**. Interpretation,
styling and visual critique each made one model request and completed. The
15 × 16 m lot, the requirement for six seats across two tables and the
0.65 m modeled passage survived generation. Both layouts modeled four
places in the salon and four in the kitchen-dining room. [Browser receipt](receipt.json) · [Worker events](events.json)

The measured hall route from study to living room was 8.62 m for Layout A and
3.25 m for B. The route from kitchen-dining to salon was 7.99 m for A and
3.29 m for B. The same geometry cannot establish acoustic privacy or glare.

## Saved edit

Project `1a3f1aff-0c41-4900-902f-34dc54050fda` used Layout A for revision 1.
Town saved the chair pullout as revision 2. The browser reopened both revisions
and verified revision 1 was unchanged.

| Revision | Whole-home render manifest | Saved Town snapshot |
| --- | --- | --- |
| 1 | [Manifest](manifest-r1.json) | [Snapshot](snapshot-r1.json) |
| 2 | [Manifest](manifest-r2.json) | [Snapshot](snapshot-r2.json) |

The measured movement is 0.300 m for `bedroom/desk-chair`. Its nearest
plan gap to `bedroom/belaya` increased from 0.060 m to 0.360 m. The distance
from the desk center to `bedroom-window` remained 2.49 m in plan. The recorded
chair answer asks for the clear width and height under the desk to establish
fit. The window answer reports distance and leaves glare and placement
intent open. [Paired calculations and SHA-256 digests](paired-measurements.json)

- [Desktop brief and confirmed controls](desktop-alternatives.png)
- [Desktop revision 2 chair explanation](desktop-saved-revision.png)
- [Narrow revision 2 plan](narrow-saved-revision.png)

A separate offline replay rebuilt the saved snapshots, checked both service
health endpoints and entered the same bedroom at desktop and narrow sizes.
Both revisions rendered the bedroom photographs. The replay made no provider
requests and ran against the replay code already on main at `9adf26f`.
[Replay receipt](replay-receipt.json)

| Saved walkthrough | Desktop | Narrow |
| --- | --- | --- |
| Revision 1 | [Desk and chair](walkthrough-1440-r1.jpg) | [Desk and chair](walkthrough-390-r1.jpg) |
| Revision 2 | [Desk and chair](walkthrough-1440-r2.jpg) | [Desk and chair](walkthrough-390-r2.jpg) |

## Reopen both revisions

After the [Town setup](../../../README.md#quick-start), run from the repository
root with Bash or Zsh and `shasum` on `PATH`. Stop any other Town launcher
running from that checkout first. A second launcher in the same checkout
would overwrite the persisted API and editor URLs. Run concurrent launchers
from separate checkouts.

The command checks the four archived files against their SHA-256 digests.
The replay builder also validates each saved home and reproduces its
manifest before opening an isolated local database with both AI providers
disabled.

```bash
replay_dir=$(mktemp -d) &&
repo_data="$PWD/docs/data/nov24-fresh-live" &&
(cd "$repo_data" && shasum -a 256 -c SHA256SUMS.txt) &&
ln -s "$repo_data/snapshot-r1.json" "$replay_dir/snapshot-r1.json" &&
ln -s "$repo_data/snapshot-r2.json" "$replay_dir/snapshot-r2.json" &&
ln -s "$repo_data/manifest-r1.json" "$replay_dir/before.json" &&
ln -s "$repo_data/manifest-r2.json" "$replay_dir/manifest.json" &&
.venv/bin/python scripts/reopen_conference_home.py "$replay_dir/town.sqlite3" --example "$replay_dir" &&
ARCHIMIND_ENABLE_OPENAI_STUDIO=0 ARCHIMIND_ENABLE_CODEX_ADVISOR=0 \
  TOWN_PORT=8852 TOWN_EDITOR_PORT=8853 TOWN_DB="$replay_dir/town.sqlite3" \
  .venv/bin/python scripts/run_town.py
```

Open [revision 1](http://127.0.0.1:8852/?project=1a3f1aff-0c41-4900-902f-34dc54050fda&revision=1)
and [revision 2](http://127.0.0.1:8852/?project=1a3f1aff-0c41-4900-902f-34dc54050fda&revision=2).
The fresh Blender proofs are tracked in [#69](https://github.com/ngstephen1/ArchiMind/issues/69).
Independent owner review remains separate from the automated browser run.

## Rehearse from the portable download

The [portable replay ZIP](Town-Replay-Candidate.zip) contains the same synthetic
project and both saved revisions. Its SHA-256 is
`3d3af89e785593ac8772c07594d7eca5e3374780eb9aaedb4e603e9b8d4b03c0`.
The ZIP includes a clean SQLite database, its source hashes and a start guide.
The database contains zero provider jobs and zero job events.

From the configured repository root, verify the outer digest and extract a
writable copy. This is an alternative to the snapshot-builder command above.

```bash
replay_dir=$(mktemp -d) &&
printf '%s  %s\n' \
  3d3af89e785593ac8772c07594d7eca5e3374780eb9aaedb4e603e9b8d4b03c0 \
  docs/data/nov24-fresh-live/Town-Replay-Candidate.zip | shasum -a 256 -c - &&
unzip -q docs/data/nov24-fresh-live/Town-Replay-Candidate.zip -d "$replay_dir" &&
(cd "$replay_dir" && shasum -a 256 -c SHA256SUMS.txt) &&
ARCHIMIND_ENABLE_OPENAI_STUDIO=0 ARCHIMIND_ENABLE_CODEX_ADVISOR=0 \
  TOWN_PORT=8852 TOWN_EDITOR_PORT=8853 TOWN_DB="$replay_dir/Town-Replay.sqlite3" \
  .venv/bin/python scripts/run_town.py
```

The ZIP records `98c80efa` as the reference checkout for replaying the
archived snapshots. A later test on
`7c900e1` opened a clean extraction of those same ZIP bytes. The database
passed SQLite integrity checks, both local endpoints returned HTTP 200,
and Chrome entered the bedroom and opened the design board for both
revisions at 1440 × 1000 and 390 × 844. View the
[inspected client book and designer archive](../nov24-fresh-book) separately.
The release and independent operator checks are tracked in
[#70](https://github.com/ngstephen1/ArchiMind/issues/70) and
[#72](https://github.com/ngstephen1/ArchiMind/issues/72).
