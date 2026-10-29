import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {toThree} from './geometry.js';
import {disposeObject} from './viewer.js';
import {validateScene,wallQuads,openingQuad,cameraFrame,canonicalVolume} from './room_geometry.js';
import {createAssetPool} from './asset_pool.js';
import {fittedInstance,placeholder,footprint,instanceMetrics,quadGeometry} from './room_objects.js';

import {PRODUCT_ASSETS,boundedProductBytes,verifyDecodedProduct,nativeProductInstance,productSceneBudget} from './product_assets.js';

const ASSET_URL=new URL('./furniture/SheenChair.glb',import.meta.url);
const pool=createAssetPool(async(id,signal)=>{
  const product=PRODUCT_ASSETS[id];
  const url=product?new URL(`./furniture/${product.filename}`,import.meta.url):ASSET_URL;
  const response=await fetch(url,{signal});if(!response.ok)throw Error('Asset unavailable');
  if(product){
    const bytes=await boundedProductBytes(response,product);let model;
    try{model=(await new GLTFLoader().parseAsync(bytes,'')).scene;verifyDecodedProduct(model,product);if(signal.aborted)throw Error('Canceled');return model;}
    catch(error){if(model)disposeObject(model);throw error;}
  }
  const bytes=await response.arrayBuffer();
  if(bytes.byteLength>15*1024*1024||new DataView(bytes).getUint32(0,true)!==0x46546c67)throw Error('Invalid asset');
  const model=(await new GLTFLoader().parseAsync(bytes,'')).scene;
  const size=new THREE.Box3().setFromObject(model).getSize(new THREE.Vector3());
  if(!size.toArray().every(v=>Number.isFinite(v)&&v>0)){disposeObject(model);throw Error('Empty asset');}
  return model;
},disposeObject,250,['sheen-chair',...Object.keys(PRODUCT_ASSETS)]);
function plankTexture(){
  const canvas=document.createElement('canvas');canvas.width=canvas.height=512;const ctx=canvas.getContext('2d');
  let seed=17;const random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
  for(let row=0;row<8;row++){
    const y=row*64;ctx.fillStyle=['#b6a58c','#c1b098','#bdae98'][row%3];ctx.fillRect(0,y,512,64);
    ctx.strokeStyle='#a39580';ctx.strokeRect(0,y,512,64);
    for(let n=0;n<50;n++){ctx.strokeStyle=`rgba(89,67,42,${.015+random()*.05})`;ctx.beginPath();const gy=y+random()*64;ctx.moveTo(0,gy);ctx.bezierCurveTo(160,gy+random()*6,350,gy-random()*6,512,gy);ctx.stroke();}
    ctx.fillStyle='#a99a83';ctx.fillRect((row%2)*256,y,1,64);
  }
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(2,2);return texture;
}
function placeholderLabel(f){
  const c=document.createElement('canvas');c.width=512;c.height=64;const ctx=c.getContext('2d');ctx.fillStyle='#ffffffee';ctx.fillRect(0,0,512,64);ctx.fillStyle='#284951';ctx.font='36px system-ui';ctx.textAlign='center';ctx.fillText(`${f.name.slice(0,24)} · placeholder`,256,42,500);
  const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),depthTest:false,depthWrite:false,toneMapped:false}));sprite.renderOrder=100;sprite.position.set(...toThree([f.x_m+f.width_m/2,f.y_m+f.depth_m/2,f.height_m+.16]));sprite.scale.set(1.85,.32,1);return sprite;
}
export function mountRoomViewer(host,input,{viewState=null}={}){
  const root=document.createElement('section');root.dataset.viewer='realistic-room';
  root.innerHTML=`<div class="stage room-stage"><div class="status" role="status">Loading architectural room…</div></div><div class="toolbar"><button class="reset" type="button">Reset camera</button><label><input type="checkbox" class="front" checked> Front walls</label><label><input type="checkbox" class="outlines" checked> Canonical footprints</label></div><p class="room-info"></p><ul class="objects"></ul><p class="metrics" aria-live="polite"></p>`;
  host.appendChild(root);const stage=root.querySelector('.stage'),status=root.querySelector('.status');
  let renderer,scene,camera,controls,envTarget,resizeObserver,visibility,frame,disposed=false,visible=true,userCamera=false;
  const owned=new THREE.Group(),instances=new THREE.Group(),footprints=new THREE.Group(),walls=new THREE.Group();
  const releases=[];const start=performance.now();
  const cleanup=()=>{
    if(disposed)return;
    disposed=true;cancelAnimationFrame(frame);resizeObserver?.disconnect();visibility?.disconnect();controls?.dispose();
    // GLB instances share resources. Only their pool owns/disposes those resources.
    instances.clear();owned.traverse(o=>o.shadow?.dispose?.());disposeObject(owned);envTarget?.dispose();releases.forEach(release=>release());
    renderer?.dispose();renderer?.forceContextLoss();root.dataset.cleanup='complete';root.remove();
  };
  const fail=()=>{status.textContent='Room viewer unavailable: invalid scene data or WebGL 2 unavailable.';status.dataset.state='error';root.dataset.state='error';};
  try{
    const data=validateScene(input),room=data.design.room,fs=[...data.design.furniture].sort((a,b)=>a.id.localeCompare(b.id));
    const bindings=new Map(data.asset_bindings.map(b=>[b.furniture_id,b.asset_id]));root.dataset.state='loading';
    root.querySelector('.room-info').textContent=`${room.name} · ${room.width_m} × ${room.depth_m} × ${room.ceiling_height_m} m · X east, Y north, Z up. ${data.schema_version===3?'Canonical layout. Only explicitly approved product bindings use native-scale meshes; other objects are labeled placeholders.':'Canonical data; illustrative fitted mesh validity is not established.'}`;
    scene=new THREE.Scene();scene.background=new THREE.Color('#e9edf0');scene.add(owned,instances);owned.add(walls,footprints);
    renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.85;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
    renderer.domElement.setAttribute('aria-label','Experimental room with wall openings, textured chairs and labeled procedural furniture');stage.prepend(renderer.domElement);
    const env=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer);envTarget=pmrem.fromScene(env,.04);scene.environment=envTarget.texture;scene.environmentIntensity=.6;disposeObject(env);pmrem.dispose();
    owned.add(new THREE.HemisphereLight(0xf2f6ff,0xa79a86,1.1));
    const sun=new THREE.DirectionalLight(0xfff4e5,3.0),span=Math.max(room.width_m,room.depth_m,room.ceiling_height_m);
    sun.position.set(room.width_m+2,room.ceiling_height_m+4,2);sun.target.position.set(room.width_m/2,0,-room.depth_m/2);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-span,right:span,top:span,bottom:-span,near:.1,far:span*5});sun.shadow.normalBias=.005;sun.shadow.bias=-.0002;sun.shadow.radius=3;owned.add(sun,sun.target);
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(room.width_m,room.depth_m),new THREE.MeshStandardMaterial({map:plankTexture(),roughness:.82,metalness:0}));floor.rotation.x=-Math.PI/2;floor.position.set(room.width_m/2,-.002,-room.depth_m/2);floor.receiveShadow=true;owned.add(floor);
    const quads=wallQuads(room);
    for(const wall of ['south','east','north','west']){
      const panels=quads.filter(q=>q.wall===wall);if(!panels.length)continue;
      const front=['south','east'].includes(wall);const mesh=new THREE.Mesh(quadGeometry(panels.map(q=>q.points)),new THREE.MeshStandardMaterial({color:'#e1e2dc',roughness:.9,side:THREE.DoubleSide,transparent:true,opacity:front?.2:.85,depthWrite:false}));
      mesh.name=wall;mesh.userData={kind:'wall',wall,panels:panels.length};mesh.castShadow=true;mesh.receiveShadow=true;walls.add(mesh);
    }
    for(const o of [...room.doors,...room.windows]){
      const points=openingQuad(room,o),window=o.sill_height_m!==undefined;
      if(window){const glass=new THREE.Mesh(quadGeometry([points]),new THREE.MeshPhysicalMaterial({color:'#91c2dd',roughness:.08,transparent:true,opacity:.25,side:THREE.DoubleSide,depthWrite:false}));glass.userData={kind:'window',id:o.id};owned.add(glass);}
      const edge=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points.map(v=>new THREE.Vector3(...toThree(v)))),new THREE.LineBasicMaterial({color:window?'#4183a4':'#a2743d'}));edge.userData={kind:window?'window-outline':'door-outline',id:o.id};owned.add(edge);
    }
    root.querySelector('.front').onchange=e=>{for(const mesh of walls.children)if(['south','east'].includes(mesh.name))mesh.visible=e.target.checked;};
    root.querySelector('.outlines').onchange=e=>{footprints.visible=e.target.checked;};
    const bounds=new THREE.Box3(new THREE.Vector3(0,0,-room.depth_m),new THREE.Vector3(room.width_m,room.ceiling_height_m,0));
    for(const f of fs){const b=canonicalVolume(f);bounds.expandByPoint(new THREE.Vector3(...b.min));bounds.expandByPoint(new THREE.Vector3(...b.max));footprints.add(footprint(f));}
    bounds.expandByScalar(.12);
    camera=new THREE.PerspectiveCamera(42,1,.02,200);controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;controls.minDistance=.5;controls.maxDistance=120;controls.maxPolarAngle=Math.PI*.49;
    controls.addEventListener('start',()=>{userCamera=true;});controls.addEventListener('change',()=>{root.dataset.camera=JSON.stringify({position:camera.position.toArray(),target:controls.target.toArray()});});
    const reset=()=>{const damping=controls.enableDamping;controls.enableDamping=false;controls.update();const view=cameraFrame(bounds.min.toArray(),bounds.max.toArray(),camera.aspect,camera.fov);camera.position.set(...view.position);controls.target.set(...view.target);controls.update();controls.enableDamping=damping;userCamera=false;};root.querySelector('.reset').onclick=reset;
    const resize=()=>{const w=Math.max(1,stage.clientWidth),h=Math.max(1,stage.clientHeight);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);if(!userCamera)reset();};resizeObserver=new ResizeObserver(resize);resizeObserver.observe(stage);resize();
    const vector=v=>Array.isArray(v)&&v.length===3&&v.every(x=>Number.isFinite(x)&&Math.abs(x)<10000);
    if(viewState&&vector(viewState.position)&&vector(viewState.target)){
      camera.position.set(...viewState.position);controls.target.set(...viewState.target);controls.update();userCamera=viewState.userCamera===true;
      for(const [selector,key] of [['.front','front'],['.outlines','outlines']])if(typeof viewState[key]==='boolean'){
        const input=root.querySelector(selector);input.checked=viewState[key];input.dispatchEvent(new Event('change'));
      }
    }
    visibility=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;});visibility.observe(stage);
    const animate=()=>{if(disposed)return;frame=requestAnimationFrame(animate);if(visible){controls.update();renderer.render(scene,camera);}};animate();
    (async()=>{
      const sourceModels=new Map(),failed=new Set(data.unavailable_assets),loadsBefore=pool.loads;
      const assetIds=[...new Set(data.asset_bindings.map(b=>b.asset_id).filter(Boolean))];
      const budget=data.schema_version===3?productSceneBudget(data.asset_bindings):null;
      if(budget&&!budget.passed)assetIds.forEach(id=>failed.add(id));
      await Promise.all(assetIds.filter(id=>!failed.has(id)).map(async id=>{const handle=pool.acquire(id);releases.push(handle.release);try{sourceModels.set(id,await handle.promise);}catch{failed.add(id);}}));
      if(disposed)return;
      const metrics=[];let failedInstances=0;
      for(const f of fs){
        const id=bindings.get(f.id),source=sourceModels.get(id);let object,kind;
        if(source){
          try{object=PRODUCT_ASSETS[id]?nativeProductInstance(source,f,PRODUCT_ASSETS[id]):fittedInstance(source,f);kind='textured';instances.add(object);}
          catch{failed.add(id);}
        }
        if(!object){object=placeholder(f);kind=id?'asset_unavailable_placeholder':'procedural_placeholder';owned.add(object,placeholderLabel(f));if(id)failedInstances++;}
        metrics.push(instanceMetrics(object,f,kind));
        const row=document.createElement('li');row.textContent=`${f.name} · ${f.id} · ${f.category} · X/Y (${f.x_m}, ${f.y_m}) · W/D/H ${f.width_m} × ${f.depth_m} × ${f.height_m} m · ${kind.replaceAll('_',' ')}${id&&failed.has(id)?(budget&&!budget.passed?' (scene resource budget exceeded)':' (local asset unavailable or failed qualification)'):PRODUCT_ASSETS[id]?' · native-scale Charles, Sod, CC BY 4.0':''}`;root.querySelector('.objects').appendChild(row);
      }
      renderer.render(scene,camera);
      const geometries=new Set();instances.traverse(o=>{if(o.isMesh)geometries.add(o.geometry);});
      const result={productBudget:budget,instances:metrics,furnitureCount:fs.length,texturedInstances:metrics.filter(m=>m.kind==='textured').length,placeholderInstances:metrics.filter(m=>m.kind!=='textured').length,assetLoadsThisMount:pool.loads-loadsBefore,uniqueAssetIds:assetIds.length,sharedAssetGeometries:geometries.size,loadMs:performance.now()-start,wallPanels:quads.map(q=>({wall:q.wall,left:q.left,right:q.right,bottom:q.bottom,top:q.top})),doors:room.doors,windows:room.windows,roomDimensions:[room.width_m,room.depth_m,room.ceiling_height_m],structuralTriangles:quads.length*2,triangles:metrics.reduce((s,m)=>s+m.triangles,0)};
      root.dataset.metrics=JSON.stringify(result);root.querySelector('.metrics').textContent=`${fs.length} objects · ${result.texturedInstances} textured / ${result.placeholderInstances} placeholder · ${result.assetLoadsThisMount} new GLB load(s) · room setup ${(result.loadMs/1000).toFixed(2)} s`;
      root.dataset.state=failedInstances?'partial':'ready';status.dataset.state=root.dataset.state;status.textContent=failedInstances?'Room loaded; textured asset unavailable. Labeled placeholders shown.':'Experimental room loaded';
    })().catch(()=>{if(!disposed)fail();});
  }catch{fail();}
  cleanup.captureView=()=>!disposed&&camera&&controls?{
    position:camera.position.toArray(),target:controls.target.toArray(),userCamera,
    front:root.querySelector('.front').checked,outlines:root.querySelector('.outlines').checked,
  }:null;
  return cleanup;
}
