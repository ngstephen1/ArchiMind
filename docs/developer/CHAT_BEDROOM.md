# Conversational bedroom — Task 09A

The catalog-aware Requirements Interpreter preserves its legacy three-item API.
The Chat bedroom input mode now shares the existing generation/results area.
Choose the mode, submit measurements and answer clarifications.
Choose each product, compatible procedural template or explicit omission, then
Prepare → Review → Generate Layouts. Review the original source quotes and units,
room/openings and each generation reservation before generation. Seed changes
preserve preparation; messages/selections/evidence changes invalidate it. Refresh
catalog choices clears pending choices without another model request. New
conversation clears pending chat only; displayed results remain frozen.

Live acceptance passed in the resumed three-request smoke: one complete desktop
request and a two-turn clarification at 390 × 844. Both reached reviewed,
prepared specifications and two passing seed-42 alternatives, with custom measured
openings, native Belaya and an explicitly accepted queen-bed placeholder.
Desktop acceptance used 1440 × 1000. No extra calls occurred on choices,
preparation, generation, A/B switches or reset. The fixed pinned model was
`gpt-5.4-mini-2026-03-17`; the request budget is exhausted. These samples establish
bounded acceptance, not universal interpretation accuracy or provider availability.
The earlier one-success/two-server-error smoke remains historical evidence.
A separate interpreter/fault fixture verifies no-match, missing-planning evidence
and sanitized provider-failure presentation; it is not additional live acceptance.
See [09A report](../data/CHAT_BEDROOM_09A.md#current-09a-continuation).

Start locally from the repository with the existing environment:

```sh
.venv/bin/python scripts/run_chat.py --port 8502
```

The launcher reads only OPENAI_API_KEY and ARCHIMIND_OPENAI_MODEL from the local,
ignored .env file (existing environment wins), enables the server gate and binds
127.0.0.1. It never evaluates shell expressions or prints credentials. The normal
`streamlit run app.py` path remains disabled unless configured explicitly. Pressing Send authorizes one live request for the submitted conversation. Rotate credentials that
have been pasted into chat; keep .env out of commits and screenshots.

Use `agents.catalog_conversation.interpret_catalog_conversation(turns,
allow_live=False, client_factory=None)` and `assets.chat_specifications`'s
`retrieve_chat_candidates(draft)` and `prepare_chat_specification(draft,
selections=..., procedural_ids=...)`. The latter returns the existing immutable
`PreparedCatalogSpecification` and calls no spatial engine.

Conversation turns have increasing integer IDs, user/assistant roles and bounded
text. Evidence quotes reference exact user turns. Number and unit sources can be
separate clarification turns; Python converts meters/feet. A ready draft requires
a rectangular bedroom, complete dimensions, measured entrance(s) and explicitly
specified windows or no windows. Canonical schemas check opening extents.
Evidence/schema success is not proof of semantic accuracy; review remains required.

Search uses the existing Python lexical provider and generation reservations.
Each `request-N` must be resolved explicitly: `selections` maps requests to current
asset IDs or explicit `None` for omission; `procedural_ids` maps requests to an
existing compatible template. Missing/overlapping choices and duplicate instances
fail closed. Procedural queen beds are never offered for unspecified bed sizes.
No product dimensions, model paths, placements or approvals originate in LLM output.

Charles/Belaya retain their approved Policy B reservations. Other catalog products
remain metadata-only. Mixed detailed scenes remain unqualified. New assets,
semantic encoders, extra agents and generated meshes are outside this task.

Live interpretation requires the existing server flag and exact per-call opt-in.
One submission is one request, no SDK retry/tools, fixed official client,
30-second timeout, 4096 output-token bound and store=false. Conversations are
limited to 20 user turns / 12000 UTF-8 context bytes; no truncation or implicit
context reset. Credentials stay in the server environment, never transcripts.

New conversation clears pending
turns, choices and preparation before widgets render. It submits nothing by
itself. A fresh message is still required for any new request. Variable chat
content has a stable container so pending edits do not move the selected viewer.
Known unsupported bed sizes may be explicitly omitted; they never silently
become the queen template. Unknown bed sizes require clarification.
