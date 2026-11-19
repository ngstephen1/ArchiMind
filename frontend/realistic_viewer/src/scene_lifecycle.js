// Selected layouts have a generation-scoped parent that outlives disposable
// Streamlit hosts. Standalone callers retain their original host-local lifetime.
export function selectedSceneOwner(host){
  for(let element=(host.host??host).parentElement;element;element=element.parentElement){
    if([...element.classList].some(name=>/^st-key-selected-realistic-owner-[0-9]+$/.test(name)))return element;
  }
  return host;
}
function snapshot(dispose){
  const value=dispose?.captureView?.();
  const vector=v=>Array.isArray(v)&&v.length===3&&v.every(x=>Number.isFinite(x)&&Math.abs(x)<10000);
  if(!value||!vector(value.position)||!vector(value.target))return null;
  return {position:[...value.position],target:[...value.target],userCamera:value.userCamera===true,
    front:value.front===true,outlines:value.outlines===true,
    ...(['high','low'].includes(value.tier)?{tier:value.tier}:{})};
}
export function createSceneManager(mount){
  const entries=new WeakMap();
  const roomSignature=data=>[2,3,4,5,6].includes(data?.schema_version)?JSON.stringify(data.design?.room):null;
  return function update(host,data,{owner=host}={}){
    // An obsolete entrypoint must not displace a current scene on a live owner.
    if(host.isConnected===false||owner.isConnected===false)return ()=>{};
    const signature=JSON.stringify(data),room=roomSignature(data),old=entries.get(owner);
    if(old?.active?.host===host&&old.active.signature===signature)return old.active.cleanup;
    const view=old&&room!==null&&old.room===room?
      (old.active?snapshot(old.active.dispose):old.view):null;
    old?.active?.cleanup();
    const record={room,view:null,active:null};
    const active={host,signature,dispose:null,cleanup:null,disposed:false};
    active.cleanup=()=>{
      if(active.disposed)return;
      active.disposed=true;
      try{
        if(entries.get(owner)===record&&record.active===active){
          record.view=owner!==host&&room!==null?snapshot(active.dispose):null;
          record.active=null;
          if(owner===host||room===null)entries.delete(owner);
        }
      }finally{
        try{active.dispose?.();}finally{active.dispose=null;active.host=null;}
      }
    };
    // The current record owns only the latest mount; old callbacks cannot write
    // into it. After cleanup it holds scalar/array view data only, never a scene.
    entries.set(owner,record);
    try{active.dispose=mount(host,data,{viewState:view});record.active=active;}
    catch(error){entries.delete(owner);throw error;}
    return active.cleanup;
  };
}
