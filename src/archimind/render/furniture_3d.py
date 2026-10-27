"""Lightweight furniture meshes in canonical meters: X east, Y north, Z up.

Only rotation 0 is supported. Every part is an axis-aligned cuboid contained in
its furniture bounding box. Decorations use proportions of the declared sizes,
not external assets or inferred real-world dimensions. Rendering is not a spatial
validity check; overlaps and out-of-room positions are deliberately representable.
"""

from fractions import Fraction
from html import escape
from math import isfinite

import plotly.graph_objects as go

from archimind.models import Furniture


class FurnitureGeometryError(ValueError):
    """Furniture geometry cannot be displayed faithfully."""


# Eight vertices, twelve explicitly oriented triangles; no automatic hull filling.
_TRIANGLES = (
    (0, 2, 1),
    (0, 3, 2),
    (4, 5, 6),
    (4, 6, 7),
    (0, 1, 5),
    (0, 5, 4),
    (1, 2, 6),
    (1, 6, 5),
    (2, 3, 7),
    (2, 7, 6),
    (3, 0, 4),
    (3, 4, 7),
)


def _appearance(item: Furniture) -> str:
    category = item.category.strip().casefold()
    if category in ("bed", "desk", "wardrobe"):
        return category
    # The canonical sample uses category=storage, name=Wardrobe. Other storage
    # objects retain the generic solid rather than being guessed to be wardrobes.
    if category == "storage" and item.name.strip().casefold() == "wardrobe":
        return "wardrobe"
    return "generic"


def _parts(appearance: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Return part/color and normalized x0,x1,y0,y1,z0,z1 inside [0,1]."""
    if appearance == "bed":
        return [
            ("frame", "#957252", ("0", "1", "0", "1", "0", ".3")),
            ("mattress", "#C6D9D1", (".035", ".965", ".035", ".965", ".3", ".85")),
            ("left pillow", "#F5F0E5", (".1", ".46", ".75", ".92", ".85", "1")),
            ("right pillow", "#F5F0E5", (".54", ".9", ".75", ".92", ".85", "1")),
        ]
    if appearance == "desk":
        parts = [("tabletop", "#769E96", ("0", "1", "0", "1", ".88", "1"))]
        for x0, x1, side in [("0", ".08", "west"), (".92", "1", "east")]:
            for y0, y1, end in [("0", ".12", "south"), (".88", "1", "north")]:
                parts.append(
                    (f"{end} {side} leg", "#876D57", (x0, x1, y0, y1, "0", ".88"))
                )
        return parts
    if appearance == "wardrobe":
        return [
            ("plinth", "#957252", ("0", "1", "0", "1", "0", ".04")),
            ("cabinet", "#AC8D67", ("0", "1", ".04", "1", ".04", "1")),
            ("left panel", "#C5A780", (".02", ".49", ".01", ".04", ".04", ".96")),
            ("right panel", "#C5A780", (".51", ".98", ".01", ".04", ".04", ".96")),
            ("left handle", "#52636A", (".45", ".47", "0", ".01", ".46", ".56")),
            ("right handle", "#52636A", (".53", ".55", "0", ".01", ".46", ".56")),
        ]
    return [("solid", "#98A9BF", ("0", "1", "0", "1", "0", "1"))]


def _cuboid(
    item: Furniture, bounds: tuple[str, ...]
) -> list[tuple[float, float, float]]:
    values = [Fraction(value) for value in bounds]
    spans = []
    for start, size, low, high in zip(
        (item.x_m, item.y_m, 0.0),
        (item.width_m, item.depth_m, item.height_m),
        values[::2],
        values[1::2],
        strict=True,
    ):
        origin, length = Fraction(str(start)), Fraction(str(size))
        try:
            first, last = float(origin + low * length), float(origin + high * length)
            area_scale = float((high - low) * length)
        except OverflowError as exc:
            raise FurnitureGeometryError(
                "Furniture coordinates exceed numeric limits"
            ) from exc
        if (
            not all(isfinite(value) for value in (first, last, area_scale))
            or last <= first
        ):
            raise FurnitureGeometryError("A furniture span collapsed or is non-finite")
        spans.append((first, last))
    # Reject numeric overflow/underflow in face areas, as in the structural renderer.
    lengths = [Fraction(str(last)) - Fraction(str(first)) for first, last in spans]
    for a, b in ((0, 1), (0, 2), (1, 2)):
        try:
            area = float(lengths[a] * lengths[b])
        except OverflowError as exc:
            raise FurnitureGeometryError(
                "Furniture face area exceeds numeric limits"
            ) from exc
        if not isfinite(area) or area <= 0:
            raise FurnitureGeometryError("Furniture face has no finite positive area")
    (x0, x1), (y0, y1), (z0, z1) = spans
    return [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]


def render_furniture_3d(furniture: Furniture) -> list[go.Mesh3d]:
    """Return recognizable, bounded part meshes without changing the input.

    Name/category select appearance only. Every cuboid uses the supplied position
    and dimensions. Unknown categories fall back to a single exact solid.
    Nonzero rotations and unrepresentable numeric spans raise explicit errors.
    """
    item = Furniture.model_validate(furniture)
    if item.rotation_deg != 0:
        raise FurnitureGeometryError(
            f"3D furniture rendering supports only rotation 0: {item.id!r} has {item.rotation_deg}°"
        )
    appearance = _appearance(item)
    hover = (
        f"<b>{escape(item.name)}</b><br>ID: {escape(item.id)}<br>"
        f"Category: {escape(item.category)}<br>"
        f"Position: ({item.x_m:g}, {item.y_m:g}) m<br>"
        f"Dimensions: {item.width_m:g} × {item.depth_m:g} × {item.height_m:g} m<br>"
        f"Height: {item.height_m:g} m<br>Rotation: 0°<extra></extra>"
    )
    meshes = []
    for index, (part, color, bounds) in enumerate(_parts(appearance)):
        vertices = _cuboid(item, bounds)
        meshes.append(
            go.Mesh3d(
                x=[v[0] for v in vertices],
                y=[v[1] for v in vertices],
                z=[v[2] for v in vertices],
                i=[t[0] for t in _TRIANGLES],
                j=[t[1] for t in _TRIANGLES],
                k=[t[2] for t in _TRIANGLES],
                flatshading=True,
                color=color,
                opacity=1.0,
                lighting={"ambient": 0.75, "diffuse": 0.65, "specular": 0.08},
                name=escape(item.name),
                legendgroup=f"furniture:{item.id}",
                showlegend=index == 0,
                ids=[item.id] * len(vertices),
                hovertemplate=hover,
                meta={
                    "kind": "furniture",
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "appearance": appearance,
                    "part": part,
                    "x_m": item.x_m,
                    "y_m": item.y_m,
                    "width_m": item.width_m,
                    "depth_m": item.depth_m,
                    "height_m": item.height_m,
                },
            )
        )
    return meshes
