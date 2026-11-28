import assert from "node:assert/strict";
import test from "node:test";
import { bindFinishChat } from "../town/finish_chat.js";

for (const outcome of ["success", "failure", "project changed", "newer revision"]) {
  test("an older finish save respects the current dialog: " + outcome, async () => {
    const elements = new Map();
    function el(id) {
      if (!elements.has(id)) {
        const item = Object.assign(new EventTarget(), {
          parentElement: {}, options: [],
          style: { removeProperty() {}, setProperty() {} },
          replaceChildren(...options) { this.options = options; },
          showModal() { this.open = true; },
          close() { this.open = false; this.dispatchEvent(new Event("close")); },
        });
        elements.set(id, item);
      }
      return elements.get(id);
    }
    let complete, fail;
    const delay = new Promise((resolve, reject) => {complete = resolve; fail = reject;});
    const state = {project:"a",revision:1,home:{rooms:[]}}, synced=[];
    bindFinishChat({el, context:()=>state, sync:data=>synced.push(data.revision),
      api:async(path)=>path.endsWith("/preview") ? {home:{id:"hash"},finish:"sage",summary:"Checked"} : delay});
    el("scopeFinish").onclick();
    await el("finishCheck").onclick();
    const save = el("finishSave").onclick();
    el("finishDialog").close();
    el("scopeFinish").onclick();
    if (outcome === "project changed") state.project = "b";
    if (outcome === "newer revision") state.revision = 4;
    await el("finishCheck").onclick();
    const laterStatus = el("finishStatus").textContent;
    if(outcome === "failure") fail(new Error("old failure")); else complete({revision:2});
    await save;
    assert.equal(el("finishDialog").open, true);
    assert.equal(el("finishStatus").textContent, laterStatus);
    assert.equal(el("finishSave").disabled, false);
    assert.deepEqual(synced, outcome === "success" ? [2] : []);
  });
}
