import {readFile,writeFile} from "node:fs/promises";
import {homeBoard} from "./home_board.js";
import {manifestText} from "./bedroom_manifest.js";
const [input,output]=process.argv.slice(2);
if(!input || !output) throw Error("Usage: node export-home.mjs SAVED_REVISION.json MANIFEST.json");
await writeFile(output,manifestText(homeBoard(JSON.parse(await readFile(input,"utf8")))));
