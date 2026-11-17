# Chat prompt-variation suite (receipt)

Measures how the chat interpreter handles different ways of asking. Cases come from real bedrooms (room size and furniture) in the P2b pack's `val` split, each written in one of 10 styles with a known correct outcome.

    python -m archimind.datasets prompt-suite --pack E:/archimind-data/p2b/pack --out cases.jsonl --per-style 3
    python -m archimind.datasets prompt-eval --cases cases.jsonl --recordings recordings.jsonl --out report.json --pack E:/archimind-data/p2b/pack --live   # 1 model call per new case
    python -m archimind.datasets prompt-eval --cases cases.jsonl --recordings recordings.jsonl --out report.json          # offline re-score, free

- `--live` needs `ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS=1` and `OPENAI_API_KEY` in the environment. Without it, nothing is sent.
- Recordings keep the model's raw extraction. A re-score sends each one through the **current** application rules, so rule changes can be re-measured without new calls.
- The files for this run are in [prompt_eval/](prompt_eval/): 33 cases, 33 recordings (`gpt-5.4-mini-2026-03-17`, 2026-11-16) and the report for the current rules.

## First result (rules before the fixes): 26 / 30 correct

| Style | Correct | What happened |
|---|---|---|
| Complete metric spec | 3/3 | ready |
| Casual wording | 3/3 | ready |
| Feet | 2/3 | 1 **unsupported**: the model also filed "one king bed" and "one wardrobe" as mandatory constraints, and any mandatory constraint makes the app answer "unsupported" |
| Typos (`bedrom`, `nighstand`, `wadrobe`) | **0/3** | The model extracted the right furniture in all 3, but the app's exact-word evidence checks then asked "Confirm that this is a bedroom" and "Confirm the function of furniture request 2" |
| Real quantities (two nightstands) | 3/3 | clarification naming quantity |
| Missing door / windows / ceiling | 9/9 | clarification naming the missing fact |
| Bed without a size | 3/3 | clarification naming bed size |
| L-shaped room | 3/3 | unsupported |

## What this says to fix (in `agents/catalog_conversation.py`, which has an owner-recorded migration history)

1. **Duplicated furniture in `hard_constraints`.** When a constraint only restates a furniture request already captured as an intent, it should not make the request "unsupported". This mechanism probably also caused the "2 twin beds …" rejection seen in manual testing.
2. **Typo-tolerant evidence checks.** The room-type and function word checks (`FUNCTION_TERMS`) need exact words, so a correct model reading is thrown away. A small edit-distance allowance, or accepting the model's function when the quote names a near spelling, would fix all three typo cases.
3. **Unsupported messages should name the reason.** The model already states it (e.g. "L-shaped bedroom"), but the screen shows only a generic sentence.

Each fix can be checked against these recordings with an offline re-score, at no cost.

## After the fixes: 32 / 33 correct (offline re-score of the same answers, plus 3 new live cases)

Changes:
- `agents/catalog_conversation.py` adds `near_term`. The bedroom and furniture-function evidence checks now accept one keyboard slip (two for words of 8+ letters). Words under 5 letters must still match exactly, so `bad` is never read as `bed`.
- A hard constraint that only restates a requested item (quantity, size, function, e.g. "one king bed", "two twin beds") no longer makes a request unsupported. Real constraints ("bed against the north wall") still do.
- `ui/bedroom_chat.py` lists what made a request unsupported (unsupported features, real mandatory constraints, unsupported room type, shape or furniture), escaped and at most 4 lines. The generic sentence remains only when no reason is known.

| Style | Before | After |
|---|---|---|
| Typos | 0/3 | **2/3** |
| Feet | 2/3 | **3/3** |
| Two twin beds (new, live) | — | **3/3**, a clarification about one instance per item |
| Every other style | 24/24 | 24/24 |

The remaining typo failure is a genuine model error: the model's depth quote ("…bedrom 3.5 m deep…") is not in the user's text, and the evidence check correctly asks again.

The 3 twin-bed answers contained no restated constraints, so a complete twin-bed prompt would also have reached a clarification under the old rules. The "two twin beds …" rejection seen in manual testing is consistent with the restated-constraint pattern from the feet case, but it cannot be confirmed without that response.

Chat regression tests (`test_catalog_conversation`, `test_catalog_chat_failures`, `test_bedroom_chat_ui`, `test_catalog_specifications`, `test_asset_catalog_packaging`): 76 passed with the same single failure as before the change (`test_catalog_in_source_wheel_and_isolated_install`, pre-existing). The new tests are in `tests/test_catalog_conversation_tolerance.py` (8).

Live evaluation requires cases exported with their source and snapshot plus the current verified pack. Each prompt is reconstructed and checked against current provider-disclosure permission before any request. Historical cases remain available for offline replay.
