import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSceneManager} from '../src/scene_lifecycle.js';
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
