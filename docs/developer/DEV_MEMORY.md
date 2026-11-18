# Hand off ArchiMind work between Codex and Claude

Run the following from an ArchiMind Git checkout on Apple Silicon macOS or x86-64 Linux. The operator needs Python 3.11+, GitHub CLI release access, Git and lsof. This local developer tool has its own loopback service and SQLite/wiki directory. Town and GBrain use their existing stores.

```sh
python3 scripts/dev_memory.py install
python3 scripts/dev_memory.py start
```

Keep that terminal open. A developer or coding agent can run the commands below from another terminal. Write a short JSON file with four reviewed, single-line fields. Put only information your teammate can see in the file. Credential-pattern checks cover common formats and cannot recognize every secret.

```json
{
  "task": "Compare public bedroom reference passages",
  "evidence": "The seed-42 fixture passed the spatial validator",
  "unresolved": "The fixture has no measured monitor glare",
  "next_action": "Check the evidence before making a daylight claim"
}
```

```sh
python3 scripts/dev_memory.py handoff --author claude --file note.json
python3 scripts/dev_memory.py list
python3 scripts/dev_memory.py export --id OPEN_ID --file reviewed-handoff.json
python3 scripts/dev_memory.py accept --id OPEN_ID
python3 scripts/dev_memory.py stop
```

Use the ID returned by the service in place of OPEN_ID. Author labels record the submitting operator's declaration. Codex uses the same commands with `--author codex`. Opening the list preserves the note for the intended reader. Acceptance explicitly claims it once. The note includes the local branch and commit. A base mismatch requires reviewing the note first, then explicitly passing `--accept-stale`.

For a teammate on another machine, review the exported JSON, share it via your PR, then run `python3 scripts/dev_memory.py import --file reviewed-handoff.json` on their running local service. Imports create a new local offer with the original provenance. The recipient accepts the returned local ID. Accepting the copy does not consume the sender's offer.

Installation checks the SHA-256 of the official v3.5.0 platform archive before extracting the binary. The version lock identifies upstream commit bc7faa7d847dd387e634ba8420d115b9dd4ecebe. The digest uses the upstream release as the trust anchor. The executable and service state live under `~/.local/share/archimind-ai-memory`. The handoff store disables embeddings, uses a file-backed bearer and runs with a separate home and no producer API credentials. No global hooks, automatic transcript capture, or paid inference are configured. Start and stop are explicit. Set `ARCHIMIND_DEV_MEMORY_PORT` in all participating terminals if port 49484 is occupied.

Run `python3 scripts/check_dev_memory.py` after installation for a disposable integration test. It exercises declared Claude and Codex submissions through the same command available to both harnesses, restarts the real server, races two accepts, and tests transfer, stale commits, unauthorized access and secret exclusion. This check spends zero model requests.

[Upstream release](https://github.com/akitaonrails/ai-memory/releases/tag/v3.5.0) · [MIT license](../third-party/AI-MEMORY-LICENSE.txt)
