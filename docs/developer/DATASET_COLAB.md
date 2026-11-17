# Running dataset processing on Google Colab (with Drive backup)

Heavy dataset work runs in Colab. Your own machine only receives the finished
**reference pack** (tens of MB). All processing logic lives in
`src/archimind/datasets/` and is tested in CI. The notebook
`notebooks/archimind_datasets_colab.ipynb` only calls
`python -m archimind.datasets ...`, so there is nothing to hand-edit in notebook
cells beyond the configuration cell.

## 1. One-time setup (about 10 minutes)

### 1.1 GitHub token (the repository is private)

1. GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate.
2. Repository access: **Only `ngstephen1/ArchiMind`**. Permissions: **Contents: Read-only**.
   Nothing else. Expiry: 30 days.
3. Copy the token. Never paste it into a notebook cell or commit it.

### 1.2 Dataset tokens

| Secret name | Needed for | How to get it |
| --- | --- | --- |
| `HF_TOKEN` | SSR-3DFRONT and MIDI-3D (Hugging Face) | huggingface.co → Settings → Access Tokens → **Read** token. Open each dataset page once while logged in and accept its access conditions if it is gated. |
| `KAGGLE_USERNAME`, `KAGGLE_KEY` | 3D-FUTURE mirror | kaggle.com → Settings → API → Create New Token (the JSON file holds both values). |
| `GH_TOKEN` | Installing ArchiMind | Section 1.1. |

### 1.3 Add the secrets to Colab

Open the notebook, click the **key icon** in the left sidebar and add the four names
above exactly. Switch **Notebook access** on for each one. Secrets are stored in your
Google account, not in the notebook file, so sharing the notebook does not share them.

### 1.4 Open the notebook

Colab → File → Open notebook → **GitHub** tab → tick *Include private repos* →
authorize → choose `ngstephen1/ArchiMind`, branch `data/dataset-reference-pilot`,
file `notebooks/archimind_datasets_colab.ipynb`. Then **File → Save a copy in Drive**
so your configuration edits survive. Edit only your Drive copy.

Runtime: **CPU** is enough (Runtime → Change runtime type → CPU). No GPU is used.

## 2. Storage layout: fast local disk, Drive as the backup

Google Drive mounted in Colab is slow for many small files and has a small free quota
(15 GB shared with Gmail). The notebook therefore works on Colab's local disk and
copies only **compact, finished** outputs to Drive.

```
/content/work/                         fast local disk, lost when the runtime ends
  raw/        downloaded source files  (never copied to Drive)
  stages/     content-addressed stage outputs
  packs/      built reference packs
/content/drive/MyDrive/ArchiMind-data/ persistent backup
  runs/<RUN_ID>/stages/                checkpoint of /content/work/stages
  runs/<RUN_ID>/packs/                 checkpoint of /content/work/packs
  runs/<RUN_ID>/receipts/              environment and stage receipts
```

- **Raw downloads stay local.** They are re-fetched within the byte budget after a
  disconnect, and a partial download resumes where it stopped.
- **Stages are content-addressed.** A finished stage writes a `_COMPLETE` file that
  lists every output with its SHA-256. When the notebook runs again, any stage whose
  inputs are unchanged and whose outputs still verify is skipped, so a disconnect
  costs only the unfinished stage.
- **Checkpoint copies are atomic.** `python -m archimind.datasets sync` writes each
  file as `.partial`, then renames it, and skips files whose size and hash already
  match. An interrupted copy never leaves a truncated file that looks complete.

## 3. Long runs: surviving disconnects

Colab ends idle sessions (roughly 90 minutes without interaction) and caps session
length (around 12 hours on the free tier, longer with paid tiers). These limits change
over time. Plan for disconnects instead of trying to prevent them:

1. **Use the same `RUN_ID`** when you reconnect. Run the cells from the top: setup is
   idempotent, the *Restore* cell copies the Drive checkpoint back to local disk, and
   finished stages are skipped.
2. **Checkpoint after every stage.** The notebook calls the *Checkpoint* cell after
   each stage. For long stages, the stage commands checkpoint their own progress
   in bounded batches.
3. **Keep the tab open and the computer awake** during long stages. Paid tiers offer
   background execution. Do not use auto-clicker scripts; they break Colab's terms.
4. **Before you close the tab**, run the *Finalize* cell. It checkpoints, verifies the
   pack and calls `drive.flush_and_unmount()` so Drive finishes writing.

Every stage also refuses to start, or stops cleanly, when free local disk would fall
below the configured floor (default: 4 GiB reserve). It does not resume automatically.

## 4. Pinning: what makes a run reproducible

- Set `ARCHIMIND_COMMIT` in the configuration cell to an **exact commit SHA**, not a
  branch name. The environment receipt records it together with the Python, NumPy and
  Pydantic versions and the source revisions.
- The install step uses `--no-deps` and pins only what the dataset package needs, so
  Colab's preinstalled packages are not replaced by the Streamlit app's dependencies.

## 5. Getting the pack onto your machine

1. Download `MyDrive/ArchiMind-data/runs/<RUN_ID>/packs/<pack_id>/` (Drive web →
   right-click → Download, or Google Drive for desktop).
2. Unzip it outside the Git checkout, for example `E:\archimind-data\packs\<pack_id>`.
3. Verify it, then point the app at it:

```powershell
.venv\Scripts\python -m archimind.datasets verify-pack E:\archimind-data\packs\<pack_id>
$env:ARCHIMIND_DATASET_REFERENCE_ROOT = "E:\archimind-data\packs\<pack_id>"
```

`verify-pack` re-hashes every file against the manifest and rejects missing, extra or
modified files.

## 6. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `fatal: could not read Username` during install | `GH_TOKEN` is missing, lacks notebook access, or has expired. |
| `401` / `403` from Hugging Face | Accept the dataset's access conditions on its web page with the same account as `HF_TOKEN`. |
| `CapacityError` | Local disk is below the floor. Delete `/content/work/raw/<source>` for finished sources, or restart the runtime. Never lower the floor to make it pass. |
| Drive copy is slow | Expected for many files. Only stage outputs and packs are synced, not raw data. |
| Stage reruns after reconnect | The `RUN_ID`, commit or stage inputs changed. Its stage key is printed in the receipt. |
