# Photoreal Style Packs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every ArchiMind design shows as a near-photoreal plan, 3D room and walkthrough, dressed in one of five user-chosen style packs, using CC0 library assets plus Codex/Blender-authored signature pieces.

**Architecture:** Python owns every decision (which pack, which asset per furniture item, where decor goes) and records it on the revision/scene, so all three views agree. A shared JS rendering layer turns that record into lighting, materials, models and decor, with `high`/`low` quality tiers. Assets live content-addressed under `_viewer_assets/packs/`, each with a release record, and load lazily per pack with SHA-256 verification; legacy palette-only revisions keep today's rendering path untouched.

**Tech Stack:** Python 3.11, Pydantic, Shapely, Streamlit (Components V2), Plotly; Three.js 0.187.0 (built-in `three/addons` only, incl. `EffectComposer`, `GTAOPass`, `OutputPass`, `RGBELoader`), esbuild, `node --test`; Blender 5.1+ with Blender Lab MCP, Codex CLI; Poly Haven / ambientCG CC0 assets.

**Spec:** `docs/superpowers/specs/2026-11-17-photoreal-style-packs-design.md` (read it first; this plan argues from it).

## Global Constraints

- No view may need a model call, desktop app, render server or third-party network fetch to display; viewing, A/B, walking and replay stay local.
- Three.js stays pinned at `0.187.0`. No new npm or PyPI dependency; post-processing uses `three/addons` only.
- Budgets (`src/archimind/assets/inspection.py`): ≤15 MB per GLB, ≤100,000 triangles per asset, ≤300,000 instantiated triangles per scene, ≤50 MB unique encoded scene bytes, textures ≤2048 px.
- Pack size cap: ≤25 MB of unique files per pack (high tier), ≤120 MB across all five. Exceeding it means dropping a 2k map or a model, never raising the cap.
- Textures: WebP or JPEG; 1k for `low`, 2k for `high` only where it visibly matters. Environment maps: 1k `.hdr` only, for both tiers.
- Every shipped asset file has a release record: source URL, licence `CC0-1.0` or `original-blender`, upstream checksum (if published), local SHA-256, byte size, pixel size or measured dimensions. Each CC0 source also gets a `THIRD_PARTY_NOTICES.txt` line.
- Style IDs, exactly: `modern_classic`, `industrial_loft`, `scandinavian`, `japandi`, `mid_century`. Default for a brief naming no style: `scandinavian`.
- Legacy finish words map: `oak → scandinavian`, `sage → japandi`, `terracotta → mid_century`. New homes also write `palette` as `scandinavian/modern_classic/industrial_loft → oak`, `japandi → sage`, `mid_century → terracotta` so existing palette readers keep working.
- Revisions saved before this ships (no `style_pack` key) render exactly as today.
- Style is per home; locked rooms keep geometry/openings/furniture positions and are re-dressed in the home's pack.
- Decor/accent placement never moves approved furniture and never breaks containment, collision or the 0.6 m clearance checks; anything that doesn't fit is skipped and listed.
- Kitchens and bathrooms: counters, vanities and baths are procedural shapes wearing the pack's worktop/tile/metal surfaces. Full model effort goes to bedroom, living room and study.
- Hash-pinned files (baseline list in `docs/data/FURNITURE_EXPANSION_08F1.json`, includes `app.py`, UI modules, `frontend/realistic_viewer/src/*`, `_viewer_assets/viewer.js`, `pyproject.toml`) may change only with a recorded migration in `docs/data/STYLE_PACKS_11A.json` (Task 1 tooling). The owner approved this design on 2026-11-17; record that as the authorization.
- Windows test runs: `PYTHONUTF8=1`, `.venv/Scripts/python -m pytest`; app UI tests need the scratchpad `-p win_selfpipe` plugin; the Windows baseline has 17 failed / 55 errors pre-existing (compare against baseline, don't chase them).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Don't push without asking.

## Review Focus

1. **A legacy revision opened after ship** (palette only, no `style_pack`) must look identical in Town, editor and presentation, with no pack fetches. Pinned in Task 6 (Python) and Task 5 (Town JS).
2. **A pack file is missing, truncated or fails its hash** halfway through loading: that surface/model falls back to a labeled plain material or the procedural piece, the rest of the room still renders, and the status line names the failure. Pinned in Task 3.
3. **The user switches style, A/B or revision while a pack is still loading:** the late load is discarded (`superseded`), never painted onto the newer room. Pinned in Task 3 and Task 5.
4. **Small or crowded rooms** (e.g. a 2.4 × 2.6 m study) where no accent piece or plant fits: nothing is placed, `skipped` lists them, validation still passes, no exception. Pinned in Task 9.
5. **Two styles in one brief** ("japandi industrial loft") or an unknown one ("gothic"): a clarification message listing the five styles, and the saved home is unchanged. Pinned in Task 6.

---

## Phase 0 — Base

### Task 1: Merge PR #21 and set up migration recording

**Files:**
- Merge: `origin/feat/blender-designer-chair` into `feat/new-feature`
- Create: `tests/pin_chain.py`
- Modify: `tests/test_furniture_source_expansion.py:488-590` (use `pin_chain`)
- Create: `scripts/record_style_pack_migrations.py`
- Create: `docs/data/STYLE_PACKS_11A.json`
- Create: `docs/images/style-packs/legacy-before/` (baseline screenshots)

**Interfaces:**
- Produces: `expected_pins(root: Path, *, include_style_packs: bool = True) -> dict[str, str]` in `tests/pin_chain.py`, the path→expected-SHA-256 map after applying every receipt in today's order, then `STYLE_PACKS_11A.json["authorized_migrations"]` last.
- Produces: `python scripts/record_style_pack_migrations.py` rewrites `STYLE_PACKS_11A.json["authorized_migrations"]` so each changed pinned path has `{"before_sha256": <chain value without 11A>, "after_sha256": <sha of the staged blob>}`; unchanged paths are removed. Every later task that edits a pinned file runs it after `git add` and before commit.

- [ ] **Step 1:** `git merge --no-ff origin/feat/blender-designer-chair`; resolve conflicts keeping both sides' intent (main moved 70 commits since PR #21 branched only from its own base; expect conflicts in `room_viewer.js`, `viewer.js` bundle, `test_furniture_source_expansion.py`). Rebuild the bundle with `npm run build --prefix frontend/realistic_viewer` instead of hand-merging `viewer.js`.
- [ ] **Step 2:** Run `npm test --prefix frontend/realistic_viewer` and `PYTHONUTF8=1 .venv/Scripts/python -m pytest -q -x --deselect <known baseline failures>`; expected: frontend all pass, Python no new failures versus the Windows baseline.
- [ ] **Step 3: Write the failing test** in `tests/test_style_pack_receipt.py`:

```python
def test_chain_matches_preservation_test():
    pins = expected_pins(ROOT)
    for path, sha in pins.items():
        assert hashlib.sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == sha

def test_receipt_records_owner_authorization():
    r = json.loads((ROOT / "docs/data/STYLE_PACKS_11A.json").read_text())
    assert r["authorization"] == {"by": "owner", "date": "2026-11-17",
        "scope": "docs/superpowers/specs/2026-11-17-photoreal-style-packs-design.md"}
    assert set(r["authorized_migrations"]) <= set(expected_pins(ROOT))
```

- [ ] **Step 4:** Run `pytest tests/test_style_pack_receipt.py -v`; expected FAIL (module missing).
- [ ] **Step 5:** Move the receipt-chain loop from the preservation test into `tests/pin_chain.py::expected_pins`, append the 11A step, make the preservation test call it (it keeps its other assertions). Create `STYLE_PACKS_11A.json` with `authorization` and empty `authorized_migrations`. Write the record script (hash `git show :<path>` bytes).
- [ ] **Step 6:** Run both test files; expected PASS.
- [ ] **Step 7:** Capture legacy baseline screenshots (Chrome, 1440×1000 and 390×844): Town showcase bedroom/living walkthrough, Town plan, Studio offline bedroom 3D and plan. Save as PNG in `docs/images/style-packs/legacy-before/`. These are the Review Focus #1 reference.
- [ ] **Step 8:** Commit "Merge designer chair work and add style-pack migration receipt".

### Task 2: Generalise designer chair → designer piece

**Files:**
- Modify: `src/archimind/assets/designer_concepts.py`, `src/archimind/_viewer_assets/designer_registry.json`
- Modify: `src/archimind/town/designer_chair.py` (keep its API; delegate)
- Rename: `scripts/author_designer_chair.py` → `scripts/author_designer_piece.py`, `scripts/release_designer_chair.py` → `scripts/release_designer_piece.py` (add `--category`, `--wdh`)
- Test: `tests/test_designer_concepts.py`

**Interfaces:**
- Produces: `DesignerPiece` (frozen dataclass): `concept_id, version, name, category, sha256, front_sha256, three_quarter_sha256, width_m, depth_m, height_m, bytes`; `category ∈ {"chair","armchair","sofa","bed","table","desk","storage","lamp","decor"}`.
- Produces: `approved_pieces(category: str | None = None) -> tuple[DesignerPiece, ...]`, `resolve_piece(concept_id, version, sha256) -> DesignerPiece`, `inspect_piece(data: bytes, wdh_m: tuple[float, float, float]) -> dict`, `preview_bytes(piece, view)`.
- Keeps: `approved_chairs()` and `resolve_chair()` as thin wrappers (category `"chair"`), so PR #21's Town/Studio code and tests are unchanged.
- Registry `schema_version: 2`, key `pieces`; a v1 registry still loads (treated as chairs).

- [ ] **Step 1: Write failing tests:** `test_registry_v2_lists_pieces_by_category` (fixture registry with one chair, one armchair → `approved_pieces("armchair")` has 1); `test_v1_registry_still_loads_as_chairs`; `test_inspect_piece_rejects_off_reservation_bounds` (chair GLB from the release vs `wdh=(0.5,0.52,0.83)` → `ValueError`); `test_unknown_category_disables_registry` (→ `()`).
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement. `inspect_piece` replaces the hard-coded chair bounds with `(-w/2, 0, -d/2, w/2, h, d/2)` from `wdh_m` and, unlike the chair, allows embedded textures (images ≤2048 px, checked via `inspection`).
- [ ] **Step 4:** Run the new tests plus `tests/test_designer_chair_authoring.py tests/test_town.py tests/test_studio.py`; expected PASS.
- [ ] **Step 5:** Commit.

## Phase 1 — Shared rendering

### Task 3: Quality tiers, pack loader and lighting module

**Files:**
- Create: `frontend/realistic_viewer/src/render_quality.js`
- Create: `frontend/realistic_viewer/src/style_pack.js`
- Test: `frontend/realistic_viewer/tests/render_quality.test.js`, `tests/style_pack.test.js`
- Modify: `frontend/realistic_viewer/package.json` (`check` script lists the new files)

**Interfaces:**
- Produces (`render_quality.js`):
  - `chooseTier({viewportWidth, deviceMemory, override}) -> "high" | "low"`: `override` wins; else `low` if `viewportWidth < 700` or `deviceMemory` is a number `< 4`; else `high`.
  - `configureRenderer(renderer, tier)`: sRGB output, `AgXToneMapping`, `PCFSoftShadowMap`, pixel ratio cap 2 (high) / 1.25 (low).
  - `createComposer(renderer, scene, camera, tier) -> {render(), setSize(w, h), dispose()}`: high = `RenderPass` + `GTAOPass` + `OutputPass`; low = plain `renderer.render`.
  - `TIER_SETTINGS = {high: {shadowMapSize: 2048, textureSize: "2k", decorDensity: 1}, low: {shadowMapSize: 1024, textureSize: "1k", decorDensity: 0.5}}`.
- Produces (`style_pack.js`):
  - `loadStylePack({baseUrl, ref: {id, version}, tier, fetchBytes = defaultFetch, isCurrent = () => true}) -> Promise<LoadedPack | "superseded">`.
  - `LoadedPack = {id, version, manifest, surface(role) -> THREE.MeshStandardMaterial, environment: THREE.Texture | null, model(assetId) -> Promise<THREE.Object3D | null>, failures: string[], dispose()}`. `role ∈ manifest.surfaces` keys.
  - Each file is fetched from `${baseUrl}packs/assets/${sha256}.${ext}`, verified with `crypto.subtle.digest("SHA-256")`; a mismatch or fetch error records `failures.push(role or assetId)` and yields the fallback (plain `MeshStandardMaterial` in the manifest's `fallback_color` for that role; `null` model so the caller keeps the procedural piece).
  - `applyLighting(scene, renderer, pack, tier) -> {dispose()}`: PMREM from the pack environment (or `RoomEnvironment` if it failed), sun from `manifest.lighting`, exposure, fill lights.

- [ ] **Step 1: Write failing tests** (node test runner, fake `fetchBytes`):

```js
test('tier: narrow or low-memory is low, override wins', () => {
  assert.equal(chooseTier({viewportWidth: 390}), 'low');
  assert.equal(chooseTier({viewportWidth: 1440, deviceMemory: 2}), 'low');
  assert.equal(chooseTier({viewportWidth: 1440, deviceMemory: 8}), 'high');
  assert.equal(chooseTier({viewportWidth: 390, override: 'high'}), 'high');
});
test('hash mismatch falls back per surface and is reported', async () => {
  const pack = await loadStylePack({baseUrl: '/', ref, tier: 'low', fetchBytes: fakeFetch({corrupt: 'floor'})});
  assert.deepEqual(pack.failures, ['floor']);
  assert.equal(pack.surface('floor').map, null);
  assert.equal(pack.surface('floor').color.getHexString(), manifest.surfaces.floor.fallback_color.slice(1));
  assert.ok(pack.surface('wall').map);
});
test('missing file and truncated file both fall back', async () => { /* 404 for wall, short bytes for trim → failures ['wall','trim'] */ });
test('a load that is no longer current returns superseded and disposes', async () => {
  let current = true;
  const p = loadStylePack({baseUrl: '/', ref, tier: 'low', fetchBytes: slowFetch(() => { current = false; }), isCurrent: () => current});
  assert.equal(await p, 'superseded');
});
test('low tier requests 1k files, high tier 2k where present', async () => { /* inspect fetched URLs */ });
```

- [ ] **Step 2:** `npm test --prefix frontend/realistic_viewer`; expected the new tests FAIL.
- [ ] **Step 3:** Implement both modules. The manifest is the pack JSON defined in Task 6 (`packs/<id>.json`: `surfaces.<role>.{asset_id, tiling_m, fallback_color}`, `lighting`) joined with `packs/releases.json` (`AssetRelease.files[].{role, tier, sha256, ext}`); Task 6 must keep these field names. Until then, use a hand-written fixture pack in `tests/fixtures/style-pack/`.
- [ ] **Step 4:** Run; expected PASS, and `npm run check` passes.
- [ ] **Step 5:** Commit.

### Task 4: Studio room viewer uses the shared layer

**Files:**
- Modify: `frontend/realistic_viewer/src/room_viewer.js` (pinned), rebuild `src/archimind/_viewer_assets/viewer.js` (pinned)
- Test: `frontend/realistic_viewer/tests/room.test.js`, `tests/test_studio_ui.py`

**Interfaces:**
- Consumes: Task 3 exports.
- Scene input gains optional `style: {style_pack: {id, version}, bindings: [...], dressing: [...], skipped: [...]}` (shape from Task 8). Absent → current code path, byte-for-byte same scene setup.
- Toolbar gains a `Quality: High | Low` toggle (`button.quality`) showing the chosen tier; persisted per viewer in `viewState.tier`.

- [ ] **Step 1: Write failing tests:** `room viewer without style keeps legacy lighting` (no `style` → `RoomEnvironment` path, no pack fetch); `room viewer with style loads pack and applies surfaces` (fake fetch, `root.dataset.stylePack === 'scandinavian@1.0.0'`); `quality toggle switches composer and records tier`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement: when `style` is present, `chooseTier` → `configureRenderer` → `loadStylePack` (with the viewer's generation-owner `isCurrent`) → `applyLighting`; floor/wall/ceiling/trim materials from `pack.surface(...)`; render via `createComposer`. Status line lists `pack.failures` ("Fallback materials: floor").
- [ ] **Step 4:** Run tests, `npm run build --prefix frontend/realistic_viewer`, then `git add` and `python scripts/record_style_pack_migrations.py`; run the preservation test; expected PASS.
- [ ] **Step 5:** Commit.

### Task 5: Town walkthrough uses the shared layer

**Files:**
- Modify: `frontend/realistic_viewer/town/world.js` (`load(h)` at ~556, palette block ~662), `town/app.js`, `town/index.html`, `town/build.mjs`
- Test: `frontend/realistic_viewer/tests/town_style.test.js`

**Interfaces:**
- Consumes: Task 3; home JSON from Task 6 (`h.style_pack`, `part.style`).
- `build.mjs` copies `src/archimind/_viewer_assets/packs/**` to `dist/town/assets/packs/`.
- Footer gains the same Quality toggle.

- [ ] **Step 1: Write failing tests** (extract the decision into a pure helper `townSurfaceSource(h) -> {kind: "legacy", wallColor} | {kind: "pack", ref}` in `town/style_source.js`): legacy home `{palette: "sage"}` → `{kind: "legacy", wallColor: "#bac6ad"}`; home with `style_pack` → `{kind: "pack", ref}`; a pack load superseded by `load(h2)` never touches `h2`'s interior (reuse the `fitBedroomChair` currentness pattern).
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement. Interior rooms of pack homes get pack surfaces and lighting (interior lights per room from `manifest.lighting`); the exterior town keeps its current look. Legacy homes run the existing code untouched.
- [ ] **Step 4:** Run tests; `node frontend/realistic_viewer/town/build.mjs`; manual check: showcase still loads (legacy until Task 6 switches it).
- [ ] **Step 5:** Commit.

## Phase 2 — Style pack contract and briefs

### Task 6: Style pack registry, Town briefs and revisions

**Files:**
- Create: `src/archimind/style_packs/__init__.py`, `models.py`, `registry.py`
- Create: `src/archimind/_viewer_assets/packs/{modern_classic,industrial_loft,scandinavian,japandi,mid_century}.json` (surfaces + lighting + plan theme filled with direction; asset IDs may point at not-yet-released assets)
- Create: `src/archimind/_viewer_assets/packs/releases.json` (empty list)
- Modify: `src/archimind/town/design.py` (`Brief`, `interpret_offline`, home construction ~267/421), `town/agents.py` (Agent E, `finish_only`), `town/service.py:175-232` (live schema/prompt), `town/api.py` (accept `style`, still accept `palette`), `town/showcase.json`, `town/app.js` + `index.html` (style select)
- Modify: `pyproject.toml` package-data: add `"_viewer_assets/packs/*", "_viewer_assets/packs/assets/*"` (pinned → record migration)
- Test: `tests/test_style_packs.py`, `tests/test_town.py`

**Interfaces:**
- Produces (`models.py`): `StyleId = Literal["modern_classic","industrial_loft","scandinavian","japandi","mid_century"]`; `StylePack` (fields per spec §2: `id, version, name, aliases, surfaces: dict[str, SurfaceSpec], furniture: dict[str, list[FurnitureChoice]], decor: DecorRules, lighting: Lighting, plan_theme: PlanTheme, quality`); `SurfaceSpec{asset_id, tiling_m, fallback_color}`; `FurnitureChoice{asset_id, width_m, depth_m, height_m}`; `AssetRelease{asset_id, kind: Literal["material","environment","model"], license: Literal["CC0-1.0","original-blender"], source_url, upstream_checksum, files: list[AssetFile]}`; `AssetFile{role, tier: Literal["low","high","both"], sha256, ext, bytes, width_px | None, height_px | None}`.
- Produces (`registry.py`): `load_pack(style_id) -> StylePack`, `all_packs() -> tuple[StylePack, ...]`, `load_releases() -> dict[str, AssetRelease]`, `pack_status(pack) -> PackStatus(released: bool, missing: tuple[str, ...], high_bytes: int, low_bytes: int)`, `resolve_style_phrase(text) -> StyleId | None`, `LEGACY_PALETTE_TO_STYLE`, `STYLE_TO_LEGACY_PALETTE`, `DEFAULT_STYLE = "scandinavian"`.
- `Brief`: replace `palette` with `style: StyleId = "scandinavian"`; `Brief.model_validate` with legacy `palette` input maps through `LEGACY_PALETTE_TO_STYLE` (model validator), so stored briefs and old clients still parse.
- New homes carry `home["style_pack"] = {"id", "version"}` and `home["palette"] = STYLE_TO_LEGACY_PALETTE[id]`.

- [ ] **Step 1: Write failing tests:**

```python
def test_all_five_packs_load_and_validate():
    assert [p.id for p in all_packs()] == ["modern_classic","industrial_loft","scandinavian","japandi","mid_century"]

@pytest.mark.parametrize("text,style", [("make it japandi","japandi"),("new york loft","industrial_loft"),
    ("industrial","industrial_loft"),("parisian","modern_classic"),("mid-century modern","mid_century"),("scandi","scandinavian")])
def test_offline_style_clause(text, style):
    assert interpret_offline(Brief(), text).style == style

@pytest.mark.parametrize("word,style", [("oak","scandinavian"),("sage","japandi"),("use terracotta finishes","mid_century")])
def test_legacy_finish_words_map(word, style): ...

def test_two_styles_or_unknown_style_ask_for_clarification():
    for text in ["japandi and industrial loft", "gothic style"]:
        with pytest.raises(ValueError, match="modern classic, industrial loft, Scandinavian, Japandi or mid-century"):
            interpret_offline(Brief(), text)

def test_no_style_defaults_to_scandinavian(): assert interpret_offline(Brief(), "quiet bedroom").style == "scandinavian"

def test_new_home_records_pack_and_legacy_palette():
    home = generate(Brief(style="japandi"), None)[0]
    assert home["style_pack"] == {"id": "japandi", "version": load_pack("japandi").version}
    assert home["palette"] == "sage"

def test_legacy_revision_round_trips_without_style_pack():
    old = legacy_home_fixture()  # palette "terracotta", no style_pack
    validate_home(old); assert "style_pack" not in old

def test_style_only_edit_preserves_geometry_and_redresses_locked_rooms(): ...
def test_live_interpreter_schema_offers_only_the_five_styles(): ...
def test_api_accepts_legacy_palette_field(): ...
```

- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement. Clarification text (exact): `"Choose one style: modern classic, industrial loft, Scandinavian, Japandi or mid-century."` The offline interpreter's existing unsupported-clause message gains "a style" in its list. Agent E emits `"Resolved style"` with `{style_pack, name}`. `finish_only` becomes `style_only` (regex built from all aliases + legacy words). Switch `showcase.json` to `scandinavian` as a new showcase version and update the tests pinned to it.
- [ ] **Step 4:** Run `tests/test_style_packs.py tests/test_town.py tests/test_town*` plus frontend tests; record migrations; run the preservation test; expected PASS.
- [ ] **Step 5:** Commit.

### Task 7: Asset release tooling and budgets

**Files:**
- Create: `scripts/fetch_cc0_asset.py`
- Create: `src/archimind/style_packs/release.py`
- Modify: `src/archimind/_viewer_assets/THIRD_PARTY_NOTICES.txt` (pinned → record migration)
- Test: `tests/test_style_pack_release.py`

**Interfaces:**
- Produces: `python scripts/fetch_cc0_asset.py --source polyhaven|ambientcg --id <slug> --kind material|environment|model [--roles diffuse,normal,roughness,ao] [--sizes 1k,2k]`: downloads into a new empty temp dir, verifies upstream checksum (Poly Haven API `md5`), converts textures to WebP (Pillow) at the requested sizes, writes `packs/assets/<sha256>.<ext>`, appends/updates the `AssetRelease` in `releases.json`, appends a notices line. Asset ID = `<source>:<slug>`.
- Produces (`release.py`): `verify_release(release) -> None` (raises `ValueError` naming the problem), `pack_budget(pack, tier) -> int`, `PACK_CAP_BYTES = 25 * 1024 * 1024`, `ALL_PACKS_CAP_BYTES = 120 * 1024 * 1024`.

- [ ] **Step 1: Write failing tests:** `test_release_requires_license_source_and_hash`; `test_texture_over_2048px_rejected`; `test_file_hash_must_match_bytes_on_disk`; `test_every_released_pack_is_within_25mb_and_total_within_120mb` (iterates `all_packs()` with `pack_status(...).released`); `test_every_cc0_release_has_a_notice_line`; `test_model_release_passes_glb_inspection_budgets` (uses `inspection` limits).
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement `release.py` and the fetch script (run the script's downloaded files only via paths; run Python with `-I`).
- [ ] **Step 4:** Run; expected PASS (no releases yet → budget tests trivially pass; add one fixture release in the test).
- [ ] **Step 5:** Commit.

### Task 8: Pack furniture binding and scene payload (Python), Studio style choice

**Files:**
- Create: `src/archimind/style_packs/binding.py`, `src/archimind/style_packs/scene.py`
- Modify: `src/archimind/town/design.py` (attach `part["style"]` per room), `src/archimind/studio/contracts.py` (`FurnishingPlan.style: StyleId = "scandinavian"`), `src/archimind/studio/workflow.py:221-240` (scene gains `style`), `src/archimind/ui/studio.py` (Style select), `src/archimind/studio/fixtures.py`
- Test: `tests/test_style_pack_binding.py`, `tests/test_studio.py`, `tests/test_studio_ui.py`

**Interfaces:**
- Produces: `bind_furniture(design: RoomDesign, pack: StylePack) -> list[PackBinding]`; `PackBinding{furniture_id, asset_id: str | None, reason: Literal["pack","designer","procedural_fallback"]}`. Rule: first `FurnitureChoice` for the item's category whose W/D/H all ≤ the item's reservation; else `None` + `procedural_fallback`. Categories `counter`, `vanity`, `bath` always `procedural_fallback` (styled by surfaces).
- Produces: `style_payload(design, pack, seed) -> dict` = `{"style_pack": {"id","version"}, "bindings": [...], "dressing": [...], "skipped": [...]}` (`dressing`/`skipped` empty until Task 9 fills them).
- Studio snapshot includes `style_payload` and the hashes of every bound asset.

- [ ] **Step 1: Write failing tests:** `test_binding_picks_first_choice_that_fits`; `test_oversized_choice_falls_back_to_procedural`; `test_kitchen_and_bath_are_procedural`; `test_payload_is_deterministic_for_seed`; `test_town_rooms_carry_style_payload_and_locked_room_is_redressed`; `test_studio_scene_carries_style_and_snapshot_lists_asset_hashes`; `test_studio_style_select_defaults_to_scandinavian` (AppTest).
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement; Town digest naturally covers `part["style"]`. Record migrations for pinned UI files.
- [ ] **Step 4:** Run; expected PASS.
- [ ] **Step 5:** Commit.

## Phase 3 — Dressing

### Task 9: Decor and accent furniture placement

**Files:**
- Create: `src/archimind/style_packs/decor.py`
- Modify: `src/archimind/style_packs/scene.py` (fill `dressing`, `skipped`)
- Create: `frontend/realistic_viewer/src/dressing.js`; modify `room_viewer.js`, `town/world.js` to call it
- Test: `tests/test_style_pack_decor.py`, `frontend/realistic_viewer/tests/dressing.test.js`

**Interfaces:**
- Produces: `place_dressing(design: RoomDesign, pack: StylePack, seed: int, density: float = 1.0) -> Dressing`; `Dressing{items: list[DressingItem], skipped: list[str]}`; `DressingItem{id, kind: Literal["rug","art","curtain","moulding","pendant","plant","floor_lamp","accent"], asset_id: str | None, x_m, y_m, z_m, width_m, depth_m, height_m, wall: Wall | None, rotation_deg: Literal[0,90,180,270]}`.
- Rules (spec §6): rug under the bed or sofa+table group (flat, may sit under furniture, never under a door swing zone); art centred on the longest wall span free of openings and tall furniture; curtains on every window; mouldings if `pack.decor.mouldings`; pendant over table/bed centre at ceiling; plants, floor lamps and accent furniture only in free floor spots that pass `validate_accessibility` with the item added as furniture (try corners first, seeded order); otherwise appended to `skipped`.
- Produces (`dressing.js`): `buildDressing(group, dressing, pack, tier) -> {dispose()}`; `low` tier draws only items with index < `ceil(n * 0.5)` in a fixed priority order (rug, curtain, pendant, art, accent, plant, floor_lamp, moulding).

- [ ] **Step 1: Write failing tests:**

```python
def test_tiny_study_skips_floor_items_and_stays_valid():
    d = study_design(width_m=2.4, depth_m=2.6)          # existing fixture helpers
    out = place_dressing(d, load_pack("japandi"), seed=42)
    assert {"plant", "accent"} & {s.split(":")[0] for s in out.skipped}
    assert not [i for i in out.items if i.kind in ("plant", "accent", "floor_lamp")]
    validate_accessibility(with_floor_items(d, out))     # no exception

def test_dressing_never_moves_furniture(): ...
def test_art_avoids_openings_and_curtains_cover_each_window(): ...
def test_same_seed_same_dressing_different_seed_may_differ(): ...
def test_every_town_room_dressing_passes_whole_home_validation(): ...
```

  JS: `low tier draws half the items in priority order`; `missing model for accent renders nothing and reports it`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement; floor-standing items enter validation as temporary `Furniture` rows; flat items are geometry-only.
- [ ] **Step 4:** Run Python and frontend suites; rebuild bundle; record migrations; expected PASS.
- [ ] **Step 5:** Commit.

## Phase 4 — Assets for the five packs

### Task 10: Surfaces and lighting for all five packs (CC0)

**Files:**
- Modify: `src/archimind/_viewer_assets/packs/*.json`, `packs/releases.json`, add files under `packs/assets/`
- Test: `tests/test_style_pack_release.py` (existing tests now run against real data)

- [ ] **Step 1:** For each pack, pick and fetch (with Task 7's script) floor, wall, ceiling, trim, door/window-frame, worktop, tile and metal materials and one 1k interior-appropriate HDRI matching the spec §2 table (e.g. dark herringbone + brass for `modern_classic`; concrete + white brick + black steel for `industrial_loft`). Reuse materials across packs where they fit.
- [ ] **Step 2:** Run `pytest tests/test_style_pack_release.py tests/test_style_packs.py -v`; expected PASS, with every pack's surfaces and lighting released and each pack under budget.
- [ ] **Step 3:** Visual check: Studio offline bedroom in all five packs, both tiers, screenshot to `docs/images/style-packs/surfaces/`. Adjust tiling/exposure in the pack JSON until each reads as its style.
- [ ] **Step 4:** Commit.

### Task 11: Blender + MCP operator setup

**Files:**
- Modify: `docs/data/STYLE_PACKS_11A.json` (`operator_environment`)
- Modify: `scripts/test_blender_operator.py` (from PR #21) only if paths differ on Windows

- [ ] **Step 1:** Install Blender 5.1.x (official installer or `winget install BlenderFoundation.Blender --version 5.1.<x>`), pin the exact version.
- [ ] **Step 2:** Install Blender Lab's MCP add-on and server following https://projects.blender.org/lab/blender_mcp/wiki/Setup.md; register it with Codex (`codex mcp add blender -- <server command>`).
- [ ] **Step 3:** Run `.venv/Scripts/python scripts/test_blender_operator.py`; expected: it reports a live Blender session reachable through MCP and round-trips the chair `.blend`.
- [ ] **Step 4:** Record Blender version, add-on version/commit, MCP server command and Codex version in `operator_environment`. Commit.

### Task 12: Furniture models — CC0 first, Blender signature pieces for gaps

**Files:**
- Modify: `packs/*.json` (`furniture` choices), `packs/releases.json`, `_viewer_assets/designer_registry.json`, asset files
- Create: `docs/images/style-packs/pieces/` (front + three-quarter previews of every authored piece)

**Interfaces:**
- Consumes: Task 2 (`release_designer_piece.py`), Task 7 (fetch script), Task 11.

- [ ] **Step 1:** For each pack and each category in bedroom/living/study (`bed, sofa, table, desk, chair, storage, armchair, lamp`), fetch a fitting CC0 model where Poly Haven has one; record in the pack's `furniture` list.
- [ ] **Step 2:** For each remaining gap and each signature piece in spec §2 (green velvet tub armchair, globe-cluster pendant, metal-frame chair, dome pendant, paper pendant, low platform bed, paper lantern, walnut lounge chair, sideboard, tripod lamp, plus any missing bed/sofa), author with Codex through the Blender MCP: named parts, PBR materials with real texture detail (wood grain, fabric weave from the pack's CC0 maps), native scale, floor-centred origin, one revision pass. Release with `release_designer_piece.py`.
- [ ] **Step 3:** Self-review each piece against its previews; reject and redo anything that reads as primitive. Save previews in `docs/images/style-packs/pieces/`.
- [ ] **Step 4:** Run `pytest tests/test_style_pack_release.py tests/test_designer_concepts.py tests/test_style_pack_binding.py -v`; expected PASS, all packs `released`, budgets within caps.
- [ ] **Step 5:** Commit (one commit per pack is fine).

## Phase 5 — Blueprint

### Task 13: Plan themes in Plotly and Town canvas

**Files:**
- Modify: `src/archimind/render/floorplan_2d.py` (`render_floorplan(design, plan_theme=None)`), callers in `ui/studio.py`, `pages/Town_Editor.py`
- Modify: `frontend/realistic_viewer/town/app.js` (`floorPlan(h, c)` at ~198)
- Test: `tests/test_floorplan_2d.py` (or existing plan tests), `frontend/realistic_viewer/tests/town_plan.test.js`

**Interfaces:**
- `PlanTheme{wall_fill, wall_stroke, floor_fill, furniture_fill, furniture_stroke, label_color, door_color, window_color}` (hex strings).
- `render_floorplan(design, plan_theme=None)`: `None` → today's figure exactly.
- Town: extract `planColors(h, manifest | null)` into `town/plan_colors.js`; legacy home → today's colours.

- [ ] **Step 1: Write failing tests:** `test_plan_without_theme_is_unchanged` (compare to a figure JSON snapshot taken before the change); `test_plan_theme_colours_walls_and_furniture`; JS `planColors legacy matches old palette map` and `pack theme overrides`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement; geometry and labels untouched.
- [ ] **Step 4:** Run; record migrations; expected PASS.
- [ ] **Step 5:** Commit.

### Task 14: Plan ↔ Room sweep

**Files:**
- Create: `frontend/realistic_viewer/src/plan_sweep.js`
- Modify: `room_viewer.js` (toolbar slider), `town/world.js` + `town/index.html` (presentation and room view)
- Test: `frontend/realistic_viewer/tests/plan_sweep.test.js`

**Interfaces:**
- Produces: `createPlanSweep({scene, renderer, root}) -> {set(t: number), dispose()}`. `t = 0` line-drawing: all meshes swapped to a white `MeshBasicMaterial` with `EdgesGeometry` dark lines (threshold 25°); `t = 1` full render; `0 < t < 1`: a vertical clipping plane sweeps along the room's X axis, line-drawing on one side and render on the other (the `room2.jpg` look). Original materials restored on `set(1)` and on `dispose()`. No generation or model call.

- [ ] **Step 1: Write failing tests:** `set(0) swaps every mesh material and adds edges`; `set(1) restores exact original materials`; `dispose restores and frees edge geometry`; `sweep position maps t to room x extent`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement; add a `Plan ↔ Room` range input (`input.sweep`, 0–100) to both viewers.
- [ ] **Step 4:** Run; rebuild bundle; record migrations; expected PASS.
- [ ] **Step 5:** Commit.

## Phase 6 — Acceptance

### Task 15: Acceptance evidence, docs and PR

**Files:**
- Create: `docs/images/style-packs/<pack>/{plan,studio,walkthrough}-{desktop,narrow}.png`
- Modify: `docs/data/STYLE_PACKS_11A.json` (`acceptance`), `docs/developer/TOWN.md`, `docs/developer/3D_STUDIO.md`, `docs/developer/STATUS.md`, `README.md` (pinned docs → record migrations)

- [ ] **Step 1:** For each pack: offline brief naming the style in Town → apply → screenshot plan, presentation and walkthrough (1440×1000, 390×844); Studio offline bedroom with that style → plan and 3D; A/B switch, save/reload and replay keep the style.
- [ ] **Step 2:** Legacy check: open the Task 1 legacy revisions; screenshot-compare to `legacy-before/` (pixel diff ≤1% outside the animated status line). Confirm no `packs/` requests in the network log.
- [ ] **Step 3:** Fault check: block one pack texture (404), corrupt one (hash), block one model → labeled fallback, status names it, layout preserved; unknown style brief → clarification, home unchanged.
- [ ] **Step 4:** Performance: record FPS during a 20 s scripted walk at high tier (desktop) and low tier (390×844 emulation) via `renderer.info` + `requestAnimationFrame` timing; record values in `acceptance`.
- [ ] **Step 5:** Full suites: `npm test`, `npm run check`, Town build, `pytest -q` versus Windows baseline; record results.
- [ ] **Step 6:** Update docs (style packs, quality toggle, sweep, operator setup, asset release). Record migrations. Commit.
- [ ] **Step 7:** Ask the owner before pushing; then open a PR into `main` with side-by-side images (references vs each pack), Blender previews, and the receipt summary.
