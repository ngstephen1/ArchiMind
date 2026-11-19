// Style-pack dressing for the Studio room viewer, kept apart from WebGL so the
// decisions are testable: which scenes are styled, which pack load is still
// current, what the status line says, and how textures repeat per metre.
import * as THREE from 'three';

export const STYLE_IDS = Object.freeze(['modern_classic', 'industrial_loft', 'scandinavian', 'japandi', 'mid_century']);
const TEXTURE_SLOTS = ['map', 'normalMap', 'roughnessMap', 'aoMap', 'metalnessMap'];

function validStyle(style) {
  const keys = style && typeof style === 'object' && !Array.isArray(style) ? Object.keys(style).sort() : [];
  const ref = style?.style_pack;
  return keys.join() === 'bindings,dressing,skipped,style_pack' &&
    ref && typeof ref === 'object' && Object.keys(ref).sort().join() === 'id,version' &&
    STYLE_IDS.includes(ref.id) && typeof ref.version === 'string' && /^[0-9]+\.[0-9]+\.[0-9]+$/.test(ref.version) &&
    ['bindings', 'dressing', 'skipped'].every(k => Array.isArray(style[k]) && style[k].length <= 256);
}

// Split the optional `style` record off a scene. Scenes without it render the legacy way.
export function splitStyle(input) {
  if (!input || typeof input !== 'object' || !('style' in input)) return {scene: input, style: null};
  const {style, ...scene} = input;
  if (!validStyle(style)) throw Error('Invalid style record');
  return {scene, style};
}

// A copy of a pack surface whose textures repeat every `tiling_m` metres over a u×v metre face.
export function tiledSurface(base, uSpanM, vSpanM) {
  const material = base.clone();
  const tiling = base.userData.tiling_m > 0 ? base.userData.tiling_m : 1;
  material.userData = {...base.userData, ownedTextures: []};
  for (const slot of TEXTURE_SLOTS) {
    if (!base[slot]) continue;
    const texture = base[slot].clone();
    texture.repeat.set(uSpanM / tiling, vSpanM / tiling);
    texture.needsUpdate = true;
    material[slot] = texture;
    material.userData.ownedTextures.push(texture);
  }
  return material;
}

export function disposeTiled(material) {
  for (const texture of material.userData.ownedTextures || []) texture.dispose();
  material.dispose();
}

// `loadPack({ref, tier, isCurrent})` resolves to a LoadedPack or 'superseded'.
// `apply(pack, tier)` dresses the room and may return an undo function.
export function createRoomStyle({style, tier, root = {dataset: {}}, loadPack, apply}) {
  let generation = 0, current = null, disposed = false, unavailable = false;
  const control = {legacy: !style, tier};
  const ref = style?.style_pack;
  if (ref) {
    root.dataset.stylePack = `${ref.id}@${ref.version}`;
    root.dataset.tier = tier;
  }
  const release = () => {
    if (!current) return;
    const {pack, undo} = current;
    current = null;
    if (typeof undo === 'function') undo();
    pack.dispose();
  };
  async function load() {
    if (control.legacy || disposed) return;
    const mine = ++generation;
    const isCurrent = () => !disposed && mine === generation;
    root.dataset.styleState = 'loading';
    let pack;
    try {
      pack = await loadPack({ref, tier: control.tier, isCurrent});
    } catch {
      if (isCurrent()) { unavailable = true; root.dataset.styleState = 'unavailable'; }
      return;
    }
    if (pack === 'superseded' || !pack) return;
    if (!isCurrent()) { pack.dispose(); return; }
    release();
    unavailable = false;
    current = {pack, undo: apply(pack, control.tier)};
    root.dataset.styleState = pack.failures.length ? 'partial' : 'ready';
  }
  control.start = load;
  control.setTier = next => {
    if (next !== 'high' && next !== 'low') return Promise.resolve();
    control.tier = next;
    if (!control.legacy) root.dataset.tier = next;
    return load();
  };
  control.captureTier = () => control.tier;
  control.pack = () => current?.pack || null;
  control.statusText = () => {
    if (control.legacy) return '';
    if (unavailable) return 'Style pack unavailable; showing standard finishes.';
    const pack = current?.pack;
    if (!pack) return `Loading style: ${ref.id} ${ref.version}…`;
    let text = `Style: ${pack.id} ${pack.version}`;
    if (pack.failures.length) text += ` · Fallback materials: ${pack.failures.join(', ')}`;
    if (pack.unreleased?.length) text += ` · Not yet released: ${pack.unreleased.join(', ')}`;
    return text;
  };
  control.dispose = () => { disposed = true; release(); };
  return control;
}
