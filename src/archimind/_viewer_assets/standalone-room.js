import {mountRoomViewer} from './viewer.js';
try {
  const response=await fetch('./room-design.json');if(!response.ok)throw Error('Sample unavailable');
  mountRoomViewer(document.querySelector('.viewer-host'),await response.json());
}catch{document.querySelector('.viewer-host').textContent='Unable to load the local room sample.';}
