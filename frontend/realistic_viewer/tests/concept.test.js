import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import * as THREE from 'three';
import {conceptInstance,validateRecipe} from '../src/concept_assets.js';
import {validateScene} from '../src/room_geometry.js';
import {disposeObject} from '../src/viewer.js';
import {createSceneManager} from '../src/scene_lifecycle.js';
const part={kind:'box',size:[1,1,1],center:[.5,.5,.5],color:'#98734f',roughness:.75};
const recipe={recipe_id:'concept-1',parts:[part]};
const fixtures=JSON.parse(await readFile(new URL('./fixtures/studio-rooms.json',import.meta.url)));
const furniture={id:'studio:1:1',name:'Concept table',category:'table',x_m:1.2,y_m:2,width_m:1.4,depth_m:.7,height_m:.75,rotation_deg:0};
test('concept A/B uses generation-owner camera persistence and releases old geometry',()=>{
  const owner={},view={position:[4,5,6],target:[2,1,-2],userCamera:true,front:false,outlines:false},live=new Set(),received=[];
  const update=createSceneManager((host,data,{viewState})=>{
    received.push(viewState);assert.equal(live.size,0);
    const objects=data.concept_assets.map((r,i)=>conceptInstance(r,data.design.furniture[i]));objects.forEach(o=>live.add(o));
    const dispose=()=>{objects.forEach(o=>{disposeObject(o);live.delete(o);});};dispose.captureView=()=>view;return dispose;
  });
  const first=fixtures[0].payload,second=fixtures[1].payload;
  update({},first,{owner})();update({},second,{owner})();
  assert.equal(live.size,0);assert.equal(received[0],null);assert.deepEqual(received[1],view);
});
for(const kind of ['box','cylinder','cone','sphere'])test(`${kind} is native-scale, grounded and inside canonical volume`,()=>{
  const r={...recipe,parts:[{...part,kind}]},before=JSON.stringify(r),o=conceptInstance(r,furniture),bounds=new THREE.Box3().setFromObject(o);
  const min=[1.2,0,-2.7],max=[2.6,.75,-2];
  for(let i=0;i<3;i++){assert.ok(bounds.min.toArray()[i]>=min[i]-2e-6);assert.ok(bounds.max.toArray()[i]<=max[i]+2e-6);}
  assert.ok(Math.abs(bounds.min.y)<2e-6);assert.equal(o.userData.scale,1);
  assert.equal(JSON.stringify(r),before);disposeObject(o);
});
for(const change of [{kind:'eval'},{uri:'https://x.invalid'},{size:[2,1,1]},{center:[0,.5,.5]},{color:'red'},{size:[NaN,1,1]}])test(`reject ${JSON.stringify(change)}`,()=>{
  assert.throws(()=>validateRecipe({...recipe,parts:[{...part,...change}]}));
});
test('recipe count and material budgets are enforced',()=>{
  assert.throws(()=>validateRecipe({...recipe,parts:Array(65).fill(part)}));
  assert.throws(()=>validateRecipe({...recipe,parts:Array.from({length:9},(_,i)=>({...part,roughness:i/10}))}));
});
test('concept scene cannot smuggle a product binding or unknown recipe',()=>{
  const data={schema_version:4,design:{name:'Concept',room:{id:'room',name:'Room',width_m:5,depth_m:4,ceiling_height_m:2.7,doors:[],windows:[]},furniture:[furniture]},asset_bindings:[{furniture_id:furniture.id,asset_id:null}],unavailable_assets:[],concept_assets:[recipe],concept_bindings:[{furniture_id:furniture.id,recipe_id:'concept-1'}],surfaces:{wall_color:'#ffffff',floor_color:'#98734f'}};
  assert.equal(validateScene(data),data);
  const wrong=structuredClone(data);wrong.asset_bindings[0].asset_id='sheen-chair';assert.throws(()=>validateScene(wrong));
  const missing=structuredClone(data);missing.concept_bindings[0].recipe_id='concept-2';assert.throws(()=>validateScene(missing));
});
for(const fixture of fixtures)test(`whole ${fixture.kind} ${fixture.label} preserves Python geometry and stays within scene budget`,()=>{
  const data=validateScene(fixture.payload),assets=new Map(data.concept_assets.map(r=>[r.recipe_id,r])),bindings=new Map(data.concept_bindings.map(b=>[b.furniture_id,b.recipe_id]));
  let triangles=0,meshes=0;
  for(const f of data.design.furniture){
    const object=conceptInstance(assets.get(bindings.get(f.id)),f);
    assert.equal(object.userData.furnitureId,f.id);
    object.traverse(o=>{if(o.isMesh){triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;meshes++;}});
    disposeObject(object);
  }
  assert.ok(triangles<=300000);assert.ok(meshes<=8*data.design.furniture.length);
});
