import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("the Plan/Room sweep stays on one footer line so the footer keeps its height", () => {
  const css = readFileSync(new URL("../town/town.css", import.meta.url), "utf8");
  const rule = css.match(/#sweepControl\s*\{([^}]*)\}/);
  assert.ok(rule, "town.css styles #sweepControl");
  assert.match(rule[1], /display:\s*(inline-)?flex/);
  assert.match(rule[1], /white-space:\s*nowrap/);
});
