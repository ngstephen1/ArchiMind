import {mountViewer} from './viewer.js';
import {mountRoomViewer} from './room_viewer.js';
export {mountViewer} from './viewer.js';
export {mountRoomViewer} from './room_viewer.js';
export default function({parentElement,data}) {
  return data?.schema_version===2?mountRoomViewer(parentElement,data):mountViewer(parentElement,data);
}
