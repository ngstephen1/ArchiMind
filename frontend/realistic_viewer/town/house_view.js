import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

// The overview borrows Town's furnished scene. Its cut walls and highlight are
// visible only during this pass so walking, exports and photographs stay intact.
export function houseView(canvas, scene, interior, street, avatar, renderer) {
  const camera = new T.OrthographicCamera(-1, 1, 1, -1, 0.01, 200);
  const controls = new OrbitControls(camera, canvas);
  controls.enabled = false;
  controls.maxPolarAngle = Math.PI * 0.46;
  controls.minZoom = 0.55;
  controls.maxZoom = 7;
  const layer = new T.Group();
  scene.add(layer);
  layer.visible = false;
  const section = new T.MeshStandardMaterial({ color: 0x303a38 });
  const unit = new T.BoxGeometry();
  const highlight = new T.Box3Helper(new T.Box3(), 0x236ee8);
  scene.add(highlight);
  highlight.visible = false;
  const paper = new T.Color("#f2f1ec");
  const ray = new T.Raycaster();
  const tags = document.getElementById("houseLabels");
  let mode = "",
    home,
    hiddenDetails = [],
    ceiling,
    walls = [],
    labels = [],
    bounds,
    selected = false,
    cutCaps;
  const pos = new T.Vector3(),
    scale = new T.Vector3(),
    matrix = new T.Matrix4();
  function refreshDetails() {
    hiddenDetails = [];
    interior.traverse((node) => {
      if (
        node.userData.aboveCut ||
        ["art", "curtain", "pendant", "moulding"].includes(
          node.userData.dressingKind,
        )
      )
        hiddenDetails.push(node);
    });
  }
  function load(h, roof, parts) {
    home = h;
    ceiling = roof;
    walls = parts;
    refreshDetails();
    if (cutCaps) {
      layer.remove(cutCaps);
      cutCaps.dispose();
    }
    cutCaps = new T.InstancedMesh(unit, section, parts.length);
    parts.forEach(({ wall, ox, oy, bottom, height }, i) => {
      const top = Math.min(bottom + height, 1.15);
      pos.set(ox + wall.position.x, top, wall.position.z - oy);
      scale.set(
        wall.scale.x + 0.015,
        bottom >= top ? 0 : 0.035,
        wall.scale.z + 0.015,
      );
      cutCaps.setMatrixAt(i, matrix.compose(pos, wall.quaternion, scale));
    });
    layer.add(cutCaps);
    tags.replaceChildren();
    labels = h.rooms.map(({ origin, design }) => {
      const { room } = design;
      const tag = document.createElement("span");
      const area = document.createElement("small");
      area.textContent = (room.width_m * room.depth_m).toFixed(1) + " m²";
      tag.append(room.name, area);
      tags.append(tag);
      return {
        tag,
        center: new T.Vector3(
          origin[0] + room.width_m / 2,
          1.2,
          -origin[1] - room.depth_m / 2,
        ),
      };
    });
    const bedroom = h.rooms.find((r) => r.design.room.id === "bedroom");
    const chair = bedroom?.design.furniture.find((f) => f.id === "desk-chair");
    bounds = null;
    if (chair) {
      const x = bedroom.origin[0] + chair.x_m,
        z = -bedroom.origin[1] - chair.y_m;
      bounds = new T.Box3(
        new T.Vector3(x, 0, z - chair.depth_m),
        new T.Vector3(x + chair.width_m, chair.height_m, z),
      );
      highlight.box.copy(bounds);
    }
    selected = false;
  }
  function set(next) {
    mode = next;
    for (const button of document.querySelectorAll("[data-view]")) {
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.view === (next || "walk")),
      );
    }
    controls.enabled = Boolean(next);
    controls.enableRotate = next === "3d";
    tags.hidden = !next;
    canvas.parentElement.dataset.houseMode = next;
    if (!next || !home) return;
    const center = new T.Vector3(home.width / 2, 0, -home.depth / 2);
    controls.target.copy(center);
    camera.zoom = 1;
    camera.position
      .copy(center)
      .add(
        next === "plan"
          ? new T.Vector3(0, 40, 0.001)
          : new T.Vector3(20, 32, 25),
      );
    controls.update();
  }
  function cut(enable) {
    ceiling.visible = !enable;
    for (const node of hiddenDetails) {
      if (enable) {
        node.userData.cutVisibility = node.visible;
        node.visible = false;
      } else node.visible = node.userData.cutVisibility;
    }
    for (const { wall, height, bottom } of walls) {
      const h = enable ? Math.max(0, Math.min(height, 1.15 - bottom)) : height;
      wall.visible = h > 0;
      wall.scale.y = h;
      wall.position.y = bottom + h / 2;
    }
  }
  function render() {
    const aspect = canvas.clientWidth / Math.max(1, canvas.clientHeight);
    const w = home.width,
      d = home.depth;
    const half =
      mode === "plan"
        ? Math.max(d / 2, w / (2 * aspect)) * 1.2
        : Math.max(Math.hypot(w, d) * 0.48, Math.hypot(w, d) / (2 * aspect)) *
          1.15;
    Object.assign(camera, {
      left: -half * aspect,
      right: half * aspect,
      top: half,
      bottom: -half,
    });
    camera.updateProjectionMatrix();
    controls.update();
    const old = [
      street.visible,
      avatar.visible,
      interior.visible,
      scene.background,
      scene.fog,
    ];
    street.visible = avatar.visible = false;
    interior.visible = layer.visible = true;
    scene.background = paper;
    scene.fog = null;
    highlight.visible = selected && !!bounds;
    try {
      cut(true);
      renderer.render(scene, camera);
      for (const { tag, center } of labels) {
        pos.copy(center).project(camera);
        tag.style.left = 50 + 50 * pos.x + "%";
        tag.style.top = 50 - 50 * pos.y + "%";
      }
    } finally {
      cut(false);
      [
        street.visible,
        avatar.visible,
        interior.visible,
        scene.background,
        scene.fog,
      ] = old;
      layer.visible = highlight.visible = false;
    }
  }
  function pointRay(event, activeCamera) {
    const rect = canvas.getBoundingClientRect();
    ray.setFromCamera(
      new T.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        1 - ((event.clientY - rect.top) / rect.height) * 2,
      ),
      activeCamera,
    );
  }
  const floor = new T.Plane(new T.Vector3(0, 1, 0), 0);
  function roomAt(event) {
    if (!mode) return;
    pointRay(event, camera);
    if (!ray.ray.intersectPlane(floor, pos)) return;
    return home.rooms.find(
      ({ origin, design }) =>
        pos.x >= origin[0] &&
        pos.x <= origin[0] + design.room.width_m &&
        -pos.z >= origin[1] &&
        -pos.z <= origin[1] + design.room.depth_m,
    )?.design.room.id;
  }
  function pick(event, walkingCamera) {
    if (!bounds) return false;
    pointRay(event, mode ? camera : walkingCamera);
    if (!ray.ray.intersectBox(bounds, pos)) return false;
    const distance = ray.ray.origin.distanceTo(pos);
    if (mode) cut(true);
    try {
      const first = ray
        .intersectObjects(interior.children, true)
        .find((hit) => {
          for (let n = hit.object; n && n !== interior; n = n.parent)
            if (!n.visible) return false;
          return true;
        });
      return !first || first.distance >= distance - 0.025;
    } finally {
      if (mode) cut(false);
    }
  }
  return {
    load,
    refreshDetails,
    set,
    render,
    pick,
    roomAt,
    walkHighlight(inside) {
      highlight.visible = inside && selected && !!bounds;
    },
    select(value) {
      selected = value;
    },
    get mode() {
      return mode;
    },
  };
}
