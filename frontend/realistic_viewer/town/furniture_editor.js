// The picker supplies a saved object identity. The backend owns geometry and revision checks.
export function bindFurnitureEditor({ el, context, api, sync }) {
  const trigger = document.createElement("button");
  trigger.hidden = true;
  el("roomInspector").append(trigger);
  const dialog = document.createElement("dialog");
  dialog.setAttribute("aria-labelledby", "furnitureEditTitle");
  dialog.innerHTML = `<form><div class="title"><h2 id="furnitureEditTitle">Edit furniture</h2><button type="button" data-close aria-label="Close">×</button></div>
  <p data-piece></p><label>Describe the edit<input name="command" maxlength="200" placeholder="Replace this with a round table"></label><button type="button" data-use>Use request</button><label>Change<select name="action"><option value="move">Move</option><option value="rotate">Rotate 90°</option><option value="replace">Replace</option><option value="duplicate">Duplicate</option><option value="remove">Remove</option></select></label>
  <div data-placement><label>West edge from room west (m)<input type="number" step="any" min="0" name="x"></label><label>South edge from room south (m)<input type="number" step="any" min="0" name="y"></label></div>
  <label data-model>Table model<select name="model"><option value="round">Round oak coffee table</option><option value="rectangular">Rectangular oak coffee table</option></select></label>
  <label data-route><input type="checkbox" name="route"> <span data-route-label>Require a 90 cm door-to-sofa route</span></label>
  <p role="status"></p><button>Check edit</button> <button type="button" data-save hidden>Save revision</button></form>`;
  document.body.append(dialog);
  const find = (q) => dialog.querySelector(q),
    fields = dialog.querySelector("form").elements,
    status = find('[role="status"]'),
    save = find("[data-save]");
  let selected,
    preview,
    busy = false,
    serial = 0;
  function invalidate() {
    serial++;
    preview = null;
    save.hidden = true;
    status.textContent = "";
  }
  function refreshFields() {
    invalidate();
    find("[data-placement]").hidden = !["move", "duplicate"].includes(
      fields.action.value,
    );
    find("[data-model]").hidden = fields.action.value !== "replace";
    find("[data-route]").hidden = selected?.room !== "salon";
  }
  el("world").addEventListener("room-picked", () => {
    selected = null;
    trigger.hidden = true;
  });
  el("world").addEventListener("furniture-picked", (e) => {
    const { project, revision, applied, homeId } = context();
    if (!project || !revision || applied.id !== homeId) return;
    selected = { ...e.detail, project, base: revision };
    trigger.textContent = "Edit " + selected.name;
    trigger.hidden = false;
  });
  trigger.onclick = () => {
    if (!selected) return;
    const f = selected;
    find("[data-piece]").textContent =
      `${f.name} · ${f.id} · ${f.width_m.toFixed(2)} × ${f.depth_m.toFixed(2)} × ${f.height_m.toFixed(2)} m`;
    fields.command.value = "";
    fields.action.value = "move";
    fields.x.value = f.x_m;
    fields.y.value = f.y_m;
    const part = context().applied.rooms.find(p => p.design.room.id === f.room);
    fields.route.disabled = fields.route.checked = Boolean(part?.sofa_route);
    find("[data-route-label]").textContent = fields.route.disabled
      ? "Saved requirement · keep the 90 cm door-to-sofa route"
      : "Require a 90 cm door-to-sofa route";
    refreshFields();
    dialog.showModal();
  };
  find("[data-use]").onclick = () => {
    invalidate();
    const q = fields.command.value.trim().toLowerCase().replace(/[.!]$/, "");
    const noun =
      "(?:this(?: piece| table| chair)?|it|the (?:coffee |side )?table)";
    const coords = q.match(
      new RegExp(
        "^(move|duplicate) " +
          noun +
          " (?:to|at) (?:x ?=? ?)?([0-9]+(?:\\.[0-9]+)?) *,? (?:y ?=? ?)?([0-9]+(?:\\.[0-9]+)?)(?: m)?$",
      ),
    );
    const model = q.match(
      new RegExp(
        "^replace " +
          noun +
          " with (?:a |an )?(round|rectangular)(?: oak)?(?: coffee)? table( and (?:keep|maintain) a 90 cm (?:route|passage) from the door to the sofa)?$",
      ),
    );
    fields.route.checked = fields.route.disabled;
    if (coords) {
      fields.action.value = coords[1];
      fields.x.value = coords[2];
      fields.y.value = coords[3];
    } else if (model) {
      fields.action.value = "replace";
      fields.model.value = model[1];
      fields.route.checked = fields.route.disabled || Boolean(model[2]);
    } else if (
      new RegExp("^rotate " + noun + "(?: (?:by )?90(?: degrees|°)?)?$").test(q)
    )
      fields.action.value = "rotate";
    else if (new RegExp("^(remove|delete) " + noun + "$").test(q))
      fields.action.value = "remove";
    else {
      status.textContent =
        "Try “Move this to 2.20, 1.45”, “Rotate this 90 degrees”, or choose the edit below.";
      return;
    }
    if (fields.route.checked && selected?.room !== "salon") {
      status.textContent = "The sofa route check is available in the salon.";
      return;
    }
    refreshFields();
    dialog.querySelector("form").requestSubmit();
  };
  fields.action.onchange = refreshFields;
  dialog.querySelector("form").oninput = invalidate;
  find("[data-close]").onclick = () => {
    if (!busy) dialog.close();
  };
  dialog.oncancel = (e) => {
    if (busy) e.preventDefault();
  };
  dialog.onclose = invalidate;
  dialog.querySelector("form").onsubmit = async (e) => {
    e.preventDefault();
    if (!selected || busy) return;
    refreshFields();
    const mine = serial,
      { base, room, id, project } = selected;
    const body = { base, room, object: id, action: fields.action.value };
    if (["move", "duplicate"].includes(body.action)) {
      if (!fields.x.value || !fields.y.value) {
        status.textContent = "Enter both coordinates.";
        return;
      }
      Object.assign(body, {
        x_m: Number(fields.x.value),
        y_m: Number(fields.y.value),
      });
    }
    if (body.action === "replace") body.replacement = fields.model.value;
    if (room === "salon" && fields.route.checked) body.sofa_route = true;
    try {
      const result = await api(
        "/projects/" + project + "/furniture-edit/preview",
        body,
      );
      if (serial !== mine || !dialog.open) return;
      preview = { project, body: { ...body, preview_id: result.home.id } };
      status.textContent = result.summary;
      save.hidden = false;
    } catch (error) {
      if (serial === mine) status.textContent = error.message;
    }
  };
  save.onclick = async () => {
    if (!preview || busy) return;
    busy = true;
    const p = preview, routeLocked = fields.route.disabled;
    status.textContent = "Saving furniture edit…";
    for (const field of fields) field.disabled = true;
    try {
      const result = await api(
        "/projects/" + p.project + "/furniture-edit/apply",
        p.body,
      );
      sync(result);
      dialog.close();
    } catch (error) {
      status.textContent = error.message;
    } finally {
      busy = false;
      for (const field of fields) field.disabled = false;
      fields.route.disabled = routeLocked;
    }
  };
}
