"""Explicit catalog generation, frozen source context and compatible render choices."""

import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from archimind.assets.specifications import BOOKCASE_ID, CHARLES_ID
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
        == 4
    )
    prepare(a)
    prepared = a.session_state[controls.PREPARED_KEY]
    assert len(prepared.assignments) == 3 and not prepared.planning_bindings
    generate(a)
    assert not a.exception
    result = a.session_state[ui.RESULT_KEY]
    before = result.model_dump_json()
    assert result.status == "complete" and len(result.candidates) == 2
    snapshot = a.session_state[view.SNAPSHOT_KEY]
    assert len(snapshot.assignments) == 3 and not snapshot.bindings
    assert {p.category for p in snapshot.assignments} == {"desk", "table", "wardrobe"}
    assert all(p.catalog_version == "1.1.0" for p in snapshot.assignments)
    assert not any("Metadata-only bookcase" in c.value for c in a.caption)
    calls = spies.generator.call_count, spies.validator.call_count
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    assert all(
        b["asset_id"] is None
        for b in spies.component.call_args.kwargs["data"]["asset_bindings"]
    )
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
