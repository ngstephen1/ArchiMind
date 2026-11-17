# Dataset setup, step by step

Sources: **SSR-3DFRONT** (Hugging Face), **MIDI-3D / 3D-Front** (Hugging Face),
**3D-FUTURE mirror** (Kaggle). The raw datasets are far too large for a laptop and the
handoff caps each source at **1 GiB transferred / 2 GiB expanded**, so always use the
bounded `python -m archimind.datasets` CLI. Never bulk-clone.

Companion guide for the Colab flow: `docs/developer/DATASET_COLAB.md`.

## Overview: pick where each job runs

| Job | Where | Why |
| --- | --- | --- |
| Fetch, SSR build, pack building | Colab notebook `notebooks/archimind_datasets_colab.ipynb` (or a Kaggle-hosted notebook) | Fast network, Drive checkpoints, resumable |
| Editing code, tests, verifying a finished pack, running the app | Your machine (Python 3.11) | Packs are only tens of MB |

No GPU and no training are needed anywhere.

Do the parts in order: **A** accounts and tokens, **B** `.env`, **C** local
environment, **D** verify, **E** Colab, **F** Kaggle-hosted (optional), **G** commands.

---

## Part A. Create the accounts and tokens

### A1. Hugging Face token (SSR-3DFRONT, MIDI-3D)

1. Sign in at huggingface.co.
2. Open each dataset page once while logged in:
   `gradient-spaces/SSR-3DFRONT` and `huanngzh/3D-Front`. If a page shows an access
   form, read the terms yourself and accept only if you are permitted to. Do not accept
   on anyone else's behalf.
3. Settings → **Access Tokens** → **Create new token** → type **Read**.
4. Copy the token (starts with `hf_`). You only see it once.

### A2. Kaggle credentials (3D-FUTURE mirror)

1. Sign in at kaggle.com. Verify your phone number if asked (needed for Internet in
   Kaggle notebooks).
2. Settings → **API** → **Create New Token**.
3. A `kaggle.json` downloads with `username` and `key`. Copy both values.
   (Newer accounts may show a single token string instead. If so, use it as
   `KAGGLE_API_TOKEN`, see B3.)
4. Open the 3D-FUTURE dataset page (`tobetheonly/3d-future-model`) once. A Kaggle
   listing is **not** permission to redistribute the assets.

### A3. GitHub token (Colab only)

The repo is private, so Colab needs a read token to clone it.

1. GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate.
2. Repository access: only `ngstephen1/ArchiMind`.
3. Permissions: **Contents: Read-only**. Nothing else. Expiry 30 days.
4. Copy the token. Skip this step if you only work locally.

---

## Part B. Fill in `.env`

`.env` is git-ignored, so keys stay local. `.env.example` is the committed template
with placeholders only. ArchiMind **does not auto-load** `.env`; Part B4 loads it into
your shell.

### B1. Open the file

Edit `.env` in the repo root. The dataset block is at the bottom.

### B2. Fill in each variable

| Variable | Value | Needed when |
| --- | --- | --- |
| `HF_TOKEN` | Token from A1 | When the source requires authentication |
| `KAGGLE_USERNAME` | `username` from `kaggle.json` | 3D-FUTURE |
| `KAGGLE_KEY` | `key` from `kaggle.json` | 3D-FUTURE |
| `GH_TOKEN` | Token from A3 | Colab only (leave placeholder locally) |
| `ARCHIMIND_COMMIT` | Output of `git rev-parse HEAD` | Pinned Colab run |
| `ARCHIMIND_DATA_ROOT` | e.g. `E:\archimind-data` (outside Git) | Local runs |
| `ARCHIMIND_FLOOR_GIB` | `4` | Free-disk stop floor |
| `ARCHIMIND_ENABLE_DATASET_REFERENCES` | `0` (default) or `1` | `1` shows *References for next specification* in Chat bedroom |
| `ARCHIMIND_DATASET_REFERENCE_ROOT` | Path of a verified pack, e.g. `E:\archimind-data\p2b\pack` | Server-side only; users never supply paths |
| `ARCHIMIND_DATASET_REFERENCE_AUDIENCE` | `public` (default) or `local` | `local` only on a research machine; a local pack is blocked for `public` |

### B3. Kaggle alternatives (optional)

- This package reads environment variables only; it does not read Kaggle credential
  files automatically. Copy legacy file values into `KAGGLE_USERNAME` and
  `KAGGLE_KEY` locally, without sharing or committing them.
- Token-string accounts: set `KAGGLE_API_TOKEN` (a `KGAT_` token). The notebook
  accepts that secret as well as legacy username/key pairs.

### B4. Load `.env` into your PowerShell session

Run in the repo root, once per terminal:

```powershell
Get-Content .env | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2; Set-Item -Path "env:$($k.Trim())" -Value $v.Trim()
}
```

Check without printing secrets:

```powershell
"HF_TOKEN set: " + [bool]$env:HF_TOKEN
```

### B5. Rules

- Never commit `.env`, `kaggle.json` or any token. Never paste tokens into notebook
  cells or chat.
- The CLI reads tokens from environment variables **by name** (`--auth-env HF_TOKEN`)
  and never prints them.

---

## Part C. Local environment

### C1. Create and activate a virtual environment

```powershell
python --version            # needs 3.11.x
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### C2. Install ArchiMind and dataset tooling

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install huggingface_hub kaggle jupyterlab ipykernel
```

### C3. Register the Jupyter kernel

```powershell
python -m ipykernel install --user --name archimind --display-name "ArchiMind"
```

### C4. Start Jupyter

- Browser: `jupyter lab`, then choose the **ArchiMind** kernel.
- VS Code: install the *Jupyter* extension, open a `.ipynb`, click the kernel picker
  (top right) and choose **ArchiMind**.

### C5. Create the data root (outside Git)

```powershell
New-Item -ItemType Directory -Force E:\archimind-data | Out-Null
```

Raw data, extracts and caches go here, never into the repo.

---

## Part D. Verify the local setup

### D1. Free-space and credential check

```powershell
python -m archimind.datasets env --data-root $env:ARCHIMIND_DATA_ROOT --floor-gib $env:ARCHIMIND_FLOOR_GIB
```

Expected: a JSON receipt with `above_floor: true` and `secrets_present` showing
`true` for each token you set (values are never printed). Exit code 3 means blocked
(below the disk floor or a credential is missing).

### D2. Synthetic self-check pack (no network, no real data)

```powershell
python -m archimind.datasets fixture-pack E:\archimind-data\packs\fixture
python -m archimind.datasets verify-pack E:\archimind-data\packs\fixture
```

### D3. Run the tests

```powershell
python -m pytest -q tests/datasets
python -m ruff check .
```

---

## Part E. Colab (heavy processing)

Full detail lives in `docs/developer/DATASET_COLAB.md`. Short version:

1. **Push the branch** so Colab can clone it (`git push -u origin data/dataset-reference-pilot`).
   Get the exact SHA with `git rev-parse HEAD`.
2. Colab → File → Open notebook → **GitHub** tab → tick *Include private repos* →
   `ngstephen1/ArchiMind`, branch `data/dataset-reference-pilot`,
   `notebooks/archimind_datasets_colab.ipynb`. Then **File → Save a copy in Drive**
   and edit only your copy.
3. Runtime → Change runtime type → **CPU**.
4. Click the **key icon**, add four secrets named exactly `GH_TOKEN`, `HF_TOKEN`,
   `KAGGLE_USERNAME`, `KAGGLE_KEY`, and switch **Notebook access** on for each.
5. In the configuration cell set `RUN_ID` (e.g. `pilot-001`) and `ARCHIMIND_COMMIT`
   (the 40-character SHA from step 1). Edit nothing else.
6. Run all cells from the top. If the runtime disconnects, reconnect and run again
   from the top **with the same `RUN_ID`**; finished stages are skipped and partial
   downloads resume.
7. When it finishes, download the finished pack from
   `MyDrive/ArchiMind-data/runs/<RUN_ID>/packs/` and check it locally:
   ```powershell
   python -m archimind.datasets verify-pack <downloaded-pack-dir>
   ```

---

## Part F. Kaggle-hosted notebook (optional alternative)

1. kaggle.com → Code → **New Notebook**.
2. Right sidebar → Settings: turn **Internet** on (requires phone verification) and
   pick an accelerator only if you want one (not needed).
3. Add-ons → **Secrets**: add `HF_TOKEN`, `KAGGLE_USERNAME`, `KAGGLE_KEY` and attach
   them to the notebook.
4. First cell:
   ```python
   import os
   from kaggle_secrets import UserSecretsClient

   s = UserSecretsClient()
   for n in ("HF_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
       os.environ[n] = s.get_secret(n)
   ```
5. Install and run the CLI (the token goes in a secret, not in the URL, if the repo is
   private; use a public mirror or upload the repo as a Kaggle dataset instead):
   ```python
   !git clone <your-repo-url> /kaggle/working/ArchiMind
   !pip install -e /kaggle/working/ArchiMind
   !python -m archimind.datasets env --data-root /kaggle/working --floor-gib 4
   ```
6. Sync notebooks from your machine with the CLI:
   ```powershell
   kaggle kernels init -p .\notebooks          # creates kernel-metadata.json
   kaggle kernels push -p .\notebooks
   kaggle kernels output <user>/<slug> -p .\out
   ```

---

## Part G. Common commands

All print one JSON document. Exit codes: `0` ok, `1` failure, `2` usage,
`3` blocked (capacity floor or missing credential).

1. **Pin a Hugging Face dataset and list its files** (do this before fetching):
   ```powershell
   python -m archimind.datasets probe-hf gradient-spaces/SSR-3DFRONT --out E:\archimind-data\receipts\ssr-probe.json
   ```
   Add `--revision <40-char-sha>` to reproduce an earlier pin.
2. **Inspect the Kaggle dataset version and files:**
   ```powershell
   python -m archimind.datasets probe-kaggle tobetheonly/3d-future-model --out E:\archimind-data\receipts\future-probe.json
   ```
3. **Bounded download** (hard byte cap, resumable, hash-checked):
   ```powershell
   python -m archimind.datasets fetch <url> <dest-file> --max-bytes 1073741824 --auth-env HF_TOKEN --sha256 <expected-hash>
   ```
   For Kaggle URLs use `--kaggle-auth` instead of `--auth-env`.
4. **List a capped `.tar.gz` prefix** without downloading the archive:
   ```powershell
   python -m archimind.datasets probe-tar-prefix <url> --max-bytes 8388608 --auth-env HF_TOKEN
   ```
5. **Profile SSR parquet shards:**
   ```powershell
   python -m archimind.datasets probe-ssr <shard.parquet> [more.parquet] --room-type bedroom
   ```
6. **Build scene references (P2a):**
   ```powershell
   python -m archimind.datasets ssr-build <shard.parquet> --inventory <probe-hf.json> --midi-dir <dir> --out <new-empty-dir> --pack-dir <pack-dir>
   ```
   Add `--permission <PermissionRecord.json> --retrieved-utc <time>` when building a
   pack; `--audience public` additionally requires documented permission.
7. **Verify a pack:** `python -m archimind.datasets verify-pack <pack-dir>`
8. **Checkpoint copy (hash-checked):** `python -m archimind.datasets sync <src> <dst>`

---

## Rules and current state

- Raw data, extracts, caches and tokens stay out of Git, CI artifacts and Claude
  context. A blocked source is BLOCKED, never a fabricated success count.
- Do not accept dataset terms for others, contact owners, or upload restricted samples
  to external services. Unknown permission means ineligible for public output.
- Budget: 1 GiB transferred / 2 GiB expanded per source; stop below the 4 GiB free-disk
  floor; request a revised budget before exceeding it.
- Progress: P0, P1, P2a done; next **P2b** (MIDI) and **P2c** (FUTURE). SSR
  permission is provisional.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `.\.venv\Scripts\Activate.ps1` is blocked | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `secrets_present` shows `false` | Re-run the B4 loader in the same terminal; check variable names |
| Exit code 3, `capacity_floor` | Free disk space or move `ARCHIMIND_DATA_ROOT` to a larger drive |
| HF 401/403 | Token missing/incorrect, or the dataset's access conditions are not accepted on your account |
| Kaggle 401/403 | Regenerate the token; open the dataset page once while logged in |
| Colab disconnect | Rerun from the top with the same `RUN_ID` |

## Current public integration boundary

The current delivery is offline tooling, probes and the SSR adapter, not a dataset
feature in the app. `ARCHIMIND_ENABLE_DATASET_REFERENCES` and
`ARCHIMIND_DATASET_REFERENCE_ROOT` are reserved for future wiring and have no
runtime effect yet. Public SSR pack creation is blocked pending pinned MIDI
category/split provenance and separate permissions, even if SSR metadata itself
has been authorized. See [DATASET_REFERENCES.md](DATASET_REFERENCES.md).

The notebook is committed without execution outputs. Select the exact reviewed
commit before running it, retain external receipts, and do not interpret a
successful login/download as permission to publish source data or send it to an LLM.
