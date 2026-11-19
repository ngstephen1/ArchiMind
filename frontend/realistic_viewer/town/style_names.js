// Display names for the five style packs; legacy homes map their finish palette.
export const STYLE_NAMES = Object.freeze({
  scandinavian: "Scandinavian",
  modern_classic: "Modern classic",
  industrial_loft: "Industrial loft",
  japandi: "Japandi",
  mid_century: "Mid-century",
});
const LEGACY = Object.freeze({ oak: "scandinavian", sage: "japandi", terracotta: "mid_century" });

export function homeStyle(h) {
  const id = h?.style_pack?.id;
  return id in STYLE_NAMES ? id : LEGACY[h?.palette] || "scandinavian";
}
