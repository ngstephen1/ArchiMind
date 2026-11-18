// Distances are plan measurements from the selected revision, expressed in metres.
function gap(a, b) {
  const dx = Math.max(0, a.x_m - b.x_m - b.width_m, b.x_m - a.x_m - a.width_m);
  const dy = Math.max(0, a.y_m - b.y_m - b.depth_m, b.y_m - a.y_m - a.depth_m);
  return Math.hypot(dx, dy);
}

export function explanation(home, question) {
  const {room, furniture} = home.rooms.find(p => p.design.room.id === "bedroom").design;
  const get = id => furniture.find(f => f.id === id);
  const desk = get("belaya"), bed = get("queen-bed");
  const q = question.toLowerCase();
  if (/rug/.test(q) && bed) {
    const width = Math.min(room.width_m - .06, bed.x_m + bed.width_m + .58) - Math.max(.06, bed.x_m - .58);
    return "The rug spans " + width.toFixed(2) + " m across the bed. Its nominal side extension is 0.58 m, clipped to leave 0.06 m at the walls.";
  }
  if (/chair/.test(q)) {
    const chair = get("desk-chair");
    if (!chair || !desk) return "This revision has no recorded desk-and-chair pair.";
    return "The writing chair is " + chair.width_m.toFixed(2) + " m wide. The closest edges of its footprint and the desk are " + gap(chair,desk).toFixed(2) + " m apart. Under-desk knee clearance has not been measured.";
  }
  if (/lamp|nightstand|bedside/.test(q)) {
    const table = get("bedside-lamp");
    if (!table || !bed) return "This revision has no recorded bed-and-nightstand pair.";
    return "The lamp shares the nightstand’s " + table.width_m.toFixed(2) + " × " + table.depth_m.toFixed(2) + " m footprint. Its nearest edge is " + gap(bed,table).toFixed(2) + " m from the bed.";
  }
  if (/desk|glare|daylight|window/.test(q) && desk) {
    if (!room.windows.length) return "This room has no recorded window for a desk-to-window measurement.";
    const windows = room.windows.map(w => {
      const along=w.offset_m+w.width_m/2;
      const x=w.wall==="west"?0:w.wall==="east"?room.width_m:along;
      const y=w.wall==="south"?0:w.wall==="north"?room.depth_m:along;
      return {wall:w.wall,distance:Math.hypot(desk.x_m+desk.width_m/2-x,desk.y_m+desk.depth_m/2-y)};
    }).sort((a,b)=>a.distance-b.distance);
    return "Belaya provides a writing surface. Its center is " + windows[0].distance.toFixed(2) + " m from the nearest window center on the " + windows[0].wall + " wall in plan. Screen glare has not been evaluated.";
  }
  return "Ask about the writing desk, window, chair, bedside lamp or rug in this revision.";
}
