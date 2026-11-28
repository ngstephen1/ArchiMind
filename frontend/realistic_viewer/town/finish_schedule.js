// Collect selected finishes once for the client presentation and exported book.
import { finishColors } from "./finish_chat.js";
import { presentationFurniture } from "./saved_pieces.js";

export function finishSchedule(home) {
  const groups = new Map();
  function record(surface, finish, location) {
    if (!finish) return;
    const key = surface + "/" + finish;
    if (!groups.has(key)) groups.set(key, {surface, finish, color: finishColors[finish], locations: []});
    groups.get(key).locations.push(location);
  }
  for (const part of home.rooms) {
    const {id, name} = part.design.room;
    const overrides = part.finish_overrides || {};
    for (const role of ["wall", "floor"]) record(role, overrides[role], {room: id, label: name});
    const objects = overrides.objects || {};
    for (const item of presentationFurniture(part)) {
      record("object", objects[item.id], {room: id, object: item.id, label: name + " · " + item.name});
    }
  }
  if (home.hall_finish && !home.photo_home) record("floor", home.hall_finish, {room: "hall", label: "Hall"});
  return [...groups.values()];
}

export function baseFinishLocations(home) {
  const locations = {wall: [], floor: [], tile: [], hall_wall: [], hall_floor: []};
  for (const part of home.rooms) {
    const room = part.design.room, overrides = part.finish_overrides || {};
    if (!overrides.wall) locations.wall.push(room.name);
    if (!overrides.floor) locations[room.id === "bathroom" ? "tile" : "floor"].push(room.name);
  }
  if (Number.isFinite(home.hall)) {
    locations.hall_wall.push("Hall ends");
    if (!home.hall_finish) locations.hall_floor.push("Hall");
  }
  return locations;
}
