# Replay the November 21 Studio House

Open the six-room home that Town generated from a live brief on a 15 × 16 m lot with seed 42. Revision 1 is Layout A. In revision 2 the visitor pulled the bedroom writing chair 30 cm away from the Belaya desk. Both revisions passed the room and whole-home spatial checks.

## Open the saved home

Complete the Town setup in the [README](../../README.md#quick-start). From the repository root, run the following commands in the same terminal. The offline replay builds its database from the two saved snapshots included in this checkout. It validates each home and checks both exported manifests against the recorded bytes. A fresh temporary directory gives each rehearsal its own writable copy. Opening a saved design and asking the measured questions use zero provider calls.

```bash
conference_dir=$(mktemp -d) &&
.venv/bin/python scripts/reopen_conference_home.py "$conference_dir/Conference-Town.sqlite3" &&
ARCHIMIND_ENABLE_OPENAI_STUDIO=0 ARCHIMIND_ENABLE_CODEX_ADVISOR=0 \
  TOWN_DB="$conference_dir/Conference-Town.sqlite3" .venv/bin/python scripts/run_town.py
```

Open [the edited home](http://127.0.0.1:8790/?project=cfe87682-1ed5-4ddf-9bec-5aa9e6795872&revision=2). Click **Visit saved home**, then **Enter house**. Select **Bedroom** from **Visit a room**, then choose **Design presentation**. The visitor can see the plan, switch rooms, inspect the furniture schedule, open the client book or ask a question. Open [the earlier revision](http://127.0.0.1:8790/?project=cfe87682-1ed5-4ddf-9bec-5aa9e6795872&revision=1) in another tab. If using a different Town port, change the port in both links. The launch runs only after the export check succeeds.

If ports 8790 or 8791 are occupied, start the replay on a different pair. Set
both variables before running the launcher so the town and editor links share
the same configuration.

```bash
ARCHIMIND_ENABLE_OPENAI_STUDIO=0 ARCHIMIND_ENABLE_CODEX_ADVISOR=0 \
  TOWN_PORT=8850 TOWN_EDITOR_PORT=8851 \
  TOWN_DB="$conference_dir/Conference-Town.sqlite3" .venv/bin/python scripts/run_town.py
```

Run these health checks from a second terminal while the launcher is running.

```bash
curl -fsS http://127.0.0.1:8850/health
curl -fsS http://127.0.0.1:8851/_stcore/health
```

Open [revision 2 on port 8850](http://127.0.0.1:8850/?project=cfe87682-1ed5-4ddf-9bec-5aa9e6795872&revision=2).
Both health endpoints returned HTTP 200 in the local command check. The saved
revisions also reopened in desktop and narrow Chrome, and a separate local run
without provider credentials declined a live job while keeping revision 2.
[Replay verification](https://github.com/ngstephen1/ArchiMind/issues/66#issuecomment-7090628981)

## Public walkthrough

The [Vercel walkthrough](https://archimind-town-walkthrough.vercel.app/) serves
the static Town. The November 23 deployment check found empty API, editor and
sign-in configuration. The page and packaged files responded, while the
same-origin API routes returned HTTP 404. Use the isolated local replay above
for the saved revisions, explanations and client book.
[Deployment evidence](https://github.com/ngstephen1/ArchiMind/issues/66#issuecomment-7090628981)

## Open both conference projects

After installing the checkout with the live conference evidence, give the builder both sources. The original and fresh projects follow the same seed and chair edit and have distinct project and manifest identities.

```bash
conference_dir=$(mktemp -d) &&
.venv/bin/python scripts/reopen_conference_home.py "$conference_dir/Conference-Town.sqlite3" \
  --example docs/data/conference-sprint --example docs/data/conference-live-final &&
ARCHIMIND_ENABLE_OPENAI_STUDIO=0 ARCHIMIND_ENABLE_CODEX_ADVISOR=0 \
  TOWN_DB="$conference_dir/Conference-Town.sqlite3" .venv/bin/python scripts/run_town.py
```

Open [the fresh revision 2](http://127.0.0.1:8790/?project=c9339e4f-a57a-4328-95dc-40dc36dd5b89&revision=2), enter the bedroom and choose **Design presentation**. Revision 2 links its own client book and source scene. Use revision 1 for the comparison.

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

The original live interpretation needed two clarifications before returning two validated alternatives. The optional Codex CLI review reported a process error. The OpenAI visual review returned a result. In the original run, when a fourth design job reached the daily limit, the user-directed chair edit went through Town's preview, validation and apply workflow. Reopening the release database replays the saved geometry. The original provider jobs and their ledger remain outside this portable database.

The landscape infographic introduces the project. The existing narrated video shows an earlier five-room design and a separate six-room Studio House at revision 5. The November 21 home and its chair move are documented in the release book and the paired exports.
