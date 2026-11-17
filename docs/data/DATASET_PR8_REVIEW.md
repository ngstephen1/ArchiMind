# Dataset PR #8 review — 2026-11-17

Reviewed base: `fc19b0ba5899a0b2968789bb8ff6aefbef6c3ed3` (main).
Incoming head: `ce22f9242264d9eff333af83b7b4a6115ec47450`.
PR: <https://github.com/ngstephen1/ArchiMind/pull/8>.

## Scope and branches

The incoming title described P0 only, but its seven commits also include P1
probes, the P2a SSR adapter and Kaggle authentication/setup work. No dataset
retrieval facade, app/chatbot wiring or reference renderer is delivered here.
Hieu's other branch, `feature/single-agent`, is already contained in main through
PR #7 (green run 42253273282). It is a separate, opt-in single-agent prototype,
not dataset integration. No additional unmerged work was found on that branch.
The `stephen-develop` tip is by ngstephen1 and has no commits beyond current main.

## Findings fixed before merge

- Incoming CI 43103516447 stopped at notebook lint. Removed the temporary curl
  authentication diagnostic cell and saved execution outputs; formatted notebook
  code and setup examples. Corrected its obsolete commit pin; authentication is
  supplied to child Git through the environment instead of credential-bearing
  clone URLs or persistent remote configuration. Both Kaggle credential styles
  are available through Colab secrets.
- A correctly rehashed pack could contain scenes with no corresponding source,
  an incorrect source revision/hash, incorrect transform version, duplicates,
  or symbolic links and still load. Build and load now check those relationships,
  asset source-file bindings and GLB byte sizes. Hashes establish consistency,
  not trusted authorship, legal permission or render qualification.
- Download resume now verifies Content-Range and complete response length;
  short responses cannot be promoted to completed files. Capacity is checked
  before each chunk write, including responses without Content-Length. Existing
  cached files must also fit the byte budget. Partials can remain for explicit
  retries; there is no automatic retry after capacity failure.
- Malformed GLB arrays/JSON and truncated chunk boundaries are controlled
  rejections. Container checking remains separate from geometry/image decoding
  and measured resource qualification.
- Stage names cannot escape their configured root. Paginated HF tree listings
  fail explicitly instead of silently presenting a first page as a complete tree.
- SSR local reports now include MIDI input hashes. Public SSR packs are explicitly
  blocked even with allowed SSR metadata permission until the MIDI-derived
  category/split provenance and its separate permission are bound into the pack.
- Extended the existing single source/wheel/install test with dataset module-byte
  checks and an offline synthetic pack round trip outside the checkout. No extra
  build is required by those assertions.

The new review regression file initially reproduced 13 failures (two cases already
passed). After fixes, the dataset suite passes 205 tests. The combined dataset,
design-agent, launcher and furniture-source preservation command passes 280 tests:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
  tests/datasets tests/test_design_agent_gate.py tests/test_design_agent_loop.py \
  tests/test_design_agent_ui.py tests/test_run_with_agent.py \
  tests/test_furniture_source_expansion.py
python -m ruff check --no-cache .
python -m ruff format --check --no-cache .
git diff --check
```

Local tests used the existing environment with no dependency downloads. Initial
local capacity was about 331 MiB and fluctuated; full regression, frontend build,
installed packaging and health are delegated to the PR's exact-commit CI. Merge
requires that complete CI to pass. No real dataset downloads, live AI requests,
new asset conversion, visual acceptance or raw-pack rebuild occurred in review.
Historical P1/P2a receipts are preserved verbatim.

## Current data status

| Track | Accepted evidence / remaining work |
| --- | --- |
| SSR | Historical pinned run: 7,328 bedroom rows → 4,168 references (53 canonical, 4,115 reference-only), 3,160 exclusions; local pack was 11.9 MB. Review did not replay those raw inputs. |
| MIDI | Pinned room/object metadata and identity join; historical bounded archive-prefix probe only. No accepted retained-room adapter or qualified mesh pack. Gzip archives do not provide selective room access. |
| FUTURE | Kaggle Bearer/legacy authentication and inventory tooling. Accepted P1 receipt remains blocked on credentials; no accepted asset conversion or qualified reference meshes. |
| Permission | SSR license signals conflict; public uses remain unresolved. Mirror access does not grant redistribution rights. MIDI-derived metadata needs its own pinned provenance and permission record. |
| Retrieval / chatbot / rendering | Not wired. Existing five-product ABO catalog, two individually approved product meshes, 09A selections/A/B generation and mixed-product restriction remain separate. |

Canonical is a dataset tier, not proof of a complete valid room. It uses recorded
classification tolerances; openings remain unknown, floor/split checks can fail,
and current app validators must run before any future layout admission. No dataset
reference becomes a purchasable product or a qualified selected-layout mesh.

Next milestone: bind the MIDI category/split dependency with exact source hashes
and independently decided permissions, then produce a bounded reproducible local
reference-pack receipt. Public integration remains blocked until applicable rights
are established; retrieval and app wiring follow in separately reviewed PRs.
