"""Exercise the editable chair profiles independently of Blender and glTF export."""

import math
import runpy
from collections import Counter
from pathlib import Path

import pytest

RECIPE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts" / "author_designer_chair.py")
)


@pytest.mark.parametrize("variant", ["gentle", "deep"])
def test_original_chair_has_closed_parts_native_dimensions_and_usable_seat(variant):
    parts = RECIPE["chair_meshes"](variant)
    assert len(parts) == len({name for name, *_ in parts}) == 10
    assert {finish for _, finish, _, _ in parts} == set(RECIPE["FINISHES"])

    points = []
    for name, _, vertices, faces in parts:
        points.extend(vertices)
        assert all(math.isfinite(c) for vertex in vertices for c in vertex)
        directed_edges = Counter()
        for face in faces:
            assert len(face) >= 3
            assert len(set(face)) == len(face)
            for a, b in zip(face, (*face[1:], face[0]), strict=True):
                assert 0 <= a < len(vertices) and 0 <= b < len(vertices)
                directed_edges[a, b] += 1
        assert all(
            count == directed_edges[b, a] == 1
            for (a, b), count in directed_edges.items()
        ), name

    x, y, z = zip(*points, strict=True)
    assert (min(x), max(x)) == pytest.approx((-0.240, 0.240))
    assert (min(y), max(y)) == pytest.approx((-0.260, 0.260))
    assert (min(z), max(z)) == pytest.approx((0.000, 0.830))
    cushion = next(vertices for n, _, vertices, _ in parts if n == "Sage seat cushion")
    assert max(z for x, y, z in cushion) == pytest.approx(0.455)


def test_variation_bends_the_back_and_meeting_uprights_without_resizing_the_chair():
    by_variant = {}
    for variant, expected_bend in (("gentle", 0.042), ("deep", 0.071)):
        parts = RECIPE["chair_meshes"](variant)
        profiles = {n: vertices for n, _, vertices, _ in parts}
        backrest = profiles["Steam-bent oak backrest"]
        center = max(y for x, y, z in backrest if x == 0)
        for x_tip in (min(x for x, y, z in backrest), max(x for x, y, z in backrest)):
            tip = max(y for x, y, z in backrest if x == x_tip)
            assert center - tip == pytest.approx(expected_bend)
        by_variant[variant] = profiles
    gentle, deep = by_variant["gentle"], by_variant["deep"]
    assert gentle.keys() == deep.keys()
    assert {name for name in gentle if gentle[name] != deep[name]} == {
        "Steam-bent oak backrest",
        "Left back upright",
        "Right back upright",
    }
