// The diagram uses Town's saved east/north dimensions in metres.
export function bindRenovation({ el, api, context, sync }) {
  const dialog = el("partitionDialog"),
    svg = el("partitionPlan");
  const ns = "http://www.w3.org/2000/svg";
  let snapshot,
    boundaries,
    chosen,
    preview,
    drag,
    pending = false;
  const room = (p) => p.design.room;
  function node(tag, attrs, parent = svg) {
    const item = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key, val]) => item.setAttribute(key, val));
    parent.append(item);
    return item;
  }
  function invalidate() {
    preview = null;
    el("savePartition").disabled = true;
    el("partitionStatus").textContent = "";
  }
  function select(i) {
    chosen = boundaries[i];
    el("partitionPair").value = String(i);
    const [south, north] = chosen;
    const key = "partition-" + room(south).id + "--" + room(north).id;
    const prior = room(south).doors.find((d) => d.id === key);
    el("partitionKind").value = snapshot.home.partitions?.[key] || "wall";
    el("partitionMove").value = 0;
    el("partitionWidth").value = prior?.width_m ?? 1;
    el("partitionOffset").value =
      prior?.offset_m ?? Math.max(0, (room(south).width_m - 1) / 2).toFixed(2);
    invalidate();
    draw();
  }
  function draw() {
    svg.replaceChildren();
    const { home } = snapshot;
    svg.setAttribute(
      "viewBox",
      [-0.3, -0.3, home.width + 0.6, home.depth + 0.6].join(" "),
    );
    for (const part of home.rooms) {
      const r = room(part),
        [x, y] = part.origin;
      const offset = Number(el("partitionMove").value) || 0;
      const isSouth = chosen?.[0] === part,
        isNorth = chosen?.[1] === part;
      const proposedDepth =
        r.depth_m + (isSouth ? offset : isNorth ? -offset : 0);
      const depth = Math.max(0, proposedDepth);
      const proposedY = y + (isNorth ? offset : 0);
      node("rect", {
        x,
        y: home.depth - proposedY - depth,
        width: r.width_m,
        height: depth,
        fill: isSouth || isNorth ? "#e4e7d9" : "#efe2d0",
        stroke: "#857864",
        "stroke-width": 0.045,
      });
      for (const f of part.design.furniture) {
        node("rect", {
          x: x + f.x_m,
          y: home.depth - y - f.y_m - f.depth_m,
          width: f.width_m,
          height: f.depth_m,
          fill: "#d7c8ad",
          "pointer-events": "none",
        });
      }
      const text = node("text", {
        x: x + r.width_m / 2,
        y: home.depth - proposedY - depth / 2,
        "text-anchor": "middle",
        "font-size": 0.44,
        fill: "#37483c",
      });
      text.textContent = r.name;
      const area = node(
        "tspan",
        { x: x + r.width_m / 2, dy: 0.49, "font-size": 0.34 },
        text,
      );
      area.textContent =
        proposedDepth > 0
          ? (r.width_m * proposedDepth).toFixed(2) + " m²"
          : "No usable depth";
    }
    boundaries.forEach(([a, b], i) => {
      const active = chosen?.[0] === a && chosen?.[1] === b;
      const y =
        home.depth -
        b.origin[1] -
        (active ? Number(el("partitionMove").value) || 0 : 0);
      const line = {
        x1: a.origin[0],
        y1: y,
        x2: a.origin[0] + room(a).width_m,
        y2: y,
      };
      node("line", {
        ...line,
        stroke: active ? "#085e53" : "#927860",
        "stroke-width": active ? 0.13 : 0.08,
      });
      const id = "partition-" + room(a).id + "--" + room(b).id;
      const door = room(a).doors.find((d) => d.id === id);
      const kind = active ? el("partitionKind").value : home.partitions?.[id];
      const offset = active
        ? Number(el("partitionOffset").value)
        : door?.offset_m;
      const width = active ? Number(el("partitionWidth").value) : door?.width_m;
      if (
        (kind === "door" || kind === "opening") &&
        Number.isFinite(offset) &&
        width > 0 &&
        offset >= 0 &&
        offset + width <= room(a).width_m
      ) {
        node("line", {
          x1: a.origin[0] + offset,
          y1: y,
          x2: a.origin[0] + offset + width,
          y2: y,
          stroke: "#fff9ef",
          "stroke-width": 0.19,
        });
        if (kind === "door") {
          node("line", {
            x1: a.origin[0] + offset,
            y1: y,
            x2: a.origin[0] + offset,
            y2: y - width,
            stroke: "#576957",
            "stroke-width": 0.045,
          });
        }
      }
      const hit = node("line", {
        ...line,
        stroke: "transparent",
        "stroke-width": 0.65,
        "data-index": i,
      });
      hit.style.cursor = "ns-resize";
    });
  }
  function pointerY(event) {
    return new DOMPoint(event.clientX, event.clientY).matrixTransform(
      svg.getScreenCTM().inverse(),
    ).y;
  }
  svg.onpointerdown = (e) => {
    if (pending || e.target.dataset.index === undefined) return;
    const i = Number(e.target.dataset.index);
    if (boundaries[i] !== chosen) select(i);
    drag = {
      id: e.pointerId,
      y: pointerY(e),
      offset: Number(el("partitionMove").value),
    };
    svg.setPointerCapture(e.pointerId);
  };
  svg.onpointermove = (e) => {
    if (!drag || drag.id !== e.pointerId) return;
    el("partitionMove").value = Math.max(
      -5,
      Math.min(5, drag.offset + drag.y - pointerY(e)),
    ).toFixed(2);
    invalidate();
    draw();
  };
  svg.onpointerup = svg.onpointercancel = () => {
    drag = null;
  };
  function busy(value) {
    pending = value;
    el("partitionFields").disabled = value;
  }
  el("renovate").onclick = () => {
    snapshot = context();
    boundaries = [];
    for (const a of snapshot.home.rooms)
      for (const b of snapshot.home.rooms) {
        if (
          Math.abs(a.origin[0] - b.origin[0]) < 0.000001 &&
          Math.abs(room(a).width_m - room(b).width_m) < 0.000001 &&
          Math.abs(a.origin[1] + room(a).depth_m - b.origin[1]) < 0.000001
        )
          boundaries.push([a, b]);
      }
    el("partitionPair").replaceChildren(
      ...boundaries.map(
        ([a, b], i) =>
          new Option(room(a).name + " / " + room(b).name, String(i)),
      ),
    );
    chosen = null;
    invalidate();
    if (boundaries.length) select(0);
    else {
      draw();
      el("partitionStatus").textContent =
        "This home has no shared full-width partitions.";
    }
    el("checkPartition").disabled = !boundaries.length;
    dialog.showModal();
  };
  el("partitionPair").onchange = (e) => select(Number(e.target.value));
  for (const id of [
    "partitionKind",
    "partitionWidth",
    "partitionMove",
    "partitionOffset",
  ])
    el(id).oninput = () => {
      invalidate();
      draw();
    };
  dialog.addEventListener("cancel", (e) => {
    if (pending) e.preventDefault();
  });
  el("closePartition").onclick = () => dialog.close();
  el("checkPartition").onclick = async () => {
    invalidate();
    busy(true);
    try {
      const body = {
        base: snapshot.revision,
        south: room(chosen[0]).id,
        north: room(chosen[1]).id,
        delta_m: Number(el("partitionMove").value),
        kind: el("partitionKind").value,
        offset_m: Number(el("partitionOffset").value),
        width_m: Number(el("partitionWidth").value),
      };
      const result = await api(
        "/projects/" + snapshot.project + "/partition/preview",
        body,
      );
      preview = { ...body, preview_id: result.home.id };
      el("savePartition").disabled = false;
      el("partitionStatus").textContent = result.summary;
    } catch (e) {
      el("partitionStatus").textContent = e.message;
    } finally {
      busy(false);
    }
  };
  el("savePartition").onclick = async () => {
    if (!preview) return;
    busy(true);
    try {
      sync(
        await api(
          "/projects/" + snapshot.project + "/partition/apply",
          preview,
        ),
      );
      dialog.close();
    } catch (e) {
      el("partitionStatus").textContent = e.message;
    } finally {
      busy(false);
    }
  };
}
