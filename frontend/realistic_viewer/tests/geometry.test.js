import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {toThree, toCanonical, fitBounds, validatePayload} from '../src/geometry.js';
// tests/ -> realistic_viewer/ -> frontend/ -> repository/
const sample = JSON.parse(await readFile(new URL('../../../src/archimind/_viewer_assets/sample-design.json', import.meta.url)));
const near = (a,b) => assert.ok(Math.abs(a-b) < 1e-10, `${a} != ${b}`);
test('right-handed mapping: east +X, north -Z, up +Y', () => {
  assert.deepEqual(toThree([1,2,3]), [1,3,-2]);
  assert.deepEqual(toCanonical(toThree([1,2,3])), [1,2,3]);
  assert.deepEqual(toThree([0,1,0]),[0,0,-1]);
  assert.deepEqual(toThree([0,0,1]),[0,1,-0]);
});
test('native +Z front faces canonical south with yaw 0', () => {
  assert.deepEqual(toCanonical([0,0,1]),[0,-1,0]);
});
for (const size of [[2,1,1],[1,2,1],[1,1,2]]) {
  test(`uniform fitting contains all corners for ${size}`, () => {
    const f=sample.furniture,min=[-2,-.2,3],max=min.map((v,i)=>v+size[i]);
    const fit=fitBounds(min,max,f);
    const ratios=fit.size.map((v,i)=>v/size[i]);
    ratios.forEach(v=>near(v,fit.scale));
    assert.ok(fit.min[0]>=f.x_m-1e-12 && fit.max[0]<=f.x_m+f.width_m+1e-12);
    near(fit.min[1],0); assert.ok(fit.max[1]<=f.height_m+1e-12);
    assert.ok(fit.min[2]>=-f.y_m-f.depth_m-1e-12 && fit.max[2]<=-f.y_m+1e-12);
    near((fit.min[0]+fit.max[0])/2,f.x_m+f.width_m/2);
    near((fit.min[2]+fit.max[2])/2,-f.y_m-f.depth_m/2);
    assert.ok(fit.size.some((v,i)=>Math.abs(v-[f.width_m,f.height_m,f.depth_m][i])<1e-12));
  });
}
test('sample is accepted without mutation; offsets do not get remapped in data', () => {
  const before=JSON.stringify(sample);validatePayload(sample);
  fitBounds([-1,-1,-1],[1,1,1],sample.furniture);
  assert.equal(JSON.stringify(sample),before);
});
test('rejects injected URLs, extra keys, non-finite coordinates and unsupported geometry', () => {
  for(const patch of [{asset_url:'https://example.com/model.glb'},{script:'alert(1)'},{asset_id:'other'}]) {
    assert.throws(()=>validatePayload({...sample,...patch}));
  }
  for(const patch of [{rotation_deg:90},{x_m:NaN},{height_m:Infinity},{width_m:0},{category:'desk'}]) {
    assert.throws(()=>validatePayload({...sample,furniture:{...sample.furniture,...patch}}));
  }
});
test('rejects collapsed, inverted and non-finite imported bounds',()=>{
  for(const max of [[0,1,1],[-1,1,1],[Infinity,1,1]])assert.throws(()=>fitBounds([0,0,0],max,sample.furniture));
});
test('one actual GLB has embedded geometry and textures',async()=>{
  const bytes=await readFile(new URL('../../../src/archimind/_viewer_assets/furniture/SheenChair.glb',import.meta.url));
  assert.equal(bytes.toString('ascii',0,4),'glTF'); assert.equal(bytes.readUInt32LE(4),2);
  assert.equal(bytes.readUInt32LE(8),bytes.length);
  const g=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  assert.equal(g.meshes.length,4);assert.equal(g.images.length,7);
  assert.ok(g.images.every(i=>i.bufferView!==undefined && i.uri===undefined));
});
