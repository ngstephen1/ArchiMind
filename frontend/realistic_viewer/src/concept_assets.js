// Bounded declarative concepts. No eval, generated scripts, assets or provider calls.
import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {makeBuilder} from './spoken_world/parts.js';
import {disposeObject} from './viewer.js';
const color=s=>typeof s==='string'&&/^#[0-9a-fA-F]{6}$/.test(s);
const exact=(v,keys)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===[...keys].sort().join(',');
const vec=(v,positive)=>Array.isArray(v)&&v.length===3&&v.every(n=>typeof n==='number'&&Number.isFinite(n)&&n>=(positive?.001:0)&&n<=1);
export function validateRecipe(recipe){
  if(!exact(recipe,['recipe_id','parts'])||!/^concept-[1-8]$/.test(recipe.recipe_id)||!Array.isArray(recipe.parts)||!recipe.parts.length||recipe.parts.length>64)throw Error('Invalid concept recipe');
  for(const p of recipe.parts){
    if(!exact(p,['kind','size','center','color','roughness'])||!['box','cylinder','cone','sphere'].includes(p.kind)||!vec(p.size,true)||!vec(p.center,false)||!color(p.color)||!Number.isFinite(p.roughness)||p.roughness<0||p.roughness>1)throw Error('Unsupported concept part');
    for(let i=0;i<3;i++)if(p.center[i]-p.size[i]/2 < -1e-9||p.center[i]+p.size[i]/2>1+1e-9)throw Error('Concept part outside reservation');
  }
  if(Math.min(...recipe.parts.map(p=>p.center[1]-p.size[1]/2))>1e-6)throw Error('Concept floats above floor');
  if(new Set(recipe.parts.map(p=>p.color.toLowerCase()+'|'+p.roughness)).size>8)throw Error('Too many concept materials');
  return recipe;
}
export const DESIGNER_CHAIR_SLOT='studio:designer-chair';
export function validateConceptScene(data){
  if(data.schema_version===6){
    const {designer_collection: releases, ...base}=data;
    if(!Array.isArray(releases) || releases.length<1 || releases.length>2 ||
       data.design.furniture.length>12 || data.concept_assets?.length+releases.length+Number(!!base.designer_chair)>8)
      throw Error('Invalid bedroom collection size');
    const slots=new Set();
    for(const binding of releases){
      if(!exact(binding,['concept_id','version','sha256']) ||
         !['upholstered-linen-bed','oak-bedside-lamp'].includes(binding.concept_id) ||
         typeof binding.version!=='string' || !/^\d+\.\d+\.\d+$/.test(binding.version) ||
         typeof binding.sha256!=='string' || !/^[a-f0-9]{64}$/.test(binding.sha256))
        throw Error('Invalid bedroom collection release');
      const slot='studio:'+binding.concept_id;
      const item=data.design.furniture.find(f=>f.id===slot);
      if(slots.has(slot) || !item || item.category!==(binding.concept_id==='upholstered-linen-bed'?'bed':'table') || item.rotation_deg!==0)
        throw Error('Invalid bedroom collection slot');
      slots.add(slot);
    }
    validateRecipesAndChair({...base,schema_version:base.designer_chair?5:4,
      design:{...data.design,furniture:data.design.furniture.filter(f=>!slots.has(f.id))}},true);
    return data;
  }
  return validateRecipesAndChair(data,false);
}
function validateRecipesAndChair(data, allowNativeOnly) {
  if(data.schema_version===5){
    const {designer_chair:binding,...rest}=data;
    const chair=data.design.furniture.find(f=>f.id===DESIGNER_CHAIR_SLOT);
    if(!chair || chair.category!=='chair' || chair.rotation_deg!==0 || !exact(binding,['concept_id','version','sha256']) ||
       typeof binding.concept_id!=='string' || binding.concept_id.length>80 || !binding.concept_id ||
       typeof binding.version!=='string' || binding.version.length>32 || !binding.version ||
       !/^[0-9a-f]{64}$/.test(binding.sha256) || data.design.furniture.length>12 || data.concept_assets?.length>=8 ||
       data.asset_bindings.some(b=>b.asset_id!==null))throw Error('Invalid designer chair scene');
    // The structural validator checked the complete design. Each other object needs its own recipe.
    validateRecipesAndChair({...rest,schema_version:4,design:{...data.design,furniture:data.design.furniture.filter(f=>f!==chair)}},allowNativeOnly);
    return data;
  }
  if(!exact(data,['schema_version','design','asset_bindings','unavailable_assets','concept_assets','concept_bindings','surfaces'])||data.schema_version!==4||!Array.isArray(data.concept_assets)||(!allowNativeOnly && !data.concept_assets.length)||data.concept_assets.length>8||!Array.isArray(data.concept_bindings)||data.concept_bindings.length>12||data.unavailable_assets.length||data.asset_bindings.some(b=>b.asset_id!==null))throw Error('Invalid concept scene');
  if(!exact(data.surfaces,['wall_color','floor_color'])||!Object.values(data.surfaces).every(color))throw Error('Invalid concept surfaces');
  const assets=new Map();
  for(const r of data.concept_assets){validateRecipe(r);if(assets.has(r.recipe_id))throw Error('Duplicate concept');assets.set(r.recipe_id,r);}
  const ids=new Set(),used=new Set();
  for(const b of data.concept_bindings){
    if(!exact(b,['furniture_id','recipe_id'])||!assets.has(b.recipe_id)||ids.has(b.furniture_id)||!data.design.furniture.some(f=>f.id===b.furniture_id)||!/^studio:[1-8]:[1-3]$/.test(b.furniture_id))throw Error('Invalid concept binding');
    ids.add(b.furniture_id);used.add(b.recipe_id);
  }
  if(ids.size!==data.design.furniture.length||used.size!==assets.size)throw Error('Incomplete concept bindings');
  return data;
}
export function conceptInstance(recipe,f){
  validateRecipe(recipe);
  const B=makeBuilder(42,64),group=new THREE.Group(),buckets=new Map();
  try{
    for(const p of recipe.parts){
      const [w,h,d]=[p.size[0]*f.width_m,p.size[1]*f.height_m,p.size[2]*f.depth_m];
      const [x,y,z]=[p.center[0]*f.width_m-f.width_m/2,p.center[1]*f.height_m,p.center[2]*f.depth_m-f.depth_m/2];
      if(p.kind==='box')B.b.box(w,h,d,p.color,x,y-h/2,z,{rough:p.roughness});
      else if(p.kind==='sphere')B.b.sphere(.5,p.color,x,y,z,{sx:w,sy:h,sz:d,rough:p.roughness});
      else B.b.cyl(p.kind==='cone'?0:w/2,w/2,h,p.color,x,y-h/2,z,{sz:d/w,rough:p.roughness});
    }
    for(const p of B.root.ch){
      let geometry;
      if(p.k==='box')geometry=new THREE.BoxGeometry(...p.a).translate(0,p.a[1]/2,0);
      else if(p.k==='cyl')geometry=new THREE.CylinderGeometry(p.a[0],p.a[1],p.a[2],16).translate(0,p.a[2]/2,0);
      else geometry=new THREE.SphereGeometry(p.a[0],16,8);
      const matrix=new THREE.Matrix4().compose(new THREE.Vector3(...p.t),new THREE.Quaternion(),new THREE.Vector3(p.o?.sx??1,p.o?.sy??1,p.o?.sz??1));
      geometry.applyMatrix4(matrix);
      const key=p.c.toLowerCase()+'|'+p.o.rough;
      if(!buckets.has(key))buckets.set(key,{color:p.c,roughness:p.o.rough,geometries:[]});
      buckets.get(key).geometries.push(geometry);
    }
    let triangles=0;
    for(const bucket of buckets.values()){
      const geometry=mergeGeometries(bucket.geometries,false);
      bucket.geometries.forEach(g=>g.dispose());bucket.geometries=[];
      if(!geometry)throw Error('Could not assemble concept');
      const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:bucket.color,roughness:bucket.roughness,metalness:0}));
      mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);triangles+=(geometry.index?.count??geometry.attributes.position.count)/3;
    }
    if(triangles>100000)throw Error('Concept triangle budget exceeded');
    group.position.set(f.x_m+f.width_m/2,0,-f.y_m-f.depth_m/2);group.updateMatrixWorld(true);
    const bounds=new THREE.Box3().setFromObject(group),min=[f.x_m,0,-f.y_m-f.depth_m],max=[f.x_m+f.width_m,f.height_m,-f.y_m],eps=2e-6;
    if(![...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite)||bounds.min.toArray().some((v,i)=>v<min[i]-eps)||bounds.max.toArray().some((v,i)=>v>max[i]+eps)||Math.abs(bounds.min.y)>eps)throw Error('Concept geometry exceeds its reservation');
    group.name=f.id;group.userData={furnitureId:f.id,kind:'procedural_concept',scale:1};return group;
  }catch(error){disposeObject(group);throw error;}
  finally{for(const b of buckets.values())b.geometries.forEach(g=>g.dispose());}
}


// The loader returns an owned, native-scale group centered on its floor anchor.
// Use a parent group so placement preserves authoring/normalization transforms.
export function placeDesignerChair(source, furniture){
  const group=new THREE.Group();
  group.add(source);
  group.position.set(furniture.x_m+furniture.width_m/2,0,-furniture.y_m-furniture.depth_m/2);
  group.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(group,true), measured=box.getSize(new THREE.Vector3());
  const expected=[furniture.width_m,furniture.height_m,furniture.depth_m];
  const tolerance=0.00001;
  if(measured.toArray().some((n,i)=>!Number.isFinite(n)||Math.abs(n-expected[i])>tolerance) ||
     Math.abs(box.min.y)>tolerance || Math.abs(box.min.x-furniture.x_m)>tolerance ||
     Math.abs(box.max.z+furniture.y_m)>tolerance){
    disposeObject(group);
    throw Error('Designer chair does not match the validated reservation');
  }
  group.name=furniture.id;
  group.userData={furnitureId:furniture.id,kind:'designer_concept',scale:1};
  return group;
}
