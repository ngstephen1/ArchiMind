"""Offline metadata/preparation contracts; no geometry or external execution."""

import socket
import subprocess

import pytest
from pydantic import ValidationError

from archimind.assets import specifications as api
from archimind.examples import create_sample_bedroom


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External operation forbidden")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)


def prepare(base=None, retained=(), products=(api.CHARLES_ID, api.BOOKCASE_ID)):
    return api.prepare_catalog_specification(
        base or create_sample_bedroom(),
        retained_manual_ids=retained,
        product_ids=products,
    )


def test_discovery_uses_current_release_without_rewriting_catalog():
    options = api.catalog_product_options()
    assert len(options) == 5
    assert [o.record.asset_id for o in options] == sorted(
        o.record.asset_id for o in options
    )
    chair, book = (
        next(o for o in options if o.record.asset_id == key)
        for key in (api.CHARLES_ID, api.BOOKCASE_ID)
    )
    assert chair.render_qualified and not chair.record.render_qualified
    assert chair.planning_dimensions.wdh == (
        0.996104896068573,
        1.0019413232803345,
        0.9760930538177491,
    )
    assert book.planning_dimensions is None and not book.render_qualified
    assert all(
        o.record.search.colors is None and o.record.search.materials is None
        for o in options
    )
    assert all(o.record.legal.public_browser_delivery for o in options)


def test_mixed_preparation_factories_and_provenance_are_immutable():
    base = create_sample_bedroom()
    before = base.model_dump_json()
    p = prepare(base, retained=[f.id for f in base.furniture])
    design = p.design()
    assert len(design.furniture) == 5 and len(p.planning_bindings) == 1
    assert design.room == base.room and design.furniture[:3] == base.furniture
    assert base.model_dump_json() == before
    assert design.furniture[-1].name == "Bookcase (Espresso)"
    assert (
        design.furniture[-1].width_m,
        design.furniture[-1].depth_m,
        design.furniture[-1].height_m,
    ) == (0.659892, 0.381762, 1.891792)
    for a, f in zip(p.assignments, design.furniture[3:], strict=True):
        a.validate_furniture(f)
        assert f.id == f"catalog:{a.asset_id}:1" and (f.x_m, f.y_m, f.rotation_deg) == (
            0,
            0,
            0,
        )
    p.planning_bindings[0].validate_furniture(design.furniture[3])
    with pytest.raises(ValidationError):
        p.assignments[0].dimensions.width_m = 2.0
    design.furniture.clear()
    assert len(p.design().furniture) == 5
    assert type(p).model_validate_json(p.model_dump_json()) == p


@pytest.mark.parametrize(
    "retained,products",
    [
        (("bad",), ()),
        (("desk", "desk"), ()),
        ((), ("bad",)),
        ((), (api.CHARLES_ID, api.CHARLES_ID)),
        ("desk", ()),
    ],
)
def test_bad_selection_rejected(retained, products):
    with pytest.raises(api.SpecificationError):
        prepare(retained=retained, products=products)


def test_collisions_rotation_and_empty():
    base = create_sample_bedroom()
    base.furniture[0].id = f"catalog:{api.CHARLES_ID}:1"
    with pytest.raises(api.SpecificationError):
        prepare(base)
    base = create_sample_bedroom()
    base.furniture[0].rotation_deg = 90
    with pytest.raises(api.SpecificationError):
        prepare(base)
    p = prepare(products=())
    assert not p.design().furniture and not p.assignments and not p.planning_bindings


def test_unavailable_planning_never_uses_published_charles_size(monkeypatch):
    monkeypatch.setattr(
        api,
        "load_planning_envelope",
        lambda *args: (_ for _ in ()).throw(ValueError("secret")),
    )
    assert not next(
        o for o in api.catalog_product_options() if o.record.asset_id == api.CHARLES_ID
    ).preparation_available
    with pytest.raises(api.SpecificationError, match="planning evidence"):
        prepare()
    assert len(prepare(products=(api.BOOKCASE_ID,)).design().furniture) == 1


def test_stale_selection_geometry_evidence_or_tampering_require_preparation(
    monkeypatch,
):
    base = create_sample_bedroom()
    p = prepare(base)
    args = dict(retained_manual_ids=(), product_ids=(api.CHARLES_ID, api.BOOKCASE_ID))
    assert api.specification_is_current(p, base, **args)
    assert not api.specification_is_current(
        p, base, retained_manual_ids=("desk",), product_ids=args["product_ids"]
    )
    changed = base.model_copy(deep=True)
    changed.room.width_m += 1
    assert not api.specification_is_current(p, changed, **args)
    assert not api.specification_is_current(
        p.model_copy(update={"input_fingerprint": "altered"}), base, **args
    )
    original = api.catalog_product_options
    monkeypatch.setattr(
        api,
        "catalog_product_options",
        lambda: tuple(
            o.model_copy(update={"render_release_digest": None}) for o in original()
        ),
    )
    assert not api.specification_is_current(p, base, **args)


def test_render_release_absence_does_not_invent_approval(monkeypatch):
    from archimind.assets import render_assets

    def missing():
        raise ValueError("private path and token")

    monkeypatch.setattr(render_assets, "product_release", missing)
    chair, book = (
        next(o for o in api.catalog_product_options() if o.record.asset_id == key)
        for key in (api.CHARLES_ID, api.BOOKCASE_ID)
    )
    assert chair.preparation_available and not chair.render_qualified
    assert not book.render_qualified
    p = prepare()
    assert len(p.planning_bindings) == 1


def test_preparation_never_changes_existing_validation_or_score(monkeypatch):
    import archimind.geometry as geometry

    base = create_sample_bedroom()
    generated = geometry.generate_layout_candidates(base.room, base.furniture)
    before = generated.model_dump_json()

    def forbidden(*args, **kwargs):
        raise AssertionError("Preparation attempted generation or spatial checking")

    monkeypatch.setattr(geometry, "generate_layout_candidates", forbidden)
    monkeypatch.setattr(geometry, "validate_accessibility", forbidden)
    p = prepare(
        generated.candidates[0].design, retained=("queen-bed", "desk", "wardrobe")
    )
    assert len(p.design().furniture) == 5
    assert generated.model_dump_json() == before


@pytest.mark.parametrize("mixed", [False, True])
def test_new_products_generate_without_geometry_or_existing_result_changes(mixed):
    from archimind.assets.selection import build_render_bindings
    from archimind.geometry import generate_layout_candidates, validate_accessibility
    from archimind.render.selected_realistic import build_selected_realistic_scene

    base = create_sample_bedroom()
    existing = generate_layout_candidates(base.room, base.furniture, seed=42)
    before = existing.model_dump_json()
    ids = [
        "abo-b074l4976t-amazon-co-uk",
        "abo-b07h8jn9qf-amazon-co-uk",
        "abo-b07b4vxxjc-amazon-com",
    ]
    if mixed:
        ids.append(api.CHARLES_ID)
    p = prepare(base, retained=("queen-bed",) if mixed else (), products=ids)
    d = p.design()
    first = generate_layout_candidates(d.room, d.furniture, seed=42)
    second = generate_layout_candidates(d.room, d.furniture, seed=42)
    assert first == second and first.attempts_used <= 500
    assert first.status == "complete" and len(first.candidates) == 2
    for candidate in first.candidates:
        assert validate_accessibility(candidate.design).status == "passed"
        for assignment in p.assignments:
            assignment.validate_furniture(
                next(
                    f
                    for f in candidate.design.furniture
                    if f.id == assignment.furniture_id
                )
            )
        bindings = {b.furniture_id: b for b in p.planning_bindings}
        resolution = build_render_bindings(candidate.design, planning_bindings=bindings)
        assert sum(b.asset_id is not None for b in resolution.bindings) == int(mixed)
        scene = build_selected_realistic_scene(
            candidate.design, planning_bindings=bindings
        )
        assert (
            scene.scene.design.model_dump_json() == candidate.design.model_dump_json()
        )
    assert existing.model_dump_json() == before
