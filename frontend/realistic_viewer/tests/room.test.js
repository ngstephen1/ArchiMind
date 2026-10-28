import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as THREE from 'three';
import {validateScene,wallQuads,openingQuad,cameraFrame,canonicalVolume} from '../src/room_geometry.js';
import {fittedInstance,placeholder,quadGeometry} from '../src/room_objects.js';
import {createAssetPool} from '../src/asset_pool.js';
const data=JSON.parse(await readFile(new URL('../../../src/archimind/_viewer_assets/room-design.json',import.meta.url)));
const copy=o=>structuredClone(o),near=(a,b,e=1e-6)=>assert.ok(Math.abs(a-b)<e,`${a} != ${b}`);
const wait=()=>new Promise(resolve=>setTimeout(resolve,20));
function triangleArea(points){return Math.abs(points.reduce((a,p,i)=>{const q=points[(i+1)%points.length];return a+p[0]*q[1]-p[1]*q[0];},0))/2;}
function clippedArea(points,rect){
  let p=points;
  for(const [axis,bound,sign] of [[0,rect.left,1],[0,rect.right,-1],[1,rect.bottom,1],[1,rect.top,-1]]){
    const next=[];
    for(let i=0;i<p.length;i++){
      const a=p[i],b=p[(i+1)%p.length],ia=sign*(a[axis]-bound)>=0,ib=sign*(b[axis]-bound)>=0;
      if(ia)next.push(a);
      if(ia!==ib){const t=(bound-a[axis])/(b[axis]-a[axis]);next.push(a.map((v,k)=>v+(b[k]-v)*t));}
    }
    p=next;
  }
  return p.length<3?0:triangleArea(p);
}
test('canonical scene is deterministic and never mutated',()=>{
  const before=JSON.stringify(data);validateScene(data);wallQuads(data.design.room);assert.equal(JSON.stringify(data),before);
  assert.deepEqual(wallQuads(data.design.room),wallQuads(copy(data.design.room)));
});
for(const wall of ['north','south','east','west'])test(`actual wall triangles leave door/window gaps on ${wall}`,()=>{
  const r=copy(data.design.room);r.doors[0].wall=wall;r.windows[0].wall=wall;r.windows[0].offset_m=2;
  const panels=wallQuads(r).filter(q=>q.wall===wall),geometry=quadGeometry(panels.map(q=>q.points));
  const positions=geometry.attributes.position,index=geometry.index.array,triangles=[];
  for(let i=0;i<index.length;i+=3){
    const points=Array.from(index.slice(i,i+3),j=>['north','south'].includes(wall)?[positions.getX(j),positions.getY(j)]:[-positions.getZ(j),positions.getY(j)]);
    assert.ok(triangleArea(points)>0);triangles.push(points);
  }
  const length=['north','south'].includes(wall)?r.width_m:r.depth_m;
  near(triangles.reduce((sum,p)=>sum+triangleArea(p),0),length*r.ceiling_height_m-.9*2.1-1.5*1.2,2e-6);
  for(const o of [...r.doors,...r.windows]){
    const rect={left:o.offset_m,right:o.offset_m+o.width_m,bottom:o.sill_height_m??0,top:(o.sill_height_m??0)+o.height_m};
    near(triangles.reduce((sum,p)=>sum+clippedArea(p,rect),0),0,1e-6);
  }
  geometry.dispose();
});
test('corner, overlapping and fully open walls have correct remaining area',()=>{
  const r=copy(data.design.room);r.windows=[];
  r.doors=[{...r.doors[0],offset_m:0,width_m:r.width_m,height_m:r.ceiling_height_m}];
  assert.equal(wallQuads(r).filter(q=>q.wall==='south').length,0);
  r.doors=[{...r.doors[0],width_m:1},{...r.doors[0],id:'overlap',offset_m:.5,width_m:1}];
  const area=wallQuads(r).filter(q=>q.wall==='south').reduce((a,p)=>a+(p.right-p.left)*(p.top-p.bottom),0);
  near(area,(5-1.5)*2.7);
});
test('decimal endpoint roundoff cannot add a sliver outside the room',()=>{
  const r=copy(data.design.room);r.width_m=.3;r.windows=[];r.doors=[{...r.doors[0],offset_m:.1,width_m:.2}];
  assert.ok(wallQuads(r).filter(q=>q.wall==='south').every(q=>q.right<=.3));
});
test('window elevation and transformed planes are canonical',()=>{
  const r=data.design.room,w=r.windows[0],q=openingQuad(r,w),g=quadGeometry([q]);
  assert.equal(Math.min(...q.map(p=>p[2])),w.sill_height_m);
  assert.ok(Array.from(g.attributes.position.array).every(Number.isFinite));
  for(let i=0;i<4;i++){near(g.attributes.position.getZ(i),-r.depth_m);}
  g.dispose();
});
test('independent fitted instances share immutable source resources',()=>{
  const source=new THREE.Group();source.add(new THREE.Mesh(new THREE.BoxGeometry(2,1,1),new THREE.MeshStandardMaterial()));
  const before=JSON.stringify(source.toJSON()),[a,b]=data.design.furniture;
  const first=fittedInstance(source,a),second=fittedInstance(source,b);
  assert.notEqual(first,second);assert.equal(first.children[0].geometry,second.children[0].geometry);
  assert.equal(first.children[0].material,second.children[0].material);
  assert.equal(first.userData.furnitureId,a.id);assert.equal(second.userData.furnitureId,b.id);
  assert.notEqual(first.userData.scale,second.userData.scale);
  for(const [object,f] of [[first,a],[second,b]]){
    const box=new THREE.Box3().setFromObject(object),v=canonicalVolume(f);
    for(let i=0;i<3;i++){assert.ok(box.min.toArray()[i]>=v.min[i]-1e-6);assert.ok(box.max.toArray()[i]<=v.max[i]+1e-6);}
    near(box.min.y,0);
  }
  const old=second.position.clone();first.position.x+=1;assert.ok(second.position.equals(old));
  assert.equal(JSON.stringify(source.toJSON()),before);
  source.children[0].geometry.dispose();source.children[0].material.dispose();
});
test('unknown category placeholder is labeled and dimensionally accurate',()=>{
  const f={...data.design.furniture[2],category:'unknown'},object=placeholder(f),box=new THREE.Box3().setFromObject(object),v=canonicalVolume(f);
  assert.equal(object.userData.kind,'procedural_placeholder');assert.equal(object.userData.furnitureId,f.id);
  box.min.toArray().forEach((x,i)=>near(x,v.min[i]));box.max.toArray().forEach((x,i)=>near(x,v.max[i]));
  object.geometry.dispose();object.material.dispose();
});
for(const aspect of [.8,1.35,2])test(`camera framing projects all room corners inside aspect ${aspect}`,()=>{
  const min=[-.12,-.12,-4.12],max=[5.12,2.82,.12],view=cameraFrame(min,max,aspect);
  const camera=new THREE.PerspectiveCamera(42,aspect,.02,200);camera.position.set(...view.position);camera.lookAt(new THREE.Vector3(...view.target));camera.updateMatrixWorld();
  for(const x of [min[0],max[0]])for(const y of [min[1],max[1]])for(const z of [min[2],max[2]]){
    const p=new THREE.Vector3(x,y,z).project(camera);assert.ok(Math.abs(p.x)<1&&Math.abs(p.y)<1&&p.z<1&&p.z>-1);
  }
  assert.deepEqual(cameraFrame(min,max,aspect),view);
});
test('empty room validates and has four wall surfaces without asset requests',()=>{
  const empty=copy(data);empty.design.furniture=[];empty.asset_bindings=[];validateScene(empty);
  assert.equal(new Set(wallQuads(empty.design.room).map(q=>q.wall)).size,4);
});
test('rejects unsupported rotation, arbitrary paths and unknown bindings',()=>{
  const bad=copy(data);bad.design.furniture[0].rotation_deg=90;assert.throws(()=>validateScene(bad));
  for(const asset_id of ['../chair.glb','https://example.com/chair.glb','made-up']){
    const b=copy(data);b.asset_bindings[0].asset_id=asset_id;assert.throws(()=>validateScene(b));
  }
  const unknown=copy(data);unknown.asset_bindings[0].furniture_id='unknown';assert.throws(()=>validateScene(unknown));
});
test('asset pool loads once, reuses pending promise and disposes once after final release',async()=>{
  let loads=0,disposals=0;const model={name:'shared'};
  const pool=createAssetPool(async()=>{loads++;return model;},()=>{disposals++;},0);
  const a=pool.acquire('sheen-chair'),b=pool.acquire('sheen-chair');
  assert.equal(a.promise,b.promise);assert.equal(await a.promise,model);assert.equal(loads,1);
  a.release();await wait();assert.equal(disposals,0);b.release();b.release();await wait();assert.equal(disposals,1);
});
test('rapid remount reuses loaded asset; missing asset is explicit and has no automatic retry',async()=>{
  let loads=0,disposed=0;const pool=createAssetPool(async()=>{loads++;return {};},()=>{disposed++;},10);
  const a=pool.acquire('sheen-chair');await a.promise;a.release();const b=pool.acquire('sheen-chair');await b.promise;
  assert.equal(loads,1);assert.equal(disposed,0);b.release();await wait();assert.equal(disposed,1);
  const broken=createAssetPool(async()=>{throw Error('missing');},()=>{},0),handle=broken.acquire('sheen-chair');
  await assert.rejects(handle.promise,/missing/);handle.release();await wait();assert.equal(broken.loads,1);
  assert.throws(()=>broken.acquire('https://invalid'));
});
test('cleanup aborts the last pending load and disposes a late decoded model once',{timeout:1000},async()=>{
  let signal,disposals=0,finish;
  const disposed=new Promise(resolve=>{finish=resolve;});
  const model={name:'late decode'};
  const pool=createAssetPool(async(id,s)=>{
    signal=s;
    // A decode already in progress can finish even after fetch cancellation.
    return new Promise(resolve=>s.addEventListener('abort',()=>resolve(model),{once:true}));
  },value=>{assert.equal(value,model);disposals++;finish();},0);
  const handle=pool.acquire('sheen-chair');await Promise.resolve();
  handle.release();handle.release();await disposed;
  assert.equal(signal.aborted,true);assert.equal(disposals,1);
});
