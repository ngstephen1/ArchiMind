# Chat prompt-variation suite (receipt)

Measures how the chat interpreter handles different ways of asking. Cases come from real bedrooms (room size and furniture) in the P2b pack's `val` split, each written in one of 10 styles with a known correct outcome.

    python -m archimind.datasets prompt-suite --pack E:/archimind-data/p2b/pack --out cases.jsonl --per-style 3
    python -m archimind.datasets prompt-eval --cases cases.jsonl --recordings recordings.jsonl --out report.json --live   # 1 model call per new case
    python -m archimind.datasets prompt-eval --cases cases.jsonl --recordings recordings.jsonl --out report.json          # offline re-score, free

- `--live` needs `ARCHIMIND_ENABLE_OPENAI_REQUIREMENTS=1` and `OPENAI_API_KEY` in the environment. Without it, nothing is sent.
- Recordings keep the model's raw extraction. A re-score sends each one through the **current** application rules, so rule changes can be re-measured without new calls.
- The files for this run are in [prompt_eval/](prompt_eval/): 30 cases, 30 recordings (`gpt-5.4-mini-2026-03-17`, 2026-11-16) and the report.

## Result: 26 / 30 correct

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
