import {mountViewer} from './viewer.js';
import {mountRoomViewer} from './room_viewer.js';
export {mountViewer} from './viewer.js';
export {mountRoomViewer} from './room_viewer.js';
export default function({parentElement,data}) {
  return [2,3].includes(data?.schema_version)?mountRoomViewer(parentElement,data):mountViewer(parentElement,data);
}
