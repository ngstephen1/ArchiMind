import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {chooseTier, configureRenderer, createComposer, TIER_SETTINGS} from '../src/render_quality.js';

test('tier: narrow or low-memory is low, override wins', () => {
  assert.equal(chooseTier({viewportWidth: 390}), 'low');
  assert.equal(chooseTier({viewportWidth: 1440, deviceMemory: 2}), 'low');
  assert.equal(chooseTier({viewportWidth: 1440, deviceMemory: 8}), 'high');
  assert.equal(chooseTier({viewportWidth: 1440}), 'high');
  assert.equal(chooseTier({viewportWidth: 390, override: 'high'}), 'high');
  assert.equal(chooseTier({viewportWidth: 1440, override: 'low'}), 'low');
  assert.equal(chooseTier({viewportWidth: 1440, override: 'ultra'}), 'high');
});

test('tier settings are frozen and halve decor on low', () => {
  assert.deepEqual(TIER_SETTINGS.high, {shadowMapSize: 2048, textureSize: '2k', decorDensity: 1});
  assert.deepEqual(TIER_SETTINGS.low, {shadowMapSize: 1024, textureSize: '1k', decorDensity: 0.5});
  assert.ok(Object.isFrozen(TIER_SETTINGS) && Object.isFrozen(TIER_SETTINGS.low));
});

function fakeRenderer() {
  return {ratio: null, shadowMap: {}, setPixelRatio(r) { this.ratio = r; }, rendered: 0, render() { this.rendered++; }};
}

test('configureRenderer sets colour management, AgX, soft shadows and caps pixel ratio', () => {
  globalThis.devicePixelRatio = 3;
  const high = fakeRenderer(), low = fakeRenderer();
  configureRenderer(high, 'high');
  configureRenderer(low, 'low');
  assert.equal(high.outputColorSpace, THREE.SRGBColorSpace);
  assert.equal(high.toneMapping, THREE.AgXToneMapping);
  assert.equal(high.shadowMap.enabled, true);
  assert.equal(high.shadowMap.type, THREE.PCFSoftShadowMap);
  assert.equal(high.ratio, 2);
  assert.equal(low.ratio, 1.25);
  delete globalThis.devicePixelRatio;
});

test('low tier composer renders directly with the renderer', () => {
  const renderer = fakeRenderer();
  const composer = createComposer(renderer, new THREE.Scene(), new THREE.PerspectiveCamera(), 'low');
  composer.render();
  composer.setSize(10, 10);
  composer.dispose();
  assert.equal(renderer.rendered, 1);
  assert.equal(composer.tier, 'low');
});
