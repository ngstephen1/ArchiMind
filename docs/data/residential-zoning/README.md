# Town residential zoning comparison

Tested runtime `554dddc`. The synthetic Town project `58996f72-a0e3-4664-a20c-92ab45b86ec9` used a 15 × 16 m shell, seed 42 and a common six-room brief. Revision 1 is the gallery. Revision 2 is the grouped service core. See the [comparison receipt](comparison.json) for full home IDs, route measurements and snapshot digests.

Both revisions reserve a 1.35 × 0.60 m bedroom wardrobe and four seats at each modeled dining table. The gallery has a 3.29 m hall route between its kitchen and salon entrances. The grouped plan has an 8.78 m route via the hall and a direct shared opening with a checked 1.30 m crossing segment. The crossing covers only the segment through the opening. It starts and ends inside the two rooms.

| Gallery | Grouped service core |
| --- | --- |
| [Revision 1 floor plan](gallery.png) | [Revision 2 floor plan](service-core.png) |

The gate run included `pytest -q tests/test_town_zoning.py tests/test_town_service_layout.py tests/test_town_live_quality.py tests/test_town_brief_confirmation.py` (243 passed). The infeasible brief on a 9 × 9 m shell failed both-scheme acceptance. The locked salon case preserved the saved room and both sides of the connecting opening.

The provider-free [Chrome receipt](browser-receipt.json) covers the presentation at 1440 × 1000 and 390 × 844. Each of the four views downloaded both operation plans, the kitchen elevation and bathroom service diagram. The 16 downloaded SVGs matched the response bytes and selected project, revision and home. Blender rendering was disabled for this check.
