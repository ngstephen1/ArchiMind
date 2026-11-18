// Plan ↔ Room: a pure view change between a line drawing (white surfaces, dark
// edges) and the full render. Between the two, a vertical clipping plane
// sweeps along X: rendered on the near (west) side, line drawing beyond it.
import * as THREE from 'three';

export const EDGE_THRESHOLD_DEG = 25;
const EPS = 1e-6;

export function createPlanSweep({ renderer, root }) {
  const white = new THREE.MeshBasicMaterial({ color: '#ffffff' });
  const ink = new THREE.LineBasicMaterial({ color: '#2b2b2b' });
  const renderPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
  const linePlane = new THREE.Plane(new THREE.Vector3(1, 0, 0), 0);
  const whiteClipped = white.clone();
  whiteClipped.clippingPlanes = [linePlane];
  const inkClipped = ink.clone();
  inkClipped.clippingPlanes = [linePlane];
  const legacyClipping = renderer.localClippingEnabled;
  const state = new Map(); // mesh -> {original, clone, edges, overlay}
  let cut = 0;

  const meshes = () => {
    const out = [];
    root.traverse(o => { if (o.isMesh && !o.userData.sweepOwned && !o.userData.noSweep) out.push(o); });
    return out;
  };
  const extentBox = () => {
    const box = new THREE.Box3();
    root.updateMatrixWorld(true);
    for (const mesh of meshes()) box.expandByObject(mesh);
    return box.isEmpty() ? [0, 0] : [box.min.x, box.max.x];
  };
  let [minX, maxX] = extentBox();

  function entry(mesh) {
    if (!state.has(mesh)) state.set(mesh, { original: mesh.material, clone: null, edges: null, overlay: null });
    return state.get(mesh);
  }
  function edgesFor(mesh, s) {
    if (!s.edges) {
      s.edges = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, EDGE_THRESHOLD_DEG), ink);
      s.edges.userData.sweepOwned = true;
      s.edges.raycast = () => {};
      mesh.add(s.edges);
    }
    return s.edges;
  }
  function overlayFor(mesh, s) {
    if (!s.overlay) {
      s.overlay = new THREE.Mesh(mesh.geometry, whiteClipped);
      s.overlay.userData.sweepOwned = true;
      s.overlay.raycast = () => {};
      mesh.add(s.overlay);
    }
    return s.overlay;
  }
  function dropClone(s) {
    if (s.clone) { s.clone.dispose(); s.clone = null; }
  }
  function restore() {
    for (const [mesh, s] of state) {
      mesh.material = s.original;
      dropClone(s);
      if (s.edges) s.edges.visible = false;
      if (s.overlay) s.overlay.visible = false;
    }
    renderer.localClippingEnabled = legacyClipping;
  }

  function set(t) {
    t = Math.min(1, Math.max(0, Number(t) || 0));
    [minX, maxX] = extentBox();
    cut = minX + t * (maxX - minX);
    if (t >= 1 - EPS) { restore(); return; }
    renderPlane.constant = cut;
    linePlane.constant = -cut;
    const full = t <= EPS;
    renderer.localClippingEnabled = full ? legacyClipping : true;
    for (const mesh of meshes()) {
      const s = entry(mesh);
      const edges = edgesFor(mesh, s);
      edges.material = full ? ink : inkClipped;
      edges.visible = true;
      if (full) {
        dropClone(s);
        mesh.material = white;
        if (s.overlay) s.overlay.visible = false;
      } else {
        if (!s.clone) {
          // Clone, never mutate, so shared materials stay untouched.
          s.clone = Array.isArray(s.original) ? null : s.original.clone();
          if (s.clone) s.clone.clippingPlanes = [renderPlane];
        }
        mesh.material = s.clone || s.original;
        overlayFor(mesh, s).visible = true;
      }
    }
  }

  function dispose() {
    restore();
    for (const s of state.values()) {
      if (s.edges) { s.edges.removeFromParent(); s.edges.geometry.dispose(); }
      if (s.overlay) s.overlay.removeFromParent();
    }
    state.clear();
    [white, ink, whiteClipped, inkClipped].forEach(m => m.dispose());
  }

  return { set, dispose, position: () => cut, extent: () => [minX, maxX] };
}
