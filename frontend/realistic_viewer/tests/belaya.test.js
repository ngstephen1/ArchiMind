import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {webcrypto} from 'node:crypto';
import {PRODUCT_ASSETS,productSceneAdmission,productSceneBudget,boundedProductBytes,compatibleProduct} from '../src/product_assets.js';
globalThis.crypto??=webcrypto;
const desk='abo-b074l4976t-amazon-co-uk',chair='abo-b075x2x4xs-amazon-com',r=PRODUCT_ASSETS[desk];
test('Belaya fixed registry retains native dimensions and inspected resources',()=>{
 assert.equal(r.product_id,'B074L4976T');assert.equal(r.category,'desk');assert.equal(r.variant_label,'Oak');
 assert.deepEqual(r.dimensions,[1.6,.8018731772899628,.7516312003135682]);
 assert.equal(r.bytes,3135676);assert.equal(r.triangles,812);assert.equal(r.texture_bytes,67108860);
 assert.ok(Object.isFrozen(r)&&Object.isFrozen(r.dimensions));
});
test('mixed qualification is distinct from numerical budget failure',()=>{
 const b=[{asset_id:desk},{asset_id:chair}],before=JSON.stringify(b);
 assert.equal(productSceneBudget(b).passed,true);
 assert.equal(productSceneBudget(b).uniqueTextureBytes,128*1024*1024-8);
 assert.deepEqual(productSceneAdmission(b),{admitted:false,reason:'mixed_scene_not_yet_qualified'});
 assert.equal(JSON.stringify(b),before);
 for(const asset_id of [desk,chair,null])assert.equal(productSceneAdmission([{asset_id}]).admitted,true);
});
test('repeated Belaya counts textures once and triangles per instance',()=>{
 assert.deepEqual(productSceneBudget([{asset_id:desk},{asset_id:desk}]),{passed:true,uniqueEncodedBytes:3135676,uniqueTextureBytes:67108860,instantiatedTriangles:1624});
});
test('published dimensions cannot substitute for planning dimensions',()=>{
 const f={category:'desk',rotation_deg:0,x_m:0,y_m:0,width_m:1.6,depth_m:.8,height_m:.75};
 assert.throws(()=>compatibleProduct(f,r));
 [f.width_m,f.depth_m,f.height_m]=r.dimensions;compatibleProduct(f,r);
 f.rotation_deg=90;assert.throws(()=>compatibleProduct(f,r));
});
test('committed Belaya bytes verify and corrupt bytes fail before decoding',async()=>{
 const bytes=await readFile(new URL('../../../src/archimind/_viewer_assets/furniture/BelayaDesk.glb',import.meta.url));
 assert.equal((await boundedProductBytes(new Response(bytes),r)).byteLength,r.bytes);
 bytes[100]^=1;await assert.rejects(()=>boundedProductBytes(new Response(bytes),r));
 await assert.rejects(()=>boundedProductBytes(new Response('',{status:404}),r));
});
