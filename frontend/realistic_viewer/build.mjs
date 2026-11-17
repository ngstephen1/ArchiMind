import {build} from 'esbuild';
import {copyFile, mkdir, readFile, writeFile} from 'node:fs/promises';
const out = new URL('../../src/archimind/_viewer_assets/', import.meta.url);
await mkdir(out, {recursive:true});
await build({entryPoints:[new URL('./src/main.js',import.meta.url).pathname], outfile:new URL('viewer.js',out).pathname,
  bundle:true, format:'esm', platform:'browser', target:['es2022'], minify:true, legalComments:'linked', logLevel:'info'});
for (const file of ['viewer.css','standalone.js','index.html','standalone-room.js','room.html']) {
  await copyFile(new URL(`./src/${file}`,import.meta.url),new URL(file,out));
}
await writeFile(new URL('THIRD_PARTY_NOTICES.txt',out), 'Three.js 0.186.1 (including addons), MIT license.\n\n'+await readFile(new URL('./node_modules/three/LICENSE',import.meta.url),'utf8'));
await writeFile(new URL('SPOKEN_WORLD_LICENSE.txt',out),await readFile(new URL('./vendor/spoken-world/LICENSE',import.meta.url),'utf8'));
await writeFile(new URL('SPOKEN_WORLD_NOTICE.txt',out),await readFile(new URL('./vendor/spoken-world/NOTICE',import.meta.url),'utf8'));
await writeFile(new URL('THIRD_PARTY_NOTICES.txt',out),await readFile(new URL('THIRD_PARTY_NOTICES.txt',out),'utf8')+'\n\n'+await readFile(new URL('./vendor/spoken-world/NOTICE',import.meta.url),'utf8')+'\nSee SPOKEN_WORLD_LICENSE.txt.\n');
