import { bedroomManifest } from "./bedroom_manifest.js";
import { bedroomCameras } from "./bedroom_cameras.js";
import { studioFinishes,studioFurniture,salonDetails } from "./studio_furniture.js";

export function homeBoard(snapshot) {
  const bedroom = bedroomManifest(snapshot);
  const studio = snapshot.home.rooms.some(p => p.design.room.id === "salon");
  return {
    schema_version: 1, kind:"whole-home-presentation", project:snapshot.project,
    revision:snapshot.revision, home_id:snapshot.home.id, palette:snapshot.home.palette,
    width:snapshot.home.width, depth:snapshot.home.depth, hall:snapshot.home.hall,
    finishes:studioFinishes, bedroom,
    rooms:snapshot.home.rooms.map(part => {
      const {room,furniture}=part.design;
      return {room, origin:part.origin, details:salonDetails(part), furniture:furniture.map(f=>({...f,
        parts:studio && room.id!=="bedroom" ? studioFurniture(f,part.suite_yaw_deg):[]})),
        cameras:bedroomCameras(part)};
    })
  };
}
