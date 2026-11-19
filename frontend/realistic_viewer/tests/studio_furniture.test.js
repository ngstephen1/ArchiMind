import test from "node:test";
import assert from "node:assert/strict";
import { studioFurniture, studioFinishes } from "../town/studio_furniture.js";

test("salon families stay within their reserved footprint at nonzero origins", () => {
  for (const [id, w, d, h] of [
    ["salon-suite", 2.8, 2.35, 0.94],
    ["salon-dining", 2.2, 2.92, 1],
  ]) {
    const pieces = studioFurniture({
      id,
      width_m: w,
      depth_m: d,
      height_m: h,
      x_m: 1.3,
      y_m: 2.7,
    });
    assert.ok(pieces.length > 30);
    for (const p of pieces) {
      assert.ok(Object.hasOwn(studioFinishes, p.finish));
      for (const [i, [origin, size]] of [
        [1.3, w],
        [2.7, d],
        [0, h],
      ].entries()) {
        assert.ok(p.wdh[i] > 0);
        assert.ok(p.xyz[i] - p.wdh[i] / 2 >= origin - 1e-7, p.name);
        assert.ok(p.xyz[i] + p.wdh[i] / 2 <= origin + size + 1e-7, p.name);
      }
    }
  }
});

test("a quarter turn swaps the design envelope and preserves every part", () => {
  const f = {
    id: "salon-suite",
    x_m: 2,
    y_m: 1,
    width_m: 2.35,
    depth_m: 2.8,
    height_m: 0.94,
  };
  const parts = studioFurniture(f, 90);
  for (const p of parts) {
    assert.ok(
      p.xyz[0] - p.wdh[0] / 2 >= 2 - 1e-8 &&
        p.xyz[0] + p.wdh[0] / 2 <= 4.35 + 1e-8,
    );
    assert.ok(
      p.xyz[1] - p.wdh[1] / 2 >= 1 - 1e-8 &&
        p.xyz[1] + p.wdh[1] / 2 <= 3.8 + 1e-8,
    );
  }
  assert.throws(() => studioFurniture(f, 33));
});
