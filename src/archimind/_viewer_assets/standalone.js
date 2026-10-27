import {mountViewer} from './viewer.js';
try {
  const response = await fetch('./sample-design.json');
  if (!response.ok) throw new Error('Sample unavailable');
  mountViewer(document.querySelector('.viewer-host'), await response.json());
} catch {
  document.querySelector('.viewer-host').textContent = 'Unable to load the local sample design.';
}
