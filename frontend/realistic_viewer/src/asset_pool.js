// A small reference-counted cache. Instance transforms never mutate shared assets.
export function createAssetPool(load,dispose,graceMs=250,allowedIds=['sheen-chair']){
  const allowed=new Set(allowedIds);
  const records=new Map();let loads=0;
  return {
    get loads(){return loads;},
    acquire(id){
      if(!allowed.has(id))throw Error('Untrusted asset ID');
      let record=records.get(id);
      if(!record){
        record={refs:0,timer:null,controller:new AbortController()};records.set(id,record);loads++;
        record.promise=Promise.resolve().then(()=>load(id,record.controller.signal)).catch(error=>{
          if(records.get(id)===record)records.delete(id);throw error;
        });
      }
      record.refs++;clearTimeout(record.timer);let released=false;
      return {promise:record.promise,release(){
        if(released)return;released=true;record.refs--;
        if(record.refs===0)record.timer=setTimeout(()=>{
          if(record.refs!==0)return;
          if(records.get(id)===record)records.delete(id);
          record.controller.abort();record.promise.then(dispose,()=>{});
        },graceMs);
      }};
    },
  };
}
