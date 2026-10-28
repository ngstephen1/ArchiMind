# Standalone AI Interior Stylist — Task 07E1

The optional `recommend_style` adapter plans colors and finish representations for
one existing, spatially approved `LayoutCandidate`. Its output is **separate
metadata**: it cannot move furniture, change dimensions/openings, select another
candidate, revise scores/reports or improve verified circulation. LangGraph routing,
the deterministic Stylist fixture, Streamlit and both renderers are unchanged.
Workflow integration belongs to Task 07E2.

## Contracts and API

```python
from archimind.agents.interior_stylist_agent import recommend_style
from archimind.agents.interior_stylist_schemas import InteriorStylistRequest
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates

design = create_sample_bedroom()
selected = generate_layout_candidates(
    design.room, design.furniture, seed=42
).candidates[0]
request = InteriorStylistRequest(
    candidate=selected,
    style_request=(
        "Scandinavian bedroom with warm white walls, light oak furniture, "
        "and muted sage accents."
    ),
)
result = recommend_style(request)  # unavailable/disabled; no client or API call
```

The input carries one caller-selected candidate's canonical `RoomDesign`, complete
deterministic report and original heuristic score. There is no candidate-selection
API. It also accepts 0–8 soft preferences and optional checked
`SpatialCriticResult` feedback. No separate geometry or material-performance model
is invented. Missing main style details return explicit clarification without a
client invocation after input verification, rather than a fabricated neutral plan.

Before any authorized model request, Python revalidates/copies the input, reruns
the existing accessibility API at zero overlap tolerance, compares the entire
report and verifies the original score using the existing score helper. Invalid,
unsupported, stale or unverified layouts cannot be labeled approved for styling.
Optional critique is rechecked with D1's preparation/interpretation and must
contain the exact selected candidate; an explicit critique target must match it.
Local critique indices are resolved by candidate data, not guessed global aliases.

`InteriorStyleProposal` is a strict, closed Pydantic Structured Outputs contract:

- `style` or `request_clarification`, one nullable theme/palette pair and wall/floor
  token selections, furniture finish selections and at most three distinct accents.
- Furniture entries use existing IDs exactly once. Python converts the list to
  the result's furniture-ID-keyed mapping after validation.
- Controlled rationale/conflict codes and one subjective assessment per preference.
  Index 0 denotes the main style request; indices 1–8 denote additional preferences.
- No arbitrary model-generated color values, paths, URLs, HTML, CSS, JavaScript,
  architectural measurements, material performance text or geometry fields.

`InteriorStylistResult` reports `styled`, `needs_clarification`, `unavailable` or
`error`, with provenance, checked context/proposal and an optional `InteriorStylePlan`.
The plan contains resolved wall/floor/furniture finishes, accents, a Python-rendered
explanation, preference notes, conflicts, unmet indices, assumptions and limitations.
`rendered` is always false. Failed/clarification results cannot present a plan.
Results preserve the complete candidate snapshot and round-trip through JSON.

## Catalog and rendering boundary

Catalog `archimind_style_v1` uses frozen records, immutable lookup maps and tuple
allowlists. It has **five themes/palettes, 15 material representations and six
accent colors**. Themes, palettes, surface roles and allowed combinations are
checked after parsing; a valid token from another palette/surface is still rejected.

| Theme ID | Palette ID | Curated appearance choices |
| --- | --- | --- |
| `scandinavian` | `scandi_warm_sage` | Warm white/soft gray walls; light oak/pale ash floor; light oak, white or linen furniture; sage/taupe/charcoal accents |
| `modern` | `modern_slate_blue` | White/gray walls; ash/concrete floor; walnut, white, dark metal or gray fabric furniture; blue/charcoal/taupe accents |
| `minimalist` | `minimalist_white` | White walls; ash/oak floor; white, oak or dark metal furniture; charcoal/taupe/sage accents |
| `industrial` | `industrial_charcoal` | Gray/charcoal walls; concrete floor; walnut, dark metal or gray fabric furniture; terracotta/charcoal/ochre accents |
| `neutral` | `neutral_sand` | Warm white/sand walls; stone/oak floor; oak, linen, walnut or white furniture; taupe/sage/terracotta accents |

The 15 tokens cover five wall colors, four floor appearances and six furniture
finish categories. Color hex values come exclusively from Python catalog records.
Each record exposes `future_mapping="flat_color_metadata"` and
`physical_asset_available=False`. These tokens could support a future color mapping;
neither Plotly nor Three.js mapping is implemented. No texture/asset URL or file is
present, downloaded or selected. Wood/metal/fabric/stone names describe appearance
only, not a verified physical product, component construction or performance.

One finish token is selected per furniture object; no component material map,
actual texture, PBR finish, procurement specification or photorealistic output is
provided. Accent colors have no placement or new-object semantics.

## Preference conflicts and unsupported claims

Preference notes are explicitly subjective, never certified satisfaction. Named
catalog themes guide the selected main theme. Multiple named themes require an
explicit compromise/conflict disclosure or clarification. An unselected named
theme cannot be marked fully favored. The small phrase checks also reject fully
favored/undisclosed choices contradicting `warm white walls`, `light oak furniture`
or `muted sage accents`. This is conservative screening, not general language
understanding; unknown intent requires human review.

Performance, durability, fire/safety, acoustic/thermal, sustainability, daylight,
ergonomic and spatial-improvement requests must remain unverified. Such preferences
produce explicit limitations; styling cannot recertify geometry or claim improved
circulation. Clarification requires null/empty style choices and unverified
assessments, with reasons such as mixed themes, unavailable material or missing
details. No unavailable model output is replaced with a fixture.

## API gates and failure handling

`ARCHIMIND_ENABLE_OPENAI_STYLIST=0` is the default. Live use requires the exact
feature flag value `1`, exact per-call `allow_live_usage=True`, bounded valid input,
an existing allowlisted model and API key. Other agents' flags cannot enable it.
Environment files are not loaded automatically; credentials are never logged.

The adapter reuses the existing SDK **3.40.0** client, fixed endpoint, model
allowlist/default and provider error conventions. It uses Responses/Pydantic
Structured Outputs following the [official OpenAI pattern](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
and verified installed SDK behavior. No new client wrapper or dependency was added.

| Boundary | Limit/policy |
| --- | --- |
| Input/context | Each at most 65,536 UTF-8 bytes; 32 furniture, 16 openings; furniture IDs at most 100 characters |
| Preferences | Main request and up to eight soft preferences, each at most 400 characters |
| Proposal | One main theme, compatible palette and finishes, at most three accents |
| Response | 4,096 output tokens and 131,072-byte application limit |
| Request | One invocation, 30-second timeout, zero automatic retries |
| Tools/storage | No tools, `store=False`, `background=False`; no shell/filesystem/web capabilities |
| Client | Existing fixed OpenAI endpoint, redirects/environment proxies disabled |

The SDK buffers/parses before the response-byte check; it is not a streaming memory
cap. The timeout follows existing SDK/request behavior, not a separate process
deadline. Trusted test/application `client_factory` injection is never selected by
user design text. Typed sanitized failures cover disabled/unauthorized operation,
authentication/model preflight, invalid layouts/critique, oversized data, timeout,
rate/connection/API failures, refusals, incomplete/missing/malformed output and
invalid catalog/furniture/preference selections. Raw provider/exception messages
and credentials are excluded. There are no automatic retries or fake fallback plans.

## Executed offline demonstration

```bash
python -m archimind.examples.style_bedroom
python -m archimind.examples.style_bedroom --json
```

This uses the existing canonical **5 × 4 × 2.7 m** bedroom and seed 42. The unchanged
default graph independently approves and selects Layout A/index 0, original score
**67.721925**. Outside the graph, a fixed mocked client supplies only catalog IDs:

| Selection | Token | Catalog color |
| --- | --- | --- |
| Theme / palette | `scandinavian` / `scandi_warm_sage` | — |
| Walls | `wall_warm_white` | `#F5F1E8` |
| Floor | `floor_light_oak` | `#D4B58C` |
| Desk, queen bed and wardrobe | Each `finish_light_oak` | `#CDB18A` |
| Accent | `muted_sage` | `#9BAE98` |

The explanation coordinates those verified catalog entries; the preference note
is a subjective appearance interpretation. Assertions compare the full candidate,
RoomDesign, coordinates, dimensions, room/openings, score, report, selected index
and workflow JSON before/after. Existing fixture styling and four-node routing
remain unchanged. Provenance is `offline_fixture`, model `None`; fixture settings
are restored. Clients are always mocked, with no live CLI option.

## Verification and next task

See [project status](STATUS.md) for exact execution and checkpoint records. Tests
block networking and mock clients, including actual SDK mock-HTTP parsing. They
cover all themes, immutable catalog compatibility, ID coverage, injection/unknown
IDs, conflicts, unsupported claims, invalid layouts, gates/errors, size limits,
immutability/JSON, Requirements/Layout/Critic compatibility and actual demo CLI.
Packaging is checked as a source archive and wheel, with an installed-wheel mock
demo outside the repository.

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pytest -q
python -m pip check
python -m ruff check .
python -m ruff format --check .
python scripts/check_health.py
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer run build
python -m archimind.examples.style_bedroom
python -m build --no-isolation
```

**No live OpenAI or C01 request was made.** Live style quality/account availability,
general intent matching, physical assets, performance and visual material rendering
remain unverified/unimplemented. Existing single-room/zero-rotation spatial limits
still apply. Recommend **Task 07E2 — optional Interior Stylist workflow integration**,
preserving selected geometry and deterministic approval. Stop at standalone E1.
