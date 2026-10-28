# Standalone Layout Designer advice — Task 07C1

This optional adapter compares **existing generator candidates** against soft
preferences and proposes an index or explicitly abstains. It never generates
positions, changes geometry/scores/reports, applies a selection, or approves a
design. The optional [Task 07C2 workflow handoff](LAYOUT_WORKFLOW.md) now reuses it
after independent critique to select an approved candidate. The adapter itself
still returns advice only; the default graph skips it entirely.
No live OpenAI request was made; all model-response verification uses mocks.

## Contracts and API

```python
from archimind.agents.layout_agent import recommend_layout
from archimind.agents.layout_schemas import LayoutAdviceRequest
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates

specification = create_sample_bedroom()
generation = generate_layout_candidates(specification.room, specification.furniture)
request = LayoutAdviceRequest(
    specification=specification,
    generation=generation,
    soft_preferences=["Prefer the desk near the north-wall window."],
)
result = recommend_layout(request)  # unavailable by default; no API request
```

| Contract | Contents |
| --- | --- |
| `LayoutAdviceRequest` | Canonical `RoomDesign`, existing `LayoutGenerationResult`, 1–8 soft preferences of at most 400 characters each |
| `LayoutAdviceContext` | Deep-copied request and deterministic measured-feature records |
| `LayoutProposal` | Model decision, nullable zero-based index, controlled rationale code, evidence refs, one subjective assessment per preference, limitation codes |
| `MeasuredFeature` | Python-generated reference, candidate/object/opening identity, feature kind, finite value and unit |
| `LayoutAdviceResult` | recommended/abstained/no_candidates/unavailable/error, checked proposal, original context, application-rendered rationale, measurements, subjective tradeoffs/unmet preference indices, limitations and typed error |

All models are strict, closed Pydantic contracts with JSON round-trip support.
Structured Outputs fields are required and nullable where appropriate. The model
has **no coordinate, dimension, score, numerical measurement or free-form rationale
field**. It selects rationale codes and existing feature refs; Python renders the
explanation. This deliberate restriction prevents model-written measurements
from being accepted as facts while keeping qualitative selection advisory.
For API shape see the [OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

## Read-only screening and grounding

`prepare_layout_context` revalidates/copies input, requires candidate room and
furniture identities/dimensions to match the specification, and calls the existing
accessibility API at zero overlap tolerance for **every** candidate. A report must
be fully passing and match the supplied report. Any invalid/unverified/forged
candidate rejects the request before a model call; indices are never filtered or
renumbered. No generation or scoring API is called by the adapter. Screening is
an input-integrity check, not the final Spatial Critic approval.

Python supplies these facts:

- Original heuristic total and usable-center-space ratio from the generator.
- Usable occupant-center area from the existing circulation report.
- Shortest Euclidean **floorplan footprint-to-opening-segment gap**, using existing
  Shapely furniture footprints and canonical door/window segments on all four walls.

Coordinates remain meters, X east/Y north from the southwest corner. Window/door
offset conventions are unchanged. Planar gaps ignore sill/elevation, furniture
function and orientation beyond existing zero-rotation support. A 0 m gap means
the 2D projections touch; it is not a daylight, ergonomic, reachability, door-swing
or minimum-passage-clearance finding. No certification is claimed.

Each model evidence ref must exist and belong to the proposed candidate. Python
includes the corresponding facts for every supplied candidate, preventing a
model from supplying its own comparison values. Measured rationale codes require:

| Rationale | Required factual relation |
| --- | --- |
| window_proximity | Smallest cited furniture/window gap among supplied candidates |
| entrance_separation | Largest cited furniture/door gap among supplied candidates |
| usable_center_space | Largest supplied usable-center-space ratio |
| preference_balance | Subjective balance; no optimal metric claim |

Out-of-range indices, nonexistent refs, wrong candidate refs, incompatible fact
types, contradictory metric rankings and incomplete/duplicate preference indices
are rejected. A lower-scoring preference choice retains the original scores and
explicitly reports the score tradeoff. Assessments remain subjective and do not
certify preference satisfaction. Common daylight/ergonomic/certification phrases
must have `uncertain` assessments; keyword screening cannot prove arbitrary intent
or recognize every paraphrase. Closed rationale codes cannot assert those findings.

Abstention requires no candidate/evidence, an insufficient-evidence/no-clear-choice
reason and uncertain preference assessments. No candidates returns `no_candidates`
without contacting a model. `requires_spatial_critic=True` is always explicit.

## API gates and limits

`ARCHIMIND_ENABLE_OPENAI_LAYOUT` defaults to **0**. Both value **1** and exact
per-call `allow_live=True` are necessary, including with a test client factory.
Requirements interpretation's feature flag does not enable layout advice.
`OPENAI_API_KEY` must be present; Codex CLI login is unrelated. No .env file is
loaded automatically. Missing credentials or disabled advice never produces a
fabricated recommendation.

The adapter reuses 07B's model allowlist, `ARCHIMIND_OPENAI_MODEL`, pinned OpenAI
SDK 3.40.0 and client constructor. Default: `gpt-5.4-mini-2026-03-17`. No dependency
or shared client behavior changed. This retains the fixed official endpoint,
30-second network timeout, zero retries, disabled redirects/environment proxies,
`tools=[]`, `tool_choice="none"`, `store=False` and `background=False`.

Input and expanded context each have a **65,536-byte** limit. Work is bounded to
two candidates, 32 requested furniture objects and 16 room openings. Output is
limited to **4,096 tokens** and a **131,072-byte** serialized response. The SDK
buffers/parses before the application output-byte check; this is not a streaming
memory quota. `store=False` does not establish zero provider retention.

User preferences and object labels are untrusted data in one user message; fixed
application instructions are supplied separately. No external tools, web searches,
shell/filesystem operations or persistent store are exposed. Typed, sanitized
errors handle API/authentication/rate/connection/timeout failures, refusals,
incomplete/missing/malformed output, invalid selections and size limits. Raw
provider errors and credentials are not logged or included in error results.

## Actual offline demonstration

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m archimind.examples.advise_layout
python -m archimind.examples.advise_layout --json
```

The CLI always uses a mock client, scopes/restores fixture settings, marks results
`offline_fixture` and has no live mode. It generates the real 5 × 4 m bedroom's two
alternatives, constructs a grounded mock response, and asserts that the original
designs and validation reports remain unchanged. This is not model-quality evidence
and is never used as a fallback for unavailable API advice.

Actual result: **recommended candidate 1 (Layout B)** for north-wall window
proximity. Computed desk-to-window planar gaps: candidate 0 **2.532114 m** and
candidate 1 **0.000000 m**. Their unchanged scores are **67.721925** and
**67.614973**, respectively. The explanation reports that the proposed candidate
has the lower heuristic score and separates measured facts from the subjective
preference judgment. Independent Spatial Critic approval is still required.

Verification: **773 passed in 31.03s**, preserving all 708 prior Python tests and
adding 65 focused cases; all **27 frontend tests passed**. Ruff lint/format,
dependency check, frontend syntax/build and Streamlit HTTP **200 ok** health check
passed. Committed bundles remained unchanged. Tests block network attempts and
cover real SDK mock-HTTP parsing, geometry grounding on four walls, selection and
abstention, invalid/unverified candidates, gates/errors, immutability, reproducible
mock output, existing Requirements Interpreter compatibility and actual CLI JSON.

Known limits: no live account/model-quality verification, no new layout search,
small candidate set, limited rationale vocabulary, subjective preference matching,
zero rotation, inherited planar spatial approximations, no daylight/ergonomic or
building-code certification. See [Task 07C2](LAYOUT_WORKFLOW.md) for the separately
gated graph integration and current verification results; counts above record C1.
