# Photoreal style packs for plan, 3D room and walkthrough

Date: 2026-11-17 · Branch: `feat/new-feature` · Status: draft for owner approval

## Intent

ArchiMind users see every design three ways: the **blueprint** (2D plan), the
**3D room** (Studio orbit view, Town presentation) and the **walkthrough**
(Town first-person). Today all three look like diagrams: flat light, primitive
furniture, a colour swap for "style". The owner wants all three to reach the
level of `ref/room1.jpg` (bright modern-classic apartment) and `ref/room2.jpg`
(industrial loft shown half as line drawing, half as finished room), in the
**style the user asks for**.

The original `ref/prompt.md` workflow (Codex designs furniture in Blender,
the same asset appears in Town and Studio, Rhino produces CAD) is the
production line for the custom pieces this needs. Its first instance, the oak
writing chair, is already implemented in open PR #21.

## Goals

1. **Instant, near-photoreal views.** Every view looks good as soon as it is
   shown and while moving. No waiting for renders.
2. **Five style packs**, selected from the user's brief: `modern_classic`
   (room1), `industrial_loft` (room2), `scandinavian`, `japandi`,
   `mid_century`. A pack defines surfaces, furniture, decor, lighting mood and
   2D-plan look as one checked unit.
3. **One design, three consistent views.** The plan, 3D room and walkthrough
   show the same furniture, positions, materials and style.
4. **Blueprint-to-room transition** in the room2 manner: the 3D view can sweep
   between a line-drawing state and the finished render, making it visible
   that plan and room are the same design.
5. **Designer furniture pipeline in real use.** PR #21's chair pipeline
   (Codex → Blender MCP → reviewed release → Town/Studio) is generalised from
   "one chair" to "a designer piece of any supported category", and is used to
   author each pack's signature pieces.

## Non-goals

- Server-side or on-demand offline rendering of user layouts (no render
  server, no GPU host, no cloud renderer; consistent with `prompt.md`).
- Open-ended styles. Free-text style requests map to the nearest of the five
  packs; unrecognised styles get a clarification, not an improvised look.
- New room types, room shapes, multi-storey homes, or changes to the layout
  engine's placement and spatial checks.
- Live Rhino editing. Rhino stays as PR #21 left it: `.3dm` archives via
  rhino3dm, desktop Rhino MCP verification pending a licence.
- Product/building certification; changes to the qualified ABO catalog
  contract.

## Anti-goals (failure even if it "works")

- Any view requires a model call, desktop app or network round trip to a
  third-party host to display. Viewing, switching A/B, walking and replaying
  stay local.
- Rooms that mix pieces from different styles or visibly mismatched quality
  (one photoscanned sofa next to grey boxes).
- Any shipped asset without a recorded licence, source URL and hash.
- Previously saved revisions change appearance after this ships.
- Phones become unusable (frozen, blank, or crashing tabs).
- Decor that breaks the validated circulation or overlaps furniture.

## Constraints

- **Renderer:** Three.js pinned at `0.187.0`, bundled locally (no CDN at
  runtime). Any post-processing library is pinned and bundled the same way,
  with its licence added to `THIRD_PARTY_NOTICES.txt`.
- **Asset budgets** (`src/archimind/assets/inspection.py`): ≤15 MB per GLB,
  ≤100k triangles per asset, ≤300k instantiated triangles per scene, ≤50 MB
  unique encoded scene bytes, textures ≤2048 px. Packs must fit these at the
  high tier, not raise them.
- **Hosting:** the Town is a Vercel static bundle; Studio is Streamlit with a
  Components viewer. Asset files ship with each bundle and are verified by
  SHA-256 in the browser as the Belaya desk and PR #21 chairs already are.
- **Licences:** CC0 sources (Poly Haven, ambientCG) or Blender-authored
  originals only. Each file gets a release record (source, licence, upstream
  checksum, local SHA-256, dimensions, budget results).
- **Offline-first briefs:** the deterministic interpreter must understand style
  requests without OpenAI; the live interpreter is optional and only returns a
  pack ID from the fixed enum.
- **Existing revisions:** saved Town revisions store `palette` ∈
  {oak, sage, terracotta}. Those keep rendering exactly as today (legacy
  path). Only new revisions carry a style pack.
- **Operator tools:** Blender 5.1+ with Blender Lab's MCP server must be
  installed on this Windows laptop (not present today; 365 GB free). Codex CLI
  and uv are installed. The builder acts as operator (see Owner decisions).

## Approaches considered

### How realism is delivered
| Option | Trade-off | Decision |
|---|---|---|
| **Instant real-time quality** in the browser (environment lighting, soft shadows, ambient occlusion, PBR materials, real furniture, decor) | Close to, not equal to, an offline render; improves all three views | **Chosen** |
| Offline Blender renders per layout | Matches the references for one still view; minutes per image, needs a render server, conflicts with `prompt.md`, doesn't help the walkthrough or plan | Rejected for user layouts. Allowed only as optional pre-rendered hero stills for the packaged showcase home |

### Where furniture, decor and materials come from
| Option | Trade-off | Decision |
|---|---|---|
| **A. CC0 libraries** (Poly Haven, ambientCG) | Excellent surfaces and lighting; furniture coverage per style is thin | **Chosen, combined with B** |
| **B. Codex + Blender authored** (PR #21 pipeline) | Owned, exact, consistent; slower; simple shapes need material work to look real | **Chosen for each pack's signature pieces and gaps in A** |
| C. Better procedural geometry in code | No asset files; never reaches reference realism | Fallback/filler only (existing procedural pieces remain the labeled fallback) |

The owner picked A + B.

## Design

### 1. Start from PR #21
Merge `origin/feat/blender-designer-chair` into `feat/new-feature` first. Its
designer registry (`designer_registry.json`, `assets/designer_concepts.py`),
release script and Town/Studio integration become the base for all
Blender-authored pieces. Generalise "designer chair" to "designer piece" with
a `category` field (chair, armchair, sofa, bed, table, desk, storage, lamp,
decor); the chair stays the first entry.

### 2. Style pack contract
A versioned, typed (Pydantic) registry, one JSON file per pack, e.g.
`src/archimind/style_packs/modern_classic.json`:

- `id`, `version`, `name`, `aliases` (phrases that select it: "modern
  classic", "parisian", "elegant"; "industrial", "loft", "new york loft"; …)
- `surfaces`: floor, wall, ceiling, trim/moulding, door, window frame →
  material IDs (with tiling scale)
- `furniture`: for each supported category, an ordered list of asset IDs
  (CC0 model or designer piece) with their measured footprints; the first that
  fits the layout's reservation is used; otherwise the procedural fallback is
  used and labeled
- `decor`: rules, not fixed placements: rug under bed/sofa group, art on the
  largest free wall span, plant in a free corner, pendant over table/centre,
  curtains on windows, wall mouldings on/off
- `lighting`: environment map ID, sun direction/intensity/colour temperature,
  exposure, interior fill lights
- `plan_theme`: 2D plan colours, wall fill, furniture symbol style
- `quality`: per-tier texture resolution and decor density

The five packs (initial direction):

| Pack | Surfaces | Signature pieces | Lighting |
|---|---|---|---|
| modern_classic | dark herringbone oak, pale grey panelled walls, white mouldings, brass | green velvet tub armchair, low sofa, globe-cluster pendant | soft daylight, tall windows |
| industrial_loft | polished concrete, white brick, black steel | metal-frame chairs, slim grey sofa, dome pendant, track spots | cool bright daylight, big glazing |
| scandinavian | pale ash/oak boards, white walls, wool | oak writing chair (PR #21), light sofa, paper pendant | soft overcast |
| japandi | light oak, warm plaster, linen, dark accents | low platform bed, low table, paper lantern | warm low sun |
| mid_century | walnut, warm white, mustard/teal textiles | walnut lounge chair, sideboard, tripod lamp | warm afternoon |

The existing stylist theme catalog (`agents/interior_stylist_catalog.py`)
stays untouched for its Streamlit flow. Its palette colours may seed the
packs' colours.

### 3. Asset library and release
- Materials and environment maps from Poly Haven / ambientCG at 1k
  (low tier) and 2k (high tier), stored in the repo next to existing viewer
  assets, each with a release record and a `THIRD_PARTY_NOTICES` entry.
- CC0 models go through the existing qualification path (native scale,
  floor contact, budgets, hash) the Belaya desk used.
- Blender-authored pieces follow PR #21: Codex drives Blender through the MCP
  server, the operator reviews previews, the release script writes `.blend`,
  `.glb`, two previews and the manifest. Rhino archives stay optional per
  piece (chair already has one).
- A pack is "released" only when every asset it references is released and a
  sample room in that pack passes the scene budget.

### 4. Brief → style pack
- **Town:** the deterministic interpreter gains style clauses built from the
  pack aliases ("industrial loft", "make it japandi"). Agent E resolves the
  pack instead of a palette. The live interpreter's output enum gains the five
  pack IDs. An unrecognised style yields a clarification listing the five.
  Combining a style with a priority and a lock works as palettes do today.
- **Studio:** the brief and recipe flow carries the pack ID; the room is
  furnished from the pack. AI recipes may still propose concepts, but
  rendering prefers pack assets for matching categories.
- **Saved revisions** record `style_pack: {id, version}`. Revisions with only
  `palette` render through the legacy path, unchanged.
- **Snapshots** (Studio download, Town presentation) include pack ID/version
  and asset hashes.

### 5. Shared rendering module
One module in `frontend/realistic_viewer/src/` used by the Studio room viewer,
the Town world and the standalone viewer, so all 3D views share the look:
- environment-map lighting per pack (replacing the generic `RoomEnvironment`)
- soft shadows tuned per tier; ambient occlusion via a pinned post-processing
  pass on the high tier
- PBR materials from the pack, with colour-correct tone mapping
- decor placement from pack rules (below)
- **Quality tiers:** `high` (desktop) and `low` (narrow/mobile or weak GPU:
  1k textures, no AO pass, smaller shadow maps, reduced decor). Auto-selected,
  with a visible toggle.

### 6. Decor placement
Decor is placed after the layout engine approves a candidate and never changes
the approved furniture. Flat items (rugs, wall art, curtains, mouldings,
ceiling pendants) don't occupy circulation and only need to avoid openings and
overlapping each other. Floor-standing decor (plants, floor lamps) is placed
only in free spots that pass the same containment/collision/clearance checks,
or skipped. Placement is seeded by the layout seed, so A/B and reloads are
reproducible.

### 7. Blueprint and plan-to-room transition
- The Plotly 2D plan (`render/floorplan_2d.py`) adopts the pack's
  `plan_theme`. Geometry and labels stay as they are.
- The 3D views get a **Plan ↔ Room** control: a sweep that moves between a
  line-drawing state (white surfaces, dark edge lines, top-down/plan-like
  camera) and the full render, as in `room2.jpg`. It is a pure view change
  (no generation, no model call).

### 8. Order of work
1. Merge PR #21; generalise designer chair → designer piece.
2. Shared rendering module and quality tiers, proven on the existing showcase
   home with one pack (`scandinavian`, since its chair exists).
3. Style pack contract, brief mapping, revision/snapshot recording, legacy
   palette path.
4. Asset library and release for all five packs (CC0 first, then Blender
   signature pieces).
5. Decor placement.
6. Blueprint theming and the Plan ↔ Room transition.

## Acceptance

- For each pack, screenshots of the plan, the Studio 3D room and the Town
  walkthrough (desktop 1440×1000 and narrow 390×844), included in the PR
  next to `room1.jpg`/`room2.jpg` for owner judgement.
- A brief naming each style (offline interpreter) produces that pack in all
  three views of the same revision; A/B, save/reload and replay keep it.
- An unrecognised style produces a clarification; the saved home is unchanged.
- Legacy revisions (oak/sage/terracotta) look identical to before
  (screenshot comparison).
- Every shipped asset has a release record and passes budgets; a scene per
  pack passes the scene budget at both tiers. Missing file and hash mismatch
  produce a labeled fallback, as today.
- Walkthrough stays smooth on this laptop at the high tier and usable in
  narrow Chrome emulation at the low tier.
- Existing Python and frontend test suites pass; new tests cover the pack
  contract, alias mapping, legacy path, decor placement rules and tier
  selection.

## Owner decisions after review

- **Blender operator:** the builder (Claude) may install Blender 5.1+ and the
  Blender Lab MCP add-on on this laptop, author pieces through Codex, and
  review/approve them without per-piece owner sign-off. The owner reviews
  results in the PR (previews and screenshots included there).
- **Kitchens and bathrooms:** counters, vanities and baths get the pack's
  surfaces (worktop, tile, metal finishes) on cleaner procedural shapes. Full
  furniture/model effort goes to the bedroom, living room and study. This is
  not considered "mixed quality" for the anti-goal.

## Calls made after review (owner may override)

- **No style named → default pack.** A new brief that names no style gets
  `scandinavian`. The finish words `oak`, `sage`, `terracotta` stay accepted
  and map to the nearest pack (oak → scandinavian, sage → japandi,
  terracotta → mid_century). Only revisions saved before this ships use the
  legacy palette path. The packaged showcase switches to a pack as a new
  showcase version; tests pinned to the old showcase are updated deliberately.
- **Style is per home, not per room.** A room lock keeps the room's
  geometry, openings and furniture positions. The room is re-dressed in the
  home's current pack (models, materials, decor), so one home never mixes
  styles. Today's palette already applies to the whole home.
- **Town's canvas plan is in scope.** The pack's `plan_theme` applies to both
  the Plotly plan (Studio, editor) and Town's canvas plans (`town/app.js`
  `floorPlan`: main, draft and board).
- **Asset storage: plain git, lazy per pack, size-capped.** No Git LFS
  (repo is 20 MB; LFS adds quota and Vercel setup costs). Textures ship as
  compressed WebP/JPEG at 1k (low) and 2k (high, where it shows). The browser
  loads only the active pack's assets. Cap: ≤25 MB of new files per pack,
  ≤120 MB for all five. Exceeding the cap means dropping a 2k map or a model,
  not raising the cap.
- **Accent furniture.** Pack pieces the layout engine has no slot for
  (armchairs, sideboards, floor lamps) are "accent furniture". They are placed
  after layout approval in free space that passes the same containment,
  collision and clearance checks, or skipped. They never move approved
  furniture.

## Left to the builder

- Exact asset choices within each pack's direction, texture sizes per tier,
  and which pieces are CC0 versus Blender-authored.
- Choice of ambient-occlusion/post-processing implementation (pinned, bundled,
  licence-recorded).
- File layout of the pack registry and asset folders.
- The exact visual treatment of the Plan ↔ Room sweep.
- Frame-rate targets and how they are measured.
