import * as T from "three";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { openingFrame } from "./bedroom_cameras.js";

export function bedroomSurfaces(renderer, materials) {
  const fabric = new T.MeshStandardMaterial({
    color: "#e6dbc5",
    roughness: 0.95,
    side: T.DoubleSide,
  });
  const veneer = new T.MeshStandardMaterial({
    color: "#bc986e",
    roughness: 0.58,
  });
  materials.set("curtain-linen", fabric);
  materials.set("bedside-veneer", veneer);
  const rug = materials.get("#bd9471");
  const loader = new T.TextureLoader();
  function loadMap(file, assign) {
    return loader.loadAsync("./assets/" + file).then((tex) => {
      tex.wrapS = tex.wrapT = T.RepeatWrapping;
      tex.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
      assign(tex);
    });
  }
  // Keep neutral fallback surfaces if a downloaded build is incomplete.
  let environment = null;
  const ready = Promise.allSettled([
    loadMap("oak-veneer-512.jpg", (tex) => {
      tex.colorSpace = T.SRGBColorSpace;
      veneer.map = tex;
      veneer.color.set("#ffffff");
      veneer.needsUpdate = true;
    }),
    loadMap("linen-weave-512.jpg", (tex) => {
      tex.colorSpace = T.SRGBColorSpace;
      fabric.map = tex;
      fabric.needsUpdate = true;
    }),
    loadMap("linen-normal-256.jpg", (tex) => {
      for (const m of [fabric, rug]) {
        m.normalMap = tex;
        m.normalScale.set(0.35, 0.35);
        m.needsUpdate = true;
      }
    }),
    new HDRLoader().loadAsync("./assets/courtyard-256.hdr").then((hdr) => {
      const pm = new T.PMREMGenerator(renderer);
      try {
        environment = pm.fromEquirectangular(hdr).texture;
      } finally {
        hdr.dispose();
        pm.dispose();
      }
    }),
  ]);
  return {
    fabric,
    veneer,
    ready,
    get environment() {
      return environment;
    },
  };
}

// These two reviewed concepts ship texture-free. Supply physical-scale UVs only
// in the viewer, leaving the source geometry, product bindings and release bytes intact.
export function finishBedroomConcept(model, surfaces) {
  model.updateMatrixWorld(true);
  model.traverse((piece) => {
    if (!piece.isMesh) return;
    const material = piece.material;
    const wood = material.name === "Oiled oak";
    const cloth = ["Oat upholstery", "Ivory linen", "Sage linen"].includes(
      material.name,
    );
    if (!wood && !cloth) return;
    const geometry = piece.geometry;
    const positions = geometry.getAttribute("position"),
      normals = geometry.getAttribute("normal");
    const uv = new Float32Array(positions.count * 2);
    const point = new T.Vector3(),
      normal = new T.Vector3();
    const transform = new T.Matrix3().getNormalMatrix(piece.matrixWorld);
    const period = wood ? 1.8 : 0.3;
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(piece.matrixWorld);
      normal.fromBufferAttribute(normals, i).applyMatrix3(transform);
      const ax = Math.abs(normal.x),
        ay = Math.abs(normal.y),
        az = Math.abs(normal.z);
      uv[i * 2] = (ax > ay && ax > az ? point.z : point.x) / period;
      uv[i * 2 + 1] = (ay > ax && ay > az ? point.z : point.y) / period;
    }
    geometry.setAttribute("uv", new T.BufferAttribute(uv, 2));
    material.map = wood ? surfaces.veneer.map : surfaces.fabric.map;
    if (cloth) {
      material.normalMap = surfaces.fabric.normalMap;
      material.normalScale.copy(surfaces.fabric.normalScale);
    }
    material.userData.townSharedMaps = true;
    material.needsUpdate = true;
  });
  return model;
}

// World-scale UVs for a box; each scan repeats at its recorded physical size.
export function scaledUV(box, period) {
  const geometry = box.geometry.clone();
  const uv = geometry.attributes.uv;
  const p = geometry.attributes.position,
    normal = geometry.attributes.normal;
  for (let i = 0; i < uv.count; i++) {
    const x = p.getX(i) * box.scale.x,
      y = p.getY(i) * box.scale.y,
      z = p.getZ(i) * box.scale.z;
    uv.setXY(
      i,
      (Math.abs(normal.getX(i)) > 0.5 ? z : x) / period[0],
      (Math.abs(normal.getY(i)) > 0.5 ? z : y) / period[1],
    );
  }
  box.geometry = geometry;
}

export function furnishedWindow(group, room, win, surfaces, block) {
  const frame = openingFrame(room, win);
  const assembly = new T.Group();
  assembly.position.set(frame.x, 0, -frame.y);
  assembly.rotation.y = Math.atan2(frame.nx, -frame.ny);
  group.add(assembly);
  const w = win.width_m,
    h = win.height_m,
    sill = win.sill_height_m,
    mid = sill + h / 2;
  const glass = block(assembly, 0, mid, 0, w, h, 0.025, "#aac9ce");
  glass.material.transparent = true;
  glass.material.opacity = 0.18;
  glass.material.depthWrite = false;
  glass.castShadow = false;
  block(assembly, 0, sill, 0, w + 0.1, 0.07, 0.19, "#e8dec9");
  block(assembly, 0, mid, 0, 0.045, h, 0.09, "#efe9dc");
  if (room.id !== "bedroom") return;
  const top = Math.min(room.ceiling_height_m - 0.12, sill + h + 0.16);
  const drop = top - 0.1;
  const tangentSpace = frame.nx ? room.depth_m : room.width_m;
  const center = win.offset_m + w / 2;
  const span = Math.min(w * 0.23, 0.4, center, tangentSpace - center);
  block(
    assembly,
    0,
    top + 0.025,
    0.13,
    Math.min(w + 0.36, 2 * center, 2 * (tangentSpace - center)),
    0.035,
    0.035,
    "#9a7546",
  );
  for (const side of [-1, 1]) {
    const cloth = new T.PlaneGeometry(span, drop, 48, 8);
    const vertices = cloth.attributes.position,
      uv = cloth.attributes.uv;
    const xCenter =
      side *
      Math.min(
        w / 2 + 0.04,
        center - span / 2,
        tangentSpace - center - span / 2,
      );
    for (let i = 0; i < vertices.count; i++) {
      const u = uv.getX(i),
        v = uv.getY(i);
      const fold = Math.cos(u * Math.PI * 10 + 0.22 * (1 - v));
      vertices.setXYZ(
        i,
        xCenter + vertices.getX(i) * (1 - 0.12 * v),
        top - drop / 2 + vertices.getY(i) + 0.016 * fold * (1 - v),
        0.13 + 0.048 * fold,
      );
      // Rough Linen spans 0.30 m vertically, at 1024 × 1026 source resolution.
      uv.setXY(i, (u * span) / ((0.3 * 1024) / 1026), (v * drop) / 0.3);
    }
    cloth.computeVertexNormals();
    const panel = new T.Mesh(cloth, surfaces.fabric);
    panel.castShadow = panel.receiveShadow = true;
    assembly.add(panel);
  }
  const light = new T.SpotLight(
    0xffefdc,
    w * h * 28,
    11,
    Math.PI * 0.43,
    0.8,
    2,
  );
  light.position.set(0, mid, 0.17);
  light.target.position.set(
    0,
    Math.max(0.1, mid - 1.0),
    Math.min(room.width_m, room.depth_m) * 0.65,
  );
  light.castShadow = true;
  light.shadow.mapSize.set(512, 512);
  light.shadow.normalBias = 0.012;
  assembly.add(light, light.target);
}
