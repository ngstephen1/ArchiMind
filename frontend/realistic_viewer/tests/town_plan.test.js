import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { planColors, LEGACY_PLAN_COLORS } from "../town/plan_colors.js";

const manifest = (id) =>
  JSON.parse(readFileSync(new URL(`../../../src/archimind/_viewer_assets/packs/${id}.json`, import.meta.url)));

test("planColors legacy matches old palette map", () => {
  const legacy = { site: "#e2d3af", room: "#f9f6ec", wall: "#46584a", furniture: "#b5bfac", furnitureStroke: null,
    door: "#dfb855", window: "#609aab", label: "#233e35" };
  assert.deepEqual(LEGACY_PLAN_COLORS, legacy);
  assert.deepEqual(planColors({ palette: "sage" }, null), legacy);
  // A home without a pack ignores any manifest; a mismatched version also stays legacy.
  assert.deepEqual(planColors({ palette: "oak" }, manifest("japandi")), legacy);
  assert.deepEqual(planColors({ style_pack: { id: "japandi", version: "9.9.9" } }, manifest("japandi")), legacy);
  assert.deepEqual(planColors({ style_pack: { id: "japandi", version: "1.0.0" } }, manifest("scandinavian")), legacy);
});

test("pack theme overrides", () => {
  const m = manifest("mid_century");
  const c = planColors({ style_pack: { id: "mid_century", version: m.version } }, m);
  const t = m.plan_theme;
  assert.deepEqual(c, { site: LEGACY_PLAN_COLORS.site, room: t.floor_fill, wall: t.wall_stroke, furniture: t.furniture_fill,
    furnitureStroke: t.furniture_stroke, door: t.door_color, window: t.window_color, label: t.label_color });
});
