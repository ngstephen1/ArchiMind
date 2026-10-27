"""Assert actual wall triangles, opening gaps, coordinates, and app integration."""

import json
from pathlib import Path

import plotly.graph_objects as go
import pytest
from pydantic import ValidationError
from shapely import Polygon, box, union_all
from streamlit.testing.v1 import AppTest

from archimind.examples import create_sample_bedroom
from archimind.models import Door, Room, RoomDesign, Window
from archimind.render import (
    MAX_ROOM_3D_OPENINGS,
    RoomGeometryError,
    render_floorplan,
    render_room_3d,
)

WALLS = ("north", "south", "east", "west")
APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _room(**changes: object) -> Room:
    return Room.model_validate(
        {
            "id": "room",
            "name": "Test room",
            "width_m": 5.0,
            "depth_m": 4.0,
            "ceiling_height_m": 2.7,
            **changes,
        }
    )


def _door(identifier: str = "door", **changes: object) -> Door:
    return Door.model_validate(
        {
            "id": identifier,
            "wall": "south",
            "offset_m": 0.7,
            "width_m": 0.9,
            "height_m": 2.1,
            **changes,
        }
    )


def _window(identifier: str = "window", **changes: object) -> Window:
    return Window.model_validate(
        {
            "id": identifier,
            "wall": "north",
            "offset_m": 2.3,
            "width_m": 0.9,
            "height_m": 1.1,
            "sill_height_m": 0.8,
            **changes,
        }
    )


def _trace(figure: go.Figure, kind: str, **metadata):
    return next(
        trace
        for trace in figure.data
        if trace.meta.get("kind") == kind
        and all(trace.meta.get(key) == value for key, value in metadata.items())
    )


def _triangles(trace, axes: tuple[str, str]) -> list[Polygon]:
    first, second = (getattr(trace, axis) for axis in axes)
    return [
        Polygon([(first[index], second[index]) for index in (i, j, k)])
        for i, j, k in zip(trace.i, trace.j, trace.k, strict=True)
    ]


def _solid_wall(figure: go.Figure, wall: str):
    axes = ("x", "z") if wall in ("north", "south") else ("y", "z")
    triangles = [
        triangle
        for trace in figure.data
        if trace.meta.get("kind") == "wall" and trace.meta["wall"] == wall
        for triangle in _triangles(trace, axes)
    ]
    assert all(triangle.is_valid and triangle.area > 0 for triangle in triangles)
    solid = union_all(triangles)
    assert solid.area == pytest.approx(sum(triangle.area for triangle in triangles))
    return solid


def _opening_box(opening: Door | Window):
    bottom = opening.sill_height_m if isinstance(opening, Window) else 0.0
    return box(
        opening.offset_m,
        bottom,
        opening.offset_m + opening.width_m,
        bottom + opening.height_m,
    )


def _assert_wall_coverage(figure: go.Figure, room: Room, wall: str) -> None:
    length = room.width_m if wall in ("north", "south") else room.depth_m
    full = box(0.0, 0.0, length, room.ceiling_height_m)
    holes = [
        _opening_box(opening)
        for opening in [*room.doors, *room.windows]
        if opening.wall == wall
    ]
    solid = _solid_wall(figure, wall)
    expected = full.difference(union_all(holes))
    assert solid.symmetric_difference(expected).area == pytest.approx(0.0, abs=1e-12)
    for hole in holes:
        assert solid.intersection(hole).area == pytest.approx(0.0, abs=1e-12)


def test_valid_interactive_figure_is_json_serializable() -> None:
    figure = render_room_3d(create_sample_bedroom().room)
    assert isinstance(figure, go.Figure)
    assert all(isinstance(trace, (go.Mesh3d, go.Scatter3d)) for trace in figure.data)
    restored = go.Figure(json.loads(figure.to_json()))
    assert json.loads(restored.to_json()) == json.loads(figure.to_json())
    json.dumps(figure.to_plotly_json(), allow_nan=False)
    assert figure.layout.meta["units"] == "m"
    assert figure.layout.meta["origin"] == "southwest_floor"
    assert figure.layout.width is None


def test_floor_dimensions_origin_and_triangles() -> None:
    room = _room(width_m=6.5, depth_m=3.25)
    floor = _trace(render_room_3d(room), "floor")
    assert set(zip(floor.x, floor.y, floor.z)) == {
        (0, 0, 0),
        (6.5, 0, 0),
        (6.5, 3.25, 0),
        (0, 3.25, 0),
    }
    geometry = union_all(_triangles(floor, ("x", "y")))
    assert geometry.equals(box(0, 0, 6.5, 3.25))
    assert geometry.area == 6.5 * 3.25


@pytest.mark.parametrize("wall", WALLS)
def test_empty_opening_walls_have_correct_plane_height_and_full_coverage(
    wall: str,
) -> None:
    room = _room()
    figure = render_room_3d(room)
    trace = _trace(figure, "wall", wall=wall)
    fixed_axis, fixed_value = {
        "south": ("y", 0),
        "north": ("y", 4),
        "west": ("x", 0),
        "east": ("x", 5),
    }[wall]
    assert set(getattr(trace, fixed_axis)) == {fixed_value}
    assert min(trace.z) == 0 and max(trace.z) == room.ceiling_height_m
    _assert_wall_coverage(figure, room, wall)


@pytest.mark.parametrize("wall", WALLS)
def test_door_and_window_openings_are_real_gaps_on_every_wall(wall: str) -> None:
    door, window = _door(wall=wall), _window(wall=wall)
    room = _room(doors=[door], windows=[window])
    figure = render_room_3d(room)
    _assert_wall_coverage(figure, room, wall)
    for other_wall in set(WALLS) - {wall}:
        _assert_wall_coverage(figure, room, other_wall)
    axes = ("x", "z") if wall in ("north", "south") else ("y", "z")
    pane = _trace(figure, "window", id=window.id)
    glass = union_all(_triangles(pane, axes))
    assert glass.symmetric_difference(_opening_box(window)).area == pytest.approx(
        0, abs=1e-12
    )
    assert 0 < pane.opacity < 1
    outline = _trace(figure, "door_outline", id=door.id)
    along = outline.x if wall in ("north", "south") else outline.y
    assert set(along) == {0.7, 1.6}
    assert set(outline.z) == {0.0, 2.1}
    expected_fixed = {
        "south": ("y", 0),
        "north": ("y", 4),
        "east": ("x", 5),
        "west": ("x", 0),
    }[wall]
    assert set(getattr(outline, expected_fixed[0])) == {expected_fixed[1]}
    assert set(getattr(pane, expected_fixed[0])) == {expected_fixed[1]}
    assert not any(
        isinstance(trace, go.Mesh3d) and trace.meta.get("kind") == "door"
        for trace in figure.data
    )


@pytest.mark.parametrize("wall", WALLS)
@pytest.mark.parametrize("at_end", [False, True])
def test_corner_openings_preserve_wall_endpoints(wall: str, at_end: bool) -> None:
    length = 5.0 if wall in ("north", "south") else 4.0
    door = _door(wall=wall, offset_m=length - 0.8 if at_end else 0.0, width_m=0.8)
    room = _room(doors=[door])
    _assert_wall_coverage(render_room_3d(room), room, wall)


def test_multiple_nonoverlapping_openings_leave_all_gaps_and_remaining_wall() -> None:
    room = _room(
        doors=[
            _door("first", offset_m=0.2, width_m=0.8),
            _door("second", offset_m=2.0),
        ],
        windows=[_window(wall="south", offset_m=3.2, width_m=1.1)],
    )
    figure = render_room_3d(room)
    _assert_wall_coverage(figure, room, "south")
    assert _solid_wall(figure, "south").area == pytest.approx(
        5 * 2.7 - 0.8 * 2.1 - 0.9 * 2.1 - 1.1 * 1.1
    )


def test_stacked_openings_with_overlapping_horizontal_spans_are_supported() -> None:
    room = _room(
        doors=[_door(offset_m=1.0, width_m=1.0, height_m=1.8)],
        windows=[
            _window(
                wall="south", offset_m=1.2, width_m=0.6, sill_height_m=2.0, height_m=0.5
            )
        ],
    )
    figure = render_room_3d(room)
    _assert_wall_coverage(figure, room, "south")
    assert _solid_wall(figure, "south").covers(box(1.2, 1.8, 1.8, 2.0))


@pytest.mark.parametrize("kind", ["door", "window"])
def test_full_wall_opening_has_no_wall_faces(kind: str) -> None:
    source = (
        _door(offset_m=0.0, width_m=5.0, height_m=2.7)
        if kind == "door"
        else _window(
            wall="south", offset_m=0.0, width_m=5.0, height_m=2.7, sill_height_m=0.0
        )
    )
    room = _room(**{"doors" if kind == "door" else "windows": [source]})
    figure = render_room_3d(room)
    assert _solid_wall(figure, "south").is_empty
    _assert_wall_coverage(figure, room, "south")


@pytest.mark.parametrize("kind", ["doors", "windows", "mixed"])
def test_positive_area_overlapping_openings_raise_explicit_geometry_error(
    kind: str,
) -> None:
    if kind == "doors":
        room = _room(doors=[_door("first"), _door("second", offset_m=1.0)])
    elif kind == "windows":
        room = _room(windows=[_window("first"), _window("second", offset_m=2.5)])
    else:
        room = _room(
            doors=[_door("first")],
            windows=[_window("second", wall="south", offset_m=1.0)],
        )
    before = room.model_dump_json()
    with pytest.raises(RoomGeometryError, match="first.*second.*overlap"):
        render_room_3d(room)
    assert room.model_dump_json() == before


@pytest.mark.parametrize("direction", ["side_by_side", "stacked"])
def test_touching_opening_boundaries_are_allowed(direction: str) -> None:
    if direction == "side_by_side":
        room = _room(
            doors=[
                _door("a", offset_m=0.5, width_m=1.0),
                _door("b", offset_m=1.5, width_m=1.0),
            ]
        )
    else:
        room = _room(
            doors=[_door(offset_m=1.0, width_m=1.0)],
            windows=[
                _window(
                    wall="south",
                    offset_m=1.0,
                    width_m=1.0,
                    sill_height_m=2.1,
                    height_m=0.6,
                )
            ],
        )
    _assert_wall_coverage(render_room_3d(room), room, "south")


def test_matching_offsets_on_different_walls_do_not_conflict() -> None:
    room = _room(doors=[_door("a", wall="north"), _door("b", wall="south")])
    figure = render_room_3d(room)
    for wall in WALLS:
        _assert_wall_coverage(figure, room, wall)


def test_decimal_openings_touch_wall_and_ceiling_without_addition_drift() -> None:
    room = _room(
        width_m=5.1,
        depth_m=4.1,
        doors=[_door(offset_m=4.2, width_m=0.9)],
        windows=[
            _window(
                wall="west", offset_m=3.2, width_m=0.9, sill_height_m=1.1, height_m=1.6
            )
        ],
    )
    figure = render_room_3d(room)
    assert max(_trace(figure, "door_outline").x) == 5.1
    pane = _trace(figure, "window")
    assert max(pane.y) == 4.1
    assert max(pane.z) == 2.7
    for wall in WALLS:
        _assert_wall_coverage(figure, room, wall)


@pytest.mark.parametrize("wall", WALLS)
def test_opening_xy_coordinates_match_existing_2d_projection(wall: str) -> None:
    room = _room(doors=[_door(wall=wall)], windows=[_window(wall=wall)])
    two = render_floorplan(RoomDesign(room=room))
    three = render_room_3d(room)
    for kind, third_kind in (("door", "door_outline"), ("window", "window")):
        flat, spatial = _trace(two, kind), _trace(three, third_kind)
        expected = sorted(set(zip(flat.x, flat.y)))
        actual = sorted(set(zip(spatial.x, spatial.y)))
        assert len(expected) == len(actual) == 2
        for point_2d, point_3d in zip(expected, actual, strict=True):
            assert point_3d == pytest.approx(point_2d)


def test_metric_scaling_isometric_camera_and_interactive_controls() -> None:
    room = _room()
    figure = render_room_3d(room)
    scene = figure.layout.scene
    assert scene.aspectmode == "manual"
    ratios = scene.aspectratio
    assert ratios.x / room.width_m == pytest.approx(ratios.y / room.depth_m)
    assert ratios.y / room.depth_m == pytest.approx(ratios.z / room.ceiling_height_m)
    for axis, maximum in ((scene.xaxis, 5.0), (scene.yaxis, 4.0), (scene.zaxis, 2.7)):
        assert tuple(axis.range) == (0.0, maximum)
        assert "(m)" in axis.title.text
    eye = scene.camera.eye
    assert abs(eye.x) == abs(eye.y) == abs(eye.z)
    assert scene.camera.up.z == 1
    assert scene.camera.projection.type == "orthographic"
    assert scene.dragmode == "orbit"
    assert figure.layout.uirevision


def test_room_input_unchanged_and_geometry_deterministic_under_opening_reordering() -> (
    None
):
    room = _room(
        doors=[_door("z", offset_m=0.1), _door("a", offset_m=2.0)],
        windows=[_window("y", offset_m=0.1), _window("b", offset_m=2.0)],
    )
    before = room.model_dump_json()
    expected = render_room_3d(room).to_json()
    assert render_room_3d(room).to_json() == expected
    assert room.model_dump_json() == before
    reordered = room.model_copy(deep=True)
    reordered.doors.reverse()
    reordered.windows.reverse()
    assert render_room_3d(reordered).to_json() == expected


def test_duplicate_opening_ids_reuse_canonical_schema_validation() -> None:
    room = _room(doors=[_door("same")], windows=[_window("same")])
    with pytest.raises(ValidationError, match="Duplicate"):
        render_room_3d(room)


def test_mutated_invalid_room_is_revalidated() -> None:
    room = _room(doors=[_door()])
    room.doors[0].offset_m = 10.0
    with pytest.raises(ValidationError):
        render_room_3d(room)


@pytest.mark.parametrize("size", [1e200, 1e-200])
def test_unrepresentable_panel_areas_raise_geometry_errors(size: float) -> None:
    with pytest.raises(RoomGeometryError, match="area"):
        render_room_3d(_room(width_m=size, depth_m=size))


def test_collapsed_opening_endpoints_raise_geometry_errors() -> None:
    room = _room(width_m=1e100, doors=[_door(offset_m=1e99, width_m=1.0)])
    with pytest.raises(RoomGeometryError, match="collapsed"):
        render_room_3d(room)


def test_work_bound_returns_an_explicit_geometry_error() -> None:
    room = _room(doors=[_door(str(index)) for index in range(MAX_ROOM_3D_OPENINGS + 1)])
    with pytest.raises(RoomGeometryError, match="at most"):
        render_room_3d(room)


def _app_3d_figure(app: AppTest) -> go.Figure:
    return next(
        go.Figure(json.loads(chart.proto.spec))
        for chart in app.get("plotly_chart")
        if json.loads(chart.proto.spec)["layout"].get("meta", {}).get("kind")
        == "room_3d"
    )


def test_streamlit_contains_structural_3d_preview_and_required_caption() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not app.exception
    assert "Interactive 3D Room Preview" in [heading.value for heading in app.subheader]
    assert (
        "3D structural preview — furniture and layout synchronization will be added in upcoming phases."
        in [item.value for item in app.caption]
    )
    figure = _app_3d_figure(app)
    floor = _trace(figure, "floor")
    assert max(floor.x) == 5 and max(floor.y) == 4
    assert figure.layout.scene.zaxis.range[1] == 2.7
    assert not any(
        trace.meta.get("kind", "").startswith("furniture") for trace in figure.data
    )


def test_selecting_a_different_layout_preserves_structural_3d_geometry() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    before = _app_3d_figure(app).to_json()
    app.button(key="generate_layouts").click().run()
    assert _app_3d_figure(app).to_json() == before
    app.radio(key="selected_layout").set_value("Layout B").run()
    assert not app.exception
    assert _app_3d_figure(app).to_json() == before
    assert app.radio(key="selected_layout").value == "Layout B"
