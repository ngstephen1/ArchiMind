# Standalone AI Spatial Design Critic — Task 07D1

`critique_design` provides evidence-grounded, advisory feedback on existing
validated alternatives. It can support or challenge a designer's recommendation,
identify preference tradeoffs, request information or abstain. **It cannot approve
geometry, select a replacement candidate or change any design data.** The existing
deterministic Spatial Critic remains authoritative. [Task 07D2](SPATIAL_CRITIC_WORKFLOW.md)
now optionally invokes this adapter in LangGraph; default routing stays unchanged.
Streamlit and renderers do not invoke this agent.

| Component | Responsibility |
| --- | --- |
| Layout Designer (C1/C2) | Propose an existing candidate against preferences; C2 can apply an approved selection |
| Deterministic Spatial Critic | Recompute actual containment, overlap, doorway and circulation checks; approve or reject |
| AI Spatial Design Critic (D1) | Explain measured advantages and disadvantages; question weak weighting; disclose missing evidence |

The model is not instructed to disagree for appearance. A challenge must cite an
actual measured advantage of another candidate under a specific proxy. It remains
a qualitative weighting judgment, not a hard spatial violation or safety finding.

## API and contracts

```python
from archimind.agents.layout_schemas import LayoutAdviceRequest
from archimind.agents.spatial_critic_agent import critique_design
from archimind.agents.spatial_critic_schemas import SpatialCriticRequest
from archimind.examples import create_sample_bedroom
from archimind.geometry import generate_layout_candidates

design = create_sample_bedroom()
layout = LayoutAdviceRequest(
    specification=design,
    generation=generate_layout_candidates(design.room, design.furniture, seed=42),
    soft_preferences=[
        "Prefer the desk near the north-facing window while maintaining a spacious room."
    ],
)
request = SpatialCriticRequest(layout=layout)
result = critique_design(request)  # unavailable/disabled; no client or API request
```

`SpatialCriticRequest` embeds the existing C1 packet: canonical `RoomDesign`,
generator candidates with positions/dimensions, reports, scores and preferences.
It also accepts up to eight `explicit_constraints` and an optional checked
`LayoutAdviceResult`. Additional hard constraints are retained and reported as
**unverified**, rather than silently converted into new geometry rules.

D2 adds optional `reviewed_candidate_index=None` to focus analysis on an existing
packet-local candidate. The default preserves D1 inputs/old JSON. A normal critique
must include evidence for the target; abstention/information requests may lack
measurable conclusions. Any designer recommendation must select the same target.
This field does not change candidate selection or spatial approval.

The optional recommendation must describe the exact supplied packet/preferences,
have explicit provenance and equal C1's canonical grounded interpretation. An
abstained recommendation can be acknowledged but cannot be supported/challenged.
Failed advice is not a recommendation. Provenance fields are consistency checks,
not cryptographic proof of model execution. Candidate IDs `candidate-0/1` refer
to the supplied packet's indices; furniture IDs remain canonical object IDs.

`SpatialCriticProposal` is the model's closed Structured Outputs schema:

- Decision: `critique`, `request_information` or `abstain`.
- At most three observations, each with a controlled category, existing candidate
  indices, furniture IDs, evidence refs and a checked comparison relation.
- Exactly one preference assessment per preference, linked to observation indices:
  `partial_support`, `tradeoff`, `conflict` or `unverified`.
- Recommendation stance: `supports`, `challenges`, `cannot_evaluate` or
  `not_provided`, with supporting observation indices when evaluated.

There are **no model-authored numeric measurements, coordinates, scores, factual
free-text explanations or safety-severity fields**. Python renders all prose and
values after checking the proposal. `SpatialCriticResult` includes context,
assessment, grounded observations, preference feedback, stance/explanation,
unverified-constraint indices, unsupported claims, limitations and typed errors.
`advisory_only` is always true. Execution status is `evaluated`, `abstained`,
`no_candidates`, `unavailable` or `error`; `evaluated` never means spatial approval.
`request_information` is an evaluated response with missing-evidence observations.

All contracts use strict Pydantic types, forbidden extra fields and instance
revalidation. Results round-trip through `model_dump_json` /
`SpatialCriticResult.model_validate_json` without losing information.

## Evidence and grounding

`prepare_critic_context` reuses **C1 `prepare_layout_context`** to copy inputs,
check fixed specification fields, independently recompute complete accessibility
reports at zero overlap tolerance, and compute opening gaps and usable-space facts.
Every supplied report must exactly match a fresh passing report. Failed, forged,
unverified or unsupported geometry never reaches the model. Original heuristic
scores are verified against the existing generator's score helper, without
generating another layout or replacing the stored score.

Additional Python facts use existing Shapely furniture/room footprints to measure
each furniture footprint's planar distance to each of the four wall segments.
Scoped check-state refs expose the existing containment, overlap, doorway and
circulation results. Original reports, including advisory warnings, are preserved.

| Category | Permitted evidence |
| --- | --- |
| `window_proximity` | C1 furniture-to-window planar footprint gap |
| `wall_proximity` | Furniture footprint to the named interior wall segment |
| `entrance_separation` | C1 furniture-to-door planar footprint gap, not required clearance |
| `usable_center_space` | Existing usable occupant-center area or score ratio |
| `heuristic_score` | Existing verified score, unchanged |
| `spatial_validation` | Existing scoped check states; passing permits advisory warnings |
| `missing_evidence` | Controlled information topics, with no asserted objects or measurements |

Single numeric observations use `reported`. Comparisons require exactly two facts
for the same kind/object/opening/wall from different candidates. Candidate order,
furniture IDs and `less`/`greater`/`equal` must exactly match those facts. Unknown,
duplicated, cross-object or inconsistent refs are rejected. The public grounding
function recomputes the context again, rejecting caller-forged feature values.

Support/challenge requires a genuine comparative advantage under the cited proxy:
smaller window/wall gaps or larger entrance separation, usable space or score.
Equal values, reported measurements and passed checks alone cannot justify a
stance. Other tradeoffs remain visible; this does not prove the candidate is best.
Preference tradeoffs require different categories favoring different candidates.

Preference matching is deliberately conservative keyword screening, **not general
language understanding**. Known window/wall/entrance/space/score topics can receive
subjective proxy assessments. Unknown intent and explicit daylight, ergonomics,
safety, usability or code-certification requests remain unverified. If all requested
judgments lack supported topics, a critique is rejected: the model must abstain
or request information. Mixed unsupported claims remain unverified. Abstention
cannot assert observations or support/challenge the recommendation.

## API gates, limits and failures

The new flag defaults to `ARCHIMIND_ENABLE_OPENAI_CRITIC=0`. A real request needs
that flag set to `1`, exact per-call `allow_live_usage=True`, valid bounded input,
an existing allowlisted `ARCHIMIND_OPENAI_MODEL` and `OPENAI_API_KEY`.
Requirements/layout flags cannot enable the critic. No credentials or environment
files are read automatically. C01 authentication remains separate.

The adapter reuses the existing SDK **3.40.0**, model allowlist/default and fixed
client configuration. No new dependency or API wrapper framework was added.
The Responses/Pydantic parsing and refusal handling follow
[official OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses),
checked against the installed SDK. No model migration was performed.

| Boundary | Limit/policy |
| --- | --- |
| Input/context | Each at most 65,536 UTF-8 bytes; 1–8 preferences, 0–8 additional constraints |
| Geometry | Up to 2 candidates, 32 furniture objects, 16 door/window openings; inherited zero-rotation support |
| Model output | At most 3 observations, 8 refs per observation, 4 named furniture IDs; closed rationale categories |
| Response | 4,096 output tokens; 131,072-byte application response limit |
| Request | One invocation, 30-second timeout, zero automatic retries |
| Capabilities | `tools=[]`, `tool_choice=none`, no web/shell/filesystem tools |
| Client | Existing fixed OpenAI endpoint; environment proxies and redirects disabled |
| Storage | `store=False`, `background=False`; no workflow persistence |

Size checks happen before client construction for input/context. The SDK buffers
and parses responses before the application's byte check; this is not a streaming
transport memory cap. The timeout follows existing SDK/request behavior rather
than a separate process wall-clock deadline. Trusted `client_factory` DI exists
only for application/tests, never from design text.

Typed sanitized failures cover disabled/unauthorized execution, missing/bad
authentication, unsupported model, malformed input, invalid candidates or
recommendation, oversized input/output, timeout, rate/connection/API errors,
refusal, incomplete/missing/malformed output and inconsistent evidence. No error
contains raw provider text, exception text or API keys. No retries or fabricated
fallback critiques are used. Missing candidates return explicit non-evaluation.

## Offline demonstration

```bash
python -m archimind.examples.critique_layout
python -m archimind.examples.critique_layout --json
```

The example uses the unchanged default graph to obtain the canonical 5 × 4 m
bedroom, seed 42, two independently approved candidates and selection A. **Outside
the graph**, it reuses C1's existing mocked advisor to propose B, then invokes the
critic with a mocked client. There is no live mode; fixture settings are restored.

| Verified fact | A | B |
| --- | ---: | ---: |
| Desk to north-window planar gap | 2.532114 m | 0 m |
| Original heuristic score | 67.721925 | 67.614973 |
| Usable occupant-center-space ratio | 0.596524064171 | 0.595187165775 |
| Independent spatial checks | Passed | Passed |

The mock critic supports B under measured window proximity, while flagging the
score/space tradeoff. It explicitly leaves actual daylight, ergonomics, desk
usability, code compliance and complete preference satisfaction unverified.
The independent challenge test instead weighs A's actual score/space advantage;
neither output changes geometry, reports or selection. Default workflow selection
stays **A/index 0**, and the designer's advisory proposal stays **B/index 1**.
Result provenance is `offline_fixture`, model `None`; this is not live quality
evidence. Assertions verify canonical data and JSON round-trips.

## Verification and next task

See [project status](STATUS.md) for exact executed results and checkpoint records.
Tests block network attempts, use actual deterministic geometry, and exercise the
real SDK with mock HTTP as well as mocked provider failures. They cover support
and challenge, invalid evidence/IDs, forged scores/reports/recommendations,
unsupported judgments, abstention/information requests, gates and limits,
immutability/serialization, Requirements/Layout compatibility, unchanged graph
behavior, and actual offline CLI execution.

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pip check
python -m ruff check .
python -m ruff format --check .
python scripts/check_health.py
npm --prefix frontend/realistic_viewer test
npm --prefix frontend/realistic_viewer run check
npm --prefix frontend/realistic_viewer run build
python -m archimind.examples.critique_layout
```

**No live OpenAI or Codex request was made.** Live quality/account availability,
general intent interpretation, functional furniture access, vertical geometry,
actual daylight/ergonomics and certification remain unverified. Existing spatial
approximations and small candidate/rationale sets still apply. The optional
[D2 workflow route](SPATIAL_CRITIC_WORKFLOW.md) is now implemented with deterministic
approval and explicit usage gates. Recommend **Task 07E — Interior Stylist agent**.
No revision loop is implemented. Verification counts above record D1.
