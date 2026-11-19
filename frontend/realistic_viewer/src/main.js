import {mountViewer} from './viewer.js';
import {mountRoomViewer} from './room_viewer.js';
import {createSceneManager,selectedSceneOwner} from './scene_lifecycle.js';
export {mountViewer} from './viewer.js';
export {mountRoomViewer} from './room_viewer.js';
const update=createSceneManager((host,data,options)=>[2,3,4,5,6].includes(data?.schema_version)?mountRoomViewer(host,data,options):mountViewer(host,data));
export default function({parentElement,data}) {
  return update(parentElement,data,{owner:selectedSceneOwner(parentElement)});
}
