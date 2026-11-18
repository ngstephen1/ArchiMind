// In-memory style pack shaped like src/archimind/_viewer_assets/packs/*.json and
// packs/releases.json (Task 6 contract). Bytes are synthetic; hashes are real.
import {createHash} from 'node:crypto';
import * as THREE from 'three';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const blob = (label, size) => new Uint8Array(Buffer.from(label.padEnd(size, '.')));

export const ref = {id: 'scandinavian', version: '1.0.0'};

export function buildFixture() {
  const files = new Map(); // url path -> bytes
  const releases = [];
  const add = (asset_id, kind, entries) => {
    const rel = {asset_id, kind, license: 'CC0-1.0', source_url: 'https://polyhaven.com/a/' + asset_id.split(':')[1],
      upstream_checksum: null, files: []};
    for (const [role, tier, ext, size] of entries) {
      const bytes = blob(`${asset_id}/${role}/${tier}`, size);
      const h = sha(bytes);
      files.set(`packs/assets/${h}.${ext}`, bytes);
      rel.files.push({role, tier, sha256: h, ext, bytes: bytes.length, width_px: tier === 'high' ? 2048 : 1024, height_px: tier === 'high' ? 2048 : 1024});
    }
    releases.push(rel);
  };
  for (const id of ['polyhaven:oak_floor', 'polyhaven:white_plaster', 'polyhaven:painted_trim']) {
    add(id, 'material', [
      ['diffuse', 'low', 'webp', 64], ['diffuse', 'high', 'webp', 96],
      ['normal', 'low', 'webp', 64], ['roughness', 'both', 'webp', 48],
    ]);
  }
  add('polyhaven:overcast_room', 'environment', [['hdr', 'both', 'hdr', 80]]);
  add('polyhaven:oak_side_table', 'model', [['model', 'both', 'glb', 120]]);
  const manifest = {
    id: 'scandinavian', version: '1.0.0', name: 'Scandinavian', aliases: ['scandi'],
    surfaces: {
      floor: {asset_id: 'polyhaven:oak_floor', tiling_m: 1.5, fallback_color: '#c8a77e'},
      wall: {asset_id: 'polyhaven:white_plaster', tiling_m: 2, fallback_color: '#f2efe8'},
      trim: {asset_id: 'polyhaven:painted_trim', tiling_m: 1, fallback_color: '#ffffff'},
      ceiling: {asset_id: 'polyhaven:not_released_yet', tiling_m: 2, fallback_color: '#fbfaf7'},
    },
    furniture: {table: [{asset_id: 'polyhaven:oak_side_table', width_m: 0.5, depth_m: 0.5, height_m: 0.55}]},
    decor: {mouldings: false},
    lighting: {environment_asset_id: 'polyhaven:overcast_room', environment_intensity: 0.8, exposure: 1,
      sun: {direction: [0.4, 0.8, 0.3], intensity: 2, kelvin: 6200}, fill: {sky_color: '#eef2f7', ground_color: '#b9ab96', intensity: 0.6}},
    plan_theme: {}, quality: {},
  };
  files.set('packs/scandinavian.json', new Uint8Array(Buffer.from(JSON.stringify(manifest))));
  files.set('packs/releases.json', new Uint8Array(Buffer.from(JSON.stringify(releases))));
  return {files, manifest, releases};
}

// fetchBytes(url) -> Uint8Array; throws on 404. `mutate(path, bytes)` lets a test corrupt a file.
export function fakeFetch({files}, {mutate = (p, b) => b, missing = [], log = []} = {}) {
  return async url => {
    const path = url.replace(/^\//, '');
    log.push(path);
    if (missing.includes(path) || !files.has(path)) throw new Error('404 ' + path);
    return mutate(path, files.get(path));
  };
}

export const fakeDecodeTexture = async () => new THREE.Texture();
export const fakeParseEnvironment = async () => new THREE.DataTexture(new Float32Array(4), 1, 1);
export const fakeParseModel = async () => new THREE.Group();

export function pathFor(fixture, assetId, role, tier) {
  const rel = fixture.releases.find(r => r.asset_id === assetId);
  const file = rel.files.find(f => f.role === role && f.tier === tier);
  return `packs/assets/${file.sha256}.${file.ext}`;
}
