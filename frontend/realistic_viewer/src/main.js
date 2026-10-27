import {mountViewer} from './viewer.js';
export {mountViewer} from './viewer.js';
export default function({parentElement, data}) {
  return mountViewer(parentElement.querySelector('.viewer-host'), data);
}
