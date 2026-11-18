import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {loadStylePack, kelvinToColor} from '../src/style_pack.js';
import {buildFixture, fakeFetch, fakeDecodeTexture, fakeParseEnvironment, fakeParseModel, pathFor, ref} from './fixtures/style_pack_fixture.js';

const load = (fixture, opts = {}, extra = {}) => loadStylePack({baseUrl: '/', ref, tier: 'low', fetchBytes: fakeFetch(fixture, opts),
  decodeTexture: fakeDecodeTexture, parseEnvironment: fakeParseEnvironment, parseModel: fakeParseModel, ...extra});

test('released surfaces get textured materials with their tiling', async () => {
  const fixture = buildFixture();
  const pack = await load(fixture);
  assert.deepEqual(pack.failures, []);
  const floor = pack.surface('floor');
  assert.ok(floor instanceof THREE.MeshStandardMaterial);
  assert.ok(floor.map && floor.normalMap && floor.roughnessMap);
  assert.equal(floor.map.colorSpace, THREE.SRGBColorSpace);
  assert.equal(floor.userData.tiling_m, 1.5);
  assert.ok(pack.environment);
});

test('a surface whose asset is not released yet uses its fallback colour and is listed', async () => {
  const pack = await load(buildFixture());
  assert.deepEqual(pack.unreleased, ['ceiling']);
  assert.equal(pack.surface('ceiling').map, null);
  assert.equal(pack.surface('ceiling').color.getHexString(), 'fbfaf7');
});

test('hash mismatch falls back per surface and is reported', async () => {
  const fixture = buildFixture();
  const bad = pathFor(fixture, 'polyhaven:oak_floor', 'diffuse', 'low');
  const pack = await load(fixture, {mutate: (p, b) => p === bad ? b.map(x => x ^ 1) : b});
  assert.deepEqual(pack.failures, ['floor']);
  assert.equal(pack.surface('floor').map, null);
  assert.equal(pack.surface('floor').color.getHexString(), fixture.manifest.surfaces.floor.fallback_color.slice(1));
  assert.ok(pack.surface('wall').map);
});

test('missing file and truncated file both fall back', async () => {
  const fixture = buildFixture();
  const wall = pathFor(fixture, 'polyhaven:white_plaster', 'normal', 'low');
  const trim = pathFor(fixture, 'polyhaven:painted_trim', 'roughness', 'both');
  const pack = await load(fixture, {missing: [wall], mutate: (p, b) => p === trim ? b.slice(0, 10) : b});
  assert.deepEqual(pack.failures, ['wall', 'trim']);
  assert.equal(pack.surface('wall').map, null);
  assert.equal(pack.surface('trim').map, null);
  assert.ok(pack.surface('floor').map);
});

test('environment failure is reported and leaves environment null', async () => {
  const fixture = buildFixture();
  const hdr = pathFor(fixture, 'polyhaven:overcast_room', 'hdr', 'both');
  const pack = await load(fixture, {missing: [hdr]});
  assert.deepEqual(pack.failures, ['environment']);
  assert.equal(pack.environment, null);
});

test('models load lazily, verified; a bad model yields null and is reported', async () => {
  const fixture = buildFixture();
  const log = [];
  const pack = await load(fixture, {log});
  const glb = pathFor(fixture, 'polyhaven:oak_side_table', 'model', 'both');
  assert.ok(!log.includes(glb));
  assert.ok(await pack.model('polyhaven:oak_side_table') instanceof THREE.Object3D);
  const broken = await load(fixture, {mutate: (p, b) => p === glb ? b.slice(1) : b});
  assert.equal(await broken.model('polyhaven:oak_side_table'), null);
  assert.equal(await broken.model('polyhaven:unknown'), null);
  assert.deepEqual(broken.failures, ['polyhaven:oak_side_table', 'polyhaven:unknown']);
});

test('a load that is no longer current returns superseded and disposes', async () => {
  const fixture = buildFixture();
  let current = true;
  const disposed = [];
  const decode = async () => { const t = new THREE.Texture(); t.addEventListener('dispose', () => disposed.push(t)); current = false; return t; };
  const result = await load(fixture, {}, {decodeTexture: decode, isCurrent: () => current});
  assert.equal(result, 'superseded');
  assert.ok(disposed.length >= 1);
});

test('low tier requests 1k files, high tier 2k where present', async () => {
  const fixture = buildFixture();
  const low = [], high = [];
  await load(fixture, {log: low});
  await load(fixture, {log: high}, {tier: 'high'});
  const lowDiffuse = pathFor(fixture, 'polyhaven:oak_floor', 'diffuse', 'low');
  const highDiffuse = pathFor(fixture, 'polyhaven:oak_floor', 'diffuse', 'high');
  assert.ok(low.includes(lowDiffuse) && !low.includes(highDiffuse));
  assert.ok(high.includes(highDiffuse) && !high.includes(lowDiffuse));
  // No 2k normal map exists, so high tier keeps the 1k one.
  assert.ok(high.includes(pathFor(fixture, 'polyhaven:oak_floor', 'normal', 'low')));
});

test('manifest whose version differs from the recorded ref is refused', async () => {
  const fixture = buildFixture();
  await assert.rejects(loadStylePack({baseUrl: '/', ref: {id: 'scandinavian', version: '2.0.0'}, tier: 'low', fetchBytes: fakeFetch(fixture),
    decodeTexture: fakeDecodeTexture, parseEnvironment: fakeParseEnvironment, parseModel: fakeParseModel}), /Style pack unavailable/);
});

test('dispose frees every texture and material', async () => {
  const pack = await load(buildFixture());
  let freed = 0;
  pack.surface('floor').map.addEventListener('dispose', () => freed++);
  pack.surface('floor').addEventListener('dispose', () => freed++);
  pack.dispose();
  assert.equal(freed, 2);
});

test('colour temperature maps warm to orange and cool to blue-white', () => {
  const warm = kelvinToColor(2700), cool = kelvinToColor(8000);
  assert.ok(warm.r > warm.b);
  assert.ok(cool.b >= cool.r - 0.05);
});

test('applyLighting sets exposure, environment, sun and fill from the manifest and disposes cleanly', async () => {
  const {applyLighting} = await import('../src/style_pack.js');
  const pack = await load(buildFixture());
  const scene = new THREE.Scene(), renderer = {};
  let envDisposed = 0;
  const makeEnvironment = (_renderer, texture) => ({texture: texture || new THREE.Texture(), dispose: () => envDisposed++});
  const lights = applyLighting(scene, renderer, pack, 'high', {center: new THREE.Vector3(2, 0, 2), span: 5, makeEnvironment});
  assert.equal(renderer.toneMappingExposure, 1);
  assert.equal(scene.environmentIntensity, 0.8);
  assert.ok(scene.environment);
  assert.equal(lights.sun.castShadow, true);
  assert.equal(lights.sun.shadow.mapSize.x, 2048);
  assert.ok(lights.sun.position.y > 0);
  assert.equal(lights.hemisphere.intensity, 0.6);
  lights.dispose();
  assert.equal(scene.children.length, 0);
  assert.equal(scene.environment, null);
  assert.equal(envDisposed, 1);
});
