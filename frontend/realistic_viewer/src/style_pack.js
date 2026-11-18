// Style pack loading for every 3D view. A pack manifest (packs/<id>.json) names
// a material per surface role, an environment map and furniture models by
// asset ID; packs/releases.json lists each asset's content-addressed files.
// Every file is fetched from packs/assets/<sha256>.<ext> and checked against
// its release hash before use. A file that is missing, truncated or fails its
// hash never reaches the scene: that surface gets a plain material in its
// fallback colour, a model yields null (the caller keeps its procedural
// piece), and the role or asset ID is listed in `failures`.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {TIER_SETTINGS} from './render_quality.js';

const MAP_ROLES = Object.freeze({diffuse: 'map', normal: 'normalMap', roughness: 'roughnessMap', ao: 'aoMap', metalness: 'metalnessMap'});
const TIER_ORDER = Object.freeze({low: ['low', 'both', 'high'], high: ['high', 'both', 'low']});
const MIME = Object.freeze({webp: 'image/webp', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png'});

function unavailable() { return new Error('Style pack unavailable'); }

async function defaultFetch(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('HTTP ' + response.status);
  return new Uint8Array(await response.arrayBuffer());
}

async function defaultDecodeTexture(bytes, ext) {
  const bitmap = await createImageBitmap(new Blob([bytes], {type: MIME[ext] || 'application/octet-stream'}), {imageOrientation: 'flipY'});
  const texture = new THREE.Texture(bitmap);
  texture.flipY = false;
  texture.needsUpdate = true;
  return texture;
}

async function defaultParseEnvironment(bytes) {
  const data = new HDRLoader().parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
  const texture = new THREE.DataTexture(data.data, data.width, data.height, THREE.RGBAFormat, data.type);
  texture.colorSpace = THREE.LinearSRGBColorSpace;
  texture.minFilter = texture.magFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

async function defaultParseModel(bytes) {
  const manager = new THREE.LoadingManager();
  manager.setURLModifier(() => { throw new Error('External model resource'); });
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  return (await new GLTFLoader(manager).parseAsync(buffer, '')).scene;
}

async function sha256Hex(bytes) {
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  return Array.from(digest, x => x.toString(16).padStart(2, '0')).join('');
}

function pickFile(release, role, tier) {
  for (const t of TIER_ORDER[tier] || TIER_ORDER.low) {
    const file = release.files.find(f => f.role === role && f.tier === t);
    if (file) return file;
  }
  return null;
}

function fallbackMaterial(spec) {
  const material = new THREE.MeshStandardMaterial({color: spec?.fallback_color || '#cccccc', roughness: 0.85, metalness: 0});
  material.userData.fallback = true;
  material.userData.tiling_m = spec?.tiling_m ?? 1;
  return material;
}

// Approximate black-body colour (Tanner Helland), 1000–40000 K.
export function kelvinToColor(kelvin) {
  const t = Math.min(40000, Math.max(1000, kelvin)) / 100;
  const clamp = v => Math.min(255, Math.max(0, v)) / 255;
  const r = t <= 66 ? 255 : 329.698727446 * Math.pow(t - 60, -0.1332047592);
  const g = t <= 66 ? 99.4708025861 * Math.log(t) - 161.1195681661 : 288.1221695283 * Math.pow(t - 60, -0.0755148492);
  const b = t >= 66 ? 255 : t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307;
  return new THREE.Color().setRGB(clamp(r), clamp(g), clamp(b), THREE.SRGBColorSpace);
}

export async function loadStylePack({baseUrl, ref, tier, fetchBytes = defaultFetch, isCurrent = () => true,
  decodeTexture = defaultDecodeTexture, parseEnvironment = defaultParseEnvironment, parseModel = defaultParseModel}) {
  if (!ref || typeof ref.id !== 'string' || !/^[a-z_]+$/.test(ref.id) || typeof ref.version !== 'string') throw unavailable();
  const url = path => baseUrl + path;
  let manifest, releaseList;
  try {
    const decoder = new TextDecoder();
    [manifest, releaseList] = await Promise.all([
      fetchBytes(url(`packs/${ref.id}.json`)).then(b => JSON.parse(decoder.decode(b))),
      fetchBytes(url('packs/releases.json')).then(b => JSON.parse(decoder.decode(b))),
    ]);
  } catch {
    throw unavailable();
  }
  if (manifest?.id !== ref.id || manifest.version !== ref.version || !manifest.surfaces || !Array.isArray(releaseList)) throw unavailable();
  const releases = new Map(releaseList.map(r => [r.asset_id, r]));
  const owned = new Set(); // textures and materials this pack must dispose
  const failures = [], unreleased = [];
  const track = x => { owned.add(x); return x; };

  async function verifiedBytes(file) {
    if (!file || !/^[0-9a-f]{64}$/.test(file.sha256) || !/^[a-z0-9]+$/.test(file.ext)) throw new Error('Invalid release file');
    const bytes = await fetchBytes(url(`packs/assets/${file.sha256}.${file.ext}`));
    if (bytes.length !== file.bytes || await sha256Hex(bytes) !== file.sha256) throw new Error('Integrity check failed');
    return bytes;
  }

  async function loadSurface(role, spec) {
    const release = releases.get(spec.asset_id);
    if (!release || release.kind !== 'material') return {role, material: fallbackMaterial(spec), status: 'unreleased'};
    const textures = [];
    try {
      const material = new THREE.MeshStandardMaterial({color: '#ffffff', roughness: 1, metalness: 0});
      textures.push(material);
      for (const [fileRole, slot] of Object.entries(MAP_ROLES)) {
        const file = pickFile(release, fileRole, tier);
        if (!file) continue;
        const texture = await decodeTexture(await verifiedBytes(file), file.ext);
        textures.push(texture);
        texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
        texture.anisotropy = tier === 'high' ? 8 : 2;
        texture.colorSpace = fileRole === 'diffuse' ? THREE.SRGBColorSpace : THREE.NoColorSpace;
        material[slot] = texture;
      }
      if (!material.map) throw new Error('Material has no diffuse map');
      material.userData.tiling_m = spec.tiling_m;
      material.userData.asset_id = spec.asset_id;
      return {role, material, status: 'ok', textures};
    } catch {
      for (const t of textures) t.dispose();
      return {role, material: fallbackMaterial(spec), status: 'failed'};
    }
  }

  const loaded = await Promise.all(Object.entries(manifest.surfaces).map(([role, spec]) => loadSurface(role, spec)));
  const surfaces = new Map();
  for (const {role, material, status, textures} of loaded) {
    surfaces.set(role, material);
    track(material);
    for (const t of textures || []) track(t);
    if (status === 'failed') failures.push(role);
    if (status === 'unreleased') unreleased.push(role);
  }

  let environment = null;
  const envRelease = releases.get(manifest.lighting?.environment_asset_id);
  if (envRelease && envRelease.kind === 'environment') {
    try {
      environment = track(await parseEnvironment(await verifiedBytes(pickFile(envRelease, 'hdr', tier))));
    } catch {
      failures.push('environment');
    }
  } else if (manifest.lighting?.environment_asset_id) {
    unreleased.push('environment');
  }

  const templates = [];
  const dispose = () => {
    for (const x of owned) x.dispose();
    owned.clear();
    for (const root of templates.splice(0)) root.traverse(o => {
      o.geometry?.dispose();
      for (const m of [o.material].flat().filter(Boolean)) { for (const v of Object.values(m)) if (v?.isTexture) v.dispose(); m.dispose(); }
    });
  };
  if (!isCurrent()) { dispose(); return 'superseded'; }

  const models = new Map();
  async function model(assetId) {
    const release = releases.get(assetId);
    try {
      if (!release || release.kind !== 'model') throw new Error('Model not released');
      if (!models.has(assetId)) models.set(assetId, verifiedBytes(pickFile(release, 'model', tier)).then(parseModel).then(root => { templates.push(root); return root; }));
      return (await models.get(assetId)).clone(true);
    } catch {
      models.delete(assetId);
      if (!failures.includes(assetId)) failures.push(assetId);
      return null;
    }
  }

  return {
    id: manifest.id, version: manifest.version, manifest, environment, failures, unreleased,
    settings: TIER_SETTINGS[tier] || TIER_SETTINGS.low,
    surface: role => surfaces.get(role) || null,
    model,
    dispose,
  };
}

function defaultMakeEnvironment(renderer, texture) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  let target;
  if (texture) {
    texture.mapping = THREE.EquirectangularReflectionMapping;
    target = pmrem.fromEquirectangular(texture);
  } else {
    const room = new RoomEnvironment();
    target = pmrem.fromScene(room, 0.04);
    room.traverse(o => { o.geometry?.dispose(); o.material?.dispose(); });
  }
  pmrem.dispose();
  return {texture: target.texture, dispose: () => target.dispose()};
}

// Pack lighting: environment reflections, a shadow-casting sun and a sky/ground fill.
export function applyLighting(scene, renderer, pack, tier, {center = new THREE.Vector3(), span = 6, makeEnvironment = defaultMakeEnvironment} = {}) {
  const lighting = pack.manifest.lighting || {};
  const env = makeEnvironment(renderer, pack.environment);
  scene.environment = env.texture;
  scene.environmentIntensity = lighting.environment_intensity ?? 0.6;
  renderer.toneMappingExposure = lighting.exposure ?? 1;
  const fill = lighting.fill || {};
  const hemisphere = new THREE.HemisphereLight(fill.sky_color || '#eef2f7', fill.ground_color || '#b9ab96', fill.intensity ?? 0.5);
  const sunSpec = lighting.sun || {};
  const sun = new THREE.DirectionalLight(kelvinToColor(sunSpec.kelvin ?? 5600), sunSpec.intensity ?? 2);
  const dir = new THREE.Vector3(...(sunSpec.direction || [0.4, 0.8, 0.3])).normalize();
  sun.position.copy(center).addScaledVector(dir, span * 2);
  sun.target.position.copy(center);
  sun.castShadow = true;
  const size = (TIER_SETTINGS[tier] || TIER_SETTINGS.low).shadowMapSize;
  sun.shadow.mapSize.set(size, size);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.02;
  sun.shadow.radius = tier === 'high' ? 4 : 2;
  Object.assign(sun.shadow.camera, {left: -span, right: span, top: span, bottom: -span, near: 0.1, far: span * 5});
  sun.shadow.camera.updateProjectionMatrix();
  scene.add(hemisphere, sun, sun.target);
  return {
    sun, hemisphere,
    dispose() {
      scene.remove(hemisphere, sun, sun.target);
      sun.shadow.map?.dispose();
      if (scene.environment === env.texture) scene.environment = null;
      env.dispose();
    },
  };
}
