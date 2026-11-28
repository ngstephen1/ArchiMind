import {finishColors} from "./finish_chat.js";
import { editable, savedFurnitureParts, coffeeTables } from "./saved_pieces.js";
import { GroundedSkybox } from "three/addons/objects/GroundedSkybox.js";
import { houseView } from "./house_view.js";
import { turnedCoverlet } from "./studio_textiles.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { studioFinishes, salonDetails } from "./studio_furniture.js";
import * as T from "three";
import { bedroomSurfaces, finishBedroomConcept, furnishedWindow, scaledUV } from "./bedroom_surfaces.js";
import { bedroomCameras, openingFrame } from "./bedroom_cameras.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import {
  PRODUCT_ASSETS,
  boundedProductBytes,
  nativeProductInstance,
  validateProductBindings,
  productSceneBudget,
  productSceneAdmission,
} from "../src/product_assets.js";
import { fitBedroomChair } from "./designer_chair.js";
import { townSurfaceSource, LEGACY_WALL_COLORS, dressWhenCurrent, dressTownSurfaces, interiorLook } from "./style_source.js";
import { loadStylePack, kelvinToColor } from "../src/style_pack.js";
import { isSoftwareRenderer, browserTier, createComposer } from "../src/render_quality.js";
import { loadDesignerChair, loadBedroomConcept } from "../src/designer_chair.js";
import { queenBed } from "../src/bedroom_finishes.js";
import { wallQuads } from "../src/room_geometry.js";
import { buildTownDressing } from "./dressing_detail.js";
import { createPlanSweep } from "../src/plan_sweep.js";
import { dressFurniture, furnitureFallbackText } from "../src/pack_furniture.js";
import { FLOOR_SLAB, dressingOrigin } from "./floor.js";

export function createTown(canvas, status, action) {
  const renderer = new T.WebGLRenderer({
    canvas,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  const scene = new T.Scene(),
    sky = new T.Color("#cddcda");
  scene.background = sky;
  scene.fog = new T.Fog(sky, 28, 96);
  const env = new RoomEnvironment(),
    pm = new T.PMREMGenerator(renderer),
    map = pm.fromScene(env);
  scene.environment = map.texture;
  scene.environmentIntensity = 0.35;
  env.dispose();
  pm.dispose();
  const townLook = { environment: map.texture, intensity: 0.35, exposure: renderer.toneMappingExposure };
  scene.add(new T.HemisphereLight(0xfff3de, 0x9a9780, 1.45));
  const sun = new T.DirectionalLight(0xffe3b5, 2.7);
  sun.position.set(-24, 38, 24);
  sun.castShadow = true;
  Object.assign(sun.shadow.camera, {
    left: -36,
    right: 36,
    top: 32,
    bottom: -32,
    far: 110,
  });
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.normalBias = 0.025;
  scene.add(sun);
  const camera = new T.PerspectiveCamera(61, 1, 0.04, 130),
    street = new T.Group(),
    interior = new T.Group(),
    avatar = new T.Group();
  scene.add(street, interior, avatar);
  interior.visible = false;
  const overview = houseView(canvas, scene, interior, street, avatar, renderer, () => lightScene(true));
  const mats = new Map(),
    unit = new T.BoxGeometry(),
    obstacles = [],
    indoor = [];
  const mat = (color) => {
    if (!mats.has(color))
      mats.set(color, new T.MeshStandardMaterial({ color, roughness: 0.82 }));
    return mats.get(color);
  };
  function mesh(g, geo, color, x, y, z) {
    const m = new T.Mesh(geo, mat(color));
    m.position.set(x, y, z);
    m.castShadow = m.receiveShadow = true;
    g.add(m);
    return m;
  }
  function block(g, x, y, z, w, h, d, c) {
    const m = mesh(g, unit, c, x, y, z);
    m.scale.set(w, h, d);
    return m;
  }
  function solid(g, x, y, z, w, h, d, c, colliders) {
    const object = block(g, x, y, z, w, h, d, c);
    colliders.push([x - w / 2, z - d / 2, x + w / 2, z + d / 2]);
    return object;
  }
  function label(g, str, x, y, z, w, bg = "#294841") {
    const c = document.createElement("canvas");
    c.width = 512;
    c.height = 104;
    const ctx = c.getContext("2d");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 512, 104);
    ctx.strokeStyle = "#eadab5";
    ctx.strokeRect(7, 7, 498, 90);
    ctx.fillStyle = "#fff5dd";
    ctx.font = "bold 40px Georgia";
    ctx.textAlign = "center";
    ctx.fillText(str, 256, 67, 466);
    const tex = new T.CanvasTexture(c);
    tex.colorSpace = T.SRGBColorSpace;
    const m = new T.Mesh(
      new T.PlaneGeometry(w, (w * 104) / 512),
      new T.MeshBasicMaterial({ map: tex }),
    );
    m.position.set(x, y, z);
    g.add(m);
  }
  block(street, 0, -0.25, 0, 130, 0.4, 125, "#879778");
  block(street, 0, -0.045, 9, 99, 0.1, 5.2, "#696b66");
  block(street, -13, -0.038, 3, 4.8, 0.1, 82, "#696b66");
  block(street, 2, 0.018, 3.33, 20, 0.09, 6.6, "#c4b398");
  for (let i = -47; i < 48; i += 4)
    block(street, i, 0.018, 9, 1.5, 0.012, 0.09, "#d7c9a7");
  // Staggered paving courses and a shallow kerb define the pedestrian square.
  for (let row = 0; row < 9; row++) {
    const z = 0.1 + row * 0.7;
    block(street, 2, 0.065, z, 20, 0.004, 0.018, "#ae9c80");
    for (let x = -7.6 + (row % 2) * 0.62; x < 12; x += 1.24)
      block(street, x, 0.065, z + 0.35, 0.018, 0.004, 0.68, "#b6a487");
  }
  for (let x = -42; x < 42; x += 2.04)
    block(street, x, 0.046, 6.67, 2, 0.12, 0.21, "#bdb3a1");
  const backdrop = new T.SphereGeometry(1, 18, 10);
  for (let i = 0; i < 14; i++) {
    const angle = (i * Math.PI) / 7,
      m = mesh(
        street,
        backdrop,
        i % 2 ? "#859b8b" : "#a1ae95",
        63 * Math.cos(angle),
        -2.8,
        58 * Math.sin(angle),
      );
    m.scale.set(17 + (i % 3) * 4, 6 + (i % 4) * 1.8, 14);
  }
  const tileRoof = new Map();
  function house(x, z, w, d, h, c, name, hero = false) {
    solid(street, x, h / 2, z, w, h, d, c, obstacles);
    const roofColor = hero ? "#536866" : "#94624e";
    const roofKey = [w, h, d].join();
    if (!tileRoof.has(roofKey)) {
      const sh = new T.Shape();
      sh.moveTo(-w / 2 - 0.25, 0);
      sh.lineTo(0, w * 0.26);
      sh.lineTo(w / 2 + 0.25, 0);
      sh.closePath();
      tileRoof.set(
        roofKey,
        new T.ExtrudeGeometry(sh, { depth: d + 0.5, bevelEnabled: false }),
      );
    }
    mesh(street, tileRoof.get(roofKey), roofColor, x, h, z - d / 2 - 0.25);
    const front = z + d / 2;
    block(street, x, 1.1, front + 0.05, 1.25, 2.2, 0.12, "#3d554d");
    block(street, x + 0.38, 1.0, front + 0.14, 0.08, 0.08, 0.08, "#d7ae69");
    for (const side of [-1, 1]) {
      const wx = x + side * w * 0.32;
      block(street, wx, 1.65, front + 0.04, w * 0.19, 1.4, 0.12, "#ece1c8");
      block(street, wx, 1.65, front + 0.115, w * 0.165, 1.18, 0.04, "#648384");
      block(street, wx, 1.65, front + 0.15, 0.055, 1.18, 0.04, "#f1e6d1");
      block(street, wx, 1.62, front + 0.15, w * 0.165, 0.055, 0.04, "#f1e6d1");
      block(street, wx, 0.93, front + 0.14, w * 0.21, 0.12, 0.24, roofColor);
    }
    block(street, x, 2.9, front + 0.35, w * 0.8, 0.16, 0.78, roofColor);
    label(street, name, x, 2.62, front + 0.15, Math.min(w * 0.58, 4));
    block(
      street,
      x + w * 0.28,
      h + 0.7,
      z - d * 0.22,
      0.48,
      1.5,
      0.55,
      "#846653",
    );
    block(
      street,
      x + w * 0.28,
      h + 1.48,
      z - d * 0.22,
      0.61,
      0.14,
      0.67,
      "#795647",
    );
    block(street, x, 0.15, front + 0.02, w, 0.3, 0.1, "#b19b83");
    for (const corner of [-1, 1])
      block(
        street,
        x + corner * (w / 2 - 0.1),
        h / 2,
        front + 0.025,
        0.16,
        h,
        0.1,
        "#ecddc0",
      );
    for (let tile = 0; tile < 7; tile++)
      block(
        street,
        x,
        2.87,
        front + 0.63 - tile * 0.09,
        w * 0.8,
        0.025,
        0.017,
        "#bca78a",
      );
    if (h > 4) {
      const upper = mesh(
        street,
        new T.CircleGeometry(0.42, 16),
        "#5a7274",
        x,
        h + 0.43,
        front + 0.265,
      );
      upper.receiveShadow = true;
    }
  }
  // The showcase frontage follows the generated shell, including its front door.
  const hero = new T.Group();
  street.add(hero);
  const heroObstacles = [];
  const shops = [
    "BOOKSHOP",
    "CERAMICS",
    "BAKERY",
    "GROCERY",
    "ATELIER",
    "FLOWERS",
  ];
  shops.forEach((s, i) =>
    house(
      -35 + i * 6.5,
      -21,
      5.9,
      5,
      3.4 + (i % 2) * 0.85,
      ["#d8c099", "#c28f76", "#acb8a0"][i % 3],
      s,
    ),
  );
  for (const [i, x] of [-33, -24, 23, 32, 42].entries())
    house(
      x,
      -3,
      6.4,
      6,
      3.7,
      ["#d8be94", "#b3beb1"][i % 2],
      ["MILL HOUSE", "MAPLE HOUSE", "POST OFFICE", "TEA ROOM", "STATION"][i],
    );
  for (let i = 0; i < 6; i++)
    house(
      -35 + i * 11,
      24,
      7,
      6,
      3.4 + (i % 2),
      ["#b6c3b5", "#d8c4a9"][i % 2],
      "",
    );
  const trunk = new T.CylinderGeometry(0.14, 0.22, 2.4, 9),
    leaf = new T.IcosahedronGeometry(1, 1);
  function tree(x, z, i) {
    mesh(street, trunk, "#785e46", x, 1.2, z);
    obstacles.push([x - 0.24, z - 0.24, x + 0.24, z + 0.24]);
    for (let n = 0; n < 3; n++) {
      const a = i + n * 2.1;
      const m = mesh(
        street,
        leaf,
        ["#627c4e", "#82965f", "#687f50"][n],
        x + 0.65 * Math.cos(a),
        2.9 + n * 0.35,
        z + 0.6 * Math.sin(a),
      );
      m.scale.set(1.4, 1.5, 1.35);
      m.rotation.y = a;
    }
  }
  for (let i = 0; i < 12; i++) tree(-36 + i * 6.5, 13 + (i % 2), i);
  // The north row sits beyond both the 16 m maximum house and the rear shops.
  for (let i = 0; i < 8; i++) tree(-31 + i * 9, -28, i + 3);
  for (const x of [-7, 9]) {
    solid(street, x, 0.5, 4, 2, 0.14, 0.53, "#855f40", obstacles);
    for (const dx of [-0.76, 0.76])
      block(street, x + dx, 0.23, 4, 0.12, 0.46, 0.42, "#444f47");
    block(street, x, 0.86, 3.79, 2, 0.44, 0.1, "#855f40");
  }
  for (const x of [-8, 11, 20, -20]) {
    block(street, x, 1.8, 6, 0.09, 3.6, 0.09, "#3e5049");
    block(street, x, 3.65, 6, 0.38, 0.48, 0.38, "#f0d99f");
  }
  // Market stalls line one edge of the square, leaving the route to the house open.
  for (const [i, name] of ["CUT FLOWERS", "ORCHARD"].entries()) {
    const x = -8 + i * 4,
      z = -1;
    solid(street, x, 0.47, z, 2.6, 0.94, 1.25, "#986d4b", obstacles);
    for (const ix of [-1, 1])
      for (const iz of [-1, 1])
        block(
          street,
          x + ix * 1.18,
          1.25,
          z + iz * 0.5,
          0.07,
          2.5,
          0.07,
          "#6e5941",
        );
    for (let k = 0; k < 9; k++) {
      const awning = block(
        street,
        x + (k - 4) * 0.34,
        2.49,
        z,
        0.34,
        0.09,
        1.96,
        k % 2 ? "#f5e6c3" : i ? "#a75941" : "#577e68",
      );
      awning.rotation.x = 0.12;
    }
    label(street, name, x, 0.64, z + 0.64, 2.12);
    for (let k = 0; k < 12; k++) {
      const fruit = mesh(
        street,
        leaf,
        i ? "#bd723d" : k % 2 ? "#c78595" : "#bda14e",
        x + ((k % 6) - 2.5) * 0.34,
        1.08,
        z + (k < 6 ? -0.21 : 0.19),
      );
      fruit.scale.set(0.17, i ? 0.15 : 0.22, 0.17);
    }
  }
  // Consolidate static repetitions by material and geometry to reduce draw calls.
  function batch(group) {
    const buckets = new Map();
    for (const m of group.children.slice()) {
      if (!m.isMesh || m.userData.furniturePick || m.userData.surface === "wall" || m.userData.aboveCut) continue;
      const key = m.geometry.uuid + m.material.uuid;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(m);
    }
    for (const meshes of buckets.values()) {
      if (meshes.length < 3) continue;
      const first = meshes[0],
        inst = new T.InstancedMesh(
          first.geometry,
          first.material,
          meshes.length,
        );
      meshes.forEach((m, i) => {
        m.updateMatrix();
        inst.setMatrixAt(i, m.matrix);
        group.remove(m);
      });
      inst.castShadow = inst.receiveShadow = true;
      group.add(inst);
    }
  }
  batch(street);
  const townScenery = street.children.filter(child => child !== hero);
  const streetObstacles = obstacles.slice();
  const siteSetting = document.getElementById("siteSetting");
  let meadowShell, meadowActive = false, meadowLoad;
  function displaySite() {
    const wasMeadow = meadowActive;
    meadowActive = siteSetting.value === "meadow" && Boolean(meadowShell);
    for (const child of townScenery) child.visible = !meadowActive;
    obstacles.splice(0, obstacles.length, ...(meadowActive ? [] : streetObstacles));
    if (wasMeadow && !meadowActive && !inside && obstacles.some(([l,t,r,b]) =>
      pos.x >= l - 0.22 && pos.x <= r + 0.22 && pos.z >= t - 0.22 && pos.z <= b + 0.22)) {
      pos.set(doorX, 0, 1.6);
    }
    if (meadowShell) meadowShell.visible = meadowActive;
    canvas.dataset.landscape = meadowActive ? "meadow" : "town";
  }
  function chooseSite() {
    if (siteSetting.value === "meadow" && !meadowLoad) {
      meadowLoad = new T.TextureLoader().loadAsync("./assets/meadow-4k.jpg").then(texture => {
        texture.colorSpace = T.SRGBColorSpace;
        meadowShell = new GroundedSkybox(texture, 4, 90, 64);
        meadowShell.material.fog = false;
        meadowShell.material.toneMapped = false;
        meadowShell.position.set(7, 3.99, -7);
        meadowShell.renderOrder = -1;
        street.add(meadowShell);
        displaySite();
      }).catch(() => {
        meadowLoad = null;
        siteSetting.value = "town";
        displaySite();
      });
    }
    displaySite();
  }
  siteSetting.value = new URL(location.href).searchParams.get("setting") === "meadow" ? "meadow" : "town";
  siteSetting.onchange = () => {
    const url = new URL(location.href);
    if (siteSetting.value === "meadow") url.searchParams.set("setting", "meadow");
    else url.searchParams.delete("setting");
    history.replaceState(null, "", url);
    chooseSite();
  };
  chooseSite();
  const head = new T.SphereGeometry(0.185, 16, 12),
    limb = new T.CapsuleGeometry(0.09, 0.42, 4, 8);
  mesh(avatar, head, "#b38467", 0, 1.57, 0);
  mesh(
    avatar,
    new T.SphereGeometry(0.192, 14, 8, 0, Math.PI * 2, 0, 1.38),
    "#42352e",
    0,
    1.6,
    0,
  );
  mesh(avatar, new T.CapsuleGeometry(0.215, 0.32, 5, 12), "#365754", 0, 1.1, 0);
  const legs = [-0.115, 0.115].map((x) =>
    mesh(avatar, limb, "#535867", x, 0.44, 0),
  );
  const shoes = [-0.115, 0.115].map((x) =>
    block(avatar, x, 0.075, -0.035, 0.18, 0.15, 0.29, "#504638"),
  );
  const arms = [-0.27, 0.27].map((x) =>
    mesh(avatar, limb, "#ad8167", x, 1.02, 0),
  );
  let home,
    inside = false,
    pos = new T.Vector3(-8.8, 0, 9.8),
    yaw = -0.57,
    pitch = 0,
    look = false,
    lastX,
    lastY,
    phase = 0,
    generation = 0,
    deskReady = Promise.resolve(),
    collectionReady = Promise.resolve("procedural"),
    chairReady = Promise.resolve("procedural");
  // Style packs: only homes with `style_pack` are dressed; the exterior keeps its look.
  let tierOverride = null,
    styleGen = 0,
    packLook = null,
    stylePending = Promise.resolve(),
    composer = null,
    qualityButton = null;
  const softwareRenderer = isSoftwareRenderer(renderer);
  const tier = () => browserTier(tierOverride, softwareRenderer);
  function releasePackLook() {
    if (!packLook) return;
    const look = packLook;
    packLook = null;
    look.undo();
    look.lights.forEach((l) => l.removeFromParent());
    look.environment?.dispose();
    look.pack.dispose();
    composer?.dispose();
    composer = null;
  }
  function updateQuality() {
    if (!qualityButton) return;
    qualityButton.hidden = townSurfaceSource(home).kind !== "pack";
    qualityButton.textContent = "Quality: " + (tier() === "high" ? "High" : "Low");
  }
  function dressInterior(pack, packTier) {
    const lighting = pack.manifest.lighting || {};
    const undoSurfaces = dressTownSurfaces(interior, pack);
    for (const group of interior.children) {
      const overrides = home.rooms.find(p=>p.design.room.id===group.userData.roomId)?.finish_overrides;
      if (!overrides) continue;
      for (const o of group.children) {
        const role=o.userData.surface==="tile"?"floor":o.userData.surface;
        if (["wall","floor"].includes(role) && overrides[role]) o.material=mat(finishColors[overrides[role]]);
      }
    }
    const seams = [];
    interior.traverse((o) => {
      if (o.userData.legacySeam && o.visible) {
        o.visible = false;
        seams.push(o);
      }
    });
    let environment = null;
    if (pack.environment) {
      const pmrem = new T.PMREMGenerator(renderer);
      pack.environment.mapping = T.EquirectangularReflectionMapping;
      environment = pmrem.fromEquirectangular(pack.environment);
      pmrem.dispose();
    }
    const fill = lighting.fill || {};
    const lights = [new T.HemisphereLight(fill.sky_color || "#eef2f7", fill.ground_color || "#b9ab96", fill.intensity ?? 0.5)];
    const warm = kelvinToColor(lighting.sun?.kelvin ?? 5600);
    for (const part of home.rooms) {
      const r = part.design.room,
        light = new T.PointLight(warm, 6 * (lighting.sun?.intensity ?? 2), Math.max(r.width_m, r.depth_m) * 1.6, 2);
      light.position.set(part.origin[0] + r.width_m / 2, 2.45, -part.origin[1] - r.depth_m / 2);
      lights.push(light);
    }
    interior.add(...lights);
    const decor = [],
      ready = [],
      furnitureFailed = [];
    let live = true;
    for (const part of home.rooms) {
      if (!Array.isArray(part.style?.dressing)) continue;
      const holder = new T.Group();
      holder.userData.roomId = part.design.room.id;
      holder.position.set(...dressingOrigin(part));
      interior.add(holder);
      const dressing = buildTownDressing(holder, part.style.dressing, pack, packTier);
      decor.push({ holder, handle: dressing });
      ready.push(dressing.ready);
      if (Array.isArray(part.style.bindings)) {
        const furniture = dressFurniture({
          bindings: part.style.bindings.filter((b) => b.furniture_id !== "belaya"),
          furniture: part.design.furniture,
          pack,
          objects: roomFurniture.get(part.design.room.id) || new Map(),
          parent: holder,
        });
        decor.push({ holder, handle: { dispose: furniture.undo } });
        ready.push(
          furniture.ready.then(({ failed }) =>
            furnitureFailed.push(...part.design.furniture.filter((f) => failed.includes(f.id))),
          ),
        );
      }
    }
    // Name pack furniture that fell back to the procedural piece, while this look is live.
    const allReady = Promise.all(ready).then(() => {
      if (!live) return;
      overview.refreshDetails();
      const text = furnitureFallbackText(
        furnitureFailed.map((f) => f.id),
        furnitureFailed,
      );
      if (text) canvas.dataset.styleFurniture = text;
      else delete canvas.dataset.styleFurniture;
    });
    packLook = {
      pack,
      lights,
      environment,
      intensity: lighting.environment_intensity ?? 0.6,
      exposure: lighting.exposure ?? 1,
      ready: allReady,
      undo: () => {
        live = false;
        delete canvas.dataset.styleFurniture;
        decor.forEach(({ holder, handle }) => {
          handle.dispose();
          holder.removeFromParent();
        });
        undoSurfaces();
        seams.forEach((o) => (o.visible = true));
      },
    };
    composer = createComposer(renderer, scene, camera, packTier);
    composer.setSize(canvas.clientWidth, canvas.clientHeight);
    canvas.dataset.styleFailures = pack.failures.join(",");
  }
  function requestPack(epoch) {
    const source = townSurfaceSource(home);
    if (source.kind !== "pack") return;
    const mine = ++styleGen,
      packTier = tier(),
      current = () => generation === epoch && styleGen === mine;
    canvas.dataset.stylePack = source.ref.id + "@" + source.ref.version;
    canvas.dataset.styleState = "loading";
    canvas.dataset.tier = packTier;
    const surfaceRoles = new Set();
    interior.traverse((o) => { if (o.isMesh && o.userData.surface) surfaceRoles.add(o.userData.surface); });
    stylePending = dressWhenCurrent(
      loadStylePack({ baseUrl: new URL("./assets/", document.baseURI).href, ref: source.ref, tier: packTier, surfaceRoles, isCurrent: current }),
      current,
      (pack) => {
        // Restyles swap materials: return the sweep to Room first.
        sweep?.set(1);
        if (sweepInput) sweepInput.value = "100";
        releasePackLook();
        dressInterior(pack, packTier);
      },
    ).then((state) => {
      if (state !== "superseded") canvas.dataset.styleState = state;
    });
  }
  const roomJump = document.getElementById("roomJump");
  const photoControls = document.getElementById("photoControls");
  const photoView = document.getElementById("photoView");
  const photoReason = document.getElementById("photoReason");
  let preset = null;
  function selectPhoto() {
    const part = home?.rooms.find((p) => p.design.room.id === "bedroom");
    preset = (photoView.value && part)
      ? bedroomCameras(part, camera.aspect).find((item) => item.id === photoView.value)
      : null;
    if (photoView.value === "landscape" && part?.design.room.windows.length) {
      const room = part.design.room, win = room.windows[0];
      const along = win.offset_m + win.width_m / 2;
      const y = win.sill_height_m + win.height_m / 2;
      const walls = {
        west:  [0, along, 1, 0],
        east:  [room.width_m, along, -1, 0],
        north: [along, room.depth_m, 0, -1],
        south: [along, 0, 0, 1],
      };
      const [localX, localY, inwardX, inwardY] = walls[win.wall];
      const x = part.origin[0] + localX, z = -part.origin[1] - localY;
      preset = {id: "landscape", eye: [x + inwardX * 1.45, y, z - inwardY * 1.45], target: [x, y, z], reason: "View through the saved bedroom window."};
    }
    photoReason.textContent = preset?.reason || "";
    canvas.dataset.camera = preset?.id || "walking";
    look = false;
    keys.clear();
  }
  photoView.onchange = () => {
    selectPhoto();
    if (!preset) canvas.focus();
  };
  function walkView() {
    if (!preset) return;
    photoView.value = "";
    selectPhoto();
  }
  roomJump.onchange = () => {
    const part = home.rooms.find((r) => r.design.room.id === roomJump.value);
    if (!inside || !part) return;
    walkView();
    const r = part.design.room, frame=openingFrame(r,r.doors[0]);
    pos.set(part.origin[0]+frame.x+.7*frame.nx,0,-part.origin[1]-frame.y-.7*frame.ny);
    if (!part.design.furniture.length) {
      yaw=Math.atan2(-frame.nx,frame.ny);pitch=0;roomJump.value="";canvas.focus();return;
    }
    // Choose an eye point with a clear walk from the door and the widest view of the furniture.
    const doorX = pos.x,
      doorZ = pos.z;
    const objects = part.design.furniture.map((f) => [
      part.origin[0] + f.x_m + f.width_m / 2,
      -part.origin[1] - f.y_m - f.depth_m / 2,
    ]);
    const center = objects.reduce(
      (a, p) => [a[0] + p[0] / objects.length, a[1] + p[1] / objects.length],
      [0, 0],
    );
    let best = -Infinity;
    for (const u of [0.12, 0.5, 0.88])
      for (const v of [0.12, 0.5, 0.88]) {
        const x = part.origin[0] + r.width_m * u,
          z = -part.origin[1] - r.depth_m * v;
        const blocked = indoor.some(([l, t, rr, b]) => {
          const path = new T.Line3(
            new T.Vector3(doorX, 0, doorZ),
            new T.Vector3(x, 0, z),
          );
          const dir = path.delta(new T.Vector3()),
            len = dir.length();
          const ray = new T.Ray(path.start, dir.normalize());
          const hit = ray.intersectBox(
            new T.Box3(
              new T.Vector3(l - 0.24, -1, t - 0.24),
              new T.Vector3(rr + 0.24, 1, b + 0.24),
            ),
            new T.Vector3(),
          );
          return hit && hit.distanceTo(path.start) <= len;
        });
        if (blocked) continue;
        const angle = Math.atan2(center[0] - x, center[1] - z);
        const score =
          Math.min(
            ...objects.map(([px, pz]) =>
              Math.cos(Math.atan2(px - x, pz - z) - angle),
            ),
          ) +
          0.03 * Math.min(7, Math.hypot(x - center[0], z - center[1]));
        if (score > best) {
          best = score;
          pos.x = x;
          pos.z = z;
        }
      }
    yaw = Math.atan2(pos.x - center[0], pos.z - center[1]);
    pitch = -0.21;
    roomJump.value = "";
    canvas.focus();
  };
  const keys = new Set();
  let doorX = 0,
    roomName = "";
  const near = () =>
    inside
      ? Math.hypot(pos.x - doorX, pos.z) < 1.8
      : Math.hypot(pos.x - doorX, pos.z) < 2.5;
  function enter(value) {
    walkView();
    inside = value;
    hero.visible = !inside;
    street.visible = true;
    interior.visible = inside;
    avatar.visible = !inside;
    pos.set(doorX, 0, inside ? -0.8 : 1.3);
    yaw = inside ? 0 : Math.PI;
    pitch = 0;
    refresh();
  }
  function refresh() {
    const text = inside ? "Exit house" : "Enter house",
      place = preset ? "Bedroom" : inside ? roomName || "Entrance hall" : meadowActive ? "Woodland meadow" : "Market Square";
    photoControls.hidden = !inside;
    if (roomJump.hidden === inside) roomJump.hidden = !inside;
    if (action.textContent !== text) action.textContent = text;
    if (action.disabled === near()) action.disabled = !action.disabled;
    if (status.textContent !== place) status.textContent = place;
    const location = inside ? "interior" : "town";
    if (canvas.dataset.location !== location)
      canvas.dataset.location = location;
  }
  action.onclick = () => {
    if (near()) enter(!inside);
  };
  const record = Object.values(PRODUCT_ASSETS).find(
    (r) => r.filename === "BelayaDesk.glb",
  );
  let source;
  function deskSource() {
    return (source ??= (async () => {
      const bytes = await boundedProductBytes(
        await fetch("./assets/BelayaDesk.glb"),
        record,
      );
      return (await new GLTFLoader().parseAsync(bytes, "")).scene;
    })().catch((err) => {
      source = null;
      throw err;
    }));
  }
  function clear(g) {
    const geometries = new Set(),
      materials = new Set();
    g.traverse((o) => {
      if (o.isSpotLight) o.shadow.dispose();
      if (o.userData.nativeSource || !o.isMesh) return;
      if (o.isInstancedMesh) o.dispose();
      if (o.geometry !== unit) geometries.add(o.geometry);
      if (o.material && !Array.from(mats.values()).includes(o.material))
        materials.add(o.material);
    });
    geometries.forEach((v) => v.dispose());
    materials.forEach((v) => {
      if (!v.userData.townSharedMaps) v.map?.dispose();
      v.bumpMap?.dispose();
      v.dispose();
    });
    g.clear();
  }
  const timber = new T.TextureLoader().load("./assets/wood-floor.jpg");
  timber.colorSpace = T.SRGBColorSpace;
  timber.wrapS = timber.wrapT = T.RepeatWrapping;
  timber.repeat.set(3, 3);
  const oak = new T.MeshStandardMaterial({ map: timber, roughness: 0.64 });
  mats.set("wood-surface", oak);
  const brass = mat("#9a7546");
  brass.metalness = 0.72;
  brass.roughness = 0.32;
  // Tileable height maps for woven linen and fine plaster catch grazing light.
  for (const [woven, colors] of [
    [true, ["#d5c9b5", "#e9e1cd", "#eddfbd", "#bd9471"]],
    [false, ["#e5d6bc", "#bac6ad", "#d8ab91"]],
  ]) {
    const data = new Uint8Array(64 * 64 * 4);
    for (let y = 0; y < 64; y++)
      for (let x = 0; x < 64; x++) {
        const v = woven
          ? 128 +
            45 * Math.cos((x * Math.PI) / 2) +
            32 * Math.sin((y * Math.PI) / 2)
          : 125 + ((x * 73 + y * 91 + x * y * 3) % 55);
        data.set([v, v, v, 255], 4 * (64 * y + x));
      }
    const bump = new T.DataTexture(data, 64, 64);
    bump.wrapS = bump.wrapT = T.RepeatWrapping;
    bump.repeat.set(8, 12);
    bump.needsUpdate = true;
    for (const color of colors) {
      const m = mat(color);
      m.bumpMap = bump;
      m.bumpScale = woven ? 0.0018 : 0.0024;
    }
  }
  let sweep = null,
    sweepInput = null;
  const roomFurniture = new Map();
  const surfaces = bedroomSurfaces(renderer, mats);
  function load(h, keepPosition = false) {
    if (!keepPosition) walkView();
    generation++;
    const epoch = generation;
    // Dispose the sweep first so the pack look is released from real materials.
    sweep?.dispose();
    sweep = null;
    if (sweepInput) sweepInput.value = "100";
    releasePackLook();
    delete canvas.dataset.stylePack;
    delete canvas.dataset.styleState;
    delete canvas.dataset.styleFailures;
    const selectedLoads = [];
    canvas.dataset.collection = "procedural";
    function replaceCollection(binding, fallback, item, onVerified) {
      if (!binding) return;
      canvas.dataset.collection = "loading";
      selectedLoads.push(fitBedroomChair(
        Promise.all([loadBedroomConcept(binding, new URL("./assets/", document.baseURI)), surfaces.ready])
          .then(([model]) => finishBedroomConcept(model, surfaces)),
        fallback, item, -1, () => generation === epoch, clear,
      ).then(status => {
        if (status === "verified") { clear(fallback); onVerified?.(); }
        return status;
      }));
    }
    home = h;
    canvas.dataset.chair = "procedural";
    chairReady = Promise.resolve("procedural");
    deskReady = Promise.resolve();
    clear(interior);
    roomFurniture.clear();
    clear(hero);
    indoor.length = 0;
    heroObstacles.length = 0;
    roomJump.length = 1;
    for (const part of h.rooms)
      roomJump.add(new Option(part.design.room.name, part.design.room.id));
    doorX = home.photo_home?.entry_x ?? home.hall + 0.8;
    const W = h.width,
      D = h.depth;
    solid(hero, W / 2, 1.4, -D / 2, W, 2.8, D, "#cdbba0", heroObstacles);
    const ridge = new T.Shape();
    ridge.moveTo(-W / 2 - 0.3, 0);
    ridge.lineTo(0, 1.72);
    ridge.lineTo(W / 2 + 0.3, 0);
    ridge.closePath();
    mesh(
      hero,
      new T.ExtrudeGeometry(ridge, { depth: D + 0.6, bevelEnabled: false }),
      "#596a67",
      W / 2,
      3,
      -D - 0.3,
    );
    for (let x = 0.14; x < W; x += 0.24) {
      if (Math.abs(x - doorX) > 0.64)
        block(hero, x, 1.38, 0.025, 0.026, 2.72, 0.034, "#bba68c");
    }
    block(hero, doorX, 2.6, 0.85, 3.7, 0.15, 1.75, "#5e7065");
    for (const v of [-1, 1])
      block(hero, doorX + v * 1.73, 1.24, 1.54, 0.14, 2.48, 0.14, "#8a755a");
    block(hero, doorX, 0.065, 0.94, 4, 0.13, 2.07, "#ae9c85");
    block(hero, W / 2, 2.88, -D / 2, W + 0.4, 0.24, D + 0.45, "#53675c");
    block(hero, doorX, 1.08, 0.07, 1.12, 2.16, 0.14, "#45645e");
    label(hero, h.photo_home ? "PHOTO HOME" : "01  ·  STUDIO HOUSE", doorX, 2.48, 0.12, 3.2);
    // Exterior glazing uses the same offset, wall, sill and width as each room.
    for (const part of h.rooms)
      for (const win of part.design.room.windows) {
        const f=openingFrame(part.design.room,win), frame=new T.Group();
        frame.position.set(part.origin[0]+f.x,0,-part.origin[1]-f.y);
        frame.rotation.y=Math.atan2(-f.nx,f.ny);hero.add(frame);
        const mid=win.sill_height_m+win.height_m/2;
        block(frame,0,mid,.025,win.width_m+.12,win.height_m+.12,.10,"#f4e8cf");
        block(frame,0,mid,.09,win.width_m,win.height_m,.04,"#66858a");
        block(frame,0,mid,.12,.06,win.height_m,.05,"#e8dec9");
      }
    batch(hero);
    const roof = new T.Group();
    interior.add(roof);
    if (h.photo_home) {
      for (const {origin,design:{room:r}} of h.rooms) {
        block(roof,origin[0]+r.width_m/2,r.ceiling_height_m+.08,-origin[1]-r.depth_m/2,r.width_m,.16,r.depth_m,"#eee4cf").userData.surface="ceiling";
      }
    } else block(roof,W/2,2.88,-D/2,W,.16,D,"#eee4cf").userData.surface="ceiling";
    roof.userData.surface = "ceiling";
    const walls = [];
    delete canvas.dataset.desk;
    const bindings = h.rooms.flatMap((p) => p.asset_bindings || []);
    const admitted =
      productSceneAdmission(bindings).admitted &&
      productSceneBudget(bindings).passed;
    block(interior, W / 2, -0.09, -D / 2, W, 0.18, D, finishColors[h.hall_finish] || "#b39b7a");
    // Woven runner and flush ceiling pendants keep the circulation route clear.
    if (!h.photo_home) {
    block(interior, doorX, 0.014, -D / 2, 0.9, 0.018, D - 0.8, "#995b44");
    for (const v of [-0.38, 0.38])
      block(
        interior,
        doorX + v,
        0.025,
        -D / 2,
        0.024,
        0.003,
        D - 0.82,
        "#d6b584",
      );
    for (let z = 1; z < D - 0.5; z += 2.3) {
      block(interior, doorX, 2.75, -z, 0.16, 0.1, 0.16, "#765b3e");
      block(interior, doorX, 2.61, -z, 0.34, 0.17, 0.34, "#e1cc98");
    }

    }
    const wallColor = LEGACY_WALL_COLORS[h.palette];
    for (const part of h.rooms) {
      const [ox, oy] = part.origin,
        r = part.design.room,
        group = new T.Group();
      group.userData.roomId = r.id;
      group.position.set(ox, 0, -oy);
      interior.add(group);
      let validBindings = true;
      try {
        validateProductBindings({
          design: part.design,
          asset_bindings: part.asset_bindings,
          unavailable_assets: [],
        });
      } catch {
        validBindings = false;
      }
      for (const q of wallQuads(r)) {
        const a = q.points[0],
          b = q.points[2],
          x = (a[0] + b[0]) / 2,
          z = -(a[1] + b[1]) / 2;
        const wall = block(
          group,
          x,
          (q.bottom + q.top) / 2,
          z,
          Math.abs(a[0] - b[0]) || 0.1,
          q.top - q.bottom,
          Math.abs(a[1] - b[1]) || 0.1,
          wallColor,
        );
        wall.userData.surface = "wall";
        if(part.finish_overrides?.wall) wall.material=mat(finishColors[part.finish_overrides.wall]);
        walls.push({wall, ox, oy, bottom:q.bottom, height:q.top-q.bottom});
        if (q.bottom === 0) {
          block(
            group,
            x,
            0.065,
            z,
            wall.scale.x + 0.022,
            0.13,
            wall.scale.z + 0.022,
            "#eadfcb",
          ).userData.surface = "trim";
        }
        if (q.bottom < 1.7 && q.top > 0.25)
          indoor.push([
            ox + x - wall.scale.x / 2,
            z - oy - wall.scale.z / 2,
            ox + x + wall.scale.x / 2,
            z - oy + wall.scale.z / 2,
          ]);
      }
      const flooring = block(
        group,
        r.width_m / 2,
        FLOOR_SLAB.centerY,
        -r.depth_m / 2,
        r.width_m,
        FLOOR_SLAB.height,
        r.depth_m,
        r.id === "bathroom" ? "#b4b8b1" : "#ba9a70",
      );
      if (r.id === "bedroom") flooring.material = oak;
      if(part.finish_overrides?.floor) flooring.material=mat(finishColors[part.finish_overrides.floor]);
      flooring.userData.surface = r.id === "bathroom" ? "tile" : "floor";
      for (let row = 0; r.id !== "bedroom" && row < r.depth_m / 0.25; row++) {
        const z = row * 0.25;
        block(
          group,
          r.width_m / 2,
          0.016,
          -z,
          r.width_m,
          0.003,
          0.006,
          "#a78c6f",
        ).userData.legacySeam = true;
        for (let x = 0.4 + (row % 3) * 0.53; x < r.width_m; x += 1.75) {
          if (z + 0.25 < r.depth_m)
            block(group, x, 0.016, -z - 0.125, 0.006, 0.003, 0.25, "#a78c6f").userData.legacySeam = true;
        }
      }
      const windowStart = group.children.length;
      for (const win of r.windows)
        furnishedWindow(group, r, win, surfaces, block);
      // Wall-mounted print, clear of the window and of the circulation door.
      if (!h.photo_home) {
      const artX = r.width_m * 0.51;
      block(group, artX, 1.55, -r.depth_m + 0.055, 1.05, 0.73, 0.06, "#6e5541");
      block(group, artX, 1.55, -r.depth_m + 0.095, 0.96, 0.64, 0.02, "#e7d4ae");
      block(group, artX, 1.45, -r.depth_m + 0.111, 0.84, 0.21, 0.01, "#899677");
      block(
        group,
        artX + 0.16,
        1.66,
        -r.depth_m + 0.116,
        0.18,
        0.17,
        0.012,
        "#ba7e5c",
      );
      }
      for (const detail of group.children.slice(windowStart)) detail.userData.aboveCut = true;
      function studioPiece(p) {
        const [w,d,h]=p.wdh,[x,y,z]=p.xyz;
        const rounded=p.shape==="sphere" || p.shape==="cylinder";
        const geom=p.shape==="sphere"?new T.SphereGeometry(.5,20,12):p.shape==="cylinder"?new T.CylinderGeometry(.5,.5,1,24):new RoundedBoxGeometry(w,h,d,2,p.radius);
        const obj=mesh(group,geom,studioFinishes[p.finish],x,z,-y);
        if(rounded)obj.scale.set(w,h,d);
        return obj;
      }
      salonDetails(part).forEach(studioPiece);
      const tagged = new Map();
      roomFurniture.set(part.design.room.id, tagged);
      for (const f of part.design.furniture) {
        const before = group.children.length;
        const x = f.x_m + f.width_m / 2,
          z = -f.y_m - f.depth_m / 2,
          w = f.width_m,
          d = f.depth_m,
          t = f.height_m;
        indoor.push([ox + f.x_m, -oy - f.y_m - d, ox + f.x_m + w, -oy - f.y_m]);
        const usesStudioFurniture = h.rooms.some(p => p.design.room.id === "salon") ||
          (h.service_layout && f.id === "breakfast-suite");
        const pieces = savedFurnitureParts(part,f,r.id !== "bedroom" && usesStudioFurniture);
        const pick = item => ({...item,room:r.id});
        const allowed = editable(part,f);
        const coffee = f.id === "salon-suite" ? coffeeTables(part,f) : [];
        const finishes=part.finish_overrides?.objects || {};
        if (pieces.length) {
          if(f.id==="salon-suite" && part.coffee_tables && !part.suite_yaw_deg) {
            indoor.pop();
            const fx=ox+f.x_m, fy=oy+f.y_m;
            for(const [a,b,c,d] of [[w/2-.99,f.depth_m-.8,w/2+.99,f.depth_m],[.02,0,.8,.68],[w-.8,0,w-.02,.68]])
              indoor.push([fx+a,-fy-d,fx+c,-fy-b]);
          }
          for(const p of pieces) {
            const obj=studioPiece(p);
            const item=p.selectedPiece || (p.coffeeComponent ? coffee[0] : (allowed ? f : null));
            if(item) obj.userData.furniturePick=pick(item);
            const color=finishColors[finishes[item?.id] || finishes[f.id]];
            if(color) obj.material=mat(color);
          }
          for(const table of coffee) indoor.push([ox+table.x_m,-oy-table.y_m-table.depth_m,ox+table.x_m+table.width_m,-oy-table.y_m]);
          continue;
        }
        if (f.id === "queen-bed") {
          if (!h.presentation_detail || !part.style?.dressing?.some(item => item.kind === "rug")) {
          const left = Math.max(0.06, f.x_m - 0.58),
            right = Math.min(r.width_m - 0.06, f.x_m + w + 0.58);
          const front = Math.max(0.06, f.y_m - 0.55),
            back = Math.min(r.depth_m - 0.06, f.y_m + d * 0.72);
          const rug = block(
            group,
            (left + right) / 2,
            0.027,
            -(front + back) / 2,
            right - left,
            0.015,
            back - front,
            "#bd9471",
          );
          scaledUV(rug, [0.30 * 1024 / 1026, 0.30]);
          for (const edge of [front + 0.048, back - 0.048])
            block(
              group,
              (left + right) / 2,
              0.036,
              -edge,
              right - left - 0.08,
              0.003,
              0.032,
              "#795d4b",
            );
          }
          const fallback = queenBed(f);
          group.add(fallback);
          replaceCollection(part.designer_collection?.[f.id]?.binding, fallback, f, () => {
            if (!h.rooms.some(p => p.design.room.id === "salon")) return;
            const textile = turnedCoverlet(f);
            const geometry = new T.BufferGeometry();
            const coords = textile.vertices.flatMap(([a,b,c]) => [a,c,-b]);
            geometry.setAttribute("position", new T.Float32BufferAttribute(coords, 3));
            geometry.setIndex(textile.faces.flat());
            geometry.computeVertexNormals();
            mesh(group, geometry, "#d5c4a9", 0, 0, 0);
          });
        } else if (f.id === "desk-chair") {
          const desk = part.design.furniture.find(
            (item) => item.id === "belaya",
          );
          const side = desk && desk.y_m > f.y_m ? 1 : -1;
          const fallback = new T.Group();
          group.add(fallback);
          for (const a of [-1, 1])
            for (const b of [-1, 1])
              block(
                fallback,
                x + a * 0.19,
                0.21,
                z + b * 0.2,
                0.043,
                0.42,
                0.043,
                "#866446",
              );
          block(fallback, x, 0.44, z, w, 0.08, d, "#879582");
          block(fallback, x, 0.646, z + side * 0.23, w, 0.36, 0.048, "#866446");
          if (r.id === "bedroom" && part.designer_chair) {
            canvas.dataset.chair = "loading";
            const baseUrl = new URL("./assets/", document.baseURI);
            chairReady = fitBedroomChair(
              loadDesignerChair(part.designer_chair.binding, baseUrl),
              fallback, f, side, () => generation === epoch, clear,
            ).then((result) => {
              if (generation === epoch) canvas.dataset.chair = result;
              return result;
            });
          }
        } else if (f.id === "bedside-lamp") {
          const fallback = new T.Group();
          group.add(fallback);
          const cabinet = block(fallback, x, 0.28, z, w, 0.56, d, "#966d48");
          cabinet.material = surfaces.veneer;
          scaledUV(cabinet, [1.8, 1.8]);
          block(fallback, x, 0.36, z + d * 0.49, 0.13, 0.025, 0.018, "#9a7546");
          mesh(
            fallback,
            new T.CylinderGeometry(0.09, 0.1, 0.025, 20),
            "#9a7546",
            x,
            0.575,
            z,
          );
          block(fallback, x, 0.7, z, 0.025, 0.25, 0.025, "#9a7546");
          mesh(
            fallback,
            new T.CylinderGeometry(0.102, 0.146, 0.22, 32),
            "#eddfbd",
            x,
            0.95,
            z,
          );
          replaceCollection(part.designer_collection?.[f.id]?.binding, fallback, f);
          const bulb = new T.PointLight(0xffcf92, 3, 3);
          bulb.position.set(x, 0.81, z);
          group.add(bulb);
        } else if (f.id === "belaya") {
          const fallback = block(group, x, t / 2, z, w, t, d, "#aa947c");
          if (
            !admitted ||
            !validBindings ||
            !part.asset_bindings.some(
              (b) => b.furniture_id === f.id && b.asset_id === record.asset_id,
            )
          ) {
            canvas.dataset.desk = "placeholder";
            continue;
          }
          deskReady = deskSource()
            .then((model) => {
              if (epoch !== generation) return;
              const obj = nativeProductInstance(model, f, record);
              obj.traverse((o) => (o.userData.nativeSource = true));
              group.remove(fallback);
              group.add(obj);
              canvas.dataset.desk = "verified";
            })
            .catch(() => {
              if (epoch === generation) canvas.dataset.desk = "placeholder";
            });
        } else if (f.category === "table" || f.category === "desk") {
          block(group, x, t - 0.04, z, w, 0.08, d, "#956e4c");
          for (const i of [-1, 1])
            for (const j of [-1, 1])
              block(
                group,
                x + i * w * 0.43,
                t / 2,
                z + j * d * 0.4,
                0.065,
                t,
                0.065,
                "#554f46",
              );
        } else if (f.category === "sofa") {
          block(group, x, t * 0.38, z, w, t * 0.58, d, "#87978a");
          block(
            group,
            x,
            t * 0.72,
            z - d * 0.41,
            w,
            t * 0.56,
            d * 0.18,
            "#718675",
          );
          for (const side of [-1, 1])
            block(
              group,
              x + side * w * 0.45,
              t * 0.48,
              z,
              w * 0.1,
              t * 0.76,
              d,
              "#829181",
            );
        } else if (f.category === "bath") {
          block(group, x, t * 0.37, z, w, t * 0.73, d, "#ece6d9");
          block(group, x, t * 0.74, z, w * 0.79, 0.025, d * 0.64, "#a9c3bd");
          for (const v of [-1, 1]) {
            block(
              group,
              x + v * w * 0.45,
              t * 0.85,
              z,
              w * 0.1,
              t * 0.3,
              d,
              "#f4efe5",
            );
            block(
              group,
              x,
              t * 0.85,
              z + v * d * 0.44,
              w * 0.8,
              t * 0.3,
              d * 0.12,
              "#f4efe5",
            );
          }
        } else if (f.category === "counter" || f.category === "vanity") {
          block(group, x, t * 0.46, z, w, t * 0.92, d, "#758575");
          block(group, x, t * 0.95, z, w, t * 0.1, d, "#eee7d8");
          block(
            group,
            x + w * 0.14,
            t * 0.999,
            z,
            w * 0.31,
            0.002,
            d * 0.58,
            "#9bada7",
          );
          for (const v of [-1, 1])
            block(
              group,
              x + v * w * 0.22,
              t * 0.72,
              z + d * 0.492,
              w * 0.14,
              0.035,
              0.012,
              "#c7af80",
            );
        } else {
          block(group, x, t * 0.47, z, w, t * 0.94, d, "#a48c73");
          block(group, x, t * 0.97, z, w, t * 0.06, d, "#e1dbcc");
        }
        const members=group.children.slice(before);
        for(const obj of members){
          if(allowed) obj.userData.furniturePick=pick(f);
          const color=finishColors[finishes[f.id]];
          if(color) obj.traverse(child=>{if(child.isMesh)child.material=mat(color);});
        }
        tagged.set(f.id,members);
      }
      // Batch only stable meshes; native desk loading may replace its stand-in later.
      // Pack homes stay unbatched so pack models can replace individual pieces.
      if (
        !part.finish_overrides &&
        !part.designer_collection &&
        !part.designer_chair &&
        !part.design.furniture.some((f) => f.id === "belaya") &&
        townSurfaceSource(h).kind !== "pack"
      )
        batch(group);
    }
    for (const part of h.photo_home ? [] : h.rooms) {
      const room = part.design.room,
        door = room.doors[0];
      const side = door.wall === "east" ? 1 : -1,
        wall = side === 1 ? h.hall : h.hall + 1.6;
      const y = part.origin[1] + door.offset_m + door.width_m / 2;
      const plaque = new T.Group();
      plaque.position.set(wall + side * 0.065, 2.29, -y);
      plaque.rotation.y = (side * Math.PI) / 2;
      label(plaque, room.name.toUpperCase(), 0, 0, 0, 0.98);
      plaque.userData.aboveCut = true;
      interior.add(plaque);
    }
    for (const [x,z,width] of h.photo_home ? [] : [[doorX,-D,1.6],[doorX-.675,0,.25],[doorX+.675,0,.25]]) {
      const wall = solid(interior,x,1.4,z,width,2.8,.1,wallColor,indoor);
      walls.push({wall,ox:0,oy:0,bottom:0,height:2.8});
    }
    overview.load(h, roof, walls);
    if (inside && !keepPosition) enter(true);
    refresh();
    updateQuality();
    requestPack(epoch);
    collectionReady = Promise.all(selectedLoads).then(states => {
      const result = states.length ? (states.every(s => s === "verified") ? "verified" : "placeholder") : "procedural";
      if (epoch === generation) canvas.dataset.collection = result;
      return result;
    });
    return Promise.all([chairReady, collectionReady]).then(states =>
      states.includes("placeholder") ? "placeholder" : states.includes("verified") ? "verified" : "procedural"
    );
  }
  function move(dx, dz) {
    const coll = inside ? indoor : [...obstacles, ...heroObstacles];
    function ok(x, z) {
      return (
        (inside
          ? x > 0.23 &&
            x < home.width - 0.23 &&
            z < -0.18 &&
            z > -home.depth + 0.23
          : Math.abs(x) < 45 && Math.abs(z) < 30) &&
        coll.every(
          ([l, t, r, b]) =>
            x < l - 0.22 || x > r + 0.22 || z < t - 0.22 || z > b + 0.22,
        )
      );
    }
    if (ok(pos.x + dx, pos.z)) pos.x += dx;
    if (ok(pos.x, pos.z + dz)) pos.z += dz;
  }
  const active = () =>
    !overview.mode && !preset && !document.querySelector("dialog[open]") &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  window.addEventListener("keydown", (e) => {
    if (!active()) return;
    if (
      [
        "KeyW",
        "KeyA",
        "KeyS",
        "KeyD",
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "KeyE",
      ].includes(e.code)
    ) {
      e.preventDefault();
      keys.add(e.code);
      if (e.code === "KeyE" && !e.repeat && near()) enter(!inside);
    }
  });
  window.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("blur", () => keys.clear());
  let pressed;
  canvas.onpointerdown = (e) => {
    pressed = {x:e.clientX,y:e.clientY,id:e.pointerId};
    if (preset || overview.mode) return;
    look = true;
    canvas.setPointerCapture(e.pointerId);
    lastX = e.clientX;
    lastY = e.clientY;
  };
  canvas.onpointermove = (e) => {
    if (look) {
      yaw -= (e.clientX - lastX) * 0.005;
      pitch = T.MathUtils.clamp(
        pitch - (e.clientY - lastY) * 0.003,
        -0.65,
        0.65,
      );
      lastX = e.clientX;
      lastY = e.clientY;
    }
  };
  canvas.onpointerup = (e) => {
    look = false;
    if (pressed?.id === e.pointerId && Math.hypot(e.clientX-pressed.x,e.clientY-pressed.y)<5) {
      if ((overview.mode || inside) && overview.pick(e,camera)) {
        canvas.dispatchEvent(new CustomEvent("chair-picked",{detail:home.id}));
      } else if (overview.mode) {
        const item=overview.pieceAt(e);
        canvas.dispatchEvent(new CustomEvent("room-picked",{detail:overview.roomAt(e)}));
        if(item) canvas.dispatchEvent(new CustomEvent("furniture-picked",{detail:item}));
      }
    }
    pressed = null;
  };
  function enterOverviewRoom(room) {
    if (!room) return;
    overview.set("");
    enter(true);
    roomJump.value = room;
    roomJump.onchange();
  };
  canvas.ondblclick = event => enterOverviewRoom(overview.roomAt(event));
  canvas.addEventListener("enter-room", event => enterOverviewRoom(event.detail));
  canvas.onpointercancel = () => {look = false; pressed = null;};
  for (const el of document.querySelectorAll("[data-key]")) {
    el.onpointerdown = (e) => {
      el.setPointerCapture(e.pointerId);
      keys.add(el.dataset.key);
    };
    el.onlostpointercapture = () => keys.delete(el.dataset.key);
  }
  new ResizeObserver(() => {
    camera.aspect = canvas.clientWidth / canvas.clientHeight;
    camera.updateProjectionMatrix();
    if (preset) selectPhoto();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    composer?.setSize(canvas.clientWidth, canvas.clientHeight);
  }).observe(canvas);
  function lightScene(indoors) {
    const lit = interiorLook(indoors && packLook, {
      ...townLook,
      environment: (indoors && surfaces.environment) || map.texture,
    });
    scene.environment = lit.environment;
    scene.environmentIntensity = lit.intensity;
    renderer.toneMappingExposure = lit.exposure;
  }
  let before = performance.now();
  renderer.setAnimationLoop((now) => {
    const dt = Math.min(0.045, (now - before) / 1000);
    before = now;
    if (overview.mode) {
      if (!document.querySelector("dialog[open]")) overview.render();
      return;
    }
    if (active()) {
      const forward =
        Number(keys.has("KeyW") || keys.has("ArrowUp")) -
        Number(keys.has("KeyS") || keys.has("ArrowDown"));
      const side = Number(keys.has("KeyD")) - Number(keys.has("KeyA"));
      yaw +=
        dt *
        1.7 *
        (Number(keys.has("ArrowLeft")) - Number(keys.has("ArrowRight")));
      const speed =
        ((inside ? 2.5 : 3.6) * dt) / (Math.hypot(side, forward) || 1);
      move(
        (side * Math.cos(yaw) - forward * Math.sin(yaw)) * speed,
        (-forward * Math.cos(yaw) - side * Math.sin(yaw)) * speed,
      );
      phase += forward || side ? dt * 9 : 0;
      legs.forEach(
        (o, i) =>
          (o.rotation.x =
            forward || side ? Math.sin(phase + i * Math.PI) * 0.48 : 0),
      );
      arms.forEach((o, i) => (o.rotation.x = -legs[i].rotation.x * 0.65));
      shoes.forEach(
        (o, i) => (o.position.z = -0.035 - 0.34 * Math.sin(legs[i].rotation.x)),
      );
    }
    avatar.position.copy(pos);
    avatar.rotation.y = yaw;
    camera.position.copy(pos);
    camera.position.y = inside ? 1.57 : 2.9;
    if (inside) {
      camera.rotation.order = "YXZ";
      camera.rotation.set(pitch, yaw, 0, "YXZ");
    } else {
      let boom = 0.25;
      for (let step = 0.4; step <= 3.21; step += 0.2) {
        const x = pos.x + Math.sin(yaw) * step,
          z = pos.z + Math.cos(yaw) * step;
        if (
          [...obstacles, ...heroObstacles].some(
            ([l, t, r, b]) =>
              x > l - 0.12 && x < r + 0.12 && z > t - 0.12 && z < b + 0.12,
          )
        )
          break;
        boom = step;
      }
      camera.position.x += Math.sin(yaw) * boom;
      camera.position.z += Math.cos(yaw) * boom;
      camera.lookAt(
        pos.x - Math.sin(yaw) * 2,
        1.3 + pitch * 2,
        pos.z - Math.cos(yaw) * 2,
      );
    }
    if (inside) {
      const part = home.rooms.find(
        (p) =>
          pos.x > p.origin[0] &&
          pos.x < p.origin[0] + p.design.room.width_m &&
          -pos.z > p.origin[1] &&
          -pos.z < p.origin[1] + p.design.room.depth_m,
      );
      roomName = part?.design.room.name || "Entrance hall";
    }
    refresh();
    if (preset) {
      camera.position.fromArray(preset.eye);
      camera.lookAt(...preset.target);
    }
    const fov = preset?.fov || 61;
    if (camera.fov !== fov) {
      camera.fov = fov;
      camera.updateProjectionMatrix();
    }
    // Inside a pack home, its environment, exposure and (high tier) AO apply.
    lightScene(inside);
    overview.walkHighlight(inside);
    if (inside && packLook && composer) composer.render();
    else renderer.render(scene, camera);
    overview.walkHighlight(false);
  });
  // Photo Studio, the client board, and revision comparison borrow the same camera and scene.
  let captureQueue = Promise.resolve();
  async function captureBedroomViews(snapshot, roomId = "bedroom", fixedViews = null) {
    const original = home, originalPreset = photoView.value;
    const eye = pos.clone(), heading = yaw, tilt = pitch, wasInside = inside;
    if (home !== snapshot) load(snapshot);
    const epoch = generation;
    try {
      await deskReady;
      const [renderedChair, renderedCollection] = await Promise.all([chairReady, collectionReady]);
      await surfaces.ready;
      // A pack home is photographed dressed: wait for its pack, decor and furniture.
      await stylePending;
      await packLook?.ready;
      if (epoch !== generation) throw Error("Presentation source changed.");
      const part = snapshot.rooms.find((p) => p.design.room.id === roomId);
      const views = fixedViews ?? bedroomCameras(part);
      const visible = [hero, street, interior, avatar].map((o) => o.visible);
      const size = renderer.getSize(new T.Vector2());
      const ratio = renderer.getPixelRatio();
      const previousSweep = Number(sweepInput?.value ?? 100)/100;
      const oldEnv = scene.environment;
      const oldIntensity = scene.environmentIntensity,
        oldExposure = renderer.toneMappingExposure;
      try {
        sweep?.set(1);
        hero.visible = avatar.visible = false;
        street.visible = interior.visible = true;
        // A pack home is photographed with its own environment and exposure.
        lightScene(true);
        renderer.setPixelRatio(1);
        const aspect = views[0]?.aspect || 16/9;
        const width = Math.round(Math.min(1280,720*aspect));
        renderer.setSize(width, Math.round(width/aspect), false);
        const images = views.map((view) => {
          const cam = new T.PerspectiveCamera(view.fov, aspect, 0.04, 130);
          cam.position.fromArray(view.eye);
          cam.lookAt(...view.target);
          renderer.render(scene, cam);
          return canvas.toDataURL("image/jpeg", 0.9);
        });
        return { images, views, chair: renderedChair, desk: canvas.dataset.desk, collection: renderedCollection };
      } finally {
        sweep?.set(previousSweep);
        renderer.setPixelRatio(ratio);
        renderer.setSize(size.x,size.y,false);
        [hero, street, interior, avatar].forEach((o,i) => {o.visible = visible[i];});
        scene.environment = oldEnv;
        scene.environmentIntensity = oldIntensity;
        renderer.toneMappingExposure = oldExposure;
      }
    } finally {
      if (epoch === generation && original !== snapshot) {
        load(original); enter(wasInside);
        pos.copy(eye); yaw = heading; pitch = tilt;
        photoView.value = originalPreset; selectPhoto();
      }
    }
  }
  return {
    load,
    overview,
    get homeId() { return home?.id; },
    walk() { overview.set(""); enter(true); },
    // Plan ↔ Room over the home's interior only; a pure view change.
    bindSweep(input) {
      sweepInput = input;
      input.value = "100";
      input.oninput = () => {
        sweep ||= createPlanSweep({ renderer, root: interior });
        sweep.set(Number(input.value) / 100);
      };
    },
    bindQuality(button) {
      qualityButton = button;
      button.onclick = () => {
        tierOverride = tier() === "high" ? "low" : "high";
        updateQuality();
        requestPack(generation);
      };
      updateQuality();
    },
    bookmark() {
      if (!inside || overview.mode) throw Error("Walk inside a room to bookmark its camera.");
      const eye = camera.position.clone();
      const room = home.rooms.find(p => eye.x >= p.origin[0] && eye.x <= p.origin[0]+p.design.room.width_m && -eye.z >= p.origin[1] && -eye.z <= p.origin[1]+p.design.room.depth_m);
      if (!room) throw Error("Enter a furnished room first.");
      return {room:room.design.room.id, eye:eye.toArray(), target:camera.getWorldDirection(new T.Vector3()).add(eye).toArray(), fov:camera.fov, aspect:camera.aspect};
    },
    bedroomViews(snapshot, roomId = "bedroom", fixedViews = null) {
      const next = captureQueue.then(() => captureBedroomViews(snapshot, roomId, fixedViews));
      captureQueue = next.catch(() => {});
      return next;
    },
    visit: () => {
      overview.set("");
      walkView();
      pos.set(doorX, 0, 1.6);
      yaw = 0;
      pitch = 0;
      inside = false;
      street.visible = hero.visible = avatar.visible = true;
      interior.visible = false;
      refresh();
    },
  };
}
