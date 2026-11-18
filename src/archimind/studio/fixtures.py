"""Reviewed offline examples, clearly distinguished from live AI concepts."""

from archimind.studio.contracts import ConceptItem, FurnishingPlan, Part, Recipe


def example_plan(kind: str) -> FurnishingPlan:
    groups = {
        "Bedroom": [
            ("Queen bed", "bed", 1.6, 2.0, 0.8),
            ("Writing desk", "desk", 1.4, 0.7, 0.75),
            ("Wardrobe", "storage", 1.0, 0.5, 1.8),
        ],
        "Living room": [
            ("Sofa", "sofa", 2.2, 0.95, 0.9),
            ("Coffee table", "table", 1.0, 0.6, 0.45),
            ("Reading chair", "chair", 0.7, 0.7, 0.8),
        ],
        "Home office": [
            ("Work desk", "desk", 1.4, 0.7, 0.75),
            ("Task chair", "chair", 0.6, 0.6, 0.85),
            ("Bookcase", "storage", 0.8, 0.4, 1.8),
        ],
    }
    return FurnishingPlan(
        description="Offline example furnishings with proposed concept dimensions; no product claims.",
        wall_color="#e8e1d5",
        floor_color="#bfaa88",
        items=tuple(
            ConceptItem(
                name=n,
                category=c,
                description="Reviewed offline procedural example",
                width_m=w,
                depth_m=d,
                height_m=h,
                quantity=1,
            )
            for n, c, w, d, h in groups[kind]
        ),
    )


def example_recipe(category: str) -> Recipe:
    parts = []

    def part(size, center, color="#98734f", kind="box"):
        parts.append(
            Part(kind=kind, size=size, center=center, color=color, roughness=0.75)
        )

    if category == "bed":
        part((1.0, 0.25, 1.0), (0.5, 0.125, 0.5))
        part((0.96, 0.35, 0.88), (0.5, 0.425, 0.55), "#eee8da")
        part((1.0, 1.0, 0.08), (0.5, 0.5, 0.04))
        for x in (0.27, 0.73):
            part((0.35, 0.1, 0.2), (x, 0.65, 0.2), "#f6f1e8")
        part((0.95, 0.05, 0.55), (0.5, 0.625, 0.7), "#66858a")
    elif category in ("desk", "table"):
        part((1.0, 0.1, 1.0), (0.5, 0.95, 0.5))
        for x in (0.06, 0.94):
            for z in (0.06, 0.94):
                part((0.08, 0.9, 0.08), (x, 0.45, z), "#554b40")
        if category == "desk":
            part((0.5, 0.15, 0.75), (0.5, 0.825, 0.5))
    elif category == "storage":
        for x in (0.025, 0.975):
            part((0.05, 1.0, 1.0), (x, 0.5, 0.5))
        part((1.0, 1.0, 0.04), (0.5, 0.5, 0.02), "#80684f")
        for y in (0.025, 0.25, 0.5, 0.75, 0.975):
            part((1.0, 0.05, 1.0), (0.5, y, 0.5))
        for x, c in ((0.18, "#456b74"), (0.3, "#ab5b45"), (0.42, "#d3b37a")):
            part((0.08, 0.16, 0.7), (x, 0.355, 0.45), c)
    elif category in ("chair", "sofa"):
        part((1.0, 0.15, 1.0), (0.5, 0.475, 0.5), "#69878d")
        part((1.0, 0.45, 0.15), (0.5, 0.775, 0.075), "#59777d")
        for x in (0.08, 0.92):
            for z in (0.08, 0.92):
                part((0.08, 0.4, 0.08), (x, 0.2, z), "#554b40")
        if category == "sofa":
            for x in (0.06, 0.94):
                part((0.12, 0.2, 0.95), (x, 0.65, 0.5), "#59777d")
            for x in (0.28, 0.72):
                part((0.38, 0.06, 0.7), (x, 0.58, 0.55), "#88a2a5")
    else:
        part((0.5, 0.07, 0.5), (0.5, 0.035, 0.5), "#4d5457", "cylinder")
        part((0.07, 0.8, 0.07), (0.5, 0.47, 0.5), "#4d5457", "cylinder")
        part((1.0, 0.2, 1.0), (0.5, 0.9, 0.5), "#e7cf9d", "cone")
    return Recipe(parts=tuple(parts))
