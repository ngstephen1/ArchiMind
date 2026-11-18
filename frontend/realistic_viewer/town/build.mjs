import { build } from "esbuild";
import { copyFile, mkdir, writeFile } from "node:fs/promises";
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
const assets = new URL("../../../src/archimind/_viewer_assets/", src);
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
