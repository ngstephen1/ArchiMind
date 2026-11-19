// Original furniture studies. Positions and sizes are room-local metres (east, north, up).
export const studioFinishes = {
  oak: "#9d7555",
  walnut: "#523b32",
  moss: "#596a4d",
  wool: "#d6cbb8",
  brass: "#aa8752",
  marble: "#e6e0d3",
  ink: "#343b39",
  paper: "#e3d9c1",
  clay: "#9e5f4b",
  glass: "#637873",
};

export function studioFurniture(f, suiteYaw = 0) {
  if (f.id === "salon-suite" && suiteYaw) {
    if (suiteYaw !== 90) throw Error("Unsupported salon grouping orientation.");
    const parts = studioFurniture({
      ...f,
      width_m: f.depth_m,
      depth_m: f.width_m,
      x_m: 0,
      y_m: 0,
    });
    return parts.map((p) => ({
      ...p,
      xyz: [f.x_m + f.width_m - p.xyz[1], f.y_m + p.xyz[0], p.xyz[2]],
      wdh: [p.wdh[1], p.wdh[0], p.wdh[2]],
    }));
  }
  const parts = [];
  function piece(
    name,
    finish,
    x,
    y,
    z,
    w,
    d,
    h,
    radius = 0.012,
    shape = "box",
  ) {
    parts.push({
      name,
      finish,
      xyz: [f.x_m + x, f.y_m + y, z],
      wdh: [w, d, h],
      radius,
      shape,
    });
  }
  function legs(x, y, w, d, height, finish) {
    for (const i of [-1, 1])
      for (const j of [-1, 1])
        piece(
          "Tapered foot",
          finish,
          x + i * w * 0.4,
          y + j * d * 0.4,
          height / 2,
          0.044,
          0.044,
          height,
          0.008,
        );
  }
  function table(x, y, w, d, h, finish) {
    legs(x, y, w, d, h - 0.045, "walnut");
    piece("Tabletop", finish, x, y, h - 0.023, w, d, 0.046, 0.022);
  }
  function seat(x, y, w, d, h, sign, finish) {
    legs(x, y, w, d, 0.24, "walnut");
    piece(
      "Upholstered deck",
      finish,
      x,
      y,
      0.28,
      w - 0.02,
      d - 0.02,
      0.15,
      0.055,
    );
    const n = w > 1.3 ? 2 : 1;
    for (let i = 0; i < n; i++) {
      const cx = x - w / 2 + (w / n) * (i + 0.5);
      piece(
        "Boxed seat cushion",
        finish,
        cx,
        y - sign * 0.045,
        0.416,
        w / n - 0.022,
        d - 0.13,
        0.15,
        0.065,
      );
      piece(
        "Back cushion",
        finish,
        cx,
        y + sign * (d / 2 - 0.085),
        (0.41 + h) / 2,
        w / n - 0.026,
        0.17,
        h - 0.41,
        0.075,
      );
    }
    for (const side of [-1, 1])
      piece(
        "Arm bolster",
        finish,
        x + side * (w / 2 - 0.055),
        y,
        0.51,
        0.11,
        d - 0.07,
        0.27,
        0.05,
      );
  }
  const w = f.width_m,
    d = f.depth_m,
    h = f.height_m,
    x = w / 2,
    y = d / 2;
  if (f.id === "salon-suite") {
    piece(
      "Bound wool rug",
      "paper",
      x,
      y,
      0.011,
      w - 0.022,
      d - 0.022,
      0.022,
      0.008,
    );
    for (const side of [-1, 1])
      piece(
        "Woven border",
        "clay",
        x + side * (w / 2 - 0.072),
        y,
        0.023,
        0.022,
        d - 0.14,
        0.002,
        0.001,
      );
    seat(x, d - 0.4, 1.98, 0.8, 0.94, 1, "wool");
    seat(0.41, 0.34, 0.78, 0.68, 0.82, -1, "moss");
    seat(w - 0.41, 0.34, 0.78, 0.68, 0.82, -1, "moss");
    table(x, 1.07, 1.03, 0.48, 0.38, "marble");
    piece(
      "Earthenware vase",
      "clay",
      x + 0.25,
      1.07,
      0.475,
      0.14,
      0.14,
      0.19,
      0,
      "sphere",
    );
    piece(
      "Ceramic neck",
      "clay",
      x + 0.25,
      1.07,
      0.56,
      0.052,
      0.052,
      0.064,
      0,
      "cylinder",
    );
    for (let i = 0; i < 5; i++) {
      const sx = x + 0.25 + Math.sin(i) * 0.026,
        sy = 1.07 + Math.cos(i) * 0.03,
        h = 0.19 + i * 0.019;
      piece(
        "Botanical stem",
        "walnut",
        sx,
        sy,
        0.57 + h / 2,
        0.006,
        0.006,
        h,
        0,
        "cylinder",
      );
      piece(
        "Olive leaf",
        "moss",
        sx + 0.018,
        sy,
        0.56 + h,
        0.065,
        0.025,
        0.039,
        0,
        "sphere",
      );
    }
    piece("Art monograph", "clay", x - 0.21, 1.08, 0.399, 0.23, 0.18, 0.038);
  } else if (f.id === "salon-dining") {
    table(x, y, 1.58, 0.76, 0.75, "walnut");
    for (const dx of [-0.44, 0.44])
      for (const sign of [-1, 1])
        seat(x + dx, y + sign * 0.72, 0.46, 0.46, 0.84, sign, "moss");
    for (const dx of [-0.44, 0.44])
      for (const sign of [-1, 1]) {
        const cy = y + sign * 0.22,
          cx = x + dx;
        piece(
          "Thrown dinner plate",
          "paper",
          cx,
          cy,
          0.763,
          0.225,
          0.225,
          0.026,
          0,
          "cylinder",
        );
        piece(
          "Linen napkin",
          "clay",
          cx,
          cy,
          0.782,
          0.065,
          0.148,
          0.016,
          0.005,
        );
        piece(
          "Water tumbler",
          "glass",
          cx + 0.19,
          cy - sign * 0.07,
          0.815,
          0.061,
          0.061,
          0.13,
          0,
          "cylinder",
        );
        piece(
          "Brass cutlery",
          "brass",
          cx - 0.15,
          cy,
          0.758,
          0.012,
          0.15,
          0.012,
          0.005,
        );
      }
    piece("Stoneware tray", "marble", x, y, 0.78, 0.4, 0.21, 0.06, 0.029);
  } else if (f.id === "writing-suite") {
    table(x, d - 0.38, 1.6, 0.74, 0.75, "oak");
    seat(x, d - 1.12, 0.49, 0.5, 0.84, -1, "moss");
    piece(
      "Leather blotter",
      "clay",
      x,
      d - 0.4,
      0.754,
      0.72,
      0.38,
      0.008,
      0.004,
    );
    piece(
      "Lamp base",
      "ink",
      0.25,
      d - 0.25,
      0.78,
      0.18,
      0.18,
      0.06,
      0.008,
      "cylinder",
    );
    piece(
      "Lamp stem",
      "brass",
      0.25,
      d - 0.25,
      0.94,
      0.016,
      0.016,
      0.27,
      0,
      "cylinder",
    );
    piece(
      "Lamp shade",
      "paper",
      0.25,
      d - 0.25,
      1.075,
      0.22,
      0.22,
      0.11,
      0.006,
      "sphere",
    );
    piece("Notebook", "paper", x + 0.29, d - 0.36, 0.767, 0.16, 0.22, 0.017);
  } else if (f.id === "breakfast-suite") {
    table(x, y, 1.32, 0.72, 0.74, "oak");
    for (const sign of [-1, 1])
      for (const dx of [-0.34, 0.34])
        seat(x + dx, y + sign * 0.61, 0.42, 0.4, 0.81, sign, "moss");
    piece("Breakfast bowl", "clay", x, y, 0.8, 0.22, 0.22, 0.12, 0, "sphere");
    for (const dx of [-0.34, 0.34])
      piece(
        "Stoneware side plate",
        "paper",
        x + dx,
        y,
        0.752,
        0.19,
        0.19,
        0.024,
        0,
        "cylinder",
      );
  } else if (f.id === "reading-suite") {
    piece("Loop pile rug", "paper", x, y, 0.012, w - 0.03, d - 0.03, 0.024);
    seat(x, d - 0.43, 1.94, 0.82, 0.89, 1, "wool");
    seat(0.43, 0.4, 0.78, 0.68, 0.81, -1, "clay");
    table(x, 0.91, 0.9, 0.46, 0.37, "walnut");
    piece("Open book", "paper", x - 0.1, 0.91, 0.382, 0.25, 0.17, 0.024);
    piece(
      "Reading lamp base",
      "ink",
      w - 0.27,
      0.4,
      0.035,
      0.29,
      0.29,
      0.07,
      0,
      "cylinder",
    );
    piece(
      "Reading lamp stem",
      "brass",
      w - 0.27,
      0.4,
      0.65,
      0.026,
      0.026,
      1.2,
      0,
      "cylinder",
    );
    piece(
      "Linen drum shade",
      "paper",
      w - 0.27,
      0.4,
      1.235,
      0.37,
      0.37,
      0.33,
      0,
      "cylinder",
    );
  } else if (f.id === "media-console" || f.id === "bookcase") {
    for (const i of [-1, 1])
      piece(
        "Carcass side",
        "walnut",
        x + (i * (w - 0.035)) / 2,
        y,
        h / 2,
        0.035,
        d,
        h,
      );
    const shelves = f.id === "bookcase" ? 5 : 2;
    for (let i = 0; i <= shelves; i++)
      piece(
        "Shelf",
        "oak",
        x,
        y,
        0.02 + ((h - 0.04) * i) / shelves,
        w,
        d,
        0.04,
      );
    for (let i = 0; i < 5; i++)
      piece(
        "Clothbound volume",
        ["paper", "moss", "clay"][i % 3],
        0.1 + i * 0.052,
        y,
        0.14,
        0.04,
        0.18,
        0.2 + (i % 2) * 0.035,
      );
  } else if (f.category === "bath") {
    piece("Bath plinth", "oak", x, y, h * 0.36, w - 0.08, d - 0.08, h * 0.72);
    piece("Enamel basin", "marble", x, y, h * 0.76, w, d, h * 0.48, 0.13);
    piece(
      "Inset basin",
      "glass",
      x,
      y,
      h * 0.994,
      w - 0.15,
      d - 0.16,
      h * 0.012,
      0.1,
    );
  } else if (f.category === "vanity" || f.category === "counter") {
    piece("Plinth", "ink", x, y, 0.05, w - 0.08, d - 0.05, 0.1);
    piece("Cabinet", "moss", x, y, h * 0.52, w - 0.02, d - 0.03, h * 0.82);
    piece("Honed stone", "marble", x, y, h - 0.023, w, d, 0.046);
    for (const sign of [-1, 1]) {
      piece(
        "Oak drawer",
        "oak",
        x + sign * w * 0.244,
        0.019,
        h * 0.53,
        w * 0.48,
        0.03,
        h * 0.71,
      );
      piece(
        "Brass pull",
        "brass",
        x + sign * w * 0.244,
        0.007,
        h * 0.72,
        w * 0.12,
        0.014,
        0.018,
      );
    }
    piece("Inset sink", "ink", x, y, h - 0.001, w * 0.45, d * 0.66, 0.002);
  } else if (f.id === "sofa") seat(x, y, w, d, h, 1, "wool");
  else if (f.category === "table" || f.id === "work-table")
    table(x, y, w, d, h, "oak");
  return parts;
}

// Elevated fixtures belong to the architectural layer, outside furniture reservations.
export function salonDetails(part) {
  const { room, furniture } = part.design;

  const out = [];
  const add = (name, finish, xyz, wdh, shape = "box", radius = 0.008) =>
    out.push({ name, finish, xyz, wdh, shape, radius });
  const { width_m: w, depth_m: d, ceiling_height_m: h } = room;
  if (room.id !== "salon") return out;
  // The south wall has no openings. Hang an original relief triptych as one ensemble.
  for (let n = 0; n < 3; n++) {
    const cx = w * 0.5 + (n - 1) * 0.58;
    add("Shadow-box frame", "walnut", [cx, 0.035, 1.6], [0.52, 0.065, 0.85]);
    add("Cotton paper", "paper", [cx, 0.071, 1.6], [0.485, 0.012, 0.815]);
    add(
      "Cut paper arc",
      ["moss", "clay", "ink"][n],
      [cx - 0.045, 0.081, 1.64 - n * 0.07],
      [0.3, 0.015, 0.38],
      "sphere",
    );
    add(
      "Cut paper horizon",
      "wool",
      [cx + 0.05, 0.095, 1.46],
      [0.32, 0.014, 0.08],
    );
  }
  for (const z of [0.13, h - 0.11]) {
    add(
      "North plaster moulding",
      "paper",
      [w / 2, d - 0.024, z],
      [w, 0.048, 0.048],
    );
    add(
      "South plaster moulding",
      "paper",
      [w / 2, 0.024, z],
      [w, 0.048, 0.048],
    );
  }
  for (const item of furniture.filter((f) => f.id === "salon-dining")) {
    const x = item.x_m + item.width_m / 2,
      y = item.y_m + item.depth_m / 2;
    add(
      "Ceiling rose",
      "brass",
      [x, y, h - 0.022],
      [0.16, 0.16, 0.044],
      "cylinder",
    );
    for (const dx of [-0.4, 0.4])
      add(
        "Pendant suspension",
        "ink",
        [x + dx, y, (2.12 + h) / 2],
        [0.009, 0.009, h - 2.12],
        "cylinder",
      );
    add("Pendant arm", "brass", [x, y, 2.12], [1.12, 0.025, 0.025]);
    for (const side of [-1, 1])
      for (const [j, dx] of [-0.48, -0.16, 0.16, 0.48].entries()) {
        const cy = y + side * 0.085;
        add(
          "Opal globe",
          "paper",
          [x + dx, cy, 2.09 + (j % 2) * 0.065],
          [0.168, 0.168, 0.168],
          "sphere",
        );
      }
  }
  return out;
}
