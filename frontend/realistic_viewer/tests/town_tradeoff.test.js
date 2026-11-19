import assert from "node:assert/strict";
import test from "node:test";
import { competingGoals } from "../town/tradeoff.js";

function home(near, far) {
  return {evidence:{room_preferences:[
    {room:"kitchen-dining", target:"salon", relation:"near", center_distance_m:near},
    {room:"living", target:"study", relation:"far", center_distance_m:far},
  ]}};
}

test("competing priorities recommend original candidates without mutating them", () => {
  const homes = [home(12.899,13.462), home(9.685,10.025)];
  homes[1].evidence.room_preferences.reverse();
  const before = JSON.stringify(homes);
  assert.deepEqual(competingGoals(homes).map(g => g.winner), [1,0]);
  assert.equal(JSON.stringify(homes), before);
});

test("offer a question only for a genuine measurable conflict", () => {
  for (const homes of [[], [home(1,2)], [{},{}], [home(1,2),home(2,1)],
    [home(1,2),home(1,3)], [home(1,2),home(NaN,3)]]) {
    assert.deepEqual(competingGoals(homes), []);
  }
});
