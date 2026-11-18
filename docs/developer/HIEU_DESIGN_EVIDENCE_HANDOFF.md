# Hieu’s handoff · Explain a saved design

**Owner:** Hieu Quang Ngo. **Reviewed baseline:** `c03ecc2`. **Deliverable:** one Town PR that answers three client questions with evidence from the selected home. Nguyen is producing the fresh home and client book in parallel. Start with fixtures today and use his edited manifest for final acceptance. [Nguyen’s runbook](FRESH_HOME_CLIENT_DEMO.md)

## What already works

[Town’s explanation control](../../frontend/realistic_viewer/town/explanation.js) already reports writing-chair width, the gap between furniture footprints, and the plan distance from desk center to nearest window center. [Agent B](../../src/archimind/town/agents.py) retrieves catalog evidence. The gap is connecting the client’s question to the right object, property, revision, and source. Start at these two entry points and the [existing explanation tests](../../frontend/realistic_viewer/tests/town_explanation.test.js).

## M1 · Establish what each answer can claim

| Client question | Supported answer | When evidence runs out |
|---|---|---|
| Will this chair fit the desk? | Resolve the selected pair. Compare physical chair width to the desk’s measured clear opening. For an armchair, compare arm height with underside clearance. Report the floor-plan gap separately, in metres. | If only external desk width is recorded, say “I need the clear width between the desk supports to confirm that the chair slides underneath.” A reservation or seat height alone cannot settle fit. |
| Why put the desk near this window? | Identify the opening and wall. Report desk-center to window-center distance in plan, with units. Cite a recorded placement rationale if one exists. | Without a rationale, describe the observed placement. Without screen orientation and lighting evidence, leave glare unresolved. If there is no window record, say which measurement is unavailable. |
| Which pieces have an oak finish? | Identify each selected item with an explicit catalog variant or finish. Identify separately any authored oak finish in the saved palette and any available catalog matches outside the room. | Brown appearance supplies no finish evidence. An “Oak” variant supports its label. Solid-oak construction requires its own source. If no finish record matches, say so. |

Create supported, partial, and unsupported fixtures for each row. Include two desks with ambiguous wording, a room with no oak matches, and a missing window. Label synthetic clearances as fixtures. Use the actual reservation and product dimensions for their respective purposes.

## M2 · Connect the answer to its evidence

Build each response from the selected room and design snapshot. Include the answer, project/home and revision identity when saved, selected object IDs, relevant values with units, a source locator, and any missing field. For a geometry calculation, identify its inputs and measurement convention. For a product claim, cite the catalog record, version and field. For an A/B preview, identify the candidate and its preview status. Ask the user to choose an object when identity is ambiguous.

Run with external packs disabled first. An eligible reference may illustrate a precedent; keep its source and permission status attached. A client’s own dimensions, product properties, and the reasons actually recorded for their placement each require their own evidence. Keep Town’s existing retrieval path. The [AI Memory evaluation](AI_MEMORY_EVALUATION.md) found the expected passage on 24/24 answerable questions with local vectors, but returned a passage on all six unsupported questions.

## M3 · Test the ordinary Town workflow and hand back one PR

1. Exercise the three questions through the selected design’s explanation control. Show the source alongside the claim. Reuse current session and selection handling.
2. Switch A to B and inspect the object identities. Apply, reopen, edit the chair, and compare the answers across revisions. Use a separate desk-position fixture to verify that moving the **desk** changes its window distance. Moving only the chair should leave that measurement unchanged.
3. Exercise missing packs, stale references, a missing dimension, and an empty match. Compare the saved design digest and revision before and after asking. Opening an explanation must preserve both.
4. From the checkout root, start with the commands below. Add cases beside the relevant existing tests and run the affected Town tests in your PR.

```sh
node --test frontend/realistic_viewer/tests/town_explanation.test.js
.venv/bin/python -m pytest -q tests/test_town.py
```

**Handback:** Include baseline and tested commit, changed files, commands and results, fixture coverage, and screenshots of one supported answer and one abstention. Once Nguyen supplies the two revisions, edited manifest digest, object IDs, and before/after positions, repeat those two questions against that home. Return the answers, citations, revision and any unresolved claim. This final check ties your PR to the actual client book.
