"""Gallery and grouped service-core comparisons using saved Town geometry."""

import copy

import pytest

from archimind.town.design import Brief, RoomGoal, generate, validate_home


@pytest.fixture(scope="module")
def zoning_pair():
    return generate(
        Brief(
            width=15,
            depth=16,
            seed=42,
            formal_salon=True,
            compare_zoning=True,
            compare_tradeoffs=True,
            dining_seats=4,
            service_layout=True,
        )
    )


def rooms(home):
    return {part["design"]["room"]["id"]: part for part in home["rooms"]}


def test_zoning_comparison_selects_the_scheme_that_best_fits_the_preference():
    homes = generate(
        Brief(
            width=15,
            depth=16,
            formal_salon=True,
            compare_zoning=True,
            service_layout=True,
            room_goals=[
                RoomGoal(room="kitchen-dining", relation="near", target="salon")
            ],
        )
    )
    assert [home["zoning"] for home in homes] == ["service-core", "gallery"]
    assert (
        homes[0]["evidence"]["room_preferences"][0]["center_distance_m"]
        < homes[1]["evidence"]["room_preferences"][0]["center_distance_m"]
    )


def test_zoning_comparison_changes_room_connections_and_keeps_the_common_program(
    zoning_pair,
):
    gallery, core = zoning_pair
    assert [home["zoning"] for home in zoning_pair] == ["gallery", "service-core"]
    assert (
        (gallery["width"], gallery["depth"])
        == (core["width"], core["depth"])
        == (15, 16)
    )
    records = [validate_home(home, measure=True) for home in zoning_pair]
    for record in records:
        assert record["room_areas_m2"].keys() == rooms(gallery).keys()
        assert record["wardrobes"] == [
            {
                "room": "bedroom",
                "id": "bedroom-wardrobe",
                "width_m": 1.35,
                "depth_m": 0.6,
            }
        ]
        assert record["dining_places"] == {"kitchen-dining": 4, "salon": 4}
    assert "direct_service" not in records[0]
    assert records[1]["direct_service"]["rooms"] == ["kitchen-dining", "salon"]
    assert records[1]["direct_service"]["crossing_m"] == 1.3
    assert records[0]["routes"] != records[1]["routes"]

    kitchen = rooms(core)["kitchen-dining"]["design"]["room"]
    salon = rooms(core)["salon"]["design"]["room"]
    assert kitchen["doors"][1]["wall"] == "north"
    assert salon["doors"][1]["wall"] == "south"


def test_unpaired_portal_and_missing_wardrobe_fail_validation(zoning_pair):
    damaged = copy.deepcopy(zoning_pair[1])
    portal = rooms(damaged)["salon"]["design"]["room"]["doors"][1]
    portal["offset_m"] += 0.01
    with pytest.raises(ValueError, match="paired openings"):
        validate_home(damaged)

    damaged = copy.deepcopy(zoning_pair[0])
    bedroom = rooms(damaged)["bedroom"]["design"]
    bedroom["furniture"] = [
        f for f in bedroom["furniture"] if f["id"] != "bedroom-wardrobe"
    ]
    with pytest.raises(ValueError, match="wardrobe reservation"):
        validate_home(damaged)


def test_infeasible_comparison_does_not_return_two_gallery_homes():
    with pytest.raises(ValueError, match="Search exhausted|both a validated gallery"):
        generate(
            Brief(
                width=9,
                depth=9,
                formal_salon=True,
                compare_zoning=True,
                service_layout=True,
            )
        )


def test_locked_salon_edit_preserves_the_opening_and_revalidates_the_pair(zoning_pair):
    old = zoning_pair[1]
    revised = generate(
        Brief(width=15, depth=16, formal_salon=True, dining_seats=4, locks=["salon"]),
        old,
    )[0]
    assert revised["zoning"] == "service-core"
    assert rooms(revised)["salon"] == rooms(old)["salon"]
    assert (
        validate_home(revised, measure=True)["direct_service"]
        == old["evidence"]["comparison"]["direct_service"]
    )
