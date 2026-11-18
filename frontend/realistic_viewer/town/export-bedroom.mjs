import { readFile,writeFile } from "node:fs/promises";
import { bedroomManifest, manifestText, manifestDigest } from "./bedroom_manifest.js";

const [input,output]=process.argv.slice(2);
if (!input || !output) throw Error("Usage: node export-bedroom.mjs SAVED_REVISION.json MANIFEST.json");
const manifest=bedroomManifest(JSON.parse(await readFile(input,"utf8")));
await writeFile(output,manifestText(manifest));
console.log(await manifestDigest(manifest));
