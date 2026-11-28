import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { studioFinishes, studioFurniture } from "./studio_furniture.js";

// Representative furniture envelopes in metres. Photo inference supplies identity and
// relative placement only. Nothing in this study binds to a purchasable product.
const sizes = {
  bed: [1.55, 2.05, 0.64],
  chair: [0.48, 0.51, 0.83],
  armchair: [0.85, 0.84, 0.88],
  sofa: [2.05, 0.85, 0.86],
  desk: [1.3, 0.65, 0.74],
  table: [1.4, 0.8, 0.75],
  cabinet: [1, 0.45, 1.3],
  bookcase: [0.9, 0.35, 1.65],
};

export function openLayout(el, draft, photos) {
  const dialog = el("layoutStudio"),
    host = el("layoutViewport"),
    choice = el("layoutPiece");
  const { width, depth } = draft;
  const scene = new T.Scene(),
    model = new T.Group(),
    pieces = [];
  scene.background = new T.Color("#edebe5");
  scene.add(model);
  model.name = "Photo furniture study";
  model.userData = {
    room_width_m: width,
    room_depth_m: depth,
    photo_sha256: draft.photo_sha256,
    uncertainty: draft.uncertainty,
    geometry:
      "Rectangular study; proxy furniture envelopes and inferred positions.",
  };
  const box = new T.BoxGeometry(),
    materials = new Map();
  function block(parent, name, color, x, y, z, w, h, d) {
    if (!materials.has(color))
      materials.set(
        color,
        new T.MeshStandardMaterial({ color, roughness: 0.82 }),
      );
    const mesh = new T.Mesh(box, materials.get(color));
    mesh.name = name;
    mesh.position.set(x, y, z);
    mesh.scale.set(w, h, d);
    mesh.castShadow = mesh.receiveShadow = true;
    parent.add(mesh);
  }
  block(
    model,
    "Floor",
    "#c5a178",
    width / 2,
    -0.07,
    -depth / 2,
    width,
    0.14,
    depth,
  );
  block(
    model,
    "Back cut edge",
    "#e2d9cb",
    width / 2,
    0.18,
    -depth,
    width,
    0.36,
    0.06,
  );
  block(
    model,
    "Left cut edge",
    "#e2d9cb",
    0,
    0.18,
    -depth / 2,
    0.06,
    0.36,
    depth,
  );
  function build(item) {
    const group = new T.Group(),
      [w, d, h] = sizes[item.kind];
    group.name = item.label;
    group.userData = {
      kind: item.kind,
      source_photo: item.photo,
      representative_size_m: [w, d, h],
    };
    const part = (name, color, x, y, z, bw, bh, bd) =>
      block(group, name, color, x, y, z, bw, bh, bd);
    if (item.kind === "bed") {
      part("Frame", "#9d7555", 0, 0.17, 0, w, 0.3, d);
      part("Mattress", "#eae5d6", 0, 0.37, 0, w - 0.03, 0.17, d - 0.04);
      part("Duvet", "#83927c", 0, 0.48, 0.18, w, 0.1, d * 0.72);
      for (const s of [-1, 1])
        part(
          "Pillow",
          "#f1ede5",
          s * w * 0.23,
          0.51,
          -d * 0.32,
          w * 0.43,
          0.11,
          0.38,
        );
      part("Headboard", "#88725a", 0, 0.32, -d / 2 + 0.035, w, 0.64, 0.07);
    } else if (item.kind === "chair") {
      part("Seat", "#869a80", 0, 0.45, 0, w, 0.08, d);
      part("Back", "#869a80", 0, 0.65, -d * 0.43, w, h - 0.45, 0.066);
      for (const a of [-1, 1])
        for (const b of [-1, 1])
          part(
            "Oak leg",
            "#947552",
            a * w * 0.4,
            0.21,
            b * d * 0.38,
            0.038,
            0.42,
            0.038,
          );
    } else {
      const id =
        {
          armchair: "sofa",
          sofa: "sofa",
          cabinet: "media-console",
          bookcase: "bookcase",
        }[item.kind] || "work-table";
      for (const piece of studioFurniture({
        id,
        category: "table",
        x_m: -w / 2,
        y_m: -d / 2,
        width_m: w,
        depth_m: d,
        height_m: h,
      })) {
        const [x, y, z] = piece.xyz,
          [bw, bd, bh] = piece.wdh;
        part(piece.name, studioFinishes[piece.finish], x, z, -y, bw, bh, bd);
      }
    }
    group.rotation.y = (-item.quarter_turns * Math.PI) / 2;
    group.position.set(
      item.center_x_fraction * width,
      0,
      -item.center_depth_fraction * depth,
    );
    return group;
  }
  function limits(piece) {
    const [w, d] = piece.userData.representative_size_m;
    const turned = Math.abs(Math.sin(piece.rotation.y)) > 0.5;
    return { x: (turned ? d : w) / 2, z: (turned ? w : d) / 2 };
  }
  function place(piece, x, z) {
    const half = limits(piece);
    if (half.x * 2 > width || half.z * 2 > depth) return false;
    piece.position.set(
      T.MathUtils.clamp(x, half.x, width - half.x),
      0,
      -T.MathUtils.clamp(z, half.z, depth - half.z),
    );
    return true;
  }
  for (const item of draft.furniture) {
    const piece = build(item);
    if (!place(piece, piece.position.x, -piece.position.z)) continue;
    piece.userData.source_index = draft.furniture.indexOf(item);
    pieces.push(piece);
    model.add(piece);
  }

  const renderer = new T.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  const camera = new T.PerspectiveCamera(40, 1, 0.03, 150);
  const center = new T.Vector3(width / 2, 0, -depth / 2),
    reach = Math.max(width, depth);
  camera.position
    .copy(center)
    .add(new T.Vector3(0.78 * reach, 1.15 * reach, 1.24 * reach));
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(center);
  controls.maxPolarAngle = Math.PI * 0.47;
  controls.minDistance = 1;
  controls.maxDistance = 4 * reach;
  controls.update();
  scene.add(new T.HemisphereLight(0xfff7ea, 0xcebcaa, 2.1));
  const sun = new T.DirectionalLight(0xffeddb, 2.4);
  sun.position.set(-4, 10, 4);
  sun.castShadow = true;
  const shadow = sun.shadow.camera;
  Object.assign(shadow, {
    left: -reach,
    right: reach,
    top: reach,
    bottom: -reach,
  });
  sun.target.position.copy(center);
  scene.add(sun, sun.target);
  sun.shadow.normalBias = 0.015;
  const outline = new T.BoxHelper(undefined, 0x366957);
  scene.add(outline);
  outline.visible = false;
  const canvas = renderer.domElement,
    render = () => renderer.render(scene, camera);
  const notice = el("layoutNotice");
  let selected,
    dragId,
    disposed = false;
  function sync() {
    if (!selected) return;
    const item = draft.furniture[selected.userData.source_index];
    item.center_x_fraction = selected.position.x / width;
    item.center_depth_fraction = -selected.position.z / depth;
    item.quarter_turns =
      ((Math.round(-selected.rotation.y / (Math.PI / 2)) % 4) + 4) % 4;
    el("layoutX").value = selected.position.x.toFixed(2);
    el("layoutDepthPos").value = (-selected.position.z).toFixed(2);
    outline.setFromObject(selected);
    outline.visible = true;
    render();
  }
  function select(i) {
    selected = pieces[i];
    choice.value = String(i);
    if (selected) {
      el("layoutEvidence").textContent =
        "Visible in photo " +
        selected.userData.source_photo +
        " · " +
        selected.userData.kind;
      const photo = el("layoutSourcePhoto");
      const index = selected.userData.source_photo - 1;
      photo.src = photos[index];
      photo.alt = "Source photo " + (index + 1) + " for " + selected.name;
      photo.hidden = false;
      sync();
    }
  }
  el("layoutSourcePhoto").hidden = true;
  choice.replaceChildren(
    ...pieces.map((p, i) => new Option(p.name, String(i))),
  );
  el("layoutEvidence").textContent = "";
  for (const id of ["layoutPiece", "layoutX", "layoutDepthPos", "rotatePiece"])
    el(id).disabled = !pieces.length;
  el("layoutDimensions").textContent =
    width + " × " + depth + " m · " + pieces.length + " represented pieces";
  el("layoutUncertainty").textContent = draft.uncertainty;
  notice.textContent =
    pieces.length < draft.furniture.length
      ? "Items larger than the supplied floor were omitted."
      : "";
  choice.onchange = () => select(Number(choice.value));
  for (const id of ["layoutX", "layoutDepthPos"])
    el(id).onchange = () => {
      const x = el("layoutX").valueAsNumber,
        z = el("layoutDepthPos").valueAsNumber;
      if (Number.isFinite(x) && Number.isFinite(z)) place(selected, x, z);
      sync();
    };
  el("rotatePiece").onclick = () => {
    selected.rotation.y -= Math.PI / 2;
    if (!place(selected, selected.position.x, -selected.position.z)) {
      selected.rotation.y += Math.PI / 2;
      notice.textContent = "This orientation exceeds the floor size.";
    }
    sync();
  };
  const ray = new T.Raycaster(),
    plane = new T.Plane(new T.Vector3(0, 1, 0), 0),
    pos = new T.Vector3(),
    offset = new T.Vector3();
  function point(e) {
    const r = canvas.getBoundingClientRect();
    ray.setFromCamera(
      new T.Vector2(
        ((e.clientX - r.left) * 2) / r.width - 1,
        1 - ((e.clientY - r.top) * 2) / r.height,
      ),
      camera,
    );
  }
  canvas.addEventListener(
    "pointerdown",
    (e) => {
      point(e);
      let obj = ray.intersectObjects(pieces, true)[0]?.object;
      if (!obj || !ray.ray.intersectPlane(plane, pos)) return;
      while (obj.parent !== model) obj = obj.parent;
      select(pieces.indexOf(obj));
      offset.copy(obj.position).sub(pos);
      controls.enabled = false;
      dragId = e.pointerId;
      canvas.setPointerCapture(dragId);
      e.stopImmediatePropagation();
    },
    true,
  );
  canvas.onpointermove = (e) => {
    if (dragId !== e.pointerId) return;
    point(e);
    if (ray.ray.intersectPlane(plane, pos)) {
      pos.add(offset);
      place(selected, pos.x, -pos.z);
      sync();
    }
  };
  canvas.onpointerup =
    canvas.onpointercancel =
    canvas.onlostpointercapture =
      () => {
        dragId = undefined;
        controls.enabled = true;
      };
  controls.addEventListener("change", render);
  el("saveStudy").onclick = async () => {
    try {
      const buffer = await new GLTFExporter().parseAsync(model, {
        binary: true,
      });
      if (disposed) return;
      const url = URL.createObjectURL(
        new Blob([buffer], { type: "model/gltf-binary" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "archimind-photo-layout-study.glb";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch {
      notice.textContent = "The editable model could not be exported.";
    }
  };
  dialog.showModal();
  host.replaceChildren(canvas);
  const resize = new ResizeObserver(() => {
    const w = host.clientWidth,
      h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.zoom = Math.min(1, w / h);
    camera.updateProjectionMatrix();
    render();
  });
  resize.observe(host);
  if (pieces.length) select(0);
  dialog.addEventListener(
    "close",
    () => {
      disposed = true;
      el("layoutSourcePhoto").removeAttribute("src");
      resize.disconnect();
      controls.dispose();
      outline.dispose();
      box.dispose();
      for (const mat of materials.values()) mat.dispose();
      sun.shadow.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
      for (const id of [
        "saveStudy",
        "rotatePiece",
        "layoutX",
        "layoutDepthPos",
        "layoutPiece",
      ]) {
        el(id).onclick = el(id).onchange = null;
      }
    },
    { once: true },
  );
}
