"""Pack furniture binding and the per-room style payload."""

import json
from types import SimpleNamespace

from archimind.examples import create_sample_bedroom
from archimind.models import Furniture, RoomDesign
from archimind.style_packs import load_pack
from archimind.style_packs.binding import bind_furniture
from archimind.style_packs.models import FurnitureChoice
from archimind.style_packs.scene import style_payload
from archimind.town import agents
from archimind.town.design import Brief, generate, interpret_offline


def _design(*items):
    room = create_sample_bedroom().room
    return RoomDesign(room=room, furniture=list(items))


def _item(fid, category, w, d, h):
    return Furniture(
        id=fid,
        name=fid,
        category=category,
        x_m=0.5,
        y_m=0.5,
        width_m=w,
        depth_m=d,
        height_m=h,
    )


def _pack_with(category, *choices):
    pack = load_pack("scandinavian")
    furniture = dict(pack.furniture)
    furniture[category] = tuple(
        FurnitureChoice(asset_id=a, width_m=w, depth_m=d, height_m=h)
        for a, w, d, h in choices
    )
    return pack.model_copy(update={"furniture": furniture})


def test_binding_picks_first_choice_that_fits():
    pack = _pack_with(
        "sofa",
        ("polyhaven:too_wide_sofa", 2.4, 0.9, 0.8),
        ("polyhaven:fitting_sofa", 1.9, 0.85, 0.8),
        ("polyhaven:also_fits", 1.5, 0.8, 0.7),
    )
    (binding,) = bind_furniture(_design(_item("sofa", "sofa", 2.0, 0.85, 0.86)), pack)
    assert binding.model_dump() == {
        "furniture_id": "sofa",
        "asset_id": "polyhaven:fitting_sofa",
        "reason": "pack",
    }


def test_pack_model_must_fill_most_of_its_reservation():
    # A nightstand fits inside a bookcase reservation but would misstate the plan.
    pack = _pack_with(
        "storage",
        ("polyhaven:nightstand", 0.57, 0.42, 0.7),
        ("polyhaven:shelves", 0.9, 0.45, 1.7),
    )
    bookcase = _item("bookcase", "storage", 1.0, 0.5, 1.8)
    (binding,) = bind_furniture(_design(bookcase), pack)
    assert binding.asset_id == "polyhaven:shelves"
    only_small = _pack_with("storage", ("polyhaven:nightstand", 0.57, 0.42, 0.7))
    (binding,) = bind_furniture(_design(bookcase), only_small)
    assert binding.reason == "procedural_fallback"


def test_designer_choice_is_reported_as_designer():
    (binding,) = bind_furniture(
        _design(_item("desk-chair", "chair", 0.48, 0.52, 0.83)),
        load_pack("scandinavian"),
    )
    assert (
        binding.asset_id == "designer:oak-sage-writing-chair@1.1.0"
        and binding.reason == "designer"
    )


def test_oversized_choice_falls_back_to_procedural():
    pack = _pack_with("bed", ("polyhaven:king_bed", 1.9, 2.1, 0.6))
    (binding,) = bind_furniture(_design(_item("bed", "bed", 1.6, 2.0, 0.6)), pack)
    assert (binding.asset_id, binding.reason) == (None, "procedural_fallback")
    # A category the pack has no choices for also stays procedural.
    (binding,) = bind_furniture(_design(_item("lamp", "plant", 0.3, 0.3, 1.0)), pack)
    assert (binding.asset_id, binding.reason) == (None, "procedural_fallback")


def test_kitchen_and_bath_are_procedural():
    pack = _pack_with("counter", ("polyhaven:counter", 1.0, 0.5, 0.8))
    items = [
        _item("counter", "counter", 2.0, 0.64, 0.92),
        _item("tub", "bath", 1.5, 0.72, 0.55),
        _item("vanity", "vanity", 0.85, 0.5, 0.85),
    ]
    assert {
        (b.furniture_id, b.asset_id, b.reason)
        for b in bind_furniture(_design(*items), pack)
    } == {
        ("counter", None, "procedural_fallback"),
        ("tub", None, "procedural_fallback"),
        ("vanity", None, "procedural_fallback"),
    }


def test_payload_is_deterministic_for_seed():
    design = _design(
        _item("sofa", "sofa", 2.0, 0.85, 0.86),
        _item("desk-chair", "chair", 0.48, 0.52, 0.83),
    )
    pack = load_pack("japandi")
    a, b = style_payload(design, pack, 7), style_payload(design, pack, 7)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert list(a) == ["style_pack", "bindings", "dressing", "skipped"]
    assert a["style_pack"] == {"id": "japandi", "version": pack.version}
    assert [x["furniture_id"] for x in a["bindings"]] == ["desk-chair", "sofa"]


def test_town_rooms_carry_style_payload_and_locked_room_is_redressed():
    home = generate(Brief(style="scandinavian"), None)[0]
    for part in home["rooms"]:
        assert part["style"]["style_pack"] == home["style_pack"]
        ids = {f["id"] for f in part["design"]["furniture"]}
        assert {b["furniture_id"] for b in part["style"]["bindings"]} == ids
    brief = interpret_offline(Brief(locks=["bedroom"]), "make it japandi")
    req = SimpleNamespace(brief=brief, message="make it japandi", live=False, base=1)
    (styled,) = agents.coordinate(
        req, home, lambda r, p: interpret_offline(r.brief, r.message), lambda *e: None
    )
    for before, after in zip(home["rooms"], styled["rooms"]):
        assert after["design"] == before["design"]
        assert after["style"]["style_pack"]["id"] == "japandi"
    # The home digest covers each room's style payload.
    assert styled["id"] != home["id"]


def test_pack_furniture_choices_are_released_models_with_measured_sizes():
    from archimind.style_packs import all_packs, load_releases
    from archimind.style_packs.release import verify_release

    releases = load_releases()
    measured = 0
    for pack in all_packs():
        for choices in pack.furniture.values():
            for choice in choices:
                if choice.asset_id.startswith("designer:"):
                    continue
                release = releases[choice.asset_id]
                assert release.kind == "model"
                (x0, y0, z0), (x1, y1, z1) = verify_release(release)[choice.asset_id][
                    "bounds_xyz"
                ]
                # glTF native frame: x = width, z = depth, y = height.
                assert abs(choice.width_m - (x1 - x0)) < 0.01, choice.asset_id
                assert abs(choice.depth_m - (z1 - z0)) < 0.01, choice.asset_id
                assert abs(choice.height_m - (y1 - y0)) < 0.01, choice.asset_id
                measured += 1
    assert measured >= 20
