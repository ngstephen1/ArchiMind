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
