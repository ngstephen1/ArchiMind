import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {toThree} from './geometry.js';
import {disposeObject} from './viewer.js';
import {validateScene,wallQuads,openingQuad,cameraFrame,canonicalVolume} from './room_geometry.js';
import {createAssetPool} from './asset_pool.js';
import {fittedInstance,placeholder,footprint,instanceMetrics,quadGeometry,wallUV} from './room_objects.js';
import {queenBed,addWallFinish,contactTexture} from './bedroom_finishes.js';
import {conceptInstance,DESIGNER_CHAIR_SLOT,placeDesignerChair} from './concept_assets.js';
import {loadDesignerChair} from './designer_chair.js';
import {browserTier,configureRenderer,createComposer} from './render_quality.js';
import {loadStylePack,applyLighting} from './style_pack.js';
import {splitStyle,createRoomStyle,tiledSurface,disposeTiled} from './room_style.js';
import {buildDressing} from './dressing.js';
import {createPlanSweep} from './plan_sweep.js';
import {dressFurniture,furnitureFallbackText} from './pack_furniture.js';

import {PRODUCT_ASSETS,boundedProductBytes,verifyDecodedProduct,nativeProductInstance,productSceneBudget,productSceneAdmission} from './product_assets.js';

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
function plankTexture(room){
  const canvas=document.createElement('canvas');canvas.width=canvas.height=512;const ctx=canvas.getContext('2d');
  let seed=17;const random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
  const woods=['#ad8b69','#c4a37d','#b79572','#c7aa87','#bda181'];
  ctx.fillStyle='#87725d';ctx.fillRect(0,0,512,512);
  for(let row=0;row<8;row++){
    const y=row*64;
    const offset=(row*97)%256;
    for(let x=-offset;x<512;x+=256){
      ctx.save();ctx.beginPath();ctx.rect(x+1,y+1,255,63);ctx.clip();
      ctx.fillStyle=woods[Math.floor(random()*woods.length)];ctx.fillRect(x,y,256,64);
      const knot=random()*256,phase=random()*6.28;
      for(let line=0;line<75;line++){
        const gy=random()*64;
        ctx.strokeStyle=`rgba(79,52,33,${.035+random()*.12})`;
        ctx.lineWidth=.5+random()*.65;ctx.beginPath();
        for(let t=0;t<=256;t+=4){
          const ripple=Math.sin(t/49+phase+gy*.04)*1.4;
          const bend=6*Math.exp(-((t-knot)**2)/950)*Math.sin(gy/12);
          if(t===0)ctx.moveTo(x+t,y+gy+ripple+bend);else ctx.lineTo(x+t,y+gy+ripple+bend);
        }
        ctx.stroke();
      }
      ctx.restore();
    }
  }
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(room.width_m/2.8,room.depth_m/1.6);texture.anisotropy=4;return texture;
}
function placeholderLabel(f){
  const c=document.createElement('canvas');c.width=512;c.height=64;const ctx=c.getContext('2d');ctx.fillStyle='#ffffffee';ctx.fillRect(0,0,512,64);ctx.fillStyle='#284951';ctx.font='36px system-ui';ctx.textAlign='center';ctx.fillText(`${f.name.slice(0,24)} · placeholder`,256,42,500);
  const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),depthTest:false,depthWrite:false,toneMapped:false}));sprite.renderOrder=100;sprite.position.set(...toThree([f.x_m+f.width_m/2,f.y_m+f.depth_m/2,f.height_m+.16]));sprite.scale.set(1.85,.32,1);return sprite;
}
export function mountRoomViewer(host,input,{viewState=null}={}){
  const root=document.createElement('section');root.dataset.viewer='realistic-room';
  root.innerHTML=`<div class="stage room-stage"><div class="status" role="status">Loading architectural room…</div></div><div class="toolbar"><button class="reset" type="button">Reset camera</button><button class="interior" type="button">Room-level view</button><label><input type="checkbox" class="front" checked> Front walls</label><label><input type="checkbox" class="outlines" checked> Canonical footprints</label><button class="quality" type="button" hidden>Quality: High</button><label class="sweep-control">Plan <input class="sweep" type="range" min="0" max="100" value="100" aria-label="Plan to room view"> Room</label></div><p class="room-info"></p><ul class="objects"></ul><p class="metrics" aria-live="polite"></p>`;
  host.appendChild(root);const stage=root.querySelector('.stage'),status=root.querySelector('.status');
  let renderer,scene,camera,controls,envTarget,resizeObserver,visibility,frame,disposed=false,visible=true,userCamera=false,composer=null,styleControl=null,sweep=null,baseStatus='',furnitureStatus='';
  // Pack furniture swaps wait until every procedural/product object exists.
  const furnitureObjects=new Map();let markFurnitureReady;const furnitureReady=new Promise(resolve=>{markFurnitureReady=resolve;});
  const owned=new THREE.Group(),instances=new THREE.Group(),footprints=new THREE.Group(),walls=new THREE.Group();
  const releases=[];const start=performance.now();
  const cleanup=()=>{
    if(disposed)return;
    disposed=true;cancelAnimationFrame(frame);resizeObserver?.disconnect();visibility?.disconnect();controls?.dispose();
    // GLB instances share resources. Only their pool owns/disposes those resources.
    sweep?.dispose();sweep=null;styleControl?.dispose();composer?.dispose();instances.clear();owned.traverse(o=>o.shadow?.dispose?.());disposeObject(owned);envTarget?.dispose();releases.forEach(release=>release());
    renderer?.dispose();renderer?.forceContextLoss();root.dataset.cleanup='complete';root.remove();
  };
  const refreshStatus=()=>{if(disposed||!baseStatus)return;const extra=[styleControl?.statusText(),furnitureStatus].filter(Boolean).join(' · ');status.textContent=extra?`${baseStatus} · ${extra}`:baseStatus;};
  const fail=()=>{status.textContent='Room viewer unavailable: invalid scene data or WebGL 2 unavailable.';status.dataset.state='error';root.dataset.state='error';};
  try{
    const {scene:sceneInput,style}=splitStyle(input),data=validateScene(sceneInput),room=data.design.room,fs=[...data.design.furniture].sort((a,b)=>a.id.localeCompare(b.id));
    const conceptRoom=data.schema_version===4 || data.schema_version===5;
    const bindings=new Map(data.asset_bindings.map(b=>[b.furniture_id,b.asset_id]));root.dataset.state='loading';
    const concepts=new Map((data.concept_assets??[]).map(r=>[r.recipe_id,r])),conceptBindings=new Map((data.concept_bindings??[]).map(b=>[b.furniture_id,b.recipe_id]));
    root.querySelector('.room-info').textContent=`${room.name} · ${room.width_m} × ${room.depth_m} × ${room.ceiling_height_m} m · X east, Y north, Z up. ${data.schema_version===3?'Canonical layout. Only explicitly approved product bindings use native-scale meshes; other objects are labeled placeholders.':'Canonical data; illustrative fitted mesh validity is not established.'}`;
    if(conceptRoom){root.dataset.conceptRoom='true';root.querySelector('.room-info').textContent=`${room.name} · Procedural concept room, not catalog products · ${room.width_m} × ${room.depth_m} × ${room.ceiling_height_m} m · reservation-based spatial checks; no product or building-code certification.`;}
    scene=new THREE.Scene();scene.background=new THREE.Color('#e9e2d8');scene.add(owned,instances);owned.add(walls,footprints);
    renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.85;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
    const tier=style?browserTier(viewState?.tier):null;if(style)configureRenderer(renderer,tier);
    renderer.domElement.setAttribute('aria-label',conceptRoom?'Procedural concept room with measured openings and generated furniture':'Experimental room with wall openings, native-scale products and labeled procedural furniture');stage.prepend(renderer.domElement);
    const env=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer);envTarget=pmrem.fromScene(env,.04);scene.environment=envTarget.texture;scene.environmentIntensity=.45;disposeObject(env);pmrem.dispose();
    const hemisphere=new THREE.HemisphereLight(0xf2f6ff,0xa79a86,.8);owned.add(hemisphere);
    const sun=new THREE.DirectionalLight(0xffeddb,2.35),span=Math.max(room.width_m,room.depth_m,room.ceiling_height_m);
    sun.position.set(room.width_m+2,room.ceiling_height_m+4,2);sun.target.position.set(room.width_m/2,0,-room.depth_m/2);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-span,right:span,top:span,bottom:-span,near:.1,far:span*5});sun.shadow.normalBias=.005;sun.shadow.bias=-.0002;sun.shadow.radius=3;owned.add(sun,sun.target);
    const floor=new THREE.Mesh(new THREE.PlaneGeometry(room.width_m,room.depth_m),new THREE.MeshStandardMaterial({map:plankTexture(room),color:data.surfaces?.floor_color??'#ffffff',roughness:.82,metalness:0}));floor.rotation.x=-Math.PI/2;floor.position.set(room.width_m/2,-.002,-room.depth_m/2);floor.receiveShadow=true;owned.add(floor);
    const base=new THREE.Mesh(new THREE.BoxGeometry(room.width_m,.12,room.depth_m),new THREE.MeshStandardMaterial({color:'#90745a',roughness:.8}));
    base.position.set(room.width_m/2,-.068,-room.depth_m/2);base.castShadow=true;owned.add(base);
    const ground=new THREE.Mesh(new THREE.PlaneGeometry(span*12,span*12),new THREE.ShadowMaterial({opacity:.19}));
    ground.rotation.x=-Math.PI/2;ground.position.y=-.13;ground.receiveShadow=true;owned.add(ground);
    if(fs.length){
      let shade;
      for(const f of fs){
        // Clip to the floor at walls; the shadow never floats past a cutaway.
        const x1=Math.max(0,f.x_m-f.width_m*.12),x2=Math.min(room.width_m,f.x_m+f.width_m*1.12);
        const y1=Math.max(0,f.y_m-f.depth_m*.12),y2=Math.min(room.depth_m,f.y_m+f.depth_m*1.12);
        if(x2<=x1||y2<=y1)continue;
        shade??=new THREE.MeshBasicMaterial({color:0x493629,map:contactTexture(),transparent:true,depthWrite:false,opacity:.34});
        const patch=new THREE.Mesh(new THREE.PlaneGeometry(x2-x1,y2-y1),shade);
        patch.rotation.x=-Math.PI/2;patch.position.set((x1+x2)/2,-.001,-(y1+y2)/2);owned.add(patch);
      }
    }
    const quads=wallQuads(room);
    for(const wall of ['south','east','north','west']){
      const panels=quads.filter(q=>q.wall===wall);if(!panels.length)continue;
      const front=['south','east'].includes(wall);const mesh=new THREE.Mesh(quadGeometry(panels.map(q=>q.points),wallUV(room,wall)),new THREE.MeshStandardMaterial({color:data.surfaces?.wall_color??(wall==='north'?'#b2b6a4':'#e4d9cb'),roughness:.9,side:THREE.DoubleSide,transparent:front,opacity:front?.16:1,depthWrite:!front}));
      mesh.name=wall;mesh.userData={kind:'wall',wall,panels:panels.length};mesh.castShadow=!front;mesh.receiveShadow=true;walls.add(mesh);addWallFinish(mesh,room,wall,panels);
    }
    for(const o of [...room.doors,...room.windows]){
      const wallGroup=walls.getObjectByName(o.wall)??owned;const points=openingQuad(room,o),window=o.sill_height_m!==undefined;
      if(window){const glass=new THREE.Mesh(quadGeometry([points]),new THREE.MeshPhysicalMaterial({color:'#91c2dd',roughness:.08,transparent:true,opacity:.25,side:THREE.DoubleSide,depthWrite:false}));glass.userData={kind:'window',id:o.id};wallGroup.add(glass);}
      const edge=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points.map(v=>new THREE.Vector3(...toThree(v)))),new THREE.LineBasicMaterial({color:window?'#4183a4':'#a2743d'}));edge.userData={kind:window?'window-outline':'door-outline',id:o.id};wallGroup.add(edge);
    }
    root.querySelector('.front').onchange=e=>{for(const mesh of walls.children)if(['south','east'].includes(mesh.name))mesh.visible=e.target.checked;};
    root.querySelector('.outlines').onchange=e=>{footprints.visible=e.target.checked;};
    const bounds=new THREE.Box3(new THREE.Vector3(0,0,-room.depth_m),new THREE.Vector3(room.width_m,room.ceiling_height_m,0));
    for(const f of fs){const b=canonicalVolume(f);bounds.expandByPoint(new THREE.Vector3(...b.min));bounds.expandByPoint(new THREE.Vector3(...b.max));footprints.add(footprint(f));}
    bounds.expandByScalar(.12);
    camera=new THREE.PerspectiveCamera(42,1,.02,200);controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;controls.minDistance=.5;controls.maxDistance=120;controls.maxPolarAngle=Math.PI*.49;
    controls.addEventListener('start',()=>{userCamera=true;});controls.addEventListener('change',()=>{root.dataset.camera=JSON.stringify({position:camera.position.toArray(),target:controls.target.toArray()});});
    const reset=()=>{const damping=controls.enableDamping;controls.enableDamping=false;controls.update();const view=cameraFrame(bounds.min.toArray(),bounds.max.toArray(),camera.aspect,camera.fov);camera.position.set(...view.position);controls.target.set(...view.target);controls.update();controls.enableDamping=damping;userCamera=false;};root.querySelector('.reset').onclick=reset;
    const toggle=(selector,on)=>{const control=root.querySelector(selector);control.checked=on;control.dispatchEvent(new Event('change'));};
    if(data.schema_version===3){toggle('.front',false);toggle('.outlines',false);}
    root.querySelector('.interior').onclick=()=>{
      toggle('.front',false);toggle('.outlines',false);
      const eye=Math.min(1.55,room.ceiling_height_m*.65);
      const items=new THREE.Box3();
      for(const f of fs){const box=canonicalVolume(f);items.expandByPoint(new THREE.Vector3(...box.min));items.expandByPoint(new THREE.Vector3(...box.max));}
      if(items.isEmpty())items.copy(bounds);
      items.getCenter(controls.target);controls.target.y=eye*.48;
      // Fit the furnishings at eye height, including in a portrait viewport.
      let distance=Math.max(.5,room.depth_m*.35);
      for(let step=0;step<48;step++){
        camera.position.set(controls.target.x+.32*distance,eye,controls.target.z+distance);
        camera.lookAt(controls.target);camera.updateMatrixWorld();
        const fits=[items.min.x,items.max.x].every(x=>[items.min.y,items.max.y].every(y=>[items.min.z,items.max.z].every(z=>{
          const point=new THREE.Vector3(x,y,z).project(camera);
          return Math.abs(point.x)<.90 && Math.abs(point.y)<.85 && Math.abs(point.z)<1;
        })));
        if(fits)break;
        distance*=1.10;
      }
      controls.update();userCamera=true;
    };
    const resize=()=>{const w=Math.max(1,stage.clientWidth),h=Math.max(1,stage.clientHeight);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h,false);composer?.setSize(w,h);if(!userCamera)reset();};resizeObserver=new ResizeObserver(resize);resizeObserver.observe(stage);resize();
    const vector=v=>Array.isArray(v)&&v.length===3&&v.every(x=>Number.isFinite(x)&&Math.abs(x)<10000);
    if(viewState&&vector(viewState.position)&&vector(viewState.target)){
      camera.position.set(...viewState.position);controls.target.set(...viewState.target);controls.update();userCamera=viewState.userCamera===true;
      for(const [selector,key] of [['.front','front'],['.outlines','outlines']])if(typeof viewState[key]==='boolean'){
        const input=root.querySelector(selector);input.checked=viewState[key];input.dispatchEvent(new Event('change'));
      }
    }
    visibility=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;});visibility.observe(stage);
    const draw=()=>composer?composer.render():renderer.render(scene,camera);
    if(style){
      composer=createComposer(renderer,scene,camera,tier);
      const center=new THREE.Vector3(room.width_m/2,room.ceiling_height_m/2,-room.depth_m/2);
      const dress=(pack,packTier)=>{
        // Swap legacy lighting and finishes for the pack's; the undo restores them exactly.
        const swaps=[],tiled=[];const swap=(mesh,material)=>{swaps.push([mesh,mesh.material]);tiled.push(material);mesh.material=material;};
        const floorSurface=pack.surface('floor');if(floorSurface)swap(floor,tiledSurface(floorSurface,room.width_m,room.depth_m));
        const wallSurface=pack.surface('wall');
        if(wallSurface)for(const mesh of walls.children){
          if(mesh.userData.kind!=='wall')continue;
          const length=['north','south'].includes(mesh.name)?room.width_m:room.depth_m,old=mesh.material;
          const m=tiledSurface(wallSurface,length,room.ceiling_height_m);Object.assign(m,{side:old.side,transparent:old.transparent,opacity:old.opacity,depthWrite:old.depthWrite});swap(mesh,m);
        }
        const trimSurface=pack.surface('trim');
        if(trimSurface){const trims=[];walls.traverse(o=>{if(o.isMesh&&o.material?.name==='trim')trims.push(o);});for(const o of trims)swap(o,tiledSurface(trimSurface,1,1));}
        const legacy={environment:scene.environment,environmentIntensity:scene.environmentIntensity,exposure:renderer.toneMappingExposure};
        hemisphere.visible=sun.visible=false;
        const lights=applyLighting(scene,renderer,pack,packTier,{center,span});
        const decor=buildDressing(owned,style.dressing,pack,packTier);
        let furniture=null,undone=false;
        furnitureReady.then(()=>{if(!undone&&!disposed)furniture=dressFurniture({bindings:style.bindings,furniture:data.design.furniture,pack,objects:furnitureObjects,parent:owned});furniture.ready.then(({failed})=>{if(undone||disposed)return;furnitureStatus=furnitureFallbackText(failed,data.design.furniture);if(failed.length)root.dataset.styleState='partial';refreshStatus();});});
        return()=>{
          undone=true;furniture?.undo();furnitureStatus='';decor.dispose();lights.dispose();hemisphere.visible=sun.visible=true;
          scene.environment=legacy.environment;scene.environmentIntensity=legacy.environmentIntensity;renderer.toneMappingExposure=legacy.exposure;
          for(const [mesh,material] of swaps.reverse())mesh.material=material;tiled.forEach(disposeTiled);
        };
      };
      styleControl=createRoomStyle({style,tier,root,apply:dress,loadPack:({ref,tier:t,isCurrent})=>loadStylePack({baseUrl:new URL('./',import.meta.url).href,ref,tier:t,isCurrent})});
      const quality=root.querySelector('.quality');quality.hidden=false;
      const label=()=>{quality.textContent=`Quality: ${styleControl.tier==='high'?'High':'Low'}`;};label();
      quality.onclick=()=>{
        const next=styleControl.tier==='high'?'low':'high';
        configureRenderer(renderer,next);composer.dispose();composer=createComposer(renderer,scene,camera,next);resize();
        styleControl.setTier(next).then(refreshStatus);label();refreshStatus();
      };
      styleControl.start().then(refreshStatus);
    }
    // Plan ↔ Room is a pure view change over everything in the scene.
    sweep=createPlanSweep({renderer,root:scene});
    const sweepInput=root.querySelector('.sweep');sweepInput.value='100';sweepInput.oninput=()=>sweep.set(Number(sweepInput.value)/100);
    const animate=()=>{if(disposed)return;frame=requestAnimationFrame(animate);if(visible){controls.update();draw();}};animate();
    (async()=>{
      const sourceModels=new Map(),failed=new Set(data.unavailable_assets),loadsBefore=pool.loads;
      const assetIds=[...new Set(data.asset_bindings.map(b=>b.asset_id).filter(Boolean))];
      const budget=data.schema_version===3?productSceneBudget(data.asset_bindings):null;
      const admission=data.schema_version===3?productSceneAdmission(data.asset_bindings):null;
      if(budget&&!budget.passed||admission&&!admission.admitted)assetIds.forEach(id=>failed.add(id));
      await Promise.all(assetIds.filter(id=>!failed.has(id)).map(async id=>{const handle=pool.acquire(id);releases.push(handle.release);try{sourceModels.set(id,await handle.promise);}catch{failed.add(id);}}));
      if(disposed)return;
      const metrics=[];let failedInstances=0,designerLoads=0;
      for(const f of fs){
        const id=bindings.get(f.id),source=sourceModels.get(id);let object,kind;
        if(data.designer_chair && f.id===DESIGNER_CHAIR_SLOT){
          designerLoads++;
          try{
            const model=await loadDesignerChair(data.designer_chair,new URL('./',import.meta.url));
            if(disposed){disposeObject(model);return;}
            object=placeDesignerChair(model,f);kind='designer_concept';owned.add(object);
          }catch{if(disposed)return;failedInstances++;}
        }else if(conceptRoom){
          try{object=conceptInstance(concepts.get(conceptBindings.get(f.id)),f);kind='procedural_concept';owned.add(object);}
          catch{failedInstances++;}
        }
        if(source){
          try{object=PRODUCT_ASSETS[id]?nativeProductInstance(source,f,PRODUCT_ASSETS[id]):fittedInstance(source,f);kind='textured';instances.add(object);}
          catch{failed.add(id);}
        }
        if(!object){const isQueen=data.schema_version===3&&!id&&f.id==='queen-bed'&&f.category==='bed';object=isQueen?queenBed(f):placeholder(f);kind=conceptRoom?'concept_unavailable_placeholder':id?'asset_unavailable_placeholder':'procedural_placeholder';owned.add(object);if(isQueen)footprints.add(placeholderLabel(f));else owned.add(placeholderLabel(f));if(id)failedInstances++;}
        metrics.push(instanceMetrics(object,f,kind));furnitureObjects.set(f.id,[object]);
        const row=document.createElement('li');row.textContent=`${f.name} · ${f.id} · ${f.category} · X/Y (${f.x_m}, ${f.y_m}) · W/D/H ${f.width_m} × ${f.depth_m} × ${f.height_m} m · ${kind.replaceAll('_',' ')}${id&&failed.has(id)?(admission&&!admission.admitted?' (mixed scene not yet qualified)':budget&&!budget.passed?' (scene resource budget exceeded)':' (local asset unavailable or failed qualification)'):PRODUCT_ASSETS[id]?` · native-scale ABO ${PRODUCT_ASSETS[id].product_id}, ${PRODUCT_ASSETS[id].variant_label}, CC BY 4.0`:''}`;root.querySelector('.objects').appendChild(row);
      }
      markFurnitureReady();
      draw();
      const geometries=new Set();instances.traverse(o=>{if(o.isMesh)geometries.add(o.geometry);});
      const result={productBudget:budget,productAdmission:admission,instances:metrics,furnitureCount:fs.length,texturedInstances:metrics.filter(m=>m.kind==='textured').length,conceptInstances:metrics.filter(m=>['procedural_concept','designer_concept'].includes(m.kind)).length,placeholderInstances:metrics.filter(m=>m.kind.includes('placeholder')).length,assetLoadsThisMount:pool.loads-loadsBefore+designerLoads,uniqueAssetIds:assetIds.length,sharedAssetGeometries:geometries.size,loadMs:performance.now()-start,wallPanels:quads.map(q=>({wall:q.wall,left:q.left,right:q.right,bottom:q.bottom,top:q.top})),doors:room.doors,windows:room.windows,roomDimensions:[room.width_m,room.depth_m,room.ceiling_height_m],structuralTriangles:quads.length*2,triangles:metrics.reduce((s,m)=>s+m.triangles,0)};
      root.dataset.metrics=JSON.stringify(result);root.querySelector('.metrics').textContent=`${fs.length} objects · ${result.texturedInstances} textured / ${result.placeholderInstances} placeholder${result.conceptInstances?' / '+result.conceptInstances+' concept':''} · ${result.assetLoadsThisMount} new GLB load(s) · room setup ${(result.loadMs/1000).toFixed(2)} s`;
      root.dataset.state=failedInstances?'partial':'ready';status.dataset.state=root.dataset.state;baseStatus=conceptRoom?(failedInstances?'Concept geometry unavailable. Labeled placeholders shown.':'Procedural concept room loaded'):(failedInstances?'Room loaded; textured asset unavailable. Labeled placeholders shown.':'Experimental room loaded');refreshStatus();
    })().catch(()=>{if(!disposed)fail();});
  }catch{fail();}
  cleanup.captureView=()=>!disposed&&camera&&controls?{
    position:camera.position.toArray(),target:controls.target.toArray(),userCamera,
    front:root.querySelector('.front').checked,outlines:root.querySelector('.outlines').checked,
    ...(styleControl?{tier:styleControl.captureTier()}:{}),
  }:null;
  return cleanup;
}
