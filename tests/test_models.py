"""Deterministic schema tests; no geometry engine or network services required."""

import json

import pytest
from pydantic import BaseModel, ValidationError

from archimind.models import Door, Furniture, Room, RoomDesign, Window

VALID_DATA = {
    Room: {
        "id": "bedroom",
        "name": "Bedroom",
        "width_m": 5.0,
        "depth_m": 4.0,
        "ceiling_height_m": 2.7,
    },
    Door: {
        "id": "south-door",
        "wall": "south",
        "offset_m": 0.6,
        "width_m": 0.85,
        "height_m": 2.1,
    },
    Window: {
        "id": "north-window",
        "wall": "north",
        "offset_m": 2.7,
        "width_m": 1.5,
        "height_m": 1.2,
        "sill_height_m": 0.9,
    },
    Furniture: {
        "id": "queen-bed",
        "name": "Queen bed",
        "category": "bed",
        "x_m": 0.4,
        "y_m": 1.4,
        "width_m": 1.6,
        "depth_m": 2.0,
        "height_m": 0.6,
        "rotation_deg": 0,
    },
}

DIMENSION_FIELDS = [
    (Room, "width_m"),
    (Room, "depth_m"),
    (Room, "ceiling_height_m"),
    (Door, "width_m"),
    (Door, "height_m"),
    (Window, "width_m"),
    (Window, "height_m"),
    (Furniture, "width_m"),
    (Furniture, "depth_m"),
    (Furniture, "height_m"),
]

POSITION_FIELDS = [
    (Door, "offset_m"),
    (Window, "offset_m"),
    (Window, "sill_height_m"),
    (Furniture, "x_m"),
    (Furniture, "y_m"),
]


@pytest.fixture
def bedroom() -> RoomDesign:
    """A 5 x 4 x 2.7 m bedroom built directly with Python model constructors."""
    return RoomDesign(
        name="Sample bedroom",
        room=Room(
            **VALID_DATA[Room],
            doors=[Door(**VALID_DATA[Door])],
            windows=[Window(**VALID_DATA[Window])],
        ),
        furniture=[
            Furniture(**VALID_DATA[Furniture]),
            Furniture(
                id="desk",
                name="Desk",
                category="desk",
                x_m=3.2,
                y_m=3.2,
                width_m=1.2,
                depth_m=0.6,
                height_m=0.75,
            ),
            Furniture(
                id="wardrobe",
                name="Wardrobe",
                category="storage",
                x_m=3.4,
                y_m=0.4,
                width_m=1.5,
                depth_m=0.6,
                height_m=2.0,
            ),
        ],
    )


def test_valid_bedroom(bedroom: RoomDesign) -> None:
    assert bedroom.room.width_m == 5
    assert bedroom.room.depth_m == 4
    assert bedroom.room.ceiling_height_m == 2.7
    assert bedroom.room.doors[0].wall == "south"
    assert bedroom.room.windows[0].wall == "north"
    assert [item.name for item in bedroom.furniture] == [
        "Queen bed",
        "Desk",
        "Wardrobe",
    ]
    assert RoomDesign.model_validate(bedroom.model_dump()) == bedroom


def test_optional_design_name_and_empty_lists() -> None:
    design = RoomDesign(room=Room(**VALID_DATA[Room]))
    assert design.name is None
    assert design.furniture == []
    assert design.room.doors == []
    assert design.room.windows == []
    assert RoomDesign.model_validate_json(design.model_dump_json()) == design


@pytest.mark.parametrize(("model", "field"), DIMENSION_FIELDS)
@pytest.mark.parametrize("value", [0, -0.1, float("nan"), float("inf"), -float("inf")])
def test_invalid_dimensions(model: type[BaseModel], field: str, value: float) -> None:
    with pytest.raises(ValidationError, match=field):
        model.model_validate({**VALID_DATA[model], field: value})


@pytest.mark.parametrize(("model", "field"), POSITION_FIELDS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_positions(model: type[BaseModel], field: str, value: float) -> None:
    with pytest.raises(ValidationError, match=field):
        model.model_validate({**VALID_DATA[model], field: value})


@pytest.mark.parametrize(
    ("model", "field"),
    [(Door, "offset_m"), (Window, "offset_m"), (Window, "sill_height_m")],
)
def test_negative_opening_positions(model: type[BaseModel], field: str) -> None:
    with pytest.raises(ValidationError, match=field):
        model.model_validate({**VALID_DATA[model], field: -0.1})


@pytest.mark.parametrize("model", [Door, Window])
@pytest.mark.parametrize("wall", ["northeast", "North", "", 1])
def test_invalid_walls(model: type[BaseModel], wall: object) -> None:
    with pytest.raises(ValidationError, match="wall"):
        model.model_validate({**VALID_DATA[model], "wall": wall})


@pytest.mark.parametrize(
    ("model", "collection"), [(Door, "doors"), (Window, "windows")]
)
@pytest.mark.parametrize(
    ("wall", "length"), [("north", 5.0), ("south", 5.0), ("east", 4.0), ("west", 4.0)]
)
def test_opening_wall_endpoints(
    model: type[BaseModel], collection: str, wall: str, length: float
) -> None:
    opening = {**VALID_DATA[model], "wall": wall, "offset_m": length - 1, "width_m": 1}
    room = Room.model_validate({**VALID_DATA[Room], collection: [opening]})
    assert getattr(room, collection)[0].offset_m == length - 1

    with pytest.raises(ValidationError, match="extends beyond"):
        Room.model_validate(
            {**VALID_DATA[Room], collection: [{**opening, "offset_m": length - 0.9}]}
        )


@pytest.mark.parametrize(
    ("model", "collection"), [(Door, "doors"), (Window, "windows")]
)
def test_opening_starting_beyond_wall(model: type[BaseModel], collection: str) -> None:
    opening = {**VALID_DATA[model], "offset_m": 5.1}
    with pytest.raises(ValidationError, match="extends beyond"):
        Room.model_validate({**VALID_DATA[Room], collection: [opening]})


@pytest.mark.parametrize(
    ("model", "collection"), [(Door, "doors"), (Window, "windows")]
)
@pytest.mark.parametrize("wall", ["north", "south", "east", "west"])
def test_decimal_wall_endpoint_contact(
    model: type[BaseModel], collection: str, wall: str
) -> None:
    opening = {
        **VALID_DATA[model],
        "wall": wall,
        "offset_m": 4.2 if wall in ("north", "south") else 3.2,
        "width_m": 0.9,
    }
    room = {**VALID_DATA[Room], "width_m": 5.1, "depth_m": 4.1}
    Room.model_validate({**room, collection: [opening]})
    with pytest.raises(ValidationError, match="extends beyond"):
        Room.model_validate({**room, collection: [{**opening, "width_m": 0.900000001}]})


def test_decimal_window_ceiling_contact() -> None:
    window = {**VALID_DATA[Window], "sill_height_m": 1.1, "height_m": 1.8}
    room = {**VALID_DATA[Room], "ceiling_height_m": 2.9}
    Room.model_validate({**room, "windows": [window]})
    with pytest.raises(ValidationError, match="exceeds the room ceiling"):
        Room.model_validate({**room, "windows": [{**window, "height_m": 1.800000001}]})


def test_door_ceiling_limit() -> None:
    door = {**VALID_DATA[Door], "height_m": 2.7, "offset_m": 0}
    room = Room.model_validate({**VALID_DATA[Room], "doors": [door]})
    assert room.doors[0].height_m == room.ceiling_height_m
    with pytest.raises(ValidationError, match="Door .* exceeds the room ceiling"):
        Room.model_validate({**VALID_DATA[Room], "doors": [{**door, "height_m": 2.8}]})


def test_window_ceiling_limit() -> None:
    window = {**VALID_DATA[Window], "sill_height_m": 1.2, "height_m": 1.5}
    room = Room.model_validate({**VALID_DATA[Room], "windows": [window]})
    assert room.windows[0].sill_height_m + room.windows[0].height_m == 2.7
    with pytest.raises(ValidationError, match="Window .* exceeds the room ceiling"):
        Room.model_validate(
            {**VALID_DATA[Room], "windows": [{**window, "sill_height_m": 1.3}]}
        )


def test_floor_level_window_is_valid() -> None:
    window = Window.model_validate({**VALID_DATA[Window], "sill_height_m": 0})
    assert window.sill_height_m == 0


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_rotation_is_stored_without_transforming_coordinates(rotation: int) -> None:
    furniture = Furniture.model_validate(
        {**VALID_DATA[Furniture], "rotation_deg": rotation}
    )
    assert (furniture.x_m, furniture.y_m) == (0.4, 1.4)
    assert (furniture.width_m, furniture.depth_m) == (1.6, 2.0)
    assert furniture.rotation_deg == rotation


@pytest.mark.parametrize(
    "rotation", [-90, 45, 360, "90", 90.0, False, True, float("nan"), float("inf")]
)
def test_invalid_rotations(rotation: object) -> None:
    with pytest.raises(ValidationError, match="rotation_deg"):
        Furniture.model_validate({**VALID_DATA[Furniture], "rotation_deg": rotation})


@pytest.mark.parametrize(
    ("source_id", "target_id"),
    [
        ("queen-bed", "desk"),
        ("bedroom", "south-door"),
        ("bedroom", "north-window"),
        ("bedroom", "queen-bed"),
        ("south-door", "north-window"),
        ("south-door", "queen-bed"),
        ("north-window", "queen-bed"),
    ],
)
def test_duplicate_identifiers_across_design(
    bedroom: RoomDesign, source_id: str, target_id: str
) -> None:
    data = bedroom.model_dump()
    objects = [
        data["room"],
        *data["room"]["doors"],
        *data["room"]["windows"],
        *data["furniture"],
    ]
    next(item for item in objects if item["id"] == target_id)["id"] = source_id
    with pytest.raises(ValidationError, match="Duplicate object identifier"):
        RoomDesign.model_validate(data)


@pytest.mark.parametrize("collection", ["doors", "windows", "furniture"])
def test_duplicate_identifiers_within_collections(
    bedroom: RoomDesign, collection: str
) -> None:
    data = bedroom.model_dump()
    items = data["furniture"] if collection == "furniture" else data["room"][collection]
    items.append(dict(items[0]))
    with pytest.raises(ValidationError, match="Duplicate object identifier"):
        RoomDesign.model_validate(data)


@pytest.mark.parametrize("model", [Room, Door, Window, Furniture])
@pytest.mark.parametrize("identifier", ["", "   "])
def test_blank_identifiers(model: type[BaseModel], identifier: str) -> None:
    with pytest.raises(ValidationError, match="id"):
        model.model_validate({**VALID_DATA[model], "id": identifier})


@pytest.mark.parametrize("model", [Room, Door, Window, Furniture])
def test_unknown_fields_are_rejected(model: type[BaseModel]) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate({**VALID_DATA[model], "unknown": "value"})


@pytest.mark.parametrize(("model", "field"), DIMENSION_FIELDS + POSITION_FIELDS)
@pytest.mark.parametrize("value", ["1.0", True])
def test_numeric_fields_do_not_coerce_strings_or_booleans(
    model: type[BaseModel], field: str, value: object
) -> None:
    with pytest.raises(ValidationError, match=field):
        model.model_validate({**VALID_DATA[model], field: value})


def test_json_round_trip_preserves_complete_design(bedroom: RoomDesign) -> None:
    payload = bedroom.model_dump_json()
    restored = RoomDesign.model_validate_json(payload)
    assert restored == bedroom
    assert restored.model_dump() == bedroom.model_dump()
    assert json.loads(payload) == bedroom.model_dump(mode="json")
    json.dumps(restored.model_dump(), allow_nan=False)


def test_spatially_invalid_furniture_is_still_representable(
    bedroom: RoomDesign,
) -> None:
    data = bedroom.model_dump()
    bed, desk, wardrobe = data["furniture"]
    desk.update(x_m=bed["x_m"], y_m=bed["y_m"])
    wardrobe.update(x_m=-2.0, y_m=20.0, width_m=10.0, height_m=4.0)
    design = RoomDesign.model_validate(data)
    assert design.furniture[1].x_m == design.furniture[0].x_m
    assert design.furniture[1].y_m == design.furniture[0].y_m
    assert design.furniture[2].x_m == -2
    assert design.furniture[2].width_m > design.room.width_m


def test_explicit_revalidation_catches_nested_mutations(bedroom: RoomDesign) -> None:
    bedroom.furniture[1].id = bedroom.furniture[0].id
    with pytest.raises(ValidationError, match="Duplicate object identifier"):
        RoomDesign.model_validate(bedroom)

    bedroom.furniture[1].id = "desk"
    bedroom.room.doors[0].offset_m = 5.0
    with pytest.raises(ValidationError, match="extends beyond"):
        RoomDesign.model_validate(bedroom)
