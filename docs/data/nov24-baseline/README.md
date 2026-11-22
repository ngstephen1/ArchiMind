# November 24 design quality baseline

Runtime baseline `c7e33364d2b148293b62ae26ad59375bdb1eb9ce`. The fixtures and visual targets support the November 22–30 sprint. Hieu owns the brief evaluation. Nguyen owns the fixed-camera visual pass. [Sprint tracker #54](https://github.com/ngstephen1/ArchiMind/issues/54) · [Brief evaluation #55](https://github.com/ngstephen1/ArchiMind/issues/55) · [Visual baseline #57](https://github.com/ngstephen1/ArchiMind/issues/57)

## Twelve public acceptance briefs

[Briefs and expected outcomes](briefs.json) includes the complete submitted text, initial controls, typed provider fixtures and expected decisions. [Baseline receipt](brief-receipt.json) records actual outcomes, provider fixture counts, timings and candidate hashes.

| Case | Accepted result |
| --- | --- |
| Compact lot | Five rooms on 12 × 13 m with validated circulation |
| Entertaining | Formal salon with two candidates ordered by measured separation from kitchen-dining |
| Study separation | Two candidates ordered by measured study-to-living separation |
| Confirmed split dining | Six places required with four modeled seats in each of two rooms |
| Single table | Ask for a decision while retaining the six-place requirement |
| Metric passage | Enforce 0.65 m in the geometry validator |
| Conflicting widths | Ask the user to confirm one modeled width |
| Local sofa clearance | Explain the unsupported clearance and return no candidate |
| Locked bedroom | Preserve the bedroom geometry and keep the entire input snapshot immutable |
| Ambiguous desk | Ask which desk or room and return no candidate |
| Mandatory second storey | Explain the unsupported geometry and return no candidate |
| Tight lot | Report search exhaustion without shrinking the 1.4 m requirement |

Replay from the repository root in the existing development environment.

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q -rxX -o junit_family=xunit1 \
  --junitxml=/tmp/archimind-nov24-briefs.xml tests/test_town_nov24_baseline.py
```

Read each JUnit test case's `observation` property as JSON. Candidate hashes bind the returned geometry and evidence. Elapsed milliseconds cover interpretation and generation on the test host and exclude the saved fixture setup and the second verification pass. Each provider fixture call returns typed data in-process. The run uses zero external model calls and measures no browser or network latency. `--runxfail` exposes the two known baseline defects as ordinary failures.

Hieu should review the expectations before tuning. Keep six distinct live prompts and their expected outcomes with the evaluation owner until the candidate is fixed. Prepare one per reserved slot below. Reuse the scoring rules but change room names, numbers or phrasing enough to test generalization. Hold back the prompt text, answer key and any client data from the training or tuning corpus. This package specifies the six slots. The private prompts and live outcome receipts are still due in [held-out evaluation #68](https://github.com/ngstephen1/ArchiMind/issues/68).

1. Hosting and home-office trade-offs on a fresh lot.
2. Ambiguous or conflicting seating that needs a confirmation.
3. A width conversion and circulation check on a compact lot.
4. A room lock and a targeted change to a saved revision.
5. Two plausible object referents in a saved-design follow-up.
6. A requested conclusion that needs site, supplier or acoustic evidence.

### Scoring

Apply each row independently. Mark candidate difference `N/A` for expected clarification, abstention or a one-result edit. Report the per-row scores and the reason for every zero or `N/A`. A release candidate must score 2 on hard constraints and source accuracy on every case. For a supported A/B case, require 2 on candidate difference as well. Treat loss of a hard requirement, invented measurements, or a change to the prior saved snapshot as a release defect regardless of total score.

| Axis | 2 | 1 | 0 |
| --- | --- | --- | --- |
| Hard constraints | Every mandatory input is checked, or the system stops at the correct boundary and retains the requirement | Requirement survives but the recovery question is incomplete | Lost, substituted or unverified requirement reaches a candidate, or the original snapshot changes |
| Source accuracy | Claims recompute from the identified geometry, revision or eligible record. Unknowns are explicit | Correct scope with incomplete evidence labeling | Wrong revision, invented fact or unsupported accessibility, acoustic or fit assertion |
| Candidate difference | Both validate and differ on a named metric computed from the candidates | Distinct valid geometry with no verified trade-off | Duplicate or invalid alternatives |
| Latency | An actionable response appears within 45 seconds | Actionable response after 45 seconds and within the existing 180-second job deadline | No actionable response by the deadline |
| Provider use | Requests and usage are attributable to the explicit action and within its configured budget | Recorded calls are within budget and some usage metadata is missing | Extra, unbounded or untracked calls |

The 45-second threshold is the review target chosen for this baseline. Report fixture and live latency separately. For live runs, record time to first valid preview or terminal clarification, total elapsed time, clarification turns, configured model, actual call count and available token and cost observations. The fixture receipt scores behavior and records local latency. It does not award points for browser or billed provider behavior.

## Revision-2 visual baseline

[Camera and artifact receipt](visual-baseline.json) binds the three saved views to the [revision-2 Town manifest](../live-quality-proof/live-manifest-r2.json) and the SHA-256 of the packed Blender scene. Keep the same saved manifest, eye, target, FOV, architectural shift, output framing, AgX treatment and exposure for the styling comparison. The three source PNGs are 1920 × 1080 at a maximum of 96 Cycles CPU samples on Blender 5.1.2. If a lighting trial changes exposure, archive that version separately and retain the fixed-exposure pair. [Packed scene and proof](https://github.com/ngstephen1/ArchiMind/actions/runs/44993303088) · [Full-resolution render and book](https://github.com/ngstephen1/ArchiMind/actions/runs/44994306268)

| Camera | Examine | Priority |
| --- | --- | --- |
| [Bedroom doorway](crops/bedroom-doorway.jpg) | Bed layers, rug return, opening and curtain folds. Use the full frame for circulation. | Give the bedding a legible duvet edge and pillow volume. Recover contrast where curtain and window trim meet. |
| [Bedroom desk](crops/bedroom-desk.jpg) | Belaya finish, sage upholstery, floor shadow and the chair pullout. | Keep contact at the chair legs and desk panels. Improve textile detail and preserve the visible approach. |
| [Salon overview](crops/salon-overview.jpg) | Landscape frame, window light, conversation seating, dining group and passage between them. | Recover pleat and jamb detail, improve upholstery seams and add texture to the seating rug. Keep the four dining seats and visible route. |

Each JPEG is a crop of its verified PNG, identified by pixel bounds and hash in the receipt. Use the same crop on the next full-resolution render without moving the camera. View the full frames for context before scoring. The field `architectural_projection` records the salon's level target and vertical shift. The two bedroom shots have no such shift.

### Visual scoring

Score each criterion at 0 (missing or distracting), 1 (readable with a visible issue), or 2 (clear at full size and the same detail remains legible in the presentation). A dash means the shot cannot provide adequate evidence. These first-pass image observations are concept visualization scores. Confirm circulation and fit separately against the saved plan and on-site dimensions where applicable.

| Criterion | Doorway | Desk | Salon | Score 2 when |
| --- | --- | --- | --- | --- |
| Believable bedding and materials | 1 | 1 | 1 | Duvet and pillows show layering at plausible scale. Timber, cloth and walls separate at both crop and full-frame scale. |
| Window highlight detail | 1 | — | 1 | At least one lit jamb, mullion and adjacent curtain folds remain distinct without a broad blank white patch. |
| Grounded furniture | 2 | 2 | 2 | Visible feet and panels meet the floor without gaps, floating or intersections. |
| Coherent furnishing | 1 | 1 | 1 | Visible furniture and materials read as a coordinated scheme with appropriate visual weight for the room. |
| Visible circulation | 2 | 2 | 2 | The approach past the desk or between seating and dining is readable in the full frame and corresponds to the saved plan. |

The next visual pass should reach 2 on the applicable bedding/material and window rows in the doorway and salon, with no regression in grounding or circulation. Revalidate any added floor-standing item against the furniture reservations. A catalog mesh, photographed surface, or model score supplies no measurement of the actual site.
