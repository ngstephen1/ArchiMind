import { presentationFurniture } from "./saved_pieces.js";
import {finishColors} from "./finish_chat.js";
// Return endpoints in room-local metres, with north along positive Y.
export function openingEndpoints(room, opening) {
  const start = opening.offset_m;
  const end = start + opening.width_m;
  switch (opening.wall) {
    case "north": return [[start, room.depth_m], [end, room.depth_m]];
    case "south": return [[start, 0], [end, 0]];
    case "east": return [[room.width_m, start], [room.width_m, end]];
    case "west": return [[0, start], [0, end]];
    default: throw new Error("Unknown opening wall");
  }
}

import { LEGACY_PLAN_COLORS } from "./plan_colors.js";

export function floorPlan(h, c, colors = LEGACY_PLAN_COLORS) {
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  const s = Math.min(510 / h.width, 350 / h.depth),
    ox = (c.width - h.width * s) / 2,
    oy = c.height - 20;
  ctx.fillStyle = colors.site;
  ctx.fillRect(ox, oy - s * h.depth, s * h.width, s * h.depth);
  if (Number.isFinite(h.hall) && finishColors[h.hall_finish]) {
    ctx.fillStyle = finishColors[h.hall_finish];
    ctx.fillRect(ox + h.hall * s, oy - h.depth * s, 1.6 * s, h.depth * s);
  }
  const walls = [], openings = [], labels = [];
  for (const p of h.rooms) {
    const r = p.design.room,
      x = ox + s * p.origin[0],
      y = oy - s * p.origin[1],
      w = s * r.width_m,
      d = s * r.depth_m;
    ctx.fillStyle = finishColors[p.finish_overrides?.floor] || colors.room;
    ctx.fillRect(x + 1, y - d + 1, w - 2, d - 2);
    walls.push([x + 0.5, y - d + 0.5, w - 1, d - 1, finishColors[p.finish_overrides?.wall] || colors.wall]);
    for (const f of presentationFurniture(p)) {
      ctx.fillStyle = finishColors[p.finish_overrides?.objects?.[f.id]] || colors.furniture;
      const rect = [x + s * f.x_m, y - s * (f.y_m + f.depth_m), s * f.width_m, s * f.depth_m];
      ctx.fillRect(...rect);
      const stroke = colors.furnitureStroke || (!p.design.furniture.includes(f) && colors.wall);
      if (stroke) {
        ctx.strokeStyle = stroke;
        ctx.strokeRect(...rect);
      }
    }
    for (const opening of [...r.windows, ...r.doors]) {
      const [[x1, y1], [x2, y2]] = openingEndpoints(r, opening);
      const color = opening.sill_height_m === undefined ? colors.door : colors.window;
      openings.push([x + s * x1, y - s * y1, x + s * x2, y - s * y2, color]);
    }
    labels.push([r, x, y - d, w]);
  }
  // Each face belongs just inside its own room. Draw openings after both faces.
  ctx.lineWidth = 1;
  for (const [x, y, w, d, paint] of walls) {
    ctx.strokeStyle = paint;
    ctx.strokeRect(x, y, w, d);
  }
  ctx.lineWidth = 3;
  for (const [x1, y1, x2, y2, color] of openings) {
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }
  ctx.lineWidth = 1;
  ctx.fillStyle = colors.label;
  for (const [r, x, top, w] of labels) {
    ctx.font = "14px sans-serif";
    ctx.fillText(r.name, x + 6, top + 18, w - 12);
    ctx.font = "12px sans-serif";
    ctx.fillText(r.width_m.toFixed(2) + " × " + r.depth_m.toFixed(2) + " m", x + 6, top + 34, w - 12);
  }
  ctx.font = "14px sans-serif";
  ctx.fillText(h.width + " m", ox, oy + 16);
  ctx.fillText(h.depth + " m", 2, oy - (h.depth * s) / 2);
}
