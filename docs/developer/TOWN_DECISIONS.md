# Town brief consistency check

Agent A can use the OpenAI Decisions API after it has interpreted an explicit live Town team brief. The original request, supplied controls and proposed brief are compared in a single call. Four predicates look for omitted dining, clearance, preservation and other unsupported requirements. Python still resolves controls, verifies geometry and writes revisions. [API guide](https://developers.openai.com/api/docs/guides/decisions)

| Server mode | Behavior |
| --- | --- |
| `off` (default) | Existing interpretation and generation |
| `shadow` | Records a signal at 0.85 for evaluation. Generation follows the same rules as before. |
| `clarify` | With a qualifying promotion receipt, the first flagged criterion opens the existing clarification path. Invalid or missing receipts select shadow behavior. |

Set `ARCHIMIND_TOWN_DECISIONS_MODE` on the API and worker. When a held-out run qualifies, point `ARCHIMIND_TOWN_DECISIONS_PROMOTION_RECEIPT` at the operator-controlled six-case receipt on both processes. The current public run produced no qualifying threshold. Use shadow for the pilot and keep the held-out cases sealed. Start locally with existing server credentials.

Both calibration and holdout need at least one labeled omission. A six-case promotion receipt must report that coverage for the operator to enable clarification.

```sh
TOWN_DAILY_MODEL_CALLS=12 TOWN_DAILY_MICROUSD=1200000 \
  ARCHIMIND_TOWN_DECISIONS_MODE=shadow .venv/bin/python scripts/run_town.py
```

Every eligible job can reserve one additional call in the same transaction as its ordinary calls. The optional slot is skipped unless enough allowance remains for it and the owner's remaining ordinary team jobs. Both settings in the example leave room for an extra check on each of the three local jobs at the default reservation amount. Reservations of queued or cancelled jobs count for that UTC day. Duplicate job IDs return their existing slot. On a hosted rollout, run the existing database initializer before serving traffic with the new API and worker. The request has a five-second timeout and no retries. A named refusal is reported as unavailable for that question. Bad responses and outages leave the existing checks in charge. Agent A records only named scores, flags, usage, elapsed time and an availability reason.

## Calibration and acceptance

Run the public corpus offline or collect a live receipt with the existing key. The 36 public examples contain 12 replayed briefs from PR #74 and 12 preserved/dropped pairs. Each threshold comparison is derived from the same 36 calls.

```sh
python scripts/evaluate_town_decisions.py
python scripts/evaluate_town_decisions.py --live --output /tmp/town-decisions-public.json
```

| Threshold | Missed omissions | False flags |
| --- | ---: | ---: |
| 0.70 | 4 | 10 |
| 0.75 | 4 | 10 |
| 0.80 | 4 | 9 |
| 0.85 | 4 | 8 |
| 0.90 | 4 | 6 |
| 0.95 | 6 | 5 |

All 36 responses were complete, with 34,356 reported input tokens and 655 ms p95. The independent access probe scored the intentionally dropped dining requirement at 0.94. No threshold met the zero-omission and at-most-one-false-flag gate. The sealed held-out set was not opened. The private replay command requires the passing calibration through `--public-receipt`, its frozen threshold through `--threshold`, and six separately labeled input rows through `--cases`. A held-out brief can have both a preserved draft and a dropped-requirement control. Each brief-and-draft pair must be distinct, and the original brief cannot appear in the public corpus. The archived calibration used reduced drafts without the live reviewed sources, assumptions, and status. Its results do not qualify a production threshold. A promotion evaluation requires a new 36-case public corpus with the same payload shape as Town and a separate six-case holdout. Pass the new corpus through `--public-corpus` and its matching receipt through `--public-receipt`. The public replay includes already rejected drafts as controls. The ordinary worker stops those drafts before spending a model call. Its gate also requires complete responses and p95 at or below three seconds. [Public cases](../data/town-decisions/public-cases.json) · [Live receipt](../data/town-decisions/public-calibration.json)

The deterministic interpreter now retains the six-place single-table wording and asks for clarification with Decisions off. A local desktop Chrome run with recorded model responses exercised the clarification path, the two validated alternatives after a corrected brief, and timeout recovery while revision 1 stayed applied. The browser run made no external model calls. [Browser receipt](../data/town-decisions/browser-receipt.json) · [Clarification](../data/town-decisions/clarification.png) · [Alternatives](../data/town-decisions/alternatives.png) · [Timeout](../data/town-decisions/timeout.png)

To repeat the browser check, build Town in local mode and run `python scripts/check_town_decisions_browser.py --output /tmp/town-decisions-browser` with Playwright and Chrome available.

## Checks for a saved design

**Check request with OpenAI** appears beside Generate layouts when routing is enabled and a saved home is selected. A request can suggest an answer, a revision comparison, an edit, a new design, or a clarification. Known saved-design questions use the existing explanation path without a model call. An advisory answer or comparison offers a separate button to open that explanation. Saved revision comparisons currently cover the bedroom desk chair. Edits and generation still require the existing explicit controls.

**Check evidence with OpenAI** appears after Explain in a saved home’s presentation when evidence review is enabled. One request evaluates up to six statements from the displayed answer against server-calculated facts. The scope covers the current bedroom chair and Belaya footprints, the preceding revision’s chair position and gap, desk-to-window center distances, and saved routes, seating counts and the configured passage check. A passed 0.60 m check does not establish an actual passage width. The reviewer can mark a statement supported, missing evidence, or contradicted. Scores apply to the supplied record. Knee clearance, glare, acoustic privacy and an unrecorded placement rationale still require evidence. Questions about unsupported facts can yield no reliable finding. The original explanation stays visible.

Both checks start off and use independent server settings. Buttons authorize a single call. Shadow runs show availability without suggesting an action or labeling a claim. Configure advisory mode with an operator-controlled receipt matching the model, rubric and both evaluation splits. A missing, stale or failing receipt selects shadow. Starting a tour, opening a presentation, generating a render, or changing views makes no review call. Results that arrive after the selection or draft changes are discarded by the browser.

```sh
TOWN_DAILY_MODEL_CALLS=12 TOWN_DAILY_MICROUSD=1200000 \
  ARCHIMIND_TOWN_DECISIONS_ROUTE_MODE=shadow \
  ARCHIMIND_TOWN_DECISIONS_EVIDENCE_MODE=advisory \
  ARCHIMIND_TOWN_DECISIONS_EVIDENCE_RECEIPT=docs/data/town-decision-reviews/evidence-receipt.json \
  .venv/bin/python scripts/run_town.py
```

Use `ARCHIMIND_TOWN_DECISIONS_ROUTE_RECEIPT` for a future qualifying route receipt. The server also requires the existing live studio flag and OpenAI key. An ordinary startup with nine call reservations leaves no optional slots before three ordinary jobs. Both optional features and the brief check share the same remaining headroom. Cancelled or timed-out reservations count for that UTC day. Hosted operators run the existing database initializer before deploying the updated API, including when both reviews are off. Ordinary live generation reads the same ledger. The server retains a request digest for replay detection and the typed outcomes, usage and duration. It sends the request text and, for evidence checks, the claims and scoped revision facts to OpenAI.

### Independent calibration

| Review | Development and holdout | Holdout result | Status |
| --- | --- | --- | --- |
| Routing | 32 + 16 prompts | 10 of 10 shown correct at 0.40, 62.5% coverage, zero saved questions routed to write, 295 ms p95 | Shadow. Coverage missed the 70% gate. |
| Evidence | 16 + 8 written claims | 8 of 8 correct at 0.30, zero false supported claims, 258 ms p95 | Eligible for opt-in advisory. |

The routing gate is at least 95% precision and 70% coverage with zero accepted saved questions routed to write. Evidence requires at least 80% recognition of all labels and zero false supported claims. Each independently requires complete responses and at most 3 seconds p95. The cutoff is selected using development cases before sending the holdout cases. After correcting the passage field to distinguish a configured check from an actual width, evidence was replayed at the same locked 0.30 cutoff. The held-out claims were unchanged. These are small, locally authored suites. Evidence uses one saved home and its predecessor, with one claim per evaluation request. The browser fixtures also exercise multi-claim presentation and delayed response handling. The separate brief predicate holdout is unchanged. [Route cases](../data/town-decision-reviews/route-cases.json) · [Route receipt](../data/town-decision-reviews/route-receipt.json) · [Evidence cases](../data/town-decision-reviews/evidence-cases.json) · [Evidence receipt](../data/town-decision-reviews/evidence-receipt.json)

```sh
PYTHONPATH=src python scripts/evaluate_town_decision_reviews.py route
PYTHONPATH=src python scripts/evaluate_town_decision_reviews.py evidence
PYTHONPATH=src python scripts/evaluate_town_decision_reviews.py evidence \
  --live --locked-threshold 0.30 --env-file .env --output /tmp/town-evidence-receipt.json
TOWN_MODE=local TOWN_API_URL=/api node frontend/realistic_viewer/town/build.mjs
PYTHONPATH=src python scripts/check_town_decision_reviews.py --output /tmp/town-decision-browser
```

The Chrome check requires Playwright and Chrome, uses recorded response fixtures, and spends no live calls. It checks route shadow, timeout, direct explanation, advisory evidence and an in-flight answer discarded after a draft edit. [Browser receipt](../data/town-decision-reviews/browser-receipt.json)

### Offline render quality experiment

The Score adapter rates window readability, grounding and material separation on three pinned revision-2 Cycles cameras. The offline script verifies source hashes and uses one request per source JPEG and one for its same-camera blurred and washed-out control. The desk view omits window readability. All eight applicable scores were higher on the originals. This experiment distinguishes the originals from deliberately degraded images. It has no independent quality ratings or test against subtle lighting or material regressions. The scores have no role in render approval, geometry, or publishing. [Render receipt](../data/town-decision-reviews/render-receipt.json)

```sh
PYTHONPATH=src python scripts/evaluate_town_render_decisions.py --live \
  --artifacts output/live-design-quality --env-file .env \
  --output /tmp/town-render-decisions.json
```
