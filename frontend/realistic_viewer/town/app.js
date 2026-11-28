import { competingGoals } from "./tradeoff.js";
import studioShowcasePublications from "./studio_publications.json";
import conferencePublications from "./conference_publications.json";
import {homeBoard} from "./home_board.js";
import {roomElevation} from "./elevations.js";
import { bedroomManifest, manifestText, manifestDigest, publicationFor } from "./bedroom_manifest.js";
import { floorPlan } from "./floor_plan.js";
import { timeline } from "./agents.js";
import { asksChairChange, asksZoningTradeoff, explanation, isSavedDesignQuestion, isUnambiguousSavedDesignQuestion } from "./explanation.js";
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
  reviewedMessage = "",
  alternatives = [],
  selected = 0,
  chairPreview = null,
  chairEpoch = 0,
  loadingChairScene = false,
  releasedChairs = [];
const token = () => sessionStorage.getItem("town-session") || "";
const world = createTown(el("world"), el("place"), el("door"));
world.bindQuality(el("quality"));
world.bindSweep(el("sweep"));
world.load(showcase);
new MutationObserver(() => {
  el("assetStatus").hidden = el("world").dataset.desk !== "placeholder";
  el("collectionStatus").hidden = el("world").dataset.collection !== "placeholder";
  el("chairStatus").hidden = el("world").dataset.chair !== "placeholder";
  const style = townStyleStatus(el("world").dataset);
  el("styleStatus").textContent = style;
  el("styleStatus").hidden = !style;
}).observe(el("world"), {
  attributes: true,
  attributeFilter: ["data-desk", "data-chair", "data-collection", "data-style-state", "data-style-failures", "data-style-furniture"],
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
  loadingChairScene = false;
  chairPreview = null;
  el("chairApply").hidden = el("chairDiscard").hidden = true;
}
function loadSavedHome() {
  world.load(applied);
  el("tour").textContent = revision ? "Visit saved home" : "Visit showcase";
}
const reviewContext = () => ({ project, revision, home_id: applied.id });
function isCurrentReview(context) {
  return context.project === project && context.revision === revision && context.home_id === applied.id;
}
let reviewModes = {}, routeSerial = 0;
function clearRouteReview() {
  routeSerial++;
  el("requestReviewStatus").textContent = "";
  el("openSavedAnswer").hidden = true;
  el("checkRequest").disabled = false;
}
async function refreshDecisionReviews() {
  const context = reviewContext();
  reviewModes = {};
  clearRouteReview();
  clearEvidenceReview();
  el("checkRequest").hidden = el("requestReview").hidden = true;
  if (!context.project || !context.revision) return;
  try {
    const modes = await api("/projects/" + encodeURIComponent(context.project) + "/decision-review");
    if (!isCurrentReview(context)) return;
    reviewModes = modes;
    el("checkRequest").hidden = el("requestReview").hidden = modes.route === "off";
  } catch { /* The rest of Town works when optional checks are unavailable. */ }
}
function requestDecisionReview(kind, context, message, claims = []) {
  return api("/projects/" + encodeURIComponent(context.project) + "/decision-review", {
    id: crypto.randomUUID(), kind, revision: context.revision, home_id: context.home_id,
    message, claims, allow_live: true,
  });
}
function reviewStatus(result) {
  if (result.status === "unavailable") {
    if (result.reason === "budget") return "The optional review allowance is used. Your saved design and normal tools are still available.";
    return "Review unavailable. Your saved design is unchanged.";
  }
  if (result.mode === "shadow") return "Calibration check recorded. Advice is unavailable in this mode.";
  if (!Object.keys(result.suggestions || {}).length)
    return "No suggestion met the evidence or confidence threshold. Your saved design is unchanged.";
  return "";
}
el("message").addEventListener("input", clearRouteReview);
el("panel").addEventListener("close", clearRouteReview);
bind("checkRequest", async () => {
  const context = reviewContext(), message = el("message").value.trim();
  const status = el("requestReviewStatus"), serial = ++routeSerial;
  el("openSavedAnswer").hidden = true;
  if (!message) {
    status.textContent = "Enter a request to check.";
    return;
  }
  function offerSavedAnswer(compare = false) {
    el("openSavedAnswer").hidden = false;
    el("openSavedAnswer").onclick = async () => {
      if (serial !== routeSerial || !isCurrentReview(context)) return;
      el("panel").close();
      await askSavedDesign(message, { compare });
    };
  }
  if (isUnambiguousSavedDesignQuestion(message)) {
    status.textContent = "This is a question about a saved design.";
    offerSavedAnswer();
    return;
  }
  const current = () => serial === routeSerial && isCurrentReview(context) && el("panel").open;
  el("checkRequest").disabled = true;
  status.textContent = "Checking the request…";
  try {
    const result = await requestDecisionReview("route", context, message);
    if (!current()) return;
    const label = result.suggestions?.intent;
    status.textContent = reviewStatus(result) || ({
      answer: "Suggested next step: open the saved-design explanation.",
      compare: "Suggested next step: compare the saved revisions.",
      edit: "Suggested next step: revise the existing design. Review the brief before choosing Generate layouts.",
      new: "Suggested next step: start a new design.",
      clarify: "Suggested next step: say whether you want an explanation, an edit, or a new design.",
    })[label];
    if (label === "answer" || label === "compare") offerSavedAnswer(label === "compare");
  } catch {
    if (current()) status.textContent = "Review unavailable. Your saved design is unchanged.";
  } finally {
    if (current()) el("checkRequest").disabled = false;
  }
});
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
  loadSavedHome();
  el("width").value = applied.width;
  el("depth").value = applied.depth;
  el("style").value = homeStyle(applied);
  el("formalSalon").checked = applied.rooms.some(part => part.design.room.id === "salon");
  const requirements = applied.evidence?.comparison;
  el("diningSeats").value = requirements?.required_dining_seats ?? 0;
  el("splitDining").checked = requirements?.split_dining ?? false;
  el("serviceLayout").checked = Boolean(applied.service_layout);
  el("serviceLayout").disabled = Boolean(applied.service_layout);
  el("compareZoning").checked = false;
  el("passage").value = requirements?.passage_m ?? 0.6;
  el("undo").hidden = revision < 2;
  el("locks").disabled = revision === 0;
  url.searchParams.set("project", project);
  url.searchParams.set("revision", revision);
  history.replaceState(null, "", url);
  links();
  void refreshDecisionReviews();
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
  planOf(h, el("plan"));
  evidence(h);
  showComparison();
}
function planOf(h, c) {
  floorPlan(h, c, planColors(h, PACK_MANIFESTS[h.style_pack?.id] || null));
}
function evidence(h) {
  const e = h.evidence;
  el("evidence").textContent =
    `${e.reachable_rooms} rooms reachable after furnishing · Bedroom center ${e.bedroom_center_from_front_m} m from front · Study window ${e.study_window_width_m} m wide. Distance and window size are proxies for privacy and daylight.`;
  if (e.room_preferences?.length) {
    const measures = e.room_preferences.map(g =>
      `${g.room} ${g.relation === "near" ? "near" : "away from"} ${g.target}: ${g.center_distance_m.toFixed(2)} m`);
    el("evidence").textContent += " Room-center distances in plan · " + measures.join(" · ") +
      ". These preferences rank validated layouts. They do not measure walking routes or sound levels.";
  }
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
function showComparison() {
  const area = el("comparisonMeasures");
  area.replaceChildren();
  for (const [index, home] of alternatives.entries()) {
    const measure = home.evidence.comparison;
    if (!measure) continue;
    const zoning = {gallery: "Gallery", "service-core": "Grouped service core"}[home.zoning];
    area.append(node("h4", "Layout " + String.fromCharCode(65 + index) + (zoning ? " · " + zoning : "")));
    const list = node("ul", "");
    for (const route of measure.routes)
      list.append(node("li", `${route.room} to ${route.target} via hall · ${route.distance_m.toFixed(2)} m`));
    for (const [room, count] of Object.entries(measure.dining_places))
      list.append(node("li", `${room} · ${count} seats at one table`));
    if (measure.direct_service)
      list.append(node("li", `Kitchen and salon share a direct passage · ${measure.direct_service.crossing_m.toFixed(2)} m checked crossing`));
    else if (zoning)
      list.append(node("li", "Kitchen and salon connect through the gallery hall."));
    for (const [room, area] of Object.entries(measure.room_areas_m2 ?? {}))
      list.append(node("li", `${room} · ${area.toFixed(1)} m²`));
    for (const item of measure.wardrobes ?? [])
      list.append(node("li", `${item.room} ${item.id} · ${item.width_m.toFixed(2)} × ${item.depth_m.toFixed(2)} m reservation`));
    const opening = Math.min(...Object.values(measure.modeled_openings_m));
    list.append(node("li", `Narrowest modeled doorway ${opening.toFixed(2)} m · checked passage ${measure.passage_m.toFixed(2)} m`));
    for (const [room, service] of Object.entries(measure.service_rooms ?? {})) {
      const fixtures = service.operating_zones.map(zone =>
        `${zone.fixture_id} ${zone.working_depth_m.toFixed(2)} m working depth`
      );
      list.append(node("li", `${room} · ${fixtures.join(", ")} · Connections need field verification`));
    }
    area.append(list);
  }
  if (area.children.length)
    area.append(node("p", "Routes run between points inside the doorways. Check clear opening and door hardware on site."));
  const items = node("details", "");
  items.append(node("summary", "Selected furniture reservations"));
  const list = node("ul", "");
  for (const { design } of alternatives[selected].rooms)
    for (const f of design.furniture)
      list.append(node("li", `${design.room.name} · ${f.name} · ${f.width_m.toFixed(2)} × ${f.depth_m.toFixed(2)} m`));
  items.append(list);
  area.append(items);
}
function showBrief(summary) {
  const panel = el("reviewBrief");
  panel.hidden = false;
  panel.replaceChildren(node("h3", "Review the design brief"));
  const states = {
    confirmed: "Hard requirements confirmed. Layouts are generated from this brief.",
    "needs confirmation": "Needs your confirmation. No layout was generated and your saved home is unchanged.",
    unsupported: "Includes an unsupported requirement. No layout was generated and your saved home is unchanged.",
  };
  if (states[summary.status]) panel.append(node("p", states[summary.status]));
  const origins = {
    brief: "From your brief", controls: "From the brief controls",
    "saved revision": "Carried from the saved revision", interpreted: "Interpreted from your request",
    default: "Town default",
  };
  const sources = new Map((summary.sources || []).map(s => [s.requirement, s]));
  for (const [title, values] of [
    ["Hard requirements", summary.requirements], ["Preferences", summary.preferences],
    ["Assumptions", summary.assumptions || []],
    ["Presentation requests", summary.presentation_requests || []],
    ["Questions", summary.questions], ["Unsupported requirements", summary.unsupported],
  ]) {
    if (!values.length) continue;
    panel.append(node("h4", title));
    const list = node("ul", "");
    for (const value of values) {
      const item = node("li", value);
      const source = sources.get(value);
      if (title === "Hard requirements" && source) {
        const cite = node("small", " · " + (origins[source.origin] || source.origin) +
          (source.statement ? `: “${source.statement}”` : ""));
        item.append(cite);
      }
      list.append(item);
    }
    panel.append(list);
  }
}

function showTradeoff() {
  const goals = competingGoals(alternatives);
  el("tradeoff").hidden = goals.length === 0;
  const select = el("tradeoffGoal");
  select.replaceChildren(new Option("Balance all preferences", ""));
  el("recommendation").textContent = "";
  select.onchange = null;
  if (!goals.length) return;
  for (const [index, goal] of goals.entries()) {
    const verb = goal.relation === "near" ? "Bring closer together" : "Put farther apart";
    select.add(new Option(`${verb} — ${goal.room} and ${goal.target}`, String(index)));
  }
  function recommend() {
    const goal = select.value === "" ? null : goals[Number(select.value)];
    selected = goal?.winner ?? 0;
    el("recommendation").textContent = goal
      ? `Prioritizing this goal ${selected ? "changes the recommendation from A to B" : "keeps A as the recommendation"}. Room centers: A ${goal.distances[0].toFixed(3)} m, B ${goal.distances[1].toFixed(3)} m.`
      : "Layout A is recommended with all preferences weighted equally.";
    draw();
  }
  select.onchange = recommend;
  el("recommendation").textContent = "Layout A is recommended with all preferences weighted equally.";
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
  showTradeoff();
  draw();
}
bind("generate", async () => {
  const question = el("message").value.trim();
  if (revision && isSavedDesignQuestion(question)) {
    el("panel").close();
    await askSavedDesign(question);
    return;
  }
  if (!el("diningSeats").reportValidity() || !el("passage").reportValidity()) return;
  el("reviewBrief").hidden = true;
  resetChairPreview();
  if (!local && !cfg.supabase)
    throw Error("Public tour only. Design service is not configured.");
  if (!local && !token()) throw Error("Sign in to generate.");
  el("generate").disabled = true;
  el("alternatives").hidden = true;
  loadSavedHome();
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
      live: true,
      agent_team: true,
      brief: {
        width: Number(el("width").value),
        depth: Number(el("depth").value),
        seed: 42 + revision,
        priority: el("priority").value,
        style: el("style").value,
        formal_salon: el("formalSalon").checked,
        compare_tradeoffs: true,
        ...(revision || Number(el("diningSeats").value) > 0 ? { dining_seats: Number(el("diningSeats").value) } : {}),
        split_dining: el("splitDining").checked,
        service_layout: el("serviceLayout").checked,
        compare_zoning: el("compareZoning").checked,
        ...(revision || Number(el("passage").value) !== 0.6 ? { passage_m: Number(el("passage").value) } : {}),
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
    planOf({ ...h, rooms }, el("draftPlan"));
  } else if (event.task === "Furnished candidate") {
    planOf(h, el("draftPlan"));
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
      for (const event of feed.events) {
        if (event.task === "Reviewable brief") showBrief(event.artifact);
        showWorkingPlan(event);
      }
      if (["ready", "failed", "cancelled"].includes(feed.status)) {
        const result = await api("/jobs/" + id);
        if (job !== id) return;
        enableReplay(history, feed.status);
        if (result.status === "ready") {
          alternatives = result.result;
          reviewedMessage = feed.message;
          show();
          const missingCritique = history.some(e => e.task === "OpenAI · Review plan images" && e.state === "failed");
          notify(missingCritique
            ? "Spatial checks passed. AI visual review unavailable. Preview a layout before applying it."
            : "Checks complete. Preview a layout before applying it.");
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
  el("tour").textContent = "Visit preview";
  world.load(alternatives[selected]);
  world.visit();
  el("door").click();
  el("panel").close();
});
bind("apply", async () => {
  const followup = reviewedMessage.match(/\b(why|explain)\b[^.!?]*/i)?.[0];
  sync(await api("/jobs/" + job + "/apply", { index: selected }));
  el("alternatives").hidden = true;
  notify("Applied revision " + revision + ".");
  world.visit();
  el("door").click();
  el("panel").close();
  if (followup) await askSavedDesign(followup);
});
async function askSavedDesign(question, options) {
  await el("present").onclick();
  el("whyQuery").value = question;
  await explainSavedQuestion(options);
}
bind("undo", async () => {
  sync(await api("/projects/" + project + "/undo", { base: revision }));
  el("alternatives").hidden = true;
  notify("Previous home restored as revision " + revision + ".");
});

el("chairStudio").ontoggle = async () => {
  if (!el("chairStudio").open || chairPreview || releasedChairs.length) return;
  const savedHome = applied;
  el("chairPicker").hidden = el("chairPreview").hidden = true;
  el("chairNotice").textContent = "Checking released furniture…";
  try {
    const [{ chairs }, { concepts }] = await Promise.all([api("/designer-chairs"),api("/bedroom-collection")]);
    if (savedHome !== applied) return;
    releasedChairs = [...chairs, ...concepts];
    el("chairChoice").replaceChildren(
      ...releasedChairs.map((c, i) => new Option([c.name,c.variant_label,c.version].filter(Boolean).join(" · "), String(i))),
    );
    el("chairPicker").hidden = el("chairPreview").hidden = !releasedChairs.length;
    if (!chairPreview) el("chairNotice").textContent = releasedChairs.length
      ? "Preview a piece at its native size in this revision."
      : "No released furniture is available.";
  } catch (e) {
    if (savedHome === applied && !chairPreview) el("chairNotice").textContent = e.message;
  }
};
function discardChair() {
  resetChairPreview();
  loadSavedHome();
  el("revision").textContent = "Studio House · Revision " + revision;
  el("chairNotice").textContent = "Showing your saved bedroom.";
}
el("chairChoice").onchange = discardChair;
bind("chairDiscard", discardChair);
bind("chairPreview", async () => {
  const { concept_id, version, sha256 } = releasedChairs[Number(el("chairChoice").value)];
  const request = { base: revision, binding: { concept_id, version, sha256 } };
  const endpoint = concept_id === "oak-sage-writing-chair" ? "designer-chair" : "bedroom-collection";
  await previewBedroomEdit(endpoint, request);
});
bind("chairPullout", () => previewBedroomEdit("chair-pullout", {base: revision}));
async function previewBedroomEdit(endpoint, request) {
  const epoch = ++chairEpoch;
  let home, status;
  try {
    ({home} = await api("/projects/" + project + "/" + endpoint + "/preview", request));
    if (epoch !== chairEpoch) return;
    loadingChairScene = true;
    chairPreview = null;
    el("chairApply").hidden = el("chairDiscard").hidden = true;
    status = await world.load(home);
  } catch (error) {
    if (epoch === chairEpoch) {
      // A refused request leaves the current room, camera and accepted preview intact.
      if (loadingChairScene) discardChair();
      throw error;
    }
    return;
  }
  const proceduralMove = endpoint === "chair-pullout" && status === "procedural";
  if (status !== "verified" && !proceduralMove) {
    if (epoch === chairEpoch) {
      discardChair();
      el("chairNotice").textContent = "Furniture preview unavailable. Your saved bedroom is still displayed.";
    }
    return;
  }
  if (epoch !== chairEpoch) return;
  loadingChairScene = false;
  chairPreview = {endpoint, request: { ...request, preview_id: home.id }};
  el("tour").textContent = "Visit preview";
  el("chairApply").hidden = el("chairDiscard").hidden = false;
  el("chairNotice").textContent = "Bedroom preview ready. Apply to save a new revision.";
  el("revision").textContent = "Bedroom furniture preview · Unsaved";
  world.visit();
  el("door").click();
  el("roomJump").value = "bedroom";
  el("roomJump").onchange();
  el("panel").close();
}
bind("chairApply", async () => {
  if (!chairPreview) return;
  const editingPosition = chairPreview.endpoint === "chair-pullout";
  sync(await api("/projects/" + project + "/"+chairPreview.endpoint+"/apply", chairPreview.request));
  el("alternatives").hidden = true;
  notify((editingPosition ? "Chair position" : "Designer furniture") + " saved in revision " + revision + ".");
});

let boardHome;
let evidenceManifest;
let exportUrl, homeUrl;

function showExport(manifest, hash, studio, studioHash) {
  if (exportUrl) URL.revokeObjectURL(exportUrl);
  exportUrl = URL.createObjectURL(new Blob([manifestText(manifest)], {type:"application/json"}));
  const manifestLink = node("a","Download bedroom manifest");
  manifestLink.href = exportUrl;
  manifestLink.download = "bedroom-r" + manifest.revision + "-" + hash.slice(0,12) + ".json";
  if(homeUrl) URL.revokeObjectURL(homeUrl);
  homeUrl=URL.createObjectURL(new Blob([manifestText(studio)],{type:"application/json"}));
  const whole=node("a","Download whole-home scene manifest");
  whole.href=homeUrl; whole.download="home-r"+revision+"-"+boardHome.id.slice(0,12)+".json";
  el("boardExports").replaceChildren(manifestLink, node("p",""),whole);
  if (boardHome.service_layout) {
    const section = node("div", "");
    const button = node("button", "Prepare kitchen and bathroom drawings");
    button.type = "button";
    const selectedHomeId = boardHome.id;
    button.onclick = async () => {
      button.disabled = true;
      try {
        const study = await api("/projects/" + encodeURIComponent(manifest.project) +
          "/service-study?revision=" + manifest.revision);
        if (study.home_id !== selectedHomeId) throw Error("The drawings did not match this revision.");
        const list = node("ul", "");
        for (const [file, svg] of Object.entries(study.drawings)) {
          const link = node("a", file);
          link.href = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
          link.download = "r" + manifest.revision + "-" + file;
          const row = node("li", "");
          row.append(link);
          list.append(row);
        }
        section.replaceChildren(list);
      } catch (error) {
        button.disabled = false;
        section.replaceChildren(button, node("p", error.message));
      }
    };
    section.append(button);
    el("boardExports").append(section);
  }
  const studioRelease = publicationFor(studio, studioHash, [...studioShowcasePublications, ...conferencePublications]);
  let downloadLabel = "Jump to downloads";
  if (studioRelease?.kind === "rehearsal-package") {
    downloadLabel = "Jump to rehearsal package";
    const pack = node("a", "Download the revision " + studio.revision + " rehearsal package (ZIP)");
    pack.id = "studioBookLink";
    pack.href = studioRelease.url;
    pack.target = "_blank";
    pack.rel = "noopener";
    el("boardExports").append(node("p", ""), pack, node("p",
      "Open Client-Book.pdf inside the ZIP. The editable files are in Designer-Handoff.zip. Sign in to GitHub before downloading. GitHub shows a 404 when signed out."
    ));
  } else if (studioRelease) {
    downloadLabel = "Jump to client book";
    const pdf = node("a", "Open the whole-home client book (PDF)");
    pdf.id = "studioBookLink";
    pdf.href = studioRelease.pdf;
    pdf.target = "_blank";
    pdf.rel = "noopener";
    const pack = node("a", "Download the editable scene, images and camera studies");
    pack.href = studioRelease.url;
    el("boardExports").append(node("p",""), pdf, node("p",""), pack);
  }
  el("jumpDownloads").textContent = downloadLabel;
  el("jumpDownloads").hidden = false;
  const publication = publicationFor(manifest,hash);
  if (publication) {
    const link = node("a","Download the Blender scene and three finished stills");
    link.href = publication.url;
    el("boardExports").append(node("p",""),link);
  } else if (!studioRelease) {
    el("boardExports").append(node("p","Offline renders have not been published for this exact revision."));
  }
}

const node = (tag, text) =>
  Object.assign(document.createElement(tag), { textContent: text });
el("jumpQuestion").onclick = () => el("whyQuery").focus();
el("jumpDownloads").onclick = () => {
  const target = el("studioBookLink") || el("boardExports").querySelector("a");
  target?.focus();
};
let renderWatch = 0;
function renderEndpoint() {
  return "/projects/" + encodeURIComponent(project) + "/render";
}
function watchRender() {
  const epoch = ++renderWatch;
  const panel = el("renderPanel");
  panel.hidden = !local || !revision;
  if (panel.hidden) return;
  const endpoint = renderEndpoint();
  const query = "?revision=" + revision;
  const statusText = el("renderStatus");
  el("renderDownloads").replaceChildren();
  el("renderHD").hidden = true;
  el("renderProof").disabled = false;
  statusText.textContent = "Checking the local rendering service.";
  async function poll() {
    try {
      const values = await api(endpoint + query);
      if (epoch !== renderWatch || !el("board").open) return;
      const { proof, hd } = values;
      el("renderProof").disabled = ["queued", "running", "ready"].includes(proof.state);
      el("renderHD").hidden = proof.state !== "ready";
      el("renderHD").disabled = ["queued", "running", "ready", "blocked"].includes(hd.state);
      statusText.textContent = hd.phase || proof.phase || "Ready to queue a proof.";
      el("renderDownloads").replaceChildren();
      for (const stage of ["proof", "hd"]) {
        for (const name of Object.keys(values[stage].files || {})) {
          const link = node("a", `${stage === "proof" ? "Proof" : "HD"} · ${name}`);
          link.href = cfg.api + endpoint + "/" + stage + "/" + encodeURIComponent(name) + query;
          link.download = name;
          el("renderDownloads").append(link, document.createElement("br"));
        }
      }
      if ([proof.state, hd.state].some(s => ["queued", "running"].includes(s))) setTimeout(poll, 1600);
    } catch (error) {
      if (epoch !== renderWatch || !el("board").open) return;
      statusText.textContent = error.message;
      el("renderProof").disabled = true;
    }
  }
  for (const [id, stage] of [["renderProof", "proof"], ["renderHD", "hd"]]) {
    el(id).onclick = async () => {
      try {
        el(id).disabled = true;
        await api(endpoint + query, { stage });
        if (epoch === renderWatch) await poll();
      } catch (error) {
        if (epoch === renderWatch) {
          statusText.textContent = error.message;
          el(id).disabled = false;
        }
      }
    };
  }
  void poll();
}
let boardGeneration = 0;
el("present").onclick = async () => {
  el("jumpDownloads").hidden = true;
  const generation = ++boardGeneration;
  el("printBoard").disabled = true;
  boardHome = applied;
  evidenceManifest = null;
  clearEvidenceReview();
  el("whyAnswer").textContent = "";
  el("boardExports").replaceChildren();
  if (revision) {
    try {
      const manifest = bedroomManifest({project, revision, home: boardHome});
      evidenceManifest = manifest;
      const studio = homeBoard({project, revision, home: boardHome});
      Promise.all([manifestDigest(manifest), manifestDigest(studio)]).then(([hash, studioHash]) => {
        if (generation === boardGeneration) showExport(manifest, hash, studio, studioHash);
      }).catch(() => { if (generation === boardGeneration) el("boardExports").textContent = "Revision export unavailable."; });
    } catch { el("boardExports").textContent = "Revision export unavailable."; }
  }
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
  watchRender();
  planOf(h, el("boardPlan"));
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
            : p.designer_collection?.[f.id]?.name || f.name) +
            " · " +
            [f.width_m, f.depth_m, f.height_m]
              .map((v) => v.toFixed(2))
              .join(" × ") +
            ` m (W × D × H) · Room position (${f.x_m.toFixed(2)}, ${f.y_m.toFixed(2)}) m`,
        ),
      );
  }
  el("boardRoom").replaceChildren(...h.rooms.map(p=>new Option(p.design.room.name,p.design.room.id)));
  el("boardRoom").value="bedroom";
  await showRoom(h,"bedroom");
};
el("boardRoom").onchange=()=>showRoom(boardHome,el("boardRoom").value);
let photoSerial=0;
async function showRoom(h,id){
  const generation=++photoSerial;
  const part=h.rooms.find(p=>p.design.room.id===id);
  el("elevations").replaceChildren(node("h3",part.design.room.name+" · schematic elevations"),roomElevation(part,"north"),roomElevation(part,"east"));
  el("printBoard").disabled=true;
  el("whyAnswer").textContent = "";
  questionSerial++;
  clearEvidenceReview();
  el("photos").textContent = "Rendering "+part.design.room.name+" views…";
  try {
    const { images, views, chair, desk, collection } = await world.bedroomViews(h,id);
    if (photoSerial !== generation || !el("board").open) return;
    el("photos").replaceChildren();
    if (id==="bedroom" && desk === "placeholder") el("photos").append(node("p", "Belaya mesh unavailable. A placeholder marks its reservation."));
    if (id==="bedroom" && collection === "placeholder") el("photos").append(node("p","Bedroom collection mesh unavailable. A procedural piece marks its reservation."));
    if (id==="bedroom" && chair === "placeholder")
      el("photos").append(node("p", "Designer chair unavailable in these views. The procedural chair marks its reservation."));
    images.forEach((src, i) => {
      const fig = document.createElement("figure"),
        img = new Image();
      img.src = src;
      img.alt = views[i].reason ? "Doorway overview" : views[i].label;
      fig.append(img, node("figcaption", views[i].label + " · " + (views[i].reason || "Eye height 1.57 m")));
      el("photos").append(fig);
    });
  } catch {
    if (photoSerial !== generation || !el("board").open) return;
    el("photos").textContent =
      "Room views could not be rendered on this device.";
  } finally {
    if (generation === photoSerial) el("printBoard").disabled = false;
  }
};
let questionSerial = 0, evidenceSerial = 0, renderedAnswer = null;
function clearEvidenceReview() {
  evidenceSerial++;
  renderedAnswer = null;
  el("evidenceReview").hidden = true;
  el("checkEvidence").disabled = false;
  el("evidenceReviewStatus").textContent = "";
  el("evidenceReviewItems").replaceChildren();
}
el("board").addEventListener("close", clearEvidenceReview);
el("whyQuery").addEventListener("input", () => {
  questionSerial++;
  clearEvidenceReview();
});
bind("checkEvidence", async () => {
  const saved = renderedAnswer;
  if (!saved) return;
  const serial = ++evidenceSerial;
  const current = () => serial === evidenceSerial && el("board").open && isCurrentReview(saved.context);
  const items = el("evidenceReviewItems"), status = el("evidenceReviewStatus");
  const labels = {
    supported: "Supported by the supplied facts",
    missing_evidence: "Evidence is missing",
    contradicted: "Conflicts with a supplied fact",
  };
  const claims = saved.answer.split(/(?<=[.?!])\s+(?=[A-Z])/).filter(Boolean).slice(0, 6);
  el("checkEvidence").disabled = true;
  status.textContent = "Checking the answer against the saved revision…";
  items.replaceChildren();
  try {
    const result = await requestDecisionReview("evidence", saved.context, saved.question, claims);
    if (!current()) return;
    status.textContent = reviewStatus(result) || "Advisory checks for the saved revision";
    if (Object.keys(result.suggestions || {}).length)
      items.replaceChildren(...claims.map((claim, index) =>
        node("li", (labels[result.suggestions["claim_" + index]] || "No reliable finding") + " — " + claim)));
  } catch {
    if (current()) status.textContent = "Review unavailable. The displayed explanation is unchanged.";
  } finally {
    if (current()) el("checkEvidence").disabled = false;
  }
});
async function explainSavedQuestion({ compare = false } = {}) {
  const serial = ++questionSerial, generation = boardGeneration;
  clearEvidenceReview();
  const question = el("whyQuery").value.trim(), manifest = evidenceManifest;
  const context = reviewContext();
  if (compare && !asksChairChange(question)) {
    el("whyAnswer").textContent = "Revision comparisons currently cover the bedroom desk chair. Ask how its position or gap to the desk changed.";
    return;
  }
  let previous = null;
  if ((asksChairChange(question) || asksZoningTradeoff(question)) && manifest?.revision > 1) {
    el("whyAnswer").textContent = "Checking the previous saved revision…";
    try {
      previous = await api("/projects/" + encodeURIComponent(manifest.project) + "?revision=" + (manifest.revision - 1));
    } catch { /* The explanation identifies the missing revision. */ }
  }
  if (serial !== questionSerial || generation !== boardGeneration || !el("board").open || !isCurrentReview(context)) return;
  const answer = explanation(boardHome, question, manifest, previous);
  const source = evidenceManifest ? `Project ${evidenceManifest.project} · Revision ${evidenceManifest.revision}` : "Bedroom preview";
  el("whyAnswer").textContent = `${source} · ${answer}`;
  if (question && manifest && reviewModes.evidence && reviewModes.evidence !== "off") {
    renderedAnswer = { answer, question, context };
    el("evidenceReview").hidden = false;
  }
}
el("askWhy").onclick = () => explainSavedQuestion();
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
  copy.querySelectorAll("button,input,label,#boardExports").forEach((n) => n.remove());
  while (copy.firstChild) sheet.appendChild(copy.firstChild);
  document.body.append(sheet);
});
window.addEventListener("afterprint", () =>
  document.getElementById("printSheet")?.remove(),
);
