// Room-local metres, Z up. One indexed surface feeds both the walk-through and Cycles.
export function turnedCoverlet(bed) {
  if (!bed || bed.id !== "queen-bed") return null;
  const vertices = [], faces = [], columns = 44, rows = 18;
  for (let j = 0; j <= rows; j++) {
    const v = j / rows;
    for (let i = 0; i <= columns; i++) {
      const u = i / columns;
      const shoulder = Math.abs(2 * u - 1);
      const hem = Math.max(0, (shoulder - 0.93) / 0.07);
      const crease = Math.sin(35 * u + 7 * v + 1.8 * Math.sin(6 * v));
      const lift = 0.016 * crease + 0.007 * Math.sin(59 * u - 4 * v);
      const turnover = Math.exp(-((v - 0.86) ** 2) / 0.006);
      vertices.push([
        bed.x_m + bed.width_m * (0.004 + 0.992 * u),
        bed.y_m + bed.depth_m * (0.18 + 0.48 * v) + 0.016 * Math.sin(8 * u + 2 * v),
        0.506 + lift * (0.45 + 0.55 * v) + 0.034 * turnover - 0.072 * hem * hem,
      ]);
      if (i && j) {
        const end = j * (columns + 1) + i;
        const start = end - columns - 2;
        faces.push([start, start + 1, end], [start, end, end - 1]);
      }
    }
  }
  return {name: "Stonewashed coverlet", vertices, faces};
}
