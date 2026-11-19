// 2D plan colours: today's palette for legacy homes, the pack's plan_theme for
// homes recorded with that exact pack id and version.
export const LEGACY_PLAN_COLORS = Object.freeze({
  site: "#e2d3af",
  room: "#f9f6ec",
  wall: "#46584a",
  furniture: "#b5bfac",
  furnitureStroke: null,
  door: "#dfb855",
  window: "#609aab",
  label: "#233e35",
});

export function planColors(h, manifest) {
  const ref = h?.style_pack;
  const t = manifest?.plan_theme;
  if (!ref || !t || manifest.id !== ref.id || manifest.version !== ref.version) return { ...LEGACY_PLAN_COLORS };
  return {
    site: LEGACY_PLAN_COLORS.site,
    room: t.floor_fill,
    wall: t.wall_stroke,
    furniture: t.furniture_fill,
    furnitureStroke: t.furniture_stroke,
    door: t.door_color,
    window: t.window_color,
    label: t.label_color,
  };
}
