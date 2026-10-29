// Native-scale products are a separate path from illustrative fitBounds().
import * as THREE from 'three';
import {PRODUCT_ASSETS} from './product_registry.js';
export {PRODUCT_ASSETS};
const require=(ok)=>{if(!ok)throw Error('Product qualification or resource check failed');};
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const same=(a,b,e=1e-9)=>a.length===b.length&&a.every((v,i)=>finite(v)&&Math.abs(v-b[i])<=e);
export function compatibleProduct(f,r){
  require(r&&f.category===r.category&&f.rotation_deg===0&&
    [f.x_m,f.y_m].every(finite)&&same([f.width_m,f.depth_m,f.height_m],r.dimensions,0));
}
export function validateProductBindings(data){
  require(Array.isArray(data.asset_bindings)&&Array.isArray(data.unavailable_assets));
  for(const b of data.asset_bindings){
    require(b&&Object.keys(b).sort().join(',')==='asset_id,envelope_sha256,furniture_id,render_version');
    const r=b.asset_id===null?null:PRODUCT_ASSETS[b.asset_id];
    if(b.asset_id===null)require(b.render_version===null&&b.envelope_sha256===null);
    else{
      require(r&&b.render_version===r.render_version&&b.envelope_sha256===r.envelope_sha256);
      compatibleProduct(data.design.furniture.find(f=>f.id===b.furniture_id)??{},r);
    }
  }
  require(new Set(data.unavailable_assets).size===data.unavailable_assets.length&&
    data.unavailable_assets.every(id=>PRODUCT_ASSETS[id]&&data.asset_bindings.some(b=>b.asset_id===id)));
}
export function productSceneBudget(bindings,registry=PRODUCT_ASSETS){
  let bytes=0,textures=0,triangles=0;const ids=new Set();
  for(const b of bindings){if(!b.asset_id)continue;const r=registry[b.asset_id];require(r);
    require(r.bytes>0&&r.bytes<=15*1024*1024&&r.triangles>0&&r.triangles<=100000&&r.texture_bytes>0&&r.texture_bytes<=128*1024*1024&&r.images.every(i=>i.width>0&&i.height>0&&i.width<=2048&&i.height<=2048));
    triangles+=r.triangles;if(!ids.has(b.asset_id)){ids.add(b.asset_id);bytes+=r.bytes;textures+=r.texture_bytes;}
  }
  return {passed:bytes<=50*1024*1024&&textures<=128*1024*1024&&triangles<=300000,uniqueEncodedBytes:bytes,uniqueTextureBytes:textures,instantiatedTriangles:triangles};
}
export async function boundedProductBytes(response,record){
  require(response.ok);const declared=response.headers.get('content-length');
  require(declared===null||Number(declared)<=15*1024*1024);
  const reader=response.body.getReader(),chunks=[];let count=0;
  try{while(true){const {done,value}=await reader.read();if(done)break;count+=value.byteLength;require(count<=15*1024*1024&&count<=record.bytes);chunks.push(value);}}
  catch(error){await reader.cancel();throw error;}
  require(count===record.bytes);const bytes=new Uint8Array(count);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  require(digest===record.sha256);
  // Only pinned reviewed bytes may reach GLTFLoader. Recheck embedded core GLB too.
  const view=new DataView(bytes.buffer);require(count>=28&&view.getUint32(0,true)===0x46546c67&&view.getUint32(4,true)===2&&view.getUint32(8,true)===count);
  const jsonLength=view.getUint32(12,true);require(jsonLength%4===0&&20+jsonLength+8<count&&view.getUint32(16,true)===0x4e4f534a);
  const d=JSON.parse(new TextDecoder().decode(bytes.subarray(20,20+jsonLength)));
  require(d.asset.version==='2.0'&&!(d.extensionsUsed?.length)&&!(d.extensionsRequired?.length)&&!(d.animations?.length)&&!(d.skins?.length));
  const walk=o=>{if(o&&typeof o==='object'){require(!Object.hasOwn(o,'uri')&&!Object.hasOwn(o,'extensions')&&!Object.hasOwn(o,'targets'));Object.values(o).forEach(walk);}};walk(d);
  require(d.buffers.length===1&&d.images.length===record.images.length);
  return bytes.buffer;
}
export function verifyDecodedProduct(model,r){
  let triangles=0,meshes=0;const images=new Set(),materials=new Set();
  model.updateMatrixWorld(true);
  model.traverse(o=>{require(!o.isSkinnedMesh&&!o.morphTargetInfluences);
    if(o.isMesh){meshes++;const p=o.geometry.attributes.position,index=o.geometry.index;require(p&&p.count>0&&p.count<=1000000);
      for(let i=0;i<p.count;i++)require([p.getX(i),p.getY(i),p.getZ(i)].every(finite));
      if(index)for(let i=0;i<index.count;i++)require(Number.isInteger(index.getX(i))&&index.getX(i)>=0&&index.getX(i)<p.count);
      const n=index?.count??p.count;require(n%3===0);triangles+=n/3;
      for(const m of (Array.isArray(o.material)?o.material:[o.material])){require(m);materials.add(m);for(const value of Object.values(m))if(value?.isTexture){require(value.image);images.add(value.image);}}
    }});
  require(meshes===r.mesh_instances&&materials.size===r.material_count&&triangles===r.triangles&&triangles<=100000);
  let textureBytes=0;const sizes=[];
  for(const image of images){const w=image.width,h=image.height;require(Number.isInteger(w)&&Number.isInteger(h)&&w>0&&h>0&&w<=2048&&h<=2048);sizes.push([w,h]);
    let x=w,y=h;while(true){textureBytes+=x*y*4;if(x===1&&y===1)break;x=Math.max(1,Math.floor(x/2));y=Math.max(1,Math.floor(y/2));}}
  require(JSON.stringify(sizes.sort())===JSON.stringify(r.images.map(i=>[i.width,i.height]).sort())&&textureBytes===r.texture_bytes&&textureBytes<=128*1024*1024);
  const box=new THREE.Box3().setFromObject(model,true);require(same(box.min.toArray(),r.native_min)&&same(box.max.toArray(),r.native_max));
  return {triangles,textureBytes,images:images.size,meshes};
}
export function nativeProductInstance(source,f,r){
  compatibleProduct(f,r);verifyDecodedProduct(source,r);
  const instance=new THREE.Group(),anchor=new THREE.Group();anchor.position.set(...r.translation);anchor.add(source.clone(true));instance.add(anchor);
  instance.position.set(f.x_m+f.width_m/2,0,-(f.y_m+f.depth_m/2));
  instance.name=f.id;instance.userData={furnitureId:f.id,assetId:r.asset_id,scale:1,placement:'native_product'};
  instance.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});instance.updateMatrixWorld(true);
  const b=new THREE.Box3().setFromObject(instance,true),lo=[f.x_m,0,-f.y_m-f.depth_m],hi=[f.x_m+f.width_m,f.height_m,-f.y_m];
  require(b.min.toArray().every((v,i)=>v>=lo[i]-1e-6)&&b.max.toArray().every((v,i)=>v<=hi[i]+1e-6)&&Math.abs(b.min.y)<=1e-6);
  return instance;
}
