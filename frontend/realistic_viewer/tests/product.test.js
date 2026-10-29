import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
import * as THREE from 'three';
import {PRODUCT_ASSETS,compatibleProduct,validateProductBindings,productSceneBudget,boundedProductBytes,verifyDecodedProduct,nativeProductInstance} from '../src/product_assets.js';
import {validateScene} from '../src/room_geometry.js';
import {createAssetPool} from '../src/asset_pool.js';
const id='abo-b075x2x4xs-amazon-com',r=PRODUCT_ASSETS[id],clone=o=>structuredClone(o);
globalThis.crypto??=webcrypto;
const legacy=JSON.parse(await readFile(new URL('../../../src/archimind/_viewer_assets/room-design.json',import.meta.url)));
function scene(){const p=clone(legacy);p.schema_version=3;for(const f of p.design.furniture)if(f.category==='chair')[f.width_m,f.depth_m,f.height_m]=r.dimensions;
 p.asset_bindings=p.design.furniture.map(f=>({furniture_id:f.id,asset_id:f.category==='chair'?id:null,render_version:f.category==='chair'?'1.0.0':null,envelope_sha256:f.category==='chair'?r.envelope_sha256:null}));return p;}
function synthetic(){
 const model=new THREE.Group(),g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute([-.5,0,-.5,.5,0,-.5,0,1,.5],3));g.setIndex([0,1,2]);
 const m=new THREE.MeshStandardMaterial();m.map=new THREE.Texture({width:1,height:1});model.add(new THREE.Mesh(g,m));model.updateMatrixWorld(true);
 const record={...clone(r),native_min:[-.5,0,-.5],native_max:[.5,1,.5],dimensions:[1,1,1],translation:[0,0,0],triangles:1,texture_bytes:4,images:[{width:1,height:1}],material_count:1,mesh_instances:1};
 return {model,record,f:{id:'f',name:'test',category:'chair',rotation_deg:0,x_m:1,y_m:2,width_m:1,depth_m:1,height_m:1}};
}
test('product registry is deeply frozen and bound to known source',()=>{assert.ok(Object.isFrozen(r)&&Object.isFrozen(r.dimensions));assert.equal(r.product_id,'B075X2X4XS');assert.equal(r.variant_label,'Sod');assert.equal(r.bytes,4252440);assert.equal(r.triangles,42706);assert.throws(()=>r.dimensions.push(5));});
test('v3 scene is exact and immutable; v2 stays accepted',()=>{const p=scene(),before=JSON.stringify(p);assert.equal(validateScene(p),p);assert.equal(JSON.stringify(p),before);assert.equal(validateScene(legacy),legacy);});
for(const kind of ['yaw','dimensions','category','asset','version','envelope','URL','approval','coverage','duplicate','unavailable','placeholder'])test(`reject ${kind} in product scene`,()=>{
 const p=scene(),f=p.design.furniture[0],b=p.asset_bindings[0];
 if(kind==='yaw')f.rotation_deg=90;if(kind==='dimensions')f.width_m=.9906;if(kind==='category')f.category='desk';if(kind==='asset')b.asset_id='sheen-chair';if(kind==='version')b.render_version='9.0.0';if(kind==='envelope')b.envelope_sha256='0'.repeat(64);if(kind==='URL')b.url='https://invalid';if(kind==='approval')b.approved=true;if(kind==='coverage')p.asset_bindings.pop();if(kind==='duplicate')p.asset_bindings.push(b);if(kind==='unavailable')p.unavailable_assets=['untrusted'];if(kind==='placeholder')p.asset_bindings[2].render_version='1.0.0';assert.throws(()=>validateScene(p));
});
test('empty v3 room requires no assets',()=>{const p=scene();p.design.furniture=[];p.asset_bindings=[];validateScene(p);assert.ok(productSceneBudget([]).passed);});
test('native product instances share unchanged source resources, unit scale and exact floor anchor',()=>{
 const {model,record,f}=synthetic(),before=JSON.stringify(model.toJSON());
 const a=nativeProductInstance(model,f,record),b=nativeProductInstance(model,{...f,id:'b',x_m:4},record);
 assert.deepEqual(a.scale.toArray(),[1,1,1]);assert.equal(a.userData.scale,1);assert.equal(a.userData.placement,'native_product');
 assert.equal(a.children[0].children[0].children[0].geometry,b.children[0].children[0].children[0].geometry);
 const box=new THREE.Box3().setFromObject(a,true);assert.deepEqual(box.min.toArray(),[1,0,-3]);assert.deepEqual(box.max.toArray(),[2,1,-2]);
 a.position.x+=1;assert.equal(b.position.x,4.5);assert.equal(JSON.stringify(model.toJSON()),before);
});
for(const kind of ['bounds','NaN','index','triangles','texture4096','textureBytes','material','meshCount','morph','skinned'])test(`decoded ${kind} fails`,()=>{
 const {model,record}=synthetic(),mesh=model.children[0];
 if(kind==='bounds')record.native_max[0]=.4;if(kind==='NaN')mesh.geometry.attributes.position.setX(0,NaN);if(kind==='index')mesh.geometry.setIndex([0,1,9]);if(kind==='triangles')record.triangles=2;if(kind==='texture4096')mesh.material.map.image.width=4096;if(kind==='textureBytes')record.texture_bytes=8;if(kind==='material')record.material_count=2;if(kind==='meshCount')record.mesh_instances=2;if(kind==='morph')mesh.morphTargetInfluences=[0];if(kind==='skinned')mesh.isSkinnedMesh=true;assert.throws(()=>verifyDecodedProduct(model,record));
});
test('native path never fits an oversized or offset mesh',()=>{const {model,record,f}=synthetic();assert.throws(()=>nativeProductInstance(model,{...f,width_m:.99},record));record.translation=[0,.01,0];assert.throws(()=>nativeProductInstance(model,f,record));});
test('shared scene budgets count unique bytes/textures once, triangles per instance',()=>{
 const b=[{asset_id:id},{asset_id:id}];assert.deepEqual(productSceneBudget(b),{passed:true,uniqueEncodedBytes:4252440,uniqueTextureBytes:67108860,instantiatedTriangles:85412});
 assert.equal(productSceneBudget(Array.from({length:8},()=>({asset_id:id}))).passed,false);
 const small={...clone(r),bytes:15*1024*1024,texture_bytes:4,triangles:1,images:[{width:1,height:1}]};
 assert.equal(productSceneBudget(['a','b','c','d'].map(asset_id=>({asset_id})),{a:small,b:small,c:small,d:small}).passed,false);
 const large={...small,bytes:1,texture_bytes:67108860};assert.equal(productSceneBudget(['a','b','c'].map(asset_id=>({asset_id})),{a:large,b:large,c:large}).passed,false);
});
for(const patch of [{bytes:15*1024*1024+1},{triangles:100001},{texture_bytes:128*1024*1024+1},{images:[{width:4096,height:1}]}])test(`per-asset budget ${JSON.stringify(patch)} rejected`,()=>{assert.throws(()=>productSceneBudget([{asset_id:'x'}],{x:{...clone(r),...patch}}));});
test('pinned local bytes pass without model acquisition; wrong hashes and stream sizes fail',async()=>{
 const bytes=await readFile(new URL('../../../src/archimind/_viewer_assets/furniture/CharlesArmchair.glb',import.meta.url));
 assert.equal((await boundedProductBytes(new Response(bytes),r)).byteLength,4252440);
 const corrupt=Uint8Array.from(bytes);corrupt[100]^=1;await assert.rejects(boundedProductBytes(new Response(corrupt),r));
 await assert.rejects(boundedProductBytes(new Response(bytes.subarray(0,28)),r));
 await assert.rejects(boundedProductBytes(new Response(bytes,{headers:{'content-length':String(16*1024*1024)}}),r));
 await assert.rejects(boundedProductBytes(new Response('',{status:404}),r));
});
async function fakeGLB(document){const json=new TextEncoder().encode(JSON.stringify(document)),n=Math.ceil(json.length/4)*4,buf=new ArrayBuffer(20+n+12),v=new DataView(buf),a=new Uint8Array(buf);v.setUint32(0,0x46546c67,true);v.setUint32(4,2,true);v.setUint32(8,buf.byteLength,true);v.setUint32(12,n,true);v.setUint32(16,0x4e4f534a,true);a.fill(32,20,20+n);a.set(json,20);v.setUint32(20+n,4,true);v.setUint32(24+n,0x004e4942,true);const sha=Buffer.from(await crypto.subtle.digest('SHA-256',a)).toString('hex');return [a,{...r,bytes:a.length,sha256:sha,images:[]}];}
for(const patch of [{extensionsUsed:['KHR_draco_mesh_compression']},{animations:[{}]},{skins:[{}]},{buffers:[{uri:'external.bin'}]},{nodes:[{extensions:{bad:{}}}]},{meshes:[{primitives:[{targets:[{}]}]}]}])test(`unreviewed GLB semantics rejected ${JSON.stringify(patch)}`,async()=>{const [bytes,record]=await fakeGLB({asset:{version:'2.0'},buffers:[{byteLength:4}],images:[],...patch});await assert.rejects(boundedProductBytes(new Response(bytes),record));});
test('product pool shares ownership, aborts and disposes a late decode once',async()=>{
 let finish,disposals=0,signal;const done=new Promise(resolve=>finish=resolve);
 const pool=createAssetPool(async(key,s)=>{signal=s;return new Promise(resolve=>s.addEventListener('abort',()=>resolve({}),{once:true}));},()=>{disposals++;finish();},0,[id]);
 const a=pool.acquire(id),b=pool.acquire(id);assert.equal(a.promise,b.promise);await Promise.resolve();a.release();b.release();b.release();await done;assert.ok(signal.aborted);assert.equal(disposals,1);assert.equal(pool.loads,1);assert.throws(()=>pool.acquire('unknown'));
});
test('pooled product owns disposal of shared geometry, material and texture once',async()=>{
 const {model}=synthetic();let geometries=0,materials=0,textures=0;const mesh=model.children[0];
 mesh.geometry.addEventListener('dispose',()=>geometries++);mesh.material.addEventListener('dispose',()=>materials++);mesh.material.map.addEventListener('dispose',()=>textures++);
 const {disposeObject}=await import('../src/viewer.js');
 const pool=createAssetPool(async()=>model,disposeObject,0,[id]),a=pool.acquire(id),b=pool.acquire(id);await a.promise;
 a.release();await new Promise(resolve=>setTimeout(resolve,10));assert.equal(geometries,0);b.release();await new Promise(resolve=>setTimeout(resolve,10));assert.deepEqual([geometries,materials,textures],[1,1,1]);
});
