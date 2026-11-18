import { build } from "esbuild";
import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, readdir, unlink, writeFile } from "node:fs/promises";
const src = new URL("./", import.meta.url),
  out = new URL("../../../dist/town/", src);
await mkdir(new URL("assets/", out), { recursive: true });
await build({
  entryPoints: [new URL("app.js", src).pathname],
  outfile: new URL("town.js", out).pathname,
  bundle: true,
  format: "esm",
  minify: true,
  target: "es2022",
  legalComments: "linked",
});
for (const f of ["index.html", "town.css"])
  await copyFile(new URL(f, src), new URL(f, out));
await copyFile(
  new URL("materials/wood-floor.jpg", src),
  new URL("assets/wood-floor.jpg", out),
);
const materialDir = new URL("materials/", src);
const surfaceManifest = await readFile(new URL("bedroom-sources.json", materialDir));
for (const entry of JSON.parse(surfaceManifest)) {
  if (!/^[a-z0-9-]+\.(jpg|hdr)$/.test(entry.local)) throw Error("Invalid surface filename");
  const local = await readFile(new URL(entry.local, materialDir));
  if (local.length !== entry.bytes || createHash("sha256").update(local).digest("hex") !== entry.sha256)
    throw Error("Bedroom surface digest mismatch: " + entry.local);
  await writeFile(new URL("assets/" + entry.local, out), local);
}
await writeFile(new URL("assets/bedroom-sources.json", out), surfaceManifest);
const assets = new URL("../../../src/archimind/_viewer_assets/", src);
// Only publish content-addressed artifacts referenced by the release registry.
const registryBytes = await readFile(new URL("designer_registry.json", assets));
const registry = JSON.parse(registryBytes);
if (registry.schema_version !== 1 || !Array.isArray(registry.chairs))
  throw Error("Invalid designer chair release registry.");
const designerAssets = new Set();
for (const chair of [...registry.chairs, ...(registry.bedroom || [])]) {
  for (const [hash, ext] of [
    [chair.sha256, "glb"],
    [chair.front_sha256, "png"],
    [chair.three_quarter_sha256, "png"],
  ]) {
    if (typeof hash !== "string" || !/^[0-9a-f]{64}$/.test(hash))
      throw Error("Invalid designer chair artifact digest.");
    const name = "designer-" + hash + "." + ext;
    if (designerAssets.has(name)) continue;
    const bytes = await readFile(new URL(name, assets));
    if (createHash("sha256").update(bytes).digest("hex") !== hash)
      throw Error("Invalid designer chair artifact: " + name);
    await writeFile(new URL("assets/" + name, out), bytes);
    designerAssets.add(name);
  }
}
for (const name of await readdir(new URL("assets/", out))) {
  if (/^designer-[a-f0-9]{64}\.(glb|png)$/.test(name) && !designerAssets.has(name))
    await unlink(new URL("assets/" + name, out));
}
await writeFile(new URL("assets/designer_registry.json", out), registryBytes);
for (const f of [
  "BelayaDesk.glb",
  "BELAYA_ATTRIBUTION.txt",
  "ABO_LICENSE_CC_BY_4.0.txt",
  "BELAYA_PROVENANCE.json",
])
  await copyFile(
    new URL("furniture/" + f, assets),
    new URL("assets/" + f, out),
  );
await copyFile(
  new URL("../node_modules/three/LICENSE", src),
  new URL("assets/THREE-LICENSE.txt", out),
);
const local = process.env.TOWN_MODE === "local";
await writeFile(
  new URL("config.json", out),
  JSON.stringify({
    mode: local ? "local" : "hosted",
    api: process.env.TOWN_API_URL || (local ? "/api" : ""),
    editor:
      process.env.TOWN_EDITOR_URL || (local ? "http://127.0.0.1:8791" : ""),
    supabase: process.env.SUPABASE_URL || "",
    anon: process.env.SUPABASE_ANON_KEY || "",
  }),
);
