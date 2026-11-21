"""Surveyed finished-face room geometry and a metre-based, editable DXF plan."""

from math import atan2, cos, degrees, dist, radians, sin
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator
from shapely.geometry import Polygon

Length = Annotated[FiniteFloat, Field(gt=0)]
Nonnegative = Annotated[FiniteFloat, Field(ge=0)]
Text = Annotated[str, Field(min_length=1)]
Point = tuple[FiniteFloat, FiniteFloat]


class SurveyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SurveySource(SurveyRecord):
    id: Text
    description: Text


class Opening(SurveyRecord):
    id: Text
    kind: Literal["door", "window"]
    wall: Annotated[int, Field(ge=0, strict=True)]
    offset_m: Nonnegative
    width_m: Length
    height_m: Length
    sill_m: Nonnegative
    source: Text
    # Hinge side is relative to travel along the directed wall segment.
    hinge: Literal["start", "end"] | None = None
    swing: Literal["inward", "outward", "sliding", "fixed"] | None = None

    @model_validator(mode="after")
    def check_swing(self) -> Self:
        if self.kind == "window" and (self.hinge or self.swing):
            raise ValueError("Door swing fields belong on doors only.")
        if self.swing in {"inward", "outward"} and not self.hinge:
            raise ValueError("A hinged door swing needs its hinge end.")
        if self.hinge and self.swing not in {"inward", "outward"}:
            raise ValueError("State the direction of the hinged door swing.")
        return self


class Fixture(SurveyRecord):
    id: Text
    x_m: FiniteFloat
    y_m: FiniteFloat
    width_m: Length
    depth_m: Length
    source: Text
    rotation_deg: FiniteFloat = 0
    bottom_m: Nonnegative | None = None
    height_m: Length | None = None

    def corners(self) -> list[Point]:
        angle = radians(self.rotation_deg)
        return [
            (
                self.x_m + x * cos(angle) - y * sin(angle),
                self.y_m + x * sin(angle) + y * cos(angle),
            )
            for x, y in (
                (0, 0),
                (self.width_m, 0),
                (self.width_m, self.depth_m),
                (0, self.depth_m),
            )
        ]


class CheckMeasure(SurveyRecord):
    """Independent on-site measurement across two boundary vertices."""

    start: Annotated[int, Field(ge=0, strict=True)]
    end: Annotated[int, Field(ge=0, strict=True)]
    length_m: Length
    tolerance_m: Nonnegative
    source: Text


class Survey(SurveyRecord):
    source_kind: Literal["measured", "demonstration", "archival"]
    vertices_m: Annotated[list[Point], Field(min_length=3)]
    height_m: Length | None = None
    sources: Annotated[list[SurveySource], Field(min_length=1)]
    geometry_source: Text
    height_source: Text | None = None
    openings: list[Opening] = Field(default_factory=list)
    fixtures: list[Fixture] = Field(default_factory=list)
    checks: list[CheckMeasure] = Field(default_factory=list)
    field_checks: list[Text] = Field(default_factory=list)

    def wall(self, index: int) -> tuple[Point, Point]:
        return self.vertices_m[index], self.vertices_m[
            (index + 1) % len(self.vertices_m)
        ]

    def along(self, index: int, offset: float) -> Point:
        a, b = self.wall(index)
        t = offset / dist(a, b)
        return a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])

    def verification_items(self) -> list[str]:
        items = list(self.field_checks)
        if self.height_m is None:
            items.append("Measure finished floor-to-ceiling height on site.")
        for measure in self.checks:
            actual = dist(self.vertices_m[measure.start], self.vertices_m[measure.end])
            if abs(actual - measure.length_m) > measure.tolerance_m + 1e-9:
                items.append(
                    f"Vertices {measure.start}–{measure.end}: survey check {measure.length_m:g} m; drawing {actual:.4f} m; tolerance {measure.tolerance_m:g} m ({measure.source})."
                )
        for opening in self.openings:
            if opening.kind == "door" and opening.swing is None:
                items.append(
                    f"Verify the operating direction and clearance of door {opening.id}."
                )
        return items

    @model_validator(mode="after")
    def validate_geometry(self) -> Self:
        if self.height_m is None and self.source_kind != "archival":
            raise ValueError("Supply the measured ceiling height for this survey type.")
        if self.height_m is None and self.height_source is not None:
            raise ValueError("A ceiling-height source needs a height value.")
        if len(set(self.vertices_m)) != len(self.vertices_m):
            raise ValueError("Provide each finished-face vertex once.")
        polygon = Polygon(self.vertices_m)
        if not polygon.is_valid or polygon.area <= 0 or not polygon.exterior.is_ccw:
            raise ValueError("Provide a simple counterclockwise room polygon.")
        source_ids = {s.id for s in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("Duplicate survey source ID.")
        elements = [*self.openings, *self.fixtures]
        if len({o.id for o in elements}) != len(elements):
            raise ValueError("Duplicate opening or fixture ID.")
        references = {e.source for e in [*elements, *self.checks]}
        references.add(self.geometry_source)
        if self.height_source:
            references.add(self.height_source)
        if missing := references - source_ids:
            raise ValueError(f"Unknown survey sources: {sorted(missing)}")
        for m in self.checks:
            if m.start == m.end or max(m.start, m.end) >= len(self.vertices_m):
                raise ValueError(
                    "Check measure references an invalid pair of vertices."
                )
        for opening in self.openings:
            if opening.wall >= len(self.vertices_m):
                raise ValueError(f"{opening.id} references an unknown wall.")
            if (
                opening.offset_m + opening.width_m
                > dist(*self.wall(opening.wall)) + 1e-9
            ):
                raise ValueError(f"{opening.id} extends past the measured wall.")
            if (
                self.height_m is not None
                and opening.sill_m + opening.height_m > self.height_m + 1e-9
            ):
                raise ValueError(f"{opening.id} extends above the measured ceiling.")
        for i in range(len(self.vertices_m)):
            end = 0.0
            for opening in self.wall_openings(i):
                if opening.offset_m < end - 1e-9:
                    raise ValueError(
                        f"Overlapping plan openings on wall {i}; verify the survey."
                    )
                end = opening.offset_m + opening.width_m
        for fixture in self.fixtures:
            if not polygon.buffer(1e-9).covers(Polygon(fixture.corners())):
                raise ValueError(f"{fixture.id} extends outside the surveyed polygon.")
            if (
                fixture.bottom_m is not None
                and fixture.height_m is not None
                and self.height_m is not None
                and fixture.bottom_m + fixture.height_m > self.height_m + 1e-9
            ):
                raise ValueError(f"{fixture.id} extends above the measured ceiling.")
        return self

    def wall_openings(self, index: int) -> list[Opening]:
        return sorted(
            (o for o in self.openings if o.wall == index), key=lambda o: o.offset_m
        )


def write_survey_dxf(survey: Survey, path: Path) -> None:
    """Write a 1:1 2D existing-conditions DXF with editable CAD line entities."""
    content: list[str] = []

    def groups(*tags: tuple[int, object]) -> None:
        for code, value in tags:
            content.extend((str(code), str(value)))

    def point(code: int, xy: Point) -> None:
        groups((code, xy[0]), (code + 10, xy[1]), (code + 20, 0))

    def entity(kind: str, layer: str) -> None:
        groups((0, kind), (100, "AcDbEntity"), (8, layer))

    def line(layer: str, a: Point, b: Point) -> None:
        if dist(a, b) <= 1e-10:
            return
        entity("LINE", layer)
        groups((100, "AcDbLine"))
        point(10, a)
        point(11, b)

    def door_leaf(opening: Opening, a: Point, b: Point) -> None:
        hinge, closed = (a, b) if opening.hinge == "start" else (b, a)
        sign = 1 if opening.swing == "inward" else -1
        dx, dy = sign * (a[1] - b[1]), sign * (b[0] - a[0])
        line("DOOR_LEAVES", hinge, (hinge[0] + dx, hinge[1] + dy))
        start = degrees(atan2(closed[1] - hinge[1], closed[0] - hinge[0])) % 360
        end = degrees(atan2(dy, dx)) % 360
        if (end - start) % 360 > 180:
            start, end = end, start
        entity("ARC", "DOOR_LEAVES")
        groups((100, "AcDbCircle"))
        point(10, hinge)
        groups((40, opening.width_m), (100, "AcDbArc"), (50, start), (51, end))

    groups((0, "SECTION"), (2, "HEADER"), (9, "$ACADVER"), (1, "AC1015"))
    groups((9, "$INSUNITS"), (70, 6), (9, "$MEASUREMENT"), (70, 1), (0, "ENDSEC"))
    layers = {
        "0": 7,
        "WALLS": 7,
        "DOORS": 3,
        "WINDOWS": 4,
        "FIXTURES": 8,
        "DOOR_LEAVES": 3,
    }
    groups(
        (0, "SECTION"), (2, "TABLES"), (0, "TABLE"), (2, "LAYER"), (5, "F0"), (330, "0")
    )
    groups((100, "AcDbSymbolTable"), (70, len(layers)))
    for layer, color in layers.items():
        groups(
            (0, "LAYER"),
            (330, "F0"),
            (100, "AcDbSymbolTableRecord"),
            (100, "AcDbLayerTableRecord"),
        )
        groups((2, layer), (70, 0), (62, color), (6, "CONTINUOUS"))
    groups((0, "ENDTAB"), (0, "ENDSEC"), (0, "SECTION"), (2, "ENTITIES"))
    for index, vertex in enumerate(survey.vertices_m):
        walk = vertex
        for opening in survey.wall_openings(index):
            a = survey.along(index, opening.offset_m)
            b = survey.along(index, opening.offset_m + opening.width_m)
            line("WALLS", walk, a)
            line("DOORS" if opening.kind == "door" else "WINDOWS", a, b)
            if opening.swing in {"inward", "outward"}:
                door_leaf(opening, a, b)
            walk = b
        line("WALLS", walk, survey.wall(index)[1])
    for fixture in survey.fixtures:
        pts = fixture.corners()
        for i, a in enumerate(pts):
            line("FIXTURES", a, pts[(i + 1) % len(pts)])
    groups((0, "ENDSEC"), (0, "EOF"))
    Path(path).write_text("\n".join(content) + "\n", encoding="ascii")


def export_intake(source: Path, destination: Path) -> None:
    """Save the submitted evidence, editable plan and outstanding field checks together."""
    import hashlib
    import json
    import tempfile

    payload = source.read_bytes()
    survey = Survey.model_validate_json(payload)
    items = survey.verification_items()
    if not survey.checks:
        items.append("Record an independent check between two nonadjacent corners.")
    if not survey.openings:
        items.append(
            "Confirm the opening inventory and record measured jamb positions."
        )
    if not survey.fixtures:
        items.append("Confirm the inventory of fixed services and obstructions.")
    if survey.source_kind == "archival":
        items.append(
            "Verify archival measurements and current site conditions in the field."
        )
    report = {
        "source_kind": survey.source_kind,
        "intake_sha256": hashlib.sha256(payload).hexdigest(),
        "drawing_units": "metres",
        "measurement_datum": "internal finished wall faces at plan level",
        "plan_area_m2": Polygon(survey.vertices_m).area,
        "height_m": survey.height_m,
        "wall_lengths_m": [
            dist(*survey.wall(i)) for i in range(len(survey.vertices_m))
        ],
        "sources": [s.model_dump() for s in survey.sources],
        "opening_ids": [o.id for o in survey.openings],
        "fixture_ids": [f.id for f in survey.fixtures],
        "field_verification_items": items,
        "review_status": "pending professional review",
    }
    destination.parent.mkdir(exist_ok=True, parents=True)
    if destination.exists():
        raise FileExistsError(
            f"Choose a new output directory; {destination} already exists."
        )
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        edition = Path(temp) / "edition"
        edition.mkdir()
        write_survey_dxf(survey, edition / "existing-conditions.dxf")
        (edition / "survey.json").write_bytes(payload)
        (edition / "field-verification.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        edition.rename(destination)


def main() -> None:
    """Command-line entry point for the measured-room intake."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "survey", type=Path, help="Source-traceable metre-based survey JSON"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="New edition directory"
    )
    args = parser.parse_args()
    try:
        export_intake(args.survey, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Survey export failed: {exc}\n")
    print(
        f"Saved existing-conditions.dxf, survey.json and field-verification.json in {args.output}"
    )


if __name__ == "__main__":
    main()
