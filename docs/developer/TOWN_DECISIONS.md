# Town brief consistency check

Agent A can use the OpenAI Decisions API after it has interpreted an explicit live Town team brief. The original request, supplied controls and proposed brief are compared in a single call. Four predicates look for omitted dining, clearance, preservation and other unsupported requirements. Python still resolves controls, verifies geometry and writes revisions. [API guide](https://developers.openai.com/api/docs/guides/decisions)

| Server mode | Behavior |
| --- | --- |
| `off` (default) | Existing interpretation and generation |
| `shadow` | Records a signal at 0.85 for evaluation. Generation follows the same rules as before. |
| `clarify` | With a qualifying promotion receipt, the first flagged criterion opens the existing clarification path. Invalid or missing receipts select shadow behavior. |

Set `ARCHIMIND_TOWN_DECISIONS_MODE` on the API and worker. When a held-out run qualifies, point `ARCHIMIND_TOWN_DECISIONS_PROMOTION_RECEIPT` at the operator-controlled six-case receipt on both processes. The current public run produced no qualifying threshold. Use shadow for the pilot and keep the held-out cases sealed. Start locally with existing server credentials.

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

All 36 responses were complete, with 34,356 reported input tokens and 655 ms p95. The independent access probe scored the intentionally dropped dining requirement at 0.94. No threshold met the zero-omission and at-most-one-false-flag gate. The sealed held-out set was not opened. The private replay command requires the passing calibration through `--public-receipt`, its frozen threshold through `--threshold`, and six separately labeled input rows through `--cases`. A held-out brief can have both a preserved draft and a dropped-requirement control. Each brief-and-draft pair must be distinct, and the original brief cannot appear in the public corpus. The public replay includes already rejected drafts as controls. The ordinary worker stops those drafts before spending a model call. Its gate also requires complete responses and p95 at or below three seconds. [Public cases](../data/town-decisions/public-cases.json) · [Live receipt](../data/town-decisions/public-calibration.json)

The deterministic interpreter now retains the six-place single-table wording and asks for clarification with Decisions off. A local desktop Chrome run with recorded model responses exercised the clarification path, the two validated alternatives after a corrected brief, and timeout recovery while revision 1 stayed applied. The browser run made no external model calls. [Browser receipt](../data/town-decisions/browser-receipt.json) · [Clarification](../data/town-decisions/clarification.png) · [Alternatives](../data/town-decisions/alternatives.png) · [Timeout](../data/town-decisions/timeout.png)

To repeat the browser check, build Town in local mode and run `python scripts/check_town_decisions_browser.py --output /tmp/town-decisions-browser` with Playwright and Chrome available.
