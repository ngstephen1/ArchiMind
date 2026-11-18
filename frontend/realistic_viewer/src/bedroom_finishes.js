import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {toThree} from './geometry.js';
import {openingRectangle,wallPoint} from './room_geometry.js';

// A small repeatable height field gives the bedding a woven surface under side light.
function wovenSurface() {
  const size=64, pixels=new Uint8Array(size*size*4);
  for(let y=0;y<size;y++) for(let x=0;x<size;x++){
    const warp=Math.cos(x*Math.PI/2), weft=Math.cos(y*Math.PI/2);
    const over=((x>>2)+(y>>2))%2;
    const value=Math.round(145+55*(over?warp:weft)+20*(over?weft:warp));
    pixels.set([value,value,value,255],4*(y*size+x));
  }
  const weave=new THREE.DataTexture(pixels,size,size);
  weave.wrapS=weave.wrapT=THREE.RepeatWrapping;
  weave.magFilter=THREE.LinearFilter; weave.minFilter=THREE.LinearMipmapLinearFilter;
  weave.generateMipmaps=true; weave.repeat.set(9,12); weave.needsUpdate=true;
  return weave;
}

// Draped top with rounded side drops, stitched channels and shallow diagonal folds.
function quilt(width, height, depth, material) {
  const cols=64, rows=56, positions=[], uv=[], indices=[];
  for(let j=0;j<=rows;j++) for(let i=0;i<=cols;i++){
    const u=i/cols,v=j/rows;
    const edge=Math.pow(Math.abs(2*u-1),16);
    const foot=Math.pow(v,14);
    const crease=Math.sin(14*u+4*Math.sin(5*v))*Math.sin(11*v+3*u);
    const channel=Math.pow(Math.cos(Math.PI*(7*u+.10*Math.sin(5*v))),12);
    const y=.747-.23*edge-.105*foot+.023*crease-.015*channel;
    positions.push((u-.5)*width*.997,height*y,depth*(-.158+.655*v));
    uv.push(u,v);
    if(i<cols && j<rows){
      const n=j*(cols+1)+i;
      indices.push(n,n+cols+1,n+1,n+1,n+cols+1,n+cols+2);
    }
  }
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
  geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  geometry.setIndex(indices);geometry.computeVertexNormals();
  const cover=new THREE.Mesh(geometry,material);
  cover.castShadow=cover.receiveShadow=true;
  return cover;
}

// A presentation model for the explicitly selected procedural queen template.
// Coordinates below are fractions of its validated reservation (origin at floor centre).
export function queenBed(f) {
  const group = new THREE.Group();
  const material = (color, roughness) => new THREE.MeshStandardMaterial({color, roughness});
  const oak = material('#76503a', .62);
  const linen = material('#e9dec9', .96);
  const duvet = material('#9faea1', .98);
  const throwFabric = material('#a05e40', .96);
  const stitch = material('#ddbb93', 1);
  const weave=wovenSurface();
  for(const fabric of [linen,duvet,throwFabric]){
    fabric.bumpMap=weave;fabric.bumpScale=.0012;
  }
  const {width_m:w, height_m:h, depth_m:d} = f;
  function layer(mat, sx, sy, sz, x, y, z, radius) {
    const size = [sx*w, sy*h, sz*d];
    const geometry = new RoundedBoxGeometry(...size, 2, Math.min(radius, ...size.map(v=>v/2)));
    const part = new THREE.Mesh(geometry, mat);
    part.position.set(x*w,y*h,z*d);
    part.castShadow = part.receiveShadow = true;
    group.add(part);
    return part;
  }
  layer(oak,.83,.16,.86,0,.08,0,.015);
  layer(oak,1,.17,1,0,.22,0,.025);
  layer(linen,.985,.34,.98,0,.47,.005,.065);
  layer(oak,1,1,.037,0,.5,-.4815,.025);
  duvet.side=THREE.DoubleSide;
  group.add(quilt(w,h,d,duvet));
  layer(linen,.975,.052,.077,0,.741,-.12,.021);
  for (const x of [-.245,.245]) {
    const pillow = layer(linen,.445,.22,.19,x,.72,-.30,.06);
    pillow.rotation.y = x * .12;
  }
  layer(throwFabric,.91,.06,.185,-.012,.766,.29,.024);
  for (const z of [.212,.22,.36,.368]) layer(stitch,.88,.006,.003,-.012,.797,z,.001);
  group.position.set(f.x_m+w/2,0,-f.y_m-d/2);
  group.name=f.id;
  group.userData={furnitureId:f.id,kind:'procedural_placeholder'};
  return group;
}

// Attach trim to its wall so the cutaway hides its frames as well as its panels.
export function addWallFinish(parent, room, wall, panels) {
  const trim = new THREE.MeshStandardMaterial({color:'#e4d8c7',roughness:.66});
  const horizontal = wall==='north' || wall==='south';
  function board(along, height, length, depth, thickness) {
    if (length<=0 || thickness<=0) return;
    const size = horizontal ? [length, thickness, depth] : [depth, thickness, length];
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size),trim);
    mesh.position.set(...toThree(wallPoint(room,wall,along,height)));
    mesh.receiveShadow=true;
    parent.add(mesh);
  }
  for (const p of panels.filter(p=>p.bottom===0)) {
    const height=Math.min(.09,p.top);
    board((p.left+p.right)/2,height/2,p.right-p.left,.035,height);
  }
  for (const opening of [...room.doors,...room.windows].filter(o=>o.wall===wall)) {
    const {left,right,bottom,top}=openingRectangle(room,opening);
    const width=right-left,height=top-bottom;
    const rail=Math.min(.045,width/8,height/8);
    for(const side of [left,right]) board(side,(bottom+top)/2,rail,.08,height);
    board((left+right)/2,top,width+rail,.08,rail);
    if(opening.sill_height_m!==undefined){
      board((left+right)/2,bottom,width+rail,.14,rail);
      board((left+right)/2,(bottom+top)/2,rail*.55,.04,height);
    }
  }
}

// Broad ambient contact complements the directional shadows under each instance.
export function contactTexture() {
  const size=64, pixels=new Uint8Array(size*size*4);
  for(let y=0;y<size;y++) for(let x=0;x<size;x++) {
    const dx=Math.abs((x+.5)*2/size-1),dy=Math.abs((y+.5)*2/size-1);
    const edge=Math.min(1,Math.pow(dx**4+dy**4,.25));
    const fade=1-edge*edge*(3-2*edge);
    pixels.set([255,255,255,Math.round(255*fade)],4*(y*size+x));
  }
  const map=new THREE.DataTexture(pixels,size,size);
  map.magFilter=THREE.LinearFilter;map.minFilter=THREE.LinearFilter;
  map.needsUpdate=true;
  return map;
}
