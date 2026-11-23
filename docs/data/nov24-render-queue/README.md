# Town render-queue baseline

Ordinary Town at 1440 × 1000 in Chrome, served over loopback with a real Blender 5.1.2 Cycles CPU worker on GitHub's Ubuntu 24.04 runner. The checkout was `de3ad902868ed71823de8e5b331791dbd1765f63`, the PR merge snapshot of `80a8e6172aa8ce69a72c7433fed76447acf5e532` and base `c7e33364d2b148293b62ae26ad59375bdb1eb9ce`. The home is a public synthetic demo. The run used no model calls. [Successful run](https://github.com/ngstephen1/ArchiMind/actions/runs/45042836876) · [Download both exact manifests and worker logs](https://github.com/ngstephen1/ArchiMind/actions/runs/45042836876/artifacts/14762624984)

| Check | Observed result |
| --- | --- |
| Failure and retry | The isolated cache path was deliberately occupied by a file. Town displayed the failure and enabled [Render this revision](retry-visible.png) again. After removing the file, the same UI admitted the retry. |
| Queue and active walkthrough | The trace shows queued and Cycles processing. The [bedroom screenshot](walk-during-proof.png) is bracketed by observations of the active Cycles phase for revision 1. |
| Ready and byte integrity | Town exposed all five download links for [revision 1](proof-ready-r1.png) and [revision 2](proof-ready-r2.png) on opening the presentation. All ten HTTP responses matched their recorded hashes. |
| Cache reuse | A duplicate POST through the browser obtained the same ready response for each revision. Worker log bytes stayed unchanged. The rendered stage's UI button was disabled once ready. |
| Revision isolation | Revision 2 started idle and its proof manifest returned 404 while revision 1 stayed ready. Its independent queued job produced the exact published revision-2 manifest bytes. |

| Revision | Blender worker elapsed | Saved manifest SHA-256 | Packed blend SHA-256 |
| --- | ---: | --- | --- |
| 1 | 632.2 s | `80c549716097cf09b0210a2944d893cbdbf91f086080951e4ac1caccd0c5487c` | `c8c2c5fd42a25b2304ae9115d3d681c865c13f3bf3e24f89b0c8d13a92e62241` |
| 2 | 625.9 s | `6837f16fa22931f0338816deb9e10e1a96bf585cb389c86847b235139d757253` | `7ef63acf43476dd203450b141080ef844d44024d6e9d24ce679f04ced8391b2a` |

[Event timings](events.json) · [Download hashes and browser results](verification.json) · [Revision 1 receipt](r1-receipt.json) · [Revision 2 receipt](r2-receipt.json) · [Committed evidence hashes](SHA256SUMS.txt)

The deliberate failure occurred before Cycles started. The screenshots show proof-mode desktop Chrome. They establish an Ubuntu loopback worker baseline. Mac hardware, HD approval and an already open board updating its links without reopening remain outside this run's evidence.

The committed ready panels are historical UI captures. The workflow now uploads separate `proof-revision-r1.png` and `proof-revision-r2.png` captures identifying each saved revision, alongside the ready panels and hashed manifests.
