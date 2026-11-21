import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import {asksChairChange, explanation} from "../town/explanation.js";

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

test("synthetic chair edit changes the measured gap independently of window and finish", () => {
  const {home, bedroom, manifest} = selected();
  const answer = q => explanation(home, q, manifest);
  const previous = ["chair", "window", "oak"].map(answer);
  bedroom.furniture.find(f => f.id === "desk-chair").y_m -= 0.2;
  assert.notEqual(answer("chair"), previous[0]);
  assert.equal(answer("window"), previous[1]);
  assert.equal(answer("oak"), previous[2]);
});

test("chair movement compares consecutive revisions of the same project", () => {
  const {home, bedroom, manifest} = selected();
  const previous = {project: manifest.project, revision: manifest.revision, home: structuredClone(home)};
  bedroom.furniture.find(f => f.id === "desk-chair").x_m += 0.2;
  manifest.revision++;
  manifest.home_id = home.id = "synthetic-edited-home";
  const ask = prior => explanation(home,"What changed when I moved the chair?",manifest,prior);
  assert.match(ask(previous), /Displacement: 0.200 m.*0.060 m before and 0.060 m after/);
  for (const q of ["Compare where the chair was before with where it is now.",
                   "Did the chair move farther under the desk or away from it?",
                   "Could you compare the bedroom chair across revisions?"]) {
    assert.match(explanation(home, q, manifest, previous), /Displacement: 0.200 m/);
  }
  assert.match(ask({...previous, project:"other"}), /needs this saved revision/);
  assert.match(ask(null), /needs this saved revision/);
});

test("a generic desk question with two desks needs a room", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  assert.match(explanation(home, "Why put the desk near the window?"), /Which desk.*bedroom.*study/);
  assert.match(explanation(home, "Why put the bedroom desk near the window?"), /Belaya.*nearest window/);
  assert.match(explanation(home, "How far is the study desk from its window?"), /study work-table footprint and window study-window/);
});


test("forward-looking chair fit asks for measurements without fetching history", () => {
  const {home, manifest} = selected();
  for (const question of ["Can I move the chair under the desk?", "Would the chair fit if I moved it?", "Will the chair I picked earlier fit under the desk?"]) {
    assert.equal(asksChairChange(question), false);
    assert.match(explanation(home, question, manifest), /clear width between supports/);
  }
});

test("study answers resolve the displayed name and use the writing suite tabletop", () => {
  const home = {id: fresh.home_id, rooms: fresh.rooms.map(part => ({design: part, suite_yaw_deg: part.suite_yaw_deg}))};
  const study = home.rooms.find(p => p.design.room.id === "study");
  const desk = study.design.furniture.find(f => f.id === "writing-suite");
  const room = study.design.room;
  study.suite_yaw_deg = 0;
  room.windows = [{id:"study-test-opening",wall:"south",offset_m:0,width_m:1}];
  const center = [desk.x_m + desk.width_m / 2, desk.y_m + desk.depth_m - 0.38];
  const distance = Math.hypot(center[0] - .5, center[1]).toFixed(2);
  const answer = explanation(home, "How far is the Writing Suite from its window?");
  assert.ok(answer.includes(distance + " m"));
  assert.match(answer, /study writing-suite tabletop and window study-test-opening/);
  assert.match(explanation(home, "Can the study chair fit under the desk?"), /clearances are unavailable for this study/);
});


test("revision comparisons distinguish a polite request from a fit question", () => {
  assert.equal(asksChairChange("Could you compare the bedroom chair across revisions?"), true);
  assert.equal(asksChairChange("How does the chair position change between revisions?"), true);
  const {home, manifest} = selected();
  assert.match(explanation(home, "Will the bedroom chair tuck in when I am done studying?", manifest), /0.48 m wide/);
});


test("conference study answer matches the saved tabletop-to-east-window distance", () => {
  const board = JSON.parse(readFileSync(new URL("../../../docs/data/conference-sprint/before.json", import.meta.url)));
  const home = {id: board.home_id, rooms: board.rooms.map(design => ({design}))};
  const study = board.rooms.find(p => p.room.id === "study");
  const suite = study.furniture.find(f => f.id === "writing-suite");
  const [x, y] = suite.parts.find(p => p.name === "Tabletop").xyz;
  const [w] = study.room.windows;
  assert.equal(w.wall, "east");
  const distance = Math.hypot(study.room.width_m - x, w.offset_m + w.width_m / 2 - y).toFixed(2);
  assert.equal(distance, "4.19");
  assert.ok(explanation(home, "How far is the Writing Suite from its window?").includes(distance + " m"));
});
