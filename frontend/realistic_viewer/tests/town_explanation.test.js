import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import {asksChairChange, explanation, isSavedDesignQuestion, isUnambiguousSavedDesignQuestion} from "../town/explanation.js";

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

test("a standalone why question stays on the saved revision", () => {
  assert.equal(isSavedDesignQuestion("Why did you put the desk there?"), true);
  assert.equal(isSavedDesignQuestion("Why is it there? Then redesign the salon."), false);
  assert.equal(isSavedDesignQuestion("WhyNot move the chair?"), false);
});

test("saved comparison evidence preserves a specific daylight question", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  home.evidence.comparison = {routes: [], dining_places: {}, passage_m: 0.6};
  assert.match(explanation(home, "Explain daylight in the study"), /nearest window center/);
  assert.match(explanation(home, "Explain the placements"), /modeled passage check/);
});


test("the Decisions shortcut only bypasses standalone saved questions", () => {
  assert.equal(isUnambiguousSavedDesignQuestion("Why is the desk 4.46 m from the window?"), true);
  assert.equal(isUnambiguousSavedDesignQuestion("Why is the chair there? I mean the one at Belaya."), true);
  assert.equal(isUnambiguousSavedDesignQuestion("Why is the chair there? I mean the one at Belaya, move it."), false);
  assert.equal(isUnambiguousSavedDesignQuestion("Why is the chair there? I mean the one at Belaya, could you move it closer?"), false);
  assert.equal(isUnambiguousSavedDesignQuestion("Why is the chair there? Move it closer."), false);
  assert.equal(isUnambiguousSavedDesignQuestion("Why is it there and move the chair closer?"), false);
  assert.equal(isUnambiguousSavedDesignQuestion("Why is it there and can you create a new one?"), false);
});

test("saved storage and task lighting answers distinguish objects from missing measurements", () => {
  const {home, bedroom} = selected();
  assert.match(explanation(home, "What storage is in the bedroom?"), /no recorded storage/);
  bedroom.furniture.push({id: "retained-wardrobe", category: "wardrobe", width_m: 1.2, depth_m: .6});
  assert.match(explanation(home, "What bedroom storage is provided?"), /bedroom retained-wardrobe, 1.20 × 0.60 m/);
  assert.match(explanation(home, "Explain task lighting at the bedroom desk"), /bedroom workspace: belaya.*work-surface light measurement/);
});

test("saved dining capacity reports seats per recorded table and ignores stale room evidence", () => {
  const home = {rooms: [
    {design: {room: {id: "bedroom"}, furniture: []}},
    {design: {room: {id: "kitchen-dining"}, furniture: [{id: "breakfast-suite"}]}},
  ], evidence: {comparison: {dining_places: {"kitchen-dining": 4, salon: 4}}}};
  const ask = () => explanation(home, "How many seats are at the dining table?");
  assert.match(ask(), /kitchen-dining breakfast-suite: 4 modeled places at one table/);
  assert.doesNotMatch(ask(), /salon|8 modeled places/);
  home.rooms[1].design.furniture = [];
  assert.match(ask(), /no recorded seating capacity/);
});

test("specific lighting questions keep their room and bypass the overview", () => {
  const home = {id: fresh.home_id, rooms: fresh.rooms.map(design => ({design})),
    evidence: {comparison: {routes: [], dining_places: {}, passage_m: 0.6}}};
  home.rooms.find(p => p.design.room.id === "living").design.furniture.push({id: "reading-suite"});
  assert.match(explanation(home, "Explain task lighting in the study"), /study workspace: writing-suite/);
  assert.match(explanation(home, "Explain task lighting at the desk"), /Which workspace.*belaya.*writing-suite/);
  assert.match(explanation(home, "Explain task lighting at the Belaya"), /bedroom workspace: belaya/);
  const reading = explanation(home, "How is the reading light in the living room?");
  assert.match(reading, /living reading-suite.*modeled reading lamp/);
  assert.doesNotMatch(reading, /belaya/);
  assert.match(explanation(home, "How far is the bedside reading light from the bed?"), /nearest edge/);
});

test("named dining groups and dedicated storage use their own saved evidence", () => {
  const home = {rooms: [
    {design: {room: {id: "bedroom"}, furniture: []}},
    {design: {room: {id: "kitchen-dining"}, furniture: [{id: "breakfast-suite"}]}},
    {design: {room: {id: "salon"}, furniture: [{id: "salon-dining"}]}},
    {design: {room: {id: "study"}, furniture: [
      {id: "bookcase", name: "Bookcase", category: "storage", width_m: .85, depth_m: .34},
    ]}},
  ], evidence: {salon: {dining_places: 4}}};
  assert.match(explanation(home, "How many dining seats are in the salon?"), /salon salon-dining: 4 modeled places/);
  assert.match(explanation(home, "What is the number of dining places in the salon?"), /salon salon-dining: 4 modeled places/);
  home.evidence.comparison = {dining_places: {"kitchen-dining": 4, salon: 4}};
  const breakfast = explanation(home, "How many seats are at the Breakfast Suite?");
  assert.match(breakfast, /kitchen-dining breakfast-suite: 4 modeled places/);
  assert.doesNotMatch(breakfast, /salon/);
  for (const names of ["Breakfast Suite and the Salon Dining table", "Salon Dining table and the Breakfast Suite"]) {
    const answer = explanation(home, `How many seats are at the ${names}?`);
    assert.match(answer, /breakfast-suite: 4.*salon-dining: 4/);
  }
  const light = explanation(home, "Explain the task lighting over the Breakfast Suite table.");
  assert.match(light, /kitchen-dining breakfast-suite.*work-surface light measurement/);
  assert.doesNotMatch(light, /modeled places/);
  assert.match(explanation(home, "How much closet space is in the study?"), /no recorded wardrobe or closet/);
  assert.match(explanation(home, "What storage is in the study?"), /study bookcase/);
  assert.match(explanation(home, "What study storage exists besides a closet?"), /study bookcase/);
});


test("zoning answers compare only the two consecutive schemes on the same saved shell", () => {
  const {home, manifest} = selected();
  Object.assign(home, {width: 15, depth: 16, zoning: "service-core"});
  home.evidence = {comparison: {routes: [{room: "kitchen-dining", target: "salon", distance_m: 8.779}],
    direct_service: {door_id: "service-core-passage", crossing_m: 1.3},
    dining_places: {}, passage_m: .6}};
  const previousHome = structuredClone(home);
  previousHome.zoning = "gallery";
  previousHome.evidence.comparison.routes[0].distance_m = 3.29;
  delete previousHome.evidence.comparison.direct_service;
  const previous = {project: manifest.project, revision: manifest.revision, home: previousHome};
  manifest.revision++;
  const ask = prior => explanation(home, "Compare the gallery and service-core zoning trade-offs", manifest, prior);
  assert.match(ask(previous), /Gallery.*3.29 m.*Grouped service core.*service-core-passage.*1.30 m.*8.78 m/);
  assert.match(explanation(home, "Explain the layout", manifest), /Grouped service core.*1.30 m checked crossing/);
  for (const evidence of [{...previous, project: "another project"},
                          {...previous, home: {...previousHome, depth: 14}},
                          {...previous, revision: previous.revision - 1}]) {
    assert.doesNotMatch(ask(evidence), /3.29 m/);
    assert.match(ask(evidence), /consecutive saved gallery and service-core revisions/);
  }
});

test("compound evidence questions keep the chair in its specified room", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  const question = "Will the bedroom chair fit under the desk? Can the study stop sound transfer? Which supplier has it in stock?";
  const answer = explanation(home, question);
  assert.match(answer, /Source: bedroom desk-chair and belaya/);
  assert.match(answer, /clear width between supports/);
  assert.match(answer, /Acoustic performance is unverified/);
  assert.match(answer, /Supplier availability is unknown/);
  assert.doesNotMatch(answer, /Study chair fit/);
  assert.match(explanation(home, "Does the living room chair fit and is it in stock?"), /For the living.*Supplier availability is unknown/);
  assert.doesNotMatch(explanation(home, "Is the supplier able to deliver that chair?"), /footprint/);
});

test("rooms in a privacy question do not become the location of the furniture", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  const answer = explanation(home, "Can the plan certify privacy between the salon and living room, and will the writing chair tuck beneath the worktable?");
  assert.match(answer, /Source: bedroom desk-chair and belaya/);
  assert.match(answer, /Acoustic performance is unverified/);
  assert.match(answer, /Supplier availability is unknown/);
  assert.doesNotMatch(answer, /Which room contains/);
});

test("composite evidence preserves distinct room questions and comparison history", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  const answer = explanation(home, "Will the bedroom chair fit? Can the study chair fit? Is it in stock?");
  assert.match(answer, /bedroom desk-chair and belaya/);
  assert.match(answer, /Study chair fit/);
  assert.doesNotMatch(explanation(home, "Will the living room chairs fit? Can I order them now?"), /bedroom desk-chair/);
  assert.match(explanation(home, "How far is the study desk from the window to avoid noise?"), /window center/);
  assert.match(explanation(home, "Can the study block sound?"), /Acoustic performance is unverified/);
  assert.match(explanation(home, "Can I order the chair now?"), /Supplier availability is unknown/);
  assert.ok(asksChairChange("What changed when I moved the bedroom chair? Can the study block sound?"));
});

test("room qualifiers and descriptive adjectives stay attached to the plan question", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  assert.match(explanation(home, "In the study, can the chair fit under the desk, and is it in stock?"), /Study chair fit/);
  assert.match(explanation(home, "Can the bedroom chair from the supplier and the desk fit together?"), /clear width between supports/);
  assert.match(explanation(home, "Measure the bedroom chair gap to the desk before contacting a supplier."), /bedroom desk-chair and belaya/);
  assert.equal(explanation(home, "What storage is in the quiet study?"), explanation(home, "What storage is in the study?"));
  assert.ok(asksChairChange("What changed when I moved the bedroom chair after adjusting the living room?"));
});

test("fit and movement stay with the named chair when another room supplies context", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  assert.match(explanation(home, "Will the bedroom chair fit, with enough privacy in the study?"), /bedroom desk-chair and belaya/);
  assert.match(explanation(home, "Can I hear the TV from the study?"), /Acoustic performance is unverified/);
  assert.match(explanation(home, "Is the quiet study suitable for calls?"), /Acoustic performance is unverified/);
  assert.match(explanation(home, "Is the study private enough for calls?"), /Acoustic performance is unverified/);
  const q = "Did the study chair move when we moved the bedroom chair?";
  assert.equal(asksChairChange(q), false);
  assert.match(explanation(home, q), /study chair move requires saved positions/);
});

test("fit questions bind chair and desk rooms separately", () => {
  const home = JSON.parse(readFileSync(new URL("../town/showcase.json", import.meta.url)));
  const ask = text => explanation(home, text);
  const mixed = ask("Will the bedroom chair fit under the desk in the study?");
  assert.match(mixed, /chair is in the bedroom.*desk is in the study/);
  assert.doesNotMatch(mixed, /closest edges|gap from that reservation/);
  assert.match(ask("Will the bedroom desk-chair fit under the study desk?"), /chair is in the bedroom.*desk is in the study/);
  assert.match(ask("Will the bedroom chair fit under the study work table?"), /chair is in the bedroom.*desk is in the study/);
  assert.match(ask("Will the bedroom chair fit under its desk? Can I hear more about the study desk?"), /bedroom desk-chair and belaya.*window center/);
  assert.match(ask("Which chair will fit under the desk, the bedroom chair or the living room chair?"), /Which chair and desk pair/);
  assert.match(ask("Can the desk-chair in the study fit under its desk?"), /Study chair fit/);
  assert.match(ask("Can the study chair be moved under the desk?"), /Study chair fit/);
  assert.match(ask("Can I hear more about the study desk?"), /window center/);
});
