// Draw a room's style-pack dressing (rug, art, curtains, mouldings, pendant,
// plants, floor lamps, accent furniture) from the Python-placed boxes.
// Room frame: three.x = x_m (east), three.y = up, three.z = -y_m (north).
import * as THREE from 'three';

export const PRIORITY = Object.freeze(['rug', 'curtain', 'pendant', 'art', 'accent', 'plant', 'floor_lamp', 'moulding']);
const MODEL_KINDS = new Set(['pendant', 'plant', 'floor_lamp', 'accent']);

/** Items in draw priority; the low tier keeps the first half (rounded up). */
export function drawOrder(items, tier) {
  const sorted = items
    .map((item, index) => [item, index])
    .filter(([item]) => PRIORITY.includes(item.kind))
    .sort((a, b) => PRIORITY.indexOf(a[0].kind) - PRIORITY.indexOf(b[0].kind) || a[1] - b[1])
    .map(([item]) => item);
  return tier === 'low' ? sorted.slice(0, Math.ceil(sorted.length * 0.5)) : sorted;
}

const fallback = (pack, role, color) => pack?.manifest?.surfaces?.[role]?.fallback_color || color;

export function buildDressing(group, dressing, pack, tier) {
  const root = new THREE.Group();
  root.name = 'dressing';
  group.add(root);
  const geometries = [], materials = [], missing = [], pending = [];
  const theme = pack?.manifest?.plan_theme || {};
  const mat = (color, extra = {}) => {
    const m = new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, ...extra });
    materials.push(m);
    return m;
  };
  const geo = g => (geometries.push(g), g);
  const part = (geometry, material, x, y, z) => {
    const mesh = new THREE.Mesh(geo(geometry), material);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    return mesh;
  };
  const shapes = {
    rug: (w, h, d) => [part(new THREE.BoxGeometry(w, h, d), mat(theme.furniture_fill || '#d8cfc2', { roughness: 1 }), 0, h / 2, 0)],
    curtain: (w, h, d, item) => {
      const linen = mat('#ece6dc', { roughness: 0.94, side: THREE.DoubleSide });
      if (!item.refined) return [part(new THREE.BoxGeometry(w, h, d), linen, 0, h / 2, 0)];
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
    moulding: (w, h, d) => {
      const trim = pack?.surface?.('trim');
      return [part(new THREE.BoxGeometry(w, h, d), trim || mat(fallback(pack, 'trim', '#f4f3ef')), 0, h / 2, 0)];
    },
    art: (w, h, d, item) => {
      // Inset the canvas along the wall and let it stand proud of the frame.
      const alongX = item.wall !== 'east' && item.wall !== 'west';
      const cw = alongX ? w * 0.86 : w * 1.2, cd = alongX ? d * 1.2 : d * 0.86;
      return [
        part(new THREE.BoxGeometry(w, h, d), mat(fallback(pack, 'metal', '#3a3a38'), { metalness: 0.4, roughness: 0.5 }), 0, h / 2, 0),
        part(new THREE.BoxGeometry(cw, h * 0.84, cd), mat(theme.door_color || '#a08262'), 0, h / 2, 0),
      ];
    },
    pendant: (w, h) => {
      const shade = Math.min(0.3, h * 0.45);
      return [
        part(new THREE.CylinderGeometry(0.006, 0.006, h - shade, 6), mat('#222222'), 0, shade + (h - shade) / 2, 0),
        part(new THREE.SphereGeometry(w / 2, 20, 12), mat('#f4ead8', { emissive: '#ffdcae', emissiveIntensity: 0.6, roughness: 0.9 }), 0, shade / 2, 0),
      ];
    },
    plant: (w, h, d, item) => {
      const span = Math.min(w, d);
      const pieces = [part(new THREE.CylinderGeometry(span * 0.32, span * 0.26, h * 0.3, 16), mat('#b9a58c'), 0, h * 0.15, 0)];
      if (!item.refined) return [...pieces, part(new THREE.IcosahedronGeometry(w * 0.48, 1), mat('#5f7a4f', { roughness: 0.9 }), 0, h * 0.62, 0)];
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
    floor_lamp: (w, h) => [
      part(new THREE.CylinderGeometry(w * 0.35, w * 0.4, 0.03, 20), mat('#2b2b2b', { metalness: 0.5 }), 0, 0.015, 0),
      part(new THREE.CylinderGeometry(0.012, 0.012, h * 0.8, 8), mat('#2b2b2b', { metalness: 0.5 }), 0, h * 0.4, 0),
      part(new THREE.CylinderGeometry(w * 0.3, w * 0.5, h * 0.2, 20, 1, true), mat('#efe6d6', { side: THREE.DoubleSide, emissive: '#ffdcae', emissiveIntensity: 0.4 }), 0, h * 0.9, 0),
    ],
  };
  for (const item of drawOrder(dressing, tier)) {
    const holder = new THREE.Group();
    holder.name = item.id;
    holder.userData.dressingKind = item.kind;
    holder.position.set(item.x_m + item.width_m / 2, item.z_m, -(item.y_m + item.depth_m / 2));
    const procedural = () => {
      // Wall-mounted boxes are stored already rotated; draw them axis-aligned.
      for (const mesh of shapes[item.kind](item.width_m, item.height_m, item.depth_m, item)) holder.add(mesh);
    };
    if (MODEL_KINDS.has(item.kind) && item.asset_id) {
      pending.push(Promise.resolve(pack?.model?.(item.asset_id)).catch(() => null).then(model => {
        if (model) {
          model.rotation.y = -THREE.MathUtils.degToRad(item.rotation_deg || 0);
          holder.add(model);
          root.add(holder);
        } else if (item.kind === 'accent') {
          missing.push(item.id);
        } else {
          procedural();
          root.add(holder);
        }
      }));
      continue;
    }
    if (item.kind === 'accent') { missing.push(item.id); continue; }
    procedural();
    root.add(holder);
  }
  // Keep children in draw order regardless of which model resolved first.
  const ready = Promise.all(pending).then(() => {
    const order = new Map(drawOrder(dressing, tier).map((item, i) => [item.id, i]));
    root.children.sort((a, b) => order.get(a.name) - order.get(b.name));
    return missing;
  });
  return {
    root,
    ready,
    missing,
    dispose() {
      root.removeFromParent();
      geometries.forEach(g => g.dispose());
      materials.forEach(m => m.dispose());
    },
  };
}
