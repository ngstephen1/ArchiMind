import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { homeBoard } from "../town/home_board.js";
import { manifestText } from "../town/bedroom_manifest.js";

const command = fileURLToPath(
  new URL("../town/export-saved-style.mjs", import.meta.url),
);

test("saved style reuses Town's shipped models and fails on a stale board", async () => {
  const dir = await mkdtemp(join(tmpdir(), "archimind-style-test-"));
  try {
    const home = JSON.parse(
      await readFile(new URL("../town/showcase.json", import.meta.url), "utf8"),
    );
    const snapshot = { home, project: "style-export-test", revision: 1 };
    const snapshotFile = join(dir, "snapshot.json");
    const boardFile = join(dir, "board.json");
    const resultFile = join(dir, "style.json");
    const board = manifestText(homeBoard(snapshot));
    await writeFile(snapshotFile, JSON.stringify(snapshot));
    await writeFile(boardFile, board);
    const run = () =>
      spawnSync(
        process.execPath,
        [command, snapshotFile, boardFile, resultFile],
        { encoding: "utf8" },
      );
    const first = run();
    assert.equal(first.status, 0, first.stderr);
    const result = JSON.parse(await readFile(resultFile, "utf8"));
    assert.equal(result.home_id, home.id);
    assert.equal(
      result.manifest_sha256,
      createHash("sha256").update(board).digest("hex"),
    );
    assert.deepEqual(
      result.rooms.map((r) => r.id),
      home.rooms.map((p) => p.design.room.id),
    );
    const bedroom = result.rooms.find((r) => r.id === "bedroom");
    assert.ok(bedroom.placed.includes("desk-chair"));
    assert.ok(bedroom.placed.includes("queen-bed"));
    assert.ok(
      bedroom.models.every(
        (m) => /^[0-9a-f]{64}$/.test(m.sha256) && m.matrix.length === 16,
      ),
    );
    assert.ok(
      bedroom.shapes.some(
        (s) => s.group === "decor/plant" && s.triangles.length > 0,
      ),
    );
    await writeFile(boardFile, board.replace(home.id, "a".repeat(64)));
    const stale = run();
    assert.notEqual(stale.status, 0);
    assert.match(stale.stderr, /exact approved Town manifest/);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
