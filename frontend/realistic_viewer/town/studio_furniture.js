// Original furniture studies. Positions and sizes are room-local metres (east, north, up).
export const studioFinishes = {
  oak: "#9d7555", walnut: "#523b32", moss: "#596a4d", wool: "#d6cbb8",
  brass: "#aa8752", marble: "#e6e0d3", ink: "#343b39", paper: "#e3d9c1",
  clay: "#9e5f4b", glass: "#637873",
};

export function studioFurniture(f) {
  const parts = [];
  function piece(name, finish, x, y, z, w, d, h, radius = 0.012, shape="box") {
    parts.push({name, finish, xyz: [f.x_m+x, f.y_m+y, z], wdh: [w,d,h], radius, shape});
  }
  function legs(x,y,w,d,height,finish) {
    for (const i of [-1,1]) for (const j of [-1,1])
      piece("Tapered foot",finish,x+i*w*.4,y+j*d*.4,height/2,.044,.044,height,.008);
  }
  function table(x,y,w,d,h,finish) {
    legs(x,y,w,d,h-.045,"walnut");
    piece("Tabletop",finish,x,y,h-.023,w,d,.046,.022);
  }
  function seat(x,y,w,d,h,sign,finish) {
    legs(x,y,w,d,.24,"walnut");
    piece("Upholstered deck",finish,x,y,.28,w-.02,d-.02,.15,.055);
    const n=w>1.3?2:1;
    for(let i=0;i<n;i++){
      const cx=x-w/2+w/n*(i+.5);
      piece("Boxed seat cushion",finish,cx,y-sign*.045,.416,w/n-.022,d-.13,.15,.065);
      piece("Back cushion",finish,cx,y+sign*(d/2-.085),(.41+h)/2,w/n-.026,.17,h-.41,.075);
    }
    for(const side of [-1,1])piece("Arm bolster",finish,x+side*(w/2-.055),y,.51,.11,d-.07,.27,.05);
  }
  const w=f.width_m,d=f.depth_m,h=f.height_m,x=w/2,y=d/2;
  if(f.id==="salon-suite"){
    piece("Bound wool rug","paper",x,y,.011,w-.022,d-.022,.022,.008);
    for(const side of [-1,1])
      piece("Woven border","clay",x+side*(w/2-.072),y,.023,.022,d-.14,.002,.001);
    seat(x,d-.40,1.98,.8,.94,1,"wool");
    seat(.41,.34,.78,.68,.82,-1,"moss");
    seat(w-.41,.34,.78,.68,.82,-1,"moss");
    table(x,1.07,1.03,.48,.38,"marble");
    piece("Earthenware vase","clay",x+.25,1.07,.475,.14,.14,.19,0,"sphere");
    piece("Ceramic neck","clay",x+.25,1.07,.56,.052,.052,.064,0,"cylinder");
    for(let i=0;i<5;i++){
      const sx=x+.25+Math.sin(i)*.026, sy=1.07+Math.cos(i)*.03, h=.19+i*.019;
      piece("Botanical stem","walnut",sx,sy,.57+h/2,.006,.006,h,0,"cylinder");
      piece("Olive leaf","moss",sx+.018,sy,.56+h,.065,.025,.039,0,"sphere");
    }
    piece("Art monograph","clay",x-.21,1.08,.399,.23,.18,.038);
  } else if(f.id==="salon-dining"){
    table(x,y,1.58,.76,.75,"walnut");
    for(const dx of [-.44,.44])for(const sign of [-1,1])
      seat(x+dx,y+sign*.72,.46,.46,.84,sign,"moss");
    for (const dx of [-.44,.44]) for (const sign of [-1,1]) {
      const cy=y+sign*.22,cx=x+dx;
      piece("Thrown dinner plate","paper",cx,cy,.763,.225,.225,.026,0,"cylinder");
      piece("Linen napkin","clay",cx,cy,.782,.065,.148,.016,.005);
      piece("Water tumbler","glass",cx+.19,cy-sign*.07,.815,.061,.061,.13,0,"cylinder");
      piece("Brass cutlery","brass",cx-.15,cy,.758,.012,.15,.012,.005);
    }
    piece("Stoneware tray","marble",x,y,.78,.40,.21,.06,.029);
  } else if(f.id==="media-console" || f.id==="bookcase"){
    for(const i of [-1,1])piece("Carcass side","walnut",x+i*(w-.035)/2,y,h/2,.035,d,h);
    const shelves=f.id==="bookcase"?5:2;
    for(let i=0;i<=shelves;i++)piece("Shelf","oak",x,y,.02+(h-.04)*i/shelves,w,d,.04);
    for(let i=0;i<5;i++)piece("Clothbound volume",["paper","moss","clay"][i%3],.1+i*.052,y,.14,.04,.18,.20+i%2*.035);
  } else if(f.category==="bath"){
    piece("Bath plinth","oak",x,y,h*.36,w-.08,d-.08,h*.72);
    piece("Enamel basin","marble",x,y,h*.76,w,d,h*.48,.13);
    piece("Inset basin","glass",x,y,h*.994,w-.15,d-.16,h*.012,.10);
  } else if(f.category==="vanity" || f.category==="counter"){
    piece("Plinth","ink",x,y,.05,w-.08,d-.05,.10);
    piece("Cabinet","moss",x,y,h*.52,w-.02,d-.03,h*.82);
    piece("Honed stone","marble",x,y,h-.023,w,d,.046);
    for(const sign of [-1,1]){
      piece("Oak drawer","oak",x+sign*w*.244,.019,h*.53,w*.48,.03,h*.71);
      piece("Brass pull","brass",x+sign*w*.244,.007,h*.72,w*.12,.014,.018);
    }
    piece("Inset sink","ink",x,y,h-.001,w*.45,d*.66,.002);
  } else if(f.id==="sofa")seat(x,y,w,d,h,1,"wool");
  else if(f.category==="table" || f.id==="work-table")table(x,y,w,d,h,"oak");
  return parts;
}

// Elevated fixtures belong to the architectural layer, outside furniture reservations.
export function salonDetails(part) {
  const {room,furniture}=part.design;
  if(room.id!=="salon")return [];
  const out=[];
  const add=(name,finish,xyz,wdh,shape="box",radius=.008)=>out.push({name,finish,xyz,wdh,shape,radius});
  const {width_m:w,depth_m:d,ceiling_height_m:h}=room;
  for(const z of [.13,h-.11]){
    add("North plaster moulding","paper",[w/2,d-.024,z],[w,.048,.048]);
    add("South plaster moulding","paper",[w/2,.024,z],[w,.048,.048]);
  }
  for(const item of furniture.filter(f=>f.id==="salon-dining")){
    const x=item.x_m+item.width_m/2,y=item.y_m+item.depth_m/2;
    add("Ceiling rose","brass",[x,y,h-.022],[.16,.16,.044],"cylinder");
    for(const dx of [-.40,.40])add("Pendant suspension","ink",[x+dx,y,(2.12+h)/2],[.009,.009,h-2.12],"cylinder");
    add("Pendant arm","brass",[x,y,2.12],[1.12,.025,.025]);
    for(const side of [-1,1])for(const [j,dx] of [-.48,-.16,.16,.48].entries()){
      const cy=y+side*.085;
      add("Opal globe","paper",[x+dx,cy,2.09+(j%2)*.065],[.168,.168,.168],"sphere");
    }
  }
  return out;
}
