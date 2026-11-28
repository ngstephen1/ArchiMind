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
  wall.userData.finishColor = "#294735";
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
  assert.equal(wall.material.color.getHexString(), "294735");
  assert.equal(surfaces.wall.color.getHexString(), "ffffff");
  assert.deepEqual(floor.material.map.repeat.toArray(), [2, 5 / 1.5]);
  assert.equal(plain.material, shared);
  undo();
  assert.equal(wall.material, shared);
  assert.equal(floor.material, shared);
});

test("style select reflects the home's pack, or its legacy palette's mapped style", async () => {
  const { homeStyle, STYLE_NAMES } = await import("../town/style_names.js");
  assert.equal(homeStyle({ palette: "sage", style_pack: { id: "industrial_loft", version: "1.0.0" } }), "industrial_loft");
  assert.equal(homeStyle({ palette: "terracotta" }), "mid_century");
  assert.equal(homeStyle({ palette: "oak", style_pack: { id: "gothic" } }), "scandinavian");
  assert.deepEqual(Object.keys(STYLE_NAMES), ["scandinavian", "modern_classic", "industrial_loft", "japandi", "mid_century"]);
});

test("Town surface undo disposes the tiled material it made, even if the sweep swapped the mesh's material", () => {
  const shared = new T.MeshStandardMaterial();
  const floor = new T.Mesh(new T.BoxGeometry(1, 1, 1), shared);
  floor.scale.set(4, 0.01, 5);
  floor.userData.surface = "floor";
  const group = new T.Group();
  group.add(floor);
  const base = new T.MeshStandardMaterial({ map: new T.Texture() });
  base.userData.tiling_m = 1;
  const undo = dressTownSurfaces(group, { surface: (r) => (r === "floor" ? base : null) });
  const tiled = floor.material;
  let disposed = false;
  tiled.addEventListener("dispose", () => (disposed = true));
  const sweepWhite = new T.MeshBasicMaterial();
  floor.material = sweepWhite; // Plan/Room sweep active during a revision switch
  undo();
  assert.ok(disposed, "the tiled material is disposed");
  assert.equal(floor.material, shared);
  assert.equal(sweepWhite.version, 0);
});

test("Town status text names pack fallbacks, failed pack furniture or an unavailable pack", async () => {
  const { townStyleStatus } = await import("../town/style_source.js");
  assert.equal(townStyleStatus({}), "");
  assert.equal(townStyleStatus({ styleState: "loading", styleFailures: "" }), "");
  assert.equal(townStyleStatus({ styleState: "ready", styleFailures: "" }), "");
  assert.equal(townStyleStatus({ styleState: "partial", styleFailures: "floor,wall" }), "Fallback materials: floor, wall");
  assert.equal(
    townStyleStatus({ styleState: "ready", styleFailures: "", styleFurniture: "Fallback furniture: Sofa" }),
    "Fallback furniture: Sofa",
  );
  assert.equal(townStyleStatus({ styleState: "unavailable" }), "Style pack unavailable; showing standard finishes.");
});

test("interior look: a pack home's environment, intensity and exposure; otherwise the Town look", async () => {
  const { interiorLook } = await import("../town/style_source.js");
  const town = { environment: "townEnv", intensity: 1, exposure: 0.9 };
  const pack = { environment: { texture: "packEnv" }, intensity: 0.6, exposure: 1.2 };
  assert.deepEqual(interiorLook(pack, town), { environment: "packEnv", intensity: 0.6, exposure: 1.2 });
  assert.deepEqual(interiorLook({ ...pack, environment: null }, town).environment, "townEnv");
  assert.deepEqual(interiorLook(null, town), town);
});
