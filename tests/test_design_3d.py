"""Composition tests against canonical 2D geometry and existing structural meshes."""

import json

import plotly.graph_objects as go
import pytest
from pydantic import ValidationError

from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates
from archimind.render import (
    MAX_DESIGN_3D_FURNITURE,
    FurnitureGeometryError,
    RoomGeometryError,
    render_design_3d,
    render_floorplan,
    render_room_3d,
)


def furniture(figure):
    return [trace for trace in figure.data if trace.meta.get("kind") == "furniture"]


def _without_legend(trace):
    return {
        key: value
        for key, value in trace.to_plotly_json().items()
        if key != "showlegend"
    }


def test_structural_meshes_and_openings_unchanged_with_closer_camera():
    design = create_sample_bedroom()
    room = render_room_3d(design.room)
    complete = render_design_3d(design)
    # Composition changes legend visibility, not structural geometry or hover data.
    assert [_without_legend(t) for t in complete.data[: len(room.data)]] == [
        _without_legend(t) for t in room.data
    ]
    assert sum(
        v * v for v in complete.layout.scene.camera.eye.to_plotly_json().values()
    ) < sum(v * v for v in room.layout.scene.camera.eye.to_plotly_json().values())
    assert complete.layout.scene.camera.up == room.layout.scene.camera.up
    assert complete.layout.scene.camera.projection.type == "perspective"
    assert room.layout.scene.camera.projection.type == "orthographic"
    assert {t.meta["kind"] for t in complete.data} >= {
        "floor",
        "wall",
        "door_outline",
        "window",
        "window_outline",
        "furniture",
    }
    assert complete.layout.meta["spatially_validated"] is False


@pytest.mark.parametrize("index", range(3))
def test_furniture_coordinates_match_2d_footprint_and_height(index):
    design = create_sample_bedroom()
    source = design.furniture[index]
    plan = next(
        t
        for t in render_floorplan(design).data
        if t.meta.get("kind") == "furniture" and t.meta["id"] == source.id
    )
    meshes = [
        t for t in furniture(render_design_3d(design)) if t.meta["id"] == source.id
    ]
    assert min(v for t in meshes for v in t.x) == min(plan.x)
    assert max(v for t in meshes for v in t.x) == pytest.approx(max(plan.x), abs=1e-12)
    assert min(v for t in meshes for v in t.y) == min(plan.y)
    # The 2D renderer uses binary float addition; 3D endpoints use decimal spans.
    assert max(v for t in meshes for v in t.y) == pytest.approx(max(plan.y), abs=1e-12)
    assert min(v for t in meshes for v in t.z) == 0
    assert max(v for t in meshes for v in t.z) == source.height_m


def test_empty_furniture_list_is_structural_geometry():
    design = create_sample_bedroom()
    design.furniture = []
    complete = render_design_3d(design)
    assert not furniture(complete)
    assert [_without_legend(t) for t in complete.data] == [
        _without_legend(t) for t in render_room_3d(design.room).data
    ]


def test_equal_meter_scaling_includes_tall_and_out_of_room_furniture():
    design = create_sample_bedroom()
    design.furniture[0].x_m = -2.0
    design.furniture[0].height_m = 4.5
    before = design.model_dump_json()
    scene = render_design_3d(design).layout.scene
    assert tuple(scene.xaxis.range) == (-2, 5)
    assert tuple(scene.yaxis.range) == (0, 4)
    assert tuple(scene.zaxis.range) == (0, 4.5)
    ratios = [
        getattr(scene.aspectratio, axis) / (limits[1] - limits[0])
        for axis, limits in zip(
            "xyz",
            [scene.xaxis.range, scene.yaxis.range, scene.zaxis.range],
            strict=True,
        )
    ]
    assert ratios == pytest.approx([ratios[0]] * 3)
    assert scene.aspectmode == "manual"
    assert scene.camera.projection.type == "perspective"
    assert design.model_dump_json() == before


def test_overlap_is_rendered_without_being_declared_valid_or_repositioned():
    design = create_sample_bedroom()
    design.furniture[1].x_m = design.furniture[0].x_m
    design.furniture[1].y_m = design.furniture[0].y_m
    figure = render_design_3d(design)
    for item in design.furniture:
        meshes = [t for t in furniture(figure) if t.meta["id"] == item.id]
        assert min(v for t in meshes for v in t.x) == item.x_m
        assert min(v for t in meshes for v in t.y) == item.y_m
    assert figure.layout.meta["spatially_validated"] is False


def test_deterministic_order_json_and_no_mutation():
    design = create_sample_bedroom()
    before = design.model_dump_json()
    first = render_design_3d(design)
    design.furniture.reverse()
    reordered = design.model_dump_json()
    assert first.to_json() == render_design_3d(design).to_json()
    assert design.model_dump_json() == reordered
    design.furniture.reverse()
    assert design.model_dump_json() == before
    assert json.loads(go.Figure(json.loads(first.to_json())).to_json()) == json.loads(
        first.to_json()
    )


def test_generated_layouts_render_without_altering_positions_or_reports():
    source = create_sample_bedroom()
    result = generate_layout_candidates(source.room, source.furniture, seed=42)
    before = result.model_dump_json()
    assert len(result.candidates) == 2
    for candidate in result.candidates:
        figure = render_design_3d(candidate.design)
        for item in candidate.design.furniture:
            meshes = [t for t in furniture(figure) if t.meta["id"] == item.id]
            assert min(v for t in meshes for v in t.x) == item.x_m
            assert min(v for t in meshes for v in t.y) == item.y_m
    assert result.model_dump_json() == before


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_rotations_fail_before_returning_incorrect_scene(rotation):
    design = create_sample_bedroom()
    design.furniture[0].rotation_deg = rotation
    with pytest.raises(FurnitureGeometryError):
        render_design_3d(design)


def test_full_design_is_schema_revalidated():
    design = create_sample_bedroom()
    design.furniture[0].id = design.room.id
    with pytest.raises(ValidationError):
        render_design_3d(design)


def test_invalid_structural_openings_keep_existing_error():
    design = create_sample_bedroom()
    design.room.doors.append(design.room.doors[0].model_copy(update={"id": "second"}))
    with pytest.raises(RoomGeometryError, match="overlap"):
        render_design_3d(design)


def test_work_limit_is_explicit():
    design = create_sample_bedroom()
    source = design.furniture[0]
    design.furniture = [
        source.model_copy(update={"id": f"item-{i}"})
        for i in range(MAX_DESIGN_3D_FURNITURE + 1)
    ]
    with pytest.raises(FurnitureGeometryError, match="at most"):
        render_design_3d(design)


# AppTest checks the rendered figure data, not just the presence of a heading.
def _app_furnished(app):
    return next(
        go.Figure(json.loads(chart.proto.spec))
        for chart in app.get("plotly_chart")
        if chart.key == "design-3d"  # Standalone sample, not the synchronized view.
    )


def _app():
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30
    ).run()


def test_streamlit_furnished_fixed_sample_and_structural_preview_both_render():
    app = _app()
    assert not app.exception
    assert "Interactive 3D Furnished Room Preview" in [h.value for h in app.subheader]
    assert any(
        "Fixed sample bedroom — independent of the selected Layout A/B." in c.value
        for c in app.caption
    )
    figure = _app_furnished(app)
    assert {t.meta["id"] for t in furniture(figure)} == {
        "queen-bed",
        "desk",
        "wardrobe",
    }
    assert json.loads(figure.to_json()) == json.loads(
        render_design_3d(create_sample_bedroom()).to_json()
    )
    structural = next(
        json.loads(chart.proto.spec)
        for chart in app.get("plotly_chart")
        if json.loads(chart.proto.spec)["layout"].get("meta", {}).get("kind")
        == "room_3d"
    )
    assert not any(t["meta"].get("kind") == "furniture" for t in structural["data"])


def test_layout_selection_and_regeneration_preserve_fixed_furnished_sample():
    app = _app()
    before = _app_furnished(app).to_json()
    app.button(key="generate_layouts").click().run()
    assert not app.exception
    assert _app_furnished(app).to_json() == before
    app.radio(key="selected_layout").set_value("Layout B").run()
    assert _app_furnished(app).to_json() == before
    app.number_input(key="layout_seed").set_value(43).run()
    app.button(key="generate_layouts").click().run()
    assert not app.exception
    assert _app_furnished(app).to_json() == before
