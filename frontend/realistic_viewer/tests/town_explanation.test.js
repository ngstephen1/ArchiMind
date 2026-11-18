import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import {explanation} from "../town/explanation.js";

test("placement answers use revision geometry, including older inventories",()=>{
 const h=JSON.parse(readFileSync(new URL("../town/showcase.json",import.meta.url)));
 const d=h.rooms.find(p=>p.design.room.id==="bedroom").design;
 const desk=d.furniture.find(f=>f.id==="belaya"),chair=d.furniture.find(f=>f.id==="desk-chair");
 chair.width_m=.51;chair.x_m=desk.x_m;chair.y_m=desk.y_m+desk.depth_m+.31;
 assert.match(explanation(h,"CHAIR"),/0.51 m wide.*0.31 m apart/);
 d.furniture=d.furniture.filter(f=>f.id!=="bedside-lamp");
 assert.match(explanation(h,"lamp"),/no recorded bed-and-nightstand/);
 d.room.windows=[];
 assert.match(explanation(h,"window"),/no recorded window/);
});

test("designer chair answers distinguish the saved model from its reservation", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  const bedroom = home.rooms.find(p => p.design.room.id === "bedroom");
  bedroom.designer_chair = {name: "Fixture chair", dimensions_wdh_m: [.45, .50, .80]};
  assert.match(explanation(home, "Why this chair?"), /Fixture chair.*0.45 m.*reserved footprint is 0.48 × 0.52 m/);
});

const fresh = JSON.parse(readFileSync(new URL("../../../docs/data/fresh-home/before.json", import.meta.url)));
function selected() {
  const manifest = structuredClone(fresh.bedroom);
  const bedroom = structuredClone(fresh.rooms.find(p => p.room.id === "bedroom"));
  const home = {id: fresh.home_id, palette: fresh.palette, rooms: [{design: bedroom}]};
  return {home, bedroom, manifest};
}
for (const [question, modify, expected] of [
  ["chair", () => {}, /0.06 m apart/],
  ["chair fit", () => {}, /clear width between supports/],
  ["chair", b => {b.furniture = b.furniture.filter(f => f.id !== "belaya");}, /no recorded desk-and-chair/],
  ["desk window", () => {}, /4.16 m.*west/],
  ["window glare", () => {}, /glare have not been established/],
  ["window", b => {b.room.windows = [];}, /no recorded window/],
  ["oak", () => {}, /belaya.*variant_label = Oak/],
  ["oak", (_, m) => {m.furniture = [];}, /No selected.*authored oak palette/],
  ["oak", (_, m) => {m.home_id = "earlier";}, /unavailable/],
]) {
  test("saved bedroom evidence: " + expected.source, () => {
    const {home, bedroom, manifest} = selected();
    modify(bedroom, manifest);
    const snapshot = JSON.stringify({home, manifest});
    assert.match(explanation(home, question, manifest), expected);
    assert.equal(JSON.stringify({home, manifest}), snapshot);
  });
}
