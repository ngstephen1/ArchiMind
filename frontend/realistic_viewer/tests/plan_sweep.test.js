import test from "node:test";
import assert from "node:assert/strict";
import * as THREE from "three";
import { createPlanSweep, EDGE_THRESHOLD_DEG } from "../src/plan_sweep.js";

function room() {
  const root = new THREE.Group();
  const floorMat = new THREE.MeshStandardMaterial({ color: "#c9a97f" });
  const floor = new THREE.Mesh(new THREE.BoxGeometry(4, 0.1, 3), floorMat);
  floor.position.set(2, -0.05, -1.5);
  const sofaMat = new THREE.MeshStandardMaterial({ color: "#888888" });
  const sofa = new THREE.Mesh(new THREE.BoxGeometry(2, 0.8, 0.9), sofaMat);
  sofa.position.set(1.5, 0.4, -2);
  const label = new THREE.Sprite(new THREE.SpriteMaterial());
  root.add(floor, sofa, label);
  const scene = new THREE.Scene();
  scene.add(root);
  root.updateMatrixWorld(true);
  return { root, scene, floor, sofa, floorMat, sofaMat, renderer: { localClippingEnabled: false } };
}
const edges = (root) => {
  const out = [];
  root.traverse((o) => o.isLineSegments && o.userData.sweepOwned && o.visible && out.push(o));
  return out;
};

test("set(0) swaps every mesh material and adds edges", () => {
  const r = room();
  const sweep = createPlanSweep(r);
  sweep.set(0);
  for (const mesh of [r.floor, r.sofa]) {
    assert.ok(mesh.material.isMeshBasicMaterial);
    assert.equal(mesh.material.color.getHexString(), "ffffff");
  }
  const lines = edges(r.root);
  assert.equal(lines.length, 2);
  assert.equal(lines[0].geometry.parameters.thresholdAngle, EDGE_THRESHOLD_DEG);
  assert.equal(EDGE_THRESHOLD_DEG, 25);
  sweep.dispose();
});

test("set(1) restores exact original materials", () => {
  const r = room();
  const sweep = createPlanSweep(r);
  sweep.set(0);
  sweep.set(0.4);
  sweep.set(1);
  assert.equal(r.floor.material, r.floorMat);
  assert.equal(r.sofa.material, r.sofaMat);
  assert.equal(r.floorMat.clippingPlanes, null);
  assert.equal(edges(r.root).length, 0);
  assert.equal(r.renderer.localClippingEnabled, false);
  sweep.dispose();
});

test("dispose restores and frees edge geometry", () => {
  const r = room();
  const sweep = createPlanSweep(r);
  sweep.set(0.5);
  const owned = [];
  r.root.traverse((o) => o.userData.sweepOwned && owned.push(o));
  assert.ok(owned.length >= 4);
  let freed = 0;
  for (const o of owned) if (o.isLineSegments) o.geometry.addEventListener("dispose", () => freed++);
  sweep.dispose();
  assert.equal(freed, 2);
  assert.equal(r.floor.material, r.floorMat);
  const left = [];
  r.root.traverse((o) => o.userData.sweepOwned && left.push(o));
  assert.deepEqual(left, []);
});

test("sweep position maps t to room x extent", () => {
  const r = room();
  const sweep = createPlanSweep(r);
  assert.deepEqual(sweep.extent(), [0, 4]);
  sweep.set(0.25);
  assert.equal(sweep.position(), 1);
  assert.ok(r.renderer.localClippingEnabled);
  // Rendered side keeps x < cut, the line drawing keeps x > cut.
  const [render] = r.floor.material.clippingPlanes;
  assert.ok(render.distanceToPoint(new THREE.Vector3(0.5, 0, 0)) > 0);
  assert.ok(render.distanceToPoint(new THREE.Vector3(1.5, 0, 0)) < 0);
  const overlay = r.floor.children.find((c) => c.isMesh && c.userData.sweepOwned);
  assert.ok(overlay.material.clippingPlanes[0].distanceToPoint(new THREE.Vector3(1.5, 0, 0)) > 0);
  sweep.set(0.75);
  assert.equal(sweep.position(), 3);
  sweep.dispose();
});

test("a material swapped in while the sweep is active (restyle) becomes the new original", () => {
  const r = room();
  const sweep = createPlanSweep(r);
  sweep.set(0.5);
  const packFloor = new THREE.MeshStandardMaterial({ color: "#445566" });
  r.floor.material = packFloor; // a style pack lands mid-sweep
  sweep.set(0.4);
  assert.equal(r.floor.material.color.getHexString(), "445566", "sweep clones the new material");
  sweep.set(0);
  sweep.set(1);
  assert.equal(r.floor.material, packFloor, "restore returns the pack material, not the stale one");
  r.floor.material = r.floorMat; // undo restores the legacy material while the sweep is at 1
  sweep.set(0.5);
  sweep.set(1);
  assert.equal(r.floor.material, r.floorMat);
});
