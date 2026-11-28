import { studioFurniture } from "./studio_furniture.js";
import { PRODUCT_ASSETS } from "../src/product_assets.js";

// Distances are plan measurements from the selected revision, expressed in metres.
function gap(a, b) {
  const dx = Math.max(0, a.x_m - b.x_m - b.width_m, b.x_m - a.x_m - a.width_m);
  const dy = Math.max(0, a.y_m - b.y_m - b.depth_m, b.y_m - a.y_m - a.depth_m);
  return Math.hypot(dx, dy);
}

function deskWindow(room, desk, tabletop = null) {
  if (!desk) return "This room has no recorded desk for a desk-to-window measurement.";
  if (!room.windows.length) return "This room has no recorded window for a desk-to-window measurement.";
  const [centerX, centerY] = tabletop?.xyz ?? [desk.x_m + desk.width_m / 2, desk.y_m + desk.depth_m / 2];
  const measured = room.windows.map(w => {
    const middle = w.offset_m + w.width_m / 2;
    const x = w.wall === "west" ? 0 : w.wall === "east" ? room.width_m : middle;
    const y = w.wall === "south" ? 0 : w.wall === "north" ? room.depth_m : middle;
    return {opening: w, distance: Math.hypot(centerX - x, centerY - y)};
  }).sort((a, b) => a.distance - b.distance);
  const {opening, distance} = measured[0];
  const name = desk.id === "belaya" ? "Belaya" : desk.name;
  return name + " is " + distance.toFixed(2) + " m from the nearest window center on the " + opening.wall +
    " wall, measured center to center in plan. Source: " + room.id + " " + desk.id +
    (tabletop ? " tabletop and window " : " footprint and window ") + opening.id + ". This measures proximity. Placement intent and screen glare have not been established.";
}

export function isSavedDesignQuestion(question) {
  return /^why\b/i.test(question.trim()) &&
    !/\b(?:then|also|redesign|change)\b/i.test(question);
}

export function isUnambiguousSavedDesignQuestion(question) {
  const text = question.trim();
  if (!isSavedDesignQuestion(text)) return false;
  const action = /(?:\b(?:and|but|please|i mean)\s+|,\s*|^)(?:(?:can|could|would|will) you\s+)?(?:please\s+)?(?:move|shift|replace|remove|add|edit|start|make|create|generate|apply|redo|swap)\b/i;
  if (action.test(text)) return false;
  const [, ...details] = text.split(/[.!?;]+(?=\s|$)/).map(part => part.trim()).filter(Boolean);
  return details.every(detail =>
    /^(?:i mean|i(?:'m| am) referring to)\s+the\s+[\p{L}\d][\p{L}\d -]*$/iu.test(detail) &&
    !/\b(?:(?:can|could|would|will) you|move|shift|replace|remove|add|edit|start|make|create|generate|apply|redo|swap)\b/i.test(detail)
  );
}

export function asksChairChange(question) {
  return planQuestions(question.trim().replace(/\s+/g, " ")).some(isBedroomChairComparison);
}

// A room can be named before a furniture noun or as a qualifier after it.
// Keep both identities when comparing alternatives instead of picking the first.
function words(value) {
  return " " + value.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim() + " ";
}

const roomScope = /^(?:in|inside|for) (?:the |my |our )?(bedroom|study|living room|salon|kitchen(?: dining)?|bathroom)\b/i;
const roomMention = /\b(bedroom|study|living room|salon|kitchen|bathroom)\b/i;

function furnitureRooms(question, kind, home) {
  const room = "(bedroom|study|living(?: room)?|salon|bathroom|kitchen(?: dining)?)";
  const noun = kind === "chair" ? "(?:(?:desk|writing)[ -])?chairs?" : "(?:(?:writing[ -])?desks?(?![ -]chairs?\\b)|work[ -]?tables?|writing[ -]suites?)";
  const qualifier = "(?:the |our |my )?";
  const pattern = new RegExp("\\b" + room + "(?:'s|’s)?[ -]+" + noun + "\\b|\\b" + noun + " (?:in|from|inside) " + qualifier + room + "\\b", "gi");
  const rooms = [];
  const unqualified = question.replace(pattern, (_, before, after) => {
    rooms.push((before || after).split(" ")[0].toLowerCase());
    return " ";
  });
  // Look up the remaining proper names in this revision. A room-qualified
  // noun has already been consumed and cannot also match an alias elsewhere.
  const prefix = roomScope.exec(question);
  const scopedNoun = prefix && new RegExp("\\b" + noun + "\\b", "i").test(unqualified);
  if (kind === "chair" && !rooms.length && scopedNoun)
    return [prefix[1].split(" ")[0].toLowerCase()];
  const rest = words(unqualified);
  for (const {design} of home?.rooms ?? []) {
    const named = design.furniture.some(item => item.category === kind &&
      [item.id, item.name].some(label => label && rest.includes(words(label))));
    if (named) rooms.push(design.room.id.split("-")[0]);
  }
  if (!rooms.length && scopedNoun) rooms.push(prefix[1].split(" ")[0].toLowerCase());
  return [...new Set(rooms)];
}

function isBedroomChairComparison(question) {
  const q = question.toLowerCase();
  if (!/\bchair\b/.test(q)) return false;
  const [room] = furnitureRooms(q, "chair");
  if (room ? room !== "bedroom" : /\b(study|living|salon|bathroom|kitchen)\b/.test(q)) return false;
  const comparative = /\b(compare|compared|comparison|difference|changes?|changed)\b/.test(q);
  const timeline = /\b(revisions?|before|after|previously|now|earlier)\b/.test(q);
  if (comparative && timeline) return true;
  if (/\bif\b/.test(q)) return false;
  if (/\bdid\b.*\b(move|shift|change)\b/.test(q)) return true;
  if (/\b(fit|fits|slide|slides|tuck|tucks|under)\b/.test(q)) return false;
  return /\b(revisions|previous revision|changed|moved|displacement)\b/.test(q);
}

export function asksZoningTradeoff(question) {
  return /\b(zoning|gallery|service[- ]core|A\s*\/\s*B)\b/i.test(question) &&
    /\b(compare|between|difference|trade[- ]?offs?)\b/i.test(question);
}

const zoningNames = {gallery: "Gallery", "service-core": "Grouped service core"};

function zoningEvidence(home) {
  const measure = home.evidence?.comparison;
  if (!zoningNames[home.zoning] || !measure) return "";
  const routes = measure.routes.map(row =>
    `${row.room} to ${row.target} via hall ${row.distance_m.toFixed(2)} m`
  );
  const opening = measure.direct_service;
  const connection = opening
    ? `Direct kitchen-to-salon opening ${opening.door_id}, ${opening.crossing_m.toFixed(2)} m checked crossing segment.`
    : "Kitchen and salon connect through the gallery hall.";
  return [zoningNames[home.zoning] + ".", connection,
    routes.length ? "Modeled entrance-to-entrance routes: " + routes.join(", ") + "." : ""]
    .filter(Boolean).join(" ");
}

function zoningComparison(home, manifest, previous) {
  const selected = zoningEvidence(home);
  const peer = previous?.home;
  const compatible = manifest?.home_id === home.id &&
    Boolean(manifest?.project) && manifest.project === previous?.project &&
    Number.isInteger(previous?.revision) && manifest.revision === previous.revision + 1 &&
    peer && home.width === peer.width && home.depth === peer.depth &&
    home.zoning !== peer.zoning;
  const other = compatible ? zoningEvidence(peer) : "";
  if (!selected || !other)
    return [selected, "A side-by-side comparison needs consecutive saved gallery and service-core revisions of this project on the same shell."].filter(Boolean).join(" ");
  return `Revision ${previous.revision}. ${other} Revision ${manifest.revision}. ${selected} The shared opening measurement covers the crossing only.`;
}

function chairChange(home, manifest, previous) {
  if (!manifest || manifest.home_id !== home.id || !previous ||
      manifest.project !== previous.project || manifest.revision !== previous.revision + 1)
    return "A chair comparison needs this saved revision and the preceding revision of the same project.";
  const pair = h => {
    const items = h?.rooms?.find(p => p.design.room.id === "bedroom")?.design.furniture || [];
    return ["desk-chair", "belaya"].map(id => items.find(f => f.id === id));
  };
  const [oldChair, oldDesk] = pair(previous.home);
  const [chair, desk] = pair(home);
  if (!oldChair || !oldDesk || !chair || !desk) return "Both revisions must contain bedroom desk-chair and belaya.";
  const position = f => "(" + f.x_m.toFixed(3) + ", " + f.y_m.toFixed(3) + ") m";
  return "Bedroom desk-chair footprint origin, revision " + previous.revision + ": " + position(oldChair) +
    "; revision " + manifest.revision + ": " + position(chair) +
    ". Displacement: " + Math.hypot(chair.x_m-oldChair.x_m, chair.y_m-oldChair.y_m).toFixed(3) +
    " m. Closest footprint gap to belaya: " + gap(oldChair,oldDesk).toFixed(3) +
    " m before and " + gap(chair,desk).toFixed(3) + " m after. Source: saved bedroom furniture coordinates.";
}

// A question about installation can include several independent evidence requests.
// Bind furniture measurements to the clause that names the item and its room.
const acousticEvidence = /\b(acoustics?|acoustically|nois(?:e|y)|quiet(?:ness|er)?(?!\s+(?:study|bedroom|salon|living room)\b(?!\s+(?:for|during)\b))|privacy|private(?= enough| for (?:calls?|meetings?))|overhear|hear(?! (?:more |something )?(?:why|about|how|from you)\b)|sound(?:proof(?:ing)?|proofed|[- ](?:isolation|transfer|transmission|insulation|proof))?|decibels?)\b/i;
const supplierEvidence = /\b(suppliers?|vendors?|(?:can|could) (?:i|we) (?:order|buy|purchase)|stock availability|retailers?|merchants?|backorders?|lead[- ]times?|in[- ]stock|ship(?:ping|ment)?|delivery(?: dates?)?|availability to purchase|available (?:to (?:order|buy|purchase)|for (?:purchase|delivery))|purchase availability)\b/i;

function asksFurnitureFit(clause) {
  return /\b(fits?|slides?|tucks?|under|underneath|beneath|clearances?)\b/i.test(clause) &&
    /\b(chairs?|desks?|tables?|worktables?)\b/i.test(clause);
}

function planQuestions(question, home) {
  const scoped = question.replace(/\b((?:in|for|inside) (?:the |my |our )?(?:study|bedroom|salon|living room|bathroom|kitchen)),/gi, "$1");
  const clauses = scoped.split(/[?!;]|\.(?!\d)/).flatMap(sentence => {
    const pieces = sentence.trim().split(/(?:,\s*(?:and\s+)?|\s+and\s+)(?=(?:that|whether|can|could|is|are|will|would|does|do|how|what|which|verify)\b)/i);
    const prefix = roomScope.exec(sentence.trim());
    return pieces.map((piece, i) => {
      if (!prefix || !i || roomScope.test(piece)) return piece;
      const chairNeedsScope = /\bchairs?\b/i.test(piece) && asksFurnitureFit(piece)
        && !furnitureRooms(piece, "chair", home).length;
      const lacksSubjectRoom = !roomMention.test(piece) && !furnitureRooms(piece, "desk", home).length;
      return chairNeedsScope || lacksSubjectRoom ? prefix[0] + " " + piece : piece;
    });
  });
  return clauses.map(clause => clause.trim()).filter(clause => clause && (
    (!acousticEvidence.test(clause) && !supplierEvidence.test(clause)) ||
    asksFurnitureFit(clause) || isBedroomChairComparison(clause) ||
    (/\b(distance|how far|proximity|gap|width|height|measure)\b/i.test(clause) && /\b(chairs?|desk|window)\b/i.test(clause)) ||
    /\b(storage|wardrobe|seating capacity|task[- ]light(?:ing)?|reading light|desk lamp|bedside lamp)\b/i.test(clause) ||
    asksZoningTradeoff(clause)
  ));
}

export function explanation(home, question, manifest = null, previous = null) {
  question = question.trim().replace(/\s+/g, " ");
  const acoustic = acousticEvidence.test(question)
    || (/\bquiet\b/i.test(question) && /\b(?:calls?|meetings?)\b/i.test(question));
  const supplier = supplierEvidence.test(question);
  const plan = planQuestions(question, home);
  const answers = [...new Set(plan.map((clause, index) => {
    // An anaphoric fit question cannot establish that the default bedroom pair is intended.
    if (index > 0 && /\b(?:under|beneath|underneath|fit(?:s)? (?:at|with)) (?:it|that|this|them)\b/i.test(clause)
        && !furnitureRooms(clause, "desk", home).length) {
      const desks = furnitureRooms(plan[index - 1], "desk", home);
      if (desks.length !== 1) return "Which desk and chair should I check? Please name their rooms.";
      return explainPlan(home, clause + " at the " + desks[0] + " desk", manifest, previous);
    }
    return explainPlan(home, clause, manifest, previous);
  }))];
  if (acoustic) answers.push("Acoustic performance is unverified. The floor plan records room positions. To assess sound transfer, obtain wall and door assembly ratings or an on-site sound measurement.");
  if (supplier || (plan.some(asksFurnitureFit) && /\b(guarantee|guaranteed|certify|promise|certain|prove)\b/i.test(question))) answers.push("Supplier availability is unknown for this revision. Confirm the item, finish, stock and delivery date with the supplier.");
  return answers.join(" ");
}

function explainPlan(home, question, manifest, previous) {
  const bedroom = home.rooms.find(p => p.design.room.id === "bedroom");
  const {room, furniture} = bedroom.design;
  const get = id => furniture.find(f => f.id === id);
  const desk = get("belaya"), bed = get("queen-bed");
  const q = question.toLowerCase();
  const normalized = words(q);
  if (isBedroomChairComparison(q)) return chairChange(home, manifest, previous);
  if (asksZoningTradeoff(q)) return zoningComparison(home, manifest, previous);
  const comparison = home.evidence?.comparison;
  const mentionedRooms = q.match(/\b(bedroom|study|living|salon|kitchen|bathroom)\b/g) ?? [];
  const requestedRooms = mentionedRooms.length
    ? home.rooms.filter(({design}) =>
        mentionedRooms.includes(design.room.id === "kitchen-dining" ? "kitchen" : design.room.id))
    : home.rooms;
  if (/\b(wardrobes?|closets?|storage)\b/.test(q)) {
    const excludesDedicated = /\b(?:besides|apart from|other than|except(?: for)?|excluding)\s+(?:(?:a|the|any)\s+)?(?:wardrobes?|closets?)\b/.test(q);
    const dedicated = /\b(wardrobes?|closets?)\b/.test(q);
    const isDedicated = item => item.category === "wardrobe" || /\b(wardrobes?|closets?)\b/i.test(item.name);
    const storage = requestedRooms.flatMap(({design}) =>
      design.furniture.filter(item => excludesDedicated
        ? item.category === "storage" && !isDedicated(item)
        : dedicated ? isDedicated(item)
        : ["storage", "wardrobe"].includes(item.category)).map(item =>
        `${design.room.id} ${item.id}, ${item.width_m.toFixed(2)} × ${item.depth_m.toFixed(2)} m in plan`
      )
    );
    return storage.length
      ? "Saved storage reservations: " + storage.join("; ") + ". Interior capacity and door operation need separate measurements."
      : `The requested area has no recorded ${excludesDedicated ? "other storage reservation" : dedicated ? "wardrobe or closet" : "storage reservation"} in this design.`;
  }
  const namedTables = (q.replaceAll("-", " ").match(/\b(breakfast suite|salon dining)\b/g) ?? [])
    .map(name => name.replaceAll(" ", "-"));
  const taskLighting = /\b(task[- ]light(?:ing)?|reading light|desk lamp)\b/.test(q) &&
    !/\b(bedside|nightstand)\b/.test(q);
  const diningEvidence = (parts, tableIds = []) => parts.flatMap(({design}) => {
    const roomId = design.room.id;
    const count = comparison?.dining_places?.[roomId] ??
      (roomId === "salon" ? home.evidence?.salon?.dining_places : undefined);
    const table = design.furniture.find(item => ["salon-dining", "breakfast-suite"].includes(item.id) &&
      (!tableIds.length || tableIds.includes(item.id)));
    return table && Number.isInteger(count) && count > 0
      ? [`${roomId} ${table.id}: ${count} modeled places at one table`]
      : [];
  });
  if ((namedTables.length || /\b(dining|dine|dinner guests)\b/.test(q)) &&
      /\b(seats?|seating|capacity|dine|guests|how many|dining places?|places at)\b/.test(q)) {
    const groups = diningEvidence(namedTables.length ? home.rooms : requestedRooms, namedTables);
    return groups.length
      ? groups.join("; ") + ". Each count applies to its own table."
      : "This design has no recorded seating capacity tied to a dining table.";
  }
  if (!taskLighting && comparison && /\b(why|explain|layout|route|seating)\b/.test(q) &&
      !/\b(desk|window|rug|chair|lamp|oak|daylight|glare|bedside|nightstand)\b/.test(q)) {
    const routes = comparison.routes.map(r => `${r.room} to ${r.target} via hall ${r.distance_m.toFixed(2)} m`);
    const seats = diningEvidence(home.rooms);
    const zoning = zoningEvidence(home);
    return [zoning || (routes.length ? "Measured routes between room entrances · " + routes.join(", ") + "." : ""),
      seats.length ? "Modeled dining · " + seats.join(", ") + "." : "",
      `The layout passed the ${comparison.passage_m.toFixed(2)} m modeled passage check. These measurements describe the plan. Acoustic privacy, glare and clear opening hardware need separate evidence.`].filter(Boolean).join(" ");
  }
  if (/\boak\b/.test(q)) {
    if (!manifest || manifest.home_id !== home.id)
      return "The verified bedroom manifest is unavailable for this design.";
    const matches = [];
    for (const item of manifest.furniture) {
      const source = item.source;
      const record = source?.kind === "catalog" && PRODUCT_ASSETS[source.id];
      if (record && record.sha256 === source.sha256 && record.variant_label?.toLowerCase() === "oak")
        matches.push(item.name + " (" + item.id + "), catalog " + source.id + ", variant_label = Oak");
    }
    const palette = home.palette === "oak" ? " The home also uses an authored oak palette." : "";
    return (matches.length ? "Selected bedroom pieces with catalog oak evidence: " + matches.join("; ") + "." :
      "No selected bedroom piece has a verified oak catalog variant.") + palette +
      " A variant label does not establish solid-oak construction.";
  }
  const study = home.rooms.find(p => p.design.room.id === "study");
  const studyDesks = study?.design.furniture.filter(f => f.category === "desk") ?? [];
  const namedDesks = furnitureRooms(q, "desk", home);
  const namedStudyDesk = (!namedDesks.length || namedDesks.includes("study")) && studyDesks.find(f =>
    [f.name, f.id].some(label => label && normalized.includes(words(label)))
  );
  if (taskLighting) {
    const surfaces = home.rooms.flatMap(({design}) => design.furniture
      .filter(item => namedTables.includes(item.id))
      .map(item => `${design.room.id} ${item.id}`));
    const lightingRooms = namedDesks.length
      ? home.rooms.filter(part => namedDesks.includes(part.design.room.id.split("-")[0]))
      : namedStudyDesk
      ? requestedRooms.filter(part => part === study)
      : /\bbelaya\b/.test(q)
        ? requestedRooms.filter(part => part === bedroom)
        : requestedRooms;
    const workspaces = lightingRooms.flatMap(({design}) => design.furniture
      .filter(item => item.category === "desk" &&
        (!namedStudyDesk || item === namedStudyDesk) &&
        (!/\bbelaya\b/.test(q) || item.id === "belaya"))
      .map(item => `${design.room.id} workspace: ${item.id}`));
    if (!namedTables.length && workspaces.length > 1) return "Which workspace do you mean? " + workspaces.join("; ") + ".";
    const reading = mentionedRooms.includes("living") && lightingRooms.some(({design}) =>
      design.room.id === "living" && design.furniture.some(item => item.id === "reading-suite"));
    return (reading ? "The living reading-suite includes a modeled reading lamp. " : "") +
      (namedTables.length ? (surfaces.length ? `Saved dining surface: ${surfaces.join(", ")}. ` : "") :
        workspaces.length ? `Saved ${workspaces[0]}. ` : "") +
      "To assess task lighting, provide the fixture or a work-surface light measurement. A daylight view alone cannot establish task illuminance or glare.";
  }
  const namedChairs = furnitureRooms(q, "chair", home);
  const fit = asksFurnitureFit(q);
  if (fit && (namedChairs.length > 1 || namedDesks.length > 1))
    return "Which chair and desk pair should I compare first? Named rooms: " + [...new Set([...namedChairs, ...namedDesks])].join(", ") + ".";
  if (fit && namedChairs.length && namedDesks.length && namedChairs[0] !== namedDesks[0]) {
    const target = home.rooms.find(p => p.design.room.id.split("-")[0] === namedDesks[0]);
    const desks = target?.design.furniture.filter(item => item.category === "desk").map(item => item.id) ?? [];
    return "The chair is in the " + namedChairs[0] + " and the requested desk is in the " + namedDesks[0] +
      (desks.length ? " (" + desks.join(", ") + ")" : "") +
      ". To check fit at that desk, identify both items and measure the chair width and arm height, clear width between supports, and floor-to-underside height.";
  }
  const chairRoom = namedChairs[0];
  const chairRooms = namedChairs.length ? namedChairs : mentionedRooms;
  if (/\bchairs?\b/.test(q) && chairRooms.some(id => id !== "study" && id !== "bedroom")) {
    const areas = [...new Set(chairRooms)];
    if (areas.length > 1) return "Which room contains the chair and desk you want to check? Named rooms: " + areas.join(", ") + ".";
    const part = requestedRooms.find(p => p.design.room.id === (areas[0] === "kitchen" ? "kitchen-dining" : areas[0]));
    const items = part?.design.furniture.filter(f => ["chair", "desk"].includes(f.category)) ?? [];
    return "For the " + areas[0] + ", the saved design " + (items.length ? "lists " + items.map(f => f.id).join(", ") : "has no individually identified chair or desk") +
      ". To verify fit, identify both pieces and measure the chair, clear width between supports and floor-to-underside height.";
  }
  if ((/\bstudy\b/.test(q) || namedStudyDesk) && chairRoom !== "bedroom") {
    if (!study) return "This revision has no recorded study.";
    if (chairRoom === "study" && /\b(?:moved?|shifted?|changed?|displacement)\b/.test(q) && !asksFurnitureFit(q))
      return "Revision comparisons track the bedroom desk-chair. A study chair move requires saved positions for that study item in both revisions.";
    if (/chair|knee|slide under/.test(q))
      return "Study chair fit requires a measured chair width and height, the desk's clear width between supports and its floor-to-underside height. These clearances are unavailable for this study.";
    if (/desk|window|daylight|glare/.test(q) || namedStudyDesk) {
      if (!namedStudyDesk && studyDesks.length > 1)
        return "Which study desk? Recorded options: " + studyDesks.map(f => f.id).join(", ") + ".";
      const selected = namedStudyDesk ?? studyDesks[0];
      const usesSuite = selected?.id === "writing-suite" && home.rooms.some(p => p.design.room.id === "salon");
      const tabletop = usesSuite && studioFurniture(selected, study.suite_yaw_deg).find(part => part.name === "Tabletop");
      return deskWindow(study.design.room, selected, tabletop);
    }
    return "Study evidence covers its recorded desk and windows.";
  }
  if (/\bdesk\b/.test(q) && !/bedroom|belaya|chair/.test(q)) {
    const rooms = home.rooms.filter(p => p.design.furniture.some(f => f.category === "desk"));
    if (rooms.length > 1) return "Which desk do you mean? Recorded desks occur in " + rooms.map(p => p.design.room.id).join(" and ") + ".";
  }
  if (/rug/.test(q) && bed) {
    const rug = bedroom.style?.dressing?.find(item => item.kind === "rug");
    if (home.presentation_detail && rug) {
      return `The saved bedroom rug measures ${rug.width_m.toFixed(2)} × ${rug.depth_m.toFixed(2)} m. Its position was checked against the doorway zone. Use those dimensions to shortlist stock sizes and verify rug thickness and door operation on site.`;
    }
    const width = Math.min(room.width_m - .06, bed.x_m + bed.width_m + .58) - Math.max(.06, bed.x_m - .58);
    return "The rug spans " + width.toFixed(2) + " m across the bed. Its nominal side extension is 0.58 m, clipped to leave 0.06 m at the walls.";
  }
  if (/chair/.test(q)) {
    const chair = get("desk-chair");
    if (!chair || !desk) return "This revision has no recorded desk-and-chair pair.";
    if (bedroom.designer_chair) {
      const {name, dimensions_wdh_m} = bedroom.designer_chair;
      return name + " has a native width of " + dimensions_wdh_m[0].toFixed(2) +
        " m. Its reserved footprint is " + chair.width_m.toFixed(2) + " × " +
        chair.depth_m.toFixed(2) + " m. The gap from that reservation to the desk is " +
        gap(chair, desk).toFixed(2) + " m. Under-desk knee clearance has not been measured. Can you provide the clear width between supports and the floor-to-underside height? Source: bedroom desk-chair and belaya footprints.";
    }
    return "The writing chair is " + chair.width_m.toFixed(2) + " m wide. The closest edges of its footprint and the desk are " + gap(chair,desk).toFixed(2) + " m apart. Under-desk knee clearance has not been measured. Can you provide the clear width between supports and the floor-to-underside height? Source: bedroom desk-chair and belaya footprints.";
  }
  if (/lamp|nightstand|bedside/.test(q)) {
    const table = get("bedside-lamp");
    if (!table || !bed) return "This revision has no recorded bed-and-nightstand pair.";
    return "The lamp shares the nightstand’s " + table.width_m.toFixed(2) + " × " + table.depth_m.toFixed(2) + " m footprint. Its nearest edge is " + gap(bed,table).toFixed(2) + " m from the bed.";
  }
  if (/desk|glare|daylight|window/.test(q)) return deskWindow(room, desk);
  return "Ask about the writing desk, window, chair, bedside lamp or rug in this revision.";
}
