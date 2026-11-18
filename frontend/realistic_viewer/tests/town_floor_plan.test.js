import assert from "node:assert/strict";
import test from "node:test";
import { openingEndpoints } from "../town/floor_plan.js";

test("presentation preserves opening offsets along all four measured walls", () => {
  const room = {width_m: 5, depth_m: 4};
  const expected = {
    north: [[1, 4], [2.5, 4]], south: [[1, 0], [2.5, 0]],
    east: [[5, 1], [5, 2.5]], west: [[0, 1], [0, 2.5]],
  };
  for (const [wall, ends] of Object.entries(expected)) {
    assert.deepEqual(openingEndpoints(room, {wall, offset_m: 1, width_m: 1.5}), ends);
  }
});
