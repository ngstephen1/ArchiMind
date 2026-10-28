# Optional OpenAI Requirements Interpreter — Task 07B

Only the Requirements Interpreter has an optional model-backed path. Layout
Designer, Spatial Critic and Interior Stylist retain their existing deterministic
algorithms. There is no new UI, renderer, asset, dataset, geometry algorithm,
persistence, revision loop or C01 integration. **No live model request was made.**
The demonstrated interpretation is a clearly labeled offline fixture.

## API and supported models

The official Python SDK is pinned to **openai 3.40.0**, tested on Python 3.11.13
with Pydantic 2.14.1. It uses `client.responses.parse(...,
text_format=RequirementsSchema)` and the returned `output_parsed`, following the
[OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
All extraction fields are required, nullable when unknown; nested objects forbid
extra properties. Actual SDK schema serialization and response parsing are tested
with an in-process HTTP mock, including refusal/incomplete/malformed responses.

Default model: **gpt-5.4-mini-2026-03-17**. `ARCHIMIND_OPENAI_MODEL` may also select
`gpt-5.4-mini` or `gpt-6-astra`. Their Responses/Structured Outputs support was
verified in official OpenAI documentation on October 27, 2026:
[GPT-5.4 Mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra).
Other identifiers fail locally with `unsupported_model`; the allowlist needs
maintenance as model availability changes. Account access/authentication and live
extraction quality are unverified. No model-list or other account request is made.

## Contracts and conversion

| Contract | Meaning |
| --- | --- |
| `RequirementsSchema` | Untrusted extraction: room type/shape, original measurements, furniture keys/quantities/explicit dimensions, openings, style, hard/soft preferences, missing/ambiguous information, assumptions and unsupported features |
| `LengthEvidence` | Finite original number, `m` or `ft`, exact source-text quote; conversion is performed by Python |
| `FurnitureRequirement` | Catalog key, source quote, quantity, optional explicit dimensions; no model-generated IDs or arbitrary categories |
| `OpeningRequirement` / `WindowRequirement` | Wall, offset, dimensions, and window sill height, with source evidence; unknown values remain null |
| `Preference` | Text plus supporting source quote; metadata cannot execute instructions |
| `RequirementsResult` | `ready`, `needs_clarification`, `unsupported`, `unavailable` or `error`; extraction, optional canonical `RoomDesign`, questions, assumptions, limitations, typed error, source mode and model |

`prepare_requirements` revalidates extraction, verifies source substrings and
numeric/unit evidence, then constructs the **existing canonical models**.
It does not duplicate spatial algorithms or assert placement validity.
Only rectangular bedrooms and simple studios are supported. Missing/ambiguous
room type/shape, width/depth/ceiling or entrance information needs clarification.
Door/window positions and dimensions are never filled from catalog defaults.
Opening extents must pass the existing wall-endpoint and ceiling checks.
Mentioned windows omitted from extraction trigger clarification; genuinely
unspecified windows remain unmodeled with a disclosed assumption.

The furniture catalog is derived from the unchanged sample bedroom:

| Catalog key | Canonical category | Default width × depth × height (m) |
| --- | --- | --- |
| `queen_bed` | bed | 1.6 × 2.0 × 0.6 |
| `desk` | desk | 1.2 × 0.6 × 0.75 |
| `wardrobe` | storage | 1.5 × 0.6 × 2.0 |

These are demonstration dimensions, not arbitrary model-generated values or
product specifications. Every omitted furniture dimension that uses a default
appears in assumptions. Explicit dimensions require matching source evidence.
An unspecified bed size uses `unknown_bed` and needs clarification; unsupported
objects stop with `unsupported`. Each furniture entry permits 1–8 instances,
with at most 32 total. IDs are assigned deterministically by Python, such as
`desk-1`/`desk-2`; canonical room/opening IDs are also assigned locally.
X/Y begins at (0,0), explicitly labeled **unplaced**, for replacement by the
existing generator. Rotation remains zero. No layout is approved at extraction.

Measurements remain in canonical meters, X east/Y north/Z up from the southwest
origin. Decimal Python conversion uses **1 ft = 0.3048 m**; the original numeric
value/unit remains in extraction. Supported numeric evidence includes `5 m`,
`5m`, `16 ft`, feet/foot and foot marks. Written-out lengths, fractions and complex
mixed feet/inches are outside the demonstrated scope and need clarification.

Style and soft preferences, such as “Scandinavian” or “desk near the window”,
remain metadata and appear in the trace. The current generator does not enforce
them, and the Stylist still produces its original deterministic fixture metadata.
Additional hard constraints stop as unsupported because silent non-enforcement
would be incorrect. Revise those requirements explicitly before generation.

## Gates and workflow compatibility

`interpret_requirements(description, allow_live=False)` requires both:

- `ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS=1` in the process environment.
- Exact per-call `allow_live=True` authorization.

It additionally requires a verified model identifier and `OPENAI_API_KEY` from
the environment. `.env` is not loaded automatically. Codex CLI login is unrelated
to API authentication. Default flag value is **0**, and `.env.example` keeps it 0.
No client is constructed before gates/configuration/input checks pass.

`run_workflow` preserves 07A behavior by default. Canonical structured requests
always bypass the interpreter, even if API flags/authorization are supplied.
Original prose remains metadata unless `interpret_free_text=True` is explicitly
selected. The new mode forwards `allow_live_requirements` to the API adapter;
without authorization or availability it returns a clear `unavailable` state.

The state adds only `interpretation` and the needed terminal/error literals;
canonical models and `DesignRequest` fields are unchanged. A ready result is
reconverted at the handoff and must match its canonical specification. Agent
mode, assumptions and retained style/preference information appear in the first
trace entry. Clarification/unsupported/unavailable/error outcomes stop before
generation. A successful handoff follows the existing four-node bounded graph,
with one generation iteration and independent zero-tolerance spatial critique.

Trusted callable dependency injection supports offline tests/demonstrations.
It is application code, not a capability exposed through user descriptions.
The built-in API adapter always enforces both live gates, including with an
injected client factory. LangGraph remote tracing remains disabled.

## Bounded requests and failures

One Responses request, no automatic SDK retries, 30-second network timeout,
12,000 input UTF-8 bytes and 4,096 output tokens. Parsed response serialization
is capped at 131,072 bytes. The SDK buffers/parses the HTTP response before the
application byte check; this is not a streaming transport/memory quota. The
workflow's existing prose field also limits input to 4,000 characters.

Fixed developer-authored instructions are separate from the untrusted user
message. There are no user-supplied system instructions, tools, web searches,
function calls, code execution or file access. Requests use `tools=[]`,
`tool_choice="none"`, `store=False`, `background=False`, a fixed official API
endpoint, disabled redirects/environment proxies and zero retries. `store=False`
does not establish zero provider retention; normal account data controls apply.

Typed sanitized failures cover disabled/unauthorized/missing credentials,
unsupported model, invalid/oversized input, timeout, authentication, rate limit,
connection/API failure, refusal, incomplete response, missing parsed output,
schema failure and oversized output. Raw provider errors, credentials and
environment contents are not included in results or logged by the adapter.

Schema and evidence checks cannot prove intent or stop every semantic prompt
injection: a model can misread negation, select the wrong source number or omit
constraints. This remains a limited prototype requiring evaluation before live
use. The tests establish deterministic conversion and failure behavior, not
real-model extraction accuracy or architectural compliance.

## Offline demonstration and checks

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m archimind.examples.interpret_bedroom
python -m archimind.examples.interpret_bedroom --json
```

The CLI has no live mode. A fixed mock client returns the fully specified sample
request's extraction; temporary fixture-only settings/key are scoped and restored.
The result is marked `offline_fixture` with no claimed live model. It is never
used as fallback when the real adapter is unavailable.

Actual output summary:

```text
Task 07B OFFLINE MOCK — no live OpenAI request
Interpretation: ready (offline_fixture)
Workflow: succeeded
Generation: 2 candidates; 9/500 attempts
Selected candidate: 0 (zero-based)
```

Verification: **708 passed in 29.14s**, retaining all 631 prior Python tests plus
63 adapter/conversion and 14 workflow integration cases. All **27 frontend tests**
passed; syntax/build, pip compatibility, Ruff lint/format, editable
installation and Streamlit HTTP **200 ok** health checks passed. Bundles and the
other three node algorithms were checked unchanged.
Wheel contents and dependency metadata include the agent modules and both example
modules; the documented offline output summary was checked against execution.

The first trace records canonical conversion and every catalog assumption;
remaining decisions are Layout Designer **generated**, Spatial Critic **approved**,
and Interior Stylist **styled** with `deterministic_fixture` metadata.
The full `--json` output reconstructs `WorkflowState` without information loss.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pip check
python -m ruff check .
python -m ruff format --check .
python scripts/check_health.py
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer run build
```

Task 07C1 now adds separate [Layout Designer advice](LAYOUT_AGENT.md).
No other LLM-powered workflow role is integrated into the graph yet.
Recommended next: **Task 07C2 — LangGraph Layout Designer integration**.
