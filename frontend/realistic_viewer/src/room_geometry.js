import {toThree} from './geometry.js';
const keys=(o,names)=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join(',')===names.sort().join(',');
const text=v=>typeof v==='string'&&v.trim().length>0&&v.length<=256;
const finite=(v,lo,hi)=>typeof v==='number'&&Number.isFinite(v)&&v>=lo&&v<=hi;
export function validateScene(data) {
  if(!keys(data,['schema_version','design','asset_bindings','unavailable_assets'])||data.schema_version!==2||
    !keys(data.design,['room','furniture','name'])||!keys(data.design.room,['id','name','width_m','depth_m','ceiling_height_m','doors','windows']))throw Error('Invalid architectural scene');
  const {room:r,furniture:fs,name}=data.design;
  if(!(name===null||text(name))||![r.id,r.name].every(text)||![r.width_m,r.depth_m,r.ceiling_height_m].every(v=>finite(v,.1,20))||
    !Array.isArray(r.doors)||!Array.isArray(r.windows)||r.doors.length+r.windows.length>128||!Array.isArray(fs)||fs.length>24||
    !Array.isArray(data.asset_bindings)||!Array.isArray(data.unavailable_assets))throw Error('Unsupported scene limits');
  const ids=new Set([r.id]);
  for(const [kind,openings] of [['door',r.doors],['window',r.windows]])for(const o of openings){
    const fields=['id','wall','offset_m','width_m','height_m',...(kind==='window'?['sill_height_m']:[])];
    if(!keys(o,fields)||!text(o.id)||ids.has(o.id)||!['north','south','east','west'].includes(o.wall))throw Error('Invalid opening');
    ids.add(o.id);const length=['north','south'].includes(o.wall)?r.width_m:r.depth_m;
    if(!finite(o.offset_m,0,length)||!finite(o.width_m,Number.MIN_VALUE,length)||!finite(o.height_m,Number.MIN_VALUE,r.ceiling_height_m)||
      (kind==='window'&&!finite(o.sill_height_m,0,r.ceiling_height_m))||o.offset_m+o.width_m>length+1e-10||
      (o.sill_height_m??0)+o.height_m>r.ceiling_height_m+1e-10)throw Error('Opening exceeds room');
  }
  for(const f of fs){
    if(!keys(f,['id','name','category','x_m','y_m','width_m','depth_m','height_m','rotation_deg'])||![f.id,f.name,f.category].every(text)||ids.has(f.id)||
      f.rotation_deg!==0||![f.x_m,f.y_m].every(v=>finite(v,-20,20))||![f.width_m,f.depth_m,f.height_m].every(v=>finite(v,.05,10)))throw Error('Unsupported furniture; only rotation 0');
    ids.add(f.id);
  }
  const assigned=new Map();
  for(const b of data.asset_bindings){
    if(!keys(b,['furniture_id','asset_id'])||assigned.has(b.furniture_id)||!fs.some(f=>f.id===b.furniture_id)||![null,'sheen-chair'].includes(b.asset_id))throw Error('Untrusted asset binding');
    if(b.asset_id&&fs.find(f=>f.id===b.furniture_id).category!=='chair')throw Error('Asset category mismatch');
    assigned.set(b.furniture_id,b.asset_id);
  }
  if(assigned.size!==fs.length||new Set(data.unavailable_assets).size!==data.unavailable_assets.length||data.unavailable_assets.some(id=>id!=='sheen-chair'||![...assigned.values()].includes(id)))throw Error('Invalid asset state');
  return data;
}
export function wallPoint(room,wall,along,z){
  if(wall==='south')return [along,0,z];
  if(wall==='north')return [along,room.depth_m,z];
  if(wall==='west')return [0,along,z];
  if(wall==='east')return [room.width_m,along,z];
  throw Error('Unsupported wall');
}
export function openingRectangle(room,opening){
  const length=['north','south'].includes(opening.wall)?room.width_m:room.depth_m;
  const left=opening.offset_m,right=Math.min(length,left+opening.width_m),bottom=opening.sill_height_m??0,top=Math.min(room.ceiling_height_m,bottom+opening.height_m);
  if(!(right>left&&top>bottom))throw Error('Collapsed opening');
  return {left,right,bottom,top};
}
export function openingQuad(room,opening){
  const {left,right,bottom,top}=openingRectangle(room,opening);
  return [[left,bottom],[right,bottom],[right,top],[left,top]].map(([a,z])=>wallPoint(room,opening.wall,a,z));
}
export function wallQuads(room){
  const result=[];
  for(const wall of ['south','east','north','west']){
    const length=['north','south'].includes(wall)?room.width_m:room.depth_m;
    const openings=[...room.doors,...room.windows].filter(o=>o.wall===wall).map(o=>openingRectangle(room,o));
    const cuts=[...new Set([0,length,...openings.flatMap(o=>[o.left,o.right])])].sort((a,b)=>a-b);
    for(let i=1;i<cuts.length;i++){
      const left=cuts[i-1],right=cuts[i];if(!(right>left))continue;
      const active=openings.filter(o=>o.left<=left&&right<=o.right).sort((a,b)=>a.bottom-b.bottom||a.top-b.top);
      let cursor=0;
      const panel=(low,high)=>{if(high>low)result.push({wall,left,right,bottom:low,top:high,points:[[left,low],[right,low],[right,high],[left,high]].map(([a,z])=>wallPoint(room,wall,a,z))});};
      for(const o of active){panel(cursor,o.bottom);cursor=Math.max(cursor,o.top);}
      panel(cursor,room.ceiling_height_m);
    }
  }
  return result;
}
// Fit all canonical volume corners in the perspective frustum, including narrow views.
export function cameraFrame(min,max,aspect,fov=42){
  if(!finite(aspect,.05,100)||min.some((v,i)=>!Number.isFinite(v)||!Number.isFinite(max[i])||max[i]<=v))throw Error('Invalid framing bounds');
  const center=min.map((v,i)=>(v+max[i])/2);
  const norm=v=>{const n=Math.hypot(...v);return v.map(x=>x/n);},dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
  const d=norm([.95,.72,1.05]),right=norm([d[2],0,-d[0]]),up=[d[1]*right[2],d[2]*right[0]-d[0]*right[2],-d[1]*right[0]];
  const vertical=Math.tan(fov*Math.PI/360),horizontal=vertical*aspect;
  let distance=0;
  for(const x of [min[0],max[0]])for(const y of [min[1],max[1]])for(const z of [min[2],max[2]]){
    const q=[x-center[0],y-center[1],z-center[2]];
    distance=Math.max(distance,dot(q,d)+Math.max(Math.abs(dot(q,right))/horizontal,Math.abs(dot(q,up))/vertical));
  }
  distance*=1.12;
  return {target:center,position:center.map((v,i)=>v+d[i]*distance)};
}
export function canonicalVolume(f){
  return {min:toThree([f.x_m,f.y_m+f.depth_m,0]),max:toThree([f.x_m+f.width_m,f.y_m,f.height_m])};
}
