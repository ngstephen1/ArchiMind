import test from "node:test";
import assert from "node:assert/strict";
import * as T from "three";
import { buildDressing, drawOrder, PRIORITY } from "../src/dressing.js";

const box = (id, kind, extra = {}) => ({
  id, kind, asset_id: null, x_m: 1, y_m: 1, z_m: 0, width_m: 0.4, depth_m: 0.4, height_m: 1, wall: null, rotation_deg: 0, ...extra,
});
const pack = (models = {}) => ({
  manifest: { plan_theme: { furniture_fill: "#d8c8b0", door_color: "#a08262" }, surfaces: { trim: { fallback_color: "#3d3127" }, metal: { fallback_color: "#3a3a38" } } },
  surface: () => null,
  model: async (id) => (models[id] ? models[id]() : null),
});

test("low tier draws half the items in priority order", async () => {
  const items = [box("plant", "plant"), box("moulding:north", "moulding"), box("art", "art"), box("rug", "rug", { height_m: 0.012 }),
    box("pendant", "pendant"), box("curtain:w", "curtain")];
  assert.deepEqual(drawOrder(items, "high").map((i) => i.kind), ["rug", "curtain", "pendant", "art", "plant", "moulding"]);
  assert.deepEqual(drawOrder(items, "low").map((i) => i.id), ["rug", "curtain:w", "pendant"]);
  assert.deepEqual(PRIORITY, ["rug", "curtain", "pendant", "art", "accent", "plant", "floor_lamp", "moulding"]);
  const group = new T.Group();
  const handle = buildDressing(group, items, pack(), "low");
  await handle.ready;
  assert.deepEqual(handle.root.children.map((c) => c.name), ["rug", "curtain:w", "pendant"]);
  handle.dispose();
  assert.equal(group.children.length, 0);
});

test("items sit in room coordinates: x east, z = -y north, y up", async () => {
  const group = new T.Group();
  const handle = buildDressing(group, [box("rug", "rug", { x_m: 1, y_m: 2, width_m: 2, depth_m: 1, height_m: 0.012 })], pack(), "high");
  await handle.ready;
  const rug = handle.root.getObjectByName("rug");
  const b = new T.Box3().setFromObject(rug);
  assert.deepEqual([b.min.x, b.max.x].map((v) => +v.toFixed(3)), [1, 3]);
  assert.deepEqual([b.min.z, b.max.z].map((v) => +v.toFixed(3)), [-3, -2]);
  assert.ok(Math.abs(b.min.y) < 1e-9);
  handle.dispose();
});

test("missing model for accent renders nothing and reports it", async () => {
  const group = new T.Group();
  const stool = () => new T.Mesh(new T.BoxGeometry(0.4, 0.45, 0.4));
  const items = [box("accent:0", "accent", { asset_id: "polyhaven:gone" }), box("accent:1", "accent", { asset_id: "polyhaven:stool" })];
  const handle = buildDressing(group, items, pack({ "polyhaven:stool": stool }), "high");
  assert.deepEqual(await handle.ready, ["accent:0"]);
  assert.equal(handle.root.getObjectByName("accent:0"), undefined);
  assert.ok(handle.root.getObjectByName("accent:1"));
  handle.dispose();
});

test("a dressing model that fails to load falls back to the procedural shape", async () => {
  const group = new T.Group();
  const handle = buildDressing(group, [box("plant", "plant", { asset_id: "polyhaven:gone" })], pack(), "high");
  assert.deepEqual(await handle.ready, []);
  assert.ok(handle.root.getObjectByName("plant").children.length > 0);
  handle.dispose();
});

test("art on an east or west wall insets its canvas along the wall, not through it", async () => {
  const group = new T.Group();
  const art = box("art", "art", { wall: "east", width_m: 0.03, depth_m: 1.2, height_m: 0.9, z_m: 1.05 });
  const handle = buildDressing(group, [art], pack(), "high");
  await handle.ready;
  const [frame, canvas] = handle.root.getObjectByName("art").children;
  const size = (m) => new T.Box3().setFromObject(m).getSize(new T.Vector3());
  assert.ok(size(canvas).z < size(frame).z, "canvas narrower along the wall");
  assert.ok(size(canvas).x > size(frame).x, "canvas stands proud of the frame");
  handle.dispose();
});
