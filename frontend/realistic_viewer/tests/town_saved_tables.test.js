import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { homeBoard } from "../town/home_board.js";
import { floorPlan } from "../town/floor_plan.js";
import { coffeeTables, presentationFurniture, schematicFurniture } from "../town/saved_pieces.js";

const fixture = new URL("../../../docs/data/furnished-residence/home.json", import.meta.url);

test("saved salon tables reach the furniture schedule, drawing and Blender export once each", () => {
  const home = JSON.parse(readFileSync(fixture, "utf8"));
  const salon = home.rooms.find(part => part.design.room.id === "salon");
  const suite = salon.design.furniture.find(item => item.id === "salon-suite");
  const [original] = coffeeTables(salon, suite);
  const copy = {...original, id: original.id + "-copy-2", x_m: 4, y_m: 0.5};
  const exported = () => homeBoard({home, project: "reopened-home", revision: 2})
    .rooms.find(part => part.room.id === "salon").furniture;
  const historicalParts = exported().find(item => item.id === suite.id).parts;
  assert.ok(!exported().some(item => item.id === original.id));
  salon.coffee_tables = [original, copy];
  salon.piece_edits = {[copy.id]: {source: original.id}};
  salon.finish_overrides = {objects: {[copy.id]: "sage"}};

  assert.deepEqual(presentationFurniture(salon).slice(-2), [original, copy]);
  const rows = exported();
  const duplicate = rows.find(item => item.id === copy.id);
  assert.deepEqual([duplicate.x_m, duplicate.y_m, duplicate.width_m, duplicate.depth_m],
    [4, 0.5, original.width_m, original.depth_m]);
  assert.ok(duplicate.parts.length && duplicate.parts.every(p => p.finish === "proposal-sage"));
  const suiteParts = rows.find(item => item.id === suite.id).parts;
  const primaryParts = rows.find(item => item.id === original.id).parts;
  assert.equal(suiteParts.length + primaryParts.length, historicalParts.length);
  assert.equal(duplicate.parts.length, primaryParts.length);

  const rectangles = [];
  const context = new Proxy({}, {get: (_, name) => name === "fillRect" ?
    (...args) => rectangles.push(args) : () => {}});
  const canvas = {width: 780, height: 400, getContext: () => context};
  floorPlan(home, canvas);
  const s = Math.min(510 / home.width, 350 / home.depth);
  const x = (canvas.width - home.width * s) / 2 + s * salon.origin[0];
  const y = canvas.height - 20 - s * salon.origin[1];
  assert.ok(rectangles.some(([left, top, width, depth]) =>
    left === x + s * copy.x_m && top === y - s * (copy.y_m + copy.depth_m) &&
    width === s * copy.width_m && depth === s * copy.depth_m));

  salon.coffee_tables = [];
  assert.ok(!exported().some(item => [copy.id, original.id].includes(item.id)));
  assert.equal(exported().find(item => item.id === suite.id).parts.length, suiteParts.length);
});

test("finish rows identify the saved surfaces and objects while preserving base materials elsewhere", () => {
  const home = JSON.parse(readFileSync(fixture, "utf8"));
  for (const part of home.rooms) part.finish_overrides = {floor: "walnut"};
  home.hall_finish = "walnut";
  const bedroom = home.rooms.find(p => p.design.room.id === "bedroom");
  bedroom.finish_overrides.wall = "dark green";
  const salon = home.rooms.find(p => p.design.room.id === "salon");
  salon.finish_overrides.objects = {"salon-coffee-table": "sage"};
  const board = homeBoard({home, project: "finish-review", revision: 4});
  assert.deepEqual(Object.keys(board.finishes).filter(k => k.startsWith("proposal-")).sort(),
    ["proposal-dark green", "proposal-sage", "proposal-walnut"]);
  const rows = board.finish_schedule;
  assert.deepEqual(rows.find(row => row.finish === "dark green").locations,
    [{room: "bedroom", label: bedroom.design.room.name}]);
  assert.equal(rows.find(row => row.finish === "walnut").locations.length, home.rooms.length + 1);
  assert.deepEqual(rows.find(row => row.finish === "sage").locations.map(loc => loc.object), ["salon-coffee-table"]);
  assert.deepEqual(board.base_finish_locations.floor, []);
  assert.deepEqual(board.base_finish_locations.tile, []);
  assert.ok(!board.base_finish_locations.wall.includes(bedroom.design.room.name));
  assert.ok(board.base_finish_locations.wall.includes(salon.design.room.name));
});

test("the original coffee table remains visible in both elevations after a finish-only edit", () => {
  const home = JSON.parse(readFileSync(fixture, "utf8"));
  const salon = home.rooms.find(part => part.design.room.id === "salon");
  const id = "salon-coffee-table";
  salon.finish_overrides = {objects: {[id]: "sage"}};
  const shapes = schematicFurniture(salon);
  const table = shapes.find(piece => piece.id === id);
  for (const east of [true, false]) {
    const h = east ? "y_m" : "x_m", width = east ? "depth_m" : "width_m";
    const depth = east ? "x_m" : "y_m";
    const order = shapes.toSorted((a, b) => b[depth] - a[depth]);
    let visible = 0;
    for (let x = table[h] + 0.005; x < table[h] + table[width]; x += 0.01) {
      const front = order.findLast(piece => piece[h] <= x && x <= piece[h] + piece[width] &&
        (piece.z_m ?? 0) <= 0.2 && 0.2 <= (piece.z_m ?? 0) + piece.height_m);
      if (front?.id === id) visible++;
    }
    assert.ok(visible > 5, "Part of the table face should be visible in this direction");
  }
});

test("a room-only paint change keeps the base hall independent of pack floors", () => {
  const home = JSON.parse(readFileSync(fixture, "utf8"));
  const room = home.rooms.find(p => p.design.room.id === "salon");
  room.finish_overrides = {wall: "dark green"};
  const board = homeBoard({project: "wall-only", home, revision: 2});
  assert.deepEqual(board.base_finish_locations.hall_floor, ["Hall"]);
  assert.deepEqual(board.base_finish_locations.hall_wall, ["Hall ends"]);
  assert.ok(!board.base_finish_locations.floor.includes("Hall"));
  assert.ok(!board.base_finish_locations.wall.includes("Hall ends"));
  assert.deepEqual(board.finish_schedule.map(r => r.surface), ["wall"]);
});
