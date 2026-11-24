# November 24 held-out live evaluation

Held-out evaluation for [#68](https://github.com/ngstephen1/ArchiMind/issues/68), run against Town at
[`301762b`](https://github.com/ngstephen1/ArchiMind/commit/301762b72aac1a537b06e38db1d69dbecdbff42e)
with `gpt-5.4-mini-2026-03-17`. The sealed packet (SHA-256
`966f99271ba19c1b2f99d6a9106f781bee919124c165df80169e4ad8dfe369a6`) was verified before
opening. Its prompts, answer key, full receipts and saved-design answers stay with the
evaluation owner until the candidate freeze. This folder publishes only case IDs, the
public slot names from the [baseline package](../nov24-baseline/README.md#twelve-public-acceptance-briefs),
outcomes, scores, calls, latency, hashes and the commit.

**Scoring status: provisional.** The agent proposed the scores below. Hieu reviews each
row against the sealed answer key and assigns the final severity and reviewer before sign-off.

[Matrix](matrix.md) · [Machine-readable receipt](matrix.json)

## Result

On this commit the run does **not** meet the sign-off bar of five expected outcomes out
of six. Two cases pass, two are partial and two fail. No case invented a measurement or
changed a saved snapshot. Each saved-revision case compared equal before and after.

| Case | Slot | Outcome | Calls | Elapsed |
| --- | --- | --- | --- | --- |
| H01 | Hosting and home-office trade-offs | Fail | 2 | 5.19 s |
| H02 | Conflicting seating needing confirmation | Partial | 2 | 4.05 s |
| H03 | Width conversion and circulation | Pass | 3 | 11.83 s |
| H04 | Room lock and targeted saved-revision change | Fail | 2 | 4.76 s |
| H05 | Two plausible referents in a follow-up | Pass | 0 | browser, immediate |
| H06 | Conclusion needing site, supplier or acoustic evidence | Partial | 0 | browser, immediate |

## Triage

| Case | Observed behavior (general) | Component | Severity |
| --- | --- | --- | --- |
| H01 | The interpreter listed a request to compare two supported priorities as an unsupported requirement, so no candidates were produced. Fixed salon seating guidance was appended although the brief made no seating request; it was triggered by the kitchen-dining room name. | Brief interpretation, `clarification_guidance` | High |
| H02 | Stopped correctly before candidates and asked about the table arrangement. The stated seat count was absent from the reviewed requirements and the four-place salon limit was not explained. | Brief review | Medium |
| H04 | A single-room furniture edit returned a clarification about conflicting room-distance preferences that the request did not contain. The interpreter also locked the room being edited. Revision 1 was preserved. | Brief interpretation, lock handling | High |
| H06 | Correctly withheld the fit conclusion and asked for the measured clearances. It omitted the acoustic part of the question, did not state supplier availability as unknown and labeled the chair by the wrong room. | Saved-design explanation | Medium |

Fixes are developed against the public fixtures only. After a fix, rerun only the affected
rows and keep these receipts.

## Run conditions

- Local Town on a dedicated SQLite evaluation database with providers enabled and the
  Codex advisor disabled. Each design job reserves three bounded OpenAI calls.
- Calls are counted as one bounded call per recorded OpenAI phase in the worker.
  Elapsed time runs from job submission to the terminal status and includes polling at 0.75 s.
- The harness submits each case's packet controls directly to the local API. The ordinary
  Town form instead derives the seed from the revision and always requests comparison.
- H04–H06 start from a zero-call base: seed 178, 15 × 15 m lot, formal salon, candidate A,
  applied as revision 1. The default 13 × 13 m lot cannot hold the six-room program.
- H05 and H06 were asked through **Ask about the saved design** in Chrome at a
  1536 × 748 CSS viewport. That path is computed in the browser and makes no provider calls.
- Two unrelated jobs were submitted through the Town page on the same evaluation database
  before H01. They used four calls and are excluded from the case totals. Thirteen calls
  were used in all.

## Reproduce

Keep the packet outside Git, for example in the ignored `storage/` directory.

```sh
python scripts/held_out_eval.py setup --packet storage/held-out-briefs.json \
  --sha256 966f99271ba19c1b2f99d6a9106f781bee919124c165df80169e4ad8dfe369a6
TOWN_DB=storage/eval-68/town-eval.sqlite3 TOWN_PORT=8890 TOWN_EDITOR_PORT=8891 \
  ARCHIMIND_ENABLE_CODEX_ADVISOR=0 python scripts/run_town.py --extra-team-jobs-on YYYY-MM-DD
python scripts/held_out_eval.py run H01 --packet storage/held-out-briefs.json --confirm-live
python scripts/held_out_eval.py record H05 --answer-file answer.txt --viewport 1536x748
python scripts/held_out_eval.py matrix --output docs/data/nov24-held-out/matrix.md
```

Local mode allows five team jobs per UTC day with the extra-jobs flag. A rerun keeps the
original receipt and writes a separate timestamped file.
