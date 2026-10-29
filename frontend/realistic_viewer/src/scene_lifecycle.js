// One renderer per component host. Streamlit can invoke the entrypoint again
// on data changes without unmounting the host; never leave the old scene alive.
export function createSceneManager(mount){
  const entries=new WeakMap();
  const roomSignature=data=>[2,3].includes(data?.schema_version)?JSON.stringify(data.design?.room):null;
  return function update(host,data){
    const signature=JSON.stringify(data),room=roomSignature(data),old=entries.get(host);
    if(old?.signature===signature)return old.cleanup;
    const view=old&&room!==null&&old.room===room?old.dispose.captureView?.():null;
    old?.cleanup();
    const dispose=mount(host,data,{viewState:view});let disposed=false;
    const entry={signature,room,dispose,cleanup(){
      if(disposed)return;disposed=true;dispose();
      if(entries.get(host)===entry)entries.delete(host);
    }};
    entries.set(host,entry);return entry.cleanup;
  };
}
