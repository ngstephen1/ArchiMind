// Each doorway is recorded independently from both rooms. The server reconciles them.
export function bindPhotoHome({ el, api, local, saved, context }) {
  if (!local) return;
  const launch = el("openPhotoHome"),
    dialog = el("photoHomeDialog");
  launch.hidden = false;
  const list = el("photoHomeRooms"),
    status = el("photoHomeStatus");
  const sections = () => Array.from(list.children);
  function refreshEnds() {
    sections().forEach((section, i, all) => {
      section.querySelector(".west").hidden = i === 0;
      section.querySelector(".east").hidden = i === all.length - 1;
      section.querySelector("legend").textContent =
        "Room " + (i + 1) + " · west to east";
    });
    el("addPhotoRoom").disabled = list.children.length >= 4;
    el("removePhotoRoom").disabled = list.children.length <= 2;
    el("photoHomeConfirmed").checked = false;
  }
  function add() {
    const node =
      el("photoRoomTemplate").content.firstElementChild.cloneNode(true);
    list.append(node);
    let editVersion = 0;
    node.addEventListener("input", () => editVersion++);
    node.querySelector(".windowAdd").onclick = () => {
      const row = el("photoWindowTemplate").content.firstElementChild.cloneNode(
        true,
      );
      row.querySelector("button").onclick = () => {
        row.remove();
        el("photoHomeConfirmed").checked = false;
      };
      node.querySelector(".windows").append(row);
      el("photoHomeConfirmed").checked = false;
    };
    node.querySelector(".suggest").onclick = async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      const version = editVersion;
      try {
        const photo = await encodePhoto(node.querySelector(".file").files[0]);
        const r = await api("/photo-home-suggest", { photo, consent: true });
        if (!node.isConnected || version !== editVersion) return;
        const width = Number(node.querySelector(".width").value);
        const ratio = r.estimated_depth_to_width_ratio;
        if (width > 0 && ratio && width * ratio >= 1.5 && width * ratio <= 12)
          node.querySelector(".depth").value = (width * ratio).toFixed(2);
        node.querySelector(".uncertainty").value =
          r.observations_and_uncertainty.slice(0, 500);
        status.textContent =
          "Visual hypothesis received. " +
          (r.possible_window_wall
            ? "Possible " + r.possible_window_wall + " window. "
            : "") +
          "Check the depth and openings against your measurements.";
        el("photoHomeConfirmed").checked = false;
      } catch (e) {
        status.textContent = e.message;
      } finally {
        button.disabled = false;
      }
    };
    refreshEnds();
  }
  async function encodePhoto(file) {
    if (
      !file ||
      !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
      file.size > 8 * 1024 * 1024
    )
      throw Error("Choose one JPEG, PNG or WebP under 8 MiB for each room.");
    const bitmap = await createImageBitmap(file),
      scale = Math.min(1, 1000 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas
      .getContext("2d")
      .drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    return canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
  }
  el("addPhotoRoom").onclick = add;
  el("removePhotoRoom").onclick = () => {
    list.lastElementChild.remove();
    refreshEnds();
  };
  launch.onclick = () => {
    if (!list.children.length) {
      add();
      add();
    }
    const { project, home } = context(),
      refs = el("photoHomeSources");
    refs.replaceChildren();
    for (const s of home?.photo_home?.sources || []) {
      const p = home.rooms.find((x) => x.design.room.id === s.room);
      const fig = document.createElement("figure"),
        img = document.createElement("img"),
        cap = document.createElement("figcaption");
      img.src =
        "./api/projects/" +
        encodeURIComponent(project) +
        "/room-photo/" +
        s.photo_sha256;
      img.width = 140;
      img.alt = p.design.room.name + " source";
      cap.textContent =
        p.design.room.name +
        " · " +
        p.design.room.width_m +
        " × " +
        p.design.room.depth_m +
        " m · " +
        (s.uncertainty || "User-confirmed room geometry.");
      fig.append(img, cap);
      refs.append(fig);
    }
    dialog.showModal();
  };
  el("closePhotoHome").onclick = () => dialog.close();
  const form = el("photoHomeForm");
  form.oninput = (e) => {
    if (e.target !== el("photoHomeConfirmed"))
      el("photoHomeConfirmed").checked = false;
  };
  form.onsubmit = async (event) => {
    event.preventDefault();
    const val = (n, c) => n.querySelector(c).valueAsNumber;
    const opening = (s, c) =>
      s.querySelector(c).hidden
        ? null
        : { offset: val(s, c + " .offset"), width: val(s, c + " .clear") };
    const button = el("savePhotoHome");
    button.disabled = true;
    try {
      const snapshots = sections().map((s) => ({
        name: s.querySelector(".name").value,
        file: s.querySelector(".file").files[0],
        width: val(s, ".width"),
        depth: val(s, ".depth"),
        ceiling_height: val(s, ".height"),
        west: opening(s, ".west"),
        east: opening(s, ".east"),
        uncertainty: s.querySelector(".uncertainty").value,
        windows: Array.from(s.querySelector(".windows").children, (r) => ({
          wall: r.querySelector("select").value,
          offset: val(r, ".offset"),
          width: val(r, ".width"),
          height: val(r, ".height"),
          sill: val(r, ".sill"),
        })),
      }));
      const entry = {
        width: val(form, "#entryWidth"),
        offset: val(form, "#entryOffset"),
      };
      const confirmed = el("photoHomeConfirmed").checked;
      const rooms = await Promise.all(
        snapshots.map(async ({ file, ...room }) => ({
          ...room,
          photo: await encodePhoto(file),
        })),
      );
      const result = await api("/photo-home", { rooms, entry, confirmed });
      saved(result);
      dialog.close();
      list.replaceChildren();
      form.reset();
      status.textContent = "";
    } catch (e) {
      status.textContent = e.message;
    } finally {
      button.disabled = false;
    }
  };
}
