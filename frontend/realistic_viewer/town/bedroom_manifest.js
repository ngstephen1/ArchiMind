import { bedroomCameras } from "./bedroom_cameras.js";
import {
  PRODUCT_ASSETS,
  productSceneAdmission,
  productSceneBudget,
  validateProductBindings,
} from "../src/product_assets.js";
import indexes from "./bedroom_indexes.cjs";

const { surfaces, publications } = indexes;

const bedDesk = PRODUCT_ASSETS["abo-b074l4976t-amazon-co-uk"];
const dim = (item) => [item.width_m, item.depth_m, item.height_m];
const HEX = /^[0-9a-f]{64}$/;

// Order keys recursively so a reloaded SQL snapshot and a fresh response export identical bytes.
export const manifestText = (record) =>
  JSON.stringify(
    record,
    (_, value) =>
      value && typeof value === "object" && !Array.isArray(value)
        ? Object.fromEntries(
            Object.keys(value)
              .sort()
              .map((key) => [key, value[key]]),
          )
        : value,
    2,
  ) + "\n";

export function bedroomManifest({ project, revision, home }) {
  if (
    !project ||
    !Number.isSafeInteger(revision) ||
    revision < 1 ||
    !HEX.test(home?.id)
  )
    throw Error("Apply a home revision before exporting.");
  const bedroom = home.rooms.find(({ design }) => design.room.id === "bedroom");
  if (!bedroom) throw Error("Saved bedroom unavailable.");
  const { room, furniture } = bedroom.design;
  const bindings = home.rooms.flatMap((part) => part.asset_bindings || []);
  let nativeProducts;
  try {
    validateProductBindings({
      design: bedroom.design,
      asset_bindings: bedroom.asset_bindings,
      unavailable_assets: [],
    });
    nativeProducts =
      productSceneAdmission(bindings).admitted &&
      productSceneBudget(bindings).passed;
  } catch {
    nativeProducts = false;
  }
  const desk = furniture.find((f) => f.id === "belaya");
  const items = furniture.map((f) => {
    let source = null,
      turn = 0;
    const binding = bedroom.asset_bindings.find((b) => b.furniture_id === f.id);
    const concept =
      f.id === "desk-chair"
        ? bedroom.designer_chair
        : bedroom.designer_collection?.[f.id];
    if (f.rotation_deg !== 0) throw Error("Unsupported reservation rotation.");
    if (
      nativeProducts &&
      f.id === "belaya" &&
      binding?.asset_id === bedDesk.asset_id &&
      binding.render_version === bedDesk.render_version &&
      binding.envelope_sha256 === bedDesk.envelope_sha256 &&
      dim(f).every((v, i) => v === bedDesk.dimensions[i])
    ) {
      source = {
        kind: "catalog",
        id: bedDesk.asset_id,
        version: bedDesk.render_version,
        sha256: bedDesk.sha256,
        translation_m: [0, -bedDesk.translation[2], 0],
      };
    } else if (concept) {
      source = {
        kind: "concept",
        id: concept.binding.concept_id,
        version: concept.binding.version,
        sha256: concept.binding.sha256,
        translation_m: [0, 0, 0],
      };
      if (!HEX.test(source.sha256))
        throw Error("Invalid saved concept release.");
    }
    if (f.id === "desk-chair" && desk && desk.y_m > f.y_m) turn = 180;
    return {
      id: f.id,
      name: concept?.name || f.name,
      source,
      rotation_deg: turn,
      footprint_xy_m: [f.x_m, f.y_m],
      reservation_wdh_m: dim(f),
      center_floor_xyz_m: [f.x_m + f.width_m / 2, f.y_m + f.depth_m / 2, 0],
    };
  });
  const fromThree = ([x, y, z]) => [
    x - bedroom.origin[0],
    -z - bedroom.origin[1],
    y,
  ];
  const cameras = bedroomCameras(bedroom).map(
    ({ id, label, eye, target, fov, reason }) => ({
      id,
      label,
      eye_xyz_m: fromThree(eye),
      target_xyz_m: fromThree(target),
      vertical_fov_degrees: fov,
      reason,
    }),
  );
  return {
    schema_version: 1,
    project,
    revision,
    home_id: home.id,
    palette: home.palette,
    coordinates: "Bedroom-local metres: +X east, +Y north, +Z up",
    origin_xy_m: bedroom.origin,
    surface_sources: surfaces.map(
      ({ asset, local, sha256, source_sha256 }) => ({
        asset,
        local,
        sha256,
        source_sha256,
      }),
    ),
    hall_context: {
      origin_xy_m: [home.hall - bedroom.origin[0], -bedroom.origin[1]],
      width_m: 1.6,
      depth_m: home.depth,
      opposite_rooms: home.rooms
        .filter((p) => p.design.room.doors[0].wall !== room.doors[0].wall)
        .map((p) => ({
          origin_xy_m: p.origin.map((v, i) => v - bedroom.origin[i]),
          room: structuredClone(p.design.room),
        })),
    },
    room: structuredClone(room),
    furniture: items,
    cameras,
  };
}

export async function manifestDigest(record) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(manifestText(record)),
  );
  return Array.from(new Uint8Array(digest), (v) =>
    v.toString(16).padStart(2, "0"),
  ).join("");
}

export function publicationFor(manifest, digest, entries = publications) {
  return entries.find(
    (entry) =>
      entry.manifest_sha256 === digest &&
      entry.project === manifest.project &&
      entry.revision === manifest.revision &&
      entry.home_id === manifest.home_id,
  );
}
