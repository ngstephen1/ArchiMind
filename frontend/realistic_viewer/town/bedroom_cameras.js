// Work in room-local metres (east, north, height). Outputs use the Three.js world frame.
export function openingFrame(room, opening) {
  const mid = opening.offset_m + opening.width_m / 2;
  switch (opening.wall) {
    case "west": return { x: 0, y: mid, nx: 1, ny: 0 };
    case "east": return { x: room.width_m, y: mid, nx: -1, ny: 0 };
    case "south": return { x: mid, y: 0, nx: 0, ny: 1 };
    case "north": return { x: mid, y: room.depth_m, nx: 0, ny: -1 };
    default: throw Error("Unknown opening wall");
  }
}

function bounds(f) {
  return [[f.x_m, f.y_m, 0], [f.x_m + f.width_m, f.y_m + f.depth_m, f.height_m]];
}

function center(f) {
  return [f.x_m + f.width_m / 2, f.y_m + f.depth_m / 2, f.height_m * 0.70];
}

// Clip the finite eye-to-subject line against the other items' reserved volumes.
function obstructs(eye, target, [min, max]) {
  let first = 0, last = 1;
  for (let i = 0; i < 3; i++) {
    const d = target[i] - eye[i];
    if (Math.abs(d) < 1e-8) {
      if (eye[i] < min[i] || eye[i] > max[i]) return false;
      continue;
    }
    const a = (min[i] - eye[i]) / d, b = (max[i] - eye[i]) / d;
    first = Math.max(first, Math.min(a,b));
    last = Math.min(last, Math.max(a,b));
    if (first > last) return false;
  }
  return last > 0.001 && first < 0.999;
}

export function bedroomCameras(part, aspect = 16 / 9) {
  const { room, furniture } = part.design;
  const { width_m: w, depth_m: d } = room;
  const world = ([x, y, z]) => [part.origin[0] + x, z, -part.origin[1] - y];
  const fov = 58;
  const door = openingFrame(room, room.doors[0]);
  const entry = [door.x + door.nx * 0.24, door.y + door.ny * 0.24, 1.57];
  const overview = { id: "doorway", label: "Doorway", eye: world(entry),
    target: world([w/2, d/2, 0.91]), fov, reason: null };
  function detail(id, label, ids, preferredDistance) {
    const subjects = ids.map((key) => furniture.find((f) => f.id === key));
    const fallback = (message) => ({ ...overview, id, label, reason: message });
    if (subjects.some((item) => !item)) return fallback("Subject unavailable. Showing the doorway view.");
    const points = subjects.map(center);
    const target = [0, 1, 2].map((i) => points.reduce((n, point) => n + point[i], 0) / points.length);
    const [primary] = subjects;
    const halfAngle = Math.atan(aspect * Math.tan((fov / 2) * Math.PI / 180));
    const side = (a) => Math.hypot(a[0] - target[0], a[1] - target[1]);
    const minDistance = Math.max(...subjects.map((item) =>
      side(center(item)) + Math.hypot(item.width_m,item.depth_m)/2)) / Math.sin(halfAngle);
    let best = null, bestScore = Infinity;
    // Sweep candidate positions inside the same convex room so sightlines cannot cross its walls.
    for (let x = 0.30; x < w - 0.22; x += 0.23) for (let y = 0.30; y < d - 0.22; y += 0.23) {
      const eye = [x, y, 1.57], distance = side(eye);
      if (distance < minDistance || distance < 0.75) continue;
      if (furniture.some((f) => x >= f.x_m-0.17 && x <= f.x_m+f.width_m+0.17 &&
        y >= f.y_m-0.17 && y <= f.y_m+f.depth_m+0.17)) continue;
      if (subjects.some((s) => furniture.some((f) => !subjects.includes(f) && obstructs(eye, center(s), bounds(f))))) continue;
      const dx = (x-target[0])/distance, dy = (y-target[1])/distance;
      const chairSide = subjects[1] && Math.sign(center(subjects[1])[1] - center(primary)[1]);
      const frontalPenalty = chairSide ? Math.max(0, 0.45 - dy * chairSide) * 3.2 : 0;
      const score = Math.abs(distance-Math.max(preferredDistance, minDistance+0.25))
        + Math.abs(Math.abs(dx)-0.61)*0.95 + frontalPenalty + distance*0.001;
      if (score < bestScore) { best = eye; bestScore = score; }
    }
    return best
      ? { id, label, eye: world(best), target: world(target), fov, reason: null }
      : fallback("No clear view of the complete subject. Showing the doorway view.");
  }
  return [overview, detail("desk", "Desk and chair", ["belaya","desk-chair"], 2.25),
    detail("bedside", "Bedside", ["bedside-lamp"], 1.52)];
}
