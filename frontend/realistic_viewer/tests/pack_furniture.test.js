import test from "node:test";
import assert from "node:assert/strict";
import * as T from "three";
import { placePackModel, dressFurniture, furnitureFallbackText } from "../src/pack_furniture.js";

const sofa = { id: "sofa", category: "sofa", x_m: 1, y_m: 2, width_m: 2, depth_m: 0.9, height_m: 0.86, rotation_deg: 0 };
const model = () => {
  // Origin off-centre and below the floor: placement must not trust it.
  const m = new T.Mesh(new T.BoxGeometry(1.8, 0.8, 0.8));
  m.position.set(0.3, -0.1, 0.2);
  const g = new T.Group();
  g.add(m);
  return g;
};

test("a pack model sits floor-centred on its reservation (x east, z = -y)", () => {
  const placed = placePackModel(model(), sofa);
  const b = new T.Box3().setFromObject(placed);
  const c = b.getCenter(new T.Vector3());
  assert.ok(Math.abs(c.x - 2) < 1e-9 && Math.abs(c.z + 2.45) < 1e-9);
  assert.ok(Math.abs(b.min.y) < 1e-9);
  assert.equal(placed.userData.packFurniture, "sofa");
});

test("bound items swap to models, unbound and failed ones keep their procedural object; undo restores", async () => {
  const parent = new T.Group();
  const objects = new Map([["sofa", [new T.Mesh()]], ["table", [new T.Mesh()]], ["bed", [new T.Mesh()]]]);
  const furniture = [sofa, { ...sofa, id: "table" }, { ...sofa, id: "bed" }];
  const bindings = [
    { furniture_id: "sofa", asset_id: "polyhaven:Sofa_01", reason: "pack" },
    { furniture_id: "table", asset_id: "polyhaven:gone", reason: "pack" },
    { furniture_id: "bed", asset_id: null, reason: "procedural_fallback" },
  ];
  const pack = { model: async (id) => (id === "polyhaven:Sofa_01" ? model() : null) };
  const handle = dressFurniture({ bindings, furniture, pack, objects, parent });
  assert.deepEqual(await handle.ready, { placed: ["sofa"], failed: ["table"] });
  assert.equal(objects.get("sofa")[0].visible, false);
  assert.equal(objects.get("table")[0].visible, true);
  assert.equal(parent.children.length, 1);
  handle.undo();
  assert.equal(objects.get("sofa")[0].visible, true);
  assert.equal(parent.children.length, 0);
});

test("an undo before models arrive leaves nothing behind", async () => {
  const parent = new T.Group();
  const objects = new Map([["sofa", [new T.Mesh()]]]);
  let release;
  const pack = { model: () => new Promise((r) => (release = r)) };
  const handle = dressFurniture({ bindings: [{ furniture_id: "sofa", asset_id: "polyhaven:Sofa_01", reason: "pack" }], furniture: [sofa], pack, objects, parent });
  handle.undo();
  release(model());
  await handle.ready;
  assert.equal(parent.children.length, 0);
  assert.equal(objects.get("sofa")[0].visible, true);
});

test("the status names furniture whose pack model failed, by its display name", () => {
  const furniture = [{ id: "sofa", name: "Sofa" }, { id: "t", name: "Coffee table" }];
  assert.equal(furnitureFallbackText(["t", "sofa"], furniture), "Fallback furniture: Coffee table, Sofa");
  assert.equal(furnitureFallbackText([], furniture), "");
});
