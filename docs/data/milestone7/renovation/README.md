# Shared partitions in Town

Open a saved gallery home, choose **Renovate**, and click the shared room edge or select the two rooms by name. Drag the edge or enter a signed distance in metres. Both proposed footprints and areas update as you drag. Choose **Wall**, **Door** or **Opening**. The width and offset run along the partition from the west edge. Check the proposal, then save the new revision. Town checks both rooms, fixed furnishings, opening alignment and the walkable paths. Undo creates a new revision.

## Browser evidence

Chrome at 1440 × 1000 used a local six-room fixture, project `aff79a22-91e3-414e-ace0-7ab66cbb8ec4`. The reproducible seed is [the furnished residence](../../furnished-residence/home.json).

| Revision | Browser action and result |
| --- | --- |
| 1 → 2 | Selected Salon / Living, dragged the partition and set its final move to 0.03 m north. The two rooms occupy the same combined footprint. [Preview](renovation-slide.jpg) |
| 2 → 3 | Added a 1.00 m opening between Kitchen-Dining and Study, 2.00 m from the west edge. Reloaded revision 3 and verified both values. [Preview](renovation-opening.jpg) |
| 3 → 4 → 5 | Closed the opening, then undid the closure. The saved home in revision 5 matched revision 3. |
| 5 | Previewed reversing the 0.03 m partition move. The salon changed from 33.04 to 32.84 m² and living from 36.09 to 36.29 m². [Live areas](renovation-live-areas.jpg) |

A keyboard walkthrough started at the same saved kitchen camera facing the edited partition in revisions 4 and 5. Walking forward stopped inside Kitchen-Dining against the solid wall in revision 4. In revision 5 it passed into Study through the restored opening.

Run `python -m pytest tests/test_town_renovation.py` from the repository root. Fixtures cover exterior wall stability, retained furniture and window locations, opening alignment, different portal heights and obstructed edits.

The editor supports full-width north/south room pairs in Town's rectangular gallery layouts. The coordinated kitchen-to-salon passage in a service-core layout and exterior shell are protected. This is a conceptual floor plan. A project designer needs site and structural information to assess a built partition.
