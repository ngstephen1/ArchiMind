"""Style pack registry, offline brief mapping and revision recording."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from archimind.style_packs import (
    DEFAULT_STYLE,
    LEGACY_PALETTE_TO_STYLE,
    STYLE_TO_LEGACY_PALETTE,
    all_packs,
    load_pack,
    load_releases,
    pack_status,
    resolve_style_phrase,
)
from archimind.style_packs.models import StylePack
from archimind.town import service
from archimind.town.api import app
from archimind.town.design import Brief, generate, interpret_offline, validate_home

ROOT = Path(__file__).resolve().parents[1]
STYLES = ["modern_classic", "industrial_loft", "scandinavian", "japandi", "mid_century"]
CLARIFY = "Choose one style: modern classic, industrial loft, Scandinavian, Japandi or mid-century."


def legacy_home_fixture():
    return json.loads((ROOT / "tests/fixtures/town_legacy_terracotta.json").read_text())


def test_all_five_packs_load_and_validate():
    packs = all_packs()
    assert [p.id for p in packs] == STYLES
    for pack in packs:
        assert isinstance(pack, StylePack)
        assert load_pack(pack.id) is pack
        assert set(pack.surfaces) == {
            "floor",
            "wall",
            "ceiling",
            "trim",
            "door",
            "window_frame",
            "worktop",
            "tile",
            "metal",
        }
        for surface in pack.surfaces.values():
            assert surface.fallback_color.startswith("#") and surface.tiling_m > 0
        assert pack.lighting.exposure > 0
        assert set(pack.plan_theme.model_dump()) == {
            "wall_fill",
            "wall_stroke",
            "floor_fill",
            "furniture_fill",
            "furniture_stroke",
            "label_color",
            "door_color",
            "window_color",
        }
    assert DEFAULT_STYLE == "scandinavian"


def test_pack_json_round_trips_and_rejects_unknown_fields():
    raw = json.loads(
        (ROOT / "src/archimind/_viewer_assets/packs/japandi.json").read_text()
    )
    assert StylePack.model_validate(raw).model_dump(mode="json") == raw
    with pytest.raises(ValueError):
        StylePack.model_validate(raw | {"mood": "calm"})
    with pytest.raises(ValueError):
        StylePack.model_validate(raw | {"id": "gothic"})


def test_every_pack_has_released_surfaces_and_lighting():
    releases = load_releases()
    for pack in all_packs():
        for surface in pack.surfaces.values():
            assert releases[surface.asset_id].kind == "material"
        assert releases[pack.lighting.environment_asset_id].kind == "environment"
    status = pack_status(load_pack("japandi"))
    assert status.released and status.missing == ()
    assert 0 < status.low_bytes < status.high_bytes
    # A pack naming an unreleased asset reports it as missing.
    floor = (
        load_pack("japandi")
        .surfaces["floor"]
        .model_copy(update={"asset_id": "polyhaven:not_fetched"})
    )
    broken = load_pack("japandi").model_copy(
        update={"surfaces": {**load_pack("japandi").surfaces, "floor": floor}}
    )
    assert pack_status(broken).missing == ("polyhaven:not_fetched",)


@pytest.mark.parametrize(
    "text,style",
    [
        ("make it japandi", "japandi"),
        ("new york loft", "industrial_loft"),
        ("industrial", "industrial_loft"),
        ("parisian", "modern_classic"),
        ("mid-century modern", "mid_century"),
        ("scandi", "scandinavian"),
        ("Quiet bedroom in a japandi style", "japandi"),
        ("modern classic finishes", "modern_classic"),
    ],
)
def test_offline_style_clause(text, style):
    assert interpret_offline(Brief(), text).style == style


@pytest.mark.parametrize(
    "word,style",
    [
        ("oak", "scandinavian"),
        ("sage", "japandi"),
        ("use terracotta finishes", "mid_century"),
        ("warm finishes", "scandinavian"),
    ],
)
def test_legacy_finish_words_map(word, style):
    assert interpret_offline(Brief(style="japandi"), word).style == style


def test_two_styles_or_unknown_style_ask_for_clarification():
    for text in [
        "japandi and industrial loft",
        "gothic style",
        "japandi industrial loft",
        "sage and industrial",
    ]:
        with pytest.raises(ValueError) as raised:
            interpret_offline(Brief(), text)
        assert str(raised.value) == CLARIFY


def test_unsupported_clause_message_lists_a_style():
    with pytest.raises(ValueError, match="a finish, a style, or"):
        interpret_offline(Brief(), "add another storey")


def test_no_style_defaults_to_scandinavian():
    assert interpret_offline(Brief(), "quiet bedroom").style == "scandinavian"


def test_resolve_style_phrase():
    assert resolve_style_phrase("japandi") == "japandi"
    assert resolve_style_phrase("New York loft") == "industrial_loft"
    assert resolve_style_phrase("gothic") is None
    assert LEGACY_PALETTE_TO_STYLE == {
        "oak": "scandinavian",
        "sage": "japandi",
        "terracotta": "mid_century",
    }
    assert STYLE_TO_LEGACY_PALETTE == {
        "scandinavian": "oak",
        "modern_classic": "oak",
        "industrial_loft": "oak",
        "japandi": "sage",
        "mid_century": "terracotta",
    }


def test_brief_accepts_legacy_palette_field():
    assert Brief.model_validate({"palette": "sage"}).style == "japandi"
    assert (
        Brief.model_validate({"palette": "oak", "style": "mid_century"}).style
        == "mid_century"
    )
    assert "palette" not in Brief().model_dump()


def test_new_home_records_pack_and_legacy_palette():
    home = generate(Brief(style="japandi"), None)[0]
    assert home["style_pack"] == {
        "id": "japandi",
        "version": load_pack("japandi").version,
    }
    assert home["palette"] == "sage"


def test_packaged_showcase_is_a_scandinavian_pack_home():
    showcase = json.loads(
        (ROOT / "frontend/realistic_viewer/town/showcase.json").read_text()
    )
    assert showcase["style_pack"] == {
        "id": "scandinavian",
        "version": load_pack("scandinavian").version,
    }
    assert showcase["palette"] == "oak"


def test_legacy_revision_round_trips_without_style_pack():
    old = legacy_home_fixture()
    before = copy.deepcopy(old)
    validate_home(old)
    assert "style_pack" not in old and old == before


def _coordinate(message, previous, brief):
    from archimind.town import agents

    events = []
    req = SimpleNamespace(brief=brief, message=message, live=False, base=1, agent_team=False)
    homes = agents.coordinate(
        req,
        previous,
        lambda r, p: interpret_offline(r.brief, r.message),
        lambda *e: events.append(e),
    )
    return homes, events


def test_style_only_edit_preserves_geometry_and_redresses_locked_rooms():
    previous = generate(Brief(), None)[0]
    homes, events = _coordinate("make it japandi", previous, Brief(locks=["bedroom"]))
    (home,) = homes
    assert [
        {k: r[k] for k in ("origin", "asset_bindings", "design")} for r in home["rooms"]
    ] == [
        {k: r[k] for k in ("origin", "asset_bindings", "design")}
        for r in previous["rooms"]
    ]
    assert home["style_pack"]["id"] == "japandi" and home["palette"] == "sage"
    assert home["id"] != previous["id"]
    assert ("C", "skipped", "Style edit preserves geometry", {}) in events
    resolved = next(e for e in events if e[2] == "Resolved style")
    assert resolved[3] == {"style_pack": home["style_pack"], "name": "Japandi"}
    legacy = legacy_home_fixture()
    (redressed,), _ = _coordinate("use sage finishes", legacy, Brief())
    assert [
        {k: r[k] for k in ("origin", "asset_bindings", "design")}
        for r in redressed["rooms"]
    ] == [
        {k: r[k] for k in ("origin", "asset_bindings", "design")}
        for r in legacy["rooms"]
    ]
    assert redressed["style_pack"]["id"] == "japandi"


def test_live_interpreter_schema_offers_only_the_five_styles():
    schema = service.Interpretation.model_json_schema()
    assert "palette" not in schema["properties"]
    style = schema["properties"]["style"]
    assert (
        style.get("enum") == STYLES
        or schema["$defs"][style["$ref"].split("/")[-1]]["enum"] == STYLES
    )


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TOWN_MODE", "local")
    monkeypatch.setenv("TOWN_DB", str(tmp_path / "test.db"))
    service.initialize()
    return TestClient(app, base_url="http://localhost")


def test_api_accepts_legacy_palette_field(local):
    import uuid

    p = service.create("local-designer")["project"]
    for brief in ({"palette": "sage"}, {"style": "industrial_loft"}):
        response = local.post(
            "/api/jobs",
            json={
                "id": str(uuid.uuid4()),
                "project": p,
                "base": 0,
                "brief": brief,
                "message": "",
            },
        )
        assert response.status_code == 200, response.text
        assert service.work_once()
    request = service.Request.model_validate(
        {
            "id": str(uuid.uuid4()),
            "project": p,
            "base": 0,
            "brief": {"palette": "terracotta"},
        }
    )
    assert request.brief.style == "mid_century"


def test_surface_tint_is_optional_hex():
    from archimind.style_packs.models import SurfaceSpec

    base = {
        "asset_id": "polyhaven:white_stucco",
        "tiling_m": 2.0,
        "fallback_color": "#f2f0eb",
    }
    assert SurfaceSpec.model_validate(base).tint is None
    assert SurfaceSpec.model_validate(base | {"tint": "#c8a165"}).tint == "#c8a165"
    with pytest.raises(ValueError):
        SurfaceSpec.model_validate(base | {"tint": "brass"})


def test_style_phrases_with_the_resolve_to_one_style():
    from archimind.town.design import Brief, interpret_offline

    for text in (
        "bright study in the japandi style",
        "the japandi style",
        "make it the japandi style",
    ):
        assert interpret_offline(Brief(), text).style == "japandi", text
