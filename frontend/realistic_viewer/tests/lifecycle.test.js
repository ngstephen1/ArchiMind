import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSceneManager,selectedSceneOwner} from '../src/scene_lifecycle.js';
import {createAssetPool} from '../src/asset_pool.js';
const scene=(id='a',width=5)=>({schema_version:3,design:{room:{id:'room',width_m:width},furniture:[{id}]},asset_bindings:[],unavailable_assets:[]});
function fixture(){
 const log=[],view={position:[1,2,3],target:[2,0,-2],userCamera:true,front:false,outlines:true};
 const update=createSceneManager((host,data,options)=>{
   const id=data.design?.furniture[0].id??'legacy';log.push({event:'mount',host,id,options});let live=true;
   const dispose=()=>{if(live){live=false;log.push({event:'dispose',id});}};
   dispose.captureView=()=>structuredClone(view);return dispose;
 });return {update,log,view};
}
test('identical reruns retain the same scene and cleanup handle',()=>{const {update,log}=fixture(),host={};const a=update(host,scene()),b=update(host,structuredClone(scene()));assert.equal(a,b);assert.equal(log.length,1);b();a();assert.equal(log.filter(x=>x.event==='dispose').length,1);});
test('A/B replacement disposes before mount and restores camera/cutaway',()=>{const {update,log,view}=fixture(),host={};const a=update(host,scene());update(host,scene('b'));assert.deepEqual(log.map(x=>x.event),['mount','dispose','mount']);assert.deepEqual(log[2].options.viewState,view);a();assert.equal(log.length,3);});
test('changed room and reopening start without stale camera state',()=>{const {update,log}=fixture(),host={};update(host,scene());const close=update(host,scene('b',6));assert.equal(log[2].options.viewState,null);close();update(host,scene('a',6));assert.equal(log.at(-1).options.viewState,null);});
test('new host/generation and independent sessions do not share camera state',()=>{const {update,log}=fixture();const a=update({},scene()),b=update({},scene('b'));assert.equal(log[0].options.viewState,null);assert.equal(log[1].options.viewState,null);a();assert.equal(log.filter(x=>x.event==='dispose').length,1);b();});
test('unmounted callback cannot dispose a replacement scene',()=>{const {update,log}=fixture(),host={};const old=update(host,scene()),current=update(host,scene('b'));old();assert.equal(log.filter(x=>x.event==='dispose').length,1);current();assert.equal(log.filter(x=>x.event==='dispose').length,2);});
test('legacy v1 contract routes through the same lifecycle without room camera',()=>{const {update,log}=fixture(),host={};update(host,{schema_version:1});update(host,scene());assert.equal(log[2].options.viewState,null);});
test('replacement cancels stale async attachment, including late completion',async()=>{
 let finish;const attached=[],update=createSceneManager((host,data)=>{let disposed=false;const done=new Promise(resolve=>{if(data.design.furniture[0].id==='a')finish=resolve;else resolve();});done.then(()=>{if(!disposed)attached.push(data.design.furniture[0].id);});return ()=>{disposed=true;};});
 const host={};update(host,scene());update(host,scene('b'));finish();await Promise.resolve();await Promise.resolve();assert.deepEqual(attached,['b']);
});

test('host teardown and remount under one owner preserves camera and controls',()=>{
 const {update,log,view}=fixture(),owner={},first={isConnected:true},second={isConnected:true};
 const close=update(first,scene(),{owner});close();first.isConnected=false;
 update(second,scene('b'),{owner});
 assert.deepEqual(log.at(-1).options.viewState,view);
 assert.equal(log.filter(x=>x.event==='dispose').length,1);
});

test('stable owner restores a copied snapshot captured before resource disposal',()=>{
 const owner={},view={position:[4,5,6],target:[1,0,-3],userCamera:true,front:false,outlines:false};let received;
 const update=createSceneManager((host,data,{viewState})=>{
   received=viewState;const close=()=>{view.position[0]=999;};close.captureView=()=>view;return close;
 });
 update({},scene(),{owner})();update({},scene('b'),{owner});
 assert.deepEqual(received,{position:[4,5,6],target:[1,0,-3],userCamera:true,front:false,outlines:false});
});
test('settled B A B replacements leave one active scene and release each resource once',()=>{
 const owner={},live=new Set(),disposals=[],state={position:[4,5,6],target:[1,0,-3],userCamera:true,front:false,outlines:false};
 const update=createSceneManager((host,data,{viewState})=>{
   const id=data.design.furniture[0].id;assert.equal(live.size,0);if(disposals.length)assert.deepEqual(viewState,state);
   const resources={id,canvas:{},listener:{},control:{}};live.add(resources);
   const close=()=>{assert.ok(live.delete(resources));disposals.push(id);};close.captureView=()=>state;return close;
 });
 const callbacks=[];for(const id of ['b','a','b']){callbacks.push(update({},scene(id),{owner}));assert.equal(live.size,1);}
 callbacks[0]();callbacks[1]();assert.equal(live.size,1);assert.equal([...live][0].id,'b');callbacks[2]();callbacks[2]();
 assert.equal(live.size,0);assert.deepEqual(disposals,['b','a','b']);
});
test('new room, generation, reopened owner and browser owner start fresh',()=>{
 const {update,log}=fixture(),owner={};update({},scene(),{owner})();
 update({},scene('b',6),{owner});assert.equal(log.at(-1).options.viewState,null);
 for(const fresh of [{},{},{}]){update({},scene(),{owner:fresh});assert.equal(log.at(-1).options.viewState,null);}
});
test('late old-host cleanup cannot overwrite new-host state or resources',()=>{
 const {update,log,view}=fixture(),owner={};const a=update({},scene(),{owner});const b=update({},scene('b'),{owner});
 view.position=[8,9,10];a();b();update({},scene('a'),{owner});
 assert.deepEqual(log.at(-1).options.viewState.position,[8,9,10]);assert.equal(log.filter(x=>x.event==='dispose').length,2);
});
test('detached host or owner cannot supersede the current selected scene',()=>{
 const {update,log}=fixture(),owner={isConnected:true};const close=update({isConnected:true},scene('b'),{owner});
 update({isConnected:false},scene('a'),{owner})();assert.equal(log.length,1);
 update({},scene('a'),{owner:{isConnected:false}})();assert.equal(log.length,1);close();
});
test('late asynchronous completion across replaced hosts cannot attach obsolete A',async()=>{
 const owner={},finish={},live=new Set(),attached=[];
 const update=createSceneManager((host,data)=>{
   const id=data.design.furniture[0].id;let disposed=false;live.add(id);
   new Promise(resolve=>{finish[id]=resolve;}).then(()=>{if(!disposed)attached.push(id);});
   return ()=>{disposed=true;live.delete(id);};
 });
 const a=update({},scene('a'),{owner}),b=update({},scene('b'),{owner});finish.b();finish.a();await Promise.resolve();
 assert.deepEqual(attached,['b']);assert.deepEqual([...live],['b']);a();assert.deepEqual([...live],['b']);b();assert.equal(live.size,0);
});
test('owner handoff preserves pool reuse; after eviction a new request is legitimate',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});let disposed=0;
 // Node 20's timer double rejects null; native clearTimeout treats it as a no-op.
 // Keep real timer IDs delegated to the mock so cancellation remains exercised.
 const clear=globalThis.clearTimeout;t.mock.method(globalThis,'clearTimeout',id=>{if(id!==null)clear(id);});
 const pool=createAssetPool(async()=>({}),()=>{disposed++;}),owner={},handles=[];
 const update=createSceneManager(()=>{const h=pool.acquire('sheen-chair');handles.push(h);return ()=>h.release();});
 update({},scene(),{owner})();update({},scene('b'),{owner})();await Promise.all(handles.map(h=>h.promise));
 assert.equal(pool.loads,1);t.mock.timers.tick(250);await Promise.resolve();assert.equal(disposed,1);
 update({},scene('a'),{owner})();await handles.at(-1).promise;assert.equal(pool.loads,2);
 t.mock.timers.tick(250);await Promise.resolve();assert.equal(disposed,2);
});
test('malformed camera state cannot be restored into a replacement',()=>{
 let restored;const update=createSceneManager((host,data,{viewState})=>{restored=viewState;const close=()=>{};close.captureView=()=>({position:[NaN,0,0],target:[0,0,0]});return close;});
 const owner={};update({},scene(),{owner})();update({},scene('b'),{owner});assert.equal(restored,null);
});
test('failed mount clears stale ownership and allows a later authentic scene',()=>{
 const owner={},live=new Set();const update=createSceneManager((host,data)=>{if(data.bad)throw Error('invalid binding');live.add(host);return ()=>live.delete(host);});
 update({},scene(),{owner});assert.throws(()=>update({}, {...scene('b'),bad:true},{owner}),/invalid binding/);assert.equal(live.size,0);
 update({},scene('b'),{owner})();assert.equal(live.size,0);
});
test('entrypoint finds only the explicit parent owner, including shadow hosts',()=>{
 const owner={classList:['stVerticalBlock','st-key-selected-realistic-owner-12'],parentElement:null};
 const element={classList:[],parentElement:owner},shadow={host:element};assert.equal(selectedSceneOwner(shadow),owner);
 const standalone={parentElement:{classList:['st-key-selected_design_3d'],parentElement:null}};assert.equal(selectedSceneOwner(standalone),standalone);
});
