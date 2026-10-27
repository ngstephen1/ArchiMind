"""Coordinate-based tests for the canonical-model floor-plan renderer."""

import json
from pathlib import Path

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from archimind.examples import create_sample_bedroom
from archimind.models import Room, RoomDesign
from archimind.render import render_floorplan


def _trace(figure: go.Figure, kind: str, **metadata: str) -> go.Scatter:
    return next(
        trace
        for trace in figure.data
        if trace.meta.get("kind") == kind
        and all(trace.meta.get(key) == value for key, value in metadata.items())
    )


def test_returns_serializable_plotly_figure() -> None:
    figure = render_floorplan(create_sample_bedroom())
    assert isinstance(figure, go.Figure)
    assert json.loads(figure.to_json())["layout"]["meta"]["units"] == "m"
    go.Figure(figure.to_dict())


def test_room_extent_and_metric_proportions() -> None:
    figure = render_floorplan(create_sample_bedroom())
    floor = next(
        shape for shape in figure.layout.shapes if shape.name == "Room footprint"
    )
    assert (floor.x0, floor.y0, floor.x1, floor.y1) == (0, 0, 5, 4)
    assert (floor.x1 - floor.x0) / (floor.y1 - floor.y0) == 5 / 4
    assert figure.layout.xaxis.range[0] < 0 < 5 < figure.layout.xaxis.range[1]
    assert figure.layout.yaxis.range[0] < 0 < 4 < figure.layout.yaxis.range[1]


def test_walls_for_empty_room() -> None:
    design = RoomDesign(
        room=Room(id="room", name="Empty", width_m=7, depth_m=3, ceiling_height_m=2.7)
    )
    figure = render_floorplan(design)
    expected = {
        "south": ((0, 7), (0, 0)),
        "north": ((0, 7), (3, 3)),
        "east": ((7, 7), (0, 3)),
        "west": ((0, 0), (0, 3)),
    }
    for wall, (x, y) in expected.items():
        trace = _trace(figure, "wall", wall=wall)
        assert tuple(trace.x[:2]) == x
        assert tuple(trace.y[:2]) == y


@pytest.mark.parametrize(
    ("kind", "collection"), [("door", "doors"), ("window", "windows")]
)
@pytest.mark.parametrize(
    ("wall", "x", "y"),
    [
        ("north", (1.1, 2.0), (4.0, 4.0)),
        ("south", (1.1, 2.0), (0.0, 0.0)),
        ("east", (5.0, 5.0), (1.1, 2.0)),
        ("west", (0.0, 0.0), (1.1, 2.0)),
    ],
)
def test_opening_coordinates_on_each_wall(
    kind: str, collection: str, wall: str, x: tuple, y: tuple
) -> None:
    data = create_sample_bedroom().model_dump()
    opening = data["room"][collection][0]
    opening.update(wall=wall, offset_m=1.1, width_m=0.9)
    figure = render_floorplan(RoomDesign.model_validate(data))
    trace = _trace(figure, kind, id=opening["id"])
    assert tuple(trace.x) == pytest.approx(x)
    assert tuple(trace.y) == pytest.approx(y)
    assert trace.meta["wall"] == wall


def test_room_walls_leave_opening_spans_clear() -> None:
    figure = render_floorplan(create_sample_bedroom())
    south = _trace(figure, "wall", wall="south")
    north = _trace(figure, "wall", wall="north")
    assert tuple(value for value in south.x if value is not None) == pytest.approx(
        (0, 0.6, 1.45, 5)
    )
    assert tuple(value for value in north.x if value is not None) == pytest.approx(
        (0, 2.7, 4.2, 5)
    )


def test_full_width_opening_has_no_wall_stroke() -> None:
    data = create_sample_bedroom().model_dump()
    data["room"]["doors"][0].update(offset_m=0, width_m=5)
    figure = render_floorplan(RoomDesign.model_validate(data))
    assert list(_trace(figure, "wall", wall="south").x) == []
    assert tuple(_trace(figure, "door", id="south-door").x) == (0, 5)


def test_overlapping_openings_are_drawn_without_spatial_validation() -> None:
    data = create_sample_bedroom().model_dump()
    data["room"]["windows"][0].update(wall="south", offset_m=0.9, width_m=1.2)
    figure = render_floorplan(RoomDesign.model_validate(data))
    wall = _trace(figure, "wall", wall="south")
    assert tuple(value for value in wall.x if value is not None) == pytest.approx(
        (0, 0.6, 2.1, 5)
    )
    assert tuple(_trace(figure, "door", id="south-door").x) == pytest.approx(
        (0.6, 1.45)
    )
    assert tuple(_trace(figure, "window", id="north-window").x) == pytest.approx(
        (0.9, 2.1)
    )


def test_furniture_footprints_names_and_identifiers() -> None:
    design = create_sample_bedroom()
    figure = render_floorplan(design)
    for item in design.furniture:
        trace = _trace(figure, "furniture", id=item.id)
        assert tuple(trace.x) == pytest.approx(
            (
                item.x_m,
                item.x_m + item.width_m,
                item.x_m + item.width_m,
                item.x_m,
                item.x_m,
            )
        )
        assert tuple(trace.y) == pytest.approx(
            (
                item.y_m,
                item.y_m,
                item.y_m + item.depth_m,
                item.y_m + item.depth_m,
                item.y_m,
            )
        )
        assert set(trace.ids) == {item.id}
        assert trace.meta["name"] == item.name
        assert item.id in trace.hovertemplate
        assert item.name in trace.hovertemplate
        assert item.id in trace.text
        assert f"Size: {item.width_m:g} × {item.depth_m:g} m" in trace.text
        label = _trace(figure, "furniture_label", id=item.id)
        assert list(label.text) == [item.name]
        assert label.x[0] == pytest.approx(item.x_m + item.width_m / 2)
        assert label.y[0] == pytest.approx(item.y_m + item.depth_m / 2)


def test_equal_scale_and_interaction_are_enabled() -> None:
    figure = render_floorplan(create_sample_bedroom())
    assert figure.layout.yaxis.scaleanchor == "x"
    assert figure.layout.yaxis.scaleratio == 1
    assert figure.layout.xaxis.fixedrange is False
    assert figure.layout.yaxis.fixedrange is False
    assert figure.layout.yaxis.range[0] < figure.layout.yaxis.range[1]
    assert figure.layout.dragmode == "pan"


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_nonzero_rotations_are_explicitly_rejected(rotation: int) -> None:
    design = create_sample_bedroom()
    design.furniture[0].rotation_deg = rotation
    before = design.model_dump_json()
    with pytest.raises(ValueError, match="Nonzero furniture rotations.*queen-bed"):
        render_floorplan(design)
    assert design.model_dump_json() == before


def test_renderer_does_not_mutate_design() -> None:
    design = create_sample_bedroom()
    before = design.model_dump_json()
    render_floorplan(design)
    assert design.model_dump_json() == before


def test_out_of_room_furniture_is_visible_not_rejected() -> None:
    design = create_sample_bedroom()
    design.furniture[0].x_m = -2
    design.furniture[0].y_m = 5
    figure = render_floorplan(design)
    assert figure.layout.xaxis.range[0] < -2
    assert figure.layout.yaxis.range[1] > 7
    assert _trace(figure, "furniture", id="queen-bed").x[0] == -2


def test_sample_factory_is_reproducible_and_returns_fresh_models() -> None:
    first, second = create_sample_bedroom(), create_sample_bedroom()
    assert first == second
    assert (first.room.width_m, first.room.depth_m, first.room.ceiling_height_m) == (
        5,
        4,
        2.7,
    )
    assert first.room.doors[0].wall == "south"
    assert first.room.windows[0].wall == "north"
    assert all(item.rotation_deg == 0 for item in first.furniture)
    first.furniture[0].name = "Changed"
    assert second.furniture[0].name == "Queen bed"


def test_app_displays_the_canonical_sample_and_caption() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()
    assert not app.exception
    assert "2D Floor Plan Preview" in [heading.value for heading in app.subheader]
    assert (
        "Demonstration layout — spatial validation and automatic placement "
        "are not yet implemented."
    ) in [caption.value for caption in app.caption]
    chart = app.get("plotly_chart")[0]
    figure = go.Figure(json.loads(chart.proto.spec))
    assert figure.layout.meta["room_id"] == create_sample_bedroom().room.id
    assert tuple(_trace(figure, "door", id="south-door").x) == pytest.approx(
        (0.6, 1.45)
    )
