import { studioFurniture } from "./studio_furniture.js";

const LOOSE = new Set([
  "coffee-table",
  "side-table",
  "console-table",
  "library-table",
  "library-chair",
  "reading-light",
  "towel-bench",
]);
export function editable(part, f) {
  const source = part.piece_edits?.[f.id]?.source || f.id;
  return (
    (LOOSE.has(source) || source === "salon-coffee-table") &&
    ![...(part.asset_bindings || []), ...(part.style?.bindings || [])].some(
      (b) => b.furniture_id === f.id && b.asset_id,
    )
  );
}
export function coffeeTables(part, suite) {
  if (!suite || part.suite_yaw_deg) return [];
  return (
    part.coffee_tables ?? [
      {
        id: "salon-coffee-table",
        name: "Marble coffee table",
        category: "table",
        x_m: suite.x_m + (suite.width_m - 1.03) / 2,
        y_m: suite.y_m + 0.83,
        width_m: 1.03,
        depth_m: 0.48,
        height_m: 0.38,
        rotation_deg: 0,
      },
    ]
  );
}
function buildPiece(part, f) {
  const spec = part.piece_edits?.[f.id] || {};
  const yaw = spec.yaw || 0,
    swapped = yaw % 180 !== 0;
  const w = swapped ? f.depth_m : f.width_m,
    d = swapped ? f.width_m : f.depth_m;
  let parts = studioFurniture({
    ...f,
    id: spec.model ? "coffee-table" : spec.source || f.id,
    x_m: 0,
    y_m: 0,
    width_m: w,
    depth_m: d,
  });
  if (!spec.model && (spec.source || f.id) === "salon-coffee-table") {
    // Reuse the authored marble tabletop, vase and book in local coordinates.
    parts = studioFurniture({
      id: "salon-suite",
      width_m: 2.8,
      depth_m: 2.35,
      height_m: 0.94,
      x_m: 0,
      y_m: 0,
    })
      .filter((p) => p.coffeeComponent)
      .map((p) => ({
        ...p,
        xyz: [p.xyz[0] - (2.8 - 1.03) / 2, p.xyz[1] - 0.83, p.xyz[2]],
      }));
  }
  if (spec.model === "round") {
    parts = [
      {
        name: "Round oak tabletop",
        xyz: [w / 2, d / 2, f.height_m - 0.025],
        wdh: [w, d, 0.05],
        shape: "cylinder",
        finish: "oak",
        radius: 0,
      },
      {
        name: "Pedestal",
        xyz: [w / 2, d / 2, (f.height_m - 0.05) / 2],
        wdh: [w * 0.36, d * 0.36, f.height_m - 0.05],
        shape: "cylinder",
        finish: "walnut",
        radius: 0,
      },
    ];
  }
  return parts.map((p) => {
    const [x, y, z] = p.xyz;
    const [a, b] =
      yaw === 90
        ? [d - y, x]
        : yaw === 180
          ? [w - x, d - y]
          : yaw === 270
            ? [y, w - x]
            : [x, y];
    return {
      ...p,
      xyz: [f.x_m + a, f.y_m + b, z],
      wdh: swapped ? [p.wdh[1], p.wdh[0], p.wdh[2]] : p.wdh,
    };
  });
}
export function savedFurnitureParts(part, f, studio) {
  if (f.id === "salon-suite" && !part.suite_yaw_deg && part.coffee_tables) {
    const original = studioFurniture(f).filter((p) => !p.coffeeComponent);
    for (const table of part.coffee_tables) {
      for (const p of buildPiece(part, table)) {
        Object.defineProperty(p, "selectedPiece", { value: table });
        original.push(p);
      }
    }
    return original;
  }
  if (part.piece_edits?.[f.id]) return buildPiece(part, f);
  return studio
    ? studioFurniture(f, part.suite_yaw_deg, part.dining_variant)
    : [];
}
