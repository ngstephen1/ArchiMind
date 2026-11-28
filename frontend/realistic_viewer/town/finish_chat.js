import { editable, coffeeTables } from "./saved_pieces.js";
export const finishColors = {
  "dark green": "#294735",
  walnut: "#795337",
  "warm oak": "#bd9059",
  "linen white": "#ebe5d8",
  sage: "#9da98c",
  terracotta: "#b56d56",
};

export function bindFinishChat({ el, api, sync, context }) {
  const dialog = el("finishDialog"),
    room = el("finishRoom"),
    object = el("finishObject"),
    scope = el("finishScope"),
    message = el("finishMessage");
  let selection,
    pending,
    epoch = 0;
  el("world").addEventListener("room-picked", (e) => {
    if (e.detail) selection = { room: e.detail };
  });
  el("world").addEventListener("furniture-picked", (e) => {
    selection = e.detail;
  });
  function invalidate() {
    epoch++;
    pending = null;
    el("finishSave").hidden = true;
    el("finishStatus").textContent = "";
    el("finishStatus").style.removeProperty("--finish-color");
  }
  function refresh() {
    invalidate();
    const part = context().home.rooms.find(
      (p) => p.design.room.id === room.value,
    );
    const items = part?.design.furniture || [];
    const supported = part
      ? [
          ...items.filter((f) => editable(part, f)),
          ...coffeeTables(
            part,
            items.find((f) => f.id === "salon-suite"),
          ),
        ]
      : [];
    object.replaceChildren(...supported.map((f) => new Option(f.name, f.id)));
    if (
      selection?.room === room.value &&
      [...object.options].some((o) => o.value === selection.id)
    )
      object.value = selection.id;
    object.parentElement.hidden = scope.value !== "object";
    room.parentElement.hidden = scope.value === "home";
    message.placeholder =
      scope.value === "object"
        ? "Apply sage"
        : scope.value === "home"
          ? "Walnut floors throughout"
          : "Dark green walls";
  }
  el("scopeFinish").onclick = () => {
    room.replaceChildren(
      ...context().home.rooms.map(
        (p) => new Option(p.design.room.name, p.design.room.id),
      ),
    );
    if ([...room.options].some((o) => o.value === selection?.room))
      room.value = selection.room;
    scope.value = selection?.id ? "object" : "room";
    message.value = "";
    refresh();
    dialog.showModal();
  };
  room.onchange = scope.onchange = refresh;
  object.onchange = message.oninput = invalidate;
  dialog.addEventListener("close", invalidate);
  el("finishCheck").onclick = async () => {
    invalidate();
    const n = epoch,
      { project, revision } = context();
    const request = {
      base: revision,
      message: message.value,
      scope: scope.value,
      room: room.value,
      object: object.value,
    };
    try {
      const result = await api(
        "/projects/" + project + "/finish/preview",
        request,
      );
      if (n !== epoch) return;
      pending = { ...request, preview_id: result.home.id };
      el("finishStatus").textContent = result.summary;
      el("finishStatus").style.setProperty("--finish-color",finishColors[result.finish]);
      el("finishSave").hidden = false;
    } catch (e) {
      if (n === epoch) el("finishStatus").textContent = e.message;
    }
  };
  el("finishSave").onclick = async () => {
    if (!pending) return;
    el("finishSave").disabled = true;
    try {
      sync(
        await api("/projects/" + context().project + "/finish/apply", pending),
      );
      dialog.close();
    } catch (e) {
      el("finishStatus").textContent = e.message;
    } finally {
      el("finishSave").disabled = false;
    }
  };
}
