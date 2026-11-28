import { bedroomCameras } from "./bedroom_cameras.js";

import recordedLayout from "./photo-study/studio-layout.json";
import { openLayout } from "./photo_layout.js";

const looks = {
  "Warm oak":
    "Keep the layout and furniture positions. Use white oak, oatmeal linen, aged brass and soft afternoon light.",
  "Soft Japandi":
    "Give this room a restrained Japandi finish with warm plaster, pale timber and woven textures. Keep the openings and furniture layout.",
  "Evening light":
    "Show this room in the evening. Layer warm task and reading lights, retain the furniture and keep the window visible.",
};

async function frameImage(url) {
  const image = new Image();
  image.src = url;
  await image.decode();
  const aspect = image.width / image.height;
  const target =
    aspect > 1.22 ? [1536, 1024] : aspect < 0.82 ? [1024, 1536] : [1024, 1024];
  const canvas = document.createElement("canvas");
  [canvas.width, canvas.height] = target;
  const scale = Math.max(
    canvas.width / image.width,
    canvas.height / image.height,
  );
  const w = image.width * scale,
    h = image.height * scale;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, (canvas.width - w) / 2, (canvas.height - h) / 2, w, h);
  return {
    url: canvas.toDataURL("image/jpeg", 0.88),
    aspect: canvas.width / canvas.height,
  };
}

async function visionPhoto(file) {
  if (
    !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
    file.size > 8 * 1024 * 1024
  )
    throw Error("Choose a JPEG, PNG or WebP photo up to 8 MiB.");
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const scale = Math.min(1, 1400 / Math.max(img.width, img.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(img.width * scale));
    canvas.height = Math.max(1, Math.round(img.height * scale));
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.83).split(",")[1];
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function bindPhotoStudio({ el, world, api, context, local }) {
  const dialog = el("conceptStudio"),
    source = el("conceptSource"),
    room = el("conceptRoom"),
    pose = el("conceptPose");
  const frame = el("conceptFrame"),
    original = el("conceptOriginal"),
    after = el("conceptAfter"),
    status = el("conceptStatus");
  const brief = el("conceptBrief"),
    generate = el("developConcept"),
    variants = el("conceptVariant");
  let layoutDraft,
    layoutSources = [];
  const exampleLayout = structuredClone(recordedLayout);
  el("exampleLayout").onclick = () =>
    openLayout(el, exampleLayout, ["./assets/studio-source.jpg"]);
  const layoutButton = el("buildLayout");
  let current,
    sourceVersion = 0,
    busy = false,
    studies = [],
    drawn,
    readQueue = Promise.resolve();

  function enable() {
    layoutButton.disabled =
      !local ||
      busy ||
      !drawn ||
      !el("layoutWidth").value ||
      !el("layoutDepth").value;
    generate.disabled = !local || busy || !drawn || !brief.value.trim();
    for (const input of [
      el("layoutWidth"),
      el("layoutDepth"),
      el("layoutExtra"),
      el("exampleLayout"),
      source,
      room,
      pose,
      el("conceptUpload"),
      brief,
      ...el("conceptIdeas").children,
    ])
      input.disabled = busy;
  }
  function clearLayout() {
    layoutDraft = null;
    layoutSources = [];
    layoutButton.textContent = "Send photos & build study";
    el("layoutStatus").textContent = "";
  }
  for (const id of ["layoutWidth", "layoutDepth", "layoutExtra"])
    el(id).addEventListener("input", () => {
      clearLayout();
      enable();
    });
  layoutButton.onclick = async () => {
    if (layoutButton.disabled) return;
    const report = el("layoutStatus");
    if (layoutDraft) {
      openLayout(el, layoutDraft, layoutSources);
      return;
    }
    const width = el("layoutWidth").valueAsNumber,
      depth = el("layoutDepth").valueAsNumber;
    const extras = [...el("layoutExtra").files];
    if (
      ![width, depth].every((v) => Number.isFinite(v) && v >= 1.5 && v <= 15)
    ) {
      report.textContent = "Enter dimensions between 1.5 and 15 metres.";
      return;
    }
    if (extras.length > 2) {
      report.textContent = "Choose at most two additional views.";
      return;
    }
    busy = true;
    enable();
    const version = sourceVersion;
    report.textContent = "Identifying visible furniture with OpenAI…";
    try {
      const first =
        source.value === "upload"
          ? await visionPhoto(el("conceptUpload").files[0])
          : (drawn.startsWith("data:")
              ? drawn
              : (await frameImage(drawn)).url
            ).split(",")[1];
      const photos = [first, ...(await Promise.all(extras.map(visionPhoto)))];
      const draft = await api("/photo-layout", {
        photos,
        width,
        depth,
        consent: true,
      });
      if (version !== sourceVersion) return;
      layoutDraft = draft;
      layoutSources = photos.map((photo) => "data:image/jpeg;base64," + photo);
      layoutButton.textContent = "Reopen layout study";
      report.textContent = "Study ready. Reopen it to adjust or export.";
      if (dialog.open) openLayout(el, layoutDraft, layoutSources);
    } catch (error) {
      if (version === sourceVersion) report.textContent = error.message;
    } finally {
      busy = false;
      enable();
    }
  };
  function wipe(percent) {
    el("conceptWipe").value = percent;
    frame.style.setProperty("--split", percent + "%");
  }
  function showStudy(index) {
    const study = studies[index];
    after.hidden =
      el("conceptSeam").hidden =
      el("conceptCompare").hidden =
        !study;
    el("downloadConcept").hidden = !study;
    if (!study) return;
    after.src = study.url;
    el("downloadConcept").href = study.url;
    variants.value = String(index);
    brief.value = study.brief;
    wipe(50);
  }
  function resetSource() {
    ++sourceVersion;
    clearLayout();
    el("layoutWidth").value =
      el("layoutDepth").value =
      el("layoutExtra").value =
        "";
    studies = [];
    drawn = null;
    variants.replaceChildren();
    el("conceptHistory").hidden = true;
    after.removeAttribute("src");
    original.removeAttribute("src");
    el("downloadConcept").removeAttribute("href");
    original.hidden = true;
    el("conceptEmpty").hidden = false;
    status.textContent = "";
    el("conceptSourceLabel").textContent = "";
    showStudy(-1);
    enable();
    return sourceVersion;
  }
  async function loadSource() {
    const version = resetSource();
    el("exampleLayout").hidden = source.value !== "example";
    const useCamera = source.value === "town";
    el("conceptCameraControls").hidden = !useCamera;
    el("conceptUploadControl").hidden = source.value !== "upload";
    if (source.value === "example") {
      drawn = "./assets/studio-source.jpg";
      original.src = drawn;
      original.hidden = false;
      el("conceptEmpty").hidden = true;
      frame.style.aspectRatio = "1.5";
      frame.style.setProperty("--frame-ratio", "1.5");
      el("conceptSourceLabel").textContent =
        "Studio House · Revision 2 · Bedroom desk";
      studies = [
        {
          url: "./assets/studio-result.jpg",
          brief:
            "Moss-green limewash, a framed print and brass task lighting. Keep the chair and desk in place.",
        },
      ];
      variants.replaceChildren(new Option("Moss and brass", "0"));
      showStudy(0);
      enable();
      status.textContent = "Recorded design study · Drag to compare.";
      return;
    }
    const file = el("conceptUpload").files[0];
    if (!useCamera && !file) return;
    status.textContent = useCamera
      ? "Framing the room…"
      : "Preparing your photo…";
    let fileUrl;
    try {
      let url, label;
      if (useCamera) {
        const saved = current,
          id = room.value,
          part = saved.home.rooms.find((p) => p.design.room.id === id);
        const camera = bedroomCameras(part).find(
          (view) => view.id === pose.value,
        );
        const capture = readQueue.then(async () => {
          if (version !== sourceVersion) return;
          return world.bedroomViews(saved.home, id, [camera]);
        });
        readQueue = capture.catch(() => {});
        const result = await capture;
        if (version !== sourceVersion) return;
        url = result.images[0];
        label = [
          saved.revision ? "Revision " + saved.revision : "Showcase",
          part.design.room.name,
          camera.label,
        ].join(" · ");
        if (camera.reason) label += " · " + camera.reason;
      } else {
        if (
          !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
          file.size > 8 * 1024 * 1024
        )
          throw Error("Choose a JPEG, PNG or WebP photo up to 8 MiB.");
        fileUrl = URL.createObjectURL(file);
        url = fileUrl;
        label = file.name;
      }
      const image = await frameImage(url);
      if (version !== sourceVersion) return;
      drawn = image.url;
      original.src = drawn;
      original.hidden = false;
      el("conceptEmpty").hidden = true;
      frame.style.aspectRatio = String(image.aspect);
      frame.style.setProperty("--frame-ratio", String(image.aspect));
      el("conceptSourceLabel").textContent = label;
      status.textContent = "";
    } catch (error) {
      if (version === sourceVersion) status.textContent = error.message;
    } finally {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
      enable();
    }
  }
  function roomChanged() {
    const part = current.home.rooms.find(
      (p) => p.design.room.id === room.value,
    );
    pose.replaceChildren(
      ...bedroomCameras(part).map((v) => new Option(v.label, v.id)),
    );
    void loadSource();
  }
  el("openPhotoStudio").hidden = false;
  el("layoutSetup").hidden = !local;
  if (!local) {
    source.closest("label").hidden = true;
    generate.hidden =
      brief.closest("label").hidden =
      el("conceptIdeas").hidden =
        true;
    generate.nextElementSibling.hidden = true;
  }
  function open(preferredRoom) {
    dialog.showModal();
    const saved = context();
    if (
      (!preferredRoom || (source.value === "town" && preferredRoom === room.value)) &&
      current?.home === saved.home &&
      saved.project === current.project &&
      saved.revision === current.revision
    )
      return;
    current = saved;
    room.replaceChildren(
      ...saved.home.rooms.map(
        (p) => new Option(p.design.room.name, p.design.room.id),
      ),
    );
    if (saved.home.rooms.some((p) => p.design.room.id === "bedroom"))
      room.value = "bedroom";
    if (preferredRoom) room.value = preferredRoom;
    el("conceptUpload").value = "";
    source.value = preferredRoom && local ? "town" : "example";
    roomChanged();
  }
  el("openPhotoStudio").onclick = () => open();
  room.onchange = roomChanged;
  pose.onchange = source.onchange = el("conceptUpload").onchange = loadSource;
  brief.oninput = enable;
  for (const button of el("conceptIdeas").children)
    button.onclick = () => {
      brief.value = looks[button.dataset.look];
      enable();
    };
  generate.onclick = async () => {
    if (generate.disabled) return;
    const version = sourceVersion,
      direction = brief.value.trim();
    busy = true;
    enable();
    status.textContent = "Developing one image with OpenAI…";
    try {
      const image = drawn.startsWith("data:")
        ? drawn
        : (await frameImage(drawn)).url;
      const result = await api("/photo-concept", {
        photo: image.split(",")[1],
        direction,
        consent: true,
      });
      if (version !== sourceVersion) return;
      if (studies.length === 3) studies.shift();
      studies.push({
        url: "data:image/jpeg;base64," + result.jpeg,
        brief: direction,
      });
      variants.replaceChildren(
        ...studies.map((s, i) => new Option(s.brief.slice(0, 64), String(i))),
      );
      el("conceptHistory").hidden = studies.length < 2;
      showStudy(studies.length - 1);
      status.textContent = "Concept ready. Drag across the image to compare.";
    } catch (error) {
      if (version === sourceVersion) status.textContent = error.message;
    } finally {
      busy = false;
      enable();
    }
  };
  variants.onchange = () => {
    showStudy(Number(variants.value));
    enable();
  };
  el("conceptWipe").oninput = (e) => wipe(e.target.value);
  function drag(e) {
    const r = frame.getBoundingClientRect();
    wipe(Math.max(0, Math.min(100, (100 * (e.clientX - r.left)) / r.width)));
  }
  frame.onpointerdown = (e) => {
    if (after.hidden) return;
    frame.setPointerCapture(e.pointerId);
    drag(e);
  };
  frame.onpointermove = (e) => {
    if (frame.hasPointerCapture(e.pointerId)) drag(e);
  };
  return open;
}
