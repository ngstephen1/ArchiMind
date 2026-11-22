import * as THREE from "three";
import { buildDressing } from "../src/dressing.js";

/** Refine Town's saved curtain and plant boxes while sharing the regular dressing loader. */
export function buildTownDressing(group, dressing, pack, tier) {
  const result = buildDressing(group, dressing, pack, tier);
  const geometries = [], materials = [];
  const mat = (color, extra = {}) => {
    const material = new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...extra });
    materials.push(material);
    return material;
  };
  const part = (geometry, material, x, y, z) => {
    geometries.push(geometry);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    return mesh;
  };
  const refinements = {
    curtain: (w, h, d, item) => {
      const linen = mat('#ece6dc', { roughness: 0.94, side: THREE.DoubleSide });
      const alongX = item.wall === 'north' || item.wall === 'south';
      const span = alongX ? w : d;
      const thickness = alongX ? d : w;
      return [-1, 1].map(side => {
        const panel = new THREE.PlaneGeometry(span * 0.22, h, 30, 3);
        const rows = panel.attributes.position;
        for (let i = 0; i < rows.count; i++) {
          const u = rows.getX(i) / (span * 0.22) + 0.5;
          const along = side * span * 0.38 + rows.getX(i);
          const fold = thickness * (0.39 * Math.sin(u * Math.PI * 12));
          rows.setXYZ(i, alongX ? along : fold, rows.getY(i), alongX ? fold : along);
        }
        panel.computeVertexNormals();
        return part(panel, linen, 0, h / 2, 0);
      });
    },
    plant: (w, h, d) => {
      const span = Math.min(w, d);
      const pieces = [part(new THREE.CylinderGeometry(span * 0.32, span * 0.26, h * 0.3, 16), mat('#b9a58c'), 0, h * 0.15, 0)];
      const stems = mat('#534534', { roughness: 0.82 });
      pieces.push(part(new THREE.CylinderGeometry(0.009, 0.014, h * 0.6, 8), stems, 0, h * 0.54, 0));
      const leaves = ['#365834', '#45683c', '#627e45'].map(color => mat(color, { roughness: 0.67 }));
      for (let i = 0; i < 21; i++) {
        const angle = i * 2.399963;
        const breadth = span * (0.13 + (i % 4) * 0.018);
        const distance = span * (0.16 + (i % 3) * 0.048);
        const leaf = new THREE.SphereGeometry(1, 8, 6);
        leaf.scale(breadth, h * 0.034, breadth * 0.31);
        leaf.rotateZ(i % 2 ? 0.48 : -0.48).rotateY(-angle);
        const x = Math.cos(angle) * distance, z = Math.sin(angle) * distance;
        const rise = h * (0.47 + 0.020 * i);
        pieces.push(part(leaf, leaves[i % 3], x, rise, z));
        const branch = new THREE.Vector3(x, h * 0.075, z);
        const twig = new THREE.CylinderGeometry(0.003, 0.004, branch.length(), 5);
        twig.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), branch.normalize()));
        pieces.push(part(twig, stems, x / 2, rise - h * 0.0375, z / 2));
      }
      return pieces;
    },
  };
  for (const item of dressing) {
    if (!item.refined || item.asset_id || !Object.hasOwn(refinements, item.kind)) continue;
    const holder = result.root.children.find(child => child.name === item.id);
    if (!holder) continue;
    holder.clear();
    holder.add(...refinements[item.kind](item.width_m, item.height_m, item.depth_m, item));
  }
  return {
    ...result,
    dispose() {
      result.dispose();
      geometries.forEach(geometry => geometry.dispose());
      materials.forEach(material => material.dispose());
    },
  };
}
