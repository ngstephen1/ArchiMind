# Prepare an existing-conditions CAD plan

A senior designer can use the survey exporter for a single room with straight walls, including angled bays and concave footprints. It produces editable metric linework for the existing conditions and a list of site questions. Keep each edition with its field notes and photographs.

## Field intake

1. Mark the inside finished wall faces and choose an X/Y origin that the next surveyor can find. Sketch a north arrow and record the instrument, visit date, drawing datum, units and source references. Convert survey measurements to metres before entry.
2. Number the plan corners counterclockwise from zero. Each wall runs from its corner to the next, and the last wall closes to the first. A door or window offset runs along this directed face from its starting corner to the first jamb. Record width, height and sill above the finished floor. For a hinged door, identify the hinge at the start or end jamb and record the inward or outward swing.
3. Locate fixed items independently. Each fixture footprint starts at its local lower-left corner, extends along local positive X and Y, and rotates counterclockwise in degrees about that corner. Record vertical limits and obstructions separately. Curved walls, profiled millwork, slopes and changing ceilings need supplemental survey drawings.
4. Take independent check dimensions between identified corners. Use the precision supported by your instrument and observations. Enter differences as field questions and preserve each survey edition.

This invented example demonstrates the file format. Replace the dimensions, sources and field notes with project evidence before marking an intake as measured.

```json
{
  "source_kind": "demonstration",
  "geometry_source": "S1",
  "sources": [{"id": "S1", "description": "Illustrative measured-plan exercise"}],
  "vertices_m": [[0,0], [4,0], [4,3], [3,4], [0,4]],
  "height_m": 2.8,
  "openings": [
    {"id":"D1","kind":"door","wall":0,"offset_m":0.5,"width_m":0.9,"height_m":2.1,"sill_m":0,"source":"S1","hinge":"end","swing":"inward"},
    {"id":"W1","kind":"window","wall":2,"offset_m":0.2,"width_m":1.0,"height_m":1.2,"sill_m":0.7,"source":"S1"}
  ],
  "fixtures": [
    {"id":"cabinet","x_m":2,"y_m":2,"width_m":0.8,"depth_m":0.4,"rotation_deg":90,"source":"S1"}
  ],
  "checks": [{"start":0,"end":2,"length_m":5.0,"tolerance_m":0.01,"source":"S1"}],
  "field_checks": ["Confirm clearance in front of the cabinet."]
}
```

Use `source_kind: measured` for sourced site measurements or `archival` for a documented historic polygon. An archival intake can have an unknown ceiling height (`null`). Where archival evidence gives only an overall size, retain it as research until the perimeter can be measured or sourced.

## Export and review

### Current bedroom field record

Give the field record a date and the bedroom project ID. Add a source ID beside each value on the sketch or in the measurement log. Keep the original record with the survey edition. Leave unresolved measurements blank and list the missing observations in `field_checks`.

| Record | What to capture |
| --- | --- |
| Perimeter and height | Each finished-face wall run and bay segment, at least one independent check dimension, and finished floor-to-ceiling height. |
| Window and door | Window jamb positions, sill height, reveal depth and trim projection. Door jamb positions, hinge end, swing direction and clear opening. |
| Fixed services and retained furniture | Outlet wall, offset and height. Locate fixed obstructions and record each retained item's footprint and height. |
| Desk and chair | Desk clear width, height to the lowest underside obstruction and usable knee depth. Chair arm height, width and overall depth. Record where the chair stands tucked in, occupied and pulled back, and measure the narrowest remaining passage in each state. |

Use the current field record for the bedroom project. Keep the whole-home demonstration under its own project ID. The Zane Street archive supplies an angled-bay observation and nominal room dimensions. Its current condition, exact perimeter and ceiling height still need field evidence.

Save the JSON as `room-survey.json`. From the installed ArchiMind environment run:

```sh
python -m archimind.designer_handoff.survey room-survey.json --output output/room-survey-v1
```

Open `existing-conditions.dxf` in CAD using metres and model-space scale 1:1. Isolate WALLS, DOORS, WINDOWS, DOOR_LEAVES and FIXTURES as needed. Use the distance tool on two known points, confirm the directed opening offsets and compare each swing with the field sketch. Hinged symbols show a schematic 90-degree opening. Verify the physical clear opening, limits of operation and trim on site.

Read `field-verification.json` for calculated area, lengths, evidence IDs and unresolved checks. `survey.json` retains the original input bytes. The verification list covers recorded and detectable discrepancies. The receiving designer still verifies site conditions, elevations, services, regulatory requirements and vendor dimensions before developing construction or procurement documents. Export corrections to a fresh edition directory.

For a rectangular Town bedroom, call `write_drawings(board, destination, provenance="survey-linked", survey=survey)` with the verified intake. Record an independent check dimension across the room. If the site inspection found no fixed obstructions, set `fixture_inventory_source` to the ID of the field record documenting that observation. The exporter compares the four vertices in room-local southwest-first order, ceiling and every opening with the selected room. It rejects unresolved field checks, unmodelled fixed fixtures and discrepancies. Each SVG includes the digest of the validated survey model. Keep the survey and CAD plan with the SVGs to review door operation. For an irregular room, use the surveyed DXF directly.

[Example archival bedroom with original plan and photo](../handovers/zane-street/README.md) · [Studio House designer transfer](STUDIO_HOUSE_DESIGNER_TRANSFER.md)
