# Optional AI spatial critique in LangGraph — Task 07D2

The existing [D1 critic](SPATIAL_CRITIC_AGENT.md) now has an optional, independently
traced workflow node. It reviews the selected, deterministically approved
candidate and can support, challenge, request information or abstain. **It never
changes selection, geometry, scores or deterministic reports.** Styling follows
successful advisory review or a safe fallback. Streamlit and renderers are unchanged.

| Mode, when its feature flags are enabled | Path after Requirements → Generation → Deterministic Spatial Critic | Nodes |
| --- | --- | ---: |
| Default | Stylist | 4 |
| Layout Advisor only | Layout Advisor → Stylist | 5 |
| AI Spatial Critic only | AI Spatial Critic → Stylist | 5 |
| Both AI agents | Layout Advisor → AI Spatial Critic → Stylist | 6 |

The node name `spatial_critic` remains the deterministic validator; the advisory
node is `ai_spatial_critic`. Routing uses one conditional outgoing edge mechanism
per routing node, with no mixed static edge that could launch a second path.
There is one generation iteration, a six-node maximum, recursion backstop 8,
and no retry/back edge. Requirements, generation and unsafe-selection failures
terminate before advisory review. The default path invokes neither AI adapter.

## API and independent authorization

```python
from archimind.examples import create_sample_bedroom
from archimind.workflow import DesignRequest, run_workflow

request = DesignRequest(
    specification=create_sample_bedroom(),
    seed=42,
    soft_preferences=[
        "Prefer the desk near the north-facing window while maintaining a spacious room."
    ],
)
default = run_workflow(request)  # four nodes, selected candidate 0
disabled = run_workflow(request, use_ai_critic=True)  # flag defaults off; no API
```

`run_workflow` adds `use_ai_critic=False`, `allow_live_critic=False`, and optional
trusted callable `spatial_critic`. Flags must be actual booleans. Request text
cannot choose a callable. Existing free-text Requirements Interpreter and Layout
Advisor options/gates are unchanged.

A real critic request needs **all three**: `ARCHIMIND_ENABLE_OPENAI_CRITIC=1`,
`use_ai_critic=True` and `allow_live_critic=True`, plus D1's existing validated input,
model/key preflight. Disabled or unrequested critique skips its node and adapter,
including injected callables. The Layout Advisor flag cannot enable the critic,
and the critic flag cannot enable the advisor. With no supported-size preference
list, critique is skipped with an explicit reason.

Trusted offline DI may run without live authorization, while still requiring
workflow opt-in and the feature flag. Successful fixture results must explicitly
say `offline_fixture`, model `None`. An `api_response` result requires the exact
per-call authorization and configured allowlisted model. These are consistency
checks, not a sandbox or cryptographic attestation of injected Python code.

**No live OpenAI or C01 request was made for D2.** D1 retains the fixed client,
30-second timeout, zero retries, bounded I/O, no-tools policy and sanitized provider
errors. No OpenAI adapter, grounding engine or agent was duplicated.

## State, review target and handoff

One additive `SpatialCritiqueState` field, `WorkflowState.spatial_critique`, stores:

| Field | Meaning |
| --- | --- |
| `requested` | Workflow-level critic opt-in |
| `status` | not_requested, pending, disabled, skipped, evaluated, abstained, unavailable, error or rejected |
| `executed` | Adapter was invoked; this does not establish a live request |
| `candidate_index` | Reviewed/attempted target's original generator index |
| `candidate_indices` | D1 packet-local → original generator index map |
| `result` | Existing checked `SpatialCriticResult`, including assessment, stance, observations, limits and typed errors |
| `reason` | Eligibility, abstention or sanitized failure reason |

`selected_candidate_index`, `approved_design` and `selection_source` remain the
selection authority. Critique metadata cannot be used to substitute another
candidate. Old JSON omitting the new metadata receives disabled-by-default
values. Strict external consumers must allow the additive fields.

D1's input contract adds optional `reviewed_candidate_index=None`, preserving
standalone/old JSON behavior. D2 supplies the selected candidate's **local** index.
A normal critique must include measured evidence for that target; alternatives
remain comparison data. Abstention and information requests may explicitly lack
measurable conclusions. A supplied designer recommendation must select that same
target. This field scopes analysis and never grants selection authority.

The node reuses C2's approved-only packet and explicit index map. If only original
candidate 1 passes, D1 receives local candidate 0, and state records map `[1]` and
reviewed original index 1. Original generation data and rejected-candidate reviews
remain visible. Deterministic failures and unknown checks are never relabeled as
passing by the advisory node.

If C2 accepted a recommendation, D2 supplies that exact checked advice and reviews
the resulting selection. If C2 was skipped, abstained, failed or rejected, D2
supplies **no recommendation**, reviews the current deterministic choice and
records `not_provided` stance when appropriate. It never invents advice.

The request includes existing preferences, canonical models, original scores and
reports. Ready interpreted hard-constraint metadata, when present, is passed to
D1 as explicitly unverified constraints. C1/D1 preparation independently screens
the approved packet. The returned context must exactly match, and the workflow
reuses D1 interpretation to require the complete grounded result to match too.
Forged IDs, targets, metrics, geometry, reports, scores, explanations or execution
provenance are rejected. Source models and injected request arguments are copied.

## Outcomes, trace and fallback

| Outcome | Selection/styling behavior |
| --- | --- |
| Supports | Store grounded support; selected candidate stays unchanged; style it |
| Challenges | Store grounded challenge/tradeoff; selected candidate stays unchanged; style it |
| Requests information / abstains | Store actual D1 outcome and limitations; retain approved selection |
| Unavailable, timeout, refusal or error | Store sanitized typed failure/code; retain safe selection |
| Forged/inconsistent output | Metadata status rejected, typed invalid-evidence result; retain safe selection |
| No safe independent selection | Terminate with no approved design or styling |

The critic node only emits metadata and trace updates. It has no selection-update
code path. Fallback retains the current source: an accepted Layout Advisor choice
remains `ai_recommendation`; a deterministic choice remains `deterministic`.
Neither label claims AI spatial approval. Later styling failure still clears the
final selection while preserving critique history for diagnosis.

The selected geometry is freshly checked through the existing accessibility API
before critic invocation and again before continuing to styling. A stale passing
report cannot authorize fallback after in-memory geometry changes. Failed fresh
verification terminates with no selected/approved design; an invocation that
already occurred remains explicitly recorded with a typed invalid-candidates
result. These are read-only calls to the existing engine, not new spatial rules.

Trace events identify deterministic approval and critic eligibility, advisor
recommendation if used, critic invocation/outcome/stance/provenance, reviewed
original index, unchanged final selection/source and styling completion. No fake
AI activity, duplicate node events, raw provider messages or credentials are logged.

## Three-scenario offline demonstration

```bash
python -m archimind.examples.critiqued_workflow
python -m archimind.examples.critiqued_workflow --json
```

This reuses the existing C1 mock and the factored D1 mock on supplied candidates,
with explicit offline provenance. Clients are always mocks; workflow-level live
authorization stays false. No live CLI option exists, and fixture settings are
restored. Each fresh graph run independently generates the same seed-42 bedroom;
neither advisor nor critic regenerates a layout.

| Scenario | Selection | Original score | Critic | Nodes |
| --- | --- | ---: | --- | ---: |
| A | A / index 0 | 67.721925 | Not invoked | 4 |
| B | B / index 1 | 67.614973 | Supports measured desk/window proximity | 6 |
| C | B / index 1 | 67.614973 | Challenges the score/space tradeoff | 6 |

B's desk/window planar gap is **0 m** versus A's **2.532114 m**. A retains score
**67.721925** and usable-space ratio **0.596524064171** versus B's **67.614973** and
**0.595187165775**. The challenge is grounded in those actual disadvantages; it
does not manufacture a hard violation or switch candidates. Assertions check
identical generation/candidate geometry/scores/reviews, input immutability and
lossless state JSON across all three scenarios.

## Verification and limits

See [status](STATUS.md) for exact local and checkpoint results. Tests use real
LangGraph and geometry with mocked adapters/clients and blocked networking. They
cover all four paths and node counts, independent opt-ins/flags, actual D1 mock
API success/timeout, support/challenge/abstention/information requests, sanitization,
forged output and missing candidates, filtered indices, no selection changes,
legacy JSON, free-text interpretation, concurrency, bounds and actual CLI output.

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
python -m archimind.examples.critiqued_workflow
```

Live model quality/account availability is unverified. D1's limited preference
vocabulary and planar geometry assumptions still apply; no actual daylight,
ergonomics, furniture usability or code certification is established. There is no
UI integration, persistence, revision loop or automatic furniture modification.
Task 07E1 now provides the standalone [Interior Stylist](INTERIOR_STYLIST_AGENT.md),
without changing this graph's fixture styling. Recommended next: **Task 07E2 —
Optional Interior Stylist workflow integration**, preserving selected canonical
geometry and deterministic approval. D2 stops at advisory integration.
