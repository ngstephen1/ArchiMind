// Interior orthographic views. North looks along +Y, east along +X.
export function roomElevation(part, wall) {
  const {room,furniture}=part.design;
  const east=wall==="east", span=east?room.depth_m:room.width_m, height=room.ceiling_height_m;
  const canvas=document.createElement("canvas");
  canvas.width=820; canvas.height=310;
  const c=canvas.getContext("2d"), s=Math.min(740/span,224/height), base=268, left=40;
  c.fillStyle="#faf8f3"; c.fillRect(0,0,820,310);
  function rect(x,z,w,h,color){
    c.fillStyle=color;c.fillRect(left+s*x,base-s*(z+h),s*w,s*h);
    c.strokeStyle="#485650";c.strokeRect(left+s*x,base-s*(z+h),s*w,s*h);
  }
  rect(0,0,span,height,"#e9e2d4");
  for(const o of [...room.doors,...room.windows].filter(o=>o.wall===wall))
    rect(o.offset_m,o.sill_height_m||0,o.width_m,o.height_m,o.sill_height_m?"#c6d9da":"#fff");
  const depth=f=>east?f.x_m:f.y_m;
  for(const f of [...furniture].sort((a,b)=>depth(b)-depth(a)))
    rect(east?f.y_m:f.x_m,0,east?f.depth_m:f.width_m,f.height_m,"#beb6a6");
  c.fillStyle="#263b32";c.font="18px sans-serif";
  c.fillText(wall.toUpperCase()+"   "+span.toFixed(2)+" m × "+height.toFixed(2)+" m",left,296);
  const image=new Image(); image.alt=room.name+" "+wall+" dimensioned schematic elevation"; image.src=canvas.toDataURL();
  return image;
}
