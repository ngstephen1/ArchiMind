import * as THREE from 'three';
import {fitBounds,toThree} from './geometry.js';
import {canonicalVolume} from './room_geometry.js';
export function fittedInstance(source,f){
  const instance=source.clone(true);
  instance.rotation.y=0;instance.updateMatrixWorld(true);
  const bounds=new THREE.Box3().setFromObject(instance);
  const fit=fitBounds(bounds.min.toArray(),bounds.max.toArray(),f);
  instance.scale.multiplyScalar(fit.scale);instance.position.add(new THREE.Vector3(...fit.translation));
  instance.name=f.id;instance.userData={furnitureId:f.id,assetId:'sheen-chair',scale:fit.scale};
  instance.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
  instance.updateMatrixWorld(true);return instance;
}
export function placeholder(f){
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(f.width_m,f.height_m,f.depth_m),new THREE.MeshStandardMaterial({color:'#87a6b1',roughness:.88,metalness:0}));
  mesh.position.set(...toThree([f.x_m+f.width_m/2,f.y_m+f.depth_m/2,f.height_m/2]));
  mesh.name=f.id;mesh.userData={furnitureId:f.id,kind:'procedural_placeholder'};
  mesh.castShadow=true;mesh.receiveShadow=true;return mesh;
}
export function footprint(f){
  const points=[[f.x_m,f.y_m,.006],[f.x_m+f.width_m,f.y_m,.006],[f.x_m+f.width_m,f.y_m+f.depth_m,.006],[f.x_m,f.y_m+f.depth_m,.006]];
  return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points.map(v=>new THREE.Vector3(...toThree(v)))),new THREE.LineBasicMaterial({color:'#197c75'}));
}
export function instanceMetrics(object,f,kind){
  const bounds=new THREE.Box3().setFromObject(object);
  let meshes=0,triangles=0;object.traverse(o=>{if(o.isMesh){meshes++;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
  return {id:f.id,category:f.category,kind,canonical:{x_m:f.x_m,y_m:f.y_m,width_m:f.width_m,depth_m:f.depth_m,height_m:f.height_m},min:bounds.min.toArray(),max:bounds.max.toArray(),scale:object.userData.scale??1,meshes,triangles,volume:canonicalVolume(f)};
}

export function quadGeometry(quads,uvFor=null){
  const positions=[],indices=[],uvs=[];
  for(const points of quads){const offset=positions.length/3;positions.push(...points.flatMap(toThree));if(uvFor)uvs.push(...points.flatMap(uvFor));indices.push(offset,offset+1,offset+2,offset,offset+2,offset+3);}
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));if(uvFor)geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));geometry.setIndex(indices);geometry.computeVertexNormals();return geometry;
}
// UV 0..1 across a whole wall (along it, then up), so a tiled pack surface repeats span/tiling times.
export function wallUV(room,wall){
  const along=['north','south'].includes(wall);
  return ([x,y,z])=>[along?x/room.width_m:y/room.depth_m,z/room.ceiling_height_m];
}
