import test from "node:test";
import assert from "node:assert/strict";
import { FLOOR_SLAB, dressingOrigin } from "../town/floor.js";

test("room dressing stands on the top of the Town floor slab, not inside it", () => {
  const top = FLOOR_SLAB.centerY + FLOOR_SLAB.height / 2;
  assert.ok(Math.abs(top - 0.015) < 1e-9);
  // A 12 mm rug must clear the slab.
  assert.deepEqual(dressingOrigin({ origin: [3, 4] }), [3, top, -4]);
});
