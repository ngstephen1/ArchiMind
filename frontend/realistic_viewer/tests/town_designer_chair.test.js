import test from "node:test";
import assert from "node:assert/strict";
import { BoxGeometry, Group, Mesh } from "three";
import { fitBedroomChair } from "../town/designer_chair.js";

const seat = { x_m: 1, y_m: 2, width_m: .48, depth_m: .52, height_m: .83, rotation_deg: 0 };

function arrangement() {
  const room = new Group(), fallback = new Group(), model = new Group();
  room.add(fallback);
  const body = new Mesh(new BoxGeometry(.48, .83, .52));
  body.position.y = .83 / 2;
  model.add(body);
  return { room, fallback, model };
}

for (const side of [1, -1])
  test("native chair fits the saved slot and faces the desk on side " + side, async () => {
    const {room, fallback, model} = arrangement();
    const status = await fitBedroomChair(Promise.resolve(model), fallback, seat, side, () => true, assert.fail);
    assert.equal(status, "verified");
    assert.deepEqual(room.children, [model]);
    assert.equal(fallback.parent, null);
    assert.deepEqual(model.scale.toArray(), [1,1,1]);
    assert.deepEqual(model.position.toArray(), [1.24, 0, -2.26]);
    assert.equal(model.rotation.y, side === 1 ? Math.PI : 0);
  });

test("missing, corrupt, displaced or oversized chair retains its procedural reservation", async () => {
  for (const fault of ["unavailable", "displaced", "oversized", "nonfinite"]) {
    const {room, fallback, model} = arrangement();
    if (fault === "displaced") model.position.y = .01;
    if (fault === "oversized") model.scale.x = 1.1;
    if (fault === "nonfinite") model.position.z = NaN;
    const source = fault === "unavailable" ? Promise.reject(Error("Failed integrity check")) : Promise.resolve(model);
    const disposed = [];
    assert.equal(await fitBedroomChair(source, fallback, seat, 1, () => true, o => disposed.push(o)), "placeholder");
    assert.deepEqual(room.children, [fallback]);
    assert.deepEqual(disposed, fault === "unavailable" ? [] : [model]);
  }
});

test("superseded native chair is disposed before editing either room", async () => {
  const {room, fallback, model} = arrangement();
  const disposed = [];
  assert.equal(await fitBedroomChair(Promise.resolve(model), fallback, seat, 1, () => false, o => disposed.push(o)), "superseded");
  assert.deepEqual(room.children, [fallback]);
  assert.deepEqual(disposed, [model]);
});
