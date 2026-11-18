// Swap a room's procedural furniture for the pack models its style bindings
// name. The binding already guarantees the model fits inside the reservation,
// so models are never scaled: they are floor-centred on it.
// Room frame: three.x = x_m (east), three.y = up, three.z = -y_m (north).
import * as THREE from 'three';

export function placePackModel(model, f) {
  const holder = new THREE.Group();
  holder.add(model);
  model.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(model);
  const centre = box.getCenter(new THREE.Vector3());
  model.position.x -= centre.x;
  model.position.z -= centre.z;
  model.position.y -= box.min.y;
  holder.position.set(f.x_m + f.width_m / 2, 0, -(f.y_m + f.depth_m / 2));
  holder.userData.packFurniture = f.id;
  holder.traverse(o => { if (o.isMesh) o.castShadow = o.receiveShadow = true; });
  return holder;
}

/**
 * objects: Map furniture_id -> Object3D[] currently drawing that item.
 * Returns {ready: Promise<{placed, failed}>, undo()}.
 */
export function dressFurniture({ bindings, furniture, pack, objects, parent }) {
  const byId = new Map(furniture.map(f => [f.id, f]));
  const placed = [], failed = [], added = [], hidden = [];
  let undone = false;
  const jobs = bindings
    .filter(b => b.reason === 'pack' && b.asset_id && byId.has(b.furniture_id))
    .map(async b => {
      let model = null;
      try { model = await pack.model(b.asset_id); } catch { model = null; }
      if (undone) return;
      if (!model) { failed.push(b.furniture_id); return; }
      const holder = placePackModel(model, byId.get(b.furniture_id));
      parent.add(holder);
      added.push(holder);
      for (const o of objects.get(b.furniture_id) || []) {
        if (o.visible) { o.visible = false; hidden.push(o); }
      }
      placed.push(b.furniture_id);
    });
  const ready = Promise.all(jobs).then(() => ({ placed: [...placed].sort(), failed: [...failed].sort() }));
  return {
    ready,
    undo() {
      undone = true;
      added.forEach(o => o.removeFromParent());
      hidden.forEach(o => { o.visible = true; });
      added.length = hidden.length = 0;
    },
  };
}
