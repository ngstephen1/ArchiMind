# Dataset integration teammate handoff

This is the November 5, 2026 engineering handoff for a separate dataset-reference
workstream. It covers SSR-3DFRONT, MIDI-3D/3D-FRONT and 3D-FUTURE in seven bounded
milestones, with Claude prompts, proposed interfaces, tests and delivery gates.

- [10-page PDF handbook](ArchiMind_Dataset_Teammate_Handoff.pdf)
- [Matching Markdown for copying into Claude](ArchiMind_Dataset_Teammate_Handoff.md)

Start with the kickoff on page 10, then execute the M0 prompt on page 3. The
teammate owns isolated data modules and tests first; app/chatbot wiring is a
separate integration PR after the owner supplies a reviewed 09A checkpoint.

## Snapshot and status boundaries

The implementation baseline is `4dc5c026cafdfec23cc0924b6bcca62ece0f29f7`.
The handbook intentionally records the state at handoff, rather than claiming
its future milestones are implemented.

- The catalog has five metadata-qualified ABO products. Charles and Belaya have
  individual approved native releases; mixed Charles/Belaya scenes remain
  placeholders.
- The owner's 09A UI and later fixes remain separate, unfinished local work.
  Publishing this handoff does not release those changes or complete live
  conversation-to-layout acceptance.
- These three datasets have no runtime integration at the handoff baseline.
  Public-use permissions, selective access, normalization, retrieval and preview
  qualification remain implementation gates. A mirror listing is not permission.
- The feature is read-only reference retrieval and explanation. It does not train
  a model, generate new 3D assets, alter product selection or replace deterministic
  generation and spatial validation.

## Document verification

The PDF and Markdown contain matching document text. All 10 rendered pages were
visually inspected; all 188 text blocks and eight complete prompt blocks were
checked through PDF extraction. The PDF has 10 clickable reference targets.
These are document checks, not dataset or application acceptance results.

Verified SHA-256 values:

```text
PDF  fa541024d0290698d3c787e17e58e03fa703cd38b1fbe61df890ec4d32b7428f
MD   508695aea9ec89eb5bbcf020d826eab7b8f7c3293876a35d014796e168c56465
```

The supplied `real_Data.pdf` was background for this handoff and is not included
here. No dataset files, restricted assets, credentials or application changes
are part of this documentation delivery.
