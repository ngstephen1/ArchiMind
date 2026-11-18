// Work in room-local metres (east, north, height). Outputs use the Three.js world frame.
export function openingFrame(room, opening) {
  const mid = opening.offset_m + opening.width_m / 2;
  switch (opening.wall) {
    case "west":
      return { x: 0, y: mid, nx: 1, ny: 0 };
    case "east":
      return { x: room.width_m, y: mid, nx: -1, ny: 0 };
    case "south":
      return { x: mid, y: 0, nx: 0, ny: 1 };
    case "north":
      return { x: mid, y: room.depth_m, nx: 0, ny: -1 };
    default:
      throw Error("Unknown opening wall");
  }
}

function bounds(f) {
  return [
    [f.x_m, f.y_m, 0],
    [f.x_m + f.width_m, f.y_m + f.depth_m, f.height_m],
  ];
}

function center(f) {
  return [f.x_m + f.width_m / 2, f.y_m + f.depth_m / 2, f.height_m * 0.7];
}

// Clip the finite eye-to-subject line against the other items' reserved volumes.
function obstructs(eye, target, [min, max]) {
  let first = 0,
    last = 1;
  for (let i = 0; i < 3; i++) {
    const d = target[i] - eye[i];
    if (Math.abs(d) < 1e-8) {
      if (eye[i] < min[i] || eye[i] > max[i]) return false;
      continue;
    }
    const a = (min[i] - eye[i]) / d,
      b = (max[i] - eye[i]) / d;
    first = Math.max(first, Math.min(a, b));
    last = Math.min(last, Math.max(a, b));
    if (first > last) return false;
  }
  return last > 0.001 && first < 0.999;
}

// Confirm that every corner of the reserved subject fits in the perspective lens.
function fits(eye, target, subjects, aspect, fov) {
  const dot = (a, b) => a.reduce((sum, v, i) => sum + v * b[i], 0);
  const unit = (v) => v.map((n) => n / Math.hypot(...v));
  const forward = unit(target.map((v, i) => v - eye[i]));
  const right = unit([forward[1], -forward[0], 0]);
  const up = [
    -forward[2] * right[1],
    forward[2] * right[0],
    forward[0] * right[1] - forward[1] * right[0],
  ];
  const half = Math.tan((fov * Math.PI) / 360) * 0.94;
  return subjects.every((item) => {
    const [a, b] = bounds(item);
    for (const x of [a[0], b[0]])
      for (const y of [a[1], b[1]])
        for (const z of [0, b[2]]) {
          const relative = [x - eye[0], y - eye[1], z - eye[2]];
          const distance = dot(relative, forward);
          if (
            distance < 0.04 ||
            Math.abs(dot(relative, right)) > distance * half * aspect ||
            Math.abs(dot(relative, up)) > distance * half
          )
            return false;
        }
    return true;
  });
}

export function bedroomCameras(part, aspect = 16 / 9) {
  const { room, furniture } = part.design;
  const { width_m: w, depth_m: d } = room;
  const world = ([x, y, z]) => [part.origin[0] + x, z, -part.origin[1] - y];
  const fov = 58;
  const door = openingFrame(room, room.doors[0]);
  const entrance = room.doors[0];
  const entry = [door.x + door.nx * 0.74, door.y + door.ny * 0.74, 1.57];
  const bed = furniture.find((f) => f.id === "queen-bed");
  const focus = bed ? center(bed) : [w / 2, d / 2, 0.91];
  const along = door.nx ? 1 : 0;
  entry[along] +=
    Math.sign(entry[along] - focus[along]) *
    Math.max(0, entrance.width_m / 2 - 0.2);
  // Retain the clear opening threshold if a furnished interior corner is occupied.
  if (
    furniture.some(
      (f) =>
        entry[0] >= f.x_m - 0.16 &&
        entry[0] <= f.x_m + f.width_m + 0.16 &&
        entry[1] >= f.y_m - 0.16 &&
        entry[1] <= f.y_m + f.depth_m + 0.16,
    )
  ) {
    entry[0] = door.x + door.nx * 0.18;
    entry[1] = door.y + door.ny * 0.18;
  }
  // Compose the arrival around the bed. A centered lens otherwise lands on bare
  // plaster whenever the seeded layout puts the desk and bed on the entrance wall.
  const overviewTarget = [
    focus[0] * 0.9 + w * 0.05,
    focus[1] * 0.9 + d * 0.05,
    bed ? Math.max(0.58, focus[2]) : 0.91,
  ];
  const overview = {
    id: "doorway",
    label: "Doorway",
    eye: world(entry),
    target: world(overviewTarget),
    fov: 69,
    reason: null,
  };
  function detail(id, label, ids, preferredDistance) {
    const subjects = ids.map((key) => furniture.find((f) => f.id === key));
    const fallback = (message) => ({ ...overview, id, label, reason: message });
    if (subjects.some((item) => !item))
      return fallback("Subject unavailable. Showing the doorway view.");
    const points = subjects.map(center);
    const target = [0, 1, 2].map(
      (i) => points.reduce((n, point) => n + point[i], 0) / points.length,
    );
    const [primary] = subjects;
    const halfAngle = Math.atan(aspect * Math.tan(((fov / 2) * Math.PI) / 180));
    const side = (a) => Math.hypot(a[0] - target[0], a[1] - target[1]);
    const minDistance =
      Math.max(
        ...subjects.map(
          (item) =>
            side(center(item)) + Math.hypot(item.width_m, item.depth_m) / 2,
        ),
      ) / Math.sin(halfAngle);
    let best = null,
      bestScore = Infinity;
    // Sweep candidate positions inside the same convex room so sightlines cannot cross its walls.
    for (let x = 0.3; x < w - 0.22; x += 0.23)
      for (let y = 0.3; y < d - 0.22; y += 0.23) {
        const eye = [x, y, 1.57],
          distance = side(eye);
        if (distance < minDistance || distance < 0.75) continue;
        if (
          furniture.some(
            (f) =>
              x >= f.x_m - 0.17 &&
              x <= f.x_m + f.width_m + 0.17 &&
              y >= f.y_m - 0.17 &&
              y <= f.y_m + f.depth_m + 0.17,
          )
        )
          continue;
        if (
          subjects.some((s) =>
            furniture.some(
              (f) =>
                !subjects.includes(f) && obstructs(eye, center(s), bounds(f)),
            ),
          )
        )
          continue;
        if (!fits(eye, target, subjects, aspect, fov)) continue;
        const dx = (x - target[0]) / distance,
          dy = (y - target[1]) / distance;
        const chairSide =
          subjects[1] && Math.sign(center(subjects[1])[1] - center(primary)[1]);
        const frontalPenalty = chairSide
          ? Math.max(0, 0.45 - dy * chairSide) * 3.2
          : 0;
        const score =
          Math.abs(distance - Math.max(preferredDistance, minDistance + 0.25)) +
          Math.abs(Math.abs(dx) - 0.61) * 0.95 +
          frontalPenalty +
          distance * 0.001;
        if (score < bestScore) {
          best = eye;
          bestScore = score;
        }
      }
    return best
      ? {
          id,
          label,
          eye: world(best),
          target: world(target),
          fov,
          reason: null,
        }
      : fallback(
          "No clear view of the complete subject. Showing the doorway view.",
        );
  }
  if (room.id === "salon") {
    const suite=furniture.find(f=>f.id==="salon-suite"), dining=furniture.find(f=>f.id==="salon-dining");
    const subjects=[suite,dining].filter(Boolean);
    if(subjects.length===2){
      const pts=subjects.map(center);
      const target=[(pts[0][0]*.54+pts[1][0]*.46),(pts[0][1]*.54+pts[1][1]*.46),1.08];
      const candidates=[];
      for(const x of [.24,w*.25,w*.5,w*.75,w-.24])
        for(const y of [.24,d*.5,d-.24]){
          const eye=[x,y,1.44];
          if(furniture.some(f=>x>f.x_m-.18 && x<f.x_m+f.width_m+.18 && y>f.y_m-.18 && y<f.y_m+f.depth_m+.18))continue;
          if(subjects.some(subject => furniture.some(f => !subjects.includes(f) && obstructs(eye,center(subject),bounds(f))))) continue;
          for(const angle of [45,52,59,65]){
            if(!fits(eye,target,subjects,aspect,angle))continue;
            const dist=Math.hypot(x-target[0],y-target[1]);
            const ds=pts.map(p=>Math.hypot(x-p[0],y-p[1]));
            candidates.push({eye,angle,score:dist*Math.tan(angle*Math.PI/360) + angle*.006 - Math.min(1.5,Math.abs(ds[0]-ds[1]))*.12});
            break;
          }
        }
      candidates.sort((a,b)=>a.score-b.score);
      if(candidates.length){
        const chosen=candidates[0];
        return [{id:"overview", label:"Salon and dining", eye:world(chosen.eye),target:world(target),fov:chosen.angle,reason:null},
          detail("seating","Conversation group",[suite.id],2.8),detail("dining","Dining group",[dining.id],2.5)];
      }
    }
  }
  const ensemble = furniture.find(f => ["reading-suite", "breakfast-suite", "writing-suite"].includes(f.id));
  if (ensemble) {
    const companion = furniture.find(f => f.id !== ensemble.id);
    return [detail("overview", room.name, [ensemble.id], 3.4), detail("ensemble", ensemble.name, [ensemble.id], 2.15),
      ...(companion ? [detail(companion.id, companion.name, [companion.id], 1.9)] : [])];
  }
  if (room.id !== "bedroom") {
    const primary = furniture[0], secondary = furniture[1] || primary;
    return [overview, ...[primary, secondary].filter((f,i,a) => f && a.indexOf(f) === i).map(f =>
      detail(f.id, f.name, [f.id], 2.25))];
  }
  return [
    overview,
    detail("desk", "Desk and chair", ["belaya", "desk-chair"], 2.25),
    detail("bedside", "Bedside", ["bedside-lamp"], 1.52),
  ];
}
