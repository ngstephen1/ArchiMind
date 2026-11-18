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
