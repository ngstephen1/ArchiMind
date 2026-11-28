import { wallQuads } from "../src/room_geometry.js";
import { baseFinishLocations, finishSchedule } from "./finish_schedule.js";
import { presentationFurniture, presentationFurnitureParts } from "./saved_pieces.js";
import { turnedCoverlet } from "./studio_textiles.js";
import { bedroomManifest } from "./bedroom_manifest.js";
import { bedroomCameras } from "./bedroom_cameras.js";
import {
  studioFinishes,
  salonDetails,
} from "./studio_furniture.js";

export function homeBoard(snapshot) {
  const imported = Boolean(snapshot.home.photo_home);
  const bedroom = imported ? null : bedroomManifest(snapshot);
  const schedule = finishSchedule(snapshot.home);
  const studio = snapshot.home.rooms.some((p) => p.design.room.id === "salon");
  return {
    schema_version: 1,
    kind: "whole-home-presentation",
    project: snapshot.project,
    revision: snapshot.revision,
    home_id: snapshot.home.id,
    palette: snapshot.home.palette,
    width: snapshot.home.width,
    depth: snapshot.home.depth,
    hall: snapshot.home.hall,
    finishes: schedule.length ? {...studioFinishes, ...Object.fromEntries(
      schedule.map(row => ["proposal-" + row.finish, row.color]))} : studioFinishes,
    ...(schedule.length ? {finish_schedule: schedule, base_finish_locations: baseFinishLocations(snapshot.home)} : {}),
    ...(Number.isFinite(snapshot.home.hall) && snapshot.home.hall_finish?{hall_finish:"proposal-"+snapshot.home.hall_finish}:{}),
    ...(snapshot.home.presentation_detail ? { presentation_detail: snapshot.home.presentation_detail } : {}),
    ...(imported ? { shell_source: "user-confirmed photo room dimensions" } : { bedroom }),
    rooms: snapshot.home.rooms.map((part) => {
      const { room, furniture } = part.design;
      const hasBed =
        studio &&
        room.id === "bedroom" &&
        bedroom.furniture.some(
          (f) => f.id === "queen-bed" && f.source?.kind === "concept",
        );
      return {
        room,
        ...(imported ? { panels: wallQuads(room) } : {}),
        origin: part.origin,
        ...(part.finish_overrides ? {finish_overrides:part.finish_overrides} : {}),
        textile: hasBed
          ? turnedCoverlet(furniture.find((f) => f.id === "queen-bed"))
          : null,
        details: salonDetails(part),
        furniture: presentationFurniture(part).map(item => {
          const usesStudio = room.id !== "bedroom" &&
            (studio || (snapshot.home.service_layout && item.id === "breakfast-suite"));
          const parts = presentationFurnitureParts(part, item, usesStudio);
          const finish = part.finish_overrides?.objects?.[item.id];
          return {
            ...item,
            parts: finish ? parts.map(piece => ({...piece, finish: "proposal-" + finish})) : parts,
          };
        }),
        cameras: bedroomCameras(part),
      };
    }),
  };
}
