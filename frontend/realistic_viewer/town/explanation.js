import { PRODUCT_ASSETS } from "../src/product_assets.js";

// Distances are plan measurements from the selected revision, expressed in metres.
function gap(a, b) {
  const dx = Math.max(0, a.x_m - b.x_m - b.width_m, b.x_m - a.x_m - a.width_m);
  const dy = Math.max(0, a.y_m - b.y_m - b.depth_m, b.y_m - a.y_m - a.depth_m);
  return Math.hypot(dx, dy);
}

function deskWindow(room, desk) {
  if (!desk) return "This room has no recorded desk for a desk-to-window measurement.";
  if (!room.windows.length) return "This room has no recorded window for a desk-to-window measurement.";
  const measured = room.windows.map(w => {
    const middle = w.offset_m + w.width_m / 2;
    const x = w.wall === "west" ? 0 : w.wall === "east" ? room.width_m : middle;
    const y = w.wall === "south" ? 0 : w.wall === "north" ? room.depth_m : middle;
    return {opening: w, distance: Math.hypot(desk.x_m + desk.width_m / 2 - x, desk.y_m + desk.depth_m / 2 - y)};
  }).sort((a, b) => a.distance - b.distance);
  const {opening, distance} = measured[0];
  const name = desk.id === "belaya" ? "Belaya" : desk.name;
  return name + " is " + distance.toFixed(2) + " m from the nearest window center on the " + opening.wall +
    " wall, measured center to center in plan. Source: " + room.id + " " + desk.id +
    " footprint and window " + opening.id + ". This measures proximity. Placement intent and screen glare have not been established.";
}

export function asksChairChange(question) {
  return /\bchair\b/i.test(question) && /\b(chang(?:e|es|ed)|mov(?:e|ed|ing)|compar(?:e|ed)|previous|before)\b/i.test(question);
}

function chairChange(home, manifest, previous) {
  if (!manifest || manifest.home_id !== home.id || !previous ||
      manifest.project !== previous.project || manifest.revision !== previous.revision + 1)
    return "A chair comparison needs this saved revision and the preceding revision of the same project.";
  const pair = h => {
    const items = h?.rooms?.find(p => p.design.room.id === "bedroom")?.design.furniture || [];
    return ["desk-chair", "belaya"].map(id => items.find(f => f.id === id));
  };
  const [oldChair, oldDesk] = pair(previous.home);
  const [chair, desk] = pair(home);
  if (!oldChair || !oldDesk || !chair || !desk) return "Both revisions must contain bedroom desk-chair and belaya.";
  const position = f => "(" + f.x_m.toFixed(3) + ", " + f.y_m.toFixed(3) + ") m";
  return "Bedroom desk-chair footprint origin, revision " + previous.revision + ": " + position(oldChair) +
    "; revision " + manifest.revision + ": " + position(chair) +
    ". Displacement: " + Math.hypot(chair.x_m-oldChair.x_m, chair.y_m-oldChair.y_m).toFixed(3) +
    " m. Closest footprint gap to belaya: " + gap(oldChair,oldDesk).toFixed(3) +
    " m before and " + gap(chair,desk).toFixed(3) + " m after. Source: saved bedroom furniture coordinates.";
}

export function explanation(home, question, manifest = null, previous = null) {
  const bedroom = home.rooms.find(p => p.design.room.id === "bedroom");
  const {room, furniture} = bedroom.design;
  const get = id => furniture.find(f => f.id === id);
  const desk = get("belaya"), bed = get("queen-bed");
  const q = question.toLowerCase();
  if (asksChairChange(q)) return chairChange(home, manifest, previous);
  if (/\boak\b/.test(q)) {
    if (!manifest || manifest.home_id !== home.id)
      return "The verified bedroom manifest is unavailable for this design.";
    const matches = [];
    for (const item of manifest.furniture) {
      const source = item.source;
      const record = source?.kind === "catalog" && PRODUCT_ASSETS[source.id];
      if (record && record.sha256 === source.sha256 && record.variant_label?.toLowerCase() === "oak")
        matches.push(item.name + " (" + item.id + "), catalog " + source.id + ", variant_label = Oak");
    }
    const palette = home.palette === "oak" ? " The home also uses an authored oak palette." : "";
    return (matches.length ? "Selected bedroom pieces with catalog oak evidence: " + matches.join("; ") + "." :
      "No selected bedroom piece has a verified oak catalog variant.") + palette +
      " A variant label does not establish solid-oak construction.";
  }
  if (/\bdesk\b/.test(q) && !/bedroom|study|belaya|chair/.test(q)) {
    const rooms = home.rooms.filter(p => p.design.furniture.some(f => f.category === "desk"));
    if (rooms.length > 1) return "Which desk do you mean? Recorded desks occur in " + rooms.map(p => p.design.room.id).join(" and ") + ".";
  }
  if (/study/.test(q) && /desk|window/.test(q)) {
    const study = home.rooms.find(p => p.design.room.id === "study")?.design;
    if (!study) return "This revision has no recorded study.";
    const desks = study.furniture.filter(f => f.category === "desk");
    if (desks.length > 1) return "The study has multiple desk footprints. Specify an object ID before measuring.";
    return deskWindow(study.room, desks[0]);
  }
  if (/rug/.test(q) && bed) {
    const width = Math.min(room.width_m - .06, bed.x_m + bed.width_m + .58) - Math.max(.06, bed.x_m - .58);
    return "The rug spans " + width.toFixed(2) + " m across the bed. Its nominal side extension is 0.58 m, clipped to leave 0.06 m at the walls.";
  }
  if (/chair/.test(q)) {
    const chair = get("desk-chair");
    if (!chair || !desk) return "This revision has no recorded desk-and-chair pair.";
    if (bedroom.designer_chair) {
      const {name, dimensions_wdh_m} = bedroom.designer_chair;
      return name + " has a native width of " + dimensions_wdh_m[0].toFixed(2) +
        " m. Its reserved footprint is " + chair.width_m.toFixed(2) + " × " +
        chair.depth_m.toFixed(2) + " m. The gap from that reservation to the desk is " +
        gap(chair, desk).toFixed(2) + " m. Under-desk knee clearance has not been measured. Can you provide the clear width between supports and the floor-to-underside height? Source: bedroom desk-chair and belaya footprints.";
    }
    return "The writing chair is " + chair.width_m.toFixed(2) + " m wide. The closest edges of its footprint and the desk are " + gap(chair,desk).toFixed(2) + " m apart. Under-desk knee clearance has not been measured. Can you provide the clear width between supports and the floor-to-underside height? Source: bedroom desk-chair and belaya footprints.";
  }
  if (/lamp|nightstand|bedside/.test(q)) {
    const table = get("bedside-lamp");
    if (!table || !bed) return "This revision has no recorded bed-and-nightstand pair.";
    return "The lamp shares the nightstand’s " + table.width_m.toFixed(2) + " × " + table.depth_m.toFixed(2) + " m footprint. Its nearest edge is " + gap(bed,table).toFixed(2) + " m from the bed.";
  }
  if (/desk|glare|daylight|window/.test(q)) return deskWindow(room, desk);
  return "Ask about the writing desk, window, chair, bedside lamp or rug in this revision.";
}
