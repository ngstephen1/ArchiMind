"""Coordinate, surface, bounding-box and input-contract tests for furniture meshes."""

import json
from math import isfinite

import plotly.graph_objects as go
import pytest
from pydantic import ValidationError
from shapely import Polygon, box, union_all

from archimind.examples import create_sample_bedroom
from archimind.models import Furniture
from archimind.render import FurnitureGeometryError, render_furniture_3d


def item(category="generic", **changes):
    return Furniture.model_validate(
        {
            "id": "object",
            "name": "Object",
            "category": category,
            "x_m": 1.25,
            "y_m": 2.5,
            "width_m": 1.6,
            "depth_m": 2.0,
            "height_m": 0.75,
            **changes,
        }
    )


def points(mesh):
    return list(zip(mesh.x, mesh.y, mesh.z, strict=True))


def projected_footprint(meshes):
    polygons = []
    for mesh in meshes:
        vertices = points(mesh)
        for indices in zip(mesh.i, mesh.j, mesh.k, strict=True):
            polygon = Polygon([(vertices[i][0], vertices[i][1]) for i in indices])
            if polygon.area > 0:
                polygons.append(polygon)
    return union_all(polygons)


@pytest.mark.parametrize("category", ["bed", "desk", "wardrobe", "unknown"])
def test_exact_envelope_and_every_part_within_declared_bounds(category):
    source = item(category)
    meshes = render_furniture_3d(source)
    for axis, low, high in [
        ("x", source.x_m, source.x_m + source.width_m),
        ("y", source.y_m, source.y_m + source.depth_m),
        ("z", 0.0, source.height_m),
    ]:
        coordinates = [v for mesh in meshes for v in getattr(mesh, axis)]
        assert min(coordinates) == pytest.approx(low)
        assert max(coordinates) == pytest.approx(high)
        assert all(low <= v <= high for v in coordinates)
    footprint = projected_footprint(meshes)
    expected = box(
        source.x_m, source.y_m, source.x_m + source.width_m, source.y_m + source.depth_m
    )
    assert footprint.symmetric_difference(expected).area == pytest.approx(0, abs=1e-12)


@pytest.mark.parametrize("category", ["bed", "desk", "wardrobe", "generic"])
def test_each_part_is_a_closed_positive_volume_triangulated_cuboid(category):
    for mesh in render_furniture_3d(item(category)):
        assert isinstance(mesh, go.Mesh3d)
        vertices = points(mesh)
        edges = {}
        volume = 0
        for indices in zip(mesh.i, mesh.j, mesh.k, strict=True):
            a, b, c = (vertices[i] for i in indices)
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            cross = [
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            ]
            assert sum(v * v for v in cross) > 0
            volume += sum(a[i] * cross[i] for i in range(3)) / 6
            for first, last in zip(indices, (*indices[1:], indices[0]), strict=True):
                key = tuple(sorted((first, last)))
                edges[key] = edges.get(key, 0) + 1
        assert set(edges.values()) == {2}
        expected = (
            (max(mesh.x) - min(mesh.x))
            * (max(mesh.y) - min(mesh.y))
            * (max(mesh.z) - min(mesh.z))
        )
        assert volume == pytest.approx(expected)


def test_bed_base_mattress_pillows_have_correct_elevations():
    meshes = {
        mesh.meta["part"]: mesh
        for mesh in render_furniture_3d(item("bed", height_m=1.0))
    }
    assert set(meshes) == {"frame", "mattress", "left pillow", "right pillow"}
    assert set(meshes["frame"].z) == {0, 0.3}
    assert set(meshes["mattress"].z) == {0.3, 0.85}
    assert set(meshes["left pillow"].z) == {0.85, 1}
    assert max(meshes["left pillow"].x) < min(meshes["right pillow"].x)


def test_desk_legs_reach_tabletop_and_leave_open_space_below():
    meshes = render_furniture_3d(item("desk", height_m=1.0))
    tabletop = next(mesh for mesh in meshes if mesh.meta["part"] == "tabletop")
    legs = [mesh for mesh in meshes if "leg" in mesh.meta["part"]]
    assert len(legs) == 4
    assert set(tabletop.z) == {0.88, 1}
    assert all(set(leg.z) == {0, 0.88} for leg in legs)
    center_x, center_y = 1.25 + 0.8, 2.5 + 1
    assert all(
        not (min(leg.x) < center_x < max(leg.x) and min(leg.y) < center_y < max(leg.y))
        for leg in legs
    )


def test_sample_storage_wardrobe_has_panels_and_correct_full_height():
    source = create_sample_bedroom().furniture[2]
    meshes = render_furniture_3d(source)
    assert {mesh.meta["appearance"] for mesh in meshes} == {"wardrobe"}
    assert {mesh.meta["part"] for mesh in meshes} == {
        "plinth",
        "cabinet",
        "left panel",
        "right panel",
        "left handle",
        "right handle",
    }
    assert max(v for mesh in meshes for v in mesh.z) == 2


@pytest.mark.parametrize(
    "category,name", [("sofa", "Sofa"), ("storage", "Chest"), ("other", "Bed")]
)
def test_generic_fallback_is_one_exact_solid(category, name):
    source = item(category, name=name)
    meshes = render_furniture_3d(source)
    assert len(meshes) == 1
    assert meshes[0].meta["appearance"] == "generic"
    assert set(points(meshes[0])) == {
        (x, y, z) for x in (1.25, 2.85) for y in (2.5, 4.5) for z in (0, 0.75)
    }


def test_hover_includes_escaped_identity_dimensions_position_height():
    source = item("desk", name="<Desk>", id="desk&1", x_m=-2.0)
    meshes = render_furniture_3d(source)
    assert sum(bool(mesh.showlegend) for mesh in meshes) == 1
    for mesh in meshes:
        assert mesh.meta["id"] == "desk&1"
        assert set(mesh.ids) == {"desk&1"}
        hover = mesh.hovertemplate
        for text in (
            "&lt;Desk&gt;",
            "desk&amp;1",
            "desk",
            "(-2, 2.5)",
            "1.6 × 2 × 0.75",
            "Height: 0.75",
        ):
            assert text in hover
        assert "<Desk>" not in hover


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_unsupported_rotation_is_explicit(rotation):
    with pytest.raises(FurnitureGeometryError, match="only rotation 0"):
        render_furniture_3d(item(rotation_deg=rotation))


def test_schema_revalidation_catches_nested_edits():
    source = item()
    source.width_m = -1
    with pytest.raises(ValidationError):
        render_furniture_3d(source)


@pytest.mark.parametrize(
    "changes",
    [
        {"x_m": 1e300},
        {"width_m": 1e300, "depth_m": 1e300},
        {"width_m": 1e-300, "depth_m": 1e-300, "x_m": 0.0, "y_m": 0.0},
    ],
)
def test_unrepresentable_spans_and_areas_fail_explicitly(changes):
    with pytest.raises(FurnitureGeometryError):
        render_furniture_3d(item(**changes))


@pytest.mark.parametrize("category", ["bed", "desk", "wardrobe", "generic"])
def test_deterministic_serialization_and_no_input_mutation(category):
    source = item(category, x_m=-1.5)
    before = source.model_dump_json()
    first = go.Figure(data=render_furniture_3d(source))
    second = go.Figure(data=render_furniture_3d(source))
    assert first.to_json() == second.to_json()
    assert source.model_dump_json() == before
    assert all(
        isfinite(v) for trace in first.data for v in (*trace.x, *trace.y, *trace.z)
    )
    assert json.loads(go.Figure(json.loads(first.to_json())).to_json()) == json.loads(
        first.to_json()
    )
