import test from "node:test";
import assert from "node:assert/strict";
import * as T from "three";
import { townSurfaceSource, LEGACY_WALL_COLORS, dressWhenCurrent, dressTownSurfaces } from "../town/style_source.js";

test("legacy home uses its palette wall colour and no pack", () => {
  assert.deepEqual(townSurfaceSource({ palette: "sage" }), { kind: "legacy", wallColor: "#bac6ad" });
  assert.deepEqual(townSurfaceSource({ palette: "oak" }), { kind: "legacy", wallColor: "#e5d6bc" });
  assert.deepEqual(townSurfaceSource({ palette: "terracotta" }), { kind: "legacy", wallColor: "#d8ab91" });
  assert.equal(LEGACY_WALL_COLORS.terracotta, "#d8ab91");
});

test("home with a style pack is dressed from that pack", () => {
  const h = { palette: "sage", style_pack: { id: "japandi", version: "1.0.0" } };
  assert.deepEqual(townSurfaceSource(h), { kind: "pack", ref: { id: "japandi", version: "1.0.0" } });
});

test("malformed style pack records fall back to the legacy path", () => {
  for (const style_pack of [{ id: "gothic", version: "1.0.0" }, { id: "japandi" }, "japandi", null])
    assert.equal(townSurfaceSource({ palette: "oak", style_pack }).kind, "legacy");
});

test("a pack load superseded by load(h2) never touches h2's interior", async () => {
  let generation = 1, disposed = 0;
  const epoch = generation;
  let release;
  const source = new Promise((resolve) => (release = resolve));
  const pending = dressWhenCurrent(source, () => generation === epoch, () => assert.fail("must not dress h2"));
  generation++; // world.load(h2)
  release({ failures: [], dispose: () => disposed++ });
  assert.equal(await pending, "superseded");
  assert.equal(disposed, 1);
});

test("a current pack load dresses and reports fallbacks; a failed load leaves the legacy look", async () => {
  const pack = { failures: ["wall"], unreleased: [], dispose: assert.fail };
  let dressed = null;
  assert.equal(await dressWhenCurrent(Promise.resolve(pack), () => true, (p) => (dressed = p)), "partial");
  assert.equal(dressed, pack);
  assert.equal(await dressWhenCurrent(Promise.reject(Error("Style pack unavailable")), () => true, assert.fail), "unavailable");
  assert.equal(await dressWhenCurrent(Promise.resolve("superseded"), () => true, assert.fail), "superseded");
});

test("tagged interior meshes take tiled pack surfaces and the undo restores shared materials", () => {
  const shared = new T.MeshStandardMaterial({ color: "#e5d6bc" });
  const wall = new T.Mesh(new T.BoxGeometry(), shared);
  wall.scale.set(4, 2.8, 0.1);
  wall.userData.surface = "wall";
  const floor = new T.Mesh(new T.BoxGeometry(), shared);
  floor.scale.set(3, 0.014, 5);
  floor.userData.surface = "floor";
  const plain = new T.Mesh(new T.BoxGeometry(), shared);
  const group = new T.Group();
  group.add(wall, floor, plain);
  const make = (tiling) => {
    const m = new T.MeshStandardMaterial({ map: new T.Texture() });
    m.userData.tiling_m = tiling;
    return m;
  };
  const surfaces = { wall: make(2), floor: make(1.5) };
  const pack = { surface: (role) => surfaces[role] || null };
  const undo = dressTownSurfaces(group, pack);
  assert.deepEqual(wall.material.map.repeat.toArray(), [2, 1.4]);
  assert.deepEqual(floor.material.map.repeat.toArray(), [2, 5 / 1.5]);
  assert.equal(plain.material, shared);
  undo();
  assert.equal(wall.material, shared);
  assert.equal(floor.material, shared);
});
