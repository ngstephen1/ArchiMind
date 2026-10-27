// ArchiMind (east, north, up) -> Three.js (right, up, south).
export const toThree = ([x, y, z]) => [x, z, -y];
export const toCanonical = ([x, y, z]) => [x, -z, y];
const exactKeys = (value, keys) => value && typeof value === 'object' &&
  !Array.isArray(value) && Object.keys(value).sort().join(',') === keys.sort().join(',');
const number = (v, min, max) => typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max;
const text = v => typeof v === 'string' && v.trim().length > 0 && v.length <= 256;
export function validatePayload(data) {
  if (!exactKeys(data, ['schema_version', 'asset_id', 'room', 'furniture']) ||
      data.schema_version !== 1 || data.asset_id !== 'sheen-chair' ||
      !exactKeys(data.room, ['id', 'name', 'width_m', 'depth_m', 'ceiling_height_m']) ||
      !exactKeys(data.furniture, ['id', 'name', 'category', 'x_m', 'y_m', 'width_m', 'depth_m', 'height_m', 'rotation_deg'])) {
    throw new Error('Unsupported viewer input.');
  }
  const r = data.room, f = data.furniture;
  if (![r.id, r.name, f.id, f.name].every(text) || f.category !== 'chair' || f.rotation_deg !== 0 ||
      ![r.width_m, r.depth_m, r.ceiling_height_m].every(v => number(v, .1, 20)) ||
      ![f.width_m, f.depth_m, f.height_m].every(v => number(v, .05, 10)) ||
      ![f.x_m, f.y_m].every(v => number(v, -20, 20))) throw new Error('Unsupported viewer input.');
  return data;
}
export function fitBounds(min, max, furniture) {
  const size = max.map((v, i) => v - min[i]);
  if (min.length !== 3 || max.length !== 3 || ![...min, ...max, ...size].every(Number.isFinite) || size.some(v => v <= 0)) {
    throw new Error('Invalid model bounds.');
  }
  const f = furniture;
  const scale = Math.min(f.width_m / size[0], f.height_m / size[1], f.depth_m / size[2]);
  if (!Number.isFinite(scale) || scale <= 0) throw new Error('Invalid model scale.');
  const translation = [
    f.x_m + f.width_m / 2 - scale * (min[0] + max[0]) / 2,
    -scale * min[1],
    -f.y_m - f.depth_m / 2 - scale * (min[2] + max[2]) / 2,
  ];
  return {scale, translation, size: size.map(v => v * scale),
    min: min.map((v, i) => v * scale + translation[i]),
    max: max.map((v, i) => v * scale + translation[i])};
}
