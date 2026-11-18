// Designer concepts use their own reviewed releases and floor-centred glTF frame.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

function check(ok) {
  if (!ok) throw new Error('Designer chair release unavailable');
}

async function boundedBytes(response, limit) {
  check(response.ok && response.body && Number(response.headers.get('content-length')) <= limit);
  const reader = response.body.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      length += value.byteLength;
      check(length <= limit);
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel();
    throw error;
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}

export async function loadDesignerChair(binding, baseUrl) {
  check(binding?.concept_id === 'oak-sage-writing-chair' && /^[0-9a-f]{64}$/.test(binding.sha256));
  const registryBytes = await boundedBytes(await fetch(new URL('designer_registry.json', baseUrl)), 256 * 1024);
  const registry = JSON.parse(new TextDecoder().decode(registryBytes));
  check(registry.schema_version === 1 && Array.isArray(registry.chairs));
  const matches = registry.chairs.filter(r => r.concept_id === binding.concept_id && r.version === binding.version);
  const r = matches[0];
  check(matches.length === 1 && r.sha256 === binding.sha256 && Number.isInteger(r.bytes) &&
    r.bytes > 0 && r.bytes <= 15 * 1024 * 1024 && r.width_m === 0.48 && r.depth_m === 0.52 && r.height_m === 0.83);
  const bytes = await boundedBytes(await fetch(new URL('designer-' + r.sha256 + '.glb', baseUrl)), r.bytes);
  check(bytes.length === r.bytes);
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  check(Array.from(digest, x => x.toString(16).padStart(2, '0')).join('') === r.sha256);
  // The approved original concept has material colours and no texture dependencies.
  const manager = new THREE.LoadingManager();
  manager.setURLModifier(() => { throw new Error('External chair resource'); });
  const model = (await new GLTFLoader(manager).parseAsync(bytes.buffer, '')).scene;
  try {
    const box = new THREE.Box3().setFromObject(model, true);
    const actual = [...box.min.toArray(), ...box.max.toArray()];
    const expected = [-r.width_m / 2, 0, -r.depth_m / 2, r.width_m / 2, r.height_m, r.depth_m / 2];
    check(actual.every((v, i) => Math.abs(v - expected[i]) <= 1e-6));
    return model;
  } catch (error) {
    model.traverse(o => {
      o.geometry?.dispose();
      for (const m of [].concat(o.material || [])) m.dispose();
    });
    throw error;
  }
}
