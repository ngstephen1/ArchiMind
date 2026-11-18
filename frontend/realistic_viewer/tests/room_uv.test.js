import test from "node:test";
import assert from "node:assert/strict";
import { quadGeometry, wallUV } from "../src/room_objects.js";

test("wall quads carry UVs spanning the wall so pack textures tile across it", () => {
  const room = { width_m: 4, depth_m: 3, ceiling_height_m: 2.5 };
  const quad = [[0, 3, 0], [4, 3, 0], [4, 3, 2.5], [0, 3, 2.5]];
  const g = quadGeometry([quad], wallUV(room, "north"));
  assert.deepEqual(Array.from(g.getAttribute("uv").array), [0, 0, 1, 0, 1, 1, 0, 1]);
  const east = quadGeometry([[[4, 0, 0], [4, 1.5, 0], [4, 1.5, 1.25], [4, 0, 1.25]]], wallUV(room, "east"));
  assert.deepEqual(Array.from(east.getAttribute("uv").array), [0, 0, 0.5, 0, 0.5, 0.5, 0, 0.5]);
  // Without a UV function the geometry is exactly as before.
  assert.equal(quadGeometry([quad]).getAttribute("uv"), undefined);
});
