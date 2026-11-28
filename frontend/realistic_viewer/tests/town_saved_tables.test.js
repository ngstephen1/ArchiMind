import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { homeBoard } from "../town/home_board.js";
import { floorPlan } from "../town/floor_plan.js";
import { coffeeTables, presentationFurniture } from "../town/saved_pieces.js";

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
