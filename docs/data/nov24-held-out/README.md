# November 24 held-out live evaluation

Held-out evaluation for [#68](https://github.com/ngstephen1/ArchiMind/issues/68), run against Town at
[`301762b`](https://github.com/ngstephen1/ArchiMind/commit/301762b72aac1a537b06e38db1d69dbecdbff42e)
with `gpt-5.4-mini-2026-03-17`. The sealed packet (SHA-256
`966f99271ba19c1b2f99d6a9106f781bee919124c165df80169e4ad8dfe369a6`) was verified before
opening. Its prompts, answer key, full receipts and saved-design answers stay with the
evaluation owner until the candidate freeze. This folder publishes only run IDs, the
public slot names from the [baseline package](../nov24-baseline/README.md#twelve-public-acceptance-briefs),
outcomes, scores, OpenAI phases, latency, hashes and commits.

**Scoring status: provisional.** The agent proposed the scores below. Hieu reviews each
row against the sealed answer key and assigns the final severity and reviewer before sign-off.

[Matrix](matrix.md) · [Machine-readable receipt](matrix.json)

## Result

On this commit the run does **not** meet the sign-off bar of five expected outcomes out
of six. Two cases pass, two are partial and two fail. No case invented a measurement or
changed a saved snapshot. H04's revision 1 compared equal before and after its job. H05
and H06 were asked in the browser. Their revision 1 was later read back through the API
and still matched the recorded base, with no jobs on either project.

| Case | Slot | Outcome | OpenAI phases | Elapsed |
| --- | --- | --- | --- | --- |
| H01 | Hosting and home-office trade-offs | Fail | 2 | 5.19 s |
| H02 | Conflicting seating needing confirmation | Partial | 2 (1 request) | 4.05 s |
| H03 | Width conversion and circulation | Pass | 3 | 11.83 s |
| H04 | Room lock and targeted saved-revision change | Fail | 2 | 4.76 s |
| H05 | Two plausible referents in a follow-up | Pass | 0 | browser, immediate |
| H06 | Conclusion needing site, supplier or acoustic evidence | Partial | 0 | browser, immediate |

## November 25 rerun of the affected rows

H01, H02 and H04 were rerun live on November 25, 2026 UTC against
[`45871da`](https://github.com/ngstephen1/ArchiMind/commit/45871daed9d71a57bc76c29768ef436562091fad).
That commit is the `eval/nov25-held-out-rerun` integration branch: main plus
[#91](https://github.com/ngstephen1/ArchiMind/pull/91),
[#111](https://github.com/ngstephen1/ArchiMind/pull/111) and
[#112](https://github.com/ngstephen1/ArchiMind/pull/112). The runs used the same packet,
the same evaluation database, the same model and the same harness. The original receipts
and rows are kept. H03, H05 and H06 were not rerun.

| Run | Outcome | OpenAI phases | Elapsed | Independent check |
| --- | --- | --- | --- | --- |
| H01 rerun | Pass | 3 | 12.36 s | Both six-room candidates pass `validate_home`. Both requested room-center distances were recomputed from the room origins and matched the recorded evidence. One candidate is better on both measures. |
| H02 rerun | Pass | 2 | 7.33 s | No candidates. The question keeps the stated party size at one table, states the four-place table limit and the conflict with the split-dining control, and does not accept a two-table total. |
| H04 rerun | Pass | 3 | 7.66 s | The revised home passes `validate_home`. The bedroom room, openings, furniture and origin are identical to revision 1, and no other room changed besides the study. The desk-to-window center distance fell from 4.445 m to 0.875 m. Revision 1 compared equal before and after the job. |

With the reruns in place of their originals, five of six rows pass and H06 remains partial.
This mixes two commits: H03, H05 and H06 were observed on `301762b`. The scores are still
provisional.

Observations for review:

- H02's clarification also says that the five-room program has no modeled table in the
  formal salon. The case's controls do not enable the salon, so the statement is
  accurate, but it repeats the four-place point as a second question.
- H01's styling direction suggests "quieter and more absorptive" study materials. It is
  a finish suggestion. It does not claim sound isolation or a measured acoustic result.
- The run plan's `home_sha256` for the H04 base does not equal the digest of the stored
  revision 1. The receipt's before-and-after comparison reads the same stored revision
  through the API, and those two digests match.
- The H06 source-accuracy defect (wrong room label, acoustic and supplier gaps) is not
  addressed by these branches.

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
- The OpenAI phase count is an upper bound on provider requests. The worker logs a phase
  before it runs, and Town's deterministic review can stop interpretation before the
  request is sent. That happened in H02, which made one request (styling). Elapsed time
  runs from job submission to the terminal status and includes polling at 0.75 s.
- The harness submits each case's packet controls directly to the local API. The ordinary
  Town form instead derives the seed from the revision and always requests comparison.
- H04–H06 start from a zero-call base: seed 178, 15 × 15 m lot, formal salon, candidate A,
  applied as revision 1. The default 13 × 13 m lot cannot hold the six-room program.
- H05 and H06 were asked through **Ask about the saved design** in Chrome at a
  1536 × 748 CSS viewport. That path is computed in the browser and makes no provider calls.
- Two unrelated jobs were submitted through the Town page on the same evaluation database
  before H01. They started four OpenAI phases and are excluded from the case totals. All
  jobs together started thirteen phases, at most twelve provider requests.
- These runs predate the `serve` command. Their model was read from `.env`, which matches
  the launcher's resolution because no shell override was set.

## Reproduce

Keep the packet outside Git, for example in the ignored `storage/` directory.

```sh
python scripts/held_out_eval.py setup --packet storage/held-out-briefs.json \
  --sha256 966f99271ba19c1b2f99d6a9106f781bee919124c165df80169e4ad8dfe369a6
# In a separate terminal. Records the checkout commit and the model the worker uses.
python scripts/held_out_eval.py serve --extra-team-jobs-on YYYY-MM-DD
python scripts/held_out_eval.py run H01 --packet storage/held-out-briefs.json --confirm-live
python scripts/held_out_eval.py record H05 --answer-file answer.txt --viewport 1536x748
# Score every run in storage/eval-68/scores.json, keyed by run ID (H01, H01-rerun-<UTC time>-<suffix>).
python scripts/held_out_eval.py matrix --output docs/data/nov24-held-out/matrix.md
```

`scores.json` maps each run ID to `outcome`, the five axis scores, `severity` and
`reviewer`. A `_status` entry describes the scoring state. `run` and `record` refuse to
start when Town was launched from a different commit than the checkout. Neither replaces
an original receipt. `--rerun` writes a separate timestamped run with its own matrix row
and score. Local mode allows five team jobs per UTC day with the extra-jobs flag.
