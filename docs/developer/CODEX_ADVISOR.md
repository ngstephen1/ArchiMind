# Optional Codex Design Advisor — C01

Backend-only, disabled by default, for single-user local testing. The Streamlit
application does not import or expose this adapter. Tasks 06A and the deterministic
layout generator remain unchanged; there is no auto-application or agent workflow.

## Python contract

```python
from archimind.examples.sample_bedroom import create_sample_bedroom
from archimind.integrations import request_codex_advice

result = request_codex_advice(
    create_sample_bedroom(),
    "Suggest a better desk position while preserving doorway accessibility.",
)
assert result.status == "disabled"  # default environment
```

To request live advice in a future explicitly authorized local session, BOTH
`ARCHIMIND_ENABLE_CODEX_ADVISOR=1` and the per-call keyword
`allow_live_usage=True` are required. Tests mock every subprocess; this task has
not made a real model request. The adapter does not load `.env` files or accept
API keys, executable paths, model choices, or arbitrary CLI flags as arguments.
Saved CLI authentication must already exist.

`CodexAdvice` contains `design_analysis`, up to three `suggestions`, and a nonempty
`limitations` list. Each suggestion contains an existing `furniture_id`, finite
`x_m`/`y_m`, and an `explanation`. Unexpected fields and scalar coercions are
rejected. `CodexAdviceResult` contains status, a typed error code, a fixed sanitized
message, optional advice, and `requires_spatial_validation=True`. A successful
response only means the advice was parsed. It does not validate proposed geometry.

Illustrative response fragment (mock data, not model output):

```json
{
  "design_analysis": "Consider another desk position.",
  "suggestions": [{
    "furniture_id": "desk",
    "x_m": 3.0,
    "y_m": 3.1,
    "explanation": "Compare this position with the current arrangement."
  }],
  "limitations": ["Not spatially validated; doorway access must be checked."]
}
```

Meters and the canonical coordinate system apply: southwest origin, X east, Y
north; furniture positions are the lower-left of the unrotated footprint. The
current geometry engine only evaluates rotation 0; other stored rotations return
`unsupported_geometry`. Existing overlaps/out-of-bounds layouts may receive
suggestions. No-door rooms may receive advice without any accessibility claim.
Suggested negative/out-of-room coordinates remain unvalidated proposals. A future
caller must reconstruct/revalidate the proposed design and run the deterministic
containment, collision, and accessibility engines before accepting any change.

## Execution and bounds

The adapter discovers `codex` on the local PATH and checks CLI help and saved-login
status before requesting advice. Missing flags fail closed. Execution uses:

```text
codex --ask-for-approval never exec --ignore-user-config --sandbox read-only
  --ephemeral --skip-git-repo-check --output-schema schema.json
  --output-last-message advice.json --color never -
```

Arguments are fixed and `shell=False`; the JSON prompt is provided through stdin.
Each call uses a private `/tmp/archimind-advisor-*` directory outside the project,
removed on completion or failure. `--skip-git-repo-check` is limited to this
isolated invocation. No repository trust settings are changed. Only supplied
room-design data and the user goal enter the prompt; no repository file is read
for prompt context. The child environment forwards only HOME, PATH, USER, LOGNAME,
TMPDIR, and CODEX_HOME when present, retaining saved CLI authentication while
excluding inherited API keys and unrelated app secrets.

Limits: 100 furniture items, 2,000 goal characters, 64 KiB UTF-8 prompt, 32 KiB
final response, and a 60-second execution deadline including preflights. Each
preflight has at most five seconds. Timeout/overflow cleanup kills the POSIX
process group and allows up to two additional seconds to reap the process. Logs
are discarded rather than accumulated. Response size is polled at most every
50 ms while waiting, with a bounded final read; this is not an OS disk quota and
transient disk overshoot is possible. Symlink/non-regular response files are
rejected. Duplicate JSON keys, non-finite values, schema errors, unknown furniture
IDs, missing CLI/auth, incompatible CLI, process errors, and I/O failures produce
typed sanitized results without raw subprocess diagnostics.

Read-only sandboxing does **not** guarantee confidentiality of files readable by
the CLI, and prompt instructions are not a security boundary. Ignoring user
configuration reduces inherited configuration; saved auth still uses the normal
CLI home. This adapter is not a container or a public-service security boundary.
Do not expose it through a public endpoint. POSIX macOS/Linux only; live provider,
account, network, and sandbox behavior remain unverified until an authorized smoke
test. There is no automatic retry or live test in CI.

## Offline verification

```bash
cd /Users/macbook/Hack/ArchiMind
source .venv/bin/activate
python -m pytest -q
python -m pip check
python -m ruff check .
python -m ruff format --check .
python scripts/check_health.py
```

The optional next integration step is C02: a Streamlit Design Advisor panel,
subject to a separate scope and review. It is not implemented here.
