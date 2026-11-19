import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { bedroomCameras, openingFrame } from "../town/bedroom_cameras.js";

const home = JSON.parse(
  readFileSync(new URL("../town/showcase.json", import.meta.url)),
);
const original = home.rooms.find((part) => part.design.room.id === "bedroom");
test("camera shots fit the saved bedroom in both wide and narrow lenses", () => {
  for (const aspect of [16 / 9, 390 / 699]) {
    const views = bedroomCameras(original, aspect);
    assert.deepEqual(
      views.map((v) => v.id),
      ["doorway", "desk", "bedside"],
    );
    for (const { eye, target, reason } of views) {
      assert.equal(reason, null);
      assert.equal(eye[1], 1.57);
      assert.ok(eye[0] > 0 && eye[0] < original.design.room.width_m);
      assert.ok(-eye[2] > 0 && -eye[2] < original.design.room.depth_m);
      assert.ok(target.every(Number.isFinite));
    }
  }
});
test("a changed furniture reservation moves its framed subject", () => {
  const modified = structuredClone(original);
  modified.design.furniture.find((item) => item.id === "bedside-lamp").x_m -=
    1.5;
  const previous = bedroomCameras(original),
    next = bedroomCameras(modified);
  assert.equal(next[2].reason, null);
  assert.equal(next[2].target[0], previous[2].target[0] - 1.5);
  assert.deepEqual(previous[1].target, next[1].target);
});
test("missing or obstructed detail subjects use a labeled doorway view", () => {
  const modified = structuredClone(original);
  modified.design.furniture = modified.design.furniture.filter(
    (f) => f.id !== "bedside-lamp",
  );
  modified.design.furniture.push({
    id: "closed-cabinet",
    x_m: 0,
    y_m: 0,
    width_m: 6,
    depth_m: 7,
    height_m: 2,
  });
  const [overview, desk, bedside] = bedroomCameras(modified);
  assert.match(desk.reason, /No clear view/);
  assert.match(bedside.reason, /Subject unavailable/);
  assert.deepEqual(desk.eye, overview.eye);
  assert.deepEqual(bedside.target, overview.target);
});
test("door positions follow offset and wall orientation on every wall", () => {
  const room = { width_m: 7, depth_m: 5 };
  for (const [wall, expected] of [
    ["west", [0, 2, 1, 0]],
    ["east", [7, 2, -1, 0]],
    ["north", [2, 5, 0, -1]],
    ["south", [2, 0, 0, 1]],
  ]) {
    const { x, y, nx, ny } = openingFrame(room, {
      wall,
      width_m: 1,
      offset_m: 1.5,
    });
    assert.deepEqual([x, y, nx, ny], expected);
  }
});
