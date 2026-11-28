import { wallQuads } from "../src/room_geometry.js";
import {finishColors} from "./finish_chat.js";
import { savedFurnitureParts } from "./saved_pieces.js";
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
    finishes: snapshot.home.rooms.some(p=>p.finish_overrides) ? {...studioFinishes,...Object.fromEntries(Object.entries(finishColors).map(([k,v])=>["proposal-"+k,v]))} : studioFinishes,
    ...(snapshot.home.hall_finish?{hall_finish:"proposal-"+snapshot.home.hall_finish}:{}),
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
        furniture: furniture.map((f) => ({
          ...f,
          parts:
            savedFurnitureParts(part,f,room.id !== "bedroom" && (studio || (snapshot.home.service_layout && f.id === "breakfast-suite"))).map(p=>{
              const id=p.selectedPiece?.id || (p.coffeeComponent?"salon-coffee-table":f.id);
              const finish=part.finish_overrides?.objects?.[id];
              return finish ? {...p,finish:"proposal-"+finish} : p;
            }),
        })),
        cameras: bedroomCameras(part),
      };
    }),
  };
}
