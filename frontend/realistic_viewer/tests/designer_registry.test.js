import test from 'node:test';
import assert from 'node:assert/strict';
import {chairRecord} from '../src/designer_chair.js';

const row = {concept_id: 'oak-sage-writing-chair', version: '1.0.0', name: 'Oak', sha256: 'a'.repeat(64),
  front_sha256: 'b'.repeat(64), three_quarter_sha256: 'c'.repeat(64), width_m: 0.48, depth_m: 0.52, height_m: 0.83, bytes: 80844};
const binding = {concept_id: row.concept_id, version: row.version, sha256: row.sha256};

test('v1 registry chair record still resolves', () => {
  assert.deepEqual(chairRecord({schema_version: 1, chairs: [row]}, binding), row);
});

test('v2 registry resolves only chair-category pieces', () => {
  const piece = {...row, category: 'chair'};
  const armchair = {...row, concept_id: 'green-velvet-tub-armchair', category: 'armchair', sha256: 'd'.repeat(64)};
  assert.deepEqual(chairRecord({schema_version: 2, pieces: [piece, armchair]}, binding), piece);
  assert.throws(() => chairRecord({schema_version: 2, pieces: [{...piece, category: 'armchair'}]}, binding));
  assert.throws(() => chairRecord({schema_version: 3, pieces: [piece]}, binding));
});
