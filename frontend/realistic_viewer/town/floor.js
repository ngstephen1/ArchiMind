// The Town interior floor is a thin slab; dressing and pack models stand on its top.
export const FLOOR_SLAB = Object.freeze({ centerY: 0.008, height: 0.014 });
const FLOOR_TOP = FLOOR_SLAB.centerY + FLOOR_SLAB.height / 2;

/** Where a room's dressing holder sits: the room origin, lifted to the floor top. */
export function dressingOrigin(part) {
  return [part.origin[0], FLOOR_TOP, -part.origin[1]];
}
