# Conversational bedroom — Task 09A

The catalog-aware Requirements Interpreter preserves its legacy three-item API.
Backend checkpoint: evidence contracts, current lexical retrieval and explicit
preparation are implemented. UI/browser/live acceptance belongs to the next
checkpoint; no live model result is claimed here.

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
