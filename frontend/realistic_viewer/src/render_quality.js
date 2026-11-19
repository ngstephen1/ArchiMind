// Quality tiers shared by the Studio room viewer and the Town world.
// `high`: 2k textures, 2048 shadow maps, ambient occlusion pass, full decor.
// `low`: 1k textures, 1024 shadow maps, no post-processing, half the decor.
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {GTAOPass} from 'three/addons/postprocessing/GTAOPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';

export const TIER_SETTINGS = Object.freeze({
  high: Object.freeze({shadowMapSize: 2048, textureSize: '2k', decorDensity: 1}),
  low: Object.freeze({shadowMapSize: 1024, textureSize: '1k', decorDensity: 0.5}),
});

export function chooseTier({viewportWidth, deviceMemory, softwareRenderer, override} = {}) {
  if (override === 'high' || override === 'low') return override;
  if (softwareRenderer) return 'low';
  if (typeof viewportWidth === 'number' && viewportWidth < 700) return 'low';
  if (typeof deviceMemory === 'number' && deviceMemory < 4) return 'low';
  return 'high';
}

// Tier for this browser; `override` is the user's toggle choice, if any.
export function isSoftwareRenderer(renderer) {
  const gl = renderer.getContext();
  const debug = gl.getExtension('WEBGL_debug_renderer_info');
  return Boolean(debug && /swiftshader|llvmpipe|software rasterizer/i.test(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)));
}

export function browserTier(override, softwareRenderer = false) {
  const nav = typeof navigator === 'undefined' ? {} : navigator;
  const width = typeof innerWidth === 'number' ? innerWidth : undefined;
  return chooseTier({viewportWidth: width, deviceMemory: nav.deviceMemory, softwareRenderer, override});
}

export function configureRenderer(renderer, tier) {
  const dpr = typeof devicePixelRatio === 'number' ? devicePixelRatio : 1;
  renderer.setPixelRatio(Math.min(dpr || 1, tier === 'high' ? 2 : 1.25));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
}

export function createComposer(renderer, scene, camera, tier) {
  if (tier !== 'high') {
    return {tier: 'low', render: () => renderer.render(scene, camera), setSize() {}, dispose() {}};
  }
  const composer = new EffectComposer(renderer);
  const ao = new GTAOPass(scene, camera);
  ao.output = GTAOPass.OUTPUT.Default;
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(ao);
  composer.addPass(new OutputPass());
  return {
    tier: 'high',
    render: () => composer.render(),
    setSize: (w, h) => composer.setSize(w, h),
    dispose: () => { ao.dispose(); composer.dispose(); },
  };
}
