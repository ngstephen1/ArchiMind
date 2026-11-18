"""P4: default-off dataset references in Chat bedroom (synthetic packs, AppTest).

The interpretation step is the only substituted boundary, as in
test_bedroom_chat_ui. Reference controls must make no model, generator or
network calls and must never disturb preparation or the displayed A/B results.
"""

import math
import socket
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from catalog_chat_helpers import TEXT, extraction, measure, turns
from streamlit.testing.v1 import AppTest

from archimind.agents.catalog_conversation import reconcile_catalog_extraction
from archimind.assets.specifications import BELAYA_ID
from archimind.datasets.contracts import (
    CheckResult,
    Footprint,
    RoomExtent,
    SceneObject,
    SceneReference,
)
from archimind.datasets.fixtures import (
    FIXTURE_VERSION,
    SYNTHETIC_REVISION,
    SYNTHETIC_TIME,
    source_manifest,
)
from archimind.datasets.pack import build_pack
from archimind.ui import bedroom_chat as chat
from archimind.ui import dataset_references as refs
from archimind.ui import furniture_assets as controls
from archimind.ui import layout_generation as ui

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("External operation forbidden")

    for n in ("connect", "connect_ex", "bind", "sendto"):
        monkeypatch.setattr(socket.socket, n, fail)
    for n in ("create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, n, fail)
    monkeypatch.setattr(subprocess, "Popen", fail)
    import openai

    monkeypatch.setattr(openai, "OpenAI", fail)
    monkeypatch.setenv("ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for name in (refs.FLAG, refs.ROOT_ENV, refs.AUDIENCE_ENV):
        monkeypatch.delenv(name, raising=False)
    refs._load.clear()


@pytest.fixture
def spies(monkeypatch):
    response = reconcile_catalog_extraction(extraction(), turns())
    agent = Mock(return_value=response)
    gen = Mock(wraps=ui.generate_layout_candidates)
    monkeypatch.setattr(chat, "interpret_catalog_conversation", agent)
    monkeypatch.setattr(ui, "generate_layout_candidates", gen)
    return agent, gen


def obj(oid, category, raw, x, y, w, d, turns=0):
    half = math.sqrt(0.5)
    rotation = (0.0, half, 0.0, half) if turns else (0.0, 0.0, 0.0, 1.0)
    return SceneObject(
        source_object_id=oid,
        jid=f"jid-{oid}",
        raw_category=raw,
        category=category,
        size_raw=(w, 0.5, d),
        position_raw=(x, 0.0, y),
        rotation_raw_xyzw=rotation,
        footprint=Footprint(
            x_m=x, y_m=y, width_m=w, depth_m=d, height_m=0.5, yaw_quarter_turns=turns
        ),
    )


def scene(house, tier, dims, objects):
    return SceneReference(
        reference_id=f"ssr:{house}:Bedroom-1",
        source="ssr_3dfront",
        source_revision=SYNTHETIC_REVISION,
        source_sha256=source_manifest("ssr_3dfront").files[0].sha256,
        split="train",
        source_scene_id=house,
        source_room_id="Bedroom-1",
        tier=tier,
        room=RoomExtent(width_m=dims[0], depth_m=dims[1], height_m=dims[2]),
        openings="unknown",
        objects=tuple(objects),
        checks=(CheckResult(name="door_clearance", status="NOT_VERIFIABLE"),),
        transform_version=FIXTURE_VERSION,
        category_map_version=FIXTURE_VERSION,
    )


def make_pack(root, audience="local"):
    build_pack(
        root,
        pack_id="ui-test",
        audience=audience,
        sources=[source_manifest("ssr_3dfront")],
        scenes=[
            scene(
                "canon",
                "canonical",
                (5.0, 4.0, 2.7),
                [
                    obj("o0", "bed", "King-size Bed", 1.0, 1.0, 1.6, 2.0),
                    obj("o1", "table", "Desk", 3.5, 3.0, 1.2, 0.6),
                ],
            ),
            scene(
                "turned",
                "reference_only",
                (4.0, 5.0, 2.7),
                [
                    obj("o0", "bed", "King-size Bed", 1.0, 1.0, 2.0, 1.6, turns=1),
                ],
            ),
        ],  # fmt: skip
        exclusions=[],
        assets=[],
        glb_files={},
        transform_version=FIXTURE_VERSION,
        category_map_version=FIXTURE_VERSION,
        builder="test",
        created_utc=SYNTHETIC_TIME,
    )
    return root


def app():
    a = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    return a.selectbox(key=controls.MODE_KEY).set_value(controls.CHAT).run()


def submit(a, text=TEXT):
    return a.chat_input(key="chat_bedroom_message").set_value(text).run()


def texts(a):
    return " ".join(
        str(e.value) for e in (*a.markdown, *a.caption, *a.info, *a.warning)
    )


def enable(monkeypatch, root=None, audience=None):
    monkeypatch.setenv(refs.FLAG, "1")
    if root is not None:
        monkeypatch.setenv(refs.ROOT_ENV, str(root))
    if audience is not None:
        monkeypatch.setenv(refs.AUDIENCE_ENV, audience)


def test_default_off_shows_nothing_and_loads_nothing(spies, monkeypatch):
    loader = Mock()
    monkeypatch.setattr("archimind.datasets.search.load_reference_pack", loader)
    a = app()
    submit(a)
    assert not a.exception
    assert "References for next specification" not in texts(a)
    assert not [b for b in a.button if b.key == "dataset_ref_find"]
    loader.assert_not_called()


def test_unconfigured_and_blocked_packs_leave_chat_usable(spies, monkeypatch, tmp_path):
    agent, gen = spies
    enable(monkeypatch)
    a = app()
    submit(a)
    a.button(key="dataset_ref_find").click().run()
    assert "No reference pack is configured" in texts(a)
    assert not a.exception and a.button(key="prepare_chat") is not None

    root = make_pack(tmp_path / "pack")
    enable(monkeypatch, root)  # default public audience; the pack is local-only
    a.button(key="dataset_ref_find").click().run()
    assert "approved for local research only" in texts(a)

    enable(monkeypatch, root, "local")
    (root / "scenes.jsonl").write_bytes(b"{}\n")  # corrupt
    a.button(key="dataset_ref_find").click().run()
    assert "The reference pack is unavailable" in texts(a)
    assert (agent.call_count, gen.call_count) == (1, 0)


def test_search_and_both_previews_without_model_or_generation(
    spies, monkeypatch, tmp_path
):
    agent, gen = spies
    enable(monkeypatch, make_pack(tmp_path / "pack"), "local")
    a = app()
    submit(a)
    assert "Nothing searched yet" in texts(a)
    a.button(key="dataset_ref_find").click().run()
    assert not a.exception
    result = a.session_state[refs.RESULT]
    assert [h.reference_id for h in result.scene_hits] == [
        "ssr:canon:Bedroom-1",
        "ssr:turned:Bedroom-1",
    ]
    shown = texts(a)
    assert "References for next specification" in shown and "openings unknown" in shown

    charts = len(a.get("plotly_chart"))
    a.button(key="dataset_ref_preview:1").click().run()
    assert len(a.get("plotly_chart")) == charts + 1
    assert "not a spatially approved layout" in texts(a)
    a.button(key="dataset_ref_preview:2").click().run()
    # P7: quarter-turn references are drawn too, by our own figure, not render_floorplan.
    assert "turned 90" in texts(a) and len(a.get("plotly_chart")) == charts + 1
    assert any(len(d.value) == 1 for d in a.dataframe)
    assert (agent.call_count, gen.call_count) == (1, 0)


def test_references_never_touch_preparation_or_displayed_results(
    spies, monkeypatch, tmp_path
):
    from archimind.ui import realistic_view as view

    agent, gen = spies
    validator = Mock(wraps=ui.validate_accessibility)
    renderer = Mock(wraps=view.render_selected_realistic_scene)
    monkeypatch.setattr(ui, "validate_accessibility", validator)
    monkeypatch.setattr(view, "render_selected_realistic_scene", renderer)
    enable(monkeypatch, make_pack(tmp_path / "pack"), "local")
    a = app()
    submit(a)
    a.selectbox(key="chat_choice:1:request-1").set_value("procedural:queen-bed").run()
    a.selectbox(key="chat_choice:1:request-2").set_value(BELAYA_ID).run()
    a.button(key="prepare_chat").click().run()
    a.button(key="generate_layouts").click().run()
    layouts, prepared = a.session_state[ui.RESULT_KEY], a.session_state[chat.PREPARED]
    a.button(key="dataset_ref_find").click().run()
    a.button(key="dataset_ref_preview:1").click().run()
    assert a.session_state[ui.RESULT_KEY] is layouts
    assert a.session_state[chat.PREPARED] is prepared
    assert (agent.call_count, gen.call_count) == (1, 1)

    assert len(layouts.candidates) == 2
    a.radio(key=view.VIEW_KEY).set_value(view.THREE_VIEW).run()
    for index, label in enumerate(("Layout A", "Layout B")):
        a.radio(key=ui.SELECTION_KEY).set_value(label).run()
        assert not a.exception
        assert a.session_state[ui.RESULT_KEY] is layouts
        assert layouts.candidates[index].validation.status == "passed"
        assert f"{label} · Approved product bindings: 1 · Placeholders: 1" in texts(a)
        assert renderer.call_args.args[0] is layouts.candidates[index].design
        (bindings,) = [
            frame.value
            for frame in a.dataframe
            if "Representation" in frame.value.columns
        ]
        assert bindings.set_index("Furniture ID")["Representation"].to_dict() == {
            f"catalog:{BELAYA_ID}:1": "approved product",
            "queen-bed": "placeholder",
        }
    assert (agent.call_count, gen.call_count, validator.call_count) == (1, 1, 2)

    a.button(key="chat_bedroom_reset").click().run()
    assert refs.RESULT not in a.session_state and refs.PREVIEW not in a.session_state
    assert a.session_state[ui.RESULT_KEY] is layouts


def test_changed_measurements_invalidate_only_references(spies, monkeypatch, tmp_path):
    agent, gen = spies
    enable(monkeypatch, make_pack(tmp_path / "pack"), "local")
    a = app()
    submit(a)
    a.button(key="dataset_ref_find").click().run()
    assert refs.RESULT in a.session_state
    wider = TEXT.replace("5 m wide", "7 m wide")
    agent.return_value = reconcile_catalog_extraction(
        extraction().model_copy(update={"width": measure(7)}), turns(wider)
    )
    submit(a, wider)
    assert refs.RESULT not in a.session_state
    assert "Nothing searched yet" in texts(a)
    assert gen.call_count == 0


def _preview(objects, dims=(4.0, 5.0, 2.7)):
    from archimind.datasets.search import PreviewObject, ReferencePreview

    return ReferencePreview(
        status="ready",
        reference_id="ssr:turned:Bedroom-1",
        snapshot_id="0" * 64,
        tier="reference_only",
        display="oriented_footprints",
        room=RoomExtent(width_m=dims[0], depth_m=dims[1], height_m=dims[2]),
        objects=tuple(PreviewObject(**o) for o in objects),
        openings="unknown",
    )


def test_reference_figure_traces_and_bounds():
    bed = dict(
        category="bed",
        x_m=1.0,
        y_m=0.5,
        width_m=1.6,
        depth_m=2.0,
        height_m=0.5,
        yaw_quarter_turns=1,
    )
    desk = dict(
        category="table",
        x_m=2.5,
        y_m=4.0,
        width_m=1.2,
        depth_m=0.6,
        height_m=0.7,
        yaw_quarter_turns=0,
    )
    stand = dict(
        category="cabinet_shelf_desk",
        x_m=-0.1,
        y_m=0.0,
        width_m=0.4,
        depth_m=0.4,
        height_m=0.5,
        yaw_quarter_turns=2,
    )
    fig = refs.reference_figure(_preview([bed, desk, stand]))
    assert len(fig.data) == 1 + 3  # room outline + one rectangle per object
    outline = fig.data[0]
    assert (min(outline.x), max(outline.x), min(outline.y), max(outline.y)) == (
        0.0,
        4.0,
        0.0,
        5.0,
    )
    rect = fig.data[1]
    assert (min(rect.x), max(rect.x)) == pytest.approx((1.0, 2.6))
    assert (min(rect.y), max(rect.y)) == pytest.approx((0.5, 2.5))
    assert rect.fill == "toself"
    names = [t.name for t in fig.data[1:]]
    assert names == ["bed · turned 90°", "table", "cabinet/shelf/desk · turned 180°"]
    x0, x1 = fig.layout.xaxis.range
    assert x0 < -0.1 and x1 > 4.0  # objects slightly outside stay visible
    assert fig.layout.yaxis.scaleanchor == "x"
    assert "not validated" in fig.layout.title.text


@pytest.mark.parametrize("withdrawal", ["audience", "remove", "replace", "corrupt"])
def test_cached_hits_disappear_on_withdrawal(tmp_path, monkeypatch, spies, withdrawal):
    root = make_pack(tmp_path / "pack")
    enable(monkeypatch, root, "local")
    a = app()
    submit(a)
    a.button(key="dataset_ref_find").click().run()
    a.button(key="dataset_ref_preview:1").click().run()
    assert "ssr:canon:Bedroom-1" in texts(a)
    if withdrawal == "audience":
        monkeypatch.setenv(refs.AUDIENCE_ENV, "public")
    elif withdrawal == "remove":
        root.rename(tmp_path / "withdrawn")
    elif withdrawal == "replace":
        from archimind.datasets.fixtures import build_synthetic_pack

        root.rename(tmp_path / "previous")
        build_synthetic_pack(root)
    else:
        (root / "sources.jsonl").write_bytes(b"{}\n")
    a.run()
    assert not a.exception
    assert "ssr:canon:Bedroom-1" not in texts(a)
    assert refs.PREVIEW not in a.session_state and refs.RESULT not in a.session_state
    assert not any(b.label == "Preview reference" for b in a.button)


@pytest.mark.parametrize("function", ["desk", "nightstand"])
def test_shipped_fixture_matches_single_chat_request(tmp_path, function):
    from catalog_chat_helpers import intent

    from archimind.datasets.fixtures import build_synthetic_pack
    from archimind.datasets.search import (
        load_reference_pack,
        reference_query_from_chat,
        search_references,
    )

    root = tmp_path / "pack"
    build_synthetic_pack(root)
    text = TEXT.replace("A queen bed and a writing desk.", f"One {function}.")
    data = extraction().model_copy(
        update={"furniture": (intent(function, f"One {function}"),)}
    )
    draft = reconcile_catalog_extraction(data, turns(text)).draft
    result = search_references(
        reference_query_from_chat(draft),
        pack=load_reference_pack(root, audience="local"),
    )
    assert len(result.scene_hits) == 1
    (match,) = result.scene_hits[0].category_matches
    assert (match.term, match.found) == (function, 1)
