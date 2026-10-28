import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {fitBounds, validatePayload, toThree} from './geometry.js';

const ASSET_URL = new URL('./furniture/SheenChair.glb', import.meta.url);
export function disposeObject(object) {
  const geometries = new Set(), materials = new Set(), textures = new Set();
  object.traverse(o => {
    if (o.geometry) geometries.add(o.geometry);
    for (const material of (Array.isArray(o.material) ? o.material : [o.material])) {
      if (!material) continue;
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  geometries.forEach(g => g.dispose());
  textures.forEach(t => { t.dispose(); t.source?.data?.close?.(); });
  materials.forEach(m => m.dispose());
}
export function mountViewer(host, input) {
  const root = document.createElement('section');
  root.dataset.viewer = 'realistic';
  // Fixed, checked-in markup only. All input strings below use textContent.
  root.innerHTML = `<div class="stage"><div class="status" role="status">Loading bundled chair…</div></div>
    <div class="toolbar"><button type="button" class="reset">Reset camera</button>
    <label><input type="checkbox" class="outline" checked> Canonical footprint</label></div>
    <p class="identity"></p><p class="fit"></p><p class="metrics" aria-live="polite"></p>`;
  host.appendChild(root);
  const stage = root.querySelector('.stage'), status = root.querySelector('.status');
  let renderer, controls, scene, environmentTarget, observer, visibility, frame, disposed = false, visible = true;
  const controller = new AbortController();
  const start = performance.now();
  const fail = message => { status.textContent = message; status.dataset.state = 'error'; status.setAttribute('role', 'alert'); root.dataset.state = 'error'; };
  const cleanup = () => {
    disposed = true; controller.abort(); cancelAnimationFrame(frame);
    observer?.disconnect(); visibility?.disconnect(); controls?.dispose();
    environmentTarget?.dispose();
    if (scene) disposeObject(scene);
    renderer?.dispose(); renderer?.forceContextLoss(); root.remove();
  };
  try {
    const data = validatePayload(input), f = data.furniture, r = data.room;
    root.dataset.state = 'loading';
    root.querySelector('.identity').textContent = `${f.name} · ${f.id} · ${f.category} · X/Y (${f.x_m}, ${f.y_m}) m · W/D/H ${f.width_m} × ${f.depth_m} × ${f.height_m} m`;
    renderer = new THREE.WebGLRenderer({antialias: true, alpha: false});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = .85;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.domElement.setAttribute('aria-label', 'Textured Sheen Chair, canonical footprint and neutral floor');
    stage.prepend(renderer.domElement);
    scene = new THREE.Scene(); scene.background = new THREE.Color('#e9edf0');
    const environment = new RoomEnvironment();
    const pmrem = new THREE.PMREMGenerator(renderer);
    environmentTarget = pmrem.fromScene(environment, .04);
    scene.environment = environmentTarget.texture;
    scene.environmentIntensity = .75;
    disposeObject(environment); pmrem.dispose();
    scene.add(new THREE.HemisphereLight(0xf2f6ff, 0xa79a86, .9));
    const sun = new THREE.DirectionalLight(0xfff4e5, 2.7);
    sun.position.set(f.x_m + 2, 4, -f.y_m + 2); sun.target.position.set(...toThree([f.x_m, f.y_m, .4]));
    sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, {left: -4, right: 4, top: 4, bottom: -4, near: .1, far: 15});
    sun.shadow.bias = -.0002; sun.shadow.normalBias = .003; sun.shadow.radius = 3;
    scene.add(sun, sun.target);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(r.width_m, r.depth_m),
      new THREE.MeshStandardMaterial({color: '#d9d4c9', roughness: .9, metalness: 0}));
    floor.rotation.x = -Math.PI / 2; floor.position.set(r.width_m / 2, -.002, -r.depth_m / 2);
    floor.receiveShadow = true; scene.add(floor);
    const footprint = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([
      [f.x_m, f.y_m, .004], [f.x_m+f.width_m, f.y_m, .004],
      [f.x_m+f.width_m, f.y_m+f.depth_m, .004], [f.x_m, f.y_m+f.depth_m, .004],
    ].map(v => new THREE.Vector3(...toThree(v)))), new THREE.LineBasicMaterial({color: '#15867e'}));
    scene.add(footprint);
    root.querySelector('.outline').onchange = e => { footprint.visible = e.target.checked; };
    const target = new THREE.Vector3(f.x_m+f.width_m/2, f.height_m*.48, -f.y_m-f.depth_m/2);
    const camera = new THREE.PerspectiveCamera(38, 1, .02, 100);
    const distance = Math.max(f.width_m, f.depth_m, f.height_m) * 2.35;
    const reset = () => {
      const damping = controls.enableDamping;
      controls.enableDamping = false; controls.update();
      camera.position.copy(target).add(new THREE.Vector3(distance*.78, distance*.5, distance));
      controls.target.copy(target); controls.update();
      controls.enableDamping = damping;
    };
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = .08;
    controls.minDistance = .4; controls.maxDistance = 12; controls.maxPolarAngle = Math.PI*.49;
    controls.addEventListener('change', () => {
      root.dataset.camera = JSON.stringify({position: camera.position.toArray(), target: controls.target.toArray()});
    });
    root.querySelector('.reset').onclick = reset; reset();
    const resize = () => {
      const width = Math.max(1, stage.clientWidth), height = Math.max(1, stage.clientHeight);
      camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.setSize(width, height, false);
    };
    observer = new ResizeObserver(resize); observer.observe(stage); resize();
    visibility = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; }); visibility.observe(stage);
    const animate = () => { if (disposed) return; frame = requestAnimationFrame(animate); if (visible) { controls.update(); renderer.render(scene, camera); } };
    animate();
    (async () => {
      try {
        const response = await fetch(ASSET_URL, {signal: controller.signal});
        if (!response.ok) throw new Error('Asset unavailable');
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > 15*1024*1024 || new DataView(bytes).getUint32(0,true) !== 0x46546c67) throw new Error('Invalid asset');
        const gltf = await new GLTFLoader().parseAsync(bytes, '');
        const model = gltf.scene;
        if (disposed) {disposeObject(model); return;}
        // SheenChair is natively Y-up, front +Z, facing canonical south (-Y).
        model.rotation.y = 0; model.updateMatrixWorld(true);
        const original = new THREE.Box3().setFromObject(model);
        const fit = fitBounds(original.min.toArray(), original.max.toArray(), f);
        model.scale.multiplyScalar(fit.scale); model.position.add(new THREE.Vector3(...fit.translation));
        model.updateMatrixWorld(true);
        let meshCount = 0, triangles = 0;
        const textures = new Set(), materials = new Set();
        model.traverse(o => {
          if (!o.isMesh) return;
          meshCount++; triangles += (o.geometry.index?.count ?? o.geometry.attributes.position.count)/3;
          o.castShadow = true; o.receiveShadow = true;
          for (const m of (Array.isArray(o.material) ? o.material : [o.material])) {
            materials.add(m.name);
            for (const t of Object.values(m)) if(t?.isTexture) textures.add(t);
          }
        });
        if (meshCount === 0 || textures.size === 0) {disposeObject(model); throw new Error('No textured furniture');}
        scene.add(model); renderer.render(scene, camera);
        const bounds = new THREE.Box3().setFromObject(model);
        const metrics = {meshCount, triangles, textureCount: textures.size, materials: [...materials],
          loadMs: performance.now()-start, assetBytes: bytes.byteLength, scale: fit.scale,
          originalMin: original.min.toArray(), originalMax: original.max.toArray(),
          min: bounds.min.toArray(), max: bounds.max.toArray(), fittedSize: fit.size,
          shadows: renderer.shadowMap.enabled, threeRevision: THREE.REVISION};
        root.dataset.metrics = JSON.stringify(metrics);
        root.querySelector('.fit').textContent = `Uniform scale ${fit.scale.toFixed(3)} · fitted W/D/H ${fit.size[0].toFixed(3)} × ${fit.size[2].toFixed(3)} × ${fit.size[1].toFixed(3)} m. Teal line = declared footprint; unused space is intentional.`;
        root.querySelector('.metrics').textContent = `${meshCount} meshes · ${triangles.toLocaleString()} triangles · ${textures.size} textures · local load + first render ${(metrics.loadMs/1000).toFixed(2)} s`;
        root.dataset.state = 'ready'; status.textContent = 'Textured chair loaded'; status.dataset.state = 'ready';
      } catch (error) { if (!disposed) fail('Unable to load the bundled chair. Check local assets or use the existing Plotly views.'); }
    })();
  } catch (error) { fail('Viewer unavailable: unsupported input or WebGL 2 is not available. Existing Plotly views remain available.'); }
  return cleanup;
}
