# Replay the November 21 Studio House

Open the six-room home that Town generated from a live brief on a 15 × 16 m lot with seed 42. Revision 1 is Layout A. In revision 2 the visitor pulled the bedroom writing chair 30 cm away from the Belaya desk. Both revisions passed the room and whole-home spatial checks.

## Open the saved home

Complete the Town setup in the [README](../../README.md#quick-start). From the repository root, run the following commands in the same terminal. The download contains only the two saved design snapshots. A fresh temporary directory gives each rehearsal its own writable copy. Opening a saved design and asking the measured questions use zero provider calls.

```bash
conference_dir=$(mktemp -d)
curl -fL --retry 2 \
  https://github.com/ngstephen1/ArchiMind/releases/download/conference-home-r2/Conference-Town.sqlite3 \
  -o "$conference_dir/Conference-Town.sqlite3"
TOWN_DB="$conference_dir/Conference-Town.sqlite3" .venv/bin/python scripts/run_town.py
```

Open [the edited home](http://127.0.0.1:8790/?project=cfe87682-1ed5-4ddf-9bec-5aa9e6795872&revision=2). Visit the bedroom, then choose **Design presentation**. The visitor can see the plan, switch rooms, inspect the furniture schedule, open the client book or ask a question. Open [the earlier revision](http://127.0.0.1:8790/?project=cfe87682-1ed5-4ddf-9bec-5aa9e6795872&revision=1) in another tab. If using a different Town port, change the port in both links.

## Follow one edit

| Ask in Design presentation | What to check |
| --- | --- |
| What changed when I moved the chair? | In the bedroom, the chair footprint origin moves from (3.720, 0.862) m to (3.720, 1.162) m. The nearest edge gap increases from 0.060 m to 0.360 m. |
| Will this chair slide under the desk? | The writing chair is 0.48 m wide. The answer asks for the clear width between the desk supports and the height beneath the apron. The exported envelope alone cannot establish fit. |
| Why put the bedroom desk near the window? | The desk and the west window are 4.46 m apart, center to center in plan. The room records contain no glare measurement or intent explaining that position. A question about an unspecified desk requires choosing the bedroom or study. |
| Which pieces have an oak finish? | The Belaya desk has a catalog variant labeled Oak. That field does not establish wood species or solid-wood construction. |

The evidence control answers documented questions about the saved design. Live brief interpretation happens during generation.

Compare the chair footprints on the A3 detail sheet and the fixed-camera desk views. Town's automatic desk camera changes composition when the chair moves. The matched Blender views hold the eye, target and field of view constant across revisions.

[Render a saved Town presentation](RENDER_SAVED_TOWN_PRESENTATION.md) · [Release files and checksums](https://github.com/ngstephen1/ArchiMind/releases/tag/conference-home-r2) · [Paired manifest exports](../data/conference-sprint/) · [Live acceptance record](https://github.com/ngstephen1/ArchiMind/issues/38)

## What the recordings show

The live interpretation needed two clarifications before returning two validated alternatives. The optional Codex CLI review reported a process error. The OpenAI visual review returned a result. When a fourth design job reached the daily limit, the user-directed chair edit went through Town's preview, validation and apply workflow. Reopening the release database replays the saved geometry. The original provider jobs and their ledger remain outside this portable database.

The landscape infographic introduces the project. The existing narrated video shows an earlier five-room design and a separate six-room Studio House at revision 5. The November 21 home and its chair move are documented in the release book and the paired exports.
