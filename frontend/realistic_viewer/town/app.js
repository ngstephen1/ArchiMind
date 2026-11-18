import { timeline } from "./agents.js";
import { explanation } from "./explanation.js";
import { createTown } from "./world.js";
import { homeStyle, STYLE_NAMES } from "./style_names.js";
import { planColors } from "./plan_colors.js";
import { townStyleStatus } from "./style_source.js";
import modernClassic from "../../../src/archimind/_viewer_assets/packs/modern_classic.json";
import industrialLoft from "../../../src/archimind/_viewer_assets/packs/industrial_loft.json";
import scandinavian from "../../../src/archimind/_viewer_assets/packs/scandinavian.json";
import japandi from "../../../src/archimind/_viewer_assets/packs/japandi.json";
import midCentury from "../../../src/archimind/_viewer_assets/packs/mid_century.json";
// Plan themes ship in the bundle so the 2D plan never waits on a fetch.
const PACK_MANIFESTS = Object.fromEntries(
  [modernClassic, industrialLoft, scandinavian, japandi, midCentury].map((m) => [m.id, m]),
);
import showcase from "./showcase.json";
const el = (id) => document.getElementById(id);
const cfg = await fetch("./config.json").then((r) => r.json());
const url = new URL(location.href),
  local = cfg.mode === "local";
const tourOnly = !local && !(cfg.api && cfg.editor && cfg.supabase && cfg.anon);
let project = url.searchParams.get("project"),
  revision = 0,
  applied = showcase,
  job = null,
  alternatives = [],
  selected = 0,
  chairPreview = null,
  chairEpoch = 0,
  releasedChairs = [];
const token = () => sessionStorage.getItem("town-session") || "";
const world = createTown(el("world"), el("place"), el("door"));
world.bindQuality(el("quality"));
world.bindSweep(el("sweep"));
world.load(showcase);
new MutationObserver(() => {
  el("assetStatus").hidden = el("world").dataset.desk !== "placeholder";
  el("chairStatus").hidden = el("world").dataset.chair !== "placeholder";
  const style = townStyleStatus(el("world").dataset);
  el("styleStatus").textContent = style;
  el("styleStatus").hidden = !style;
}).observe(el("world"), {
  attributes: true,
  attributeFilter: ["data-desk", "data-chair", "data-style-state", "data-style-failures", "data-style-furniture"],
});
const notify = (text) => (el("notice").textContent = text);
async function api(path, body) {
  const r = await fetch(cfg.api + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token() ? { Authorization: "Bearer " + token() } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const j = await r.json();
  if (r.status === 401) {
    sessionStorage.removeItem("town-session");
    account();
  }
  if (!r.ok) throw Error(j.error || "Service unavailable");
  return j;
}
function bind(id, fn) {
  el(id).onclick = async () => {
    try {
      await fn();
    } catch (e) {
      notify(e.message);
    }
  };
}
function links() {
  const editor = el("editor");
  if (!cfg.editor) {
    editor.hidden = true;
    return;
  }
  const target = new URL(cfg.editor);
  if (project) {
    target.searchParams.set("project", project);
    target.searchParams.set("revision", revision);
  }
  editor.href = target;
}
function resetChairPreview() {
  chairEpoch++;
  chairPreview = null;
  el("chairApply").hidden = el("chairDiscard").hidden = true;
}
function sync(data) {
  resetChairPreview();
  releasedChairs = [];
  el("chairChoice").replaceChildren();
  el("chairPicker").hidden = el("chairPreview").hidden = true;
  revision = data.revision;
  if (data.history) {
    el("briefHistory").hidden = !data.history.length;
    el("briefHistory")
      .querySelector("ol")
      .replaceChildren(
        ...data.history.map((run) => {
          const item = document.createElement("li");
          item.textContent =
            "From revision " +
            run.base +
            " · " +
            run.status +
            " · " +
            (run.message || "Measured design brief");
          return item;
        }),
      );
  }
  if (data.latest_job && data.head === data.revision && job !== data.latest_job)
    watch(data.latest_job).catch((e) => notify(e.message));
  el("revision").textContent = "Studio House · Revision " + revision;
  applied = data.home || showcase;
  el("chairStudio").hidden = revision === 0 || (data.head !== undefined && data.head !== revision);
  el("chairStudio").open = false;
  world.load(applied);
  el("width").value = applied.width;
  el("depth").value = applied.depth;
  el("style").value = homeStyle(applied);
  el("undo").hidden = revision < 2;
  el("locks").disabled = revision === 0;
  url.searchParams.set("project", project);
  url.searchParams.set("revision", revision);
  history.replaceState(null, "", url);
  links();
}
async function restore() {
  if (tourOnly) return;
  if (project && (local || token()))
    sync(
      await api(
        "/projects/" +
          encodeURIComponent(project) +
          (url.searchParams.has("revision")
            ? "?revision=" +
              encodeURIComponent(url.searchParams.get("revision"))
            : ""),
      ),
    );
}
function account() {
  if (tourOnly) {
    el("design").hidden = true;
    return;
  }
  el("account").textContent = local
    ? "Local designer · Projects saved on this computer."
    : token()
      ? "Signed in · Private design project."
      : "Tour freely. Sign in to create a private home.";
  el("auth").hidden = local || !!token();
  el("logout").hidden = local || !token();
}
for (const kind of [
  "bedroom",
  "study",
  "living",
  "kitchen-dining",
  "bathroom",
]) {
  const label = document.createElement("label"),
    box = document.createElement("input");
  box.type = "checkbox";
  box.value = kind;
  label.append(box, " " + kind);
  el("locks").append(label);
}
el("locks").disabled = true;
links();
account();
restore().catch((e) => {
  el("panel").showModal();
  notify(e.message);
});
el("tour").onclick = () => world.visit();
el("design").onclick = () => el("panel").showModal();
async function sign(up) {
  if (!cfg.supabase) throw Error("Hosted sign-in is not configured.");
  const r = await fetch(
    cfg.supabase + "/auth/v1/" + (up ? "signup" : "token?grant_type=password"),
    {
      method: "POST",
      headers: { apikey: cfg.anon, "Content-Type": "application/json" },
      body: JSON.stringify({
        email: el("email").value,
        password: el("password").value,
      }),
    },
  );
  const data = await r.json();
  el("password").value = "";
  if (!r.ok)
    throw Error(
      "Sign-in failed. Check your credentials and email confirmation.",
    );
  if (!data.access_token) {
    notify("Check your email to confirm the account, then sign in.");
    return;
  }
  sessionStorage.setItem("town-session", data.access_token);
  account();
  await restore();
  notify("Ready to design.");
}
bind("logout", async () => {
  const previous = token();
  sessionStorage.removeItem("town-session");
  job = null;
  url.searchParams.delete("project");
  url.searchParams.delete("revision");
  history.replaceState(null, "", url);
  try {
    await fetch(cfg.supabase + "/auth/v1/logout", {
      method: "POST",
      headers: { apikey: cfg.anon, Authorization: "Bearer " + previous },
    });
  } finally {
    location.replace(url);
  }
});
bind("login", () => sign(false));
bind("signup", () => sign(true));
function draw() {
  const h = alternatives[selected];
  floorPlan(h, el("plan"));
  evidence(h);
}
function floorPlan(h, c) {
  const ctx = c.getContext("2d");
  const colors = planColors(h, PACK_MANIFESTS[h.style_pack?.id] || null);
  ctx.clearRect(0, 0, c.width, c.height);
  const s = Math.min(510 / h.width, 350 / h.depth),
    ox = (c.width - h.width * s) / 2,
    oy = c.height - 20;
  ctx.fillStyle = colors.site;
  ctx.fillRect(ox, oy - s * h.depth, s * h.width, s * h.depth);
  for (const p of h.rooms) {
    const r = p.design.room,
      x = ox + s * p.origin[0],
      y = oy - s * p.origin[1],
      w = s * r.width_m,
      d = s * r.depth_m;
    ctx.fillStyle = colors.room;
    ctx.fillRect(x + 1, y - d + 1, w - 2, d - 2);
    ctx.strokeStyle = colors.wall;
    ctx.strokeRect(x, y - d, w, d);
    for (const f of p.design.furniture) {
      ctx.fillStyle = colors.furniture;
      const rect = [x + s * f.x_m, y - s * (f.y_m + f.depth_m), s * f.width_m, s * f.depth_m];
      ctx.fillRect(...rect);
      if (colors.furnitureStroke) {
        ctx.strokeStyle = colors.furnitureStroke;
        ctx.strokeRect(...rect);
      }
    }
    for (const opening of [...r.windows, ...r.doors]) {
      const xx = x + (opening.wall === "east" ? w : 0),
        yy = y - s * opening.offset_m;
      ctx.strokeStyle =
        opening.sill_height_m === undefined ? colors.door : colors.window;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(xx, yy);
      ctx.lineTo(xx, yy - s * opening.width_m);
      ctx.stroke();
      ctx.lineWidth = 1;
    }
    ctx.fillStyle = colors.label;
    ctx.font = "14px sans-serif";
    ctx.fillText(r.name, x + 6, y - d + 18);
  }
  ctx.fillText(h.width + " m", ox, oy + 16);
  ctx.fillText(h.depth + " m", 2, oy - (h.depth * s) / 2);
}
function evidence(h) {
  const e = h.evidence;
  el("evidence").textContent =
    `${e.reachable_rooms} rooms reachable after furnishing · Bedroom center ${e.bedroom_center_from_front_m} m from front · Study window ${e.study_window_width_m} m wide. Distance and window size are proxies for privacy and daylight.`;
  if (e.study_desk_window_center_distance_m) {
    const gap = e.study_desk_window_center_distance_m;
    el("evidence").textContent +=
      " Study desk center to window center in plan: " +
      gap.before.toFixed(2) +
      " → " +
      gap.after.toFixed(2) +
      " m.";
  }
  if (revision) {
    const changed = h.rooms
      .filter((p) => {
        const old = applied.rooms.find(
          (r) => r.design.room.id === p.design.room.id,
        );
        return (
          !old ||
          JSON.stringify([old.origin, old.design]) !==
            JSON.stringify([p.origin, p.design])
        );
      })
      .map((p) => p.design.room.name);
    el("evidence").textContent +=
      " Compared with revision " +
      revision +
      ": " +
      (changed.length
        ? changed.join(", ") + " changed."
        : "room geometry and furniture retained.") +
      " Style: " +
      STYLE_NAMES[homeStyle(h)] +
      ".";
  }
  Array.from(el("choices").children).forEach((b, i) =>
    b.setAttribute("aria-pressed", String(i === selected)),
  );
}
function show() {
  el("alternatives").hidden = false;
  el("choices").replaceChildren();
  alternatives.forEach((_, i) => {
    const b = document.createElement("button");
    b.textContent = "Layout " + String.fromCharCode(65 + i);
    b.onclick = () => {
      selected = i;
      draw();
    };
    el("choices").append(b);
  });
  selected = 0;
  draw();
}
bind("generate", async () => {
  resetChairPreview();
  if (!local && !cfg.supabase)
    throw Error("Public tour only. Design service is not configured.");
  if (!local && !token()) throw Error("Sign in to generate.");
  el("generate").disabled = true;
  el("alternatives").hidden = true;
  world.load(applied);
  el("revision").textContent = revision
    ? "Studio House · Revision " + revision
    : "Studio House · Showcase";
  try {
    if (!project) {
      project = (await api("/projects", {})).project;
      url.searchParams.set("project", project);
      history.replaceState(null, "", url);
      links();
    }
    const req = {
      id: crypto.randomUUID(),
      project,
      base: revision,
      message: el("message").value,
      live: el("live").checked,
      brief: {
        width: Number(el("width").value),
        depth: Number(el("depth").value),
        seed: 42 + revision,
        priority: el("priority").value,
        style: el("style").value,
        locks: [...el("locks").querySelectorAll(":checked")].map(
          (v) => v.value,
        ),
      },
    };
    const id = (await api("/jobs", req)).job;
    await watch(id);
  } finally {
    el("generate").disabled = false;
    el("cancel").hidden = true;
  }
});
let playback = 0;
function showWorkingPlan(event) {
  const h = event.artifact;
  if (event.task === "Proposed partitions") {
    const rooms = h.rooms.map(({ x, y, name, w, d }) => ({
      origin: [x, y],
      design: {
        room: { name, width_m: w, depth_m: d, doors: [], windows: [] },
        furniture: [],
      },
    }));
    floorPlan({ ...h, rooms }, el("draftPlan"));
  } else if (event.task === "Furnished candidate") {
    floorPlan(h, el("draftPlan"));
  } else return;
  el("draftFigure").hidden = false;
}
function enableReplay(events, status) {
  const button = el("replayAgents");
  button.hidden = !events.length;
  button.onclick = async () => {
    const key = ++playback;
    button.disabled = true;
    el("replayLabel").textContent = " Replaying recorded events in order";
    el("draftFigure").hidden = true;
    for (let i = 0; i < events.length; i++) {
      if (key !== playback) return;
      timeline(el("agentCards"), events.slice(0, i + 1), "replaying");
      showWorkingPlan(events[i]);
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    if (key !== playback) return;
    timeline(el("agentCards"), events, status);
    el("replayLabel").textContent = " Replay complete";
    button.disabled = false;
  };
}
async function watch(id) {
  playback++;
  el("replayLabel").textContent = "";
  el("replayAgents").hidden = true;
  el("replayAgents").disabled = false;
  job = id;
  const history = [];
  el("runStudio").hidden = false;
  el("draftFigure").hidden = true;
  el("generate").disabled = true;
  el("cancel").hidden = false;
  timeline(el("agentCards"), history, "queued");
  try {
    while (job === id) {
      const feed = await api(
        "/jobs/" + id + "/events?after=" + (history.at(-1)?.seq || 0),
      );
      if (job !== id) return;
      history.push(...feed.events);
      el("runPrompt").textContent = feed.message || "Measured design brief";
      timeline(el("agentCards"), history, feed.status);
      feed.events.forEach(showWorkingPlan);
      if (["ready", "failed", "cancelled"].includes(feed.status)) {
        const result = await api("/jobs/" + id);
        if (job !== id) return;
        enableReplay(history, feed.status);
        if (result.status === "ready") {
          alternatives = result.result;
          show();
          notify("Checks complete. Preview a layout before applying it.");
        } else notify(result.result || "Cancelled.");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 750));
    }
  } finally {
    if (job === id) {
      el("generate").disabled = false;
      el("cancel").hidden = true;
    }
  }
}
bind("cancel", async () => {
  await api("/jobs/" + job + "/cancel", {});
  el("cancel").hidden = true;
  notify("Cancelled. Your applied home is preserved.");
});
bind("visit", () => {
  resetChairPreview();
  el("revision").textContent =
    "Preview · Layout " + String.fromCharCode(65 + selected) + " · Unapplied";
  world.load(alternatives[selected]);
  world.visit();
  el("door").click();
  el("panel").close();
});
bind("apply", async () => {
  sync(await api("/jobs/" + job + "/apply", { index: selected }));
  el("alternatives").hidden = true;
  notify("Applied revision " + revision + ".");
  world.visit();
  el("door").click();
  el("panel").close();
});
bind("undo", async () => {
  sync(await api("/projects/" + project + "/undo", { base: revision }));
  el("alternatives").hidden = true;
  notify("Previous home restored as revision " + revision + ".");
});

el("chairStudio").ontoggle = async () => {
  if (!el("chairStudio").open || chairPreview || releasedChairs.length) return;
  const epoch = ++chairEpoch;
  el("chairPicker").hidden = el("chairPreview").hidden = true;
  el("chairNotice").textContent = "Checking released chairs…";
  try {
    const { chairs } = await api("/designer-chairs");
    if (epoch !== chairEpoch) return;
    releasedChairs = chairs;
    el("chairChoice").replaceChildren(
      ...chairs.map((c, i) => new Option(c.name + " · " + c.variant_label + " · " + c.version, String(i))),
    );
    el("chairPicker").hidden = el("chairPreview").hidden = !chairs.length;
    el("chairNotice").textContent = chairs.length
      ? "Preview the chair at its native size in this revision."
      : "No designer chair has been released. The bedroom uses its procedural chair.";
  } catch (e) {
    if (epoch === chairEpoch) el("chairNotice").textContent = e.message;
  }
};
function discardChair() {
  resetChairPreview();
  world.load(applied);
  el("revision").textContent = "Studio House · Revision " + revision;
  el("chairNotice").textContent = "Showing your saved bedroom.";
}
el("chairChoice").onchange = discardChair;
bind("chairDiscard", discardChair);
bind("chairPreview", async () => {
  resetChairPreview();
  const epoch = chairEpoch;
  const { concept_id, version, sha256 } = releasedChairs[Number(el("chairChoice").value)];
  const request = { base: revision, binding: { concept_id, version, sha256 } };
  const { home } = await api("/projects/" + project + "/designer-chair/preview", request);
  if (epoch !== chairEpoch) return;
  if ((await world.load(home)) !== "verified") {
    if (epoch === chairEpoch) {
      discardChair();
      el("chairNotice").textContent = "Chair preview unavailable. Your saved bedroom is still displayed.";
    }
    return;
  }
  if (epoch !== chairEpoch) return;
  chairPreview = { ...request, preview_id: home.id };
  el("chairApply").hidden = el("chairDiscard").hidden = false;
  el("chairNotice").textContent = "Bedroom preview ready. Apply to save a new revision.";
  el("revision").textContent = "Bedroom chair preview · Unsaved";
  world.visit();
  el("door").click();
  el("roomJump").value = "bedroom";
  el("roomJump").onchange();
  el("panel").close();
});
bind("chairApply", async () => {
  if (!chairPreview) return;
  sync(await api("/projects/" + project + "/designer-chair/apply", chairPreview));
  el("alternatives").hidden = true;
  notify("Designer chair saved in revision " + revision + ".");
});

let boardHome;
const node = (tag, text) =>
  Object.assign(document.createElement(tag), { textContent: text });
el("present").onclick = async () => {
  boardHome = applied;
  const h = boardHome;
  el("boardSource").textContent =
    (revision ? "Saved revision " + revision : "Packaged showcase") +
    " · " +
    h.width +
    " × " +
    h.depth +
    " m · " +
    h.id.slice(0, 12);
  el("board").showModal();
  floorPlan(h, el("boardPlan"));
  el("schedule").replaceChildren();
  el("swatches").replaceChildren();
  for (const [name, color] of [
    [
      "Bedroom plaster",
      { oak: "#e5d6bc", sage: "#bac6ad", terracotta: "#d8ab91" }[h.palette],
    ],
    ["Timber floor", null],
    ["Curtain linen", "#e9e1cd"],
    ["Brushed brass", "#9a7546"],
  ]) {
    const tile = node("div", name);
    tile.style.borderTop = "20px solid " + (color || "#ad8562");
    if (!color)
      tile.style.borderImage = "url(./assets/wood-floor.jpg) 24 round";
    el("swatches").append(tile);
  }
  for (const p of h.rooms) {
    const r = p.design.room;
    el("schedule").append(
      node(
        "h4",
        r.name +
          " · " +
          r.width_m.toFixed(2) +
          " × " +
          r.depth_m.toFixed(2) +
          " m",
      ),
    );
    for (const f of p.design.furniture)
      el("schedule").append(
        node(
          "div",
          (f.id === "desk-chair" && p.designer_chair
            ? p.designer_chair.name + (p.designer_chair.variant_label ? " · " + p.designer_chair.variant_label : "") + " · Designer concept v" + p.designer_chair.binding.version +
              " · Native " + p.designer_chair.dimensions_wdh_m.join(" × ") + " m · Reservation"
            : f.name) +
            " · " +
            [f.width_m, f.depth_m, f.height_m]
              .map((v) => v.toFixed(2))
              .join(" × ") +
            " m (W × D × H)",
        ),
      );
  }
  el("whyAnswer").textContent = "";
  el("photos").textContent = "Rendering bedroom views…";
  try {
    const { images, chair } = await world.bedroomViews(h);
    el("photos").replaceChildren();
    if (chair === "placeholder")
      el("photos").append(node("p", "Designer chair unavailable in these views. The procedural chair marks its reservation."));
    images.forEach((src, i) => {
      const fig = document.createElement("figure"),
        img = new Image();
      img.src = src;
      img.alt = i ? "Bedroom from doorway" : "Bedroom overview";
      fig.append(img, node("figcaption", img.alt + " · Eye height 1.57 m"));
      el("photos").append(fig);
    });
  } catch {
    el("photos").textContent =
      "Bedroom views could not be rendered on this device.";
  }
};
el("askWhy").onclick = () =>
  (el("whyAnswer").textContent = explanation(
    boardHome,
    el("whyQuery").value.toLowerCase(),
  ));
el("printBoard").onclick = () => window.print();

// Chromium retains modal scroll position during printing. Print a normal-flow
// copy and rasterize the plan canvas before cloning loses its drawing buffer.
window.addEventListener("beforeprint", () => {
  if (!el("board").open) return;
  document.getElementById("printSheet")?.remove();
  const sheet = document.createElement("article");
  sheet.id = "printSheet";
  const copy = el("board").cloneNode(true);
  const plan = new Image();
  plan.src = el("boardPlan").toDataURL();
  plan.alt = "Dimensioned home plan";
  copy.querySelector("canvas").replaceWith(plan);
  copy.querySelectorAll("button,input,label").forEach((n) => n.remove());
  while (copy.firstChild) sheet.appendChild(copy.firstChild);
  document.body.append(sheet);
});
window.addEventListener("afterprint", () =>
  document.getElementById("printSheet")?.remove(),
);
