"""Explicit catalog generation, frozen source context and compatible render choices."""

import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.assets.specifications import BELAYA_ID, BOOKCASE_ID, CHARLES_ID
from archimind.geometry import LayoutGenerationResult
from archimind.render import product_scene
from archimind.ui import furniture_assets as controls
from archimind.ui import interior_styling as styling
from archimind.ui import layout_generation as ui
from archimind.ui import realistic_view as view

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("External work forbidden")

    for name in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, name, forbidden)
    for name in ("getaddrinfo", "create_connection", "gethostbyname"):
        monkeypatch.setattr(socket, name, forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    import openai

    for name in ("OpenAI", "AsyncOpenAI", "Client", "AsyncClient"):
        monkeypatch.setattr(openai, name, forbidden)


@pytest.fixture
def spies(monkeypatch):
    spies = SimpleNamespace(
        generator=Mock(wraps=ui.generate_layout_candidates),
        validator=Mock(wraps=ui.validate_accessibility),
        styling=Mock(wraps=ui.render_interior_styling),
        plan=Mock(wraps=ui.render_floorplan),
        plot=Mock(wraps=ui.render_design_3d),
        three=Mock(wraps=view.render_selected_realistic_scene),
        component=Mock(),
    )
    for name, spy in [
        ("generate_layout_candidates", spies.generator),
        ("validate_accessibility", spies.validator),
        ("render_interior_styling", spies.styling),
        ("render_floorplan", spies.plan),
        ("render_design_3d", spies.plot),
    ]:
        monkeypatch.setattr(ui, name, spy)
    monkeypatch.setattr(view, "render_selected_realistic_scene", spies.three)
    monkeypatch.setattr(product_scene, "_component", lambda: spies.component)
    return spies


def app():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()


def catalog(a, products=(CHARLES_ID, BOOKCASE_ID), manual=True):
    a.selectbox(key=controls.MODE_KEY).set_value(controls.CATALOG).run()
    for fid in ("queen-bed", "desk", "wardrobe"):
        a.checkbox(key=f"keep_manual:{fid}").set_value(manual).run()
    for asset in products:
        a.checkbox(key=f"catalog_product:{asset}").check().run()
    return a


def prepare(a):
    return a.button(key="prepare_catalog").click().run()


def generate(a):
    return a.button(key="generate_layouts").click().run()


@pytest.mark.parametrize("with_bed", [False, True])
def test_belaya_explicit_generation_and_exact_ab_handoff(spies, with_bed):
    a = catalog(app(), products=(BELAYA_ID,), manual=False)
    if with_bed:
        a.checkbox(key="keep_manual:queen-bed").check().run()
    assert a.button(key="generate_layouts").disabled
    prepare(a)
    p = a.session_state[controls.PREPARED_KEY]
    # AppTest.run() settles the full rerun. In the browser the review may
    # arrive before the downstream Generate button's enabled-state update.
    assert not a.button(key="generate_layouts").disabled
    assert any("Review next specification" in item.value for item in a.markdown)
    reviews = [
        item.value for item in a.dataframe if "Dimension basis" in item.value.columns
    ]
    assert len(reviews) == 1
    review = reviews[0]
    belaya_row = review[review["Identity"] == "B074L4976T"].iloc[0]
    assert belaya_row["Dimension basis"] == "Policy B planning reservation"
    assert p.product_ids == (BELAYA_ID,)
    a.run()
    assert a.session_state[controls.PREPARED_KEY] is p
    assert not a.button(key="generate_layouts").disabled
    assert not spies.generator.called and not spies.validator.called
    assert p.assignments[0].dimensions.wdh == (
        1.6,
        0.8018731772899628,
        0.7516312003135682,
    )
    generate(a)
    assert not a.exception
    assert spies.generator.call_count == 1
    result = a.session_state[ui.RESULT_KEY]
    assert result.status == "complete" and len(result.candidates) == 2
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    assert snapshot.bindings == p.planning_bindings
    assert snapshot.source_specification_json == p.source_specification_json
    assert type(snapshot).model_validate_json(snapshot.model_dump_json()) == snapshot
    before = result.model_dump_json()
    counts = spies.generator.call_count, spies.validator.call_count
    for index, label in [(1, "Layout B"), (0, "Layout A")]:
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
        assert (
            spies.plan.call_args.args[0]
            is spies.plot.call_args.args[0]
            is result.candidates[index].design
        )
        assert result.candidates[index].validation.status == "passed"
        a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
        assert spies.three.call_args.args[0] is result.candidates[index].design
        data = spies.component.call_args.kwargs["data"]
        assert data["design"] == result.candidates[index].design.model_dump(mode="json")
        assert sum(b["asset_id"] == BELAYA_ID for b in data["asset_bindings"]) == 1
        assert all(b["asset_id"] in (BELAYA_ID, None) for b in data["asset_bindings"])
        assert any("ABO B074L4976T, Oak" in c.value for c in a.caption)
        assert not any(
            "ABO B074L4976T" in c.value and "Amazon.com" in c.value for c in a.caption
        )
        assert not any("Charles, Sod" in c.value for c in a.caption)
        a.radio(key=view.VIEW_KEY).set_value(view.PLOTLY_VIEW).run()
    a.run()
    a.run()
    assert (spies.generator.call_count, spies.validator.call_count) == counts
    assert a.session_state[ui.RESULT_KEY].model_dump_json() == before
    a.checkbox(key=f"catalog_product:{BELAYA_ID}").uncheck().run()
    assert a.button(key="generate_layouts").disabled
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert a.session_state[ui.RESULT_KEY].model_dump_json() == before


def test_generated_belaya_charles_mixed_scene_is_explicitly_unqualified(spies):
    a = generate(
        prepare(catalog(app(), products=(BELAYA_ID, CHARLES_ID), manual=False))
    )
    result = a.session_state[ui.RESULT_KEY]
    before = result.model_dump_json()
    assert result.status == "complete"
    assert len(a.session_state[view.SNAPSHOT_KEY].bindings) == 2
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert all(
        b["asset_id"] is None
        for b in spies.component.call_args.kwargs["data"]["asset_bindings"]
    )
    assert any("Mixed scene not yet qualified" in i.value for i in a.info)
    assert a.session_state[ui.RESULT_KEY].model_dump_json() == before


def test_belaya_missing_planning_blocks_pending_but_preserves_existing(
    spies, monkeypatch
):
    from archimind.assets import specifications

    a = generate(prepare(catalog(app(), products=(BELAYA_ID,), manual=False)))
    result = a.session_state[ui.RESULT_KEY]
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    original = specifications.load_planning_envelope

    def missing(asset_id):
        if asset_id == BELAYA_ID:
            raise ValueError("secret-token")
        return original(asset_id)

    monkeypatch.setattr(specifications, "load_planning_envelope", missing)
    a.run()
    assert a.checkbox(key=f"catalog_product:{BELAYA_ID}").disabled
    assert a.button(key="generate_layouts").disabled
    assert a.session_state[ui.RESULT_KEY] is result
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert not a.exception
    assert any("Published measurements cannot replace it" in c.value for c in a.caption)


def test_catalog_requires_current_explicit_review_seed_does_not_invalidate(spies):
    a = catalog(app())
    assert a.button(key="generate_layouts").disabled
    assert not spies.generator.called and not spies.validator.called
    prepare(a)
    p = a.session_state[controls.PREPARED_KEY]
    assert not a.button(key="generate_layouts").disabled
    a.number_input(key="layout_seed").set_value(123).run()
    assert a.session_state[controls.PREPARED_KEY] is p
    assert not a.button(key="generate_layouts").disabled
    a.checkbox(key=f"catalog_product:{BOOKCASE_ID}").uncheck().run()
    assert a.button(key="generate_layouts").disabled
    assert not spies.generator.called and not spies.validator.called


def test_mixed_generation_preserves_evidence_and_exact_selected_design(spies):
    a = generate(prepare(catalog(app())))
    assert not a.exception
    result = a.session_state[ui.RESULT_KEY]
    assert result.status == "complete" and len(result.candidates) == 2
    assert result.attempts_used == 198
    before = result.model_dump_json()
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    assert len(snapshot.assignments) == 2 and len(snapshot.bindings) == 1
    assert (
        spies.styling.call_args.args[0].model_dump_json()
        == snapshot.source_specification_json
    )
    counts = spies.generator.call_count, spies.validator.call_count
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert (
        sum(
            b["asset_id"] is not None
            for b in spies.component.call_args.kwargs["data"]["asset_bindings"]
        )
        == 1
    )
    for index, label in [(1, "Layout B"), (0, "Layout A")]:
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
        assert spies.plan.call_args.args[0] is result.candidates[index].design
        assert spies.three.call_args.args[0] is result.candidates[index].design
        for assignment in snapshot.assignments:
            assignment.validate_furniture(
                next(
                    f
                    for f in result.candidates[index].design.furniture
                    if f.id == assignment.furniture_id
                )
            )
    assert (spies.generator.call_count, spies.validator.call_count) == counts
    assert result.model_dump_json() == before
    assert any("Metadata-only bookcase" in c.value for c in a.caption)


def test_pending_selection_and_preparation_preserve_current_styling_and_source(spies):
    a = generate(app())
    a.button(key="show_fixture_styling").click().run()
    style = a.session_state[styling.RESULT_KEY]
    result = a.session_state[ui.RESULT_KEY]
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    calls = spies.generator.call_count, spies.validator.call_count
    prepare(catalog(a, manual=False))
    assert a.session_state[ui.RESULT_KEY] is result
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert a.session_state[styling.RESULT_KEY] == style
    assert (
        spies.styling.call_args.args[0].model_dump_json()
        == snapshot.source_specification_json
    )
    assert (spies.generator.call_count, spies.validator.call_count) == calls


def test_render_override_is_generation_bound_and_cannot_promote_bookcase(spies):
    a = generate(prepare(catalog(app(), manual=False)))
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    result = a.session_state[ui.RESULT_KEY]
    before = result.model_dump_json()
    calls = spies.generator.call_count, spies.validator.call_count
    key = f"product_representation:1:catalog:{CHARLES_ID}:1"
    assert a.selectbox(key=key).value == "Approved product mesh"
    assert (
        len([s for s in a.selectbox if s.key.startswith("product_representation:")])
        == 1
    )
    a.selectbox(key=key).set_value("Procedural placeholder").run()
    assert all(
        b["asset_id"] is None
        for b in spies.component.call_args.kwargs["data"]["asset_bindings"]
    )
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    assert a.selectbox(key=key).value == "Procedural placeholder"
    a.radio(key=view.VIEW_KEY).set_value(view.PLOTLY_VIEW).run()
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert a.selectbox(key=key).value == "Procedural placeholder"
    assert result.model_dump_json() == before
    assert (spies.generator.call_count, spies.validator.call_count) == calls
    generate(a)
    assert (
        a.selectbox(key=f"product_representation:2:catalog:{CHARLES_ID}:1").value
        == "Approved product mesh"
    )
    assert a.session_state[view.REVISION_KEY] == 2


def test_exception_preserves_full_context_but_normal_empty_replaces_it(spies):
    a = generate(prepare(catalog(app(), manual=False)))
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    prior, snapshot = a.session_state[ui.RESULT_KEY], a.session_state[view.SNAPSHOT_KEY]
    spies.generator.side_effect = RuntimeError("secret-token")
    generate(a)
    assert (
        a.session_state[ui.RESULT_KEY] is prior
        and a.session_state[view.SNAPSHOT_KEY] is snapshot
    )
    assert a.radio(key=ui.SELECTION_KEY).value == "Layout B"
    assert "secret-token" not in str([i.value for i in a.error])
    spies.generator.side_effect = None
    raw = prior.model_dump(mode="json")
    raw.update(
        status="search_exhausted", candidates=[], message="Bounded search exhausted"
    )
    spies.generator.return_value = LayoutGenerationResult.model_validate(raw)
    generate(a)
    assert not a.session_state[ui.RESULT_KEY].candidates
    assert a.session_state[view.REVISION_KEY] == snapshot.revision + 1
    assert not a.exception


def test_reviewed_empty_specification_reports_honest_partial_outcome(spies):
    a = generate(prepare(catalog(app(), products=(), manual=False)))
    result = a.session_state[ui.RESULT_KEY]
    assert result.status == "search_exhausted" and len(result.candidates) == 1
    assert not result.candidates[0].design.furniture
    assert not a.exception


def test_independent_sessions_and_generic_chairs_cannot_gain_mesh(spies):
    a = generate(prepare(catalog(app(), products=(BOOKCASE_ID,), manual=False)))
    b = generate(app())
    assert len(a.session_state[view.SNAPSHOT_KEY].assignments) == 1
    assert not b.session_state[view.SNAPSHOT_KEY].assignments
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert all(
        x["asset_id"] is None
        for x in spies.component.call_args.kwargs["data"]["asset_bindings"]
    )
    assert not any(s.key.startswith("product_representation:") for s in a.selectbox)
    assert b.radio(key=view.VIEW_KEY).value == view.PLOTLY_VIEW


def test_catalog_styling_uses_committed_input_after_mode_and_seed_changes(spies):
    a = generate(prepare(catalog(app(), manual=False)))
    a.button(key="show_fixture_styling").click().run()
    original = a.session_state[styling.RESULT_KEY]
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    assert original[1].approved_design is not None
    a.selectbox(key=controls.MODE_KEY).set_value(controls.PROCEDURAL).run()
    a.number_input(key="layout_seed").set_value(101).run()
    assert a.session_state[styling.RESULT_KEY] == original
    assert (
        spies.styling.call_args.args[0].model_dump_json()
        == snapshot.source_specification_json
    )
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    key = f"product_representation:1:catalog:{CHARLES_ID}:1"
    a.selectbox(key=key).set_value("Procedural placeholder").run()
    assert a.session_state[styling.RESULT_KEY] == original
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot


def test_evidence_loss_blocks_next_generation_without_replacing_current(
    spies, monkeypatch
):
    from archimind.assets import specifications

    a = generate(prepare(catalog(app(), manual=False)))
    result, snapshot = (
        a.session_state[ui.RESULT_KEY],
        a.session_state[view.SNAPSHOT_KEY],
    )
    original = specifications.load_catalog
    monkeypatch.setattr(
        specifications, "load_catalog", Mock(side_effect=ValueError("secret-token"))
    )
    a.run()
    assert a.button(key="generate_layouts").disabled
    assert (
        a.session_state[ui.RESULT_KEY] is result
        and a.session_state[view.SNAPSHOT_KEY] is snapshot
    )
    assert not a.exception and "secret-token" not in str([e.value for e in a.error])
    monkeypatch.setattr(specifications, "load_catalog", original)
    a.run()
    assert not a.button(key="generate_layouts").disabled


def test_new_metadata_products_review_generate_and_pending_edits(spies):
    products = (
        "abo-b074l4976t-amazon-co-uk",
        "abo-b07b4vxxjc-amazon-com",
        "abo-b07h8jn9qf-amazon-co-uk",
    )
    a = catalog(app(), products=products, manual=False)
    assert all(
        not a.checkbox(key=f"catalog_product:{key}").disabled for key in products
    )
    assert (
        len([c for c in a.checkbox if c.key and c.key.startswith("catalog_product:")])
        == 5
    )
    assert not spies.generator.called and not spies.validator.called
    assert (
        sum("Approved planning envelope: unavailable" in c.value for c in a.caption)
        == 3
    )
    prepare(a)
    prepared = a.session_state[controls.PREPARED_KEY]
    assert len(prepared.assignments) == 3 and len(prepared.planning_bindings) == 1
    assert prepared.planning_bindings[0].envelope.asset_id == BELAYA_ID
    generate(a)
    assert not a.exception
    result = a.session_state[ui.RESULT_KEY]
    before = result.model_dump_json()
    assert result.status == "complete" and len(result.candidates) == 2
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    assert len(snapshot.assignments) == 3 and len(snapshot.bindings) == 1
    assert {p.category for p in snapshot.assignments} == {"desk", "table", "wardrobe"}
    assert all(p.catalog_version == "1.1.0" for p in snapshot.assignments)
    assert not any("Metadata-only bookcase" in c.value for c in a.caption)
    calls = spies.generator.call_count, spies.validator.call_count
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert {
        b["asset_id"]
        for b in spies.component.call_args.kwargs["data"]["asset_bindings"]
    } == {None, BELAYA_ID}
    a.radio(key=ui.SELECTION_KEY).set_value("Layout B").run()
    assert spies.three.call_args.args[0] is result.candidates[1].design
    a.checkbox(key=f"catalog_product:{products[0]}").uncheck().run()
    assert a.button(key="generate_layouts").disabled
    assert a.session_state[ui.RESULT_KEY].model_dump_json() == before
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert (spies.generator.call_count, spies.validator.call_count) == calls
    assert (
        spies.styling.call_args.args[0].model_dump_json()
        == snapshot.source_specification_json
    )


def test_selected_view_parent_is_generation_scoped_and_removed_on_close(spies):
    a = app()
    generate(a)

    def owners():
        return [
            block.proto.id
            for block in a.get("flex_container")
            if "selected-realistic-owner-" in block.proto.id
        ]

    assert not owners()
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert not a.exception
    first = owners()
    assert len(first) == 1 and first[0].endswith("selected-realistic-owner-1")
    result = a.session_state[ui.RESULT_KEY]
    for label, index in [("Layout B", 1), ("Layout A", 0), ("Layout B", 1)]:
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
        assert not a.exception
        assert owners() == first
        assert spies.three.call_args.args[0] is result.candidates[index].design
    assert spies.generator.call_count == 1
    assert spies.validator.call_count == 2
    a.radio(key=view.VIEW_KEY).set_value(view.PLOTLY_VIEW).run()
    assert not owners()
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert owners() == first  # Reinserted DOM owner, not a persistent browser cache.
    generate(a)
    assert len(owners()) == 1 and owners()[0].endswith("selected-realistic-owner-2")
    assert owners() != first
    empty = a.session_state[ui.RESULT_KEY].model_dump()
    empty.update(status="search_exhausted", candidates=[], attempts_used=500)
    spies.generator.return_value = LayoutGenerationResult.model_validate(empty)
    generate(a)
    assert not a.exception
    assert not owners()


def test_belaya_same_session_regeneration_and_pending_recovery(spies):
    a = prepare(catalog(app(), products=(BELAYA_ID,), manual=False))
    prepared = a.session_state[controls.PREPARED_KEY]
    generate(a)
    first = a.session_state[ui.RESULT_KEY]
    first_json = first.model_dump_json()
    assert a.session_state[view.REVISION_KEY] == 1
    assert (spies.generator.call_count, spies.validator.call_count) == (1, 2)
    for label in ("Layout B", "Layout A"):
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert spies.three.call_args.args[0] is first.candidates[0].design
    assert (spies.generator.call_count, spies.validator.call_count) == (1, 2)
    generate(a)
    second = a.session_state[ui.RESULT_KEY]
    assert second is not first
    assert second.model_dump_json() == first_json
    assert a.session_state[view.REVISION_KEY] == 2
    assert (spies.generator.call_count, spies.validator.call_count) == (2, 4)
    assert a.session_state[controls.PREPARED_KEY] is prepared
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    assert snapshot.bindings == prepared.planning_bindings
    assert snapshot.source_specification_json == prepared.source_specification_json
    for index, label in enumerate(("Layout A", "Layout B")):
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
        assert spies.three.call_args.args[0] is second.candidates[index].design
        furniture = second.candidates[index].design.furniture[0]
        assert furniture.id == f"catalog:{BELAYA_ID}:1"
        assert furniture.rotation_deg == 0
        assert (furniture.width_m, furniture.depth_m, furniture.height_m) == (
            1.6,
            0.8018731772899628,
            0.7516312003135682,
        )
    a.checkbox(key="keep_manual:queen-bed").check().run()
    assert a.button(key="generate_layouts").disabled
    assert a.session_state[ui.RESULT_KEY] is second
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    a.checkbox(key="keep_manual:queen-bed").uncheck().run()
    prepare(a)
    assert not a.button(key="generate_layouts").disabled
    assert a.session_state[ui.RESULT_KEY] is second
    assert a.session_state[view.SNAPSHOT_KEY] is snapshot
    assert second.model_dump_json() == first.model_dump_json() == first_json
    assert a.session_state[view.REVISION_KEY] == 2
    assert (spies.generator.call_count, spies.validator.call_count) == (2, 4)
    assert not a.exception
