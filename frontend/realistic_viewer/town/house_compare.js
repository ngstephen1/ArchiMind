import { bedroomCameras } from "./bedroom_cameras.js";
import { homeBoard } from "./home_board.js";
import { manifestDigest } from "./bedroom_manifest.js";

const bedroom = (home) =>
  home.rooms.find((part) => part.design.room.id === "bedroom");

export function bindHouseComparison({ el, world, api, context, asset }) {
  const bookmarks = new Map();
  const dialog = el("houseCompare");
  let serial = 0,
    running = Promise.resolve(),
    objectUrl,
    openingPose,
    openingError;
  function clear() {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null;
    el("compareFrames").hidden = el("wipeControl").hidden = true;
    for (const id of ["compareRight", "compareLeft"])
      el(id).removeAttribute("src");
  }
  async function render(number, saved, kind, view) {
    const { project, revision, home } = saved;
    const current = () =>
      number === serial && dialog.open && context().home === home;
    if (!current()) return;
    const path = "/projects/" + encodeURIComponent(project);
    const capture = async (snapshot, pose) => {
      const shot = await world.bedroomViews(snapshot, pose.room || "bedroom", [
        pose,
      ]);
      return shot.images[0];
    };
    let left, right, caption;
    const savedPose = bookmarks.get(view);
    if (savedPose) {
      const hasRoom = (snapshot) =>
        snapshot.rooms.some((p) => p.design.room.id === savedPose.room);
      if (!hasRoom(home))
        throw Error("The bookmarked room is absent in this revision.");
      if (kind === "revision") {
        if (revision < 2)
          throw Error("Save an edit before comparing two revisions.");
        const before = await api(path + "?revision=" + (revision - 1));
        if (!hasRoom(before.home))
          throw Error(
            "The bookmarked room is absent in the previous revision.",
          );
        if (!current()) return;
        left = await capture(before.home, savedPose);
        if (!current()) return;
        right = await capture(home, savedPose);
        caption =
          savedPose.room + " · Revision " + before.revision + " / " + revision;
      } else {
        el("compareStatus").textContent =
          "Preparing the bookmarked Blender view…";
        const response = await asset(path + "/bookmark-photo", {
          revision,
          pose: savedPose,
        });
        if (!current()) return;
        left = await capture(home, savedPose);
        if (!current()) return;
        objectUrl = URL.createObjectURL(await response.blob());
        right = objectUrl;
        caption = savedPose.room + " · Town / Blender · Revision " + revision;
      }
    } else if (home.photo_home) {
      throw Error(
        "Enter a room in Walk and choose Bookmark this view to compare its saved camera.",
      );
    } else if (kind === "revision") {
      if (revision < 2)
        throw Error("Save a chair move first to compare two revisions.");
      const before = await api(path + "?revision=" + (revision - 1));
      if (!current()) return;
      if (
        before.project !== project ||
        before.revision !== revision - 1 ||
        !before.home ||
        !bedroom(before.home)
      )
        throw Error("The previous bedroom revision is unavailable.");
      const frame = (snapshot) => {
        const { origin, design } = bedroom(snapshot);
        return JSON.stringify([
          origin,
          design.room.width_m,
          design.room.depth_m,
          design.room.height_m,
          design.room.doors,
          design.room.windows,
        ]);
      };
      if (frame(home) !== frame(before.home))
        throw Error(
          "The bedroom shell or openings changed between revisions. Choose a pair with matching geometry.",
        );
      const pose = bedroomCameras(bedroom(home)).find((v) => v.id === view);
      left = await capture(before.home, pose);
      if (!current()) return;
      right = await capture(home, pose);
      caption =
        "Left · Revision " +
        before.revision +
        "     |     Right · Revision " +
        revision;
      if (pose.reason) caption += " · " + pose.reason;
    } else {
      const file = (name) =>
        path + "/render/hd/" + name + "?revision=" + revision;
      const receipt = await (await asset(file("eye-view-receipt.json"))).json();
      const shot = receipt.shots?.find(
        (s) => s.room === "bedroom" && s.view === view,
      );
      if (
        receipt.home_id !== home.id ||
        receipt.revision !== revision ||
        receipt.manifest_sha256 !== (await manifestDigest(homeBoard(saved))) ||
        !shot ||
        shot.file !== "bedroom-" + view + ".png" ||
        shot.architectural_projection ||
        receipt.resolution[0] * 9 !== receipt.resolution[1] * 16
      )
        throw Error(
          "The available render does not match this revision and camera.",
        );
      const blob = await (await asset(file(shot.file))).blob();
      const hash = await crypto.subtle.digest(
        "SHA-256",
        await blob.arrayBuffer(),
      );
      if (
        Array.from(new Uint8Array(hash), (n) =>
          n.toString(16).padStart(2, "0"),
        ).join("") !== shot.sha256
      )
        throw Error("Render checksum mismatch.");
      if (!current()) return;
      left = await capture(home, shot.camera);
      if (!current()) return;
      objectUrl = URL.createObjectURL(blob);
      right = objectUrl;
      caption =
        "Left · Town 3D     |     Right · Blender HD     ·     Revision " +
        revision;
    }
    if (!current()) return;
    const aspect = savedPose?.aspect || 16 / 9;
    el("compareFrames").style.aspectRatio = String(aspect);
    el("compareFrames").style.width = "min(100%, " + 66 * aspect + "vh)";
    el("compareLeft").src = left;
    el("compareRight").src = right;
    el("compareFrames").hidden = el("wipeControl").hidden = false;
    el("compareStatus").textContent = caption;
  }
  function refresh() {
    const number = ++serial,
      saved = context(),
      kind = el("compareKind").value,
      view = el("compareCamera").value;
    el("restoreRoomView").hidden = !bookmarks.has(view);
    clear();
    el("compareStatus").textContent = "Preparing matched views…";
    running = running
      .then(() => render(number, saved, kind, view))
      .catch((error) => {
        if (number === serial) el("compareStatus").textContent = error.message;
      });
  }
  function install(views) {
    const select = el("compareCamera"),
      previous = select.value;
    const imported = Boolean(context().home.photo_home);
    bookmarks.clear();
    el("compareCamera")
      .querySelectorAll("[data-bookmark]")
      .forEach((o) => o.remove());
    for (const option of select.options)
      option.disabled = option.hidden = imported;
    for (const pose of views) {
      const key = "bookmark/" + pose.room,
        opt = new Option("Saved view · " + pose.room, key);
      opt.dataset.bookmark = "true";
      el("compareCamera").add(opt);
      bookmarks.set(key, pose);
    }
    if (bookmarks.has(previous)) select.value = previous;
    else if (imported) select.value = bookmarks.keys().next().value ?? "";
  }
  el("compareHouse").onclick = async () => {
    openingPose = null;
    try {
      openingPose = world.bookmark();
    } catch (error) {
      openingError = error;
    }
    install([]);
    dialog.showModal();
    const project = context().project;
    try {
      const data = await api("/projects/" + project + "/bookmarks");
      if (!dialog.open || context().project !== project) return;
      install(data.views);
      refresh();
    } catch (error) {
      el("compareStatus").textContent = error.message;
    }
  };
  el("bookmarkView").onclick = async () => {
    try {
      const { project, revision } = context(),
        pose = openingPose;
      if (!pose) throw openingError;
      await api("/projects/" + project + "/bookmarks", { pose, revision });
      install(
        [...bookmarks.values()]
          .filter((v) => v.room !== pose.room)
          .concat(pose),
      );
      el("compareCamera").value = "bookmark/" + pose.room;
      ++serial;
      clear();
      el("compareStatus").textContent =
        "Saved this camera for " +
        pose.room +
        ". Reopen Compare after saving an edit.";
    } catch (error) {
      el("compareStatus").textContent = error.message;
    }
  };
  el("restoreRoomView").onclick = async () => {
    const pose = bookmarks.get(el("compareCamera").value);
    if (!pose) return;
    dialog.close();
    await running;
    world.restoreWalkingView(pose);
  };
  el("compareKind").onchange = el("compareCamera").onchange = refresh;
  el("compareWipe").oninput = (event) =>
    el("compareFrames").style.setProperty("--wipe", event.target.value + "%");
  const frames = el("compareFrames");
  function wipeAt(event) {
    const rect = frames.getBoundingClientRect();
    const percent = Math.max(
      0,
      Math.min(100, (100 * (event.clientX - rect.left)) / rect.width),
    );
    el("compareWipe").value = Math.round(percent);
    frames.style.setProperty("--wipe", percent + "%");
  }
  frames.onpointerdown = (event) => {
    frames.setPointerCapture(event.pointerId);
    wipeAt(event);
  };
  frames.onpointermove = (event) => {
    if (frames.hasPointerCapture(event.pointerId)) wipeAt(event);
  };
  dialog.addEventListener("close", () => {
    serial++;
    clear();
  });
}
