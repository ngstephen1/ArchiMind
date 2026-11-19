// Which homes the Town dresses from a style pack, and how. Homes saved before
// style packs carry only `palette` and keep the legacy wall colours untouched.
import { tiledSurface, disposeTiled, STYLE_IDS } from "../src/room_style.js";

export const LEGACY_WALL_COLORS = Object.freeze({
  oak: "#e5d6bc",
  sage: "#bac6ad",
  terracotta: "#d8ab91",
});

export function townSurfaceSource(h) {
  const ref = h?.style_pack;
  if (
    ref && typeof ref === "object" && STYLE_IDS.includes(ref.id) &&
    typeof ref.version === "string" && /^[0-9]+\.[0-9]+\.[0-9]+$/.test(ref.version)
  )
    return { kind: "pack", ref: { id: ref.id, version: ref.version } };
  return { kind: "legacy", wallColor: LEGACY_WALL_COLORS[h?.palette] };
}

// Dress only if the home that requested the pack is still loaded. Returns
// "ready" | "partial" | "unavailable" | "superseded".
export async function dressWhenCurrent(source, current, dress) {
  let pack;
  try {
    pack = await source;
  } catch {
    return current() ? "unavailable" : "superseded";
  }
  if (pack === "superseded" || !pack) return "superseded";
  if (!current()) {
    pack.dispose();
    return "superseded";
  }
  dress(pack);
  return pack.failures.length ? "partial" : "ready";
}

// Interior meshes are unit boxes scaled to size and tagged with
// `userData.surface`. Floors and ceilings tile over X×Z, walls and trim over
// their long side × height. Shared block materials are restored, never disposed.
export function dressTownSurfaces(group, pack) {
  const swaps = [];
  group.traverse((o) => {
    const role = o.isMesh && o.userData.surface;
    const base = role && pack.surface(role);
    if (!base) return;
    const { x, y, z } = o.scale;
    const flat = role === "floor" || role === "ceiling";
    const material = flat ? tiledSurface(base, x, z) : tiledSurface(base, Math.max(x, z), y);
    swaps.push([o, o.material, material]);
    o.material = material;
  });
  return () => {
    // Dispose what this call made, whatever the mesh shows now (the sweep may have swapped it).
    for (const [mesh, original, tiled] of swaps.reverse()) {
      disposeTiled(tiled);
      mesh.material = original;
    }
  };
}

// Status text for a Town home's pack from the world canvas dataset ('' when
// nothing failed): fallback surfaces, failed pack furniture, or no pack at all.
export function townStyleStatus(data) {
  if (data.styleState === "unavailable") return "Style pack unavailable; showing standard finishes.";
  const parts = [];
  if (data.styleState === "partial" && data.styleFailures)
    parts.push("Fallback materials: " + data.styleFailures.split(",").join(", "));
  if (data.styleFurniture) parts.push(data.styleFurniture);
  return parts.join(" · ");
}

// Lighting for a view inside a home: the pack's when it is dressed, else the Town's.
export function interiorLook(packLook, townLook) {
  if (!packLook) return { ...townLook };
  return {
    environment: packLook.environment?.texture || townLook.environment,
    intensity: packLook.intensity,
    exposure: packLook.exposure,
  };
}
