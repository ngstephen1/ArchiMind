import { Box3 } from "three";

// The placeholder and its collision reservation remain in the scene until the
// native model is ready. A late completion belongs to its original home.
export async function fitBedroomChair(source, fallback, seat, side, current, dispose) {
  let model;
  try {
    model = await source;
    if (!current()) {
      dispose(model);
      return "superseded";
    }
    const box = new Box3().setFromObject(model, true);
    // Allow Float32 rounding at a face that coincides with the reservation.
    const eps = 1e-6;
    if (seat.rotation_deg !== 0 || box.isEmpty() ||
        ![...box.min.toArray(), ...box.max.toArray()].every(Number.isFinite) ||
        box.min.x < -seat.width_m / 2 - eps || box.max.x > seat.width_m / 2 + eps ||
        box.min.z < -seat.depth_m / 2 - eps || box.max.z > seat.depth_m / 2 + eps ||
        Math.abs(box.min.y) > eps || box.max.y > seat.height_m + eps) {
      dispose(model);
      return "placeholder";
    }
    model.position.set(seat.x_m + seat.width_m / 2, 0, -seat.y_m - seat.depth_m / 2);
    model.rotation.y = side === 1 ? Math.PI : 0;
    const parent = fallback.parent;
    parent.add(model);
    parent.remove(fallback);
    return "verified";
  } catch {
    if (model) dispose(model);
    return current() ? "placeholder" : "superseded";
  }
}
