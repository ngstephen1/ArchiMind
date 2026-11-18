import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {queenBed,addWallFinish} from '../src/bedroom_finishes.js';
import {canonicalVolume,wallQuads} from '../src/room_geometry.js';
import {disposeObject} from '../src/viewer.js';

test('illustrative bedding stays inside the measured queen reservation',()=>{
  const f={id:'queen-bed',width_m:1.6,depth_m:2,height_m:.6,x_m:3.4,y_m:2};
  const bed=queenBed(f), bounds=new THREE.Box3().setFromObject(bed), expected=canonicalVolume(f);
  assert.equal(bed.userData.kind,'procedural_placeholder');
  for(let i=0;i<3;i++){
    assert.ok(Math.abs(bounds.min.getComponent(i)-expected.min[i])<1e-5);
    assert.ok(Math.abs(bounds.max.getComponent(i)-expected.max[i])<1e-5);
  }
  disposeObject(bed);
});

test('baseboards stop on either side of the doorway',()=>{
  const room={width_m:5,depth_m:4,ceiling_height_m:2.7,doors:[
    {wall:'south',offset_m:.6,width_m:.85,height_m:2.1}],windows:[]};
  const group=new THREE.Group();
  addWallFinish(group,room,'south',wallQuads(room).filter(q=>q.wall==='south'));
  const center=new THREE.Vector3(1.025,.045,0);
  assert.ok(group.children.length>=5);
  assert.ok(group.children.every(mesh=>!new THREE.Box3().setFromObject(mesh).containsPoint(center)));
  disposeObject(group);
});
